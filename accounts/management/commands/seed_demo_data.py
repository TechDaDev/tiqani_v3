"""
Management command to seed demo data for frontend integration and Postman testing.

Idempotent — safe to run multiple times.
Uses update_or_create where possible to avoid duplicates.

Usage:
    python manage.py seed_demo_data
"""

from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import ClientProfile, TechnicianProfile, AdminProfile
from category.models import Category, Skill
from contract.models import Contract
from wallet.models import Wallet, PlatformFeeConfig
from notification.services import create_notification
from ratereview.models import Review
from dealership.models import (
    DealershipProfile, DealershipGuarantee,
    DealershipRechargeFeeConfig, DealershipClientRecharge,
)
from dealership.services import create_recharge

User = get_user_model()


class Command(BaseCommand):
    help = "Seed demo data for frontend integration and Postman testing"

    def _create_or_update_user(self, username, email, password, role, is_staff=False, is_superuser=False):
        user, created = User.objects.update_or_create(
            username=username,
            defaults={
                'email': email,
                'role': role,
                'is_staff': is_staff,
                'is_superuser': is_superuser,
                'phone_number': None,  # Will be set per user
                'governorate': 'Baghdad',
                'address': 'Demo Address, Baghdad',
            },
        )
        if created:
            user.set_password(password)
            user.save()
        return user, created

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding demo data..."))
        results = {'created': 0, 'existing': 0}

        def _report(name, created):
            status = self.style.SUCCESS("✓ CREATED") if created else self.style.WARNING("✓ EXISTS")
            self.stdout.write(f"  {status}  {name}")
            if created:
                results['created'] += 1
            else:
                results['existing'] += 1

        # ── Demo Admin: system_admin ─────────────────────────────
        user, created = self._create_or_update_user(
            'admin_demo', 'admin.demo@tiqani.local', 'AdminDemo123!',
            'admin', is_staff=True, is_superuser=True,
        )
        AdminProfile.objects.update_or_create(
            user=user, defaults={'role': AdminProfile.AdminRole.SYSTEM_ADMIN}
        )
        _report('admin_demo (system_admin)', created)

        # ── Demo Finance Admin ───────────────────────────────────
        user, created = self._create_or_update_user(
            'finance_demo', 'finance.demo@tiqani.local', 'FinanceDemo123!',
            'admin', is_staff=True,
        )
        # Ensure unique phone number
        user.phone_number = '07700000901'
        user.save()
        AdminProfile.objects.update_or_create(
            user=user, defaults={'role': AdminProfile.AdminRole.FINANCE}
        )
        _report('finance_demo (finance_admin)', created)

        # ── Demo Moderator ───────────────────────────────────────
        user, created = self._create_or_update_user(
            'moderator_demo', 'moderator.demo@tiqani.local', 'ModeratorDemo123!',
            'admin', is_staff=True,
        )
        user.phone_number = '07700000902'
        user.save()
        AdminProfile.objects.update_or_create(
            user=user, defaults={'role': AdminProfile.AdminRole.MODERATOR}
        )
        _report('moderator_demo (content_moderator)', created)

        # ── Demo Account Manager ─────────────────────────────────
        user, created = self._create_or_update_user(
            'account_manager_demo', 'account.manager.demo@tiqani.local',
            'AccountManagerDemo123!', 'admin', is_staff=True,
        )
        user.phone_number = '07700000903'
        user.save()
        AdminProfile.objects.update_or_create(
            user=user, defaults={'role': AdminProfile.AdminRole.ACCOUNT_MANAGER}
        )
        _report('account_manager_demo (account_manager)', created)

        # ── Demo Client ──────────────────────────────────────────
        client_user, created = self._create_or_update_user(
            'client_demo', 'client.demo@tiqani.local', 'ClientDemo123!', 'client',
        )
        client_user.phone_number = '07700000904'
        client_user.date_of_birth = timezone.now().date().replace(year=1995, month=1, day=15)
        client_user.gender = 'male'
        client_user.save()
        ClientProfile.objects.update_or_create(user=client_user)
        # Wallet with balance
        wallet, _ = Wallet.objects.get_or_create(user=client_user)
        if wallet.balance < Decimal('500000'):
            wallet.balance = Decimal('500000')
            wallet.save()
        _report('client_demo (client)', created)

        # ── Demo Approved Technician ─────────────────────────────
        tech_user, created = self._create_or_update_user(
            'tech_demo', 'tech.demo@tiqani.local', 'TechDemo123!', 'technician',
        )
        tech_user.phone_number = '07700000905'
        tech_user.date_of_birth = timezone.now().date().replace(year=1992, month=3, day=20)
        tech_user.gender = 'male'
        tech_user.save()
        tech_profile, _ = TechnicianProfile.objects.update_or_create(
            user=tech_user,
            defaults={
                'approved': True,
                'is_available': True,
                'job_title': 'Full-Stack Developer & IT Specialist',
                'about': 'Expert technician with 8+ years of experience in software development, networking, and hardware repair.',
                'years_of_expertise': 8,
                'rate': Decimal('4.50'),
            },
        )
        Wallet.objects.get_or_create(user=tech_user)
        _report('tech_demo (approved technician)', created)

        # ── Demo Pending Technician ──────────────────────────────
        pending_user, created = self._create_or_update_user(
            'tech_pending_demo', 'tech.pending.demo@tiqani.local',
            'TechPendingDemo123!', 'technician',
        )
        pending_user.phone_number = '07700000906'
        pending_user.date_of_birth = timezone.now().date().replace(year=1998, month=7, day=10)
        pending_user.gender = 'female'
        pending_user.save()
        TechnicianProfile.objects.update_or_create(
            user=pending_user,
            defaults={
                'approved': False,
                'is_available': False,
                'job_title': 'Junior Electrician',
                'about': 'New technician looking for opportunities.',
                'years_of_expertise': 1,
            },
        )
        _report('tech_pending_demo (pending technician)', created)

        # ── Categories & Skills ──────────────────────────────────
        cat_data = {
            'Home Maintenance': ['General Repair', 'Painting', 'Cleaning'],
            'Electrical': ['Electrical Wiring', 'AC Repair', 'Switch Installation'],
            'Plumbing': ['Pipe Leak Fix', 'Drain Cleaning', 'Water Heater Repair'],
            'Mobile Repair': ['Android Repair', 'Screen Replacement', 'Battery Replacement'],
            'Computer Repair': ['Laptop Maintenance', 'Software Installation', 'Data Recovery'],
        }
        for cat_name, skills in cat_data.items():
            cat, _ = Category.objects.get_or_create(name=cat_name)
            for skill_name in skills:
                Skill.objects.get_or_create(name=skill_name, category=cat)
        self.stdout.write(self.style.SUCCESS(f"  ✓  {len(cat_data)} categories with skills"))
        results['existing'] += len(cat_data)

        # ── Platform Fee Config ──────────────────────────────────
        from django.core.management import call_command
        call_command('seed_platform_fees')
        self.stdout.write(self.style.SUCCESS("  ✓  Platform fee config seeded"))
        results['existing'] += 1

        # ── Demo Contracts ───────────────────────────────────────
        client_profile = ClientProfile.objects.get(user=client_user)
        tech_profile = TechnicianProfile.objects.get(user=tech_user)

        # Completed contract
        completed, _ = Contract.objects.update_or_create(
            contract_reference='DEMO-COMPLETED-001',
            defaults={
                'client': client_profile,
                'technician': tech_profile,
                'work_description': 'Website development and deployment — completed demo contract',
                'agreed_amount': Decimal('250000'),
                'stage_number': 3,
                'start_date': timezone.now().date() - timezone.timedelta(days=30),
                'duration_days': 14,
                'status': 'completed',
                'client_accepted': True,
                'technician_accepted': True,
            },
        )
        _report(f'Contract {completed.contract_reference}', False)

        # Draft contract
        draft, _ = Contract.objects.update_or_create(
            contract_reference='DEMO-DRAFT-001',
            defaults={
                'client': client_profile,
                'technician': tech_profile,
                'work_description': 'Mobile app bug fixes and performance optimization',
                'agreed_amount': Decimal('150000'),
                'stage_number': 2,
                'start_date': timezone.now().date() + timezone.timedelta(days=7),
                'duration_days': 10,
                'status': 'draft',
            },
        )
        _report(f'Contract {draft.contract_reference}', False)

        # In-progress contract
        in_progress, _ = Contract.objects.update_or_create(
            contract_reference='DEMO-ACTIVE-001',
            defaults={
                'client': client_profile,
                'technician': tech_profile,
                'work_description': 'Weekly website maintenance and content updates',
                'agreed_amount': Decimal('100000'),
                'stage_number': 2,
                'start_date': timezone.now().date() - timezone.timedelta(days=5),
                'duration_days': 30,
                'status': 'in_progress',
                'client_accepted': True,
                'technician_accepted': True,
            },
        )
        _report(f'Contract {in_progress.contract_reference}', False)

        # ── Demo Review ──────────────────────────────────────────
        review, _ = Review.objects.update_or_create(
            contract=completed,
            defaults={
                'reviewer': client_user,
                'technician': tech_profile,
                'rating': 5,
                'work_quality_rating': 5,
                'communication_rating': 4,
                'timeliness_rating': 5,
                'professionalism_rating': 5,
                'title': 'Excellent work!',
                'comment': 'The technician completed all work on time and exceeded expectations. Highly recommended!',
                'is_public': True,
                'is_verified': True,
                'technician_response': 'Thank you! It was a pleasure working with you.',
            },
        )
        _report(f'Review for contract {completed.contract_reference}', False)

        # ── Demo Notifications ───────────────────────────────────
        # Unread for client
        create_notification(
            recipient=client_user,
            notification_type='contract_completed',
            title='Contract Completed',
            message=f'Contract {completed.contract_reference} has been completed.',
            target_type='contract',
            target_id=completed.id,
        )
        # Read notification for client
        read_notif = create_notification(
            recipient=client_user,
            notification_type='system',
            title='Welcome to Tiqani!',
            message='Your account has been created successfully.',
        )
        if read_notif:
            read_notif.mark_read()
        # Unread for technician
        create_notification(
            recipient=tech_user,
            notification_type='review_created',
            title='New Review Received',
            message=f'You received a 5-star review from {client_user.username}.',
            target_type='review',
            target_id=review.id,
        )
        self.stdout.write(self.style.SUCCESS("  ✓  Demo notifications created"))
        results['existing'] += 3

        # ── Dealership Demo ──────────────────────────────────────
        dealership_user, created = self._create_or_update_user(
            'dealership_demo', 'dealership.demo@tiqani.local', 'DealershipDemo123!',
            'dealership',
        )
        dealership_user.phone_number = '07700000907'
        dealership_user.save()

        profile, _ = DealershipProfile.objects.update_or_create(
            user=dealership_user,
            defaults={
                'business_name': 'Tiqani Demo Dealership',
                'owner_name': 'Ali Demo',
                'phone': '07700000907',
                'governorate': 'Baghdad',
                'address': 'Demo Dealership Address, Baghdad',
                'status': DealershipProfile.Status.ACTIVE,
                'active': True,
                'usage_limit_percent': Decimal('80.00'),
                'recharge_enabled': True,
                'cashout_enabled': True,
            },
        )
        _report('dealership_demo (active dealership)', created)

        # Verified guarantee
        guarantee, _ = DealershipGuarantee.objects.update_or_create(
            dealership=profile,
            cash_amount=Decimal('50000000'),  # 50M IQD cash
            bank_check_amount=Decimal('0'),
            legal_document_amount=Decimal('0'),
            defaults={
                'status': DealershipGuarantee.Status.VERIFIED,
                'total_guarantee_amount': Decimal('50000000'),
            },
        )
        _report('Dealership guarantee 50M IQD (verified)', False)

        # Fee config
        DealershipRechargeFeeConfig.objects.update_or_create(
            fee_percent=Decimal('1.00'),
            defaults={
                'default_fee_mode': DealershipRechargeFeeConfig.FeeMode.ADDED_ON_TOP,
                'is_active': True,
            },
        )
        self.stdout.write(self.style.SUCCESS("  ✓  Dealership fee config (1%)"))

        # Sample recharge
        client_profile = ClientProfile.objects.get(user=client_user)
        try:
            recharge, _ = create_recharge(
                dealership=profile,
                client=client_user,
                fee_mode=DealershipRechargeFeeConfig.FeeMode.ADDED_ON_TOP,
                wallet_credit_amount=Decimal('100000'),  # 100K IQD
                created_by=dealership_user,
            )
            _report(f'Recharge {recharge.wallet_credit_amount} IQD → {client_user.username}', False)
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"  ⚠  Recharge skipped: {exc}"))

        self.stdout.write(self.style.SUCCESS("  ✓  Dealership demo data seeded"))
        results['existing'] += 2

        # ── Summary ──────────────────────────────────────────────
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS(
            f"Demo data seeded: {results['created']} created, {results['existing']} existing/skipped"
        ))
        self.stdout.write('\nDemo credentials:')
        self.stdout.write('  admin_demo / AdminDemo123!')
        self.stdout.write('  finance_demo / FinanceDemo123!')
        self.stdout.write('  moderator_demo / ModeratorDemo123!')
        self.stdout.write('  account_manager_demo / AccountManagerDemo123!')
        self.stdout.write('  client_demo / ClientDemo123!')
        self.stdout.write('  tech_demo / TechDemo123!')
        self.stdout.write('  tech_pending_demo / TechPendingDemo123!')
        self.stdout.write('  dealership_demo / DealershipDemo123!')
