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
         "Motorverzekering vergelijken en direct afsluiten | Motorverzekering.nl",
         "Bereken je motorverzekering in ongeveer 1 minuut en sluit direct online af. "
         "Vergelijk WA, WA+ en Allrisk — rider-first, zonder tussenpersoon.",
         1.0, "daily", extra=content.home_context),
    Page("dekkingen", "dekkingen/", "pages/dekkingen.html",
         "Dekkingen: WA, WA + Casco en Allrisk motorverzekering | Motorverzekering.nl",
         "WA, WA + Casco of Allrisk voor je motor? Vergelijk de drie dekkingen helder naast "
         "elkaar en kies wat bij jou past.",
         0.9, "monthly", extra=content.dekkingen_context),
    Page("kennisbank", "kennisbank/", "pages/kennisbank.html",
         "Kennisbank motorverzekering: veelgestelde vragen | Motorverzekering.nl",
         "Antwoord op je vragen over afsluiten, dekkingen, premie, schade en beveiliging — "
         "geschreven en gecontroleerd door onze WFT-experts.",
         0.8, "weekly", extra=content.kennisbank_context),
    Page("blog", "blog/", "pages/blog.html",
         "Blog: tips, onderhoud en verzekeren voor motorrijders | Motorverzekering.nl",
         "Verhalen, tips en uitleg voor onderweg: onderhoud, veiligheid, touring en alles over "
         "je motorverzekering — zonder jargon.",
         0.7, "weekly", extra=content.blog_context),
    Page("over_ons", "over-ons/", "pages/over_ons.html",
         "Onze experts & redactieproces | Motorverzekering.nl",
         "Onze content wordt geschreven door verzekeringsexperts en gecontroleerd door "
         "WFT-gecertificeerde adviseurs. Maak kennis met het team achter onze adviezen.",
         0.6, "monthly", extra=content.over_ons_context),
    Page("klantenservice", "klantenservice/", "pages/klantenservice.html",
         "Klantenservice & contact | Motorverzekering.nl",
         "Bereik ons via chat, WhatsApp of e-mail, bekijk de openingstijden en regel "
         "veelvoorkomende zaken direct zelf.",
         0.6, "monthly", extra=content.klantenservice_context),
    Page("mijn_omgeving", "mijn-omgeving/", "pages/mijn_omgeving.html",
         "Mijn omgeving | Motorverzekering.nl",
         "Je persoonlijke omgeving is nog in ontwikkeling. Voor wijzigingen en vragen "
         "helpt onze klantenservice je graag persoonlijk.",
         0.3, "monthly"),
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


# Eén-pagina-per-claim: koppel een korte kennisbank-vraag aan het bijbehorende
# blog-diepteartikel (kennisbank-slug -> blog-slug). Zo versterken de Q&A en de
# pillar elkaar (hub & spoke) i.p.v. te concurreren om dezelfde claim.
_KB_VERDIEPING = {
    "hoe-werken-schadevrije-jaren-en-no-claim": "schadevrije-jaren-bij-een-motorverzekering",
    "welk-art-slot-heb-ik-nodig-voor-mijn-motor": "welke-beveiligingseisen-stellen-verzekeraars-aan-je-motor",
    "ben-ik-verzekerd-bij-diefstal-van-mijn-motor": "welke-beveiligingseisen-stellen-verzekeraars-aan-je-motor",
    "kan-ik-mijn-motorverzekering-in-de-winter-stopzetten": "winterstop-of-motor-schorsen-wat-is-slimmer",
    "wat-is-het-verschil-tussen-wa-wa-en-allrisk": "wa-wa-of-allrisk-welke-motorverzekering-past-bij-jouw-motor",
    "wat-dekt-wa-casco-precies": "wa-wa-of-allrisk-welke-motorverzekering-past-bij-jouw-motor",
    "ben-ik-verzekerd-bij-schade-aan-mijn-opzittende": "opzittendenverzekering-voor-je-motor-wat-dekt-het",
    "waarom-verschilt-mijn-premie-van-vorig-jaar": "wat-kost-een-motorverzekering-in-nederland",
}


def kennisbank_artikel(request, slug):
    """Detailpagina van één kennisbank-vraag (slug-based, DB = bron)."""
    import re

    from .models import BlogArtikel, KennisbankArtikel
    artikel = get_object_or_404(KennisbankArtikel, slug=slug, active=True)
    related = list(KennisbankArtikel.objects.filter(categorie=artikel.categorie, active=True)
                   .exclude(pk=artikel.pk)[:3])
    verdieping = None
    _bs = _KB_VERDIEPING.get(slug)
    if _bs:
        verdieping = BlogArtikel.objects.filter(slug=_bs, active=True).first()
    plain = re.sub(r"<[^>]+>", "", artikel.kort_antwoord or artikel.excerpt or "")
    return render(request, "pages/kennisbank_artikel.html", {
        "artikel": artikel,
        "related": related,
        "verdieping": verdieping,
        "seo_title": f"{artikel.titel} | Motorverzekering.nl",
        "seo_description": (artikel.excerpt or plain)[:160],
        "active_page": "kennisbank",
    })


def blog_artikel(request, slug):
    """Detailpagina van één blogartikel (slug-based, DB = bron)."""
    from .models import BlogArtikel
    artikel = get_object_or_404(BlogArtikel, slug=slug, active=True)
    related = list(BlogArtikel.objects.filter(active=True).exclude(pk=artikel.pk)
                   .filter(categorie=artikel.categorie)[:3])
    if len(related) < 3:
        extra = BlogArtikel.objects.filter(active=True).exclude(
            pk__in=[artikel.pk] + [r.pk for r in related]).order_by("order")[:3 - len(related)]
        related += list(extra)
    return render(request, "pages/blog_artikel.html", {
        "artikel": artikel,
        "related": related,
        "seo_title": artikel.meta_title or f"{artikel.titel} | Motorverzekering.nl",
        "seo_description": artikel.meta_description or artikel.excerpt,
        "active_page": "blog",
    })


def content_pagina(request, slug):
    """Render an imported content-fabriek page (catch-all by slug)."""
    from django.urls import NoReverseMatch, reverse

    from .models import ContentPagina

    obj = get_object_or_404(ContentPagina, slug=slug, published=True)
    prefix = slug.split("/")[0] if "/" in slug else ""
    label, url_name = _SECTION_LABELS.get(prefix, (None, None))
    section_url = None
    if url_name:
        try:  # overview route may have been removed → breadcrumb without a link
            section_url = reverse(url_name)
        except NoReverseMatch:
            section_url = None
    ctx = {
        "seo_title": obj.get_seo_title(),
        "seo_description": obj.get_seo_description(),
        "pagina": obj,
        "section_label": label,
        "section_url": section_url,
        "active_page": None,
    }
    if prefix in _RICH_PREFIXES:
        ctx["siblings"] = list(ContentPagina.objects.filter(
            slug__startswith=f"{prefix}/", published=True
        ).exclude(pk=obj.pk).order_by("titel")[:12])
        ctx["siblings_label"] = _RICH_PREFIXES[prefix]
        return render(request, "pages/content_rich.html", ctx)
    return render(request, "pages/content_pagina.html", ctx)
