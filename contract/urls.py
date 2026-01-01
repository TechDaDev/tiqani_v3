"""URL routing for contract endpoints."""

from django.urls import path
from .views import (
    ContractListCreateView,
    ContractDetailView,
    ContractStageListView,
    ContractStageDetailView,
    TimeExtensionRequestListCreateView,
    TimeExtensionRequestRespondView,
    TimeExtensionDistributeView,
)

urlpatterns = [
    # --- Contract Management ---
    path('contracts/', ContractListCreateView.as_view(), name='contract_list_create'),
    path('contracts/<uuid:contract_id>/', ContractDetailView.as_view(), name='contract_detail'),
    
    # --- Contract Stages ---
    path('contracts/<uuid:contract_id>/stages/', ContractStageListView.as_view(), name='contract_stages_list'),
    path('stages/<int:stage_id>/', ContractStageDetailView.as_view(), name='contract_stage_detail'),
    
    # --- Time Extension Requests ---
    path('extension-requests/', TimeExtensionRequestListCreateView.as_view(), name='extension_requests_list'),
    path('extension-requests/<int:request_id>/respond/', TimeExtensionRequestRespondView.as_view(), name='extension_request_respond'),
    path('extension-requests/<int:request_id>/distribute_days/', TimeExtensionDistributeView.as_view(), name='extension_distribute'),
]
