"""
Management command to seed default platform fee configuration.

Usage:
    python manage.py seed_platform_fees
    python manage.py seed_platform_fees --force
"""

from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from wallet.models import PlatformFeeConfig


class Command(BaseCommand):
    help = "Seed default PlatformFeeConfig (10% tech / 5% client = 15% total)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Deactivate existing configs and create a new default",
        )

    def handle(self, *args, **options):
        existing = PlatformFeeConfig.objects.filter(is_active=True).first()
        if existing and not options["force"]:
            self.stdout.write(
                self.style.WARNING(
                    f"Active fee config already exists: {existing}. "
                    "Use --force to deactivate and create a new one."
                )
            )
            return

        if options["force"]:
            PlatformFeeConfig.objects.filter(is_active=True).update(is_active=False)
            self.stdout.write(self.style.WARNING("Deactivated existing fee configs."))

        config = PlatformFeeConfig.objects.create(
            name="Default 15% Platform Fee",
            technician_commission_rate=Decimal("10.00"),
            client_service_fee_rate=Decimal("5.00"),
            is_active=True,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Created fee config: {config}"
            )
        )
