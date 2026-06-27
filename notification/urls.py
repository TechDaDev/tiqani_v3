from django.urls import path
from .views import (
    NotificationListView, NotificationDetailView,
    NotificationUnreadCountView,
    NotificationMarkReadView, NotificationMarkUnreadView,
    NotificationMarkAllReadView,
    ActivityLogListView,
    NotificationPreferenceView,
)

urlpatterns = [
    # Notifications
    path('', NotificationListView.as_view(), name='notification_list'),
    path('unread-count/', NotificationUnreadCountView.as_view(), name='notification_unread_count'),
    path('preferences/', NotificationPreferenceView.as_view(), name='notification_preferences'),
    path('<uuid:id>/', NotificationDetailView.as_view(), name='notification_detail'),
    path('<uuid:id>/mark-read/', NotificationMarkReadView.as_view(), name='notification_mark_read'),
    path('<uuid:id>/mark-unread/', NotificationMarkUnreadView.as_view(), name='notification_mark_unread'),
    path('mark-all-read/', NotificationMarkAllReadView.as_view(), name='notification_mark_all_read'),
    # Activity
    path('activity/', ActivityLogListView.as_view(), name='activity_log_list'),
]
