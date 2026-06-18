"""
Download imported ContentPagina images locally so they run through the
responsive {% picture %} pipeline (WebP/JPEG variants), instead of hot-linking
external Pexels/Unsplash URLs. Mirrors how the sibling sites store their images.

    python manage.py download_content_images          # only the ones not yet done
    python manage.py download_content_images --force   # re-download all
"""

import os
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import ContentPagina

SUBDIR = "content"


class Command(BaseCommand):
    help = "Download ContentPagina images to media/content/ and set image_local."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true",
                            help="Re-download even when image_local is already set.")
        parser.add_argument("--limit", type=int, default=0, help="Max images this run (0 = all).")

    def handle(self, *args, **opts):
        dest = os.path.join(settings.MEDIA_ROOT, SUBDIR)
        os.makedirs(dest, exist_ok=True)

        qs = ContentPagina.objects.exclude(image_url="").order_by("slug")
        if not opts["force"]:
            qs = qs.filter(image_local="")
        if opts["limit"]:
            qs = qs[: opts["limit"]]

        done = failed = skipped = 0
        for cp in qs:
            ext = self._ext(cp.image_url)
            filename = f"{cp.slug.replace('/', '-')}.{ext}"
            rel = f"{SUBDIR}/{filename}"
            abs_path = os.path.join(settings.MEDIA_ROOT, rel)

            if not opts["force"] and os.path.exists(abs_path):
                cp.image_local = rel
                cp.save(update_fields=["image_local"])
                skipped += 1
                continue
            try:
                r = requests.get(cp.image_url, timeout=30,
                                 headers={"User-Agent": "Mozilla/5.0"})
                r.raise_for_status()
                with open(abs_path, "wb") as fh:
                    fh.write(r.content)
                cp.image_local = rel
                cp.save(update_fields=["image_local"])
                done += 1
                self.stdout.write(f"  ok  {cp.slug} ({len(r.content) // 1024} KB)")
            except Exception as exc:  # noqa: BLE001 — keep going on a single failure
                failed += 1
                self.stderr.write(f"  FAIL {cp.slug}: {exc}")

        self.stdout.write(self.style.SUCCESS(
            f"Klaar: {done} gedownload, {skipped} al aanwezig, {failed} mislukt."))

    @staticmethod
    def _ext(url):
        path = urlparse(url).path.lower()
        for e in ("jpeg", "jpg", "png", "webp"):
            if path.endswith("." + e):
                return "jpg" if e == "jpeg" else e
        return "jpg"
