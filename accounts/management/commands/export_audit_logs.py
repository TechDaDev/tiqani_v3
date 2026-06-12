"""
Management command to export security audit events as JSON or CSV.

Sources:
  - Log entries from the ``security`` logger (emitted by
    ``tiqani_v3.security_events.log_security_event``).
  - Token blacklist events (token refresh, logout).
  - User model changes (last_login, date_joined).

Usage:
    python manage.py export_audit_logs --days 30 --format json
    python manage.py export_audit_logs --days 7 --format csv > audit.csv
"""

import csv
import io
import json
import logging
from datetime import timedelta

from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = "Export audit-log events (log entries, token events, user activity)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Number of days to look back (default: 30).",
        )
        parser.add_argument(
            "--format",
            choices=["json", "csv"],
            default="json",
            help="Output format (default: json).",
        )

    def _collect_admin_logs(self, since):
        """Return admin LogEntry records created since *since*."""
        entries = []
        for log in LogEntry.objects.filter(action_time__gte=since).select_related("user").iterator():
            entries.append({
                "timestamp": log.action_time.isoformat(),
                "source": "admin_log",
                "user_id": log.user_id,
                "username": str(log.user),
                "action": log.get_action_flag_display(),
                "content_type": str(log.content_type),
                "object_id": str(log.object_id),
                "object_repr": log.object_repr,
                "change_message": log.change_message,
            })
        return entries

    def _collect_token_events(self, since):
        """Return token blacklist events created since *since*."""
        entries = []
        for tok in OutstandingToken.objects.filter(created_at__gte=since).iterator():
            entries.append({
                "timestamp": tok.created_at.isoformat(),
                "source": "token_issued",
                "user_id": tok.user_id,
                "token_id": str(tok.jti),
            })
        for bt in BlacklistedToken.objects.filter(
            blacklisted_at__gte=since,
        ).select_related("token").iterator():
            entries.append({
                "timestamp": bt.blacklisted_at.isoformat(),
                "source": "token_blacklisted",
                "user_id": bt.token.user_id,
                "token_id": str(bt.token.jti),
            })
        return entries

    def _collect_user_activity(self, since):
        """Return user login / join events since *since*."""
        entries = []
        for u in User.objects.filter(last_login__gte=since).iterator():
            entries.append({
                "timestamp": u.last_login.isoformat(),
                "source": "user_login",
                "user_id": u.pk,
                "email": u.email,
            })
        for u in User.objects.filter(date_joined__gte=since).iterator():
            entries.append({
                "timestamp": u.date_joined.isoformat(),
                "source": "user_registered",
                "user_id": u.pk,
                "email": u.email,
            })
        return entries

    def handle(self, *args, **options):
        days = options["days"]
        fmt = options["format"]
        since = timezone.now() - timedelta(days=days)

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Exporting audit logs (last {days} days, since {since.date()})"
            ),
            ending="\n",
        )

        entries = []
        entries.extend(self._collect_admin_logs(since))
        entries.extend(self._collect_token_events(since))
        entries.extend(self._collect_user_activity(since))

        # Sort newest first
        entries.sort(key=lambda e: e["timestamp"], reverse=True)

        self.stdout.write(f"  {len(entries)} event(s) found.\n")

        if fmt == "json":
            output = json.dumps(entries, indent=2, default=str)
            self.stdout.write(output)
        else:
            buf = io.StringIO()
            if entries:
                writer = csv.DictWriter(buf, fieldnames=entries[0].keys())
                writer.writeheader()
                writer.writerows(entries)
            self.stdout.write(buf.getvalue())
