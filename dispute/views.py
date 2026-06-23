"""Phase 10 — Dispute, refund, and chargeback API views."""

from uuid import UUID

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from contract.models import Contract
from wallet.models import ContractSettlement

from .models import (
    ContractDispute,
    DisputeEvidence,
    DisputeStatement,
    RefundRecord,
    ChargebackEvent,
    UserFinancialLiability,
    DisputeStatus,
)
from .serializers import (
    DisputeListSerializer,
    DisputeDetailSerializer,
    DisputeCreateSerializer,
    DisputeStatementSerializer,
    DisputeStatementCreateSerializer,
    DisputeEvidenceSerializer,
    DisputeEvidenceCreateSerializer,
    DisputeEligibilitySerializer,
    AdminDisputeResolveSerializer,
    AdminDisputeAssignSerializer,
    AdminDisputeRejectSerializer,
    AdminDisputeResolutionProposeSerializer,
    RefundRecordSerializer,
    AdminRefundCreateSerializer,
    ChargebackEventSerializer,
    ChargebackSandboxCreateSerializer,
    ChargebackSandboxActionSerializer,
    ChargebackSandboxPartialSerializer,
    UserFinancialLiabilitySerializer,
)
from . import services as svc


# ──────────────────────────────────────────────
#  Permission helpers
# ──────────────────────────────────────────────


