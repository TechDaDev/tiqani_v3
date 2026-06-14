"""Tests for the electronic contract signing lifecycle — freeze, OTP, sign, finalize."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from accounts.models import ClientProfile, TechnicianProfile, OTPVerification
from contract.models import (
    Contract,
)
from wallet.models import Wallet, PlatformFeeConfig

User = get_user_model()


class ElectronicContractLifecycleBase(APITestCase):
    """Shared setup for Phase 19 electronic contract tests."""

    @classmethod
    def setUpTestData(cls):
        # Fee config
        PlatformFeeConfig.objects.create(
            name="Test",
            technician_commission_rate=Decimal("10.00"),
            client_service_fee_rate=Decimal("5.00"),
        )

        # Users
        cls.client_user = User.objects.create_user(
            username="eclient", email="eclient@test.com",
            password="pass", role="client",
            phone_number="07701234567", governorate="Baghdad", address="A",
        )
        cls.tech_user = User.objects.create_user(
            username="etech", email="etech@test.com",
            password="pass", role="technician",
            phone_number="07701234568", governorate="Basra", address="B",
        )
        cls.other_user = User.objects.create_user(
            username="eother", email="eother@test.com",
            password="pass", role="client",
            phone_number="07701234569", governorate="Baghdad", address="C",
        )
        cls.admin_user = User.objects.create_superuser(
            username="eadmin", email="eadmin@test.com", password="pass",
        )

        # Profiles
        cls.client_profile = ClientProfile.objects.create(user=cls.client_user)
        cls.tech_profile = TechnicianProfile.objects.create(
            user=cls.tech_user, approved=True, job_title="Dev",
            years_of_expertise=3,
        )
        TechnicianProfile.objects.filter(pk=cls.tech_profile.pk).update(is_complete=True)

        # Wallets — fund both participants adequately
        for u in [cls.client_user, cls.tech_user]:
            Wallet.objects.get_or_create(user=u)
        Wallet.objects.filter(user=cls.client_user).update(balance=Decimal("600000"))
        Wallet.objects.filter(user=cls.tech_user).update(balance=Decimal("60000"))

        # Contract ready for acceptance flow
        cls.contract = Contract.objects.create(
            client=cls.client_profile,
            technician=cls.tech_profile,
            work_description="Phase 19 test contract for electronic signatures",
            agreed_amount=Decimal("500000.00"),
            stage_number=3,
            start_date=timezone.now().date(),
            duration_days=15,
        )
        cls.contract.save()  # moves to pending_acceptance

    def setUp(self):
        self.api = APIClient()

    def _accept_as(self, user):
        self.api.force_authenticate(user=user)
        resp = self.api.post(f"/api/contracts/{self.contract.id}/accept/")
        self.api.force_authenticate(user=None)
        self.contract.refresh_from_db()
        return resp

    def _freeze(self, user):
        self.api.force_authenticate(user=user)
        resp = self.api.post(f"/api/contracts/{self.contract.id}/freeze/")
        self.api.force_authenticate(user=None)
        return resp

    def _sign_as(self, user, otp_code):
        self.api.force_authenticate(user=user)
        resp = self.api.post(f"/api/contracts/{self.contract.id}/sign/",
                             {"otp_code": otp_code}, format="json")
        self.api.force_authenticate(user=None)
        return resp

    def _finalize(self, user):
        self.api.force_authenticate(user=user)
        resp = self.api.post(f"/api/contracts/{self.contract.id}/finalize/")
        self.api.force_authenticate(user=None)
        return resp


class LifecycleFlowTest(ElectronicContractLifecycleBase):
    """Test the complete lifecycle — uses services directly for reliability."""

    def test_acceptance_moves_to_pending_signatures(self):
        from contract.services import accept_contract
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "pending_acceptance")

        accept_contract(self.contract, self.client_user)
        self.contract.refresh_from_db()
        self.assertTrue(self.contract.client_accepted)
        self.assertEqual(self.contract.status, "pending_acceptance")

        accept_contract(self.contract, self.tech_user)
        self.contract.refresh_from_db()
        self.assertTrue(self.contract.technician_accepted)
        self.assertEqual(self.contract.status, "pending_signatures")
        self.assertEqual(self.contract.escrow_amount, 0)

    def test_one_signature_insufficient(self):
        from contract.services import accept_contract, freeze_contract_version, sign_contract_version
        accept_contract(self.contract, self.client_user)
        accept_contract(self.contract, self.tech_user)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "pending_signatures")

        version = freeze_contract_version(self.contract, self.client_user)
        otp = OTPVerification.generate_otp(self.client_user)
        sign_contract_version(self.contract, self.client_user, otp.otp_code)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "pending_signatures")

    def test_both_signatures_move_to_pending_finalization(self):
        from contract.services import accept_contract, sign_contract_version
        accept_contract(self.contract, self.client_user)
        accept_contract(self.contract, self.tech_user)

        otp1 = OTPVerification.generate_otp(self.client_user)
        sign_contract_version(self.contract, self.client_user, otp1.otp_code)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "pending_signatures")

        otp2 = OTPVerification.generate_otp(self.tech_user)
        sign_contract_version(self.contract, self.tech_user, otp2.otp_code)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "pending_finalization")

    def test_full_finalization_moves_to_in_progress(self):
        from contract.services import accept_contract, sign_contract_version, finalize_signed_contract
        accept_contract(self.contract, self.client_user)
        accept_contract(self.contract, self.tech_user)

        otp1 = OTPVerification.generate_otp(self.client_user)
        sign_contract_version(self.contract, self.client_user, otp1.otp_code)
        otp2 = OTPVerification.generate_otp(self.tech_user)
        sign_contract_version(self.contract, self.tech_user, otp2.otp_code)

        result = finalize_signed_contract(self.contract, self.client_user)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "in_progress")
        self.assertIsNotNone(self.contract.finalized_at)
        self.assertGreater(self.contract.escrow_amount, 0)

    def test_no_wallet_charge_on_acceptance(self):
        from contract.services import accept_contract
        bal_before = self.client_user.wallet.balance
        accept_contract(self.contract, self.client_user)
        accept_contract(self.contract, self.tech_user)
        self.contract.refresh_from_db()
        bal_after = self.client_user.wallet.balance
        self.assertEqual(bal_before, bal_after)

    def test_escrow_and_fees_charged_once(self):
        from contract.services import accept_contract, sign_contract_version, finalize_signed_contract
        accept_contract(self.contract, self.client_user)
        accept_contract(self.contract, self.tech_user)

        otp1 = OTPVerification.generate_otp(self.client_user)
        sign_contract_version(self.contract, self.client_user, otp1.otp_code)
        otp2 = OTPVerification.generate_otp(self.tech_user)
        sign_contract_version(self.contract, self.tech_user, otp2.otp_code)

        r1 = finalize_signed_contract(self.contract, self.client_user)
        self.contract.refresh_from_db()
        escrow_first = self.contract.escrow_amount
        self.assertGreater(escrow_first, 0)

        r2 = finalize_signed_contract(self.contract, self.client_user)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.escrow_amount, escrow_first)

        from wallet.models import PaymentIntent, ContractPaymentBreakdown
        self.assertEqual(PaymentIntent.objects.filter(contract=self.contract).count(), 1)
        self.assertEqual(ContractPaymentBreakdown.objects.filter(contract=self.contract).count(), 1)


class OTPValidationTest(ElectronicContractLifecycleBase):
    """OTP signing validation — uses services directly."""

    def _setup(self):
        from contract.services import accept_contract
        accept_contract(self.contract, self.client_user)
        accept_contract(self.contract, self.tech_user)
        self.contract.refresh_from_db()

    def test_valid_otp_signs_successfully(self):
        from contract.services import sign_contract_version
        self._setup()
        otp = OTPVerification.generate_otp(self.client_user)
        sig = sign_contract_version(self.contract, self.client_user, otp.otp_code)
        self.assertIsNotNone(sig.signature_hash)

    def test_invalid_otp_rejected(self):
        from contract.services import sign_contract_version
        self._setup()
        with self.assertRaises(ValueError):
            sign_contract_version(self.contract, self.client_user, "000000")

    def test_expired_otp_rejected(self):
        from contract.services import sign_contract_version
        self._setup()
        otp = OTPVerification.generate_otp(self.client_user)
        otp.created_at = timezone.now() - timezone.timedelta(minutes=15)
        otp.save(update_fields=["created_at"])
        with self.assertRaises(ValueError):
            sign_contract_version(self.contract, self.client_user, otp.otp_code)

    def test_unrelated_user_cannot_sign(self):
        from contract.services import sign_contract_version
        self._setup()
        otp = OTPVerification.generate_otp(self.client_user)
        with self.assertRaises(PermissionError):
            sign_contract_version(self.contract, self.other_user, otp.otp_code)

    def test_user_signs_correct_role(self):
        from contract.services import sign_contract_version
        self._setup()
        otp = OTPVerification.generate_otp(self.tech_user)
        sig = sign_contract_version(self.contract, self.tech_user, otp.otp_code)
        self.assertEqual(sig.signer_role, "technician")

    def test_used_otp_cannot_be_reused(self):
        from contract.services import sign_contract_version
        self._setup()
        otp = OTPVerification.generate_otp(self.client_user)
        sign_contract_version(self.contract, self.client_user, otp.otp_code)
        with self.assertRaises(ValueError):
            sign_contract_version(self.contract, self.client_user, otp.otp_code)


class PermissionTest(ElectronicContractLifecycleBase):
    """Permission checks for Phase 19 endpoints."""

    def test_unrelated_user_cannot_freeze(self):
        from contract.services import accept_contract, freeze_contract_version
        accept_contract(self.contract, self.client_user)
        accept_contract(self.contract, self.tech_user)
        with self.assertRaises(PermissionError):
            freeze_contract_version(self.contract, self.other_user)

    def test_unauthenticated_cannot_access_documents(self):
        resp = self.api.get(f"/api/contracts/{self.contract.id}/documents/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_cannot_access_final_document(self):
        resp = self.api.get(f"/api/contracts/{self.contract.id}/documents/final/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_public_verify_no_auth_required(self):
        resp = self.api.get("/api/contracts/verify/NONEXISTENT/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_public_verify_pdf_no_auth_required(self):
        from io import BytesIO
        dummy_pdf = BytesIO(b"%PDF-1.4 fake pdf content for testing")
        resp = self.api.post("/api/contracts/verify-pdf/", {"file": dummy_pdf}, format="multipart")
        self.assertIn(resp.status_code, (status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST))
