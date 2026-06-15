"""
Management command to seed reproducible E2E test fixtures.

Creates deterministic disposable users for local Playwright testing.
Refuses to run in production unless --force is passed.

Usage:
    E2E_FIXTURE_PASSWORD='local-test-only' python manage.py seed_e2e_fixtures
    E2E_FIXTURE_PASSWORD='local-test-only' python manage.py seed_e2e_fixtures --reset
    E2E_FIXTURE_PASSWORD='local-test-only' python manage.py seed_e2e_fixtures --force  # production override
"""

import os
import sys
from datetime import date
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from accounts.models import TechnicianProfile, ClientProfile, TechnicianSkillSet
from category.models import Category, Skill
from servicerequest.models import ServiceRequest

User = get_user_model()


def _running_tests():
    """Detect whether the command is running under a test runner."""
    return "test" in sys.argv or "pytest" in sys.argv[0]

# ---------------------------------------------------------------------------
# Fixture identifiers — deterministic, local-only
# ---------------------------------------------------------------------------
FIXTURE_EMAILS = {
    "client": "e2e-client@tiqani.local",
    "technician": "e2e-technician@tiqani.local",
    "approved_technician": "e2e-approved-tech@tiqani.local",
    "restricted_technician": "e2e-restricted-tech@tiqani.local",
    "second_approved": "e2e-approved-tech2@tiqani.local",
}

FIXTURE_USERNAMES = {
    "client": "e2e_client",
    "technician": "e2e_technician",
    "approved_technician": "e2e_approved_tech",
    "restricted_technician": "e2e_restricted_tech",
    "second_approved": "e2e_approved_tech2",
}

FIXTURE_FIRST_NAMES = {
    "client": "E2EClient",
    "technician": "E2ETechnician",
    "approved_technician": "E2EApproved",
    "restricted_technician": "E2ERestricted",
    "second_approved": "E2EApproved2",
}

FIXTURE_LAST_NAMES = {
    "client": "User",
    "technician": "User",
    "approved_technician": "Technician",
    "restricted_technician": "Technician",
    "second_approved": "Technician",
}

FIXTURE_ROLES = {
    "client": User.Role.CLIENT,
    "technician": User.Role.TECHNICIAN,
    "approved_technician": User.Role.TECHNICIAN,
    "restricted_technician": User.Role.TECHNICIAN,
    "second_approved": User.Role.TECHNICIAN,
}

FIXTURE_GOVERNORATES = {
    "client": "Baghdad",
    "technician": "Baghdad",
    "approved_technician": "Baghdad",
    "restricted_technician": "Basra",
    "second_approved": "Erbil",
}


def get_password():
    """Read fixture password from environment; fail with clear message if missing."""
    password = os.environ.get("E2E_FIXTURE_PASSWORD")
    if not password:
        raise CommandError(
            "E2E_FIXTURE_PASSWORD environment variable is required.\n"
            "Usage: E2E_FIXTURE_PASSWORD='local-test-only' python manage.py seed_e2e_fixtures"
        )
    return password


def is_production():
    """Heuristic: refuse to run in production unless --force is passed."""
    return not settings.DEBUG and not _running_tests()


