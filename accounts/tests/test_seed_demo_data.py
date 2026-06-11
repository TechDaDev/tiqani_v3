"""Tests for the seed_demo_data management command."""

from io import StringIO
from django.core.management import call_command
from django.test import TestCase
from django.contrib.auth import get_user_model
from category.models import Category
from wallet.models import PlatformFeeConfig

User = get_user_model()


class SeedDemoDataCommandTest(TestCase):

    def test_command_runs_without_error(self):
        out = StringIO()
        call_command('seed_demo_data', stdout=out)
        output = out.getvalue()
        self.assertIn('Demo data seeded', output)

    def test_command_is_idempotent(self):
        out1 = StringIO()
        call_command('seed_demo_data', stdout=out1)
        first_output = out1.getvalue()

        out2 = StringIO()
        call_command('seed_demo_data', stdout=out2)
        second_output = out2.getvalue()

        # Both runs should succeed
        self.assertIn('Demo data seeded', first_output)
        self.assertIn('Demo data seeded', second_output)

    def test_demo_users_exist(self):
        call_command('seed_demo_data', stdout=StringIO())

        demo_usernames = [
            'admin_demo', 'finance_demo', 'moderator_demo',
            'account_manager_demo', 'client_demo', 'tech_demo', 'tech_pending_demo',
        ]
        for username in demo_usernames:
            exists = User.objects.filter(username=username).exists()
            self.assertTrue(exists, f'Demo user {username} should exist')

    def test_active_platform_fee_config_exists(self):
        call_command('seed_demo_data', stdout=StringIO())
        self.assertTrue(
            PlatformFeeConfig.objects.filter(is_active=True).exists(),
            'Active platform fee config should exist',
        )

    def test_categories_exist(self):
        call_command('seed_demo_data', stdout=StringIO())
        # At least some categories should exist
        self.assertGreaterEqual(Category.objects.count(), 1)
