"""
Management command to export API route inventory.

Usage:
    python manage.py export_api_routes
    python manage.py export_api_routes --output docs/API_ROUTES_GENERATED.md
"""

import os
from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import URLResolver, URLPattern


class Command(BaseCommand):
    help = "Export API route inventory to console or markdown file"

    def add_arguments(self, parser):
        parser.add_argument('--output', type=str, help='Output file path (optional)')

    def _collect_routes(self, urlpatterns, prefix='', routes=None):
        if routes is None:
            routes = []
        for pattern in urlpatterns:
            if isinstance(pattern, URLResolver):
                # Recurse into included URL confs
                new_prefix = prefix + str(pattern.pattern)
                self._collect_routes(pattern.url_patterns, new_prefix, routes)
            elif isinstance(pattern, URLPattern):
                route = str(pattern.pattern)
                name = pattern.name or ''
                # Try to get the view name
                view_cls = ''
                if hasattr(pattern.callback, 'cls'):
                    view_cls = f"{pattern.callback.cls.__module__}.{pattern.callback.cls.__name__}"
                elif hasattr(pattern.callback, 'view_class'):
                    view_cls = f"{pattern.callback.view_class.__module__}.{pattern.callback.view_class.__name__}"
                elif hasattr(pattern.callback, '__name__'):
                    view_cls = pattern.callback.__name__
                else:
                    view_cls = str(pattern.callback)[:80]
                routes.append({
                    'route': prefix + route,
                    'name': name,
                    'view': view_cls,
                })
        return routes

    def handle(self, *args, **options):
        from tiqani_v3 import urls as root_urls
        routes = self._collect_routes(root_urls.urlpatterns)

        output_path = options.get('output')

        if output_path:
            lines = []
            lines.append("# API Routes — tiqani_v3 (auto-generated)\n")
            lines.append(f"Total routes: {len(routes)}\n")
            lines.append("| # | Route | Name | View |")
            lines.append("|---|-------|------|------|")
            for i, r in enumerate(routes, 1):
                lines.append(f"| {i} | `{r['route']}` | {r['name']} | `{r['view']}` |")
            content = '\n'.join(lines) + '\n'

            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(content)
            self.stdout.write(self.style.SUCCESS(f"Routes written to {output_path}"))
        else:
            self.stdout.write(self.style.MIGRATE_HEADING(f"API Routes ({len(routes)} total)"))
            fmt = "{:<5} {:<60} {:<30} {:<60}"
            self.stdout.write(fmt.format("#", "Route", "Name", "View"))
            self.stdout.write("-" * 155)
            for i, r in enumerate(routes, 1):
                self.stdout.write(fmt.format(str(i), r['route'], r['name'][:28], r['view'][:58]))
