"""Views for notification and activity feed APIs."""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView, RetrieveAPIView, GenericAPIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend

from .models import Notification, ActivityLog, NotificationPreference
from .serializers import (
    NotificationSerializer,
    ActivityLogSerializer,
    NotificationPreferenceSerializer,
)
from .permissions import IsNotificationOwner, IsAdminOrStaffForActivity
from .services import mark_notification_read, mark_all_notifications_read


class NotificationListView(ListAPIView):
    """GET /api/notifications/ — list current user's notifications."""
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'is_read': ['exact'],
        'notification_type': ['exact'],
        'created_at': ['gte', 'lte'],
    }

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)


class NotificationDetailView(RetrieveAPIView):
    """GET /api/notifications/<id>/ — retrieve a notification."""
    permission_classes = [IsAuthenticated, IsNotificationOwner]
    serializer_class = NotificationSerializer
    queryset = Notification.objects.all()
    lookup_field = 'id'


class NotificationUnreadCountView(GenericAPIView):
    """GET /api/notifications/unread-count/ — unread count."""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        count = Notification.unread_count_for_user(request.user)
        return Response({'unread_count': count})


class NotificationMarkReadView(GenericAPIView):
    """POST /api/notifications/<id>/mark-read/ — mark one as read."""
    permission_classes = [IsAuthenticated, IsNotificationOwner]

    def get_object(self):
        n = get_object_or_404(Notification, id=self.kwargs['id'])
        self.check_object_permissions(self.request, n)
        return n

    def post(self, request, *args, **kwargs):
        notification = self.get_object()
        mark_notification_read(notification, request.user)
        return Response({'status': 'ok', 'is_read': True})


class NotificationMarkUnreadView(GenericAPIView):
    """POST /api/notifications/<id>/mark-unread/ — mark one as unread."""
    permission_classes = [IsAuthenticated, IsNotificationOwner]

    def get_object(self):
        n = get_object_or_404(Notification, id=self.kwargs['id'])
        self.check_object_permissions(self.request, n)
        return n

    def post(self, request, *args, **kwargs):
        notification = self.get_object()
        notification.mark_unread()
        return Response({'status': 'ok', 'is_read': False})


class NotificationMarkAllReadView(GenericAPIView):
    """POST /api/notifications/mark-all-read/ — mark all as read."""
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        count = mark_all_notifications_read(request.user)
        return Response({'status': 'ok', 'updated': count})


class ActivityLogListView(ListAPIView):
    """GET /api/notifications/activity/ — admin activity feed."""
    permission_classes = [IsAuthenticated, IsAdminOrStaffForActivity]
    serializer_class = ActivityLogSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'actor': ['exact'],
        'audience': ['exact'],
        'target_type': ['exact'],
        'created_at': ['gte', 'lte'],
    }

    def get_queryset(self):
        return ActivityLog.objects.all()


class NotificationPreferenceView(GenericAPIView):
    """GET/PATCH /api/notifications/preferences/."""
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationPreferenceSerializer

    def get_object(self):
        preferences, _ = NotificationPreference.objects.get_or_create(user=self.request.user)
        return preferences

    def get(self, request, *args, **kwargs):
        return Response(self.get_serializer(self.get_object()).data)

    def patch(self, request, *args, **kwargs):
        preferences = self.get_object()
        serializer = self.get_serializer(preferences, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
