"""Offer API views — technician create/list/update, client review/accept/reject."""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from contract.offer_models import Offer
from contract.offer_serializers import (
    OfferListSerializer,
    OfferDetailSerializer,
    OfferCreateSerializer,
    OfferUpdateSerializer,
)
from contract.offer_services import (
    create_offer,
    update_offer,
    submit_offer,
    withdraw_offer,
    accept_offer,
    reject_offer,
)
from servicerequest.models import ServiceRequest


# ------------------------------------------------------------------
# Technician offer management
# ------------------------------------------------------------------

class TechnicianOfferListCreateView(APIView):
    """
    GET  /api/technician/offers/          — List own offers.
    POST /api/technician/offers/          — Create draft offer.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != "technician":
            return Response(
                {"detail": "Only technicians can view their offers."},
                status=status.HTTP_403_FORBIDDEN,
            )
        qs = Offer.objects.filter(
            service_request__technician__user=request.user,
        ).select_related(
            "service_request__technician__user",
            "service_request__client__user",
        )

        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter.upper())

        serializer = OfferListSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    def post(self, request):
        if request.user.role != "technician":
            return Response(
                {"detail": "Only technicians can create offers."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = OfferCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Resolve service request
        sr = get_object_or_404(
            ServiceRequest,
            id=serializer.validated_data["service_request_id"],
        )

        try:
            offer = create_offer(sr, request.user, serializer.validated_data)
            detail_serializer = OfferDetailSerializer(offer, context={"request": request})
            return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
        except (PermissionError, ValueError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN
                          if isinstance(e, PermissionError) else status.HTTP_409_CONFLICT)


class TechnicianOfferDetailView(APIView):
    """
    GET   /api/technician/offers/<uuid:offer_id>/   — View own offer.
    PATCH /api/technician/offers/<uuid:offer_id>/   — Update draft offer.
    """
    permission_classes = [IsAuthenticated]

    def _get_offer(self, offer_id, user):
        return get_object_or_404(
            Offer,
            id=offer_id,
            service_request__technician__user=user,
        )

    def get(self, request, offer_id):
        if request.user.role != "technician":
            return Response(
                {"detail": "Only technicians can view their offers."},
                status=status.HTTP_403_FORBIDDEN,
            )
        offer = self._get_offer(offer_id, request.user)
        serializer = OfferDetailSerializer(offer, context={"request": request})
        return Response(serializer.data)

    def patch(self, request, offer_id):
        if request.user.role != "technician":
            return Response(
                {"detail": "Only technicians can update their offers."},
                status=status.HTTP_403_FORBIDDEN,
            )
        offer = self._get_offer(offer_id, request.user)

        serializer = OfferUpdateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            offer = update_offer(offer, request.user, serializer.validated_data)
            detail_serializer = OfferDetailSerializer(offer, context={"request": request})
            return Response(detail_serializer.data)
        except (PermissionError, ValueError) as e:
            return Response({"detail": str(e)},
                          status=status.HTTP_403_FORBIDDEN
                          if isinstance(e, PermissionError) else status.HTTP_409_CONFLICT)


class TechnicianOfferSubmitView(APIView):
    """
    POST /api/technician/offers/<uuid:offer_id>/submit/ — Submit draft offer.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, offer_id):
        if request.user.role != "technician":
            return Response(
                {"detail": "Only technicians can submit offers."},
                status=status.HTTP_403_FORBIDDEN,
            )
        offer = get_object_or_404(
            Offer,
            id=offer_id,
            service_request__technician__user=request.user,
        )

        try:
            offer = submit_offer(offer, request.user)
            detail_serializer = OfferDetailSerializer(offer, context={"request": request})
            return Response(detail_serializer.data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)


