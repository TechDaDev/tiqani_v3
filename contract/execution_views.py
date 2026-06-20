"""Views for Phase 8 contract execution and milestone workflow."""

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import (
    ListModelMixin,
    CreateModelMixin,
    RetrieveModelMixin,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound

from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import (
    Contract,
    ExecutionMilestone,
    DeliverableSubmission,
    RevisionRequest,
    CompletionRequest,
)
from .execution_serializers import (
    ExecutionMilestoneListSerializer,
    ExecutionMilestoneCreateSerializer,
    ExecutionMilestoneUpdateSerializer,
    ExecutionMilestoneDetailSerializer,
    ExecutionMilestoneReorderSerializer,
    DeliverableCreateSerializer,
    DeliverableSubmissionSerializer,
    RevisionCreateSerializer,
    RevisionRequestSerializer,
    CompletionRequestSerializer,
    CompletionRequestCreateSerializer,
    CompletionRespondSerializer,
    ExecutionHistorySerializer,
    ContractExecutionEligibilitySerializer,
)
from .execution_permissions import (
    IsContractClient,
    IsContractTechnician,
    IsContractParticipant,
    IsMilestoneContractClient,
    IsMilestoneContractTechnician,
    IsCompletionContractClient,
    IsCompletionContractTechnician,
)
from .execution_services import (
    check_execution_eligibility,
    check_completion_eligibility,
    activate_contract,
    create_milestone,
    start_milestone,
    submit_deliverable,
    request_revision,
    approve_milestone,
    request_completion,
    confirm_completion,
    reject_completion,
    reorder_milestones,
    get_execution_history,
)


def _get_contract(contract_id, user):
    """Get contract with participant check."""
    try:
        contract = Contract.objects.get(id=contract_id)
    except Contract.DoesNotExist:
        raise NotFound("Contract not found.")
    if not (
        hasattr(user, 'client_profile') and contract.client.user == user or
        hasattr(user, 'technician_profile') and contract.technician.user == user or
        user.is_staff
    ):
        raise NotFound("Contract not found.")
    return contract


def _get_milestone(milestone_id, user):
    """Get milestone with participant check."""
    try:
        milestone = ExecutionMilestone.objects.select_related('contract').get(id=milestone_id)
    except ExecutionMilestone.DoesNotExist:
        raise NotFound("Milestone not found.")
    contract = milestone.contract
    if not (
        hasattr(user, 'client_profile') and contract.client.user == user or
        hasattr(user, 'technician_profile') and contract.technician.user == user or
        user.is_staff
    ):
        raise NotFound("Milestone not found.")
    return milestone


# ──────────────────────────────────────────────
#  Eligibility & Activation
# ──────────────────────────────────────────────


class ContractExecutionEligibilityView(GenericAPIView):
    """Check if contract can start execution."""
    permission_classes = [IsAuthenticated]

    def get(self, request, contract_id):
        contract = _get_contract(contract_id, request.user)
        eligible, reason = check_execution_eligibility(contract, request.user)

        from wallet.services import get_contract_funding_status
        funding_status_str = get_contract_funding_status(contract)

        milestone_count = contract.execution_milestones.count()
        can_complete, comp_reason = check_completion_eligibility(contract, request.user)
        has_pending_completion = contract.completion_requests.filter(
            status=CompletionRequest.Status.PENDING
        ).exists()

        serializer = ContractExecutionEligibilitySerializer({
            'eligible': eligible,
            'reason': reason,
            'contract_status': contract.status,
            'funding_status': funding_status_str,
            'milestone_count': milestone_count,
            'can_activate': eligible,
            'can_request_completion': can_complete,
            'can_confirm_completion': has_pending_completion,
        })
        return Response(serializer.data)


class ContractActivateView(GenericAPIView):
    """Activate contract execution."""
    permission_classes = [IsAuthenticated]

    def post(self, request, contract_id):
        contract = _get_contract(contract_id, request.user)
        # Only client can activate
        if not (hasattr(request.user, 'client_profile') and contract.client.user == request.user):
            raise PermissionDenied("Only the client can activate execution.")
        eligible, reason = check_execution_eligibility(contract, request.user)
        if not eligible:
            raise ValidationError(reason)
        contract = activate_contract(contract, request.user)
        return Response({'status': 'active', 'activated_at': contract.activated_at})


# ──────────────────────────────────────────────
#  Milestones
# ──────────────────────────────────────────────


class MilestoneListCreateView(ListModelMixin, CreateModelMixin, GenericAPIView):
    """List or create milestones for a contract."""
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ExecutionMilestoneCreateSerializer
        return ExecutionMilestoneListSerializer

    def get_queryset(self):
        contract_id = self.kwargs.get('contract_id')
        contract = _get_contract(contract_id, self.request.user)
        return contract.execution_milestones.all().order_by('sequence')

    def perform_create(self, serializer):
        contract_id = self.kwargs.get('contract_id')
        contract = _get_contract(contract_id, self.request.user)
        # Only client can create milestones
        if not (hasattr(self.request.user, 'client_profile') and contract.client.user == self.request.user):
            raise PermissionDenied("Only the client can create milestones.")
        if contract.status not in ('in_progress', 'active', 'draft'):
            raise ValidationError("Cannot create milestones for this contract status.")
        create_milestone(contract, serializer.validated_data, self.request.user)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class MilestoneDetailView(GenericAPIView):
    """Retrieve or update a milestone."""
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return ExecutionMilestoneUpdateSerializer
        return ExecutionMilestoneDetailSerializer

    def get_object(self):
        return _get_milestone(self.kwargs.get('milestone_id'), self.request.user)

    def get(self, request, milestone_id, contract_id=None):
        milestone = self.get_object()
        serializer = ExecutionMilestoneDetailSerializer(milestone)
        return Response(serializer.data)

    def patch(self, request, milestone_id, contract_id=None):
        milestone = self.get_object()
        # Only client can update draft milestones
        if not (hasattr(request.user, 'client_profile') and milestone.contract.client.user == request.user):
            raise PermissionDenied("Only the client can update milestones.")
        if milestone.status != ExecutionMilestone.Status.DRAFT:
            raise ValidationError("Only draft milestones can be updated.")
        serializer = ExecutionMilestoneUpdateSerializer(milestone, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(milestone, field, value)
        milestone.save()
        return Response(ExecutionMilestoneDetailSerializer(milestone).data)


class MilestoneReorderView(GenericAPIView):
    """Reorder milestones."""
    permission_classes = [IsAuthenticated]

    def post(self, request, contract_id):
        contract = _get_contract(contract_id, request.user)
        if not (hasattr(request.user, 'client_profile') and contract.client.user == request.user):
            raise PermissionDenied("Only the client can reorder milestones.")
        serializer = ExecutionMilestoneReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reorder_milestones(contract, serializer.validated_data['sequence'])
        qs = contract.execution_milestones.all().order_by('sequence')
        return Response(ExecutionMilestoneListSerializer(qs, many=True).data)


class MilestoneStartView(GenericAPIView):
    """Technician starts work on a milestone."""
    permission_classes = [IsAuthenticated]

    def post(self, request, milestone_id, contract_id=None):
        milestone = _get_milestone(milestone_id, request.user)
        if not (hasattr(request.user, 'technician_profile') and milestone.contract.technician.user == request.user):
            raise PermissionDenied("Only the assigned technician can start milestones.")
        start_milestone(milestone, request.user)
        return Response(ExecutionMilestoneDetailSerializer(milestone).data)


# ──────────────────────────────────────────────
#  Deliverables
# ──────────────────────────────────────────────


class DeliverableSubmitView(GenericAPIView):
    """Technician submits a deliverable."""
    permission_classes = [IsAuthenticated]

    def post(self, request, milestone_id, contract_id=None):
        milestone = _get_milestone(milestone_id, request.user)
        if not (hasattr(request.user, 'technician_profile') and milestone.contract.technician.user == request.user):
            raise PermissionDenied("Only the assigned technician can submit deliverables.")
        serializer = DeliverableCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            submission = submit_deliverable(milestone, serializer.validated_data, request.user)
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(DeliverableSubmissionSerializer(submission).data,
                        status=status.HTTP_201_CREATED)


class SubmissionListView(GenericAPIView):
    """List submissions for a milestone."""
    permission_classes = [IsAuthenticated]

    def get(self, request, milestone_id, contract_id=None):
        milestone = _get_milestone(milestone_id, request.user)
        qs = milestone.submissions.all().order_by('-version')
        serializer = DeliverableSubmissionSerializer(qs, many=True)
        return Response(serializer.data)


# ──────────────────────────────────────────────
#  Revisions
# ──────────────────────────────────────────────


class RevisionRequestView(GenericAPIView):
    """Client requests revision on a submission."""
    permission_classes = [IsAuthenticated]

    def post(self, request, milestone_id, contract_id=None):
        milestone = _get_milestone(milestone_id, request.user)
        if not (hasattr(request.user, 'client_profile') and milestone.contract.client.user == request.user):
            raise PermissionDenied("Only the client can request revisions.")
        serializer = RevisionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Get latest submission
        submission = milestone.submissions.order_by('-version').first()
        if not submission:
            raise ValidationError("No submission to revise.")
        try:
            revision = request_revision(milestone, submission, serializer.validated_data, request.user)
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(RevisionRequestSerializer(revision).data,
                        status=status.HTTP_201_CREATED)


# ──────────────────────────────────────────────
#  Approval
# ──────────────────────────────────────────────


class MilestoneApproveView(GenericAPIView):
    """Client approves a milestone."""
    permission_classes = [IsAuthenticated]

    def post(self, request, milestone_id, contract_id=None):
        milestone = _get_milestone(milestone_id, request.user)
        if not (hasattr(request.user, 'client_profile') and milestone.contract.client.user == request.user):
            raise PermissionDenied("Only the client can approve milestones.")
        try:
            approve_milestone(milestone, request.user)
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(ExecutionMilestoneDetailSerializer(milestone).data)


# ──────────────────────────────────────────────
#  Completion
# ──────────────────────────────────────────────


class CompletionRequestView(GenericAPIView):
    """Technician requests contract completion."""
    permission_classes = [IsAuthenticated]

    def post(self, request, contract_id):
        contract = _get_contract(contract_id, request.user)
        if not (hasattr(request.user, 'technician_profile') and contract.technician.user == request.user):
            raise PermissionDenied("Only the assigned technician can request completion.")
        serializer = CompletionRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            request_completion(contract, serializer.validated_data, request.user)
        except ValueError as e:
            raise ValidationError(str(e))
        return Response({'status': 'completion_requested'})


class CompletionRejectView(GenericAPIView):
    """Client rejects completion request."""
    permission_classes = [IsAuthenticated]

    def post(self, request, contract_id):
        contract = _get_contract(contract_id, request.user)
        if not (hasattr(request.user, 'client_profile') and contract.client.user == request.user):
            raise PermissionDenied("Only the client can reject completion.")
        serializer = CompletionRespondSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pending = contract.completion_requests.filter(
            status=CompletionRequest.Status.PENDING
        ).first()
        if not pending:
            raise ValidationError("No pending completion request.")
        reject_completion(contract, pending, serializer.validated_data, request.user)
        return Response({'status': 'active'})


class CompletionConfirmView(GenericAPIView):
    """Client confirms contract completion."""
    permission_classes = [IsAuthenticated]

    def post(self, request, contract_id):
        contract = _get_contract(contract_id, request.user)
        if not (hasattr(request.user, 'client_profile') and contract.client.user == request.user):
            raise PermissionDenied("Only the client can confirm completion.")
        pending = contract.completion_requests.filter(
            status=CompletionRequest.Status.PENDING
        ).first()
        if not pending:
            raise ValidationError("No pending completion request.")
        confirm_completion(contract, pending, request.user)
        return Response({
            'status': 'completed',
            'escrow_held': str(contract.escrow_amount),
            'total_paid': str(contract.total_paid),
        })


# ──────────────────────────────────────────────
#  History
# ──────────────────────────────────────────────


class ExecutionHistoryView(GenericAPIView):
    """Get execution history for a contract."""
    permission_classes = [IsAuthenticated]

    def get(self, request, contract_id):
        contract = _get_contract(contract_id, request.user)
        events = get_execution_history(contract)
        serializer = ExecutionHistorySerializer(events, many=True)
        return Response(serializer.data)
