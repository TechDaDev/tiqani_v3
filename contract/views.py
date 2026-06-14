"""Contract API views for managing work agreements and payment workflows."""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.http import FileResponse
from django.utils import timezone
from django.db import transaction
from drf_spectacular.utils import OpenApiResponse, extend_schema

from .models import Contract, ContractStage, TimeExtensionRequest
from .serializers import (
    ContractListSerializer,
    ContractDetailSerializer,
    ContractCreateSerializer,
    ContractProposalSerializer,
    ContractAcceptSerializer,
    ContractCancelSerializer,
    ContractStageSerializer,
    TimeExtensionRequestSerializer,
    TimeExtensionCreateSerializer,
    ExtensionRespondSerializer,
    ContractSignSerializer,
    ContractSignatureSerializer,
    ContractDocumentSerializer,
    PublicVerifyCodeSerializer,
    PublicVerifyPdfSerializer,
)
from .permissions import IsContractParticipantOrAdmin, IsContractClient, IsContractTechnician, IsAdminUser
from . import services as svc
from accounts.models import TechnicianProfile, ClientProfile


# ──────────────────────────────────────────────
#  Contract list & create
# ──────────────────────────────────────────────

class ContractListCreateView(APIView):
    """
    GET:  List contracts (client sees own, tech sees own, admin sees all)
    POST: Create a draft contract (client only)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        qs = Contract.objects.filter(is_delete=False).select_related("client", "technician")

        # Filter by role
        if hasattr(user, "client_profile"):
            qs = qs.filter(client=user.client_profile)
        elif hasattr(user, "technician_profile"):
            qs = qs.filter(technician=user.technician_profile)
        elif user.is_staff:
            pass  # admin sees all
        else:
            return Response(
                {"detail": "User must have client or technician profile."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Query params
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        created_after = request.query_params.get("created_after")
        if created_after:
            qs = qs.filter(created_at__gte=created_after)

        created_before = request.query_params.get("created_before")
        if created_before:
            qs = qs.filter(created_at__lte=created_before)

        ordering = request.query_params.get("ordering", "-created_at")
        allowed_ordering = {"created_at", "-created_at", "status", "-status", "agreed_amount", "-agreed_amount"}
        if ordering.lstrip("-") not in {o.lstrip("-") for o in allowed_ordering}:
            ordering = "-created_at"
        qs = qs.order_by(ordering)

        serializer = ContractListSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if not hasattr(request.user, "client_profile"):
            return Response(
                {"detail": "Only clients can create contracts."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ContractCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        try:
            contract = serializer.save()
            return Response(
                ContractDetailSerializer(contract, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ──────────────────────────────────────────────
#  Contract detail, proposal, accept, cancel
# ──────────────────────────────────────────────

class ContractDetailView(APIView):
    """GET detail, PATCH proposal (technician)."""
    permission_classes = [IsAuthenticated]

    def _get_contract(self, contract_id, user):
        contract = get_object_or_404(Contract, id=contract_id, is_delete=False)
        if not self._is_participant(contract, user):
            raise PermissionError
        return contract

    def _is_participant(self, contract, user):
        if user.is_staff:
            return True
        if hasattr(user, "client_profile") and contract.client.user == user:
            return True
        if hasattr(user, "technician_profile") and contract.technician.user == user:
            return True
        return False

    def get(self, request, contract_id):
        try:
            contract = self._get_contract(contract_id, request.user)
        except PermissionError:
            return Response(
                {"detail": "You do not have permission to access this contract."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ContractDetailSerializer(contract, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, contract_id):
        """Technician updates proposal on draft contract."""
        try:
            contract = self._get_contract(contract_id, request.user)
        except PermissionError:
            return Response(
                {"detail": "You do not have permission to update this contract."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Only technician can fill proposal on draft
        if not hasattr(request.user, "technician_profile"):
            return Response(
                {"detail": "Only the assigned technician can update the proposal."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if contract.status != "draft":
            return Response(
                {"detail": "Proposal can only be updated on draft contracts."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ContractProposalSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            contract = svc.update_contract_proposal(contract, request.user.technician_profile, serializer.validated_data)
            return Response(
                ContractDetailSerializer(contract, context={"request": request}).data,
                status=status.HTTP_200_OK,
            )
        except (ValueError, PermissionError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ContractAcceptView(APIView):
    """POST: Accept contract (client or technician)."""
    permission_classes = [IsAuthenticated]

    def post(self, request, contract_id):
        contract = get_object_or_404(Contract, id=contract_id, is_delete=False)

        try:
            contract = svc.accept_contract(contract, request.user)
            return Response(
                ContractDetailSerializer(contract, context={"request": request}).data,
                status=status.HTTP_200_OK,
            )
        except (ValueError, PermissionError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ContractCancelView(APIView):
    """POST: Cancel contract."""
    permission_classes = [IsAuthenticated]

    def post(self, request, contract_id):
        contract = get_object_or_404(Contract, id=contract_id, is_delete=False)
        serializer = ContractCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            contract = svc.cancel_contract(contract, request.user, serializer.validated_data.get("reason", ""))
            return Response(
                ContractDetailSerializer(contract, context={"request": request}).data,
                status=status.HTTP_200_OK,
            )
        except (ValueError, PermissionError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ──────────────────────────────────────────────
#  Contract stages
# ──────────────────────────────────────────────

class ContractStageListView(APIView):
    """GET: List stages for a contract."""
    permission_classes = [IsAuthenticated]

    def get(self, request, **kwargs):
        contract = get_object_or_404(Contract, id=kwargs["contract_id"], is_delete=False)
        if not _is_participant(contract, request.user):
            return Response(
                {"detail": "You do not have permission."},
                status=status.HTTP_403_FORBIDDEN,
            )
        stages = contract.stages.all().order_by("stage_number")
        serializer = ContractStageSerializer(stages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ContractStageDetailView(APIView):
    """GET detail, PATCH update stage (technician only, before approval)."""
    permission_classes = [IsAuthenticated]

    def get(self, request, **kwargs):
        stage_id = kwargs.get("stage_id")
        stage = get_object_or_404(ContractStage, id=stage_id)
        contract = stage.contract
        if not _is_participant(contract, request.user):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        serializer = ContractStageSerializer(stage)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, **kwargs):
        stage_id = kwargs.get("stage_id")
        stage = get_object_or_404(ContractStage, id=stage_id)
        contract = stage.contract
        if not hasattr(request.user, "technician_profile"):
            return Response(
                {"detail": "Only the technician can update stage details."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            stage = svc.update_stage(stage, request.user.technician_profile, request.data)
            return Response(ContractStageSerializer(stage).data, status=status.HTTP_200_OK)
        except (ValueError, PermissionError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ContractStageSubmitView(APIView):
    """POST: Technician submits stage as complete."""
    permission_classes = [IsAuthenticated]

    def post(self, request, **kwargs):
        contract = get_object_or_404(Contract, id=kwargs["contract_id"], is_delete=False)
        stage = get_object_or_404(ContractStage, id=kwargs["stage_id"], contract=contract)
        if not hasattr(request.user, "technician_profile"):
            return Response({"detail": "Only technicians can submit stages."}, status=status.HTTP_403_FORBIDDEN)
        try:
            stage = svc.submit_stage(stage, request.user.technician_profile)
            return Response(ContractStageSerializer(stage).data, status=status.HTTP_200_OK)
        except (ValueError, PermissionError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ContractStageApproveView(APIView):
    """POST: Client approves stage — payment released."""
    permission_classes = [IsAuthenticated]

    def post(self, request, **kwargs):
        contract = get_object_or_404(Contract, id=kwargs["contract_id"], is_delete=False)
        stage = get_object_or_404(ContractStage, id=kwargs["stage_id"], contract=contract)
        if not hasattr(request.user, "client_profile"):
            return Response({"detail": "Only the client can approve stages."}, status=status.HTTP_403_FORBIDDEN)
        try:
            stage = svc.approve_stage(stage, request.user.client_profile)
            return Response(
                {"detail": f"Stage {stage.stage_number} approved and payment released.", "stage": ContractStageSerializer(stage).data},
                status=status.HTTP_200_OK,
            )
        except (ValueError, PermissionError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ──────────────────────────────────────────────
#  Time extension requests
# ──────────────────────────────────────────────

class ContractExtensionListView(APIView):
    """GET: List extension requests for a contract."""
    permission_classes = [IsAuthenticated]

    def get(self, request, **kwargs):
        contract = get_object_or_404(Contract, id=kwargs["contract_id"], is_delete=False)
        if not _is_participant(contract, request.user):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        qs = contract.extension_requests.all()
        serializer = TimeExtensionRequestSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ContractExtensionCreateView(APIView):
    """POST: Technician creates extension request."""
    permission_classes = [IsAuthenticated]

    def post(self, request, **kwargs):
        contract = get_object_or_404(Contract, id=kwargs["contract_id"], is_delete=False)

        if not hasattr(request.user, "technician_profile"):
            return Response(
                {"detail": "Only technicians can request extensions."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = TimeExtensionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            ext = svc.create_extension_request(
                contract, request.user.technician_profile, serializer.validated_data
            )
            return Response(
                TimeExtensionRequestSerializer(ext).data,
                status=status.HTTP_201_CREATED,
            )
        except (ValueError, PermissionError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ContractExtensionRespondView(APIView):
    """POST: Client approves or rejects extension request."""
    permission_classes = [IsAuthenticated]

    def post(self, request, **kwargs):
        contract = get_object_or_404(Contract, id=kwargs["contract_id"], is_delete=False)
        ext = get_object_or_404(TimeExtensionRequest, id=kwargs["request_id"], contract=contract)

        if not hasattr(request.user, "client_profile"):
            return Response({"detail": "Only the contract client can respond."}, status=status.HTTP_403_FORBIDDEN)

        # Determine if approve or reject based on URL name
        is_approve = request.resolver_match.url_name == "contract-extension-approve"

        if not is_approve:
            serializer = ExtensionRespondSerializer(data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            approve = False
            response_text = serializer.validated_data.get("client_response", "")
        else:
            serializer = ExtensionRespondSerializer(data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            approve = serializer.validated_data.get("approve", True)
            response_text = serializer.validated_data.get("client_response", "")

        try:
            ext = svc.respond_extension_request(ext, request.user.client_profile, approve, response_text)
            return Response(
                {"detail": f"Extension request {'approved' if ext.status == 'approved' else 'rejected'}."},
                status=status.HTTP_200_OK,
            )
        except (ValueError, PermissionError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ──────────────────────────────────────────────
#  Phase 19: Freeze, Sign, Finalize, Verify
# ──────────────────────────────────────────────

class ContractFreezeView(APIView):
    """POST: Freeze immutable contract snapshot for signatures."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={
            200: OpenApiResponse(description='Contract version frozen.'),
            400: OpenApiResponse(description='Invalid state for freezing.'),
            403: OpenApiResponse(description='Permission denied.'),
        },
        tags=['Contracts'],
    )
    def post(self, request, **kwargs):
        contract = get_object_or_404(Contract, id=kwargs["contract_id"], is_delete=False)
        try:
            version = svc.freeze_contract_version(contract, request.user)
            return Response(
                {
                    "detail": "Contract version frozen.",
                    "version_number": version.version_number,
                    "snapshot_hash": version.canonical_snapshot_hash,
                },
                status=status.HTTP_200_OK,
            )
        except PermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ContractRequestSignatureOtpView(APIView):
    """POST: Request OTP email for signing."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={
            200: OpenApiResponse(description='OTP sent to email for signature.'),
            400: OpenApiResponse(description='Failed to send OTP or invalid state.'),
            403: OpenApiResponse(description='Permission denied.'),
        },
        tags=['Contracts'],
    )
    def post(self, request, **kwargs):
        contract = get_object_or_404(Contract, id=kwargs["contract_id"], is_delete=False)
        try:
            otp = svc.request_signature_otp(contract, request.user)
            return Response(
                {
                    "detail": "OTP sent to email for signature.",
                    "verification_id": otp.verification_id,
                },
                status=status.HTTP_200_OK,
            )
        except PermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ContractSignView(APIView):
    """POST: Submit OTP to sign frozen contract version."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ContractSignSerializer,
        responses={
            200: ContractSignatureSerializer,
            400: OpenApiResponse(description='Invalid OTP or contract state.'),
            403: OpenApiResponse(description='Permission denied.'),
        },
        tags=['Contracts'],
    )
    def post(self, request, **kwargs):
        contract = get_object_or_404(Contract, id=kwargs["contract_id"], is_delete=False)
        serializer = ContractSignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            signature = svc.sign_contract_version(
                contract,
                request.user,
                serializer.validated_data["otp_code"],
                ip_address=self._client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )
            return Response(ContractSignatureSerializer(signature).data, status=status.HTTP_200_OK)
        except PermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def _client_ip(self, request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")


class ContractSignaturesView(APIView):
    """GET: List signatures for latest frozen version."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: ContractSignatureSerializer(many=True),
            403: OpenApiResponse(description='Permission denied.'),
        },
        tags=['Contracts'],
    )
    def get(self, request, **kwargs):
        contract = get_object_or_404(Contract, id=kwargs["contract_id"], is_delete=False)
        try:
            signatures = svc.get_contract_signatures(contract, request.user)
            return Response(ContractSignatureSerializer(signatures, many=True).data, status=status.HTTP_200_OK)
        except PermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)


class ContractFinalizeView(APIView):
    """POST: Finalize signed contract and activate escrow/workflow."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={
            200: OpenApiResponse(description='Contract finalized successfully.'),
            400: OpenApiResponse(description='Invalid state or missing signatures.'),
            403: OpenApiResponse(description='Permission denied.'),
        },
        tags=['Contracts'],
    )
    def post(self, request, **kwargs):
        contract = get_object_or_404(Contract, id=kwargs["contract_id"], is_delete=False)
        if not (_is_participant(contract, request.user) or request.user.is_staff):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        try:
            result = svc.finalize_signed_contract(contract, request.user)
            return Response(
                {
                    "detail": "Contract finalized successfully.",
                    "contract_id": str(result["contract"].id),
                    "status": result["contract"].status,
                    "version_number": result["version"].version_number if result.get("version") else None,
                    "verification_code": result["attestation"].verification_code if result.get("attestation") else None,
                    "document_sha256": result["document"].sha256 if result.get("document") else None,
                },
                status=status.HTTP_200_OK,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ContractDocumentsView(APIView):
    """GET: List contract document metadata."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: ContractDocumentSerializer(many=True),
            403: OpenApiResponse(description='Permission denied.'),
        },
        tags=['Contracts'],
    )
    def get(self, request, **kwargs):
        contract = get_object_or_404(Contract, id=kwargs["contract_id"], is_delete=False)
        try:
            documents = svc.get_contract_documents(contract, request.user)
            return Response(
                ContractDocumentSerializer(documents, many=True, context={"request": request}).data,
                status=status.HTTP_200_OK,
            )
        except PermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)


class ContractFinalDocumentView(APIView):
    """GET: Download final signed PDF document."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: OpenApiResponse(description='Signed PDF file response.'),
            403: OpenApiResponse(description='Permission denied.'),
            404: OpenApiResponse(description='Final document not found.'),
        },
        tags=['Contracts'],
    )
    def get(self, request, **kwargs):
        contract = get_object_or_404(Contract, id=kwargs["contract_id"], is_delete=False)
        try:
            document = svc.get_final_document(contract, request.user)
        except PermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)

        if not document or not document.file:
            return Response({"detail": "Final signed document not found."}, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(document.file.open("rb"), content_type=document.mime_type)


class PublicVerifyCodeView(APIView):
    """GET: Public verification by attestation code (no auth required)."""
    permission_classes = []
    authentication_classes = []

    @extend_schema(
        responses={
            200: PublicVerifyCodeSerializer,
            404: OpenApiResponse(description='Verification code not found.'),
        },
        tags=['Contracts Public Verification'],
    )
    def get(self, request, verification_code):
        try:
            result = svc.public_verify_by_code(verification_code)
            return Response(result, status=status.HTTP_200_OK)
        except Exception:
            return Response({"detail": "Verification code not found."}, status=status.HTTP_404_NOT_FOUND)


class PublicVerifyPdfView(APIView):
    """POST: Public verification by uploaded PDF hash."""
    permission_classes = []
    authentication_classes = []

    @extend_schema(
        request=PublicVerifyPdfSerializer,
        responses={
            200: OpenApiResponse(description='PDF verification result.'),
            400: OpenApiResponse(description='Invalid file.'),
        },
        tags=['Contracts Public Verification'],
    )
    def post(self, request):
        serializer = PublicVerifyPdfSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = svc.public_verify_uploaded_pdf(serializer.validated_data["file"])
        return Response(result, status=status.HTTP_200_OK)


# ──────────────────────────────────────────────
#  Helper
# ──────────────────────────────────────────────

def _is_participant(contract, user):
    if user.is_staff:
        return True
    if hasattr(user, "client_profile") and contract.client.user == user:
        return True
    if hasattr(user, "technician_profile") and contract.technician.user == user:
        return True
    return False