class IsAdminUser(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_staff


def _get_contract(contract_id, user):
    """Get contract with participant check."""
    try:
        contract = Contract.objects.get(id=contract_id)
    except Contract.DoesNotExist:
        return None
    is_participant = (
        (hasattr(user, "client_profile") and contract.client.user_id == user.id) or
        (hasattr(user, "technician_profile") and contract.technician.user_id == user.id) or
        user.is_staff
    )
    if not is_participant:
        return None
    return contract


def _get_dispute(dispute_id, user):
    """Get dispute with participant or staff check."""
    try:
        dispute = ContractDispute.objects.select_related(
            "contract", "opened_by", "respondent"
        ).get(id=dispute_id)
    except ContractDispute.DoesNotExist:
        return None
    is_participant = (
        dispute.opened_by_id == user.id or
        dispute.respondent_id == user.id
    )
    if not is_participant and not user.is_staff:
        return None
    return dispute


# ──────────────────────────────────────────────
#  Participant endpoints
# ──────────────────────────────────────────────


class DisputeListView(APIView):
    """List disputes for the current user (as opener, respondent, or staff)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            qs = ContractDispute.objects.all()
        else:
            qs = ContractDispute.objects.filter(
                opened_by=request.user,
            ) | ContractDispute.objects.filter(
                respondent=request.user,
            )
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        qs = qs.select_related("contract", "opened_by", "respondent").order_by("-created_at")
        serializer = DisputeListSerializer(qs, many=True)
        return Response(serializer.data)


class DisputeCreateView(APIView):
    """Open a new dispute on a contract."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DisputeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        contract_id = request.data.get("contract_id")
        if not contract_id:
            return Response(
                {"error": "contract_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate UUID
        try:
            UUID(str(contract_id))
        except (ValueError, AttributeError):
            return Response(
                {"error": "Invalid contract_id format."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        contract = _get_contract(contract_id, request.user)
        if not contract:
            return Response(
                {"error": "Contract not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            dispute = svc.open_dispute(
                contract_id=contract.id,
                opened_by=request.user,
                reason=serializer.validated_data["reason"],
                statement=serializer.validated_data["statement"],
                claimed_amount=serializer.validated_data["claimed_amount"],
                idempotency_key=serializer.validated_data.get("idempotency_key"),
            )
            output = DisputeDetailSerializer(dispute)
            return Response(output.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DisputeDetailView(APIView):
    """Get dispute details."""

    permission_classes = [IsAuthenticated]

    def get(self, request, dispute_id):
        dispute = _get_dispute(dispute_id, request.user)
        if not dispute:
            return Response({"error": "Dispute not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = DisputeDetailSerializer(dispute)
        return Response(serializer.data)


class DisputeStatementCreateView(APIView):
    """Add a statement to a dispute."""

    permission_classes = [IsAuthenticated]

    def post(self, request, dispute_id):
        dispute = _get_dispute(dispute_id, request.user)
        if not dispute:
            return Response({"error": "Dispute not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = DisputeStatementCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated_dispute = svc.add_dispute_statement(
                dispute_id=dispute.id,
                submitted_by=request.user,
                statement=serializer.validated_data["statement"],
            )
            output = DisputeDetailSerializer(updated_dispute)
            return Response(output.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DisputeEvidenceCreateView(APIView):
    """Submit evidence for a dispute."""

    permission_classes = [IsAuthenticated]

    def post(self, request, dispute_id):
        dispute = _get_dispute(dispute_id, request.user)
        if not dispute:
            return Response({"error": "Dispute not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = DisputeEvidenceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            evidence = svc.add_dispute_evidence(
                dispute_id=dispute.id,
                submitted_by=request.user,
                evidence_type=serializer.validated_data["evidence_type"],
                description=serializer.validated_data.get("description", ""),
                mime_type=serializer.validated_data.get("mime_type", ""),
                file_size=serializer.validated_data.get("file_size", 0),
                integrity_hash=serializer.validated_data.get("integrity_hash", ""),
            )
            output = DisputeEvidenceSerializer(evidence)
            return Response(output.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DisputeCancelView(APIView):
    """Cancel a dispute."""

    permission_classes = [IsAuthenticated]

    def post(self, request, dispute_id):
        dispute = _get_dispute(dispute_id, request.user)
        if not dispute:
            return Response({"error": "Dispute not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            updated = svc.cancel_dispute(dispute_id=dispute.id, actor=request.user)
            output = DisputeDetailSerializer(updated)
            return Response(output.data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ──────────────────────────────────────────────
#  Contract dispute eligibility
# ──────────────────────────────────────────────


class ContractDisputeEligibilityView(APIView):
    """Check if a contract is eligible for dispute."""

    permission_classes = [IsAuthenticated]

    def get(self, request, contract_id):
        contract = _get_contract(contract_id, request.user)
        if not contract:
            return Response({"error": "Contract not found."}, status=status.HTTP_404_NOT_FOUND)

        eligible, reason = svc.check_dispute_eligibility(contract, request.user)
        serializer = DisputeEligibilitySerializer(data={"eligible": eligible, "reason": reason})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)


class ContractActiveDisputeView(APIView):
    """Get the active dispute for a contract, if any."""

    permission_classes = [IsAuthenticated]

    def get(self, request, contract_id):
        contract = _get_contract(contract_id, request.user)
        if not contract:
            return Response({"error": "Contract not found."}, status=status.HTTP_404_NOT_FOUND)

        dispute = ContractDispute.objects.filter(
            contract=contract,
            status__in=[DisputeStatus.OPEN, DisputeStatus.AWAITING_RESPONSE,
                         DisputeStatus.UNDER_REVIEW, DisputeStatus.MEDIATION,
                         DisputeStatus.RESOLUTION_PROPOSED],
        ).first()

        if not dispute:
            return Response({"active": False, "dispute": None})

        serializer = DisputeListSerializer(dispute)
        return Response({"active": True, "dispute": serializer.data})


# ──────────────────────────────────────────────
#  Staff endpoints
# ──────────────────────────────────────────────


class AdminDisputeListView(APIView):
    """List all disputes for staff."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = ContractDispute.objects.all().select_related(
            "contract", "opened_by", "respondent", "assigned_staff",
        )
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        category_filter = request.query_params.get("category")
        if category_filter:
            qs = qs.filter(category=category_filter)
        qs = qs.order_by("-created_at")
        serializer = DisputeListSerializer(qs, many=True)
        return Response(serializer.data)


class AdminDisputeDetailView(APIView):
    """Full dispute detail for staff."""

    permission_classes = [IsAdminUser]

    def get(self, request, dispute_id):
        try:
            dispute = ContractDispute.objects.select_related(
                "contract", "opened_by", "respondent", "assigned_staff",
            ).get(id=dispute_id)
        except ContractDispute.DoesNotExist:
            return Response({"error": "Dispute not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = DisputeDetailSerializer(dispute)
        return Response(serializer.data)


class AdminDisputeAssignView(APIView):
    """Assign staff to a dispute."""

    permission_classes = [IsAdminUser]

    def post(self, request, dispute_id):
        try:
            dispute = ContractDispute.objects.get(id=dispute_id)
        except ContractDispute.DoesNotExist:
            return Response({"error": "Dispute not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminDisputeAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from accounts.models import CustomUser
        try:
            staff_user = CustomUser.objects.get(id=serializer.validated_data["staff_id"], is_staff=True)
        except CustomUser.DoesNotExist:
            return Response({"error": "Staff user not found."}, status=status.HTTP_404_NOT_FOUND)

        updated = svc.assign_staff(dispute_id=dispute.id, staff_user=staff_user)
        output = DisputeDetailSerializer(updated)
        return Response(output.data)


class AdminDisputeStartReviewView(APIView):
    """Start review of a dispute."""

    permission_classes = [IsAdminUser]

    def post(self, request, dispute_id):
        try:
            dispute = ContractDispute.objects.get(id=dispute_id)
        except ContractDispute.DoesNotExist:
            return Response({"error": "Dispute not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            updated = svc.start_review(dispute_id=dispute.id, actor=request.user)
            output = DisputeDetailSerializer(updated)
            return Response(output.data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminDisputeStartMediationView(APIView):
    """Start mediation."""

    permission_classes = [IsAdminUser]

    def post(self, request, dispute_id):
        try:
            dispute = ContractDispute.objects.get(id=dispute_id)
        except ContractDispute.DoesNotExist:
            return Response({"error": "Dispute not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            updated = svc.start_mediation(dispute_id=dispute.id, actor=request.user)
            output = DisputeDetailSerializer(updated)
            return Response(output.data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminDisputeProposeResolutionView(APIView):
    """Propose resolution (no financial execution)."""

    permission_classes = [IsAdminUser]

    def post(self, request, dispute_id):
        try:
            dispute = ContractDispute.objects.get(id=dispute_id)
        except ContractDispute.DoesNotExist:
            return Response({"error": "Dispute not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminDisputeResolutionProposeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = svc.propose_resolution(
                dispute_id=dispute.id,
                actor=request.user,
                resolution_data=serializer.validated_data,
            )
            output = DisputeDetailSerializer(updated)
            return Response(output.data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminDisputeResolveView(APIView):
    """Resolve a dispute with full financial execution."""

    permission_classes = [IsAdminUser]

    def post(self, request, dispute_id):
        try:
            dispute = ContractDispute.objects.get(id=dispute_id)
        except ContractDispute.DoesNotExist:
            return Response({"error": "Dispute not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminDisputeResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated, resolution, refund_record, liability = svc.resolve_dispute(
                dispute_id=dispute.id,
                actor=request.user,
                **serializer.validated_data,
            )
            output = DisputeDetailSerializer(updated)
            result = output.data
            result["resolution"] = serializer.__class__.__name__
            return Response(result)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminDisputeRejectView(APIView):
    """Reject a dispute."""

    permission_classes = [IsAdminUser]

    def post(self, request, dispute_id):
        try:
            dispute = ContractDispute.objects.get(id=dispute_id)
        except ContractDispute.DoesNotExist:
            return Response({"error": "Dispute not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminDisputeRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = svc.reject_dispute(
                dispute_id=dispute.id,
                actor=request.user,
                reason=serializer.validated_data.get("reason", ""),
            )
            output = DisputeDetailSerializer(updated)
            return Response(output.data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminDisputeCloseView(APIView):
    """Close a resolved/rejected dispute."""

    permission_classes = [IsAdminUser]

    def post(self, request, dispute_id):
        try:
            dispute = ContractDispute.objects.get(id=dispute_id)
        except ContractDispute.DoesNotExist:
            return Response({"error": "Dispute not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            updated = svc.close_dispute(dispute_id=dispute.id, actor=request.user)
            output = DisputeDetailSerializer(updated)
            return Response(output.data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminDisputeReconciliationView(APIView):
    """Get reconciliation data for a dispute."""

    permission_classes = [IsAdminUser]

    def get(self, request, dispute_id):
        try:
            dispute = ContractDispute.objects.get(id=dispute_id)
        except ContractDispute.DoesNotExist:
            return Response({"error": "Dispute not found."}, status=status.HTTP_404_NOT_FOUND)

        data = svc.get_dispute_reconciliation(str(dispute.id))
        return Response(data)


# ──────────────────────────────────────────────
#  Refund endpoints
# ──────────────────────────────────────────────


class DisputeRefundListView(APIView):
    """List refunds for a dispute."""

    permission_classes = [IsAuthenticated]

    def get(self, request, dispute_id):
        dispute = _get_dispute(dispute_id, request.user)
        if not dispute:
            return Response({"error": "Dispute not found."}, status=status.HTTP_404_NOT_FOUND)
        refunds = RefundRecord.objects.filter(dispute=dispute).order_by("-created_at")
        serializer = RefundRecordSerializer(refunds, many=True)
        return Response(serializer.data)


class AdminDisputeRefundCreateView(APIView):
    """Staff-initiated refund for a dispute."""

    permission_classes = [IsAdminUser]

    def post(self, request, dispute_id):
        try:
            dispute = ContractDispute.objects.get(id=dispute_id)
        except ContractDispute.DoesNotExist:
            return Response({"error": "Dispute not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminRefundCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Execute refund through resolution (creates resolution if needed)
        try:
            updated, resolution, refund_record, liability = svc.resolve_dispute(
                dispute_id=dispute.id,
                actor=request.user,
                resolution_type="full_client_refund",
                client_refund_amount=serializer.validated_data["amount"],
                resolution_reason="Admin-initiated refund.",
                idempotency_key=serializer.validated_data.get("idempotency_key"),
            )
            if refund_record:
                output = RefundRecordSerializer(refund_record)
                return Response(output.data, status=status.HTTP_201_CREATED)
            return Response({"error": "Refund could not be created."}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RefundDetailView(APIView):
    """Get refund details."""

    permission_classes = [IsAuthenticated]

    def get(self, request, refund_id):
        try:
            refund = RefundRecord.objects.get(id=refund_id)
        except RefundRecord.DoesNotExist:
            return Response({"error": "Refund not found."}, status=status.HTTP_404_NOT_FOUND)

        # Check permission
        is_participant = (
            refund.client_id == request.user.id or
            refund.created_by_id == request.user.id or
            request.user.is_staff
        )
        if not is_participant:
            return Response({"error": "Refund not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = RefundRecordSerializer(refund)
        return Response(serializer.data)


class AdminRefundSandboxConfirmView(APIView):
    """Sandbox confirm a refund."""

    permission_classes = [IsAdminUser]

    def post(self, request, refund_id):
        try:
            refund = RefundRecord.objects.get(id=refund_id)
        except RefundRecord.DoesNotExist:
            return Response({"error": "Refund not found."}, status=status.HTTP_404_NOT_FOUND)

        if refund.status == "completed":
            serializer = RefundRecordSerializer(refund)
            return Response(serializer.data)

        refund.status = "completed"
        refund.completed_at = timezone.now()
        refund.save(update_fields=["status", "completed_at"])

        serializer = RefundRecordSerializer(refund)
        return Response(serializer.data)


class AdminRefundRetryView(APIView):
    """Retry a failed refund."""

    permission_classes = [IsAdminUser]

    def post(self, request, refund_id):
        try:
            refund = RefundRecord.objects.get(id=refund_id)
        except RefundRecord.DoesNotExist:
            return Response({"error": "Refund not found."}, status=status.HTTP_404_NOT_FOUND)

        if refund.status != "failed":
            return Response({"error": "Only failed refunds can be retried."}, status=status.HTTP_400_BAD_REQUEST)

        refund.status = "processing"
        refund.failure_code = ""
        refund.failure_message = ""
        refund.save(update_fields=["status", "failure_code", "failure_message"])

        # Re-execute refund
        try:
            svc.resolve_dispute(
                dispute_id=refund.dispute_id,
                actor=request.user,
                resolution_type="full_client_refund",
                client_refund_amount=refund.amount,
                resolution_reason="Retry of failed refund.",
            )
        except ValueError as e:
            refund.status = "failed"
            refund.failure_message = str(e)
            refund.save(update_fields=["status", "failure_message"])
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        refund.refresh_from_db()
        serializer = RefundRecordSerializer(refund)
        return Response(serializer.data)


# ──────────────────────────────────────────────
#  Chargeback endpoints
# ──────────────────────────────────────────────


class AdminChargebackListView(APIView):
    """List all chargebacks."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = ChargebackEvent.objects.all().select_related("contract", "dispute")
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        qs = qs.order_by("-created_at")
        serializer = ChargebackEventSerializer(qs, many=True)
        return Response(serializer.data)


class AdminChargebackSandboxCreateView(APIView):
    """Create a sandbox chargeback event."""

    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = ChargebackSandboxCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            cb = svc.create_sandbox_chargeback(
                contract_id=serializer.validated_data["contract_id"],
                amount=serializer.validated_data["amount"],
                reason_code=serializer.validated_data.get("reason_code", ""),
                created_by=request.user,
                idempotency_key=serializer.validated_data.get("idempotency_key"),
            )
            output = ChargebackEventSerializer(cb)
            return Response(output.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminChargebackDetailView(APIView):
    """Get chargeback details."""

    permission_classes = [IsAdminUser]

    def get(self, request, chargeback_id):
        try:
            cb = ChargebackEvent.objects.select_related(
                "contract", "dispute", "resolved_by",
            ).get(id=chargeback_id)
        except ChargebackEvent.DoesNotExist:
            return Response({"error": "Chargeback not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ChargebackEventSerializer(cb)
        return Response(serializer.data)


class AdminChargebackStartReviewView(APIView):
    """Start chargeback review."""

    permission_classes = [IsAdminUser]

    def post(self, request, chargeback_id):
        try:
            cb = ChargebackEvent.objects.get(id=chargeback_id)
        except ChargebackEvent.DoesNotExist:
            return Response({"error": "Chargeback not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            updated = svc.start_chargeback_review(chargeback_id=cb.id, actor=request.user)
            output = ChargebackEventSerializer(updated)
            return Response(output.data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminChargebackSubmitEvidenceView(APIView):
    """Submit evidence for chargeback."""

    permission_classes = [IsAdminUser]

    def post(self, request, chargeback_id):
        try:
            cb = ChargebackEvent.objects.get(id=chargeback_id)
        except ChargebackEvent.DoesNotExist:
            return Response({"error": "Chargeback not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            updated = svc.submit_chargeback_evidence(chargeback_id=cb.id, actor=request.user)
            output = ChargebackEventSerializer(updated)
            return Response(output.data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminChargebackSandboxUpholdView(APIView):
    """Sandbox: uphold chargeback."""

    permission_classes = [IsAdminUser]

    def post(self, request, chargeback_id):
        serializer = ChargebackSandboxActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            cb, dispute, resolution = svc.sandbox_uphold_chargeback(
                chargeback_id=chargeback_id,
                actor=request.user,
                idempotency_key=serializer.validated_data.get("idempotency_key"),
            )
            output = ChargebackEventSerializer(cb)
            return Response(output.data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminChargebackSandboxRejectView(APIView):
    """Sandbox: reject chargeback."""

    permission_classes = [IsAdminUser]

    def post(self, request, chargeback_id):
        serializer = ChargebackSandboxActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            cb = svc.sandbox_reject_chargeback(
                chargeback_id=chargeback_id,
                actor=request.user,
                idempotency_key=serializer.validated_data.get("idempotency_key"),
            )
            output = ChargebackEventSerializer(cb)
            return Response(output.data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminChargebackSandboxPartialView(APIView):
    """Sandbox: partial chargeback."""

    permission_classes = [IsAdminUser]

    def post(self, request, chargeback_id):
        serializer = ChargebackSandboxPartialSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            cb = svc.sandbox_partial_chargeback(
                chargeback_id=chargeback_id,
                actor=request.user,
                partial_amount=serializer.validated_data["partial_amount"],
                idempotency_key=serializer.validated_data.get("idempotency_key"),
            )
            output = ChargebackEventSerializer(cb)
            return Response(output.data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
