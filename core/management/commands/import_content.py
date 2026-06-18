"""
Import content-fabriek pages from the content-systeem WP-import CSVs.

Reads the 49-column WP All Import CSVs (per content-type) produced by
content-systeem and upserts them into ContentPagina (idempotent on slug).
Assembles the h2_1..h2_14 / body_1..body_14 sections into one body_html with
anchor ids + a table of contents.

    python manage.py import_content
    python manage.py import_content --dir "C:\\path\\to\\wp-import" --dry-run
    python manage.py import_content --only 4-verzekeraar.csv
"""

import csv
import re
from html import unescape
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from core.models import ContentPagina

csv.field_size_limit(10_000_000)

DEFAULT_DIR = Path(r"C:\Users\robin\content-systeem\output\bestelautoverzekering\wp-import")

_TAG_RE = re.compile(r"<[^>]+>")
_H2_RE = re.compile(r"<h2[^>]*>(.*?)</h2>", re.IGNORECASE | re.DOTALL)


def _text(html):
    return unescape(_TAG_RE.sub("", html or "")).strip()


def _build_body(row):
    """Concatenate the 14 h2/body pairs into body_html + a TOC, adding h2 ids."""
    parts, toc = [], []
    for i in range(1, 15):
        h2 = (row.get(f"h2_{i}") or "").strip()
        body = (row.get(f"body_{i}") or "").strip()
        if not h2 and not body:
            continue
        if h2:
            title = _text(h2)
            anchor = slugify(title)[:60] or f"sectie-{i}"
            toc.append({"text": title, "id": anchor})
            # replace the opening <h2 ...> with one carrying the id
            h2 = _H2_RE.sub(lambda m, a=anchor: f'<h2 id="{a}">{m.group(1)}</h2>', h2, count=1)
            parts.append(h2)
        if body:
            parts.append(body)
    return "\n".join(parts), toc


class Command(BaseCommand):
    help = "Import content-fabriek WP-import CSVs into ContentPagina (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--dir", default=str(DEFAULT_DIR), help="Map met de wp-import CSV's.")
        parser.add_argument("--only", default="", help="Eén CSV-bestandsnaam (bv. 4-verzekeraar.csv).")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **o):
        directory = Path(o["dir"])
        if not directory.exists():
            self.stderr.write(self.style.ERROR(f"Map niet gevonden: {directory}"))
            return

        files = ([directory / o["only"]] if o["only"]
                 else sorted(directory.glob("*.csv")))
        created = updated = skipped = 0

        for path in files:
            if not path.exists():
                self.stderr.write(self.style.WARNING(f"Overslaan (bestaat niet): {path}"))
                continue
            with open(path, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    slug = (row.get("slug") or "").strip().strip("/")
                    if not slug or not (row.get("post_title") or "").strip():
                        skipped += 1
                        continue
                    body_html, toc = _build_body(row)
                    defaults = {
                        "contenttype": (row.get("contenttype") or "").strip(),
                        "titel": (row.get("post_title") or "").strip()[:300],
                        "focus_keyword": (row.get("focus_keyword") or "").strip()[:200],
                        "zoekintentie": (row.get("zoekintentie") or "").strip()[:40],
                        "meta_title": (row.get("meta_title") or "").strip()[:300],
                        "meta_description": (row.get("meta_description") or "").strip(),
                        "image_url": (row.get("featured_image_url") or "").strip()[:600],
                        "image_alt": (row.get("featured_image_alt") or "").strip()[:400],
                        "image_credit": (row.get("featured_image_credit") or "").strip()[:300],
                        "image_credit_url": (row.get("featured_image_credit_url") or "").strip()[:600],
                        "intro_html": (row.get("intro") or "").strip(),
                        "body_html": body_html,
                        "faq_html": (row.get("faq") or "").strip(),
                        "conclusie_html": (row.get("conclusie") or "").strip(),
                        "cta_html": (row.get("cta_tekst") or "").strip(),
                        "interne_links_html": (row.get("interne_links") or "").strip(),
                        "toc": toc,
                        "schema_jsonld": (row.get("schema_jsonld") or "").strip(),
                        "bronnen": (row.get("bronnen") or "").strip(),
                        "gate_status": (row.get("gate_status") or "").strip()[:20],
                        "published": (row.get("gate_status") or "").strip() == "output",
                    }
                    if o["dry_run"]:
                        created += 1
                        continue
                    _, was_created = ContentPagina.objects.update_or_create(
                        slug=slug, defaults=defaults)
                    created += was_created
                    updated += (not was_created)

        verb = "zou aanmaken" if o["dry_run"] else "aangemaakt"
        self.stdout.write(self.style.SUCCESS(
            f"Import klaar — {created} {verb}, {updated} bijgewerkt, {skipped} overgeslagen. "
            f"Totaal nu: {ContentPagina.objects.count()} content-pagina's."))
