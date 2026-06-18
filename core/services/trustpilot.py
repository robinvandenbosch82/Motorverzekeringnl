"""
Trustpilot Public API client — fetches the TrustScore + latest reviews for the
autoverzekering.nl business unit.

Why the API and not scraping: Trustpilot's public review pages return HTTP 403
to automated requests (anti-bot), and scraping violates their ToS. The Public
API is the supported, stable, ToS-compliant route. It needs a (free) API key
from the Trustpilot Business account, read from settings.TRUSTPILOT_API_KEY
(which comes from .env — never hardcoded).

Used by `manage.py fetch_trustpilot` (weekly). Without a key every call raises
TrustpilotError, which the command turns into a graceful no-op.

Endpoints (https://api.trustpilot.com/v1):
  GET /business-units/find?name={domain}        -> resolve business unit id
  GET /business-units/{id}                       -> score.trustScore, score.stars, numberOfReviews.total
  GET /business-units/{id}/reviews?perPage=N...  -> latest reviews
"""
import logging

import requests
from django.conf import settings

log = logging.getLogger(__name__)


class TrustpilotError(Exception):
    """Any failure talking to Trustpilot (missing key, HTTP error, bad payload)."""


def _get(path, params=None):
    key = settings.TRUSTPILOT_API_KEY
    if not key:
        raise TrustpilotError(
            "TRUSTPILOT_API_KEY ontbreekt - zet de key in .env om reviews op te halen.")
    params = dict(params or {})
    params["apikey"] = key
    url = f"{settings.TRUSTPILOT_API_BASE.rstrip('/')}/{path.lstrip('/')}"
    try:
        r = requests.get(
            url, params=params, timeout=settings.TRUSTPILOT_API_TIMEOUT,
            headers={"User-Agent": "Bestelautoverzekering.nl/1.0 (+https://bestelautoverzekering.nl)"},
        )
    except requests.RequestException as exc:
        raise TrustpilotError(f"Netwerkfout bij {path}: {exc}") from exc
    if r.status_code != 200:
        raise TrustpilotError(f"HTTP {r.status_code} bij {path}: {r.text[:200]}")
    try:
        return r.json()
    except ValueError as exc:
        raise TrustpilotError(f"Ongeldige JSON bij {path}") from exc


def resolve_business_unit_id(domain):
    """Use the configured id if set, else resolve it from the domain (cached by
    the caller so we normally hit the API only once for the lookup)."""
    if settings.TRUSTPILOT_BUSINESS_UNIT_ID:
        return settings.TRUSTPILOT_BUSINESS_UNIT_ID
    data = _get("business-units/find", {"name": domain})
    bid = data.get("id") or (data.get("businessUnit") or {}).get("id")
    if not bid:
        raise TrustpilotError(f"Geen Trustpilot business unit gevonden voor '{domain}'.")
    return bid


def _review_url(item, profile_url):
    links = item.get("links") or []
    for ln in links:
        if isinstance(ln, dict) and ln.get("href"):
            return ln["href"]
    return profile_url


def fetch(domain=None, limit=4, profile_url=""):
    """Return {'summary': {...}, 'reviews': [ {...}, ... ]} from Trustpilot.

    Raises TrustpilotError on any problem (no key, HTTP error, empty result).
    """
    domain = domain or settings.TRUSTPILOT_DOMAIN
    bid = resolve_business_unit_id(domain)

    bu = _get(f"business-units/{bid}")
    score = bu.get("score") or {}
    nrev = bu.get("numberOfReviews")
    if isinstance(nrev, dict):
        review_count = nrev.get("total") or nrev.get("usedForTrustScoreCalculation") or 0
    elif isinstance(nrev, int):
        review_count = nrev
    else:
        review_count = 0

    summary = {
        "business_unit_id": bid,
        "trust_score": score.get("trustScore"),
        "stars": score.get("stars"),
        "review_count": int(review_count or 0),
    }

    data = _get(f"business-units/{bid}/reviews",
                {"perPage": limit, "orderBy": "createdat.desc"})
    reviews = []
    for it in (data.get("reviews") or [])[:limit]:
        consumer = it.get("consumer") or {}
        reviews.append({
            "external_id": str(it.get("id") or "").strip(),
            "author": (consumer.get("displayName") or "Trustpilot-gebruiker").strip(),
            "rating": int(it.get("stars") or 0),
            "title": (it.get("title") or "").strip(),
            "text": (it.get("text") or "").strip(),
            "language": (it.get("language") or "").strip(),
            "created_at": it.get("createdAt"),
            "review_url": _review_url(it, profile_url),
        })
    return {"summary": summary, "reviews": reviews}
