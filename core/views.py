"""
Page views for Bestelautoverzekering.nl.

These are content/marketing pages translated from the Claude Design handoff.
Each view is intentionally thin: it sets the per-page SEO metadata and renders
a server-side template. Structured page data (insurers, professions, articles)
will later be sourced from the content-systeem CSV importer; for now the
prototype content lives in the templates.

The PAGES registry is the single source of truth that drives URL routing,
the sitemap and the check_pages smoke test, add a page once, here.
"""

from dataclasses import dataclass, field
from typing import Callable

from django.shortcuts import get_object_or_404, render

from . import content


@dataclass(frozen=True)
class Page:
    name: str          # URL name
    path: str          # URL path (without leading slash); "" = home
    template: str      # template under templates/pages/
    title: str         # <title> / og:title
    description: str   # meta description
    sitemap_priority: float = 0.6
    sitemap_changefreq: str = "monthly"
    extra: Callable[[], dict] = field(default=lambda: {})


PAGES: list[Page] = [
    Page("home", "", "pages/home.html",
         "Bestelautoverzekering vergelijken voor ondernemers | Bestelautoverzekering.nl",
         "Dé specialist in bestelautoverzekeringen voor ondernemers. Vergelijk 12+ verzekeraars, "
         "bereken je premie in 2 minuten en zorg dat je werk gewoon doorgaat.",
         1.0, "daily", extra=content.home_context),
    Page("dekkingen", "dekkingen/", "pages/dekkingen.html",
         "Dekkingen: WA, WA+ en Allrisk bestelautoverzekering | Bestelautoverzekering.nl",
         "WA, WA+ of Allrisk voor je bestelauto? Vergelijk de drie dekkingen helder naast elkaar "
         "en kies wat past bij hoe jij werkt.",
         0.9, "monthly", extra=content.dekkingen_context),
    Page("vergelijken", "vergelijken/", "pages/vergelijken.html",
         "Bestelautoverzekering vergelijken: 12+ verzekeraars | Bestelautoverzekering.nl",
         "Vergelijk de premies en voorwaarden van 12+ bestelautoverzekeraars onafhankelijk naast "
         "elkaar. Sorteer op laagste premie of beste beoordeling.",
         0.9, "weekly"),
    Page("situaties_beroepen", "situaties-en-beroepen/", "pages/situaties_beroepen.html",
         "Bestelautoverzekering per situatie en beroep | Bestelautoverzekering.nl",
         "Elektrisch, gereedschap, wagenpark of een specifiek beroep? Vind de dekking die past bij "
         "jouw situatie en vak.",
         0.8, "monthly", extra=content.situaties_beroepen_context),
    Page("situatie_gereedschap", "situaties/gereedschap-in-de-bus/", "pages/situatie_gereedschap.html",
         "Gereedschap in de bus verzekeren | Bestelautoverzekering.nl",
         "Je inventaris is je verdienmodel. Verzeker tot € 25.000 aan gereedschap in je bus, ook "
         "bij diefstal buiten werktijd.",
         0.7, "monthly"),
    Page("beroep_timmerman", "beroepen/timmerman/", "pages/beroep_timmerman.html",
         "Bestelautoverzekering voor timmerlieden | Bestelautoverzekering.nl",
         "Verzekering op maat voor timmerlieden: gereedschap gedekt, snelle vervanging en advies "
         "van specialisten die jouw werk kennen.",
         0.7, "monthly"),
    Page("verzekeraars", "verzekeraars/", "pages/verzekeraars.html",
         "Bestelautoverzekeraars vergelijken | Bestelautoverzekering.nl",
         "Bekijk en vergelijk alle bestelautoverzekeraars: score, premie vanaf en dekkingen. "
         "Onafhankelijk en transparant.",
         0.8, "weekly", extra=content.verzekeraars_context),
    Page("verzekeraar_asr", "verzekeraars/asr-bestelauto-prive-of-zakelijk/", "pages/verzekeraar_asr.html",
         "ASR bestelautoverzekering: privé of zakelijk | Bestelautoverzekering.nl",
         "Alles over de bestelautoverzekering van ASR: dekkingen, premiefactoren, privé of zakelijk "
         "op grijs kenteken, ervaringen en veelgestelde vragen.",
         0.7, "monthly"),
    Page("kennisbank", "kennisbank/", "pages/kennisbank.html",
         "Kennisbank bestelautoverzekering | Bestelautoverzekering.nl",
         "Honderden artikelen over dekkingen, beroepen, modellen, schade en regelgeving rond de "
         "bestelautoverzekering, helder uitgelegd.",
         0.8, "weekly", extra=content.kennisbank_context),
    Page("kennisbank_artikel", "kennisbank/gereedschap-verzekeren-in-je-bestelauto/", "pages/kennisbank_artikel.html",
         "Is gereedschap in je bestelauto verzekerd? | Bestelautoverzekering.nl",
         "Standaard is je gereedschap niet meeverzekerd. Lees hoe je tot € 25.000 aan inventaris "
         "verzekert, ook bij nachtelijke diefstal.",
         0.7, "monthly"),
    Page("blog", "blog/", "pages/blog.html",
         "Blog & nieuws over bestelauto's en verzekeren | Bestelautoverzekering.nl",
         "Verhalen van de weg: praktische artikelen en nieuws over bestelauto's, verzekeren, "
         "regelgeving en elektrisch rijden.",
         0.7, "weekly", extra=content.blog_context),
    Page("blog_artikel", "blog/elektrische-bedrijfswagen-allrisk-verzekeren/", "pages/blog_artikel.html",
         "Elektrische bedrijfswagen allrisk verzekeren | Bestelautoverzekering.nl",
         "Waarom een allrisk-dekking voor je elektrische bedrijfswagen nu slim is: accu, laadkabel "
         "en laadpaalschade uitgelegd.",
         0.7, "monthly"),
    Page("over_ons", "over-ons/", "pages/over_ons.html",
         "Over ons & vertrouwen | Bestelautoverzekering.nl",
         "Wie we zijn, ons redactieteam met diploma's, onze bronnen en werkwijze. Onafhankelijk, "
         "AFM-vergund en aangesloten bij Kifid.",
         0.6, "monthly", extra=content.over_ons_context),
    Page("klantenservice", "klantenservice/", "pages/klantenservice.html",
         "Klantenservice & contact | Bestelautoverzekering.nl",
         "Bereik onze specialisten via telefoon, WhatsApp of e-mail, bekijk openingstijden en regel "
         "veelvoorkomende zaken direct zelf.",
         0.6, "monthly"),
]

