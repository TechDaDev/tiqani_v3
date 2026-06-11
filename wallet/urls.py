from django.urls import path
from .views import (
    WalletMeView,
    WalletTransactionListView,
    WithdrawalListCreateView,
    WithdrawalDetailView,
    WithdrawalApproveView,
    WithdrawalRejectView,
    PaymentIntentListView,
    PaymentIntentDetailView,
    PaymentIntentMarkPaidView,
    FeeConfigListView,
    ContractBreakdownView,
)

urlpatterns = [
    path("me/", WalletMeView.as_view(), name="wallet-me"),
    path("transactions/", WalletTransactionListView.as_view(), name="wallet-transactions"),
    # Withdrawals
    path("withdrawals/", WithdrawalListCreateView.as_view(), name="withdrawal-list"),
    path("withdrawals/<uuid:withdrawal_id>/", WithdrawalDetailView.as_view(), name="withdrawal-detail"),
    path("withdrawals/<uuid:withdrawal_id>/approve/", WithdrawalApproveView.as_view(), name="withdrawal-approve"),
    path("withdrawals/<uuid:withdrawal_id>/reject/", WithdrawalRejectView.as_view(), name="withdrawal-reject"),
    # Payment Intents
    path("payment-intents/", PaymentIntentListView.as_view(), name="payment-intent-list"),
    path("payment-intents/<uuid:intent_id>/", PaymentIntentDetailView.as_view(), name="payment-intent-detail"),
    path("payment-intents/<uuid:intent_id>/mark-paid/", PaymentIntentMarkPaidView.as_view(), name="payment-intent-mark-paid"),
    # Fee Config
    path("fee-config/", FeeConfigListView.as_view(), name="fee-config-list"),
    # Contract Breakdown
    path("contracts/<uuid:contract_id>/breakdown/", ContractBreakdownView.as_view(), name="contract-breakdown"),
]
