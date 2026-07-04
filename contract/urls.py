"""URL routing for contract endpoints."""

from django.urls import path
from .views import (
    ContractListCreateView,
    ContractDetailView,
    ContractAcceptView,
    ContractCancelView,
    ContractStageListView,
    ContractStageDetailView,
    ContractStageSubmitView,
    ContractStageApproveView,
    ContractExtensionListView,
    ContractExtensionCreateView,
    ContractExtensionRespondView,
    ContractFreezeView,
    ContractRequestSignatureOtpView,
    ContractSignView,
    ContractSignaturesView,
    ContractFinalizeView,
    ContractDocumentsView,
    ContractFinalDocumentView,
    PublicVerifyCodeView,
    PublicVerifyPdfView,
)

# ──────────────────────────────────────────────
#  Phase 8 — Contract Execution
# ──────────────────────────────────────────────

from .execution_views import (
    ContractExecutionEligibilityView,
    ContractActivateView,
    MilestoneListCreateView,
    MilestoneDetailView,
    MilestoneReorderView,
    MilestoneStartView,
    DeliverableSubmitView,
    SubmissionListView,
    RevisionRequestView,
    MilestoneApproveView,
    CompletionRequestView,
    CompletionRejectView,
    CompletionConfirmView,
    ExecutionHistoryView,
)
from ratereview.views import ContractReviewEligibilityView, ContractReviewCreateView

execution_urlpatterns = [
    # Eligibility & Activation
    path("<uuid:contract_id>/execution/eligibility/",
         ContractExecutionEligibilityView.as_view(),
         name="contract-execution-eligibility"),
    path("<uuid:contract_id>/activate/",
         ContractActivateView.as_view(),
         name="contract-activate"),
    # Milestones
    path("<uuid:contract_id>/milestones/",
         MilestoneListCreateView.as_view(),
         name="milestone-list"),
    path("<uuid:contract_id>/milestones/reorder/",
         MilestoneReorderView.as_view(),
         name="milestone-reorder"),
    path("milestones/<uuid:milestone_id>/",
         MilestoneDetailView.as_view(),
         name="milestone-detail"),
    path("milestones/<uuid:milestone_id>/start/",
         MilestoneStartView.as_view(),
         name="milestone-start"),
    # Deliverables
    path("milestones/<uuid:milestone_id>/submissions/",
         SubmissionListView.as_view(),
         name="submission-list"),
    path("milestones/<uuid:milestone_id>/submit/",
         DeliverableSubmitView.as_view(),
         name="deliverable-submit"),
    # Revisions & Approval
    path("milestones/<uuid:milestone_id>/revision/",
         RevisionRequestView.as_view(),
         name="milestone-revision"),
    path("milestones/<uuid:milestone_id>/approve/",
         MilestoneApproveView.as_view(),
         name="milestone-approve"),
    # Completion
    path("<uuid:contract_id>/completion-request/",
         CompletionRequestView.as_view(),
         name="completion-request"),
    path("<uuid:contract_id>/completion-reject/",
         CompletionRejectView.as_view(),
         name="completion-reject"),
    path("<uuid:contract_id>/complete/",
         CompletionConfirmView.as_view(),
         name="completion-confirm"),
    # Reviews
    path("<uuid:contract_id>/review-eligibility/",
         ContractReviewEligibilityView.as_view(),
         name="contract-review-eligibility"),
    path("<uuid:contract_id>/reviews/",
         ContractReviewCreateView.as_view(),
         name="contract-review-create"),
    # History
    path("<uuid:contract_id>/execution-history/",
         ExecutionHistoryView.as_view(),
         name="execution-history"),
]

