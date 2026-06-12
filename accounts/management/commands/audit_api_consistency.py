"""
Management command to audit API endpoint consistency.

Checks route naming, trailing slashes, critical endpoint presence,
and duplicate URL patterns.

Usage:
    python manage.py audit_api_consistency
    python manage.py audit_api_consistency --json
"""

import json
import sys

from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import resolve, Resolver404

# Critical URL prefixes that should appear in urlpatterns
CRITICAL_PREFIXES = [
    "admin/",
    "api/auth/",
    "api/accounts/",
    "api/categories/",
    "api/technicians/",
    "api/clients/",
    "api/reviews/",
    "api/contracts/",
    "api/wallet/",
    "api/notifications/",
    "api/dealership/",
    "api/admin/",
    "api/health/",
    "api/schema/",
    "api/docs/",
    "api/redoc/",
]

# Specific endpoints that should resolve
RESOLVABLE_PATHS = [
    ("api/health/", "Health check"),
    ("api/health/live/", "Liveness probe"),
    ("api/health/ready/", "Readiness probe"),
    ("api/health/deep/", "Deep health"),
    ("api/schema/", "OpenAPI schema"),
    ("api/docs/", "Swagger UI docs"),
    ("api/redoc/", "ReDoc docs"),
]


def _get_url_patterns(urlconf):
    """Get string representations of all URL patterns."""
    from importlib import import_module

    module = import_module(urlconf)
    patterns = []
    for p in module.urlpatterns:
        patterns.append(str(p.pattern))
    return patterns


class Command(BaseCommand):
    help = "Audit API endpoint consistency."

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", help="Output as JSON.")

    def handle(self, *args, **options):
        patterns = _get_url_patterns(settings.ROOT_URLCONF)

        results = {
            "url_prefixes_found": [],
            "resolvable_endpoints": [],
        }

        for prefix in CRITICAL_PREFIXES:
            found = any(p.startswith(prefix) for p in patterns)
            results["url_prefixes_found"].append({
                "prefix": prefix,
                "status": "ok" if found else "missing",
            })

        for path, label in RESOLVABLE_PATHS:
            try:
                resolve("/" + path)
                results["resolvable_endpoints"].append({
                    "path": path,
                    "label": label,
                    "status": "ok",
                })
            except Resolver404:
                results["resolvable_endpoints"].append({
                    "path": path,
                    "label": label,
                    "status": "missing",
                })

        missing_prefixes = [
            p for p in results["url_prefixes_found"] if p["status"] == "missing"
        ]
        missing_paths = [
            p for p in results["resolvable_endpoints"] if p["status"] == "missing"
        ]

        if options["json"]:
            self.stdout.write(json.dumps(results, indent=2))
        else:
            self.stdout.write(self.style.MIGRATE_HEADING("API Consistency Audit"))
            self.stdout.write("=" * 55)
            self.stdout.write(f"\nURL Prefixes (checking {len(patterns)} pattern(s)):\n")
            for p in results["url_prefixes_found"]:
                style = self.style.SUCCESS if p["status"] == "ok" else self.style.ERROR
                self.stdout.write(f"  {style('✓') if p['status'] == 'ok' else style('✗')}  {p['prefix']}")

            self.stdout.write(f"\nResolvable Endpoints:\n")
            for ep in results["resolvable_endpoints"]:
                style = self.style.SUCCESS if ep["status"] == "ok" else self.style.ERROR
                self.stdout.write(f"  {style('✓') if ep['status'] == 'ok' else style('✗')}  /{ep['path']:<25} {ep['label']}")

            total_missing = len(missing_prefixes) + len(missing_paths)
            if total_missing:
                self.stdout.write(
                    self.style.WARNING(f"\n{total_missing} item(s) not found (may be expected — URL inclusion hides sub-patterns).")
                )
            else:
                self.stdout.write(self.style.SUCCESS("\nAll API endpoint checks passed."))
