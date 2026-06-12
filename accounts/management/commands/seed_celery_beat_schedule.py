"""
Management command to seed default Celery Beat periodic tasks.

Idempotent — safe to run multiple times.
Uses update_or_create to avoid duplicates.

Usage:
    python manage.py seed_celery_beat_schedule
"""

import json
from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule


class Command(BaseCommand):
    help = "Seed default Celery Beat periodic task schedule."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding Celery Beat schedule..."))
        results = {"created": 0, "updated": 0}

        # ── Interval: every 10 minutes ─────────────────────────
        interval_10min, _ = IntervalSchedule.objects.get_or_create(
            every=10,
            period=IntervalSchedule.MINUTES,
        )

        # ── Interval: every hour ───────────────────────────────
        interval_1h, _ = IntervalSchedule.objects.get_or_create(
            every=1,
            period=IntervalSchedule.HOURS,
        )

        # ── Interval: every 6 hours ────────────────────────────
        interval_6h, _ = IntervalSchedule.objects.get_or_create(
            every=6,
            period=IntervalSchedule.HOURS,
        )

        # ── Interval: every day ────────────────────────────────
        interval_1d, _ = IntervalSchedule.objects.get_or_create(
            every=1,
            period=IntervalSchedule.DAYS,
        )

        # ── Crontab: daily at 3 AM ─────────────────────────────
        daily_3am, _ = CrontabSchedule.objects.get_or_create(
            minute="0",
            hour="3",
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
        )

        # ── Crontab: hourly ────────────────────────────────────
        hourly, _ = CrontabSchedule.objects.get_or_create(
            minute="0",
            hour="*",
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
        )

        tasks = [
            {
                "name": "OTP Cleanup — Expired OTPs",
                "task": "accounts.tasks.cleanup_expired_otps_task",
                "crontab": daily_3am,
                "description": "Mark expired/unused OTPs as used after retention period.",
            },
            {
                "name": "Cash-out Code Expiry",
                "task": "dealership.tasks.expire_old_cashout_codes_task",
                "interval": interval_10min,
                "description": "Mark cash-out codes as expired past their expiry time.",
            },
            {
                "name": "Notification Cleanup (Dry Run)",
                "task": "notification.tasks.cleanup_old_read_notifications_task",
                "crontab": daily_3am,
                "kwargs": {"dry_run": True},
                "description": "Report old read notifications (dry run — no deletion).",
            },
            {
                "name": "Dealership Threshold Alerts",
                "task": "dealership.tasks.send_dealership_threshold_alerts_task",
                "interval": interval_1h,
                "description": "Alert admins when dealerships approach or reach credit limit.",
            },
            {
                "name": "Dealership Guarantee Expiry Alerts",
                "task": "dealership.tasks.send_dealership_guarantee_expiry_alerts_task",
                "interval": interval_1d,
                "description": "Alert dealerships when guarantees are expiring within 30 days.",
            },
            {
                "name": "Media Orphan Report (Dry Run)",
                "task": "tiqani_v3.tasks.generate_media_orphan_report_task",
                "interval": interval_6h,
                "description": "Generate report of orphaned media files (dry run only).",
            },
            {
                "name": "Celery Health Check",
                "task": "tiqani_v3.tasks.celery_health_check_task",
                "interval": interval_10min,
                "description": "Periodic health check to verify Celery worker is responsive.",
            },
        ]

        for t_def in tasks:
            defaults = {
                "task": t_def["task"],
                "description": t_def["description"],
                "enabled": True,
            }
            if "interval" in t_def:
                defaults["interval"] = t_def["interval"]
            if "crontab" in t_def:
                defaults["crontab"] = t_def["crontab"]
            if "kwargs" in t_def:
                defaults["kwargs"] = json.dumps(t_def["kwargs"])

            task, created = PeriodicTask.objects.update_or_create(
                name=t_def["name"],
                defaults=defaults,
            )
            if created:
                results["created"] += 1
                self.stdout.write(self.style.SUCCESS(f"  ✓ CREATED {t_def['name']}"))
            else:
                results["updated"] += 1
                self.stdout.write(self.style.WARNING(f"  ✓ EXISTS {t_def['name']}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSchedule seeded: {results['created']} created, {results['updated']} updated."
            )
        )
