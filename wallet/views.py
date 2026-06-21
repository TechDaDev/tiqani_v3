from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import (
    ContractSettlement,
    PlatformFeeConfig,
    ContractPaymentBreakdown,
    PaymentIntent,
    WithdrawalRequest,
    Wallet,
    WalletTransaction,
)
from .serializers import (
    WalletSerializer,
    WalletBalanceSerializer,
    WalletTransactionSerializer,
    PlatformFeeConfigSerializer,
    ContractPaymentBreakdownSerializer,
    PaymentIntentSerializer,
    WithdrawalRequestSerializer,
    WithdrawalRequestCreateSerializer,
    SettlementEligibilitySerializer,
    ContractSettlementSerializer,
    SettlementCreateSerializer,
    AdminWithdrawalActionSerializer,
)
from . import services as svc
from .settlement_services import (
    check_settlement_eligibility,
    settle_completed_contract,
    get_financial_summary,
)


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


# ── Phase 7: Contract Funding ─────────────────────

class ContractFundingEligibilityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, contract_id):
        from contract.models import Contract
        contract = get_object_or_404(Contract, id=contract_id, is_delete=False)
        eligible, reason = svc.check_funding_eligibility(contract, request.user)
        funding_status = svc.get_contract_funding_status(contract)
        data = {
            "contract_id": str(contract.id),
            "contract_reference": contract.contract_reference,
            "eligible": eligible,
            "reason": reason,
            "funding_status": funding_status,
            "agreed_amount": str(contract.agreed_amount) if contract.agreed_amount else None,
            "currency": contract.currency,
        }
        if eligible:
            try:
                breakdown = svc.ensure_contract_payment_breakdown(contract)
                data["client_total_amount"] = str(breakdown.client_total_amount)
                data["client_service_fee"] = str(breakdown.client_service_fee_amount)
                data["technician_commission"] = str(breakdown.technician_commission_amount)
            except Exception:
                pass
        return Response(data, status=status.HTTP_200_OK)


class ContractPaymentIntentCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, contract_id):
        from contract.models import Contract
        contract = get_object_or_404(Contract, id=contract_id, is_delete=False)
        try:
            intent = svc.create_contract_payment_intent(contract, request.user)
            serializer = PaymentIntentSerializer(intent)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PaymentIntentSandboxConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, intent_id):
        pi = get_object_or_404(PaymentIntent, id=intent_id)
        if pi.user != request.user and not request.user.is_staff:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        simulate_failure = request.data.get("simulate_failure", False)
        try:
            intent, result = svc.confirm_sandbox_payment(
                intent_id=str(pi.id),  # Re-fetch for atomic safety
                simulate_failure=bool(simulate_failure),
            )
            serializer = PaymentIntentSerializer(intent)
            return Response({
                "payment_intent": serializer.data,
                "provider_result": {
                    "success": result["success"],
                    "provider": result["provider"],
                    "provider_reference": result.get("provider_reference"),
                    "error_code": result.get("error_code"),
                    "error_message": result.get("error_message"),
                },
            }, status=status.HTTP_200_OK)
        except RuntimeError as e:
            return Response({"detail": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ContractFundingStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, contract_id):
        from contract.models import Contract
        contract = get_object_or_404(Contract, id=contract_id, is_delete=False)
        is_participant = (
            hasattr(request.user, "client_profile") and contract.client.user == request.user
        ) or (
            hasattr(request.user, "technician_profile") and contract.technician.user == request.user
        )
        if not is_participant and not request.user.is_staff:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        funding_status = svc.get_contract_funding_status(contract)
        intents = PaymentIntent.objects.filter(
            contract=contract,
            purpose=PaymentIntent.Purpose.CONTRACT_FUNDING,
        ).order_by("-created_at")

        data = {
            "contract_id": str(contract.id),
            "contract_reference": contract.contract_reference,
            "funding_status": funding_status,
            "escrow_amount": str(contract.escrow_amount or "0.00"),
            "agreed_amount": str(contract.agreed_amount) if contract.agreed_amount else None,
            "currency": contract.currency,
            "active_intent": None,
        }
        active = intents.exclude(status__in=[PaymentIntent.Status.PAID, PaymentIntent.Status.CANCELED]).first()
        if active:
            data["active_intent"] = {
                "id": str(active.id),
                "status": active.status,
                "amount": str(active.amount),
                "created_at": active.created_at.isoformat() if active.created_at else None,
            }
        # Technician sees limited info
        if hasattr(request.user, "technician_profile") and contract.technician.user == request.user:
            data.pop("active_intent", None)
            data["message"] = "Contract funding status (read-only for technicians)."

        return Response(data, status=status.HTTP_200_OK)


# ══════════════════════════════════════════════
#  Phase 9 — Settlement
# ══════════════════════════════════════════════


class SettlementEligibilityView(APIView):
    """Check if a completed contract is eligible for escrow settlement."""
    permission_classes = [IsAuthenticated]

    def get(self, request, contract_id):
        from contract.models import Contract
        try:
            contract = Contract.objects.get(id=contract_id, is_delete=False)
        except Contract.DoesNotExist:
            return Response({"detail": "Contract not found."}, status=status.HTTP_404_NOT_FOUND)

        eligible, reason = check_settlement_eligibility(contract, request.user)
        serializer = SettlementEligibilitySerializer({"eligible": eligible, "reason": reason if not eligible else None})
        return Response(serializer.data)


class SettlementCreateView(APIView):
    """Release escrow for a completed contract."""
    permission_classes = [IsAuthenticated]

    def post(self, request, contract_id):
        from contract.models import Contract
        try:
            contract = Contract.objects.get(id=contract_id, is_delete=False)
        except Contract.DoesNotExist:
            return Response({"detail": "Contract not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = SettlementCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            settlement = settle_completed_contract(
                contract_id=contract_id,
                actor=request.user,
                idempotency_key=serializer.validated_data.get("idempotency_key"),
            )
            return Response(
                ContractSettlementSerializer(settlement).data,
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SettlementDetailView(APIView):
    """Get settlement for a contract."""
    permission_classes = [IsAuthenticated]

    def get(self, request, contract_id):
        from contract.models import Contract
        try:
            contract = Contract.objects.get(id=contract_id, is_delete=False)
        except Contract.DoesNotExist:
            return Response({"detail": "Contract not found."}, status=status.HTTP_404_NOT_FOUND)

        is_participant = (
            hasattr(request.user, "client_profile") and contract.client.user == request.user
        ) or (
            hasattr(request.user, "technician_profile") and contract.technician.user == request.user
        )
        if not is_participant and not request.user.is_staff:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        settlement = ContractSettlement.objects.filter(
            contract=contract
        ).order_by("-created_at").first()
        if not settlement:
            return Response({"detail": "No settlement found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ContractSettlementSerializer(settlement)
        return Response(serializer.data)


class ContractFinancialSummaryView(APIView):
    """Get full financial summary for a contract."""
    permission_classes = [IsAuthenticated]

    def get(self, request, contract_id):
        from contract.models import Contract
        try:
            contract = Contract.objects.get(id=contract_id, is_delete=False)
        except Contract.DoesNotExist:
            return Response({"detail": "Contract not found."}, status=status.HTTP_404_NOT_FOUND)

        is_participant = (
            hasattr(request.user, "client_profile") and contract.client.user == request.user
        ) or (
            hasattr(request.user, "technician_profile") and contract.technician.user == request.user
        )
        if not is_participant and not request.user.is_staff:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            summary = get_financial_summary(contract_id)
            return Response(summary)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ══════════════════════════════════════════════
#  Phase 9 — Wallet
# ══════════════════════════════════════════════


class WalletAvailableBalanceView(APIView):
    """Get technician's available balance."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet = request.user.wallet
        reserved = svc.get_available_balance(wallet)
        total = wallet.balance
        available = svc.get_available_balance(wallet)
        serializer = WalletBalanceSerializer({
            "total_balance": total,
            "reserved_balance": total - available,
            "available_balance": available,
            "currency": "IQD",
        })
        return Response(serializer.data)


# ══════════════════════════════════════════════
#  Phase 9 — Withdrawals (enhanced)
# ══════════════════════════════════════════════


class WithdrawalCancelView(APIView):
    """Cancel a pending or approved withdrawal request."""
    permission_classes = [IsAuthenticated]

    def post(self, request, withdrawal_id):
        wr = get_object_or_404(WithdrawalRequest, id=withdrawal_id)
        try:
            wr = svc.cancel_withdrawal_request(wr, request.user)
            return Response(WithdrawalRequestSerializer(wr).data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ══════════════════════════════════════════════
#  Phase 9 — Staff Withdrawal Management
# ══════════════════════════════════════════════


class AdminWithdrawalListView(APIView):
    """List all withdrawal requests (staff only)."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        status_filter = request.query_params.get("status")
        qs = WithdrawalRequest.objects.all()
        if status_filter:
            qs = qs.filter(status=status_filter)
        qs = qs.order_by("-created_at")
        serializer = WithdrawalRequestSerializer(qs, many=True)
        return Response(serializer.data)


class AdminWithdrawalProcessView(APIView):
    """Move withdrawal from APPROVED to PROCESSING."""
    permission_classes = [IsAdminUser]

    def post(self, request, withdrawal_id):
        wr = get_object_or_404(WithdrawalRequest, id=withdrawal_id)
        try:
            wr = svc.process_withdrawal_request(wr, request.user)
            return Response(WithdrawalRequestSerializer(wr).data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminWithdrawalSandboxConfirmView(APIView):
    """Complete sandbox payout for a withdrawal."""
    permission_classes = [IsAdminUser]

    def post(self, request, withdrawal_id):
        wr = get_object_or_404(WithdrawalRequest, id=withdrawal_id)
        serializer = AdminWithdrawalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            wr = svc.confirm_withdrawal_payout(
                wr,
                request.user,
                simulate_failure=serializer.validated_data.get("simulate_failure", False),
            )
            return Response(WithdrawalRequestSerializer(wr).data)
        except (ValueError, RuntimeError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminWithdrawalRetryView(APIView):
    """Retry a failed withdrawal payout."""
    permission_classes = [IsAdminUser]

    def post(self, request, withdrawal_id):
        wr = get_object_or_404(WithdrawalRequest, id=withdrawal_id)
        serializer = AdminWithdrawalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            wr = svc.retry_failed_withdrawal(
                wr,
                request.user,
                simulate_failure=serializer.validated_data.get("simulate_failure", False),
            )
            return Response(WithdrawalRequestSerializer(wr).data)
        except (ValueError, RuntimeError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
