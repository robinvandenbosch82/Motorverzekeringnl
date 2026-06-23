"""
Site-wide template context.

Single source of truth for navigation, footer columns and per-request SEO
defaults. The menus are admin-editable (core.models.MenuItem); when no menu
rows exist yet, we fall back to the hardcoded structure below so the site
always renders. Templates use plain `{{ item.url }}` links (not {% url %}),
so both the DB rows and the resolved fallback share one shape.
"""

from django.conf import settings
from django.core.cache import cache
from django.urls import NoReverseMatch, reverse

from .models import SiteSettings

# Menus change rarely but are read on every request; cache the built structures
# and invalidate them on MenuItem save/delete (see core.signals). The TTL is a
# safety net for multi-process setups where a signal only clears one worker.
NAV_CACHE_KEY = "menu_nav_v1"
FOOTER_CACHE_KEY = "menu_footer_v1"
MENU_CACHE_TTL = 3600

# ── Hardcoded fallback (used only until the menus are seeded/edited) ─────────
# Motor (MV-design): flat top-nav, 5 footer columns incl. Juridisch.
_NAV_FALLBACK = [
    {"label": "Dekkingen", "url_name": "dekkingen", "children": []},
    {"label": "Blog", "url_name": "blog", "children": []},
    {"label": "Kennisbank", "url_name": "kennisbank", "children": []},
    {"label": "Klantenservice", "url_name": "klantenservice", "children": []},
]

_FOOTER_FALLBACK = [
    {"title": "Verzekering", "links": [
        {"label": "WA", "url_name": "dekkingen"},
        {"label": "WA + Casco", "url_name": "dekkingen"},
        {"label": "Allrisk", "url_name": "dekkingen"},
        {"label": "Voorwaarden", "path": "/algemene-voorwaarden/"},
    ]},
    {"title": "Service", "links": [
        {"label": "Schade melden", "url_name": "klantenservice"},
        {"label": "Veelgestelde vragen", "url_name": "kennisbank"},
        {"label": "Blog", "url_name": "blog"},
        {"label": "Klantenservice", "url_name": "klantenservice"},
    ]},
    {"title": "Bedrijf", "links": [
        {"label": "Over ons", "url_name": "over_ons"},
        {"label": "Reviews", "url_name": "over_ons"},
        {"label": "Contact", "url_name": "klantenservice"},
    ]},
    {"title": "Juridisch", "links": [
        {"label": "Algemene voorwaarden", "path": "/algemene-voorwaarden/"},
        {"label": "Privacy & cookies", "path": "/privacy-cookies/"},
        {"label": "Dienstenwijzer", "path": "/dienstenwijzer/"},
        {"label": "Disclaimer", "path": "/disclaimer/"},
        {"label": "Toegankelijkheidsverklaring",
         "path": "https://cdn.autoverzekering.nl/doc/Toegankelijkheidsverklaring-Autoverzekering.nl_.pdf"},
    ]},
]


def _resolve(entry):
    """Resolve a fallback entry to a plain URL string. Supports {url_name} or
    {path}; returns '' when there's no destination (a header-only group)."""
    if entry.get("path"):
        return entry["path"]
    name = entry.get("url_name")
    if not name:
        return ""
    try:
        return reverse(name)
    except NoReverseMatch:
        return ""


def _fallback_nav():
    return [{"label": it["label"], "url": _resolve(it),
             "children": [{"label": c["label"], "url": _resolve(c)} for c in it["children"]]}
            for it in _NAV_FALLBACK]


def _fallback_footer():
    return [{"title": col["title"],
             "links": [{"label": ln["label"], "url": _resolve(ln)} for ln in col["links"]]}
            for col in _FOOTER_FALLBACK]


def _nav_from_db():
    cached = cache.get(NAV_CACHE_KEY)
    if cached is not None:
        return cached
    from .models import MenuItem
    tops = (MenuItem.objects.filter(menu="nav", active=True, parent__isnull=True)
            .prefetch_related("children"))
    nav = []
    for t in tops:
        children = [{"label": c.label, "url": c.url} for c in t.children.all() if c.active]
        nav.append({"label": t.label, "url": t.url, "children": children})
    cache.set(NAV_CACHE_KEY, nav, MENU_CACHE_TTL)
    return nav


def _footer_from_db():
    cached = cache.get(FOOTER_CACHE_KEY)
    if cached is not None:
        return cached
    from .models import MenuItem
    tops = (MenuItem.objects.filter(menu="footer", active=True, parent__isnull=True)
            .prefetch_related("children"))
    cols = []
    for t in tops:
        links = [{"label": c.label, "url": c.url} for c in t.children.all() if c.active]
        cols.append({"title": t.label, "links": links})
    cache.set(FOOTER_CACHE_KEY, cols, MENU_CACHE_TTL)
    return cols


def site_context(request):
    """Inject brand defaults, navigation, SiteSettings and a canonical URL."""
    try:
        site = SiteSettings.load()
    except Exception:  # DB not migrated yet (e.g. first run), fall back gracefully
        site = SiteSettings()

    try:
        nav_items = _nav_from_db() or _fallback_nav()
        footer_columns = _footer_from_db() or _fallback_footer()
    except Exception:
        nav_items, footer_columns = _fallback_nav(), _fallback_footer()

    # Copy for the global premie-conversion band (admin-editable, every page).
    try:
        from .content import secties
        premie_band = secties("premie_widget").get("band")
    except Exception:
        premie_band = None

    # Stable, host-independent origin for structured-data @id's and canonical
    # URLs. In dev this points at the production domain on purpose: a canonical
    # URL should always be the production one, and @id's must be identical on
    # every page so Google can reconcile the entity graph.
    site_origin = settings.SITE_ORIGIN
    canonical_url = site_origin + request.path

    return {
        "site_name": settings.SITE_NAME,
        "site_domain": settings.SITE_DOMAIN,
        "site_origin": site_origin,
        "default_seo_title": settings.DEFAULT_SEO_TITLE,
        "default_seo_description": settings.DEFAULT_SEO_DESCRIPTION,
        "nav_items": nav_items,
        "footer_columns": footer_columns,
        "premie_band": premie_band,
        "site": site,
        "review_score": site.review_score,
        "review_count": site.review_count,
        "canonical_url": canonical_url,
    }
