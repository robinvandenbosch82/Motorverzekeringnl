"""
Smoke test: render every registered page and assert it is healthy.

Mirrors the `check_pages` convention from cruises.nl. Run after any template
or view change, and in CI before deploy:

    python manage.py check_pages
    python manage.py check_pages --verbose
"""

from django.core.management.base import BaseCommand
from django.test import Client
from django.urls import reverse

from core.views import PAGES

# Markers that must appear on every page (shared chrome) and red flags that
# must never appear (template/rendering errors leaking into the HTML).
REQUIRED_MARKERS = [
    'data-site-nav',       # SiteNav partial rendered
    'data-site-footer',    # SiteFooter partial rendered
    'application/ld+json',  # structured data present
]
FORBIDDEN_MARKERS = [
    "TemplateSyntaxError",
    "Traceback (most recent call last)",
    "Invalid block tag",
    "Could not parse",
]


class Command(BaseCommand):
    help = "Render every registered page and assert it returns 200 + healthy HTML."

    def add_arguments(self, parser):
        parser.add_argument("--verbose", action="store_true", help="Print every passing page.")

    def handle(self, *args, **options):
        verbose = options["verbose"]
        # SERVER_NAME must be in ALLOWED_HOSTS — the test client otherwise
        # defaults to "testserver", which this project does not allow.
        client = Client(SERVER_NAME="localhost")
        failures = 0

        # Build the target list: registry pages + content hubs + one sample
        # imported content page (so the catch-all route is smoke-tested too).
        from core.hubs import HUBS
        from core.models import ContentPagina
        targets = [(p.name, reverse(p.name)) for p in PAGES]
        targets += [(h["name"], reverse(h["name"])) for h in HUBS]
        sample = ContentPagina.objects.filter(published=True).first()
        if sample:
            targets.append((f"content:{sample.slug}", sample.get_absolute_url()))

        for label, url in targets:
            try:
                resp = client.get(url)
            except Exception as exc:  # noqa: BLE001 — surface any render error
                failures += 1
                self.stderr.write(self.style.ERROR(f"FAIL {url} — raised {exc!r}"))
                continue

            problems = []
            if resp.status_code != 200:
                problems.append(f"status {resp.status_code}")
            html = resp.content.decode("utf-8", errors="replace")
            for marker in REQUIRED_MARKERS:
                if marker not in html:
                    problems.append(f"missing {marker!r}")
            for marker in FORBIDDEN_MARKERS:
                if marker in html:
                    problems.append(f"contains {marker!r}")
            if "<title>" not in html or "name=\"description\"" not in html:
                problems.append("missing SEO head tags")

            if problems:
                failures += 1
                self.stderr.write(self.style.ERROR(f"FAIL {url} — {', '.join(problems)}"))
            elif verbose:
                self.stdout.write(self.style.SUCCESS(f"OK   {url} ({label})"))

        total = len(targets)
        if failures:
            self.stderr.write(self.style.ERROR(f"\n{failures}/{total} pages failed."))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS(f"\nAll {total} pages OK."))
