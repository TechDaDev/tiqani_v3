import shutil
import tempfile
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from wallet.models import Wallet, WalletRechargeRequest, WalletTransaction

User = get_user_model()


def receipt_file(name="receipt.jpg", content=b"receipt-bytes", content_type="image/jpeg"):
    return SimpleUploadedFile(name, content, content_type=content_type)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class WalletRechargeRequestApiTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        media_root = getattr(cls, "_overridden_settings", {}).get("MEDIA_ROOT")
        super().tearDownClass()
        if media_root:
            shutil.rmtree(media_root, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user(
            username="wallet-client",
            email="wallet-client@example.com",
            password="pass12345",
            role="client",
        )
        self.other_user = User.objects.create_user(
            username="other-client",
            email="other-client@example.com",
            password="pass12345",
            role="client",
        )
        self.finance = User.objects.create_superuser(
            username="finance-admin",
            email="finance-admin@example.com",
            password="pass12345",
        )
        self.staff_not_finance = User.objects.create_user(
            username="support-staff",
            email="support-staff@example.com",
            password="pass12345",
            is_staff=True,
        )
        self.wallet, _ = Wallet.objects.get_or_create(user=self.user)
        self.wallet.balance = Decimal("1000.00")
        self.wallet.save(update_fields=["balance"])

    def create_request(self, user=None, amount="25000.00", file_name="receipt.jpg"):
        self.client.force_authenticate(user or self.user)
        return self.client.post(
            "/api/wallet/recharge-requests/",
            {
                "amount": amount,
                "note": "bank transfer",
                "receipt_file": receipt_file(file_name),
            },
            format="multipart",
        )

    def test_user_creates_recharge_request_with_valid_receipt(self):
        response = self.create_request()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], WalletRechargeRequest.Status.PENDING_REVIEW)
        self.assertEqual(response.data["amount"], "25000.00")
        self.assertIn("/api/wallet/recharge-requests/", response.data["receipt_download_url"])

        obj = WalletRechargeRequest.objects.get(id=response.data["id"])
        self.assertEqual(obj.original_filename, "receipt.jpg")
        self.assertEqual(obj.mime_type, "image/jpeg")

    def test_invalid_file_type_rejected(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/wallet/recharge-requests/",
            {
                "amount": "25000.00",
                "receipt_file": receipt_file("receipt.exe", b"bad", "application/x-msdownload"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("receipt_file", response.data)

    def test_oversized_file_rejected(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/wallet/recharge-requests/",
            {
                "amount": "25000.00",
                "receipt_file": receipt_file("receipt.pdf", b"x" * (6 * 1024 * 1024), "application/pdf"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("receipt_file", response.data)

    def test_amount_must_be_positive(self):
        response = self.create_request(amount="0.00")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("amount", response.data)

    def test_second_pending_request_rejected(self):
        first = self.create_request(file_name="first.jpg")
        second = self.create_request(file_name="second.jpg")

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            WalletRechargeRequest.objects.filter(
                user=self.user,
                status=WalletRechargeRequest.Status.PENDING_REVIEW,
            ).count(),
            1,
        )

    def test_user_lists_only_own_requests(self):
        own = self.create_request(user=self.user, file_name="own.jpg")
        other = self.create_request(user=self.other_user, file_name="other.jpg")
        self.assertEqual(own.status_code, status.HTTP_201_CREATED)
        self.assertEqual(other.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(self.user)
        response = self.client.get("/api/wallet/recharge-requests/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], own.data["id"])

    def test_unrelated_user_cannot_access_request_or_receipt(self):
        created = self.create_request(user=self.user)
        self.client.force_authenticate(self.other_user)

        detail = self.client.get(f"/api/wallet/recharge-requests/{created.data['id']}/")
        receipt = self.client.get(f"/api/wallet/recharge-requests/{created.data['id']}/receipt/")

        self.assertEqual(detail.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(receipt.status_code, status.HTTP_404_NOT_FOUND)

    def test_finance_lists_pending_requests(self):
        self.create_request(user=self.user)
        self.client.force_authenticate(self.finance)
        response = self.client.get(
            f"/api/admin/financial/recharge-requests/?status={WalletRechargeRequest.Status.PENDING_REVIEW}"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["count"], 1)
        self.assertIn("receipt_download_url", response.data["results"][0])

    def test_approval_creates_one_confirmed_wallet_credit_and_is_idempotent(self):
        created = self.create_request(user=self.user)
        approve_url = f"/api/admin/financial/recharge-requests/{created.data['id']}/approve/"
        self.client.force_authenticate(self.finance)

        first = self.client.post(approve_url, {"review_note": "matched bank receipt"}, format="json")
        second = self.client.post(approve_url, {"review_note": "duplicate click"}, format="json")

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("26000.00"))
        self.assertEqual(
            WalletTransaction.objects.filter(
                wallet=self.wallet,
                transaction_type=WalletTransaction.Type.DEPOSIT,
                amount=Decimal("25000.00"),
            ).count(),
            1,
        )

    def test_rejection_does_not_change_wallet_balance(self):
        created = self.create_request(user=self.user)
        self.client.force_authenticate(self.finance)

        response = self.client.post(
            f"/api/admin/financial/recharge-requests/{created.data['id']}/reject/",
            {"review_note": "receipt unreadable"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("1000.00"))
        self.assertEqual(response.data["status"], WalletRechargeRequest.Status.REJECTED)

    def test_non_finance_cannot_approve_or_reject(self):
        created = self.create_request(user=self.user)
        self.client.force_authenticate(self.staff_not_finance)

        approve = self.client.post(
            f"/api/admin/financial/recharge-requests/{created.data['id']}/approve/",
            {"review_note": "no"},
            format="json",
        )
        reject = self.client.post(
            f"/api/admin/financial/recharge-requests/{created.data['id']}/reject/",
            {"review_note": "no"},
            format="json",
        )

        self.assertEqual(approve.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(reject.status_code, status.HTTP_403_FORBIDDEN)

    def test_receipt_endpoint_hides_raw_file_path(self):
        created = self.create_request(user=self.user)
        self.client.force_authenticate(self.finance)

        response = self.client.get(
            f"/api/admin/financial/recharge-requests/{created.data['id']}/receipt/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertNotIn("wallet/recharge_receipts", str(response.headers))

    def test_overview_includes_recharge_counts_and_totals(self):
        created = self.create_request(user=self.user)
        self.client.force_authenticate(self.finance)
        self.client.post(
            f"/api/admin/financial/recharge-requests/{created.data['id']}/approve/",
            {"review_note": "matched"},
            format="json",
        )

        response = self.client.get("/api/admin/financial/overview/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["summary"]["approvedWalletRecharges"], "25000.00")
        self.assertEqual(response.data["counts"]["walletRechargeRequestsApproved"], 1)
