"""
Management command to export API route inventory.

Usage:
    python manage.py export_api_routes
    python manage.py export_api_routes --output docs/API_ROUTES_GENERATED.md
"""

import os
import re
from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import URLResolver, URLPattern

SKIP_PREFIXES = ('admin/', '^media/', '^static/')


def _clean_route_path(path):
    """Clean up router-generated regex patterns into readable paths."""
    path = path.replace('^', '').replace('$', '')
    path = re.sub(r'\(\?P<\w+>\[\.\^/\]\+\+\)', '{id}', path)
    path = re.sub(r'\(\?P<\w+>\[\./\w\]\+\)', '{id}', path)
    path = re.sub(r'\(\?P<\w+>\[/\.\]\+\)', '{id}', path)
    path = re.sub(r'\(\?P<\w+>\.\*\)', '{path}', path)
    path = re.sub(r'\(\?P<pk>\[\.\^/\]\+\)', '{id}', path)
    path = re.sub(r'\(\?P<pk>\[/\.\]\+\)', '{id}', path)
    path = path.replace('//', '/')
    return path


def _should_skip(route):
    for prefix in SKIP_PREFIXES:
        if route.startswith(prefix):
            return True
    return False


class Command(BaseCommand):
    help = "Export API route inventory to console or markdown file"

    def add_arguments(self, parser):
        parser.add_argument('--output', type=str, help='Output file path (optional)')

    def _collect_routes(self, urlpatterns, prefix='', routes=None):
        if routes is None:
            routes = []
        for pattern in urlpatterns:
            if isinstance(pattern, URLResolver):
                new_prefix = prefix + str(pattern.pattern)
                self._collect_routes(pattern.url_patterns, new_prefix, routes)
            elif isinstance(pattern, URLPattern):
                route = str(pattern.pattern)
                full_path = prefix + route
                if _should_skip(full_path):
                    continue
                name = pattern.name or ''
                method_hint = ''
                if hasattr(pattern.callback, 'view_class'):
                    view_cls = pattern.callback.view_class
                    raw = getattr(view_cls, 'http_method_names', [])
                    if hasattr(view_cls, 'allowed_methods'):
                        try:
                            am = view_cls.allowed_methods
                            if am:
                                method_hint = ', '.join(am)
                        except Exception:
                            pass
                    if not method_hint and raw:
                        irrelevant = {'head', 'options', 'trace'}
                        http = [m.upper() for m in raw if m not in irrelevant]
                        if http and len(http) < 4:
                            method_hint = ', '.join(http)
                clean_path = _clean_route_path(full_path)
                routes.append({
                    'route': clean_path,
                    'name': name,
                    'methods': method_hint,
                })
        return routes

    def handle(self, *args, **options):
        from tiqani_v3 import urls as root_urls
        routes = self._collect_routes(root_urls.urlpatterns)

        output_path = options.get('output')

        if output_path:
            lines = []
            lines.append("# API Routes - tiqani_v3 (auto-generated)\n\n")
            lines.append(f"**{len(routes)} API routes** (Django admin, static/media excluded)\n\n")
            lines.append("| # | Method | Route | Name |")
            lines.append("|---|--------|-------|------|")
            for i, r in enumerate(routes, 1):
                methods = r['methods'] or 'varies'
                lines.append(f"| {i} | {methods} | `{r['route']}` | {r['name']} |")
            content = '\n'.join(lines) + '\n'

            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(content)
            self.stdout.write(self.style.SUCCESS(f"Routes written to {output_path}"))
        else:
            self.stdout.write(self.style.MIGRATE_HEADING(f"API Routes ({len(routes)} total)"))
            fmt = "{:<5} {:<10} {:<65} {:<30}"
            self.stdout.write(fmt.format("#", "Method", "Route", "Name"))
            self.stdout.write("-" * 110)
            for i, r in enumerate(routes, 1):
                methods = r['methods'] or 'varies'
                self.stdout.write(fmt.format(str(i), methods, r['route'][:63], r['name'][:28]))
