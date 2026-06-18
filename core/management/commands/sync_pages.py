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
    "kennisbank_artikel": "Kennisbank — Gereedschap verzekeren",
    "blog": "Blog & nieuws (overzicht)",
    "blog_artikel": "Blog — Elektrische bedrijfswagen allrisk",
    "over_ons": "Over ons & vertrouwen",
    "klantenservice": "Klantenservice",
}


class Command(BaseCommand):
    help = "Create/update a Page row for every route in the PAGES registry."

    def handle(self, *args, **options):
        created = updated = 0
        for p in PAGES:
            path = reverse(p.name)
            obj, was_created = Page.objects.get_or_create(
                key=p.name,
                defaults={
                    "label": LABELS.get(p.name, p.name),
                    "path": path,
                    "seo_title": p.title,
                    "seo_description": p.description,
                },
            )
            if was_created:
                created += 1
            else:
                # Refresh the read-only bits; never overwrite editor content.
                changed = False
                if obj.path != path:
                    obj.path = path
                    changed = True
                if not obj.label:
                    obj.label = LABELS.get(p.name, p.name)
                    changed = True
                if changed:
                    obj.save(update_fields=["path", "label"])
                    updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Pages synced — {created} created, {updated} updated, {len(PAGES)} total."
        ))
