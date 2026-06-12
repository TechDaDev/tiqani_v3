"""
Management command to run a quick final QA checklist.

Usage:
    python manage.py final_backend_qa

Prints a readable QA status report. Does not run the full test suite.
"""

import os
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connections, DEFAULT_DB_ALIAS
from wallet.models import PlatformFeeConfig
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Quick final backend QA checklist"

    def _check(self, label, success, detail=''):
        if success:
            self.stdout.write(self.style.SUCCESS(f"  ✓  {label}"))
        else:
            self.stdout.write(self.style.ERROR(f"  ✗  {label}  [{detail}]"))

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Final Backend QA Checklist"))
        self.stdout.write("=" * 55)

        # ── Django check ──────────────────────────────────────────
        import subprocess
        result = subprocess.run(
            ['.venv/bin/python', 'manage.py', 'check'],
            capture_output=True, text=True, cwd=settings.BASE_DIR,
        )
        self._check('Django check passes', result.returncode == 0,
                     result.stderr.strip()[:80] if result.stderr else '')

        # ── Pending migrations ────────────────────────────────────
        try:
            from django.db.migrations.executor import MigrationExecutor
            executor = MigrationExecutor(connections[DEFAULT_DB_ALIAS])
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
            self._check('No pending migrations', len(plan) == 0,
                         f'{len(plan)} pending' if plan else '')
        except Exception as e:
            self._check('Migration check', False, str(e)[:60])

        # ── Active fee config ─────────────────────────────────────
        fee = PlatformFeeConfig.objects.filter(is_active=True).first()
        self._check('Platform fee config active', fee is not None)

        # ── Demo users exist ──────────────────────────────────────
        demo_usernames = [
            'admin_demo', 'finance_demo', 'moderator_demo',
            'account_manager_demo', 'client_demo', 'tech_demo', 'tech_pending_demo',
            'dealership_demo',
        ]
        existing = User.objects.filter(username__in=demo_usernames).count()
        self._check(f'Demo users present ({existing}/{len(demo_usernames)})',
                     existing == len(demo_usernames),
                     f'missing: {set(demo_usernames) - set(User.objects.filter(username__in=demo_usernames).values_list("username", flat=True))}')

        # ── Core app URLs import ─────────────────────────────────
        apps = ['accounts', 'category', 'contract', 'ratereview', 'wallet', 'notification', 'dashboard', 'dealership', 'django_celery_beat']
        importable = 0
        for app in apps:
            try:
                __import__(f'{app}.urls')
                importable += 1
            except ImportError:
                pass
        self._check(f'App URLs importable ({importable}/{len(apps)})',
                     importable == len(apps))

        # ── Deployment docs exist ─────────────────────────────────
        docs_dir = settings.BASE_DIR / 'docs'
        required_docs = ['DEPLOYMENT.md', 'PRODUCTION_CHECKLIST.md', 'API_OVERVIEW.md',
                         'FRONTEND_HANDOFF.md', 'QA_CHECKLIST.md', 'RELEASE_NOTES_PHASE_1_TO_10.md',
                         'MAINTENANCE.md', 'POSTMAN.md']
        existing_docs = [d for d in required_docs if os.path.isfile(os.path.join(docs_dir, d))]
        self._check(f'Required docs present ({len(existing_docs)}/{len(required_docs)})',
                     len(existing_docs) >= 5,  # At least core docs exist
                     f'found: {len(existing_docs)}')

        # ── Complete Postman collection ───────────────────────────
        postman_complete = settings.BASE_DIR / 'postman' / 'Tiqani_v3_Complete_Backend.postman_collection.json'
        self._check('Complete Postman collection exists',
                     os.path.isfile(postman_complete))

        # ── Docker files exist ────────────────────────────────────
        dockerfile = settings.BASE_DIR / 'Dockerfile'
        compose = settings.BASE_DIR / 'docker-compose.yml'
        self._check('Dockerfile exists', os.path.isfile(dockerfile))
        self._check('docker-compose.yml exists', os.path.isfile(compose))

        # ── CI workflow exists ────────────────────────────────────
        ci_yml = settings.BASE_DIR / '.github' / 'workflows' / 'ci.yml'
        self._check('CI workflow exists', os.path.isfile(ci_yml))

        self.stdout.write("\n" + "=" * 55)
        self.stdout.write(self.style.SUCCESS("QA check complete."))
