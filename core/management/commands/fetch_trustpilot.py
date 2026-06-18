"""
Fetch the Trustpilot TrustScore + latest reviews and cache them in the DB.

Run weekly (see the project README / deploy docs for the cron line). Without a
TRUSTPILOT_API_KEY in the environment this is a graceful no-op so it never
breaks a scheduled run — the site keeps rendering the last cached data (or the
manual SiteSettings score).

    python manage.py fetch_trustpilot            # fetch + store
    python manage.py fetch_trustpilot --dry-run  # fetch + print, store nothing
"""
import decimal
from datetime import timezone as dt_timezone

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.models import TrustpilotProfile, TrustpilotReview
from core.services import trustpilot
from core.services.trustpilot import TrustpilotError


class Command(BaseCommand):
    help = "Haalt de Trustpilot-score + laatste reviews op (wekelijks draaien)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=4,
                            help="Aantal reviews om op te halen (standaard 4).")
        parser.add_argument("--dry-run", action="store_true",
                            help="Wel ophalen + tonen, niets opslaan.")

    def handle(self, *args, **opts):
        profile = TrustpilotProfile.load()
        try:
            data = trustpilot.fetch(
                domain=profile.domain or None,
                limit=opts["limit"],
                profile_url=profile.profile_url,
            )
        except TrustpilotError as exc:
            # No key / network / API problem → don't fail the scheduled run.
            self.stderr.write(self.style.WARNING(f"Trustpilot overgeslagen: {exc}"))
            return

        s, reviews = data["summary"], data["reviews"]
        self.stdout.write(
            f"TrustScore {s.get('trust_score')} · {s.get('review_count')} reviews · "
            f"{len(reviews)} reviews opgehaald.")

        if opts["dry_run"]:
            for r in reviews:
                self.stdout.write(f"  - {r['author']} {r['rating']}★  {r['title'][:60]}")
            self.stdout.write(self.style.NOTICE("dry-run: niets opgeslagen."))
            return

        # ── Upsert the summary ──
        if s.get("trust_score") is not None:
            profile.trust_score = decimal.Decimal(str(s["trust_score"]))
        if s.get("stars") is not None:
            profile.stars = decimal.Decimal(str(s["stars"]))
        profile.review_count = int(s.get("review_count") or 0)
        if s.get("business_unit_id"):
            profile.business_unit_id = s["business_unit_id"]
        profile.last_fetched = timezone.now()
        profile.save()

        # ── Replace the cached reviews with the freshly fetched set ──
        keep = []
        for i, r in enumerate(reviews):
            if not r["external_id"]:
                continue
            created = parse_datetime(r["created_at"]) if r.get("created_at") else None
            if created is None:
                created = timezone.now()
            elif timezone.is_naive(created):
                created = timezone.make_aware(created, dt_timezone.utc)
            obj, _ = TrustpilotReview.objects.update_or_create(
                external_id=r["external_id"],
                defaults={
                    "author": r["author"], "rating": r["rating"], "title": r["title"],
                    "text": r["text"], "language": r["language"],
                    "review_url": r["review_url"], "created_at": created, "order": i,
                },
            )
            keep.append(obj.external_id)
        # Prune reviews that are no longer in the latest set.
        TrustpilotReview.objects.exclude(external_id__in=keep).delete()

        self.stdout.write(self.style.SUCCESS(
            f"Trustpilot bijgewerkt: {profile.trust_score}/5 · "
            f"{profile.review_count} reviews · {len(keep)} kaarten opgeslagen."))
