"""
Views for ServiceRequest — client create/list/detail, technician list/detail,
and status action endpoints.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ServiceRequest
from .serializers import (
    ServiceRequestListSerializer,
    ServiceRequestDetailSerializer,
    ServiceRequestCreateSerializer,
)


class ClientRequestListCreateView(APIView):
    """
    GET  /api/requests/          — List authenticated client's requests.
    POST /api/requests/          — Create a new request (client only).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != "client":
            return Response(
                {"detail": "Only clients can view their requests."},
                status=status.HTTP_403_FORBIDDEN,
            )
        qs = ServiceRequest.objects.filter(client__user=request.user)
        qs = qs.select_related(
            "client__user", "technician__user", "category", "skill"
        )

        # Optional status filter
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter.upper())

        serializer = ServiceRequestListSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    def post(self, request):
        if request.user.role != "client":
            return Response(
                {"detail": "Only clients can create requests."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ServiceRequestCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        sr = serializer.save(
            client=request.user.client_profile,
        )
        detail_serializer = ServiceRequestDetailSerializer(sr, context={"request": request})
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)


class ClientRequestDetailView(APIView):
    """
    GET /api/requests/<uuid:request_id>/ — Client view their request detail.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, request_id):
        try:
            sr = ServiceRequest.objects.select_related(
                "client__user", "technician__user", "category", "skill"
            ).get(id=request_id, client__user=request.user)
        except ServiceRequest.DoesNotExist:
            return Response(
                {"detail": "Request not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ServiceRequestDetailSerializer(sr, context={"request": request})
        return Response(serializer.data)


class ClientCancelRequestView(APIView):
    """
    POST /api/requests/<uuid:request_id>/cancel/ — Client cancels their request.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id):
        if request.user.role != "client":
            return Response(
                {"detail": "Only clients can cancel requests."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            sr = ServiceRequest.objects.get(id=request_id, client__user=request.user)
        except ServiceRequest.DoesNotExist:
            return Response(
                {"detail": "Request not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if sr.status != ServiceRequest.Status.PENDING:
            return Response(
                {"detail": f"Cannot cancel a request with status '{sr.status}'."},
                status=status.HTTP_409_CONFLICT,
            )

        sr.status = ServiceRequest.Status.CANCELLED
        sr.save()
        serializer = ServiceRequestDetailSerializer(sr, context={"request": request})
        return Response(serializer.data)


class ClientWithdrawRequestView(APIView):
    """
    POST /api/requests/<uuid:request_id>/withdraw/ — Client withdraws their request.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id):
        if request.user.role != "client":
            return Response(
                {"detail": "Only clients can withdraw requests."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            sr = ServiceRequest.objects.get(id=request_id, client__user=request.user)
        except ServiceRequest.DoesNotExist:
            return Response(
                {"detail": "Request not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if sr.status != ServiceRequest.Status.PENDING:
            return Response(
                {"detail": f"Cannot withdraw a request with status '{sr.status}'."},
                status=status.HTTP_409_CONFLICT,
            )

        sr.status = ServiceRequest.Status.WITHDRAWN
        sr.save()
        serializer = ServiceRequestDetailSerializer(sr, context={"request": request})
        return Response(serializer.data)


class TechnicianRequestListView(APIView):
    """
    GET /api/technician/requests/ — List authenticated technician's incoming requests.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != "technician":
            return Response(
                {"detail": "Only technicians can view their incoming requests."},
                status=status.HTTP_403_FORBIDDEN,
            )
        qs = ServiceRequest.objects.filter(technician__user=request.user)
        qs = qs.select_related(
            "client__user", "technician__user", "category", "skill"
        )

        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter.upper())

        serializer = ServiceRequestListSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)


class TechnicianRequestDetailView(APIView):
    """
    GET /api/technician/requests/<uuid:request_id>/ — Technician view request detail.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, request_id):
        try:
            sr = ServiceRequest.objects.select_related(
                "client__user", "technician__user", "category", "skill"
            ).get(id=request_id, technician__user=request.user)
        except ServiceRequest.DoesNotExist:
            return Response(
                {"detail": "Request not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ServiceRequestDetailSerializer(sr, context={"request": request})
        return Response(serializer.data)


class TechnicianAcceptRequestView(APIView):
    """
    POST /api/technician/requests/<uuid:request_id>/accept/ — Technician accepts.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id):
        if request.user.role != "technician":
            return Response(
                {"detail": "Only technicians can accept requests."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            sr = ServiceRequest.objects.get(id=request_id, technician__user=request.user)
        except ServiceRequest.DoesNotExist:
            return Response(
                {"detail": "Request not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if sr.status != ServiceRequest.Status.PENDING:
            return Response(
                {"detail": f"Cannot accept a request with status '{sr.status}'."},
                status=status.HTTP_409_CONFLICT,
            )

        sr.status = ServiceRequest.Status.ACCEPTED
        sr.save()
        serializer = ServiceRequestDetailSerializer(sr, context={"request": request})
        return Response(serializer.data)


class TechnicianDeclineRequestView(APIView):
    """
    POST /api/technician/requests/<uuid:request_id>/decline/ — Technician declines.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id):
        if request.user.role != "technician":
            return Response(
                {"detail": "Only technicians can decline requests."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            sr = ServiceRequest.objects.get(id=request_id, technician__user=request.user)
        except ServiceRequest.DoesNotExist:
            return Response(
                {"detail": "Request not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if sr.status != ServiceRequest.Status.PENDING:
            return Response(
                {"detail": f"Cannot decline a request with status '{sr.status}'."},
                status=status.HTTP_409_CONFLICT,
            )

        sr.status = ServiceRequest.Status.DECLINED
        sr.save()
        serializer = ServiceRequestDetailSerializer(sr, context={"request": request})
        return Response(serializer.data)
