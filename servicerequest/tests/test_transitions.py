"""State transition tests for ServiceRequest — valid and invalid transitions via API."""

from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model

from accounts.models import ClientProfile, TechnicianProfile
from servicerequest.models import ServiceRequest

User = get_user_model()


class ServiceRequestTransitionTest(APITestCase):
    """Test all valid and invalid status transitions via API endpoints."""

    def setUp(self):
        self.api = APIClient()
        self.client_user = User.objects.create_user(
            username="tr_client", email="tr_c@t.com", password="pass123",
            role="client", phone_number="07500000700", governorate="Baghdad",
            address="Addr",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)
        self.tech_user = User.objects.create_user(
            username="tr_tech", email="tr_t@t.com", password="pass123",
            role="technician", phone_number="07500000701", governorate="Baghdad",
            address="Addr",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, job_title="Tech", about="Test",
            years_of_expertise=3, approved=True, is_available=True,
        )

    def _auth_client(self):
        self.api.force_authenticate(user=self.client_user)

    def _auth_tech(self):
        self.api.force_authenticate(user=self.tech_user)

    def _new_pending(self):
        return ServiceRequest.objects.create(
            client=self.client_profile, technician=self.tech_profile,
            title="Transitions", description="Test transitions",
        )

    # ---- Valid client transitions ----

    def test_pending_cancel_via_api(self):
        self._auth_client()
        sr = self._new_pending()
        response = self.api.post(f"/api/requests/{sr.id}/cancel/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "CANCELLED")

    def test_pending_withdraw_via_api(self):
        self._auth_client()
        sr = self._new_pending()
        response = self.api.post(f"/api/requests/{sr.id}/withdraw/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "WITHDRAWN")

    # ---- Valid technician transitions ----

    def test_pending_accept_via_api(self):
        self._auth_tech()
        sr = self._new_pending()
        response = self.api.post(f"/api/technician/requests/{sr.id}/accept/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ACCEPTED")

    def test_pending_decline_via_api(self):
        self._auth_tech()
        sr = self._new_pending()
        response = self.api.post(f"/api/technician/requests/{sr.id}/decline/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "DECLINED")

    # ---- Invalid client transitions ----

    def test_cancel_accepted_returns_409(self):
        self._auth_client()
        sr = self._new_pending()
        sr.status = ServiceRequest.Status.ACCEPTED
        sr.save()
        response = self.api.post(f"/api/requests/{sr.id}/cancel/")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_cancel_declined_returns_409(self):
        self._auth_client()
        sr = self._new_pending()
        sr.status = ServiceRequest.Status.DECLINED
        sr.save()
        response = self.api.post(f"/api/requests/{sr.id}/cancel/")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_cancel_cancelled_returns_409(self):
        self._auth_client()
        sr = self._new_pending()
        sr.status = ServiceRequest.Status.CANCELLED
        sr.save()
        response = self.api.post(f"/api/requests/{sr.id}/cancel/")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_cancel_withdrawn_returns_409(self):
        self._auth_client()
        sr = self._new_pending()
        sr.status = ServiceRequest.Status.WITHDRAWN
        sr.save()
        response = self.api.post(f"/api/requests/{sr.id}/cancel/")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_withdraw_accepted_returns_409(self):
        self._auth_client()
        sr = self._new_pending()
        sr.status = ServiceRequest.Status.ACCEPTED
        sr.save()
        response = self.api.post(f"/api/requests/{sr.id}/withdraw/")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_withdraw_declined_returns_409(self):
        self._auth_client()
        sr = self._new_pending()
        sr.status = ServiceRequest.Status.DECLINED
        sr.save()
        response = self.api.post(f"/api/requests/{sr.id}/withdraw/")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    # ---- Invalid technician transitions ----

    def test_accept_cancelled_returns_409(self):
        self._auth_tech()
        sr = self._new_pending()
        sr.status = ServiceRequest.Status.CANCELLED
        sr.save()
        response = self.api.post(f"/api/technician/requests/{sr.id}/accept/")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_accept_withdrawn_returns_409(self):
        self._auth_tech()
        sr = self._new_pending()
        sr.status = ServiceRequest.Status.WITHDRAWN
        sr.save()
        response = self.api.post(f"/api/technician/requests/{sr.id}/accept/")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_decline_accepted_returns_409(self):
        self._auth_tech()
        sr = self._new_pending()
        sr.status = ServiceRequest.Status.ACCEPTED
        sr.save()
        response = self.api.post(f"/api/technician/requests/{sr.id}/decline/")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_accept_after_decline_returns_409(self):
        self._auth_tech()
        sr = self._new_pending()
        sr.status = ServiceRequest.Status.DECLINED
        sr.save()
        response = self.api.post(f"/api/technician/requests/{sr.id}/accept/")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_decline_after_accept_returns_409(self):
        self._auth_tech()
        sr = self._new_pending()
        sr.status = ServiceRequest.Status.ACCEPTED
        sr.save()
        response = self.api.post(f"/api/technician/requests/{sr.id}/decline/")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    # ---- Duplicate transitions ----

    def test_duplicate_accept_returns_409(self):
        self._auth_tech()
        sr = self._new_pending()
        self.api.post(f"/api/technician/requests/{sr.id}/accept/")
        response = self.api.post(f"/api/technician/requests/{sr.id}/accept/")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_duplicate_decline_returns_409(self):
        self._auth_tech()
        sr = self._new_pending()
        self.api.post(f"/api/technician/requests/{sr.id}/decline/")
        response = self.api.post(f"/api/technician/requests/{sr.id}/decline/")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_duplicate_cancel_returns_409(self):
        self._auth_client()
        sr = self._new_pending()
        self.api.post(f"/api/requests/{sr.id}/cancel/")
        response = self.api.post(f"/api/requests/{sr.id}/cancel/")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_duplicate_withdraw_returns_409(self):
        self._auth_client()
        sr = self._new_pending()
        self.api.post(f"/api/requests/{sr.id}/withdraw/")
        response = self.api.post(f"/api/requests/{sr.id}/withdraw/")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