class Command(BaseCommand):
    help = "Seed reproducible E2E test fixtures for local Playwright testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Remove all existing E2E fixtures before seeding.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Override production safety guard.",
        )

    def handle(self, *args, **options):
        if is_production() and not options.get("force"):
            raise CommandError(
                "Refusing to run in production. Set --force to override (not recommended)."
            )

        password = get_password()
        reset = options.get("reset", False)

        if reset:
            self._reset_fixtures()

        self._seed_fixtures(password)
        self._report()

    def _reset_fixtures(self):
        """Remove all E2E fixture users."""
        emails = list(FIXTURE_EMAILS.values())
        deleted, _ = User.objects.filter(email__in=emails).delete()
        self.stdout.write(self.style.WARNING(f"Removed {deleted} existing fixture(s)."))

    @transaction.atomic
    def _seed_fixtures(self, password):
        """Create or update all fixture users and requests."""
        self._create_client(password)
        self._create_technician(password)
        self._create_approved_technician(password)
        self._create_restricted_technician(password)
        self._create_second_approved_technician(password)
        self._seed_request_fixtures()

    def _get_or_create_user(self, key, password):
        """Helper to get_or_create a fixture user."""
        user, created = User.objects.update_or_create(
            username=FIXTURE_USERNAMES[key],
            defaults={
                "email": FIXTURE_EMAILS[key],
                "first_name": FIXTURE_FIRST_NAMES[key],
                "last_name": FIXTURE_LAST_NAMES[key],
                "role": FIXTURE_ROLES[key],
                "governorate": FIXTURE_GOVERNORATES[key],
                "phone_number": None,  # set per-fixture below
                "is_active": True,
                "is_staff": False,
                "is_superuser": False,
            },
        )
        if created or not user.has_usable_password():
            user.set_password(password)
            user.save(update_fields=["password"])
        return user, created

    def _create_client(self, password):
        user, created = self._get_or_create_user("client", password)
        user.phone_number = "07500000001"
        user.address = "E2E Client Address"
        user.gender = "male"
        user.date_of_birth = date(1990, 1, 15)
        user.save(update_fields=["phone_number", "address", "gender", "date_of_birth"])

        profile, _ = ClientProfile.objects.update_or_create(
            user=user,
            defaults={},
        )
        # Force is_complete=True (bypasses age + profile_image requirements)
        ClientProfile.objects.filter(pk=profile.pk).update(is_complete=True)
        status = "created" if created else "updated"
        self.stdout.write(f"  Client: {user.email} ({status})")

    def _create_technician(self, password):
        user, created = self._get_or_create_user("technician", password)
        user.phone_number = "07500000002"
        user.address = "E2E Technician Address"
        user.gender = "male"
        user.date_of_birth = date(1988, 3, 20)
        user.save(update_fields=["phone_number", "address", "gender", "date_of_birth"])

        profile, _ = TechnicianProfile.objects.update_or_create(
            user=user,
            defaults={
                "job_title": "E2E Technician",
                "about": "E2E test technician profile for seeding purposes.",
                "years_of_expertise": 5,
                "is_available": True,
                "rate": "3.50",
                "approved": True,
            },
        )
        TechnicianProfile.objects.filter(pk=profile.pk).update(is_complete=True)
        profile.refresh_from_db()
        status = "created" if created else "updated"
        self.stdout.write(f"  Technician: {user.email} ({status})")

    def _create_approved_technician(self, password):
        user, created = self._get_or_create_user("approved_technician", password)
        user.phone_number = "07500000003"
        user.address = "E2E Approved Tech Address"
        user.gender = "male"
        user.date_of_birth = date(1985, 7, 10)
        user.profile_image = None
        user.save(
            update_fields=["phone_number", "address", "gender", "date_of_birth", "profile_image"]
        )

        profile, _ = TechnicianProfile.objects.update_or_create(
            user=user,
            defaults={
                "job_title": "E2E Approved Specialist",
                "about": "Experienced technician for E2E marketplace validation.",
                "years_of_expertise": 10,
                "is_available": True,
                "rate": "4.50",
                "approved": True,
            },
        )

        # Bypass completion calculation — force is_complete=True directly
        TechnicianProfile.objects.filter(pk=profile.pk).update(is_complete=True)
        profile.refresh_from_db()

        # Attach skills/categories if any exist
        self._attach_skills(profile)

        status = "created" if created else "updated"
        self.stdout.write(f"  Approved technician: {user.email} ({status})")

    def _create_restricted_technician(self, password):
        user, created = self._get_or_create_user("restricted_technician", password)
        user.phone_number = "07500000004"
        user.address = "E2E Restricted Tech Address"
        user.gender = "female"
        user.date_of_birth = date(1992, 11, 5)
        user.save(update_fields=["phone_number", "address", "gender", "date_of_birth"])

        profile, _ = TechnicianProfile.objects.update_or_create(
            user=user,
            defaults={
                "job_title": "E2E Pending Technician",
                "about": "This technician should NOT appear in public listings.",
                "years_of_expertise": 2,
                "is_available": False,
                "rate": "0.00",
                "approved": False,
            },
        )
        status = "created" if created else "updated"
        self.stdout.write(f"  Restricted technician (unapproved): {user.email} ({status})")

    def _create_second_approved_technician(self, password):
        user, created = self._get_or_create_user("second_approved", password)
        user.phone_number = "07500000005"
        user.address = "E2E Second Approved Tech Address"
        user.gender = "female"
        user.date_of_birth = date(1990, 5, 22)
        user.save(update_fields=["phone_number", "address", "gender", "date_of_birth"])

        profile, _ = TechnicianProfile.objects.update_or_create(
            user=user,
            defaults={
                "job_title": "E2E Senior Technician",
                "about": "Second approved technician for pagination and sorting tests.",
                "years_of_expertise": 8,
                "is_available": True,
                "rate": "4.00",
                "approved": True,
            },
        )
        TechnicianProfile.objects.filter(pk=profile.pk).update(is_complete=True)
        profile.refresh_from_db()
        status = "created" if created else "updated"
        self.stdout.write(f"  Second approved technician: {user.email} ({status})")

    def _attach_skills(self, profile):
        """Attach the first available category and skill to a technician profile."""
        cat = Category.objects.filter(is_active=True).first()
        if cat:
            skill_set, _ = TechnicianSkillSet.objects.get_or_create(technician=profile)
            skill_set.categories.add(cat)

            skill = Skill.objects.filter(category=cat, is_active=True).first()
            if skill:
                skill_set.skills.add(skill)

    def _seed_request_fixtures(self):
        """Create deterministic service request fixtures for E2E testing.
        
        Creates requests in various states to support Playwright tests.
        Idempotent: updates if exists, creates if not.
        """
        try:
            client_profile = ClientProfile.objects.get(user__email=FIXTURE_EMAILS["client"])
            approved_tech_profile = TechnicianProfile.objects.get(
                user__email=FIXTURE_EMAILS["approved_technician"]
            )
            second_tech_profile = TechnicianProfile.objects.get(
                user__email=FIXTURE_EMAILS["second_approved"]
            )
        except (ClientProfile.DoesNotExist, TechnicianProfile.DoesNotExist):
            self.stdout.write(self.style.WARNING("  Skipping request fixtures: users not seeded yet."))
            return

        # Pending request — assigned to approved technician
        ServiceRequest.objects.update_or_create(
            id=self._request_id("pending"),
            defaults=dict(
                client=client_profile,
                technician=approved_tech_profile,
                title="Fix AC Unit",
                description="My air conditioner is not cooling properly. Need a technician to check.",
                status=ServiceRequest.Status.PENDING,
                is_urgent=True,
                governorate="Baghdad",
            ),
        )

        # Accepted request
        ServiceRequest.objects.update_or_create(
            id=self._request_id("accepted"),
            defaults=dict(
                client=client_profile,
                technician=approved_tech_profile,
                title="Install Smart Lock",
                description="Need help installing a smart lock at my office.",
                status=ServiceRequest.Status.ACCEPTED,
                governorate="Baghdad",
            ),
        )

        # Declined request
        ServiceRequest.objects.update_or_create(
            id=self._request_id("declined"),
            defaults=dict(
                client=client_profile,
                technician=approved_tech_profile,
                title="Fix Leaking Pipe",
                description="Kitchen sink pipe is leaking.",
                status=ServiceRequest.Status.DECLINED,
            ),
        )

        # Cancelled request
        ServiceRequest.objects.update_or_create(
            id=self._request_id("cancelled"),
            defaults=dict(
                client=client_profile,
                technician=approved_tech_profile,
                title="Paint Living Room",
                description="Need to paint the living room walls.",
                status=ServiceRequest.Status.CANCELLED,
            ),
        )

        # Withdrawn request
        ServiceRequest.objects.update_or_create(
            id=self._request_id("withdrawn"),
            defaults=dict(
                client=client_profile,
                technician=approved_tech_profile,
                title="Fix Garden Fence",
                description="The wooden fence needs repairs.",
                status=ServiceRequest.Status.WITHDRAWN,
            ),
        )

        # Cross-client request (for IDOR tests) — client A to second technician
        ServiceRequest.objects.update_or_create(
            id=self._request_id("cross_client"),
            defaults=dict(
                client=client_profile,
                technician=second_tech_profile,
                title="Cross-Client Request",
                description="This request belongs to the primary client but assigned to second tech.",
                status=ServiceRequest.Status.PENDING,
            ),
        )

        self.stdout.write(f"  Created {ServiceRequest.objects.count()} request fixture(s).")

    def _request_id(self, label):
        """Generate a deterministic UUID for a request fixture label."""
        import uuid
        return uuid.uuid5(uuid.NAMESPACE_DNS, f"e2e-request-{label}.tiqani.local")

    def _report(self):
        """Print a summary of created fixtures."""
        self.stdout.write()
        self.stdout.write(self.style.SUCCESS("E2E fixture summary:"))
        self.stdout.write(f"  Client:              {FIXTURE_EMAILS['client']}")
        self.stdout.write(f"  Technician:          {FIXTURE_EMAILS['technician']}")
        self.stdout.write(f"  Approved technician: {FIXTURE_EMAILS['approved_technician']}")
        self.stdout.write(f"  Restricted tech:     {FIXTURE_EMAILS['restricted_technician']}")
        self.stdout.write(f"  Second approved:     {FIXTURE_EMAILS['second_approved']}")
        req_count = ServiceRequest.objects.filter(
            client__user__email__in=FIXTURE_EMAILS.values()
        ).count()
        self.stdout.write(f"  Service requests:    {req_count} fixtures")
        self.stdout.write()
        self.stdout.write("  Credentials: Set via E2E_FIXTURE_PASSWORD environment variable.")
        self.stdout.write("  Production guard: Active (use --force to override).")
