from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import (
    PlatformFeeConfig,
    ContractPaymentBreakdown,
    PaymentIntent,
    WithdrawalRequest,
    Wallet,
    WalletTransaction,
)
from .serializers import (
    WalletSerializer,
    WalletTransactionSerializer,
    PlatformFeeConfigSerializer,
    ContractPaymentBreakdownSerializer,
    PaymentIntentSerializer,
    WithdrawalRequestSerializer,
    WithdrawalRequestCreateSerializer,
)
from . import services as svc


class IsAdminUser(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_staff


# ── Wallet ─────────────────────────────────────

class WalletMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet = request.user.wallet
        txn_qs = wallet.transactions.all()[:10]
        data = WalletSerializer(wallet).data
        data["recent_transactions"] = WalletTransactionSerializer(txn_qs, many=True).data
        return Response(data, status=status.HTTP_200_OK)


class WalletTransactionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = request.user.wallet.transactions.all()
        ttype = request.query_params.get("transaction_type")
        if ttype:
            qs = qs.filter(transaction_type=ttype)
        ca = request.query_params.get("created_after")
        if ca:
            qs = qs.filter(created_at__gte=ca)
        cb = request.query_params.get("created_before")
        if cb:
            qs = qs.filter(created_at__lte=cb)
        serializer = WalletTransactionSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ── Withdrawals ────────────────────────────────

class WithdrawalListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            qs = WithdrawalRequest.objects.all()
        else:
            qs = WithdrawalRequest.objects.filter(user=request.user)
        serializer = WithdrawalRequestSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = WithdrawalRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            wr = svc.create_withdrawal_request(
                request.user,
                serializer.validated_data["amount"],
                serializer.validated_data.get("requested_method", ""),
                serializer.validated_data.get("notes", ""),
            )
            return Response(WithdrawalRequestSerializer(wr).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class WithdrawalDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, withdrawal_id):
        wr = get_object_or_404(WithdrawalRequest, id=withdrawal_id)
        if not request.user.is_staff and wr.user != request.user:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = WithdrawalRequestSerializer(wr)
        return Response(serializer.data, status=status.HTTP_200_OK)


class WithdrawalApproveView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, withdrawal_id):
        wr = get_object_or_404(WithdrawalRequest, id=withdrawal_id)
        note = request.data.get("admin_note", "")
        try:
            wr = svc.approve_withdrawal_request(wr, request.user, note)
            return Response(WithdrawalRequestSerializer(wr).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class WithdrawalRejectView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, withdrawal_id):
        wr = get_object_or_404(WithdrawalRequest, id=withdrawal_id)
        note = request.data.get("admin_note", "")
        try:
            wr = svc.reject_withdrawal_request(wr, request.user, note)
            return Response(WithdrawalRequestSerializer(wr).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ── Payment Intents ────────────────────────────

class PaymentIntentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            qs = PaymentIntent.objects.all()
        else:
            qs = PaymentIntent.objects.filter(user=request.user)
        serializer = PaymentIntentSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PaymentIntentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, intent_id):
        pi = get_object_or_404(PaymentIntent, id=intent_id)
        if not request.user.is_staff and pi.user != request.user:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = PaymentIntentSerializer(pi)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PaymentIntentMarkPaidView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, intent_id):
        pi = get_object_or_404(PaymentIntent, id=intent_id)
        try:
            pi = svc.mark_payment_intent_paid(pi)
            return Response(PaymentIntentSerializer(pi).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ── Fee Config ─────────────────────────────────

class FeeConfigListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = PlatformFeeConfig.objects.all()
        serializer = PlatformFeeConfigSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = PlatformFeeConfigSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ── Contract Breakdown ─────────────────────────

class ContractBreakdownView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, contract_id):
        from contract.models import Contract
        contract = get_object_or_404(Contract, id=contract_id, is_delete=False)
        # Check participant or admin
        is_participant = (
            hasattr(request.user, "client_profile") and contract.client.user == request.user
        ) or (
            hasattr(request.user, "technician_profile") and contract.technician.user == request.user
        )
        if not is_participant and not request.user.is_staff:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        breakdown = svc.ensure_contract_payment_breakdown(contract)
        serializer = ContractPaymentBreakdownSerializer(breakdown)
        return Response(serializer.data, status=status.HTTP_200_OK)
