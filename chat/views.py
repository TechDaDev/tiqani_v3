"""
Chat REST API views — rooms, messages, attachments, price offers, read state, closing.
"""

import logging

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.http import Http404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, JSONParser

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from accounts.models import TechnicianProfile
from contract.models import Contract

from .models import ServiceChatRoom, ServiceChatMessage, ServiceChatReadState
from .serializers import (
    RoomSerializer,
    RoomListSerializer,
    RoomCreateSerializer,
    RoomCloseSerializer,
    LinkContractSerializer,
    MessageSerializer,
    MessageCreateSerializer,
    AttachmentUploadSerializer,
    PriceOfferSerializer,
    UnreadSummarySerializer,
    RequestRoomCreateSerializer,
)
from servicerequest.models import ServiceRequest
from .permissions import (
    CanCreateRoom,
    IsRoomParticipant,
    CanSendMessage,
    CanSendPriceOffer,
    CanAcceptPriceOffer,
    CanLinkContract,
)
from . import services as svc

logger = logging.getLogger(__name__)


# ===================================================================
# Unread summary
# ===================================================================

class UnreadSummaryView(APIView):
    """Get total unread count and per-room breakdown."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get unread chat summary",
        responses={200: UnreadSummarySerializer},
        tags=["Chat"],
    )
    def get(self, request):
        data = svc.get_unread_summary(request.user)
        return Response(data, status=status.HTTP_200_OK)


# ===================================================================
# Rooms
# ===================================================================

class RoomListCreateView(APIView):
    """
    GET:  List current user's chat rooms.
    POST: Client creates a new chat room with a technician.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    @extend_schema(
        summary="List chat rooms",
        description="Returns chat rooms where the current user is a participant.",
        responses={200: RoomListSerializer(many=True)},
        tags=["Chat"],
    )
    def get(self, request):
        qs = svc.get_room_queryset_for_user(request.user)

        # Optional filtering
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        qs = qs.order_by("-last_message_at", "-updated_at")
        serializer = RoomListSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Create chat room",
        description="Client starts a conversation with a technician.",
        request=RoomCreateSerializer,
        responses={201: RoomSerializer, 400: OpenApiResponse(description="Bad request")},
        tags=["Chat"],
    )
    def post(self, request):
        # Only clients can create rooms
        if request.user.role != "client":
            return Response(
                {"detail": "Only clients can initiate chat rooms."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not hasattr(request.user, "client_profile"):
            return Response(
                {"detail": "Client profile not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RoomCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        technician_id = serializer.validated_data["technician_id"]

        # Validate technician exists and is approved
        try:
            tech_profile = TechnicianProfile.objects.get(
                id=technician_id,
                approved=True,
            )
        except TechnicianProfile.DoesNotExist:
            return Response(
                {"detail": "Technician not found or not approved."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Prevent self-chat
        if tech_profile.user == request.user:
            return Response(
                {"detail": "Cannot start a chat with yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            room, created = svc.get_or_create_chat_room(
                client_user=request.user,
                technician_profile=tech_profile,
                created_by=request.user,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create initial message if provided
        initial_message = serializer.validated_data.get("initial_message", "")
        if initial_message:
            try:
                svc.create_message(
                    room=room,
                    sender=request.user,
                    body=initial_message,
                )
            except Exception as exc:
                logger.warning("Failed to create initial message: %s", exc)

        resp_serializer = RoomSerializer(room, context={"request": request})
        http_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(resp_serializer.data, status=http_status)


class RoomDetailView(APIView):
    """GET: Retrieve a single chat room with full details."""

    permission_classes = [IsAuthenticated, IsRoomParticipant]
    parser_classes = [JSONParser]

    def get_object(self):
        room = get_object_or_404(ServiceChatRoom, id=self.kwargs["room_id"])
        self.check_object_permissions(self.request, room)
        return room

    @extend_schema(
        summary="Get chat room details",
        responses={200: RoomSerializer},
        tags=["Chat"],
    )
    def get(self, request, room_id):
        room = self.get_object()
        serializer = RoomSerializer(room, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


# ===================================================================
# Request-linked conversation
# ===================================================================

class RoomByRequestView(APIView):
    """
    GET:   Get existing room linked to a service request.
    POST:  Create (or get) a conversation for a service request.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def _get_request(self, request_id):
        """Get a service request and verify the current user is involved."""
        service_request = get_object_or_404(ServiceRequest, id=request_id)

        # Verify user is the client or assigned technician
        user = self.request.user
        is_client = (
            hasattr(user, "client_profile")
            and user.client_profile == service_request.client
        )
        is_technician = (
            hasattr(user, "technician_profile")
            and user.technician_profile == service_request.technician
        )
        if not is_client and not is_technician and not user.is_staff:
            raise Http404

        return service_request

    @extend_schema(
        summary="Get conversation for service request",
        responses={200: RoomSerializer, 404: OpenApiResponse(description="Room not found")},
        tags=["Chat"],
    )
    def get(self, request, request_id):
        service_request = self._get_request(request_id)
        room = ServiceChatRoom.objects.filter(service_request=service_request).first()
        if not room:
            return Response(
                {"detail": "No conversation linked to this request."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = RoomSerializer(room, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Create or get conversation for service request",
        responses={200: RoomSerializer, 201: RoomSerializer},
        tags=["Chat"],
    )
    def post(self, request, request_id):
        service_request = self._get_request(request_id)

        try:
            room, created = svc.get_or_create_room_for_request(
                service_request=service_request,
                created_by=request.user,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RoomSerializer(room, context={"request": request})
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=status_code)


# ===================================================================
# Messages
# ===================================================================

class MessageListView(APIView):
    """GET: List messages in a room (paginated, oldest first)."""

    permission_classes = [IsAuthenticated, IsRoomParticipant]
    parser_classes = [JSONParser]

    def get_room(self):
        room = get_object_or_404(ServiceChatRoom, id=self.kwargs["room_id"])
        self.check_object_permissions(self.request, room)
        return room

    @extend_schema(
        summary="List chat messages",
        description="Returns paginated messages (oldest first). Supports ?before=<id> and ?after=<id>.",
        parameters=[
            OpenApiParameter("before", OpenApiTypes.UUID, description="Get messages before this ID"),
            OpenApiParameter("after", OpenApiTypes.UUID, description="Get messages after this ID"),
            OpenApiParameter("page", OpenApiTypes.INT, description="Page number"),
        ],
        responses={200: MessageSerializer(many=True)},
        tags=["Chat"],
    )
    def get(self, request, room_id):
        room = self.get_room()
        qs = ServiceChatMessage.objects.filter(
            room=room,
        ).select_related("sender").order_by("created_at")

        # Optional cursor-based filtering
        before = request.query_params.get("before")
        after = request.query_params.get("after")

        if before:
            qs = qs.filter(id__lt=before)
        if after:
            qs = qs.filter(id__gt=after)

        # Pagination
        page = int(request.query_params.get("page", 1))
        page_size = 50
        start = (page - 1) * page_size
        end = start + page_size
        qs_page = qs[start:end]

        serializer = MessageSerializer(qs_page, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class MessageCreateView(APIView):
    """POST: Send a text message via REST fallback."""

    permission_classes = [IsAuthenticated, IsRoomParticipant]
    parser_classes = [JSONParser]

    def get_room(self):
        room = get_object_or_404(ServiceChatRoom, id=self.kwargs["room_id"])
        self.check_object_permissions(self.request, room)
        return room

    @extend_schema(
        summary="Send a text message",
        request=MessageCreateSerializer,
        responses={201: MessageSerializer},
        tags=["Chat"],
    )
    def post(self, request, room_id):
        room = self.get_room()

        if not room.can_send(request.user):
            return Response(
                {"detail": "Cannot send messages in this room (closed/blocked)."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            message, _ = svc.create_message(
                room=room,
                sender=request.user,
                body=serializer.validated_data["body"],
            )
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

        resp_serializer = MessageSerializer(message, context={"request": request})
        return Response(resp_serializer.data, status=status.HTTP_201_CREATED)


class AttachmentUploadView(APIView):
    """POST: Upload a file attachment as a message."""

    permission_classes = [IsAuthenticated, IsRoomParticipant]
    parser_classes = [MultiPartParser]

    def get_room(self):
        room = get_object_or_404(ServiceChatRoom, id=self.kwargs["room_id"])
        self.check_object_permissions(self.request, room)
        return room

    @extend_schema(
        summary="Upload attachment",
        description="Upload a file as a chat message (multipart).",
        request=AttachmentUploadSerializer,
        responses={201: MessageSerializer},
        tags=["Chat"],
    )
    def post(self, request, room_id):
        room = self.get_room()

        if not room.can_send(request.user):
            return Response(
                {"detail": "Cannot send messages in this room (closed/blocked)."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = AttachmentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["file"]
        body = serializer.validated_data.get("body", "")

        try:
            message, _ = svc.create_message(
                room=room,
                sender=request.user,
                body=body,
                message_type="FILE",
                attachment=uploaded_file,
                attachment_name=uploaded_file.name,
                attachment_size=uploaded_file.size,
                attachment_content_type=uploaded_file.content_type or "",
            )
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

        resp_serializer = MessageSerializer(message, context={"request": request})
        return Response(resp_serializer.data, status=status.HTTP_201_CREATED)


# ===================================================================
# Price offers
# ===================================================================

class PriceOfferCreateView(APIView):
    """POST: Technician sends a price offer."""

    permission_classes = [IsAuthenticated, IsRoomParticipant]
    parser_classes = [JSONParser]

    def get_room(self):
        room = get_object_or_404(ServiceChatRoom, id=self.kwargs["room_id"])
        self.check_object_permissions(self.request, room)
        return room

    @extend_schema(
        summary="Send price offer",
        description="Technician sends a price offer to the client.",
        request=PriceOfferSerializer,
        responses={201: MessageSerializer},
        tags=["Chat"],
    )
    def post(self, request, room_id):
        room = self.get_room()

        # Only technicians
        if request.user.role != "technician":
            return Response(
                {"detail": "Only technicians can send price offers."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not hasattr(request.user, "technician_profile"):
            return Response(
                {"detail": "Technician profile not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request.user.technician_profile != room.technician:
            return Response(
                {"detail": "You are not the technician for this room."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if room.status in (ServiceChatRoom.Status.CLOSED, ServiceChatRoom.Status.BLOCKED):
            return Response(
                {"detail": "Cannot send offers in a closed or blocked room."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = PriceOfferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            message, _ = svc.create_price_offer(
                room=room,
                technician_user=request.user,
                amount=serializer.validated_data["amount"],
                currency=serializer.validated_data.get("currency", "IQD"),
                description=serializer.validated_data.get("description", ""),
            )
        except (PermissionError, ValueError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

        resp_serializer = MessageSerializer(message, context={"request": request})
        return Response(resp_serializer.data, status=status.HTTP_201_CREATED)


class PriceOfferAcceptView(APIView):
    """POST: Client accepts a price offer."""

    permission_classes = [IsAuthenticated, IsRoomParticipant]
    parser_classes = [JSONParser]

    def get_room(self):
        room = get_object_or_404(ServiceChatRoom, id=self.kwargs["room_id"])
        self.check_object_permissions(self.request, room)
        return room

    @extend_schema(
        summary="Accept price offer",
        description="Client accepts a price offer in the room.",
        responses={200: MessageSerializer},
        tags=["Chat"],
    )
    def post(self, request, room_id, message_id):
        room = self.get_room()

        if request.user.role != "client":
            return Response(
                {"detail": "Only clients can accept price offers."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            offer_msg, accept_msg = svc.accept_price_offer(
                room=room,
                client_user=request.user,
                message_id=message_id,
            )
        except (PermissionError, ValueError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        resp_serializer = MessageSerializer(accept_msg, context={"request": request})
        return Response(resp_serializer.data, status=status.HTTP_200_OK)


# ===================================================================
# Room actions
# ===================================================================

class MarkRoomReadView(APIView):
    """POST: Mark all messages in a room as read."""

    permission_classes = [IsAuthenticated, IsRoomParticipant]
    parser_classes = [JSONParser]

    def get_room(self):
        room = get_object_or_404(ServiceChatRoom, id=self.kwargs["room_id"])
        self.check_object_permissions(self.request, room)
        return room

    @extend_schema(
        summary="Mark room as read",
        responses={200: OpenApiResponse(description="Read state updated")},
        tags=["Chat"],
    )
    def post(self, request, room_id):
        room = self.get_room()
        try:
            svc.mark_room_read(room, request.user)
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

        return Response({"detail": "Room marked as read."}, status=status.HTTP_200_OK)


class CloseRoomView(APIView):
    """POST: Close a chat room."""

    permission_classes = [IsAuthenticated, IsRoomParticipant]
    parser_classes = [JSONParser]

    def get_room(self):
        room = get_object_or_404(ServiceChatRoom, id=self.kwargs["room_id"])
        self.check_object_permissions(self.request, room)
        return room

    @extend_schema(
        summary="Close chat room",
        request=RoomCloseSerializer,
        responses={200: RoomSerializer},
        tags=["Chat"],
    )
    def post(self, request, room_id):
        room = self.get_room()
        serializer = RoomCloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            svc.close_room(
                room=room,
                user=request.user,
                reason=serializer.validated_data.get("reason", ""),
            )
        except (PermissionError, ValueError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        resp_serializer = RoomSerializer(room, context={"request": request})
        return Response(resp_serializer.data, status=status.HTTP_200_OK)


class LinkContractView(APIView):
    """POST: Link an existing contract to the room."""

    permission_classes = [IsAuthenticated, IsRoomParticipant]
    parser_classes = [JSONParser]

    def get_room(self):
        room = get_object_or_404(ServiceChatRoom, id=self.kwargs["room_id"])
        self.check_object_permissions(self.request, room)
        return room

    @extend_schema(
        summary="Link contract to room",
        request=LinkContractSerializer,
        responses={200: RoomSerializer},
        tags=["Chat"],
    )
    def post(self, request, room_id):
        room = self.get_room()
        serializer = LinkContractSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        contract_id = serializer.validated_data["contract_id"]

        try:
            contract = Contract.objects.get(id=contract_id, is_delete=False)
        except Contract.DoesNotExist:
            return Response(
                {"detail": "Contract not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            svc.link_contract_to_room(room, contract, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        resp_serializer = RoomSerializer(room, context={"request": request})
        return Response(resp_serializer.data, status=status.HTTP_200_OK)