class TechnicianOfferWithdrawView(APIView):
    """
    POST /api/technician/offers/<uuid:offer_id>/withdraw/ — Withdraw submitted offer.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, offer_id):
        if request.user.role != "technician":
            return Response(
                {"detail": "Only technicians can withdraw offers."},
                status=status.HTTP_403_FORBIDDEN,
            )
        offer = get_object_or_404(
            Offer,
            id=offer_id,
            service_request__technician__user=request.user,
        )

        try:
            offer = withdraw_offer(offer, request.user)
            detail_serializer = OfferDetailSerializer(offer, context={"request": request})
            return Response(detail_serializer.data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)


# ------------------------------------------------------------------
# Client offer review
# ------------------------------------------------------------------

class ClientOfferListView(APIView):
    """
    GET /api/offers/ — List incoming offers for the authenticated client's requests.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != "client":
            return Response(
                {"detail": "Only clients can view their incoming offers."},
                status=status.HTTP_403_FORBIDDEN,
            )
        qs = Offer.objects.filter(
            service_request__client__user=request.user,
        ).select_related(
            "service_request__technician__user",
            "service_request__client__user",
        )

        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter.upper())

        serializer = OfferListSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)


class ClientOfferDetailView(APIView):
    """
    GET /api/offers/<uuid:offer_id>/ — View incoming offer detail.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, offer_id):
        if request.user.role != "client":
            return Response(
                {"detail": "Only clients can view incoming offers."},
                status=status.HTTP_403_FORBIDDEN,
            )
        offer = get_object_or_404(
            Offer,
            id=offer_id,
            service_request__client__user=request.user,
        )
        serializer = OfferDetailSerializer(offer, context={"request": request})
        return Response(serializer.data)


class ClientOfferAcceptView(APIView):
    """
    POST /api/offers/<uuid:offer_id>/accept/ — Accept offer and create contract.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, offer_id):
        if request.user.role != "client":
            return Response(
                {"detail": "Only clients can accept offers."},
                status=status.HTTP_403_FORBIDDEN,
            )
        offer = get_object_or_404(
            Offer,
            id=offer_id,
            service_request__client__user=request.user,
        )

        try:
            offer, contract = accept_offer(offer, request.user)
            return Response(
                {
                    "detail": "Offer accepted. Contract created.",
                    "offer_id": str(offer.id),
                    "contract_id": str(contract.id),
                    "offer_status": offer.status,
                },
                status=status.HTTP_200_OK,
            )
        except (PermissionError, ValueError) as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_403_FORBIDDEN
                if isinstance(e, PermissionError) else status.HTTP_409_CONFLICT,
            )


class ClientOfferRejectView(APIView):
    """
    POST /api/offers/<uuid:offer_id>/reject/ — Reject offer.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, offer_id):
        if request.user.role != "client":
            return Response(
                {"detail": "Only clients can reject offers."},
                status=status.HTTP_403_FORBIDDEN,
            )
        offer = get_object_or_404(
            Offer,
            id=offer_id,
            service_request__client__user=request.user,
        )

        try:
            offer = reject_offer(offer, request.user)
            serializer = OfferDetailSerializer(offer, context={"request": request})
            return Response(serializer.data)
        except (PermissionError, ValueError) as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_403_FORBIDDEN
                if isinstance(e, PermissionError) else status.HTTP_409_CONFLICT,
            )


# ------------------------------------------------------------------
# By-request lookup (authenticated participants)
# ------------------------------------------------------------------

class OfferByRequestView(APIView):
    """
    GET /api/offers/by-request/<uuid:request_id>/ — List offers for a specific request.
    Accessible to client (request owner) or technician (assigned).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, request_id):
        sr = get_object_or_404(ServiceRequest, id=request_id)

        # Check authorization
        is_client = sr.client.user_id == request.user.id
        is_technician = sr.technician.user_id == request.user.id

        if not (is_client or is_technician or request.user.is_staff):
            return Response(
                {"detail": "You do not have access to offers for this request."},
                status=status.HTTP_404_NOT_FOUND,
            )

        qs = Offer.objects.filter(service_request=sr).select_related(
            "service_request__technician__user",
            "service_request__client__user",
        )
        serializer = OfferListSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)
