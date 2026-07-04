"""Serializer tests for ServiceRequest — field validation, technician resolution, private fields."""

from django.test import TestCase
from django.contrib.auth import get_user_model

from accounts.models import ClientProfile, TechnicianProfile
from servicerequest.models import ServiceRequest
from servicerequest.serializers import (
    ServiceRequestCreateSerializer,
    ServiceRequestListSerializer,
    ServiceRequestDetailSerializer,
    ClientBasicSerializer,
    TechnicianBasicSerializer,
)

User = get_user_model()


class ServiceRequestCreateSerializerTest(TestCase):
    """Test creation serializer — technician UUID resolution, validation."""

    def setUp(self):
        self.client_user = User.objects.create_user(
            username="cs_client", email="cs_c@t.com", password="pass123",
            role="client", phone_number="07500000200", governorate="Baghdad",
            address="Addr",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        self.tech_user = User.objects.create_user(
            username="cs_tech", email="cs_t@t.com", password="pass123",
            role="technician", phone_number="07500000201", governorate="Baghdad",
            address="Addr",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user,
            job_title="Tech", about="Test", years_of_expertise=3,
            approved=True, is_available=True,
        )

    def _valid_data(self):
        return {
            "technician": str(self.tech_user.id),
            "title": "Fix my AC",
            "description": "The air conditioner is not cooling properly.",
        }

    def test_valid_creation_data(self):
        serializer = ServiceRequestCreateSerializer(data=self._valid_data())
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_missing_title(self):
        data = self._valid_data()
        data.pop("title")
        serializer = ServiceRequestCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_short_title(self):
        data = self._valid_data()
        data["title"] = "AB"
        serializer = ServiceRequestCreateSerializer(data=data)
        # The model has max_length=255, no min_length; this is valid
        self.assertTrue(serializer.is_valid())

    def test_missing_description(self):
        data = self._valid_data()
        data.pop("description")
        serializer = ServiceRequestCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_blank_title(self):
        data = self._valid_data()
        data["title"] = ""
        serializer = ServiceRequestCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_invalid_technician_uuid(self):
        data = self._valid_data()
        data["technician"] = "not-a-uuid"
        serializer = ServiceRequestCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_nonexistent_technician(self):
        data = self._valid_data()
        data["technician"] = "00000000-0000-0000-0000-000000000000"
        serializer = ServiceRequestCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("technician", serializer.errors)

    def test_technician_without_profile(self):
        """A user with role=technician but no TechnicianProfile."""
        no_profile_user = User.objects.create_user(
            username="cs_no_profile", email="cs_np@t.com", password="pass123",
            role="technician", phone_number="07500000202", governorate="Baghdad",
            address="Addr",
        )
        data = self._valid_data()
        data["technician"] = str(no_profile_user.id)
        serializer = ServiceRequestCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_unapproved_technician_rejected(self):
        self.tech_profile.approved = False
        self.tech_profile.save()
        data = self._valid_data()
        serializer = ServiceRequestCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_unavailable_technician_rejected(self):
        self.tech_profile.is_available = False
        self.tech_profile.save()
        data = self._valid_data()
        serializer = ServiceRequestCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_optional_fields_accepted(self):
        data = self._valid_data()
        data.update({
            "governorate": "Baghdad",
            "service_address": "123 Main St",
            "preferred_date": "2026-07-01",
            "preferred_time": "10:00",
            "is_urgent": True,
        })
        serializer = ServiceRequestCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_category_and_skill(self):
        from category.models import Category, Skill
        cat = Category.objects.create(name="HVAC", is_active=True)
        skill = Skill.objects.create(name="AC Repair", category=cat, is_active=True)
        data = self._valid_data()
        data["category"] = cat.id
        data["skill"] = skill.id
        serializer = ServiceRequestCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_client_role_not_accepted_as_technician(self):
        """A client user UUID should not resolve as a valid technician."""
        data = self._valid_data()
        data["technician"] = str(self.client_user.id)
        serializer = ServiceRequestCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_admin_role_rejected(self):
        admin_user = User.objects.create_user(
            username="cs_admin", email="cs_a@t.com", password="pass123",
            role="admin", is_staff=True,
            phone_number="07500000203", governorate="Baghdad", address="Addr",
        )
        data = self._valid_data()
        data["technician"] = str(admin_user.id)
        serializer = ServiceRequestCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_is_urgent_default_false(self):
        data = self._valid_data()
        serializer = ServiceRequestCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertNotIn("is_urgent", serializer.validated_data)


class ServiceRequestListSerializerTest(TestCase):
    """Test list serializer — private fields excluded."""

    def setUp(self):
        self.client_user = User.objects.create_user(
            username="ls_client", email="ls_c@t.com", password="pass123",
            role="client", phone_number="07500000300", governorate="Baghdad",
            address="Addr",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)
        self.tech_user = User.objects.create_user(
            username="ls_tech", email="ls_t@t.com", password="pass123",
            role="technician", phone_number="07500000301", governorate="Baghdad",
            address="Addr",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, job_title="Tech", about="Test",
            years_of_expertise=3, approved=True, is_available=True,
        )
        self.sr = ServiceRequest.objects.create(
            client=self.client_profile, technician=self.tech_profile,
            title="Test", description="Test description",
        )

    def test_list_serializer_does_not_expose_private_fields(self):
        data = ServiceRequestListSerializer(self.sr).data
        client = data.get("client", {})
        technician = data.get("technician", {})
        # Should NOT expose email or phone
        self.assertNotIn("email", client)
        self.assertNotIn("phone", client)
        self.assertNotIn("email", technician)
        self.assertNotIn("phone", technician)

    def test_list_serializer_contains_required_fields(self):
        data = ServiceRequestListSerializer(self.sr).data
        self.assertIn("id", data)
        self.assertIn("title", data)
        self.assertIn("status", data)
        self.assertIn("client", data)
        self.assertIn("technician", data)
        self.assertIn("created_at", data)


class ServiceRequestDetailSerializerTest(TestCase):
    """Test detail serializer — full safe fields."""

    def setUp(self):
        self.client_user = User.objects.create_user(
            username="ds_client", email="ds_c@t.com", password="pass123",
            role="client", phone_number="07500000400", governorate="Baghdad",
            address="Addr",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)
        self.tech_user = User.objects.create_user(
            username="ds_tech", email="ds_t@t.com", password="pass123",
            role="technician", phone_number="07500000401", governorate="Baghdad",
            address="Addr",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, job_title="Tech", about="Test",
            years_of_expertise=3, approved=True, is_available=True,
        )
        self.sr = ServiceRequest.objects.create(
            client=self.client_profile, technician=self.tech_profile,
            title="Test", description="Test description",
            service_address="123 Street",
        )

    def test_detail_serializer_excludes_private_fields(self):
        data = ServiceRequestDetailSerializer(self.sr).data
        client = data.get("client", {})
        technician = data.get("technician", {})
        self.assertNotIn("email", client)
        self.assertNotIn("phone_number", client)
        self.assertNotIn("email", technician)
        self.assertNotIn("phone_number", technician)
        self.assertNotIn("password", str(data))
