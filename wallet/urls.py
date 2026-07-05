from django.urls import path
from .views import (
    WalletMeView,
    WalletTransactionListView,
    WalletAvailableBalanceView,
    WalletRechargeRequestListCreateView,
    WalletRechargeRequestDetailView,
    WalletRechargeRequestCancelView,
    WalletRechargeRequestReceiptView,
    WithdrawalListCreateView,
    WithdrawalDetailView,
    WithdrawalApproveView,
    WithdrawalRejectView,
    WithdrawalCancelView,
    PaymentIntentListView,
    PaymentIntentDetailView,
    PaymentIntentMarkPaidView,
    FeeConfigListView,
    ContractBreakdownView,
    ContractFundingEligibilityView,
    ContractPaymentIntentCreateView,
    ContractFundingStatusView,
    PaymentIntentSandboxConfirmView,
    SettlementEligibilityView,
    SettlementCreateView,
    SettlementDetailView,
    ContractFinancialSummaryView,
    AdminWithdrawalListView,
    AdminWithdrawalProcessView,
    AdminWithdrawalSandboxConfirmView,
    AdminWithdrawalRetryView,
)

urlpatterns = [
    # Wallet
    path("me/", WalletMeView.as_view(), name="wallet-me"),
    path("transactions/", WalletTransactionListView.as_view(), name="wallet-transactions"),
    path("available-balance/", WalletAvailableBalanceView.as_view(), name="wallet-available-balance"),
    path("recharge-requests/", WalletRechargeRequestListCreateView.as_view(), name="wallet-recharge-request-list"),
    path("recharge-requests/<uuid:recharge_id>/", WalletRechargeRequestDetailView.as_view(), name="wallet-recharge-request-detail"),
    path("recharge-requests/<uuid:recharge_id>/cancel/", WalletRechargeRequestCancelView.as_view(), name="wallet-recharge-request-cancel"),
    path("recharge-requests/<uuid:recharge_id>/receipt/", WalletRechargeRequestReceiptView.as_view(), name="wallet-recharge-request-receipt"),
    # Withdrawals
    path("withdrawals/", WithdrawalListCreateView.as_view(), name="withdrawal-list"),
    path("withdrawals/<uuid:withdrawal_id>/", WithdrawalDetailView.as_view(), name="withdrawal-detail"),
    path("withdrawals/<uuid:withdrawal_id>/approve/", WithdrawalApproveView.as_view(), name="withdrawal-approve"),
    path("withdrawals/<uuid:withdrawal_id>/reject/", WithdrawalRejectView.as_view(), name="withdrawal-reject"),
    path("withdrawals/<uuid:withdrawal_id>/cancel/", WithdrawalCancelView.as_view(), name="withdrawal-cancel"),
    # Payment Intents
    path("payment-intents/", PaymentIntentListView.as_view(), name="payment-intent-list"),
    path("payment-intents/<uuid:intent_id>/", PaymentIntentDetailView.as_view(), name="payment-intent-detail"),
    path("payment-intents/<uuid:intent_id>/mark-paid/", PaymentIntentMarkPaidView.as_view(), name="payment-intent-mark-paid"),
    # Fee Config
    path("fee-config/", FeeConfigListView.as_view(), name="fee-config-list"),
    # Contract Breakdown
    path("contracts/<uuid:contract_id>/breakdown/", ContractBreakdownView.as_view(), name="contract-breakdown"),
    # Phase 7 — Contract Funding
    path("contracts/<uuid:contract_id>/funding/eligibility/", ContractFundingEligibilityView.as_view(), name="contract-funding-eligibility"),
    path("contracts/<uuid:contract_id>/funding/intents/", ContractPaymentIntentCreateView.as_view(), name="contract-payment-intent-create"),
    path("contracts/<uuid:contract_id>/funding/status/", ContractFundingStatusView.as_view(), name="contract-funding-status"),
    path("payment-intents/<uuid:intent_id>/sandbox-confirm/", PaymentIntentSandboxConfirmView.as_view(), name="payment-intent-sandbox-confirm"),
    # Phase 9 — Settlement
    path("contracts/<uuid:contract_id>/settlement/eligibility/", SettlementEligibilityView.as_view(), name="settlement-eligibility"),
    path("contracts/<uuid:contract_id>/settlements/", SettlementCreateView.as_view(), name="settlement-create"),
    path("contracts/<uuid:contract_id>/settlement/", SettlementDetailView.as_view(), name="settlement-detail"),
    path("contracts/<uuid:contract_id>/financial-summary/", ContractFinancialSummaryView.as_view(), name="contract-financial-summary"),
    # Phase 9 — Staff Withdrawals
    path("admin/withdrawals/", AdminWithdrawalListView.as_view(), name="admin-withdrawal-list"),
    path("admin/withdrawals/<uuid:withdrawal_id>/process/", AdminWithdrawalProcessView.as_view(), name="admin-withdrawal-process"),
    path("admin/withdrawals/<uuid:withdrawal_id>/sandbox-confirm/", AdminWithdrawalSandboxConfirmView.as_view(), name="admin-withdrawal-sandbox-confirm"),
    path("admin/withdrawals/<uuid:withdrawal_id>/retry/", AdminWithdrawalRetryView.as_view(), name="admin-withdrawal-retry"),
]