PAGES_BY_NAME = {p.name: p for p in PAGES}


def _render_page(request, page: Page):
    # Per-page admin overrides (Page model) win over the registry defaults.
    from .models import Page as PageModel

    page_obj = PageModel.objects.filter(key=page.name).first()
    context = {
        "seo_title": (page_obj.seo_title if page_obj and page_obj.seo_title else page.title),
        "seo_description": (page_obj.seo_description if page_obj and page_obj.seo_description
                            else page.description),
        "page": page_obj,
        "noindex": bool(page_obj and page_obj.noindex),
        "active_page": page.name,
    }
    # Extras are normally no-arg; an extra that declares a parameter receives the
    # request (so e.g. the kennisbank can read ?q= for search).
    import inspect
    try:
        wants_request = len(inspect.signature(page.extra).parameters) >= 1
    except (TypeError, ValueError):
        wants_request = False
    context.update(page.extra(request) if wants_request else page.extra())
    return render(request, page.template, context)


def make_view(page: Page):
    """Build a thin view callable bound to a single Page."""

    def view(request):
        return _render_page(request, page)

    view.__name__ = f"page_{page.name}"
    return view


# Slug-prefix → (breadcrumb label, optional existing overview URL name).
_SECTION_LABELS = {
    "verzekeraars": ("Verzekeraars", "verzekeraars"),
    "beroep": ("Beroepen", "situaties_beroepen"),
    "regio": ("Per regio", None),
    "merk-model": ("Modellen", None),
    "vergelijking": ("Vergelijken", "vergelijken"),
    "dekkingen": ("Dekkingen", "dekkingen"),
    "schade": ("Schade", None),
}


# Prefixes that get the rich product-style template (à la the Timmerman demo),
# mapped to the plural noun used in the "ook voor andere …" section.
_RICH_PREFIXES = {"beroep": "beroepen", "merk-model": "modellen"}


def content_pagina(request, slug):
    """Render an imported content-fabriek page (catch-all by slug)."""
    from django.urls import reverse

    from .models import ContentPagina

    obj = get_object_or_404(ContentPagina, slug=slug, published=True)
    prefix = slug.split("/")[0] if "/" in slug else ""
    label, url_name = _SECTION_LABELS.get(prefix, (None, None))
    ctx = {
        "seo_title": obj.get_seo_title(),
        "seo_description": obj.get_seo_description(),
        "pagina": obj,
        "section_label": label,
        "section_url": reverse(url_name) if url_name else None,
        "active_page": None,
    }
    if prefix in _RICH_PREFIXES:
        ctx["siblings"] = list(ContentPagina.objects.filter(
            slug__startswith=f"{prefix}/", published=True
        ).exclude(pk=obj.pk).order_by("titel")[:12])
        ctx["siblings_label"] = _RICH_PREFIXES[prefix]
        return render(request, "pages/content_rich.html", ctx)
    return render(request, "pages/content_pagina.html", ctx)


def make_hub_view(hub):
    """Build a listing view for a content hub (lists ContentPagina by prefix)."""
    def view(request):
        from .hubs import hub_children
        return render(request, "pages/content_hub.html", {
            "seo_title": hub["seo_title"],
            "seo_description": hub["seo_description"],
            "hub": hub,
            "children": hub_children(hub["prefix"]),
            "active_page": None,
        })

    view.__name__ = f"hubview_{hub['name']}"
    return view
