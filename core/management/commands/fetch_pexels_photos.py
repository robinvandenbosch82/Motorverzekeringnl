"""
Bulk-fill content photos from Pexels (ported pattern from the sibling sites).

For every PhotoMixin object without a photo, search Pexels with a per-model
query and store the result (photo_url + credit + pexels_id). With --download
the photo is also saved locally (photo_local) so the responsive {% picture %}
pipeline kicks in. Requires a Pexels key (admin → Site-instellingen, or .env).

    python manage.py fetch_pexels_photos --model all
    python manage.py fetch_pexels_photos --model situatie --download --overwrite
    python manage.py fetch_pexels_photos --model expert --limit 5 --dry-run
"""

import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from core.services import pexels

# model-key -> (Model, query builder, download subdir, filename prefix)
def _registry():
    from core.models import (
        BlogArtikel, Expert, KennisbankArtikel, Review, Situatie, Verzekeraar,
    )
    return {
        "situatie": (Situatie, lambda o: f"{o.titel} bestelbus bedrijf", "photos/situaties", "situatie"),
        "verzekeraar": (Verzekeraar, lambda o: f"{o.naam} kantoor logo", "photos/verzekeraars", "logo"),
        "blog": (BlogArtikel, lambda o: f"{o.categorie or 'bestelauto'} bestelbus", "photos/blog", "blog"),
        "kennisbank": (KennisbankArtikel, lambda o: f"{o.categorie or 'bestelauto'} bestelbus", "photos/kennisbank", "kb"),
        "expert": (Expert, lambda o: "professional portrait office", "photos/experts", "expert"),
        "review": (Review, lambda o: "tradesperson portrait", "photos/reviews", "review"),
    }


class Command(BaseCommand):
    help = "Fill content photos from Pexels (photo_url/credit/pexels_id, optionally downloaded)."

    def add_arguments(self, parser):
        parser.add_argument("--model", default="all", help="situatie|verzekeraar|blog|kennisbank|expert|review|all")
        parser.add_argument("--overwrite", action="store_true", help="Replace existing photos too.")
        parser.add_argument("--download", action="store_true", help="Also download locally (photo_local).")
        parser.add_argument("--limit", type=int, default=0, help="Max objects to process (0 = all).")
        parser.add_argument("--delay", type=float, default=1.0, help="Seconds between API calls.")
        parser.add_argument("--dry-run", action="store_true", help="Show what would happen, change nothing.")

    def handle(self, *args, **o):
        if not pexels._get_api_key():
            self.stderr.write(self.style.ERROR(
                "Geen Pexels API-sleutel (admin → Site-instellingen of .env PEXELS_API_KEY)."))
            return

        registry = _registry()
        keys = list(registry) if o["model"] == "all" else [o["model"]]
        processed = filled = 0

        for key in keys:
            entry = registry.get(key)
            if not entry:
                self.stderr.write(self.style.WARNING(f"Onbekend model: {key}"))
                continue
            Model, build_query, subdir, prefix = entry
            qs = Model.objects.all()
            for obj in qs:
                if o["limit"] and processed >= o["limit"]:
                    break
                has_photo = bool(obj.photo_url or obj.photo_local or obj.photo_upload)
                if has_photo and not o["overwrite"]:
                    continue
                processed += 1
                query = build_query(obj)
                photos = pexels.search_photos(query, per_page=1)
                if not photos:
                    self.stdout.write(f"  geen resultaat: {key} «{obj}» (q={query!r})")
                    time.sleep(o["delay"])
                    continue
                p = photos[0]
                self.stdout.write(f"  {key} «{obj}» ← {p['id']} ({query!r})")
                if not o["dry_run"]:
                    obj.photo_url = p["url"]
                    obj.photo_credit = pexels.build_credit(p)
                    obj.photo_pexels_id = p["id"]
                    if not obj.photo_alt:
                        obj.photo_alt = p.get("alt") or obj.default_photo_alt()
                    if o["download"]:
                        fn = f"{prefix}-{slugify(str(obj))[:40] or 'foto'}.jpg"
                        local = pexels.download_photo(p, Path(settings.MEDIA_ROOT) / subdir, fn)
                        if local:
                            obj.photo_local = local
                            obj.photo_url = ""
                    obj.save()
                    filled += 1
                time.sleep(o["delay"])

        msg = f"Klaar — {processed} bekeken, {filled} gevuld" + (" (dry-run)" if o["dry_run"] else "")
        self.stdout.write(self.style.SUCCESS(msg))
