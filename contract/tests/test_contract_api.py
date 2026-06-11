"""Tests for contract lifecycle API endpoints."""

from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import ClientProfile, TechnicianProfile
from contract.models import Contract, ContractStage, TimeExtensionRequest
from wallet.models import Wallet, WalletTransaction

User = get_user_model()


class ContractApiTestBase(APITestCase):
    """Base setup with client, technician, funded wallets."""

    def setUp(self):
        self.client_api = APIClient()

        # Create client user + profile
        self.client_user = User.objects.create_user(
            username="client1", email="client@test.com",
            password="pass123", role="client",
            phone_number="07701234567", governorate="Baghdad", address="Addr",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        # Create technician user + profile
        self.tech_user = User.objects.create_user(
            username="tech1", email="tech@test.com",
            password="pass123", role="technician",
            phone_number="07701234568", governorate="Basra", address="Addr2",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, approved=True,
            job_title="Plumber", about="Expert", years_of_expertise=5,
        )
        TechnicianProfile.objects.filter(pk=self.tech_profile.pk).update(is_complete=True)

        # Create unapproved technician
        self.unapproved_user = User.objects.create_user(
            username="unapproved", email="unapproved@test.com",
            password="pass123", role="technician",
            phone_number="07701234569", governorate="Baghdad", address="Addr3",
        )
        self.unapproved_profile = TechnicianProfile.objects.create(
            user=self.unapproved_user, approved=False,
        )

        # Create unrelated user
        self.other_user = User.objects.create_user(
            username="other", email="other@test.com",
            password="pass123", role="client",
            phone_number="07701234560", governorate="Najaf", address="Addr4",
        )
        ClientProfile.objects.create(user=self.other_user)

        # Fund wallets (enough for escrow + 10% fee each side)
        self._fund_wallet(self.client_user, Decimal("5000.00"))
        self._fund_wallet(self.tech_user, Decimal("1000.00"))

    def _fund_wallet(self, user, amount):
        """Create Wallet record with initial balance."""
        wallet, _ = Wallet.objects.get_or_create(user=user)
        wallet.balance = amount
        wallet.save(update_fields=["balance"])


class ContractListCreateTest(ContractApiTestBase):
    """Tests for GET/POST /api/contracts/."""

    def test_anonymous_cannot_list(self):
        resp = self.client_api.get("/api/contracts/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_client_sees_own_contracts(self):
        self.client_api.force_authenticate(user=self.client_user)
        c = Contract.objects.create(client=self.client_profile, technician=self.tech_profile)
        resp = self.client_api.get("/api/contracts/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_technician_sees_own_contracts(self):
        self.client_api.force_authenticate(user=self.tech_user)
        c = Contract.objects.create(client=self.client_profile, technician=self.tech_profile)
        resp = self.client_api.get("/api/contracts/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_unrelated_user_cannot_see_contract(self):
        self.client_api.force_authenticate(user=self.other_user)
        c = Contract.objects.create(client=self.client_profile, technician=self.tech_profile)
        resp = self.client_api.get("/api/contracts/")
        self.assertEqual(len(resp.data), 0)

    def test_client_can_create_draft(self):
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.post("/api/contracts/", {
            "technician_id": str(self.tech_user.id),
            "work_description": "Fix leaky pipe",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["status"], "draft")

    def test_anonymous_cannot_create(self):
        resp = self.client_api.post("/api/contracts/", {
            "technician_id": str(self.tech_user.id),
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_technician_cannot_create_contract(self):
        self.client_api.force_authenticate(user=self.tech_user)
        resp = self.client_api.post("/api/contracts/", {
            "technician_id": str(self.client_user.id),
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_create_with_unapproved_technician(self):
        """The serializer checks is_available; unapproved is also not available."""
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.post("/api/contracts/", {
            "technician_id": str(self.unapproved_user.id),
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class ContractProposalTest(ContractApiTestBase):
    """Tests for PATCH proposal on draft contract."""

    def setUp(self):
        super().setUp()
        self.contract = Contract.objects.create(
            client=self.client_profile, technician=self.tech_profile,
            work_description="Initial request",
        )
        self.url = f"/api/contracts/{self.contract.id}/"

    def test_technician_can_update_proposal(self):
        self.client_api.force_authenticate(user=self.tech_user)
        resp = self.client_api.patch(self.url, {
            "work_description": "Detailed fix",
            "agreed_amount": "1000.00",
            "duration_days": 10,
            "start_date": "2026-06-15",
            "stage_number": 3,
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.agreed_amount, Decimal("1000.00"))

    def test_proposal_completion_moves_to_pending_acceptance(self):
        self.client_api.force_authenticate(user=self.tech_user)
        self.client_api.patch(self.url, {
            "work_description": "Full proposal",
            "agreed_amount": "1000.00",
            "duration_days": 10,
            "start_date": "2026-06-15",
            "stage_number": 3,
        }, format="json")
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "pending_acceptance")

    def test_client_cannot_set_proposal_fields(self):
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.patch(self.url, {"agreed_amount": "500.00"}, format="json")
        # Client should get 403 because PATCH is technician-only
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unrelated_technician_cannot_update(self):
        other_tech = User.objects.create_user(
            username="othertech", email="ot@test.com",
            password="pass123", role="technician",
        )
        TechnicianProfile.objects.create(user=other_tech, approved=True)
        self.client_api.force_authenticate(user=other_tech)
        resp = self.client_api.patch(self.url, {"agreed_amount": "500.00"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class ContractAcceptTest(ContractApiTestBase):
    """Tests for accepting contracts."""

    def setUp(self):
        super().setUp()
        self.contract = Contract.objects.create(
            client=self.client_profile, technician=self.tech_profile,
            work_description="Test work",
            agreed_amount=Decimal("1000.00"),
            stage_number=3,
            start_date=timezone.now().date(),
            duration_days=15,
            status="pending_acceptance",
        )
        # Trigger save to set contract_duration
        self.contract.save()
        self.accept_url = f"/api/contracts/{self.contract.id}/accept/"

    def test_client_accept(self):
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.post(self.accept_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.contract.refresh_from_db()
        self.assertTrue(self.contract.client_accepted)

    def test_technician_accept(self):
        self.client_api.force_authenticate(user=self.tech_user)
        resp = self.client_api.post(self.accept_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.contract.refresh_from_db()
        self.assertTrue(self.contract.technician_accepted)

    def test_both_accept_moves_to_in_progress(self):
        # Client accepts
        self.client_api.force_authenticate(user=self.client_user)
        self.client_api.post(self.accept_url)
        self.contract.refresh_from_db()
        self.assertTrue(self.contract.client_accepted)
        self.assertEqual(self.contract.status, "pending_acceptance")

        # Technician accepts → should move to in_progress
        self.client_api.force_authenticate(user=self.tech_user)
        resp = self.client_api.post(self.accept_url)
        self.contract.refresh_from_db()
        self.assertTrue(self.contract.technician_accepted)
        self.assertEqual(self.contract.status, "in_progress")

    def test_stages_created_when_in_progress(self):
        self.client_api.force_authenticate(user=self.client_user)
        self.client_api.post(self.accept_url)
        self.client_api.force_authenticate(user=self.tech_user)
        self.client_api.post(self.accept_url)
        self.contract.refresh_from_db()
        stage_count = self.contract.stages.count()
        self.assertEqual(stage_count, 3)

    def test_escrow_created_when_in_progress(self):
        self.client_api.force_authenticate(user=self.client_user)
        self.client_api.post(self.accept_url)
        self.client_api.force_authenticate(user=self.tech_user)
        self.client_api.post(self.accept_url)
        self.contract.refresh_from_db()
        self.assertGreater(self.contract.escrow_amount, 0)

    def test_accept_idempotent(self):
        self.client_api.force_authenticate(user=self.client_user)
        resp1 = self.client_api.post(self.accept_url)
        resp2 = self.client_api.post(self.accept_url)
        self.assertEqual(resp1.status_code, status.HTTP_200_OK)

    def test_unrelated_user_cannot_accept(self):
        self.client_api.force_authenticate(user=self.other_user)
        resp = self.client_api.post(self.accept_url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class ContractCancelTest(ContractApiTestBase):
    """Tests for canceling contracts."""

    def setUp(self):
        super().setUp()
        self.contract = Contract.objects.create(
            client=self.client_profile, technician=self.tech_profile,
            work_description="Test",
        )
        self.cancel_url = f"/api/contracts/{self.contract.id}/cancel/"

    def test_client_can_cancel_draft(self):
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.post(self.cancel_url, {"reason": "Changed mind"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "canceled")

    def test_completed_contract_cannot_be_canceled(self):
        self.contract.status = "completed"
        self.contract.save()
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.post(self.cancel_url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