urlpatterns = [
    # --- Contract CRUD & Actions ---
    path("", ContractListCreateView.as_view(), name="contract-list"),
    path("<uuid:contract_id>/", ContractDetailView.as_view(), name="contract-detail"),
    path("<uuid:contract_id>/accept/", ContractAcceptView.as_view(), name="contract-accept"),
    path("<uuid:contract_id>/cancel/", ContractCancelView.as_view(), name="contract-cancel"),
    # --- Stages ---
    path("<uuid:contract_id>/stages/", ContractStageListView.as_view(), name="contract-stage-list"),
    path("<uuid:contract_id>/stages/<uuid:stage_id>/", ContractStageDetailView.as_view(), name="contract-stage-detail"),
    path("<uuid:contract_id>/stages/<uuid:stage_id>/submit/", ContractStageSubmitView.as_view(), name="contract-stage-submit"),
    path("<uuid:contract_id>/stages/<uuid:stage_id>/approve/", ContractStageApproveView.as_view(), name="contract-stage-approve"),
    # --- Extension Requests ---
    path("<uuid:contract_id>/extension-requests/", ContractExtensionListView.as_view(), name="contract-extension-list"),
    path("<uuid:contract_id>/extension-requests/create/", ContractExtensionCreateView.as_view(), name="contract-extension-create"),
    path("<uuid:contract_id>/extension-requests/<uuid:request_id>/approve/", ContractExtensionRespondView.as_view(), name="contract-extension-approve"),
    path("<uuid:contract_id>/extension-requests/<uuid:request_id>/reject/", ContractExtensionRespondView.as_view(), name="contract-extension-reject"),

    # --- Phase 19: Signatures & Finalization ---
    path("<uuid:contract_id>/freeze/", ContractFreezeView.as_view(), name="contract-freeze"),
    path("<uuid:contract_id>/request-signature-otp/", ContractRequestSignatureOtpView.as_view(), name="contract-request-signature-otp"),
    path("<uuid:contract_id>/sign/", ContractSignView.as_view(), name="contract-sign"),
    path("<uuid:contract_id>/signatures/", ContractSignaturesView.as_view(), name="contract-signatures"),
    path("<uuid:contract_id>/finalize/", ContractFinalizeView.as_view(), name="contract-finalize"),
    path("<uuid:contract_id>/documents/", ContractDocumentsView.as_view(), name="contract-documents"),
    path("<uuid:contract_id>/documents/final/", ContractFinalDocumentView.as_view(), name="contract-final-document"),

    # --- Public Verification ---
    path("verify/<str:verification_code>/", PublicVerifyCodeView.as_view(), name="contract-public-verify-code"),
    path("verify-pdf/", PublicVerifyPdfView.as_view(), name="contract-public-verify-pdf"),

    # --- Phase 8: Execution ---
    *execution_urlpatterns,
]

# ──────────────────────────────────────────────
#  Offer endpoints (Phase 6)
# ──────────────────────────────────────────────

from .offer_views import (
    ClientOfferListView,
    ClientOfferDetailView,
    ClientOfferAcceptView,
    ClientOfferRejectView,
    OfferByRequestView,
)

offer_urlpatterns = [
    # Client-facing offers
    path("", ClientOfferListView.as_view(), name="client-offer-list"),
    path("<uuid:offer_id>/", ClientOfferDetailView.as_view(), name="client-offer-detail"),
    path("<uuid:offer_id>/accept/", ClientOfferAcceptView.as_view(), name="client-offer-accept"),
    path("<uuid:offer_id>/reject/", ClientOfferRejectView.as_view(), name="client-offer-reject"),
    # By-request lookup
    path("by-request/<uuid:request_id>/", OfferByRequestView.as_view(), name="offer-by-request"),
]

from .offer_views import (
    TechnicianOfferListCreateView,
    TechnicianOfferDetailView,
    TechnicianOfferSubmitView,
    TechnicianOfferWithdrawView,
)

technician_offer_urlpatterns = [
    path("", TechnicianOfferListCreateView.as_view(), name="technician-offer-list"),
    path("<uuid:offer_id>/", TechnicianOfferDetailView.as_view(), name="technician-offer-detail"),
    path("<uuid:offer_id>/submit/", TechnicianOfferSubmitView.as_view(), name="technician-offer-submit"),
    path("<uuid:offer_id>/withdraw/", TechnicianOfferWithdrawView.as_view(), name="technician-offer-withdraw"),
]
