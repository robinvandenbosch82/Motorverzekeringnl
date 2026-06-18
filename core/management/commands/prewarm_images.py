"""
Pre-generate the responsive AVIF/WebP/JPEG variants for every local image, so
the first visitor to any page is served cached files (no on-render encoding
that would otherwise hurt LCP). Run once after import/deploy.

    python manage.py prewarm_images
"""

import glob
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from core.services.image_pipeline import get_variant_urls

PHOTO_MODELS = ("Expert", "Review", "Situatie", "Verzekeraar", "BlogArtikel", "KennisbankArtikel")


class Command(BaseCommand):
    help = "Pre-warm AVIF/WebP/JPEG variants for all local images."

    def handle(self, *args, **opts):
        from core import models as m

        warmed = skipped = 0

        def warm(src):
            nonlocal warmed, skipped
            if not src or src.startswith("http"):
                skipped += 1
                return
            try:
                get_variant_urls(src)
                warmed += 1
            except Exception as exc:  # noqa: BLE001
                self.stderr.write(f"  fail {src}: {exc}")

        for cp in m.ContentPagina.objects.exclude(image_local=""):
            warm(cp.get_image_source())
        for name in PHOTO_MODELS:
            for obj in getattr(m, name).objects.all():
                warm(obj.get_photo_source())
        for f in glob.glob(os.path.join(settings.MEDIA_ROOT, "heroes", "*")):
            warm("heroes/" + os.path.basename(f))

        self.stdout.write(self.style.SUCCESS(
            f"Pre-warm klaar: {warmed} afbeeldingen verwerkt, {skipped} overgeslagen (extern/leeg)."))
