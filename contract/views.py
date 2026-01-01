"""Contract API views for managing work agreements and payment workflows."""

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Contract, ContractStage, TimeExtensionRequest
from .serializers import (
    ContractListSerializer,
    ContractDetailSerializer,
    ContractCreateSerializer,
    ContractUpdateSerializer,
    ContractStageSerializer,
    TimeExtensionRequestSerializer,
)


class IsContractParty(IsAuthenticated):
    """
    Permission to ensure user is either client or technician in the contract.
    """
    def has_object_permission(self, request, view, obj):
        """Check if user is a party to this contract."""
        if hasattr(request.user, 'client_profile'):
            return obj.client.user == request.user
        elif hasattr(request.user, 'technician_profile'):
            return obj.technician.user == request.user
        return False


class ContractListCreateView(APIView):
    """
    GET: List contracts for authenticated user (client sees their contracts, technician sees assigned contracts)
    POST: Create a new contract (client only)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List contracts based on user role."""
        user = request.user
        
        # Client - show contracts where they are the client
        if hasattr(user, 'client_profile'):
            contracts = Contract.objects.filter(
                client=user.client_profile,
                is_delete=False
            ).select_related('client', 'technician')
        # Technician - show contracts where they are the technician
        elif hasattr(user, 'technician_profile'):
            contracts = Contract.objects.filter(
                technician=user.technician_profile,
                is_delete=False
            ).select_related('client', 'technician')
        else:
            return Response(
                {"detail": "User must have either client or technician profile."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ContractListSerializer(
            contracts,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Create a new contract (client only)."""
        # Verify user is a client
        if not hasattr(request.user, 'client_profile'):
            return Response(
                {"detail": "Only clients can create contracts."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ContractCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        try:
            contract = serializer.save()
            return Response(
                ContractDetailSerializer(contract, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ContractDetailView(APIView):
    """
    GET: Retrieve contract details
    PATCH: Update contract (technician completes, parties accept)
    """
    permission_classes = [IsAuthenticated]

    def get_contract(self, contract_id, user):
        """Get contract and verify user is a party."""
        contract = get_object_or_404(Contract, id=contract_id, is_delete=False)
        
        # Verify user is a party to this contract
        is_client = hasattr(user, 'client_profile') and contract.client.user == user
        is_technician = hasattr(user, 'technician_profile') and contract.technician.user == user
        
        if not (is_client or is_technician):
            raise PermissionError("You do not have permission to access this contract.")
        
        return contract

    def get(self, request, contract_id):
        """Retrieve contract details."""
        try:
            contract = self.get_contract(contract_id, request.user)
        except PermissionError:
            return Response(
                {"detail": "You do not have permission to access this contract."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ContractDetailSerializer(contract, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, contract_id):
        """Update contract."""
        try:
            contract = self.get_contract(contract_id, request.user)
        except PermissionError:
            return Response(
                {"detail": "You do not have permission to update this contract."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ContractUpdateSerializer(
            contract,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        try:
            updated_contract = serializer.save()
            return Response(
                ContractDetailSerializer(updated_contract, context={'request': request}).data,
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ContractStageListView(APIView):
    """
    GET: List all stages for a contract
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, contract_id):
        """List stages for a specific contract."""
        try:
            contract = get_object_or_404(Contract, id=contract_id, is_delete=False)
            
            # Verify user is a party
            is_client = hasattr(request.user, 'client_profile') and contract.client.user == request.user
            is_technician = hasattr(request.user, 'technician_profile') and contract.technician.user == request.user
            
            if not (is_client or is_technician):
                return Response(
                    {"detail": "You do not have permission to view these stages."},
                    status=status.HTTP_403_FORBIDDEN
                )
        except:
            return Response(
                {"detail": "Contract not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        stages = contract.stages.all().order_by('stage_number')
        serializer = ContractStageSerializer(stages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ContractStageDetailView(APIView):
    """
    GET: Retrieve stage details
    PATCH: Update stage (technician edits description/deadline, client approves)
    """
    permission_classes = [IsAuthenticated]

    def get_stage_and_contract(self, stage_id, user):
        """Get stage and verify user is a party to the contract."""
        stage = get_object_or_404(ContractStage, id=stage_id)
        contract = stage.contract
        
        # Verify user is a party
        is_client = hasattr(user, 'client_profile') and contract.client.user == user
        is_technician = hasattr(user, 'technician_profile') and contract.technician.user == user
        
        if not (is_client or is_technician):
            raise PermissionError("You do not have permission to access this stage.")
        
        return stage, contract, is_client, is_technician

    def get(self, request, stage_id):
        """Retrieve stage details."""
        try:
            stage, contract, _, _ = self.get_stage_and_contract(stage_id, request.user)
        except PermissionError:
            return Response(
                {"detail": "You do not have permission to access this stage."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ContractStageSerializer(stage)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, stage_id):
        """Update stage (technician edits, client approves)."""
        try:
            stage, contract, is_client, is_technician = self.get_stage_and_contract(stage_id, request.user)
        except PermissionError:
            return Response(
                {"detail": "You do not have permission to update this stage."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Verify contract is in progress
        if contract.status != 'in_progress':
            return Response(
                {"detail": "Cannot modify stages unless the contract is in progress."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Technician updates description/deadline
        if is_technician:
            if 'stage_description' in request.data or 'deadline' in request.data:
                stage.stage_description = request.data.get('stage_description', stage.stage_description)
                stage.deadline = request.data.get('deadline', stage.deadline)
                stage.save()
                serializer = ContractStageSerializer(stage)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"detail": "Technician can only update stage_description and deadline."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Client approves stage
        if is_client:
            if stage.is_approved_by_client:
                return Response(
                    {"detail": "This stage has already been approved."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                stage.approve_by_client()
                
                # Check if contract is complete (all stages approved)
                all_approved = not contract.stages.filter(
                    is_approved_by_client=False
                ).exists()
                
                if all_approved:
                    contract.mark_completed()
                
                return Response(
                    {"detail": "Stage approved and payment released."},
                    status=status.HTTP_200_OK
                )
            except Exception as e:
                return Response(
                    {"detail": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(
            {"detail": "Invalid request."},
            status=status.HTTP_400_BAD_REQUEST
        )


class TimeExtensionRequestListCreateView(APIView):
    """
    GET: List extension requests for user's contracts
    POST: Create a new extension request (technician only)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List extension requests based on user role."""
        user = request.user
        
        if hasattr(user, 'technician_profile'):
            # Technicians see their sent requests
            requests_qs = TimeExtensionRequest.objects.filter(
                requested_by=user.technician_profile
            ).select_related('contract')
        elif hasattr(user, 'client_profile'):
            # Clients see requests for their contracts
            requests_qs = TimeExtensionRequest.objects.filter(
                contract__client=user.client_profile
            ).select_related('contract')
        else:
            return Response(
                {"detail": "User must have either client or technician profile."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = TimeExtensionRequestSerializer(requests_qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Create a new extension request (technician only)."""
        # Verify user is a technician
        if not hasattr(request.user, 'technician_profile'):
            return Response(
                {"detail": "Only technicians can request extensions."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            contract_id = request.data.get('contract')
            contract = Contract.objects.get(id=contract_id, technician=request.user.technician_profile)
        except Contract.DoesNotExist:
            return Response(
                {"detail": "Contract not found or you are not the assigned technician."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = TimeExtensionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            ext_request = TimeExtensionRequest(
                contract=contract,
                requested_by=request.user.technician_profile,
                requested_days=serializer.validated_data['requested_days'],
                reason=serializer.validated_data['reason']
            )
            ext_request.full_clean()  # Run model validation
            ext_request.save()
            
            return Response(
                TimeExtensionRequestSerializer(ext_request).data,
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class TimeExtensionRequestRespondView(APIView):
    """
    POST: Respond to an extension request (client approve/reject)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id):
        """Respond to extension request."""
        try:
            ext_request = TimeExtensionRequest.objects.get(id=request_id)
        except TimeExtensionRequest.DoesNotExist:
            return Response(
                {"detail": "Extension request not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verify user is the client
        if not hasattr(request.user, 'client_profile') or ext_request.contract.client.user != request.user:
            return Response(
                {"detail": "Only the contract client can respond to extension requests."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if already processed
        if ext_request.status != 'pending':
            return Response(
                {"detail": "This extension request has already been processed."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        approve = request.data.get('approve', False)
        client_response = request.data.get('client_response', '')
        
        try:
            if approve:
                ext_request.approve(client_response)
            else:
                ext_request.reject(client_response)
            
            return Response(
                {"detail": f"Extension request has been {'approved' if approve else 'rejected'}."},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class TimeExtensionDistributeView(APIView):
    """
    POST: Distribute approved extension days to stages (technician only)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id):
        """Distribute extension days to contract stages."""
        # Verify user is a technician
        if not hasattr(request.user, 'technician_profile'):
            return Response(
                {"detail": "Only technicians can distribute extension days."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            ext_request = TimeExtensionRequest.objects.get(id=request_id)
        except TimeExtensionRequest.DoesNotExist:
            return Response(
                {"detail": "Extension request not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verify technician is the requester
        if ext_request.requested_by.user != request.user:
            return Response(
                {"detail": "Only the requesting technician can distribute extension days."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Verify request is approved
        if ext_request.status != 'approved':
            return Response(
                {"detail": "Only approved extension requests can have days distributed."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        distribution = request.data.get('distribution', {})
        
        # Validate distribution
        total_days = sum(int(v) for v in distribution.values() if isinstance(v, (int, str)))
        
        if total_days != ext_request.requested_days:
            return Response(
                {
                    "detail": f"Sum of distributed days ({total_days}) does not match approved days ({ext_request.requested_days})."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Apply distribution to stages
        try:
            contract = ext_request.contract
            for stage_id, additional_days in distribution.items():
                stage = contract.stages.get(id=stage_id)
                
                if stage.is_approved_by_client:
                    return Response(
                        {"detail": f"Stage {stage.stage_number} is already completed."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Update deadline
                from datetime import timedelta
                if stage.deadline:
                    stage.deadline += timedelta(days=int(additional_days))
                    stage.save()
            
            contract.contract_duration += timedelta(days=ext_request.requested_days)
            contract.save()
            
            return Response(
                {
                    "detail": "Extension days distributed successfully.",
                    "contract_duration": contract.contract_duration
                },
                status=status.HTTP_200_OK
            )
        except ContractStage.DoesNotExist:
            return Response(
                {"detail": f"One or more stages do not exist in this contract."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

