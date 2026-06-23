"""
Sync the Page table with the routing registry (core.views.PAGES).

Keeps the admin page-list in lock-step with the live site: creates a Page row
for every route, fills SEO defaults on first creation (without clobbering edits),
and updates the read-only path. Safe to run repeatedly.

    python manage.py sync_pages
"""

from django.core.management.base import BaseCommand
from django.urls import reverse

from core.models import Page
from core.views import PAGES

# Friendly Dutch labels for the admin list.
LABELS = {
    "home": "Homepage",
    "dekkingen": "Dekkingen (WA / WA+ / Allrisk)",
    "vergelijken": "Vergelijken",
    "situaties_beroepen": "Situaties & beroepen",
    "situatie_gereedschap": "Situatie — Gereedschap in de bus",
    "beroep_timmerman": "Beroep — Timmerman",
    "verzekeraars": "Verzekeraars (overzicht)",
    "verzekeraar_asr": "Verzekeraar — ASR",
    "kennisbank": "Kennisbank (overzicht)",
    "kennisbank_artikel": "Kennisbank — Welk ART-slot heb ik nodig",
    "blog": "Blog & nieuws (overzicht)",
    "blog_artikel": "Blog — Motor rijklaar na de winterstop",
    "over_ons": "Onze experts & redactieproces",
    "klantenservice": "Klantenservice",
}


class Command(BaseCommand):
    help = "Create/update a Page row for every route in the PAGES registry."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force-seo", action="store_true",
            help="Overwrite seo_title/seo_description/label from the registry "
                 "(use after the registry SEO changed; clobbers admin SEO edits).")

    def handle(self, *args, **options):
        force_seo = options["force_seo"]
        created = updated = 0
        for p in PAGES:
            path = reverse(p.name)
            label = LABELS.get(p.name, p.name)
            obj, was_created = Page.objects.get_or_create(
                key=p.name,
                defaults={
                    "label": label,
                    "path": path,
                    "seo_title": p.title,
                    "seo_description": p.description,
                },
            )
            if was_created:
                created += 1
            else:
                # Refresh the read-only bits; never overwrite editor content
                # unless --force-seo is given (one-off after a registry rebrand).
                changed = False
                if obj.path != path:
                    obj.path = path
                    changed = True
                if not obj.label or force_seo:
                    obj.label = label
                    changed = True
                if force_seo:
                    obj.seo_title = p.title
                    obj.seo_description = p.description
                    changed = True
                if changed:
                    obj.save(update_fields=["path", "label", "seo_title", "seo_description"])
                    updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Pages synced — {created} created, {updated} updated, {len(PAGES)} total."
        ))
