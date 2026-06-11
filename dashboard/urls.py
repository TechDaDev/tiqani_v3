from django.urls import path
from .views import (
    DashboardSummaryView,
    AdminUserListView, AdminUserDetailUpdateView,
    AdminUserActivateView, AdminUserDeactivateView,
    AdminTechnicianListView, AdminTechnicianPendingView,
    AdminTechnicianDetailView, AdminTechnicianApproveView, AdminTechnicianRejectView,
    AdminContractListView, AdminContractDetailView, AdminContractForceCancelView,
    AdminReviewListView, AdminReviewFlaggedView, AdminReviewDetailView,
    AdminReviewHideView, AdminReviewPublishView, AdminReviewVerifyView, AdminReviewUnverifyView,
    AdminFinanceSummaryView,
    AdminPlatformEarningListView, AdminPaymentIntentListView, AdminWithdrawalListView,
    AdminWithdrawalApproveView, AdminWithdrawalRejectView, AdminPaymentIntentMarkPaidView,
    AdminActivityListView,
)

urlpatterns = [
    # Dashboard
    path('dashboard/summary/', DashboardSummaryView.as_view(), name='admin_dashboard_summary'),

    # Users
    path('users/', AdminUserListView.as_view(), name='admin_user_list'),
    path('users/<uuid:id>/', AdminUserDetailUpdateView.as_view(), name='admin_user_detail_update'),
    path('users/<uuid:id>/activate/', AdminUserActivateView.as_view(), name='admin_user_activate'),
    path('users/<uuid:id>/deactivate/', AdminUserDeactivateView.as_view(), name='admin_user_deactivate'),

    # Technicians
    path('technicians/', AdminTechnicianListView.as_view(), name='admin_technician_list'),
    path('technicians/pending/', AdminTechnicianPendingView.as_view(), name='admin_technician_pending'),
    path('technicians/<uuid:id>/', AdminTechnicianDetailView.as_view(), name='admin_technician_detail'),
    path('technicians/<uuid:id>/approve/', AdminTechnicianApproveView.as_view(), name='admin_technician_approve'),
    path('technicians/<uuid:id>/reject/', AdminTechnicianRejectView.as_view(), name='admin_technician_reject'),

    # Contracts
    path('contracts/', AdminContractListView.as_view(), name='admin_contract_list'),
    path('contracts/<uuid:id>/', AdminContractDetailView.as_view(), name='admin_contract_detail'),
    path('contracts/<uuid:id>/force-cancel/', AdminContractForceCancelView.as_view(), name='admin_contract_force_cancel'),

    # Reviews
    path('reviews/', AdminReviewListView.as_view(), name='admin_review_list'),
    path('reviews/flagged/', AdminReviewFlaggedView.as_view(), name='admin_review_flagged'),
    path('reviews/<uuid:id>/', AdminReviewDetailView.as_view(), name='admin_review_detail'),
    path('reviews/<uuid:id>/hide/', AdminReviewHideView.as_view(), name='admin_review_hide'),
    path('reviews/<uuid:id>/publish/', AdminReviewPublishView.as_view(), name='admin_review_publish'),
    path('reviews/<uuid:id>/verify/', AdminReviewVerifyView.as_view(), name='admin_review_verify'),
    path('reviews/<uuid:id>/unverify/', AdminReviewUnverifyView.as_view(), name='admin_review_unverify'),

    # Finance
    path('finance/summary/', AdminFinanceSummaryView.as_view(), name='admin_finance_summary'),
    path('finance/platform-earnings/', AdminPlatformEarningListView.as_view(), name='admin_finance_earnings'),
    path('finance/payment-intents/', AdminPaymentIntentListView.as_view(), name='admin_finance_payment_intents'),
    path('finance/payment-intents/<uuid:id>/mark-paid/', AdminPaymentIntentMarkPaidView.as_view(), name='admin_finance_pi_mark_paid'),
    path('finance/withdrawals/', AdminWithdrawalListView.as_view(), name='admin_finance_withdrawals'),
    path('finance/withdrawals/<uuid:id>/approve/', AdminWithdrawalApproveView.as_view(), name='admin_finance_withdrawal_approve'),
    path('finance/withdrawals/<uuid:id>/reject/', AdminWithdrawalRejectView.as_view(), name='admin_finance_withdrawal_reject'),

    # Activity
    path('activity/', AdminActivityListView.as_view(), name='admin_activity_list'),
]
