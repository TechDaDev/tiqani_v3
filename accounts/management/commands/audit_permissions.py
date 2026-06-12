"""
Management command to audit permission class configuration.

Checks that known permission classes are importable and that critical
admin/finance views declare explicit permission classes.

Usage:
    python manage.py audit_permissions
    python manage.py audit_permissions --json
"""

import json

from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import resolve, Resolver404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView


# Endpoints that should NOT use AllowAny
SENSITIVE_ENDPOINTS = [
    "api/auth/login/",
    "api/auth/register/",
    "api/wallet/",
    "api/wallet/transactions/",
    "api/wallet/withdraw/",
    "api/dealership/",
    "api/dealership/recharge/",
    "api/dealership/cashout/",
    "api/admin/",
    "api/notifications/",
    "api/accounts/",
]

# Endpoints that are intentionally public
PUBLIC_ENDPOINTS = [
    "api/health/",
    "api/health/live/",
    "api/health/ready/",
    "api/health/deep/",
    "api/categories/",
    "api/schema/",
]


def _resolve_permission_classes(path):
    """Try to resolve a URL path and return its view's permission_classes."""
    try:
        view_func = resolve("/" + path).func
        # DRF viewsets have .cls or .view_class; function views use .view
        view_class = getattr(view_func, "view_class", None) or getattr(
            view_func, "cls", None
        )
        if view_class and issubclass(view_class, APIView):
            return getattr(view_class, "permission_classes", None)
        return None
    except (Resolver404, Exception):
        return None


KNOWN_PERMISSION_CLASSES = [
    "rest_framework.permissions.AllowAny",
    "rest_framework.permissions.IsAuthenticated",
    "rest_framework.permissions.IsAdminUser",
    "accounts.permissions.IsClient",
    "accounts.permissions.IsTechnician",
    "accounts.permissions.IsOwnerOrAdmin",
    "contract.permissions.IsContractParticipantOrAdmin",
    "contract.permissions.IsContractClient",
    "contract.permissions.IsContractTechnician",
    "contract.permissions.IsAdminUser",
    "dealership.permissions.IsDealership",
    "dealership.permissions.IsClientUser",
    "dealership.permissions.IsDealershipOrAdmin",
    "dealership.permissions.IsSystemAdminOrFinance",
    "dealership.permissions.IsAccountManagerOrFinance",
    "dealership.permissions.IsContentModeratorDenied",
    "notification.permissions.IsNotificationOwner",
    "notification.permissions.IsAdminOrStaffForActivity",
    "ratereview.permissions.IsReviewOwner",
    "ratereview.permissions.IsReviewedTechnician",
    "ratereview.permissions.IsPlatformAdminOrStaff",
    "ratereview.permissions.IsAuthenticatedOrStaffForPost",
    "dashboard.permissions.IsPlatformAdmin",
    "dashboard.permissions.IsSystemAdmin",
    "dashboard.permissions.IsFinanceAdmin",
    "dashboard.permissions.IsAccountManager",
    "dashboard.permissions.IsContentModerator",
    "dashboard.permissions.IsAdminOrStaff",
]


class Command(BaseCommand):
    help = "Audit permission class configuration."

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", help="Output as JSON.")

    def handle(self, *args, **options):
        results = {
            "permission_classes_importable": [],
            "sensitive_endpoints": [],
        }

        # Check permission classes are importable
        for perm_path in KNOWN_PERMISSION_CLASSES:
            try:
                from importlib import import_module

                module_path, class_name = perm_path.rsplit(".", 1)
                module = import_module(module_path)
                getattr(module, class_name)
                results["permission_classes_importable"].append({
                    "class": perm_path,
                    "status": "ok",
                })
            except (ImportError, AttributeError) as e:
                results["permission_classes_importable"].append({
                    "class": perm_path,
                    "status": "error",
                    "detail": str(e),
                })

        # Check sensitive endpoints for explicit permission classes
        for path in SENSITIVE_ENDPOINTS:
            perms = _resolve_permission_classes(path)
            if perms is None:
                results["sensitive_endpoints"].append({
                    "path": path,
                    "status": "unresolved",
                })
            elif AllowAny in perms:
                results["sensitive_endpoints"].append({
                    "path": path,
                    "status": "warning",
                    "detail": "AllowAny on sensitive endpoint",
                })
            else:
                results["sensitive_endpoints"].append({
                    "path": path,
                    "status": "ok",
                })

        if options["json"]:
            self.stdout.write(json.dumps(results, indent=2))
        else:
            self.stdout.write(self.style.MIGRATE_HEADING("Permission Audit"))
            self.stdout.write("=" * 55)
            self.stdout.write("\nPermission Classes:\n")
            for pc in results["permission_classes_importable"]:
                style = self.style.SUCCESS if pc["status"] == "ok" else self.style.ERROR
                self.stdout.write(f"  {style('✓') if pc['status'] == 'ok' else style('✗')}  {pc['class']}")
            self.stdout.write("\nSensitive Endpoints:\n")
            for ep in results["sensitive_endpoints"]:
                if ep["status"] == "ok":
                    self.stdout.write(f"  {self.style.SUCCESS('✓')}  /{ep['path']}")
                elif ep["status"] == "warning":
                    self.stdout.write(f"  {self.style.WARNING('⚠')}  /{ep['path']}  {ep.get('detail', '')}")
                else:
                    self.stdout.write(f"  {self.style.WARNING('?')}  /{ep['path']}  (unresolved)")
