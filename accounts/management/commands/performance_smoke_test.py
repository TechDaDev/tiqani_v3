"""
Management command to run performance smoke tests on critical read endpoints.

Usage:
    python manage.py performance_smoke_test
    python manage.py performance_smoke_test --iterations 10
    python manage.py performance_smoke_test --iterations 3 --json
"""

import json
import time

from django.core.management.base import BaseCommand
from django.test import RequestFactory
from django.urls import resolve


SMOKE_ENDPOINTS = [
    ("/api/health/", "Health"),
    ("/api/health/live/", "Liveness"),
    ("/api/health/ready/", "Readiness"),
    ("/api/health/deep/", "Deep Health"),
    ("/api/categories/", "Categories"),
]


class Command(BaseCommand):
    help = "Run performance smoke tests on critical read endpoints."

    def add_arguments(self, parser):
        parser.add_argument(
            "--iterations",
            type=int,
            default=5,
            help="Number of iterations per endpoint (default: 5).",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output results as JSON.",
        )

    def handle(self, *args, **options):
        iterations = options["iterations"]
        factory = RequestFactory()
        results = []

        for path, label in SMOKE_ENDPOINTS:
            timings = []
            last_status = None
            for _ in range(iterations):
                request = factory.get(path)
                try:
                    resolved = resolve(path)
                    start = time.perf_counter()
                    response = resolved.func(request)
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    timings.append(elapsed_ms)
                    last_status = response.status_code
                except Exception as exc:
                    timings.append(0)
                    last_status = str(exc)

            if timings:
                avg_ms = sum(timings) / len(timings)
                max_ms = max(timings)
            else:
                avg_ms = 0
                max_ms = 0

            results.append({
                "endpoint": path,
                "label": label,
                "status_code": last_status,
                "avg_ms": round(avg_ms, 2),
                "max_ms": round(max_ms, 2),
                "iterations": iterations,
            })

        if options["json"]:
            self.stdout.write(json.dumps(results, indent=2))
        else:
            self.stdout.write(self.style.MIGRATE_HEADING("Performance Smoke Test"))
            self.stdout.write("=" * 55)
            self.stdout.write(f"{'Endpoint':<25} {'Status':>8} {'Avg (ms)':>10} {'Max (ms)':>10}")
            self.stdout.write("-" * 55)
            for r in results:
                self.stdout.write(
                    f"{r['endpoint']:<25} {str(r['status_code']):>8} {r['avg_ms']:>10.2f} {r['max_ms']:>10.2f}"
                )
            self.stdout.write(self.style.SUCCESS(f"\nSmoke test complete — {len(results)} endpoint(s) tested."))
