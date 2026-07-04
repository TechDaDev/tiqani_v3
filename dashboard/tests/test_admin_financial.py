from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import ClientProfile, TechnicianProfile
from contract.models import Contract
from dispute.models import (
    ContractDispute,
    DisputeReason,
    RefundRecord,
    RefundSourceType,
    RefundStatus,
)
from notification.models import ActivityLog
from wallet.models import PaymentIntent, Wallet, WalletTransaction, WithdrawalRequest

User = get_user_model()


class AdminFinancialApiTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_superuser(
            username="finance-admin",
            email="finance-admin@example.com",
            password="pass12345",
        )
        self.client_user = User.objects.create_user(
            username="finance-client",
            email="finance-client@example.com",
            password="pass12345",
            role="client",
        )
        self.tech_user = User.objects.create_user(
            username="finance-tech",
            email="finance-tech@example.com",
            password="pass12345",
            role="technician",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)
        self.tech_profile = TechnicianProfile.objects.create(user=self.tech_user, approved=True)
        self.client_wallet, _ = Wallet.objects.get_or_create(user=self.client_user)
        self.tech_wallet, _ = Wallet.objects.get_or_create(user=self.tech_user)
        self.tech_wallet.balance = Decimal("100000.00")
        self.tech_wallet.save(update_fields=["balance"])
        self.contract = Contract.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            agreed_amount=Decimal("50000.00"),
            escrow_amount=Decimal("50000.00"),
            status="in_progress",
        )
        self.payment = PaymentIntent.objects.create(
            contract=self.contract,
            user=self.client_user,
            amount=Decimal("52500.00"),
            provider_reference="provider-secret-reference-123456",
            metadata={"secret": "never-render"},
            status=PaymentIntent.Status.PAID,
            paid_at=timezone.now(),
        )
        self.ledger = WalletTransaction.objects.create(
            wallet=self.client_wallet,
            contract=self.contract,
            transaction_type=WalletTransaction.Type.ESCROW,
            amount=Decimal("50000.00"),
            description="Escrow funding",
        )
        self.dispute = ContractDispute.objects.create(
            contract=self.contract,
            opened_by=self.client_user,
            respondent=self.tech_user,
            reason=DisputeReason.PAYMENT_OR_SETTLEMENT_ERROR,
            claimed_amount=Decimal("10000.00"),
        )
        self.refund = RefundRecord.objects.create(
            dispute=self.dispute,
            contract=self.contract,
            client=self.client_user,
            amount=Decimal("10000.00"),
            source_type=RefundSourceType.ESCROW,
            status=RefundStatus.COMPLETED,
            provider_reference="refund-provider-secret-9876",
            created_by=self.staff,
        )
        self.withdrawal = WithdrawalRequest.objects.create(
            user=self.tech_user,
            wallet=self.tech_wallet,
            amount=Decimal("25000.00"),
            requested_method="bank-account-private",
        )
        ActivityLog.objects.create(
            verb="withdrawal_approved",
            actor=self.staff,
            target_type="withdrawal",
            target_id=self.withdrawal.id,
            audience="admin",
            metadata={
                "reason": "reviewed",
                "amount": "25000.00",
                "previous_state": {"status": "pending"},
                "new_state": {"status": "approved"},
                "secret": "hidden",
            },
        )

    def test_admin_financial_overview_staff_allowed(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get("/api/admin/financial/overview/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("summary", response.data)
        self.assertIn("charts", response.data)

    def test_participant_denied_financial_overview(self):
        self.client.force_authenticate(self.client_user)
        response = self.client.get("/api/admin/financial/overview/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_overview_serializes_decimal_money_as_strings(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get("/api/admin/financial/overview/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data["summary"]["grossPayments"], str)
        self.assertEqual(response.data["summary"]["grossPayments"], "52500.00")

    def test_payments_list_excludes_provider_secrets(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get("/api/admin/financial/payments/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = str(response.data).lower()
        self.assertIn("provider_reference_masked", body)
        self.assertNotIn("provider-secret-reference-123456", body)
        self.assertNotIn("never-render", body)
        self.assertNotIn("metadata", body)

    def test_refunds_list_includes_reconciliation_state(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get("/api/admin/financial/refunds/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data["results"][0]
        self.assertIn("reconciliation", item)
        self.assertEqual(item["amount"], "10000.00")

    def test_ledger_list_is_read_only(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post("/api/admin/financial/ledger/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_withdrawal_review_requires_reason(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            f"/api/admin/finance/withdrawals/{self.withdrawal.id}/approve/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reason", response.data)

    def test_financial_audit_excludes_secrets(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get("/api/admin/financial/audit/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = str(response.data).lower()
        self.assertNotIn("hidden", body)
        self.assertNotIn("secret", body)

    def test_pagination_enforced(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get("/api/admin/financial/payments/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertIn("count", response.data)
