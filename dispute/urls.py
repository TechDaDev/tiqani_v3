"""Phase 10 — Dispute, refund, and chargeback URL routing."""

from django.urls import path

from .views import (
    # Participant
    DisputeListView,
    DisputeCreateView,
    DisputeDetailView,
    DisputeStatementCreateView,
    DisputeEvidenceCreateView,
    DisputeCancelView,
    ContractDisputeEligibilityView,
    ContractActiveDisputeView,
    # Admin disputes
    AdminDisputeListView,
    AdminDisputeDetailView,
    AdminDisputeAssignView,
    AdminDisputeStartReviewView,
    AdminDisputeStartMediationView,
    AdminDisputeProposeResolutionView,
    AdminDisputeResolveView,
    AdminDisputeRejectView,
    AdminDisputeCloseView,
    AdminDisputeReconciliationView,
    # Refunds
    DisputeRefundListView,
    AdminDisputeRefundCreateView,
    AdminRefundListView,
    RefundDetailView,
    AdminRefundSandboxConfirmView,
    AdminRefundRetryView,
    # Chargebacks
    AdminChargebackListView,
    AdminChargebackSandboxCreateView,
    AdminChargebackDetailView,
    AdminChargebackStartReviewView,
    AdminChargebackSubmitEvidenceView,
    AdminChargebackSandboxUpholdView,
    AdminChargebackSandboxRejectView,
    AdminChargebackSandboxPartialView,
)

urlpatterns = [
    # ── Participant endpoints ────────────────────────
    path("disputes/", DisputeListView.as_view(), name="dispute-list"),
    path("disputes/create/", DisputeCreateView.as_view(), name="dispute-create"),
    path("disputes/<uuid:dispute_id>/", DisputeDetailView.as_view(), name="dispute-detail"),
    path("disputes/<uuid:dispute_id>/statements/", DisputeStatementCreateView.as_view(), name="dispute-statement-create"),
    path("disputes/<uuid:dispute_id>/evidence/", DisputeEvidenceCreateView.as_view(), name="dispute-evidence-create"),
    path("disputes/<uuid:dispute_id>/cancel/", DisputeCancelView.as_view(), name="dispute-cancel"),
    path("disputes/<uuid:dispute_id>/refunds/", DisputeRefundListView.as_view(), name="dispute-refund-list"),

    # ── Contract dispute eligibility ─────────────────
    path("contracts/<uuid:contract_id>/dispute-eligibility/",
         ContractDisputeEligibilityView.as_view(), name="contract-dispute-eligibility"),
    path("contracts/<uuid:contract_id>/active-dispute/",
         ContractActiveDisputeView.as_view(), name="contract-active-dispute"),

    # ── Refund details ───────────────────────────────
    path("refunds/<uuid:refund_id>/", RefundDetailView.as_view(), name="refund-detail"),

    # ── Admin dispute management ─────────────────────
    path("admin/disputes/", AdminDisputeListView.as_view(), name="admin-dispute-list"),
    path("admin/disputes/<uuid:dispute_id>/", AdminDisputeDetailView.as_view(), name="admin-dispute-detail"),
    path("admin/disputes/<uuid:dispute_id>/assign/", AdminDisputeAssignView.as_view(), name="admin-dispute-assign"),
    path("admin/disputes/<uuid:dispute_id>/start-review/", AdminDisputeStartReviewView.as_view(), name="admin-dispute-start-review"),
    path("admin/disputes/<uuid:dispute_id>/start-mediation/", AdminDisputeStartMediationView.as_view(), name="admin-dispute-start-mediation"),
    path("admin/disputes/<uuid:dispute_id>/propose-resolution/", AdminDisputeProposeResolutionView.as_view(), name="admin-dispute-propose-resolution"),
    path("admin/disputes/<uuid:dispute_id>/resolve/", AdminDisputeResolveView.as_view(), name="admin-dispute-resolve"),
    path("admin/disputes/<uuid:dispute_id>/reject/", AdminDisputeRejectView.as_view(), name="admin-dispute-reject"),
    path("admin/disputes/<uuid:dispute_id>/close/", AdminDisputeCloseView.as_view(), name="admin-dispute-close"),
    path("admin/disputes/<uuid:dispute_id>/reconciliation/", AdminDisputeReconciliationView.as_view(), name="admin-dispute-reconciliation"),

    # ── Admin refund operations ──────────────────────
    path("admin/refunds/", AdminRefundListView.as_view(), name="admin-refund-list"),
    path("admin/disputes/<uuid:dispute_id>/refunds/", AdminDisputeRefundCreateView.as_view(), name="admin-dispute-refund-create"),
    path("admin/refunds/<uuid:refund_id>/sandbox-confirm/", AdminRefundSandboxConfirmView.as_view(), name="admin-refund-sandbox-confirm"),
    path("admin/refunds/<uuid:refund_id>/retry/", AdminRefundRetryView.as_view(), name="admin-refund-retry"),

    # ── Admin chargeback management ──────────────────
    path("admin/chargebacks/", AdminChargebackListView.as_view(), name="admin-chargeback-list"),
    path("admin/chargebacks/sandbox-create/", AdminChargebackSandboxCreateView.as_view(), name="admin-chargeback-sandbox-create"),
    path("admin/chargebacks/<uuid:chargeback_id>/", AdminChargebackDetailView.as_view(), name="admin-chargeback-detail"),
    path("admin/chargebacks/<uuid:chargeback_id>/start-review/", AdminChargebackStartReviewView.as_view(), name="admin-chargeback-start-review"),
    path("admin/chargebacks/<uuid:chargeback_id>/submit-evidence/", AdminChargebackSubmitEvidenceView.as_view(), name="admin-chargeback-submit-evidence"),
    path("admin/chargebacks/<uuid:chargeback_id>/sandbox-uphold/", AdminChargebackSandboxUpholdView.as_view(), name="admin-chargeback-sandbox-uphold"),
    path("admin/chargebacks/<uuid:chargeback_id>/sandbox-reject/", AdminChargebackSandboxRejectView.as_view(), name="admin-chargeback-sandbox-reject"),
    path("admin/chargebacks/<uuid:chargeback_id>/sandbox-partial/", AdminChargebackSandboxPartialView.as_view(), name="admin-chargeback-sandbox-partial"),
]
