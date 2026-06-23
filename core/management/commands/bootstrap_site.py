"""
One-shot deploy bootstrap for a fresh host (empty Postgres + empty media disk).

Loads the seed data, restores the essential bundled media (heroes + experts),
self-heals content images whose local file is missing (falls back to their
external URL so nothing breaks), pre-warms the responsive variants, and ensures
an admin user from env. Fully idempotent — safe to run on every deploy.

    python manage.py bootstrap_site              # data + media + prewarm + superuser
    python manage.py bootstrap_site --localize   # also download the content images locally
    python manage.py bootstrap_site --force      # loaddata even if content already exists
"""
import os
import shutil
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Vul een verse host: seed-data + media + prewarm + superuser (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true",
                            help="loaddata ook als er al content-pagina's zijn.")
        parser.add_argument("--localize", action="store_true",
                            help="content-afbeeldingen lokaal downloaden (trager, eenmalig).")

    def handle(self, *args, **opts):
        from core.models import ContentPagina

        base = Path(settings.BASE_DIR)
        media_root = Path(settings.MEDIA_ROOT)

        # 1) DATA — seed the authored motor content (idempotent guard on content).
        #    seed_content is the single source of truth (alle SectieTekst/Kaart/menu's/
        #    verzekeraars/legal pages); sync_pages maakt de Page-rijen. Eenmalig op een
        #    lege DB; daarna bezit de admin de content (de guard slaat latere deploys over).
        if opts["force"] or not ContentPagina.objects.exists():
            self.stdout.write("Motor-content seeden (seed_content + sync_pages)…")
            call_command("seed_content")
            call_command("sync_pages")
        else:
            self.stdout.write("Content bestaat al -> seeden overgeslagen.")

        # 2) MEDIA — copy the bundled essential images onto the (possibly empty) disk.
        src = base / "deploy" / "seed_media"
        copied = 0
        if src.exists():
            for f in src.rglob("*"):
                if f.is_file():
                    dst = media_root / f.relative_to(src)
                    if not dst.exists():
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(f, dst)
                        copied += 1
        self.stdout.write(f"Media hersteld: {copied} nieuwe bestanden.")

        # 3) Optioneel: content-afbeeldingen lokaal downloaden (van hun externe URL).
        if opts["localize"]:
            self.stdout.write("Content-afbeeldingen downloaden…")
            call_command("download_content_images")

        # 4) Self-heal: lokaal pad gezet maar bestand ontbreekt -> terug naar externe URL,
        #    zodat er nooit een gebroken afbeelding op de site staat.
        healed = 0
        for cp in ContentPagina.objects.exclude(image_local=""):
            if not (media_root / cp.image_local).exists() and cp.image_url:
                cp.image_local = ""
                cp.save(update_fields=["image_local"])
                healed += 1
        if healed:
            self.stdout.write(f"{healed} content-afbeeldingen teruggezet op externe URL "
                              "(lokaal bestand ontbrak).")

        # 5) Beeldvarianten voorverwarmen (WebP/JPEG) voor wat lokaal aanwezig is.
        call_command("prewarm_images")

        # 6) Superuser uit env (DJANGO_SUPERUSER_USERNAME/PASSWORD/EMAIL).
        self._ensure_superuser()

        self.stdout.write(self.style.SUCCESS("bootstrap_site klaar."))

    def _ensure_superuser(self):
        from django.contrib.auth import get_user_model

        username = os.getenv("DJANGO_SUPERUSER_USERNAME")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "")
        if not username or not password:
            return
        User = get_user_model()
        if User.objects.filter(username=username).exists():
            self.stdout.write(f"Superuser '{username}' bestaat al.")
            return
        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' aangemaakt."))
