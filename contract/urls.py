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
)

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
]
