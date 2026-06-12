"""
Dealership URL configuration.

Dealership-facing endpoints:
  /api/dealership/me/
  /api/dealership/me/summary/
  /api/dealership/clients/lookup/
  /api/dealership/fee-config/
  /api/dealership/recharges/preview/
  /api/dealership/recharges/
  /api/dealership/recharges/<id>/
  /api/dealership/cashouts/preview/
  /api/dealership/cashouts/
  /api/dealership/cashouts/<id>/
  /api/dealership/cashouts/<id>/confirm-code/
  /api/dealership/settlements/

Admin/finance endpoints:
  /api/admin/dealerships/
  /api/admin/dealerships/<id>/
  /api/admin/dealerships/<id>/approve/
  /api/admin/dealerships/<id>/suspend/
  /api/admin/dealerships/<id>/block/
  /api/admin/dealerships/<id>/unlock/
  /api/admin/dealerships/<id>/guarantees/
  /api/admin/dealership-guarantees/<id>/verify/
  /api/admin/dealership-guarantees/<id>/reject/
  /api/admin/dealership-recharges/
  /api/admin/dealership-cashouts/
  /api/admin/dealership-settlements/
  /api/admin/dealership-settlements/generate/
  /api/admin/dealership-settlements/<id>/complete/
"""

from django.urls import path
from .views import (
    DealershipMeView,
    DealershipSummaryView,
    ClientLookupView,
    FeeConfigDetailView,
    RechargePreviewView,
    RechargeCreateView,
    RechargeListView,
    RechargeDetailView,
    CashoutPreviewView,
    CashoutCreateView,
    CashoutConfirmView,
    CashoutListView,
    CashoutDetailView,
    SettlementListView,
    # Admin
    AdminDealershipListView,
    AdminDealershipDetailView,
    AdminDealershipApproveView,
    AdminDealershipSuspendView,
    AdminDealershipBlockView,
    AdminDealershipUnlockView,
    AdminGuaranteeListView,
    AdminGuaranteeCreateView,
    AdminGuaranteeVerifyView,
    AdminGuaranteeRejectView,
    AdminRechargeListView,
    AdminCashoutListView,
    AdminSettlementListView,
    AdminSettlementGenerateView,
    AdminSettlementCompleteView,
)

urlpatterns = [
    # Dealership profile
    path('me/', DealershipMeView.as_view(), name='dealership-me'),
    path('me/summary/', DealershipSummaryView.as_view(), name='dealership-summary'),

    # Client lookup
    path('clients/lookup/', ClientLookupView.as_view(), name='dealership-client-lookup'),

    # Fee config
    path('fee-config/', FeeConfigDetailView.as_view(), name='dealership-fee-config'),

    # Recharges
    path('recharges/preview/', RechargePreviewView.as_view(), name='dealership-recharge-preview'),
    path('recharges/', RechargeListView.as_view(), name='dealership-recharge-list'),
    path('recharges/<uuid:recharge_id>/', RechargeDetailView.as_view(), name='dealership-recharge-detail'),
    path('recharges/create/', RechargeCreateView.as_view(), name='dealership-recharge-create'),

    # Cashouts
    path('cashouts/preview/', CashoutPreviewView.as_view(), name='dealership-cashout-preview'),
    path('cashouts/', CashoutListView.as_view(), name='dealership-cashout-list'),
    path('cashouts/create/', CashoutCreateView.as_view(), name='dealership-cashout-create'),
    path('cashouts/<int:cashout_id>/', CashoutDetailView.as_view(), name='dealership-cashout-detail'),
    path('cashouts/<int:cashout_id>/confirm-code/', CashoutConfirmView.as_view(), name='dealership-cashout-confirm'),

    # Settlements
    path('settlements/', SettlementListView.as_view(), name='dealership-settlement-list'),
]
