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
        """Remove all E2E fixture records, including wallet and payment state."""
        from wallet.models import PaymentIntent, WalletTransaction
        from contract.models import Contract
        from accounts.models import ClientProfile, TechnicianProfile
        emails = list(FIXTURE_EMAILS.values())
        users = list(User.objects.filter(email__in=emails))
        if not users:
            self.stdout.write(self.style.WARNING("  No existing fixture users to remove."))
            return

        # Delete wallet transactions first (PROTECT fkey on wallet)
        from django.db.models import Q
        user_ids = [u.pk for u in users]
        from accounts.models import ClientProfile, TechnicianProfile
        cp_ids = list(ClientProfile.objects.filter(user_id__in=user_ids).values_list("pk", flat=True))
        tp_ids = list(TechnicianProfile.objects.filter(user_id__in=user_ids).values_list("pk", flat=True))

        # Phase 9 — delete in dependency-safe order
        from wallet.models import (
            ContractSettlement, PlatformWalletTransaction, PlatformEarning,
            WithdrawalRequest,
        )
        from contract.models import ContractAuditEvent
        from contract.models import Contract

        contract_ids = list(
            Contract.objects.filter(
                client_id__in=cp_ids
            ).values_list("pk", flat=True)
        ) + list(
            Contract.objects.filter(
                technician_id__in=tp_ids
            ).values_list("pk", flat=True)
        )

        # Payout audit records
        WithdrawalRequest.objects.filter(user_id__in=user_ids).delete()
        # Settlement audit events
        ContractAuditEvent.objects.filter(contract_id__in=contract_ids).delete()
        # Platform wallet transactions
        PlatformWalletTransaction.objects.filter(source_user_id__in=user_ids).delete()
        # Platform earnings
        PlatformEarning.objects.filter(contract_id__in=contract_ids).delete()
        # Wallet transactions
        WalletTransaction.objects.filter(wallet__user_id__in=user_ids).delete()
        # Settlements
        ContractSettlement.objects.filter(contract_id__in=contract_ids).delete()
        # Payment intents
        PaymentIntent.objects.filter(user_id__in=user_ids).delete()
        # Contracts
        Contract.objects.filter(client_id__in=cp_ids).delete()
        Contract.objects.filter(technician_id__in=tp_ids).delete()

        deleted, _ = User.objects.filter(pk__in=user_ids).delete()
        self.stdout.write(self.style.WARNING(f"Removed {deleted} fixture user(s) and related records."))

    @transaction.atomic
    def _seed_fixtures(self, password):
        """Create or update all fixture users and requests."""
        self._create_client(password)
        self._create_technician(password)
        self._create_approved_technician(password)
        self._create_restricted_technician(password)
        self._create_second_approved_technician(password)
        self._seed_request_fixtures()
        self._seed_messaging_fixtures()
        self._seed_offer_fixtures()
        self._seed_payment_fixtures()
        self._seed_execution_fixtures()
        self._seed_phase9_fixtures()

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

    def _room_id(self, label):
        """Generate a deterministic UUID for a chat room fixture label."""
        import uuid
        return uuid.uuid5(uuid.NAMESPACE_DNS, f"e2e-room-{label}.tiqani.local")

    def _message_id(self, label):
        """Generate a deterministic UUID for a message fixture label."""
        import uuid
        return uuid.uuid5(uuid.NAMESPACE_DNS, f"e2e-msg-{label}.tiqani.local")

    def _seed_messaging_fixtures(self):
        """Create deterministic messaging fixtures for E2E testing.

        Creates chat rooms linked to service requests with sample messages.
        Idempotent: updates if exists, creates if not.
        """
        from chat.models import ServiceChatRoom, ServiceChatMessage, ServiceChatReadState
        from accounts.models import TechnicianProfile

        try:
            client_profile = ClientProfile.objects.get(user__email=FIXTURE_EMAILS["client"])
            approved_tech_profile = TechnicianProfile.objects.get(
                user__email=FIXTURE_EMAILS["approved_technician"]
            )
            second_tech_profile = TechnicianProfile.objects.get(
                user__email=FIXTURE_EMAILS["second_approved"]
            )
            tech_profile = TechnicianProfile.objects.get(
                user__email=FIXTURE_EMAILS["technician"]
            )
        except (ClientProfile.DoesNotExist, TechnicianProfile.DoesNotExist):
            self.stdout.write(self.style.WARNING("  Skipping messaging fixtures: users not seeded."))
            return

        client_user = client_profile.user
        approved_tech_user = approved_tech_profile.user
        second_tech_user = second_tech_profile.user
        tech_user = tech_profile.user

        accepted_request = ServiceRequest.objects.filter(
            client=client_profile,
            technician=approved_tech_profile,
            status=ServiceRequest.Status.ACCEPTED,
        ).first()

        # Room 1: Client A + Technician A, linked to accepted request
        room1, _ = ServiceChatRoom.objects.update_or_create(
            id=self._room_id("room1"),
            defaults={
                "client": client_profile,
                "technician": approved_tech_profile,
                "created_by": client_user,
                "service_request": accepted_request,
                "status": ServiceChatRoom.Status.OPEN,
                "last_message_at": "2026-06-16T09:30:00Z",
            },
        )

        # Client A message in room 1
        ServiceChatMessage.objects.update_or_create(
            id=self._message_id("room1_client"),
            defaults={
                "room": room1,
                "sender": client_user,
                "message_type": "TEXT",
                "body": "Hi, I'd like to discuss the smart lock installation.",
                "created_at": "2026-06-16T09:00:00Z",
            },
        )

        # Technician A reply (unread for client)
        ServiceChatMessage.objects.update_or_create(
            id=self._message_id("room1_tech_reply"),
            defaults={
                "room": room1,
                "sender": approved_tech_user,
                "message_type": "TEXT",
                "body": "Sure! I can install the smart lock tomorrow. What time works for you?",
                "created_at": "2026-06-16T09:30:00Z",
            },
        )

        # Set unread count for client
        ServiceChatReadState.objects.update_or_create(
            room=room1,
            user=client_user,
            defaults={"unread_count": 1},
        )
        ServiceChatReadState.objects.update_or_create(
            room=room1,
            user=approved_tech_user,
            defaults={"unread_count": 0},
        )

        # Room 2: Client B + Technician B, linked to cross-client request
        cross_request = ServiceRequest.objects.filter(
            client=client_profile,
            technician=second_tech_profile,
        ).first()

        room2, _ = ServiceChatRoom.objects.update_or_create(
            id=self._room_id("room2"),
            defaults={
                "client": client_profile,
                "technician": second_tech_profile,
                "created_by": client_user,
                "service_request": cross_request,
                "status": ServiceChatRoom.Status.OPEN,
            },
        )

        # Read conversation
        ServiceChatMessage.objects.update_or_create(
            id=self._message_id("room2_greeting"),
            defaults={
                "room": room2,
                "sender": client_user,
                "message_type": "TEXT",
                "body": "Hello! I need help with a network setup.",
                "created_at": "2026-06-15T14:00:00Z",
            },
        )
        # All read
        ServiceChatReadState.objects.update_or_create(
            room=room2,
            user=client_user,
            defaults={"unread_count": 0},
        )
        ServiceChatReadState.objects.update_or_create(
            room=room2,
            user=second_tech_user,
            defaults={"unread_count": 0},
        )

        # Room 3: Client A + Technician C (e2e_technician), plain conversations
        room3, _ = ServiceChatRoom.objects.update_or_create(
            id=self._room_id("room3"),
            defaults={
                "client": client_profile,
                "technician": tech_profile,
                "created_by": client_user,
                "status": ServiceChatRoom.Status.OPEN,
                "last_message_at": "2026-06-16T10:00:00Z",
            },
        )
        # Client A message in room 3
        ServiceChatMessage.objects.update_or_create(
            id=self._message_id("room3_client"),
            defaults={
                "room": room3,
                "sender": client_user,
                "message_type": "TEXT",
                "body": "Hello, I need help with my computer.",
                "created_at": "2026-06-16T09:45:00Z",
            },
        )
        # Technician C reply
        ServiceChatMessage.objects.update_or_create(
            id=self._message_id("room3_tech_reply"),
            defaults={
                "room": room3,
                "sender": tech_user,
                "message_type": "TEXT",
                "body": "I'd be happy to help! What seems to be the issue?",
                "created_at": "2026-06-16T10:00:00Z",
            },
        )
        # Unread for technician
        ServiceChatReadState.objects.update_or_create(
            room=room3,
            user=client_user,
            defaults={"unread_count": 0},
        )
        ServiceChatReadState.objects.update_or_create(
            room=room3,
            user=tech_user,
            defaults={"unread_count": 1},
        )

        self.stdout.write(f"  Created messaging fixtures: 3 rooms, 6 messages.")

    def _seed_offer_fixtures(self):
        """Create deterministic offer fixtures for E2E testing.

        Creates offers in various states to support Playwright tests.
        Idempotent: updates if exists, creates if not.
        """
        from contract.offer_models import Offer

        try:
            client_profile = ClientProfile.objects.get(user__email=FIXTURE_EMAILS["client"])
            approved_tech_profile = TechnicianProfile.objects.get(
                user__email=FIXTURE_EMAILS["approved_technician"]
            )
            second_tech_profile = TechnicianProfile.objects.get(
                user__email=FIXTURE_EMAILS["second_approved"]
            )
        except (ClientProfile.DoesNotExist, TechnicianProfile.DoesNotExist):
            self.stdout.write(self.style.WARNING("  Skipping offer fixtures: users not seeded."))
            return

        from servicerequest.models import ServiceRequest

        # Accepted request — suitable for offers
        accepted_request = ServiceRequest.objects.filter(
            client=client_profile,
            technician=approved_tech_profile,
            status=ServiceRequest.Status.ACCEPTED,
        ).first()

        # Second accepted request for cross-client
        accepted_request_2 = ServiceRequest.objects.filter(
            client=client_profile,
            technician=second_tech_profile,
            status=ServiceRequest.Status.PENDING,
        ).first()

        if not accepted_request:
            self.stdout.write(self.style.WARNING("  Skipping offer fixtures: no accepted request."))
            return

        import uuid

        # Submitted offer — eligible for client acceptance test
        _sid = uuid.uuid5(uuid.NAMESPACE_DNS, "e2e-offer-submitted.tiqani.local")
        Offer.objects.filter(id=_sid).delete()
        Offer.objects.create(
            id=_sid,
            service_request=accepted_request,
            amount="150000.00",
            description="Complete smart lock installation including mounting, wiring, and configuration.",
            duration_days=2,
            status=Offer.Status.SUBMITTED,
        )

        # Submitted offer — for rejection test
        _rid = uuid.uuid5(uuid.NAMESPACE_DNS, "e2e-offer-for-rejection.tiqani.local")
        Offer.objects.filter(id=_rid).delete()
        Offer.objects.create(
            id=_rid,
            service_request=accepted_request,
            amount="250000.00",
            description="Premium installation with additional security features.",
            duration_days=3,
            status=Offer.Status.SUBMITTED,
        )

        # Accepted offer — should have a Contract created
        _aid = uuid.uuid5(uuid.NAMESPACE_DNS, "e2e-offer-accepted.tiqani.local")
        Offer.objects.filter(id=_aid).delete()
        accepted_offer = Offer.objects.create(
            id=_aid,
            service_request=accepted_request,
            amount="120000.00",
            description="Basic smart lock installation.",
            duration_days=1,
            status=Offer.Status.ACCEPTED,
        )

        # Create a contract for the accepted offer
        from contract.models import Contract
        Contract.objects.update_or_create(
            id=uuid.uuid5(uuid.NAMESPACE_DNS, "e2e-contract-from-offer.tiqani.local"),
            defaults={
                "client": client_profile,
                "technician": approved_tech_profile,
                "work_description": accepted_offer.description,
                "agreed_amount": accepted_offer.amount,
                "currency": "IQD",
                "status": "draft",
                "client_accepted": True,
                "technician_accepted": True,
            },
        )

        # Withdrawn offer
        _wid = uuid.uuid5(uuid.NAMESPACE_DNS, "e2e-offer-withdrawn.tiqani.local")
        Offer.objects.filter(id=_wid).delete()
        Offer.objects.create(
            id=_wid,
            service_request=accepted_request,
            amount="50000.00",
            description="Quick fix offer (withdrawn).",
            duration_days=1,
            status=Offer.Status.WITHDRAWN,
        )

        # Offer for Client B / Tech B — IDOR test
        if accepted_request_2:
            _cid = uuid.uuid5(uuid.NAMESPACE_DNS, "e2e-offer-cross-client.tiqani.local")
            Offer.objects.filter(id=_cid).delete()
            Offer.objects.create(
                id=_cid,
                service_request=accepted_request_2,
                amount="180000.00",
                description="Cross-client offer for IDOR testing.",
                duration_days=4,
                status=Offer.Status.SUBMITTED,
            )

        self.stdout.write(f"  Created offer fixtures.")

    def _p9_id(self, label):
        import uuid
        return uuid.uuid5(uuid.NAMESPACE_DNS, f"e2e-p9-{label}.tiqani.local")

    def _seed_phase9_fixtures(self):
        """Create deterministic Phase 9 fixtures for settlement, wallet, and withdrawal tests."""
        from decimal import Decimal
        import uuid
        from wallet.models import (
            PaymentIntent, WalletTransaction, Wallet,
            WithdrawalRequest, ContractSettlement, PlatformWallet,
            PlatformEarning,
        )
        from wallet.settlement_services import settle_completed_contract
        from wallet import services as svc
        from contract.models import Contract, ContractAuditEvent

        try:
            client_profile = ClientProfile.objects.get(user__email=FIXTURE_EMAILS["client"])
            tech_profile = TechnicianProfile.objects.get(user__email=FIXTURE_EMAILS["approved_technician"])
            tech2_profile = TechnicianProfile.objects.get(user__email=FIXTURE_EMAILS["second_approved"])
        except (ClientProfile.DoesNotExist, TechnicianProfile.DoesNotExist):
            self.stdout.write(self.style.WARNING("  Skipping Phase 9 fixtures: users not seeded."))
            return

        client_user = client_profile.user
        tech_user = tech_profile.user

        # Ensure wallets
        Wallet.objects.get_or_create(user=client_user, defaults={"balance": Decimal("0")})
        Wallet.objects.get_or_create(user=tech_user, defaults={"balance": Decimal("0")})

        def _pay_id(label):
            return uuid.uuid5(uuid.NAMESPACE_DNS, f"e2e-pay-{label}.tiqani.local")

        # ── 1. Settlement-eligible completed+funded contract ──
        c_eligible, _ = Contract.objects.update_or_create(
            id=self._p9_id("eligible"),
            defaults={
                "client": client_profile, "technician": tech_profile,
                "agreed_amount": Decimal("500000.00"), "currency": "IQD",
                "status": "completed", "escrow_amount": Decimal("500000.00"),
                "total_paid": Decimal("525000.00"),
                "work_description": "E2E Phase 9 settlement-eligible fixture.",
                "start_date": timezone.now().date(), "duration_days": 10,
            },
        )
        PaymentIntent.objects.update_or_create(
            id=_pay_id("p9-eligible"),
            defaults={
                "contract": c_eligible, "user": client_user,
                "amount": Decimal("525000.00"), "purpose": PaymentIntent.Purpose.CONTRACT_FUNDING,
                "status": PaymentIntent.Status.PAID, "paid_at": timezone.now(),
            },
        )
        from wallet.services import ensure_contract_payment_breakdown
        ensure_contract_payment_breakdown(c_eligible)

        # ── 2. Already settled contract ──
        c_settled, _ = Contract.objects.update_or_create(
            id=self._p9_id("already-settled"),
            defaults={
                "client": client_profile, "technician": tech_profile,
                "agreed_amount": Decimal("300000.00"), "currency": "IQD",
                "status": "completed", "escrow_amount": Decimal("0.00"),
                "total_paid": Decimal("315000.00"),
                "work_description": "E2E Phase 9 already-settled fixture.",
                "start_date": timezone.now().date(), "duration_days": 10,
            },
        )
        PaymentIntent.objects.update_or_create(
            id=_pay_id("p9-settled"),
            defaults={
                "contract": c_settled, "user": client_user,
                "amount": Decimal("315000.00"), "purpose": PaymentIntent.Purpose.CONTRACT_FUNDING,
                "status": PaymentIntent.Status.PAID, "paid_at": timezone.now(),
            },
        )
        ensure_contract_payment_breakdown(c_settled)
        settle_completed_contract(
            contract_id=str(c_settled.id), actor=client_user,
            idempotency_key="p9-seed-already-settled",
        )

        # ── 3. Active/ineligible contract ──
        c_active, _ = Contract.objects.update_or_create(
            id=self._p9_id("active"),
            defaults={
                "client": client_profile, "technician": tech_profile,
                "agreed_amount": Decimal("200000.00"), "currency": "IQD",
                "status": "active", "escrow_amount": Decimal("0.00"),
                "work_description": "E2E Phase 9 active ineligible fixture.",
                "start_date": timezone.now().date(), "duration_days": 10,
            },
        )

        # ── 4. Completed but unfunded ──
        c_unfunded, _ = Contract.objects.update_or_create(
            id=self._p9_id("unfunded"),
            defaults={
                "client": client_profile, "technician": tech_profile,
                "agreed_amount": Decimal("150000.00"), "currency": "IQD",
                "status": "completed", "escrow_amount": Decimal("0.00"),
                "work_description": "E2E Phase 9 completed but unfunded.",
                "start_date": timezone.now().date(), "duration_days": 10,
            },
        )
        ensure_contract_payment_breakdown(c_unfunded)

        # ── 5. Completed with zero escrow ──
        c_zero_escrow, _ = Contract.objects.update_or_create(
            id=self._p9_id("zero-escrow"),
            defaults={
                "client": client_profile, "technician": tech_profile,
                "agreed_amount": Decimal("100000.00"), "currency": "IQD",
                "status": "completed", "escrow_amount": Decimal("0.00"),
                "work_description": "E2E Phase 9 zero escrow.",
                "start_date": timezone.now().date(), "duration_days": 10,
            },
        )
        ensure_contract_payment_breakdown(c_zero_escrow)

        # ── 6. Duplicate settlement scenario ──
        c_dup, _ = Contract.objects.update_or_create(
            id=self._p9_id("duplicate"),
            defaults={
                "client": client_profile, "technician": tech_profile,
                "agreed_amount": Decimal("400000.00"), "currency": "IQD",
                "status": "completed", "escrow_amount": Decimal("400000.00"),
                "total_paid": Decimal("420000.00"),
                "work_description": "E2E Phase 9 duplicate settlement fixture.",
                "start_date": timezone.now().date(), "duration_days": 10,
            },
        )
        PaymentIntent.objects.update_or_create(
            id=_pay_id("p9-dup"),
            defaults={
                "contract": c_dup, "user": client_user,
                "amount": Decimal("420000.00"), "purpose": PaymentIntent.Purpose.CONTRACT_FUNDING,
                "status": PaymentIntent.Status.PAID, "paid_at": timezone.now(),
            },
        )
        ensure_contract_payment_breakdown(c_dup)

        # ── 7. Wallet with available balance (for tech_user) ──
        tech_wallet = Wallet.objects.get(user=tech_user)
        tech_wallet.balance = Decimal("100000.00")
        tech_wallet.save(update_fields=["balance"])

        # ── 8. Withdrawal eligible ──
        svc.create_withdrawal_request(
            tech_user, Decimal("10000.00"),
            method="sandbox", notes="E2E withdrawal eligible",
        )

        # ── 9. Withdrawal pending ──
        wr_pending = svc.create_withdrawal_request(
            tech_user, Decimal("20000.00"),
            method="sandbox", notes="E2E withdrawal pending",
        )

        # ── 10. Withdrawal approved ──
        staff = User.objects.filter(is_staff=True, is_superuser=True).first()
        if staff:
            wr_approved = svc.create_withdrawal_request(
                tech_user, Decimal("15000.00"),
                method="sandbox", notes="E2E withdrawal approved",
            )
            svc.approve_withdrawal_request(wr_approved, staff, "Approved via seed")

        # ── 11. Withdrawal processing ──
        if staff:
            wr_processing = svc.create_withdrawal_request(
                tech_user, Decimal("5000.00"),
                method="sandbox", notes="E2E withdrawal processing",
            )
            svc.approve_withdrawal_request(wr_processing, staff, "Processing via seed")
            svc.process_withdrawal_request(wr_processing, staff)

        # ── 12. Withdrawal paid ──
        if staff:
            wr_paid = svc.create_withdrawal_request(
                tech_user, Decimal("5000.00"),
                method="sandbox", notes="E2E withdrawal paid",
            )
            svc.approve_withdrawal_request(wr_paid, staff, "Paid via seed")
            svc.confirm_withdrawal_payout(wr_paid, staff, simulate_failure=False)

        # ── 13. Withdrawal failed ──
        if staff:
            wr_failed = svc.create_withdrawal_request(
                tech_user, Decimal("5000.00"),
                method="sandbox", notes="E2E withdrawal failed",
            )
            svc.approve_withdrawal_request(wr_failed, staff, "Failed via seed")
            svc.confirm_withdrawal_payout(wr_failed, staff, simulate_failure=True)

        # ── 14. Insufficient balance test ──

        # ── 15. Settlement IDOR contract ──
        c_idor, _ = Contract.objects.update_or_create(
            id=self._p9_id("idor"),
            defaults={
                "client": client_profile, "technician": tech_profile,
                "agreed_amount": Decimal("250000.00"), "currency": "IQD",
                "status": "completed", "escrow_amount": Decimal("250000.00"),
                "total_paid": Decimal("262500.00"),
                "work_description": "E2E Phase 9 IDOR settlement fixture.",
                "start_date": timezone.now().date(), "duration_days": 10,
            },
        )
        PaymentIntent.objects.update_or_create(
            id=_pay_id("p9-idor"),
            defaults={
                "contract": c_idor, "user": client_user,
                "amount": Decimal("262500.00"), "purpose": PaymentIntent.Purpose.CONTRACT_FUNDING,
                "status": PaymentIntent.Status.PAID, "paid_at": timezone.now(),
            },
        )
        ensure_contract_payment_breakdown(c_idor)

        # ── 16. Reconciliation mismatch contract (will settle, then break) ──
        c_mismatch, _ = Contract.objects.update_or_create(
            id=self._p9_id("mismatch"),
            defaults={
                "client": client_profile, "technician": tech_profile,
                "agreed_amount": Decimal("350000.00"), "currency": "IQD",
                "status": "completed", "escrow_amount": Decimal("350000.00"),
                "total_paid": Decimal("367500.00"),
                "work_description": "E2E Phase 9 reconciliation mismatch fixture.",
                "start_date": timezone.now().date(), "duration_days": 10,
            },
        )
        PaymentIntent.objects.update_or_create(
            id=_pay_id("p9-mismatch"),
            defaults={
                "contract": c_mismatch, "user": client_user,
                "amount": Decimal("367500.00"), "purpose": PaymentIntent.Purpose.CONTRACT_FUNDING,
                "status": PaymentIntent.Status.PAID, "paid_at": timezone.now(),
            },
        )
        ensure_contract_payment_breakdown(c_mismatch)

        self.stdout.write("  Created Phase 9 fixtures.")

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
        from chat.models import ServiceChatRoom, ServiceChatMessage
        chat_room_count = ServiceChatRoom.objects.count()
        chat_msg_count = ServiceChatMessage.objects.count()
        self.stdout.write(f"  Chat rooms:          {chat_room_count} fixtures")
        self.stdout.write(f"  Chat messages:       {chat_msg_count} fixtures")
        from contract.offer_models import Offer
        offer_count = Offer.objects.count()
        self.stdout.write(f"  Offers:              {offer_count} fixtures")
        from wallet.models import PaymentIntent, WalletTransaction
        pay_count = PaymentIntent.objects.filter(
            user__email__in=list(FIXTURE_EMAILS.values())
        ).count()
        txn_count = WalletTransaction.objects.filter(
            wallet__user__email__in=list(FIXTURE_EMAILS.values())
        ).count()
        self.stdout.write(f"  Payment intents:     {pay_count} fixtures")
        self.stdout.write(f"  Wallet transactions: {txn_count} fixtures")

        # Phase 8 execution counts
        from contract.models import (
            ExecutionMilestone, DeliverableSubmission,
            RevisionRequest, CompletionRequest, ContractAuditEvent,
        )
        exec_ms_count = ExecutionMilestone.objects.filter(contract__client__user__email__in=FIXTURE_EMAILS.values()).count()
        exec_sub_count = DeliverableSubmission.objects.filter(milestone__contract__client__user__email__in=FIXTURE_EMAILS.values()).count()
        exec_rev_count = RevisionRequest.objects.filter(milestone__contract__client__user__email__in=FIXTURE_EMAILS.values()).count()
        exec_cr_count = CompletionRequest.objects.filter(contract__client__user__email__in=FIXTURE_EMAILS.values()).count()
        exec_hist_count = ContractAuditEvent.objects.filter(contract__client__user__email__in=FIXTURE_EMAILS.values()).count()
        self.stdout.write(f"  Execution milestones:       {exec_ms_count} fixtures")
        self.stdout.write(f"  Deliverable submissions:   {exec_sub_count} fixtures")
        self.stdout.write(f"  Revision requests:         {exec_rev_count} fixtures")
        self.stdout.write(f"  Completion requests:       {exec_cr_count} fixtures")
        self.stdout.write(f"  Execution history events:  {exec_hist_count} fixtures")
        self.stdout.write()
        self.stdout.write("  Credentials: Set via E2E_FIXTURE_PASSWORD environment variable.")
        self.stdout.write("  Production guard: Active (use --force to override).")

    def _seed_payment_fixtures(self):
        """Create deterministic payment fixtures for E2E funding tests."""

        def _pay_id(label):
            return uuid.uuid5(uuid.NAMESPACE_DNS, f"e2e-pay-{label}.tiqani.local")

        def _contract_id(label):
            return uuid.uuid5(uuid.NAMESPACE_DNS, f"e2e-contract-{label}.tiqani.local")

        try:
            client_profile = ClientProfile.objects.get(user__email=FIXTURE_EMAILS["client"])
            approved_tech_profile = TechnicianProfile.objects.get(
                user__email=FIXTURE_EMAILS["approved_technician"]
            )
        except (ClientProfile.DoesNotExist, TechnicianProfile.DoesNotExist):
            self.stdout.write(self.style.WARNING("  Skipping payment fixtures: users not seeded."))
            return

        import uuid
        from decimal import Decimal
        from wallet.models import PaymentIntent, WalletTransaction, Wallet, ContractPaymentBreakdown
        from contract.models import Contract
        from wallet.services import ensure_contract_payment_breakdown

        client_user = client_profile.user
        tech_user = approved_tech_profile.user

        # Ensure wallets exist
        Wallet.objects.get_or_create(user=client_user, defaults={"balance": Decimal("0")})
        Wallet.objects.get_or_create(user=tech_user, defaults={"balance": Decimal("0")})

        # ── Helper ──────────────────────────────────────────────────
        def _make_contract(label, *, amount="500000.00", desc=None):
            c, _ = Contract.objects.update_or_create(
                id=_contract_id(label),
                defaults={
                    "client": client_profile,
                    "technician": approved_tech_profile,
                    "agreed_amount": Decimal(amount),
                    "currency": "IQD",
                    "status": "in_progress",
                    "escrow_amount": Decimal("0"),
                    "work_description": desc or f"E2E test contract \u2014 {label}.",
                    "start_date": timezone.now().date(),
                    "duration_days": 10,
                },
            )
            ensure_contract_payment_breakdown(c)
            return c

        # ── 1. Mutable (unfunded) contracts ─────────────────────────
        # Each mutating test gets its own contract so tests never block each other.

        success_ct = _make_contract("success", amount="500000.00",
                                    desc="E2E success flow \u2014 starts unfunded.")
        failure_ct = _make_contract("failure", amount="250000.00",
                                    desc="E2E failure flow \u2014 starts unfunded.")
        double_ct = _make_contract("double-click", amount="300000.00",
                                   desc="E2E double-click idempotency \u2014 starts unfunded.")
        duplicate_ct = _make_contract("duplicate-confirm", amount="350000.00",
                                      desc="E2E duplicate confirm \u2014 starts unfunded.")
        logout_ct = _make_contract("logout", amount="400000.00",
                                   desc="E2E logout security \u2014 starts unfunded.")
        localization_ct = _make_contract("localization", amount="450000.00",
                                         desc="E2E localization \u2014 starts unfunded.")
        responsive_ct = _make_contract("responsive", amount="475000.00",
                                       desc="E2E responsive \u2014 starts unfunded.")

        # Backward-compat unfunded contract \u2014 KEEP clean
        _make_contract("unfunded", amount="500000.00",
                       desc="Backward-compat unfunded contract.")

        # ── 2. Pending-view contract (immutable, has pending intent) ─
        pending_ct = _make_contract("pending-view", amount="600000.00",
                                    desc="E2E pending status fixture.")
        PaymentIntent.objects.update_or_create(
            id=_pay_id("pending-view"),
            defaults={
                "contract": pending_ct,
                "user": client_user,
                "amount": Decimal("630000.00"),
                "currency": "IQD",
                "purpose": PaymentIntent.Purpose.CONTRACT_FUNDING,
                "provider": "sandbox",
                "status": PaymentIntent.Status.PENDING,
            },
        )

        # ── 3. Funded-view contract (immutable, has paid intent + txn) ─
        funded_ct = Contract.objects.update_or_create(
            id=_contract_id("funded-view"),
            defaults={
                "client": client_profile,
                "technician": approved_tech_profile,
                "agreed_amount": Decimal("1000000.00"),
                "currency": "IQD",
                "status": "in_progress",
                "escrow_amount": Decimal("1000000.00"),
                "work_description": "E2E funded-view fixture.",
                "start_date": timezone.now().date(),
                "duration_days": 15,
            },
        )[0]
        ensure_contract_payment_breakdown(funded_ct)

        paid_intent, _ = PaymentIntent.objects.update_or_create(
            id=_pay_id("funded-view-paid"),
            defaults={
                "contract": funded_ct,
                "user": client_user,
                "amount": Decimal("1050000.00"),
                "currency": "IQD",
                "purpose": PaymentIntent.Purpose.CONTRACT_FUNDING,
                "provider": "sandbox",
                "status": PaymentIntent.Status.PAID,
                "paid_at": timezone.now(),
            },
        )
        wallet = client_user.wallet
        wallet.balance += paid_intent.amount
        wallet.save(update_fields=["balance"])
        WalletTransaction.objects.update_or_create(
            id=_pay_id("funded-view-deposit"),
            defaults={
                "wallet": wallet,
                "contract": funded_ct,
                "transaction_type": WalletTransaction.Type.DEPOSIT,
                "amount": paid_intent.amount,
                "description": f"E2E deposit \u2014 {funded_ct.contract_reference}",
            },
        )
        WalletTransaction.objects.update_or_create(
            id=_pay_id("funded-view-escrow"),
            defaults={
                "wallet": wallet,
                "contract": funded_ct,
                "transaction_type": WalletTransaction.Type.ESCROW,
                "amount": Decimal("1000000.00"),
                "description": f"E2E escrow \u2014 {funded_ct.contract_reference}",
            },
        )

        # ── 4. Legacy failure contract ──────────────────────────────
        # Keep its failed intent for backward compat
        PaymentIntent.objects.update_or_create(
            id=_pay_id("failed"),
            defaults={
                "contract": failure_ct,
                "user": client_user,
                "amount": Decimal("262500.00"),
                "currency": "IQD",
                "purpose": PaymentIntent.Purpose.CONTRACT_FUNDING,
                "provider": "sandbox",
                "status": PaymentIntent.Status.FAILED,
                "metadata": {"failure_code": "sandbox_simulated_failure",
                             "failure_message": "Simulated failure."},
            },
        )

        # Legacy funded contract (backward compat)
        Contract.objects.update_or_create(
            id=_contract_id("funded"),
            defaults={
                "client": client_profile,
                "technician": approved_tech_profile,
                "agreed_amount": Decimal("1000000.00"),
                "currency": "IQD",
                "status": "in_progress",
                "escrow_amount": Decimal("1000000.00"),
                "work_description": "E2E legacy funded fixture.",
                "start_date": timezone.now().date(),
                "duration_days": 15,
            },
        )
        PaymentIntent.objects.update_or_create(
            id=_pay_id("success"),
            defaults={
                "contract_id": _contract_id("funded"),
                "user": client_user,
                "amount": Decimal("1050000.00"),
                "currency": "IQD",
                "purpose": PaymentIntent.Purpose.CONTRACT_FUNDING,
                "provider": "sandbox",
                "status": PaymentIntent.Status.PAID,
                "paid_at": timezone.now(),
            },
        )

        self.stdout.write(f"  Created payment fixtures.")


    def _exec_contract_id(self, label):
        import uuid
        return uuid.uuid5(uuid.NAMESPACE_DNS, f"e2e-exec-{label}.tiqani.local")

    def _milestone_id(self, label):
        import uuid
        return uuid.uuid5(uuid.NAMESPACE_DNS, f"e2e-ms-{label}.tiqani.local")

    def _submission_id(self, label):
        import uuid
        return uuid.uuid5(uuid.NAMESPACE_DNS, f"e2e-sub-{label}.tiqani.local")

    def _revision_id(self, label):
        import uuid
        return uuid.uuid5(uuid.NAMESPACE_DNS, f"e2e-rev-{label}.tiqani.local")

    def _completion_request_id(self, label):
        import uuid
        return uuid.uuid5(uuid.NAMESPACE_DNS, f"e2e-cr-{label}.tiqani.local")

    def _history_id(self, label):
        import uuid
        return uuid.uuid5(uuid.NAMESPACE_DNS, f"e2e-hist-{label}.tiqani.local")

    def _seed_execution_fixtures(self):
        from decimal import Decimal
        from contract.models import Contract, ExecutionMilestone, DeliverableSubmission, CompletionRequest, ContractAuditEvent

        try:
            client_profile = ClientProfile.objects.get(user__email=FIXTURE_EMAILS["client"])
            tech_profile = TechnicianProfile.objects.get(user__email=FIXTURE_EMAILS["approved_technician"])
            pw = get_password()
            client2_user, _ = User.objects.update_or_create(
                username="e2e_client_b",
                defaults={"email": "e2e-client-b@tiqani.local", "role": User.Role.CLIENT, "phone_number": "07500000099", "governorate": "Baghdad", "is_active": True},
            )
            if not client2_user.has_usable_password():
                client2_user.set_password(pw)
                client2_user.save(update_fields=["password"])
            client2, _ = ClientProfile.objects.update_or_create(user=client2_user)
            ClientProfile.objects.filter(pk=client2.pk).update(is_complete=True)

            tech2_user, _ = User.objects.update_or_create(
                username="e2e_tech_b",
                defaults={"email": "e2e-tech-b@tiqani.local", "role": User.Role.TECHNICIAN, "phone_number": "07500000098", "governorate": "Basra", "is_active": True},
            )
            if not tech2_user.has_usable_password():
                tech2_user.set_password(pw)
                tech2_user.save(update_fields=["password"])
            tech2, _ = TechnicianProfile.objects.update_or_create(
                user=tech2_user,
                defaults={"job_title": "Tech B", "years_of_expertise": 3, "approved": True},
            )
            TechnicianProfile.objects.filter(pk=tech2.pk).update(is_complete=True)
        except (ClientProfile.DoesNotExist, TechnicianProfile.DoesNotExist):
            self.stdout.write(self.style.WARNING("  Skipping execution fixtures: users not seeded."))
            return

        client_user = client_profile.user
        tech_user = tech_profile.user

        def _make(label, *, status="in_progress", escrow="100000.00", client=client_profile, tech=tech_profile):
            c, _ = Contract.objects.update_or_create(
                id=self._exec_contract_id(label),
                defaults={
                    "client": client, "technician": tech,
                    "work_description": f"E2E execution -- {label}.",
                    "agreed_amount": Decimal("100000.00"), "currency": "IQD",
                    "status": status, "escrow_amount": Decimal(escrow),
                    "start_date": timezone.now().date(), "duration_days": 10,
                    "stage_number": 2, "total_paid": Decimal("0"),
                },
            )
            return c

        import uuid
        def _pay_id(label):
            return uuid.uuid5(uuid.NAMESPACE_DNS, f"e2e-pay-{label}.tiqani.local")

        def _fund(label):
            """Create a PAID PaymentIntent so contract is 'funded' per backend checks."""
            from wallet.models import PaymentIntent
            c = Contract.objects.get(id=self._exec_contract_id(label))
            PaymentIntent.objects.update_or_create(
                id=_pay_id(f"exec-{label}"),
                defaults={
                    "contract": c,
                    "user": client_user,
                    "amount": c.escrow_amount or Decimal("100000.00"),
                    "currency": "IQD",
                    "purpose": PaymentIntent.Purpose.CONTRACT_FUNDING,
                    "provider": "sandbox",
                    "status": PaymentIntent.Status.PAID,
                    "paid_at": timezone.now(),
                },
            )

        _make("activation")
        _fund("activation")
        ExecutionMilestone.objects.update_or_create(
            id=self._milestone_id("act-ms"), defaults={"contract_id": self._exec_contract_id("activation"), "sequence": 1, "title": "First", "status": ExecutionMilestone.Status.DRAFT},
        )
        _make("milestone-create")
        re = _make("milestone-reorder")
        for i in range(1, 4):
            ExecutionMilestone.objects.update_or_create(
                id=self._milestone_id(f"re-ms{i}"), defaults={"contract": re, "sequence": i, "title": f"Step {i}", "status": ExecutionMilestone.Status.DRAFT},
            )
        _make("milestone-start", status="active")
        ExecutionMilestone.objects.update_or_create(
            id=self._milestone_id("st-ms"), defaults={"contract_id": self._exec_contract_id("milestone-start"), "sequence": 1, "title": "First", "status": ExecutionMilestone.Status.PENDING},
        )
        _make("deliverable-submit", status="active")
        ExecutionMilestone.objects.update_or_create(
            id=self._milestone_id("del-ms"), defaults={"contract_id": self._exec_contract_id("deliverable-submit"), "sequence": 1, "title": "Deliver", "status": ExecutionMilestone.Status.IN_PROGRESS},
        )
        _make("revision-request", status="active")
        rev_ms = ExecutionMilestone.objects.update_or_create(
            id=self._milestone_id("rev-ms"), defaults={"contract_id": self._exec_contract_id("revision-request"), "sequence": 1, "title": "Revise", "status": ExecutionMilestone.Status.SUBMITTED},
        )[0]
        DeliverableSubmission.objects.update_or_create(
            id=self._submission_id("rev-sub"), defaults={"milestone": rev_ms, "submitted_by": tech_user, "version": 1, "summary": "First try"},
        )
        _make("resubmission", status="active")
        resub_ms = ExecutionMilestone.objects.update_or_create(
            id=self._milestone_id("resub-ms"), defaults={"contract_id": self._exec_contract_id("resubmission"), "sequence": 1, "title": "Resub", "status": ExecutionMilestone.Status.REVISION_REQUESTED, "revision_count": 1},
        )[0]
        DeliverableSubmission.objects.update_or_create(
            id=self._submission_id("resub-sub"), defaults={"milestone": resub_ms, "submitted_by": tech_user, "version": 1, "summary": "Original"},
        )
        _make("milestone-approval", status="active")
        app_ms = ExecutionMilestone.objects.update_or_create(
            id=self._milestone_id("app-ms"), defaults={"contract_id": self._exec_contract_id("milestone-approval"), "sequence": 1, "title": "Approve", "status": ExecutionMilestone.Status.SUBMITTED},
        )[0]
        DeliverableSubmission.objects.update_or_create(
            id=self._submission_id("app-sub"), defaults={"milestone": app_ms, "submitted_by": tech_user, "version": 1, "summary": "Review me"},
        )
        _make("completion-request", status="active")
        ExecutionMilestone.objects.update_or_create(
            id=self._milestone_id("cr-ms"), defaults={"contract_id": self._exec_contract_id("completion-request"), "sequence": 1, "title": "Only", "status": ExecutionMilestone.Status.APPROVED},
        )
        _make("completion-confirm", status="completion_requested")
        ExecutionMilestone.objects.update_or_create(
            id=self._milestone_id("cf-ms"), defaults={"contract_id": self._exec_contract_id("completion-confirm"), "sequence": 1, "title": "Done", "status": ExecutionMilestone.Status.APPROVED},
        )
        CompletionRequest.objects.update_or_create(
            id=self._completion_request_id("cf-cr"), defaults={"contract_id": self._exec_contract_id("completion-confirm"), "requested_by": tech_user, "completion_message": "All done", "status": CompletionRequest.Status.PENDING},
        )
        _make("completion-reject", status="completion_requested")
        ExecutionMilestone.objects.update_or_create(
            id=self._milestone_id("rj-ms"), defaults={"contract_id": self._exec_contract_id("completion-reject"), "sequence": 1, "title": "Rev", "status": ExecutionMilestone.Status.APPROVED},
        )
        CompletionRequest.objects.update_or_create(
            id=self._completion_request_id("rj-cr"), defaults={"contract_id": self._exec_contract_id("completion-reject"), "requested_by": tech_user, "completion_message": "Ready", "status": CompletionRequest.Status.PENDING},
        )
        _make("execution-history", status="active")
        ContractAuditEvent.objects.update_or_create(
            id=self._history_id("h1"), defaults={"contract_id": self._exec_contract_id("execution-history"), "event_type": "CONTRACT_ACTIVATED", "actor": client_user},
        )
        ContractAuditEvent.objects.update_or_create(
            id=self._history_id("h2"), defaults={"contract_id": self._exec_contract_id("execution-history"), "event_type": "MILESTONE_CREATED", "actor": client_user},
        )
        _make("client-b-only", client=client2, tech=tech_profile)
        _make("tech-b-only", client=client_profile, tech=tech2)
        _make("completed", status="completed", escrow="100000.00")
        ExecutionMilestone.objects.update_or_create(
            id=self._milestone_id("co-ms"), defaults={"contract_id": self._exec_contract_id("completed"), "sequence": 1, "title": "Final", "status": ExecutionMilestone.Status.APPROVED, "approved_at": timezone.now()},
        )
        CompletionRequest.objects.update_or_create(
            id=self._completion_request_id("co-cr"), defaults={"contract_id": self._exec_contract_id("completed"), "requested_by": tech_user, "completion_message": "Complete", "status": CompletionRequest.Status.CONFIRMED},
        )

        self.stdout.write("  Created execution fixtures.")
