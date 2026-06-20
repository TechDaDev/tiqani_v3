"""Serializers for Phase 8 contract execution and milestone workflow."""

from rest_framework import serializers
from django.utils import timezone

from .models import (
    Contract,
    ExecutionMilestone,
    DeliverableSubmission,
    RevisionRequest,
    CompletionRequest,
    ContractAuditEvent,
)


class ExecutionMilestoneListSerializer(serializers.ModelSerializer):
    """List view for milestones (no sensitive fields)."""

    class Meta:
        model = ExecutionMilestone
        fields = (
            'id', 'contract', 'sequence', 'title', 'description',
            'due_date', 'status', 'created_at', 'updated_at',
            'started_at', 'submitted_at', 'approved_at', 'revision_count',
        )
        read_only_fields = (
            'id', 'contract', 'status', 'created_at', 'updated_at',
            'started_at', 'submitted_at', 'approved_at', 'revision_count',
        )


class ExecutionMilestoneCreateSerializer(serializers.ModelSerializer):
    """Create a draft milestone."""

    sequence = serializers.IntegerField(required=False)

    class Meta:
        model = ExecutionMilestone
        fields = ('title', 'description', 'due_date', 'sequence')

    def validate_due_date(self, value):
        if value and value < timezone.now().date():
            raise serializers.ValidationError("Due date cannot be in the past.")
        return value

    def validate_sequence(self, value):
        if value < 1:
            raise serializers.ValidationError("Sequence must be at least 1.")
        return value


class ExecutionMilestoneUpdateSerializer(serializers.ModelSerializer):
    """Update a draft milestone (title, description, due_date only)."""

    class Meta:
        model = ExecutionMilestone
        fields = ('title', 'description', 'due_date')

    def validate_due_date(self, value):
        if value and value < timezone.now().date():
            raise serializers.ValidationError("Due date cannot be in the past.")
        return value


class ExecutionMilestoneReorderSerializer(serializers.Serializer):
    """Reorder milestones for a contract."""
    sequence = serializers.ListField(
        child=serializers.UUIDField(),
        help_text="Ordered list of milestone IDs"
    )

    def validate_sequence(self, value):
        if not value:
            raise serializers.ValidationError("Sequence list cannot be empty.")
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Duplicate milestone IDs in sequence.")
        return value


class ExecutionMilestoneDetailSerializer(serializers.ModelSerializer):
    """Full milestone detail with submissions and revisions."""

    submissions = serializers.SerializerMethodField()
    revisions = serializers.SerializerMethodField()

    class Meta:
        model = ExecutionMilestone
        fields = (
            'id', 'contract', 'sequence', 'title', 'description',
            'due_date', 'status', 'created_by', 'started_at',
            'submitted_at', 'approved_at', 'revision_count',
            'created_at', 'updated_at', 'submissions', 'revisions',
        )
        read_only_fields = (
            'id', 'contract', 'status', 'created_by',
            'started_at', 'submitted_at', 'approved_at',
            'revision_count', 'created_at', 'updated_at',
        )

    def get_submissions(self, obj):
        qs = obj.submissions.all()
        return DeliverableSubmissionSerializer(qs, many=True).data

    def get_revisions(self, obj):
        qs = obj.revisions.all()
        return RevisionRequestSerializer(qs, many=True).data


class DeliverableSubmissionSerializer(serializers.ModelSerializer):
    """Deliverable submission data."""

    submitted_by_name = serializers.SerializerMethodField()

    class Meta:
        model = DeliverableSubmission
        fields = (
            'id', 'milestone', 'submitted_by', 'submitted_by_name',
            'version', 'summary', 'notes', 'external_link',
            'submitted_at', 'created_at',
        )
        read_only_fields = (
            'id', 'milestone', 'submitted_by', 'version',
            'submitted_at', 'created_at',
        )

    def get_submitted_by_name(self, obj):
        return obj.submitted_by.get_full_name() or obj.submitted_by.username


class DeliverableCreateSerializer(serializers.Serializer):
    """Technician submits a deliverable for a milestone."""
    summary = serializers.CharField(max_length=5000)
    notes = serializers.CharField(max_length=10000, required=False, allow_blank=True)
    external_link = serializers.URLField(required=False, allow_blank=True, max_length=2000)

    def validate_summary(self, value):
        if not value.strip():
            raise serializers.ValidationError("Summary cannot be empty.")
        return value


class RevisionRequestSerializer(serializers.ModelSerializer):
    """Revision request data."""

    requested_by_name = serializers.SerializerMethodField()

    class Meta:
        model = RevisionRequest
        fields = (
            'id', 'milestone', 'submission', 'requested_by',
            'requested_by_name', 'reason', 'status',
            'revision_number', 'created_at', 'resolved_at',
        )
        read_only_fields = (
            'id', 'milestone', 'submission', 'requested_by',
            'status', 'revision_number', 'created_at', 'resolved_at',
        )

    def get_requested_by_name(self, obj):
        return obj.requested_by.get_full_name() or obj.requested_by.username


class RevisionCreateSerializer(serializers.Serializer):
    """Client requests revision on a submission."""
    reason = serializers.CharField(max_length=5000)

    def validate_reason(self, value):
        if not value.strip():
            raise serializers.ValidationError("Reason cannot be empty.")
        return value


class CompletionRequestSerializer(serializers.ModelSerializer):
    """Completion request data."""

    requested_by_name = serializers.SerializerMethodField()

    class Meta:
        model = CompletionRequest
        fields = (
            'id', 'contract', 'requested_by', 'requested_by_name',
            'completion_message', 'status', 'response_message',
            'responded_at', 'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'contract', 'requested_by', 'status',
            'responded_at', 'created_at', 'updated_at',
        )

    def get_requested_by_name(self, obj):
        return obj.requested_by.get_full_name() or obj.requested_by.username


class CompletionRequestCreateSerializer(serializers.Serializer):
    """Technician requests completion."""
    completion_message = serializers.CharField(
        max_length=5000, required=False, allow_blank=True
    )


class CompletionRespondSerializer(serializers.Serializer):
    """Client responds to completion request."""
    confirm = serializers.BooleanField(default=True)
    response_message = serializers.CharField(
        max_length=5000, required=False, allow_blank=True
    )


class ExecutionHistorySerializer(serializers.ModelSerializer):
    """Audit event for execution history."""

    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = ContractAuditEvent
        fields = (
            'id', 'contract', 'event_type', 'actor',
            'actor_name', 'payload', 'created_at',
        )
        read_only_fields = fields

    def get_actor_name(self, obj):
        if obj.actor:
            return obj.actor.get_full_name() or obj.actor.username
        return None


class ContractExecutionEligibilitySerializer(serializers.Serializer):
    """Execution eligibility check."""

    eligible = serializers.BooleanField()
    reason = serializers.CharField(required=False, allow_blank=True)
    contract_status = serializers.CharField()
    funding_status = serializers.CharField(required=False, allow_blank=True)
    milestone_count = serializers.IntegerField(default=0)
    can_activate = serializers.BooleanField(default=False)
    can_request_completion = serializers.BooleanField(default=False)
    can_confirm_completion = serializers.BooleanField(default=False)
