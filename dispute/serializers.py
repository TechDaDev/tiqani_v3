"""Phase 10 — Dispute, refund, and chargeback serializers."""

from decimal import Decimal

from rest_framework import serializers

from .models import (
    ContractDispute,
    DisputeStatement,
    DisputeEvidence,
    DisputeResolution,
    DisputeAuditEvent,
    RefundRecord,
    ChargebackEvent,
    UserFinancialLiability,
    DisputeStatus,
    DisputeReason,
    EvidenceType,
    ResolutionType,
    RefundSourceType,
)


# ──────────────────────────────────────────────
#  Participant serializers
# ──────────────────────────────────────────────


class DisputeListSerializer(serializers.ModelSerializer):
    """Compact dispute list view (no private financial details)."""

    contract_reference = serializers.CharField(source="contract.contract_reference", read_only=True)
    reason_display = serializers.CharField(source="get_reason_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    opened_by_name = serializers.SerializerMethodField()
    respondent_name = serializers.SerializerMethodField()
    assigned_staff_name = serializers.SerializerMethodField()

    class Meta:
        model = ContractDispute
        fields = [
            "id", "contract", "contract_reference",
            "opened_by", "opened_by_name",
            "respondent", "respondent_name",
            "reason", "reason_display",
            "category", "category_display",
            "claimed_amount", "currency",
            "status", "status_display",
            "assigned_staff", "assigned_staff_name",
            "opened_at", "response_due_at",
            "review_started_at", "resolved_at",
            "closed_at", "resolution_summary",
        ]
        read_only_fields = fields

    def get_opened_by_name(self, obj):
        return obj.opened_by.username if obj.opened_by else ""

    def get_respondent_name(self, obj):
        return obj.respondent.username if obj.respondent else ""

    def get_assigned_staff_name(self, obj):
        return obj.assigned_staff.username if obj.assigned_staff else None


class DisputeDetailSerializer(serializers.ModelSerializer):
    """Full dispute detail with related data."""

    contract_reference = serializers.CharField(source="contract.contract_reference", read_only=True)
    reason_display = serializers.CharField(source="get_reason_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    statements = serializers.SerializerMethodField()
    evidence_items = serializers.SerializerMethodField()
    resolution = serializers.SerializerMethodField()
    audit_events = serializers.SerializerMethodField()

    class Meta:
        model = ContractDispute
        fields = [
            "id", "contract", "contract_reference",
            "opened_by", "respondent",
            "reason", "reason_display",
            "category", "category_display",
            "claimed_amount", "currency",
            "status", "status_display",
            "assigned_staff",
            "opened_at", "response_due_at",
            "review_started_at", "resolved_at", "closed_at",
            "resolution_summary",
            "statements", "evidence_items",
            "resolution", "audit_events",
        ]
        read_only_fields = fields

    def get_statements(self, obj):
        qs = obj.statements.all()
        return DisputeStatementSerializer(qs, many=True).data

    def get_evidence_items(self, obj):
        qs = obj.evidence_items.all()
        return DisputeEvidenceSerializer(qs, many=True).data

    def get_resolution(self, obj):
        if hasattr(obj, "resolution") and obj.resolution:
            return DisputeResolutionSerializer(obj.resolution).data
        return None

    def get_audit_events(self, obj):
        qs = obj.audit_events.all()[:50]
        return DisputeAuditEventSerializer(qs, many=True).data


class DisputeCreateSerializer(serializers.Serializer):
    """Opening a new dispute."""

    reason = serializers.ChoiceField(choices=DisputeReason.choices)
    statement = serializers.CharField(min_length=20, max_length=5000)
    claimed_amount = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=Decimal("0.01"))
    idempotency_key = serializers.CharField(max_length=64, required=False, allow_null=True)


class DisputeStatementSerializer(serializers.ModelSerializer):
    """Statement view serializer."""

    submitted_by_name = serializers.CharField(source="submitted_by.username", read_only=True)

    class Meta:
        model = DisputeStatement
        fields = ["id", "dispute", "submitted_by", "submitted_by_name", "statement", "created_at"]
        read_only_fields = ["id", "dispute", "submitted_by", "created_at"]


class DisputeStatementCreateSerializer(serializers.Serializer):
    """Submit a statement."""

    statement = serializers.CharField(min_length=10, max_length=5000)


class DisputeEvidenceSerializer(serializers.ModelSerializer):
    """Evidence view serializer (safe fields only)."""

    submitted_by_name = serializers.CharField(source="submitted_by.username", read_only=True)

    class Meta:
        model = DisputeEvidence
        fields = [
            "id", "dispute", "submitted_by", "submitted_by_name",
            "evidence_type", "description", "file", "mime_type",
            "file_size", "created_at",
        ]
        read_only_fields = ["id", "dispute", "submitted_by", "created_at"]


class DisputeEvidenceCreateSerializer(serializers.Serializer):
    """Submit evidence."""

    evidence_type = serializers.ChoiceField(choices=EvidenceType.choices)
    description = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    mime_type = serializers.CharField(max_length=100, required=False, allow_blank=True)
    file_size = serializers.IntegerField(min_value=0, required=False, default=0)
    integrity_hash = serializers.CharField(max_length=64, required=False, allow_blank=True)


class DisputeResolutionSerializer(serializers.ModelSerializer):
    """Resolution view serializer."""

    resolved_by_name = serializers.CharField(source="resolved_by.username", read_only=True)
    resolution_type_display = serializers.CharField(source="get_resolution_type_display", read_only=True)

    class Meta:
        model = DisputeResolution
        fields = "__all__"
        read_only_fields = [
            "id", "dispute", "resolved_by", "resolved_at",
        ]


class DisputeAuditEventSerializer(serializers.ModelSerializer):
    """Audit event view serializer."""

    actor_name = serializers.CharField(source="actor.username", read_only=True, allow_null=True)

    class Meta:
        model = DisputeAuditEvent
        fields = ["id", "dispute", "event_type", "actor", "actor_name", "payload", "created_at"]
        read_only_fields = fields


# ──────────────────────────────────────────────
#  Staff serializers
# ──────────────────────────────────────────────


class AdminDisputeResolveSerializer(serializers.Serializer):
    """Staff resolves a dispute with financial execution."""

    resolution_type = serializers.ChoiceField(choices=ResolutionType.choices)
    client_refund_amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"),
    )
    technician_retained_amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"),
    )
    platform_fee_reversal_amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"),
    )
    escrow_released_amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"),
    )
    wallet_reversal_amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"),
    )
    unrecoverable_amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"),
    )
    outstanding_liability_amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"),
    )
    resolution_reason = serializers.CharField(max_length=5000)
    idempotency_key = serializers.CharField(max_length=64, required=False, allow_null=True)


