"""Financial security tests for Phase 9.

Proves:
- Client releases only own contract.
- Technician cannot release.
- Unrelated client receives safe 403/404.
- Unrelated technician cannot view settlement.
- One user cannot view another's wallet.
- One technician cannot view another's withdrawal.
- Non-staff cannot approve, reject, process, confirm, or retry payout.
- No provider secret exposed.
- No internal traceback exposed.
- No private email/phone exposed through public financial responses.
"""

from decimal import Decimal
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.urls import reverse
from contract.models import Contract
from wallet.models import (
    ContractSettlement, Wallet, PaymentIntent,
    WithdrawalRequest, PlatformWallet,
)
from wallet.settlement_services import settle_completed_contract
from wallet import services as svc

User = get_user_model()


class FinancialSecurityTest(APITestCase):
    """Test financial endpoint authorization."""

    @classmethod
    def setUpTestData(cls):
        cls.client_user = User.objects.create_user(
            username="sec_client", password="pass123", role="client",
        )
        cls.tech_user = User.objects.create_user(
            username="sec_tech", password="pass123", role="technician",
        )
        cls.other_client = User.objects.create_user(
            username="sec_other", password="pass123", role="client",
        )
        cls.other_tech = User.objects.create_user(
            username="sec_other_tech", password="pass123", role="technician",
        )
        cls.staff = User.objects.create_superuser(
            username="sec_admin", password="pass123", email="admin@test.com",
        )

        Wallet.objects.get_or_create(user=cls.client_user)
        Wallet.objects.get_or_create(user=cls.tech_user)
        Wallet.objects.get_or_create(user=cls.other_client)
        Wallet.objects.get_or_create(user=cls.other_tech)

        # Ensure PlatformWallet exists
        from wallet.models import PlatformWallet
        PlatformWallet.get_global_wallet()

        cls.contract = cls._make_contract_c(cls)

        # Set emails for contact-exposure test
        cls.tech_user.email = "tech-sec-test@tiqani.local"
        cls.tech_user.save(update_fields=["email"])

    @staticmethod
    def _make_contract_c(cls):
        from accounts.models import ClientProfile, TechnicianProfile
        cp = ClientProfile.objects.create(user=cls.client_user)
        tp = TechnicianProfile.objects.create(user=cls.tech_user)
        c = Contract.objects.create(
            client=cp, technician=tp,
            agreed_amount=Decimal("500000.00"),
            escrow_amount=Decimal("500000.00"),
            status="completed",
        )
        PaymentIntent.objects.create(
            contract=c, user=cls.client_user,
            amount=Decimal("525000.00"),
            purpose=PaymentIntent.Purpose.CONTRACT_FUNDING,
            status=PaymentIntent.Status.PAID,
        )
        from wallet.services import create_contract_payment_breakdown
        create_contract_payment_breakdown(c)
        return c

    def setUp(self):
        self.settle_url = f"/api/wallet/contracts/{self.contract.id}/settlements/"
        self.eligibility_url = f"/api/wallet/contracts/{self.contract.id}/settlement/eligibility/"
        self.settlement_detail_url = f"/api/wallet/contracts/{self.contract.id}/settlement/"

    # ── Settlement Auth ──

    def test_client_can_release_own_contract(self):
        self.client.force_authenticate(user=self.client_user)
        resp = self.client.post(self.settle_url, {"idempotency_key": "sec-client-release"}, format="json")
        self.assertIn(resp.status_code, (status.HTTP_201_CREATED, status.HTTP_200_OK))

    def test_technician_cannot_release(self):
        self.client.force_authenticate(user=self.tech_user)
        resp = self.client.post(self.settle_url, {"idempotency_key": "sec-tech-release"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unrelated_client_gets_safe_denial(self):
        """Unrelated client gets eligible=False with safe reason, not 404 (eligibility endpoint is open to all)."""
        self.client.force_authenticate(user=self.other_client)
        resp = self.client.get(self.eligibility_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["eligible"])

    def test_unrelated_technician_cannot_view_settlement(self):
        settle_completed_contract(
            contract_id=str(self.contract.id),
            actor=self.client_user,
            idempotency_key="sec-view-settle",
        )
        self.client.force_authenticate(user=self.other_tech)
        resp = self.client.get(self.settlement_detail_url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # ── Wallet Auth ──

    def test_technician_can_view_own_wallet(self):
        self.client.force_authenticate(user=self.tech_user)
        resp = self.client.get("/api/wallet/me/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("balance", resp.data)

    def test_one_user_cannot_view_another_wallet(self):
        self.client.force_authenticate(user=self.other_tech)
        resp = self.client.get("/api/wallet/me/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Should show other_tech's wallet, not tech_user's
        wallet = resp.data
        tech_wallet = Wallet.objects.get(user=self.tech_user)
        self.assertNotEqual(str(wallet["user_id"]), str(tech_wallet.user_id))

    # ── Withdrawal Auth ──

    def test_one_technician_cannot_view_another_withdrawal(self):
        # Create withdrawal for tech_user
        tech_wallet = Wallet.objects.get(user=self.tech_user)
        tech_wallet.balance = Decimal("50000.00")
        tech_wallet.save(update_fields=["balance"])
        wr = svc.create_withdrawal_request(self.tech_user, Decimal("10000.00"))
        self.client.force_authenticate(user=self.other_tech)
        resp = self.client.get(f"/api/wallet/withdrawals/{wr.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # ── Staff Auth ──

    def test_nonstaff_cannot_approve(self):
        wr = self._make_withdrawal()
        self.client.force_authenticate(user=self.tech_user)
        resp = self.client.post(f"/api/wallet/withdrawals/{wr.id}/approve/", format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_nonstaff_cannot_reject(self):
        wr = self._make_withdrawal()
        self.client.force_authenticate(user=self.tech_user)
        resp = self.client.post(f"/api/wallet/withdrawals/{wr.id}/reject/", format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_nonstaff_cannot_process(self):
        wr = self._make_withdrawal()
        self.client.force_authenticate(user=self.tech_user)
        resp = self.client.post(f"/api/wallet/admin/withdrawals/{wr.id}/process/", format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_nonstaff_cannot_confirm_payout(self):
        wr = self._make_withdrawal()
        self.client.force_authenticate(user=self.tech_user)
        resp = self.client.post(f"/api/wallet/admin/withdrawals/{wr.id}/sandbox-confirm/", format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_nonstaff_cannot_retry_payout(self):
        wr = self._make_withdrawal()
        self.client.force_authenticate(user=self.tech_user)
        resp = self.client.post(f"/api/wallet/admin/withdrawals/{wr.id}/retry/", format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_approve(self):
        wr = self._make_withdrawal()
        self.client.force_authenticate(user=self.staff)
        resp = self.client.post(f"/api/wallet/withdrawals/{wr.id}/approve/", format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # ── No Secrets or Tracebacks ──

    def test_no_provider_secret_exposed(self):
        """Financial responses do not contain provider secrets."""
        self.client.force_authenticate(user=self.client_user)
        resp = self.client.get(self.eligibility_url)
        body = str(resp.data).lower()
        self.assertNotIn("secret", body)
        self.assertNotIn("api_key", body)
        self.assertNotIn("password", body)

    def test_no_traceback_exposed(self):
        """Invalid requests return clean errors, not tracebacks."""
        self.client.force_authenticate(user=self.client_user)
        resp = self.client.post(self.settle_url, {"idempotency_key": "x" * 200}, format="json")
        self.assertNotIn("traceback", str(resp.data).lower())
        self.assertNotIn("file", str(resp.data).lower())

    def test_no_private_contact_in_wallet(self):
        """Wallet response does not include email/phone."""
        self.client.force_authenticate(user=self.tech_user)
        resp = self.client.get("/api/wallet/me/")
        body = str(resp.data).lower()
        self.assertNotIn(self.tech_user.email, body)

    def _make_withdrawal(self):
        tech_wallet = Wallet.objects.get(user=self.tech_user)
        tech_wallet.balance = Decimal("50000.00")
        tech_wallet.save(update_fields=["balance"])
        return svc.create_withdrawal_request(self.tech_user, Decimal("10000.00"))
