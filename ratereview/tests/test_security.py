"""Security hardening tests for reviews — sensitive exposure, moderation checks, permission hardening."""

from decimal import Decimal
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import TechnicianProfile, ClientProfile, AdminProfile
from contract.models import Contract
from ratereview.models import Review

User = get_user_model()


class ReviewSensitiveExposureTest(APITestCase):
    """Public reviews do not expose reviewer emails or sensitive data."""

    def setUp(self):
        self.client_user = User.objects.create_user(
            username='rev_sec', email='reviewer-secret@t.com', password='pass123',
            role='client',
            phone_number='07700000300', governorate='Basra', address='A',
        )
        client = ClientProfile.objects.create(user=self.client_user)

        tech_user = User.objects.create_user(
            username='t_rev_sec', email='tech-secret@t.com', password='pass123',
            role='technician',
            phone_number='07700000301', governorate='Basra', address='A',
        )
        tech = TechnicianProfile.objects.create(user=tech_user, approved=True, job_title='Dev')

        contract = Contract.objects.create(
            client=client, technician=tech,
            work_description='Test', agreed_amount=Decimal('50000'),
            stage_number=2, start_date=timezone.now().date(), duration_days=7,
            status='completed',
        )

        self.review = Review.objects.create(
            reviewer=self.client_user, technician=tech, contract=contract,
            rating=4, comment='Great work!', is_public=True, is_verified=True,
        )

        self.unauth = APIClient()

    def test_public_review_does_not_expose_reviewer_email(self):
        resp = self.unauth.get(f'/api/reviews/{self.review.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # The response should not include reviewer email
        json_str = str(resp.data)
        self.assertNotIn('reviewer-secret@t.com', json_str)

    def test_public_review_does_not_expose_technician_email(self):
        resp = self.unauth.get(f'/api/reviews/{self.review.id}/')
        json_str = str(resp.data)
        self.assertNotIn('tech-secret@t.com', json_str)


class ReviewHiddenVisibilityTest(APITestCase):
    """Hidden reviews are not publicly visible."""

    def setUp(self):
        self.client_user = User.objects.create_user(
            username='rh_sec', email='rh@t.com', password='pass123',
            role='client',
            phone_number='07700000310', governorate='Basra', address='A',
        )
        client = ClientProfile.objects.create(user=self.client_user)

        tech_user = User.objects.create_user(
            username='t_rh_sec', email='trh@t.com', password='pass123',
            role='technician',
            phone_number='07700000311', governorate='Basra', address='A',
        )
        tech = TechnicianProfile.objects.create(user=tech_user, approved=True, job_title='Dev')

        contract = Contract.objects.create(
            client=client, technician=tech,
            work_description='Test', agreed_amount=Decimal('50000'),
            stage_number=2, start_date=timezone.now().date(), duration_days=7,
            status='completed',
        )

        self.public_review = Review.objects.create(
            reviewer=self.client_user, technician=tech, contract=contract,
            rating=5, comment='Visible', is_public=True,
        )
        self.hidden_review = Review.objects.create(
            reviewer=self.client_user, technician=tech, contract=None,
            rating=1, comment='Hidden', is_public=False,
        )

        self.unauth = APIClient()
        self.client_auth = APIClient()
        self.client_auth.force_authenticate(user=self.client_user)

    def test_hidden_review_not_in_public_list(self):
        url = f'/api/reviews/technician/{self.public_review.technician.id}/'
        resp = self.unauth.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get('results', resp.data)
        comments = [r.get('comment', '') for r in (results if isinstance(results, list) else [])]
        self.assertIn('Visible', comments)
        self.assertNotIn('Hidden', comments)

    def test_hidden_review_404_on_detail(self):
        resp = self.unauth.get(f'/api/reviews/{self.hidden_review.id}/')
        # Should be 404 since it's filtered by is_public=True
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_public_review_accessible(self):
        resp = self.unauth.get(f'/api/reviews/{self.public_review.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class ReviewModerationPermissionTest(APITestCase):
    """Review moderation endpoints reject non-moderators."""

    def setUp(self):
        self.mod_user = User.objects.create_user(
            username='mod_sec', email='mods@t.com', password='pass123',
            role='admin', is_staff=True,
            phone_number='07700000320', governorate='Basra', address='A',
        )
        AdminProfile.objects.create(user=self.mod_user, role=AdminProfile.AdminRole.MODERATOR)

        self.normal_user = User.objects.create_user(
            username='norm_sec', email='ns@t.com', password='pass123',
            role='client',
            phone_number='07700000321', governorate='Basra', address='A',
        )
        ClientProfile.objects.create(user=self.normal_user)

        tech_user = User.objects.create_user(
            username='t_mod_sec', email='tms@t.com', password='pass123',
            role='technician',
            phone_number='07700000322', governorate='Basra', address='A',
        )
        tech = TechnicianProfile.objects.create(user=tech_user, approved=True, job_title='Dev')

        self.review = Review.objects.create(
            reviewer=self.normal_user, technician=tech,
            rating=3, comment='Moderate me', is_public=True,
        )

        self.mod_auth = APIClient()
        self.mod_auth.force_authenticate(user=self.mod_user)
        self.norm_auth = APIClient()
        self.norm_auth.force_authenticate(user=self.normal_user)

    def test_normal_user_cannot_hide_review(self):
        resp = self.norm_auth.post(f'/api/admin/reviews/{self.review.id}/hide/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_moderator_can_hide_review(self):
        resp = self.mod_auth.post(f'/api/admin/reviews/{self.review.id}/hide/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_normal_user_cannot_verify_review(self):
        resp = self.norm_auth.post(f'/api/admin/reviews/{self.review.id}/verify/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_moderator_can_verify_review(self):
        resp = self.mod_auth.post(f'/api/admin/reviews/{self.review.id}/verify/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