class AdminDisputeAssignSerializer(serializers.Serializer):
    """Assign staff to dispute."""

    staff_id = serializers.UUIDField()


class AdminDisputeRejectSerializer(serializers.Serializer):
    """Reject a dispute."""

    reason = serializers.CharField(max_length=5000, required=False, allow_blank=True)


class AdminDisputeResolutionProposeSerializer(serializers.Serializer):
    """Propose resolution without executing finances."""

    resolution_type = serializers.ChoiceField(choices=ResolutionType.choices)
    client_refund_amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"),
    )
    resolution_reason = serializers.CharField(max_length=5000, required=False, allow_blank=True)


# ──────────────────────────────────────────────
#  Refund serializers
# ──────────────────────────────────────────────


class RefundRecordSerializer(serializers.ModelSerializer):
    """Refund record view serializer."""

    source_type_display = serializers.CharField(source="get_source_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = RefundRecord
        fields = [
            "id", "dispute", "contract", "client",
            "amount", "currency", "source_type", "source_type_display",
            "status", "status_display",
            "refund_method", "provider_reference",
            "wallet_transaction",
            "created_by",
            "initiated_at", "completed_at", "failed_at",
            "failure_code", "failure_message",
        ]
        read_only_fields = fields


class AdminRefundCreateSerializer(serializers.Serializer):
    """Staff-initiated refund."""

    amount = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=Decimal("0.01"))
    source_type = serializers.ChoiceField(choices=RefundSourceType.choices)
    idempotency_key = serializers.CharField(max_length=64, required=False, allow_null=True)


# ──────────────────────────────────────────────
#  Chargeback serializers
# ──────────────────────────────────────────────


class ChargebackEventSerializer(serializers.ModelSerializer):
    """Chargeback view serializer."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    contract_reference = serializers.CharField(source="contract.contract_reference", read_only=True)

    class Meta:
        model = ChargebackEvent
        fields = [
            "id", "contract", "contract_reference",
            "dispute", "provider_reference",
            "amount", "reason_code",
            "received_at", "evidence_deadline",
            "status", "status_display",
            "outcome", "resolved_by", "resolved_at",
        ]
        read_only_fields = fields


class ChargebackSandboxCreateSerializer(serializers.Serializer):
    """Create a sandbox chargeback."""

    contract_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=Decimal("0.01"))
    reason_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    idempotency_key = serializers.CharField(max_length=64, required=False, allow_null=True)


class ChargebackSandboxActionSerializer(serializers.Serializer):
    """Sandbox chargeback action (uphold/reject/partial)."""

    idempotency_key = serializers.CharField(max_length=64, required=False, allow_null=True)


class ChargebackSandboxPartialSerializer(serializers.Serializer):
    """Sandbox partial chargeback."""

    partial_amount = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=Decimal("0.01"))
    idempotency_key = serializers.CharField(max_length=64, required=False, allow_null=True)


# ──────────────────────────────────────────────
#  Liability serializer
# ──────────────────────────────────────────────


class UserFinancialLiabilitySerializer(serializers.ModelSerializer):
    """Liability view serializer."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = UserFinancialLiability
        fields = [
            "id", "user", "source_dispute",
            "original_amount", "recovered_amount", "remaining_amount",
            "status", "status_display",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


# ──────────────────────────────────────────────
#  Eligibility serializer
# ──────────────────────────────────────────────


class DisputeEligibilitySerializer(serializers.Serializer):
    """Dispute eligibility check result."""

    eligible = serializers.BooleanField()
    reason = serializers.CharField(allow_blank=True)
