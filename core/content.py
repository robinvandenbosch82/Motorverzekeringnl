"""
Prototype page content.

This module holds the static content used by the design templates while the
site is being built out. It is deliberately isolated so that when the
content-systeem CSV importer lands, these literals can be swapped for
database-backed querysets without touching templates or views.

Geometric icons are tiny inline markup snippets matching the design's
"no-nonsense" badge system (petrol tile + orange shape). They are trusted,
authored markup (rendered with |safe), never user input.
"""

import re

from django.utils.safestring import mark_safe

_ICON_SQUARE = mark_safe('<span style="width:16px;height:16px;border:2.5px solid var(--orange);border-radius:4px;display:block;"></span>')
_ICON_CIRCLE = mark_safe('<span style="width:16px;height:16px;border-radius:50%;border:2.5px solid var(--orange);display:block;"></span>')
_ICON_BARS = mark_safe('<span style="width:18px;height:3px;background:var(--orange);display:block;box-shadow:0 6px 0 var(--orange),0 -6px 0 var(--orange);"></span>')
_ICON_TRI = mark_safe('<span style="width:0;height:0;border-left:8px solid transparent;border-right:8px solid transparent;border-bottom:14px solid var(--orange);display:block;"></span>')
_ICON_DIAMOND = mark_safe('<span style="width:12px;height:12px;background:var(--orange);border-radius:2px;transform:rotate(45deg);display:block;"></span>')
_ICON_PILL = mark_safe('<span style="width:16px;height:7px;background:var(--orange);border-radius:3px;display:block;"></span>')
_ICON_SQ_SM = mark_safe('<span style="width:14px;height:14px;background:var(--orange);border-radius:2px;display:block;"></span>')
_ICON_RING = mark_safe('<span style="width:13px;height:13px;border-radius:50%;border:2.5px solid var(--orange);display:block;"></span>')


def home_context():
    """Build the homepage context.

    FAQ, reviews, experts and the small situation cards are read from the CMS
    (admin is the source of truth); everything else is still seeded static and
    is wired to its admin model in a later step. Each DB section falls back to
    the static defaults below if the table is empty (e.g. before seeding).
    """
    return {
        "situatie_small": _db_situaties() or _STATIC_SITUATIE_SMALL,
        "situatie_featured": _db_situatie_featured(),
        "dekkingstiers": _db_dekkingstiers(),
        "home_blog": _db_home_blog(),
        "kb_tegels": _db_kb_categories(),
        "tier_wa": [
            {"label": "Schade aan anderen (wettelijk verplicht)", "included": True},
            {"label": "Hulp na ongeval & rechtsbijstand verkeer", "included": True},
            {"label": "Schade aan je eigen bus", "included": False},
            {"label": "Diefstal & ruitschade", "included": False},
        ],
        "tier_waplus": [
            "Alles uit WA",
            "Diefstal, brand & stormschade",
            "Ruitschade & aanrijding met wild",
            "Gereedschap meeverzekerbaar",
        ],
        "tier_allrisk": [
            {"label": "Alles uit WA+", "included": True},
            {"label": "Eigen schade, ook eigen schuld", "included": True},
            {"label": "Vervangende bus binnen 24 uur", "included": True},
            {"label": "Nieuwwaarderegeling tot 36 mnd", "included": True},
        ],
        "voordelen": [
            {"icon": _ICON_SQUARE, "title": "Vervanging in 24 uur", "text": "Pech of schade? Je staat snel weer in een bus, zodat het werk doorgaat."},
            {"icon": _ICON_CIRCLE, "title": "Gereedschap gedekt", "text": "Je inventaris meeverzekerd tot € 25.000, ook bij nachtelijke diefstal."},
            {"icon": _ICON_BARS, "title": "Onafhankelijk advies", "text": "Wij vergelijken 12+ verzekeraars en kiezen wat écht bij jou past."},
            {"icon": _ICON_TRI, "title": "Echte vakmensen", "text": "Vragen? Je spreekt een specialist die jouw branche kent, geen callcenter."},
        ],
        "reviews": _db_reviews() or REVIEWS,
        "trustpilot": _trustpilot(),
        "kb_categories": [
            {"icon": _ICON_SQUARE, "title": "Vragen & antwoorden", "count": "214 artikelen"},
            {"icon": _ICON_SQ_SM, "title": "Verzekeraars", "count": "32 profielen"},
            {"icon": _ICON_TRI, "title": "Beroepen", "count": "48 beroepen"},
            {"icon": _ICON_PILL, "title": "Modellen", "count": "76 bussen"},
            {"icon": _ICON_DIAMOND, "title": "Schade", "count": "63 artikelen"},
            {"icon": _ICON_BARS, "title": "Regelgeving", "count": "39 artikelen"},
            {"icon": _ICON_RING, "title": "Elektrisch", "count": "27 artikelen"},
        ],
        "faqs": _db_faqs() or FAQS,
        "experts": _db_experts() or EXPERTS,
    }


def over_ons_context():
    """Experts for the 'Over ons' page (admin = source of truth, static fallback)."""
    return {"experts": _db_experts() or EXPERTS}


# ── DB-backed accessors (admin = source of truth, static = fallback) ─────────
_STATIC_SITUATIE_SMALL = [
    {"title": "Meerdere bestuurders", "text": "Wisselend personeel achter het stuur? Verzeker iedereen in één keer."},
    {"title": "Negatieve schadevrije jaren", "text": "Minder mooi verleden? Wij vinden verzekeraars die je een eerlijke kans geven."},
    {"title": "Wagenpark", "text": "Van 2 tot 200 bussen op één polis. Eén overzicht, één aanspreekpunt."},
    {"title": "Koeriersdiensten", "text": "Veel kilometers, strakke deadlines. Dekking die meebeweegt met je ritten."},
]


def _db_faqs():
    from .models import Faq
    try:
        return [{"q": f.question, "a": f.answer}
                for f in Faq.objects.filter(page_key="home", active=True)]
    except Exception:
        return None


def _db_reviews():
    from .models import Review
    try:
        return [{"quote": r.quote, "name": r.name, "role": r.role,
                 "photo": r.get_photo_source(), "photo_alt": r.get_photo_alt()}
                for r in Review.objects.filter(active=True)]
    except Exception:
        return None


def _trustpilot():
    """Cached Trustpilot reviews + (optional) aggregate score. Shows the review
    cards as soon as any review exists; the numeric score + aggregateRating only
    appear once a real TrustScore + count are known (API fetch or manual entry),
    so we never invent an aggregate. Returns None when there are no reviews."""
    from .models import TrustpilotProfile, TrustpilotReview
    try:
        reviews = list(TrustpilotReview.objects.all()[:6])
        if not reviews:
            return None
        profile = TrustpilotProfile.load()
        return {"profile": profile, "reviews": reviews, "has_aggregate": profile.has_data}
    except Exception:
        return None


def _db_experts():
    from .models import Expert
    try:
        return [{"name": e.name, "role": e.role, "bio": e.bio, "tags": e.tags_list,
                 "photo": e.get_photo_source(), "photo_alt": e.get_photo_alt()}
                for e in Expert.objects.filter(active=True)]
    except Exception:
        return None


def _db_situaties():
    from .models import Situatie
    try:
        return [{"title": s.titel, "text": s.omschrijving, "link": s.link,
                 "photo": s.get_photo_source(), "photo_alt": s.get_photo_alt()}
                for s in Situatie.objects.filter(active=True, featured=False)]
    except Exception:
        return None


def _db_dekkingstiers():
    """Coverage tiers (WA/WA+/Allrisk) with their features, for the homepage."""
    from .models import Dekkingstier
    try:
        return list(Dekkingstier.objects.prefetch_related("features"))
    except Exception:
        return None


def _db_situatie_featured():
    """The two large featured situation cards on the homepage."""
    from .models import Situatie
    try:
        return list(Situatie.objects.filter(active=True, featured=True))
    except Exception:
        return None


def _blog_card(cp):
    """Map an imported 'blog' ContentPagina to the shape the blog cards expect."""
    return {"titel": cp.titel, "excerpt": cp.excerpt, "url": cp.get_absolute_url(),
            "image": cp.get_image_source(), "image_alt": cp.image_alt or cp.titel}


def _blog_pages():
    from .models import ContentPagina
    return (ContentPagina.objects.filter(contenttype="blog", published=True)
            .order_by("-imported_at", "titel"))


def _db_home_blog():
    """Homepage blog teaser: the latest three imported blog articles."""
    try:
        return [_blog_card(cp) for cp in _blog_pages()[:3]]
    except Exception:
        return None


def _kb_real_count(cat, pub):
    """Live count of items BEHIND a category tile, so the number always matches
    its destination page. Returns None for an unknown destination (keep stored)."""
    from django.db.models import Q

    from .hubs import HUBS, hub_children
    from .models import Verzekeraar

    link = (cat.link or "").strip()
    if "?q=" in link:  # kennisbank search tile → same filter the page uses, capped
        term = link.split("?q=", 1)[1]
        n = pub.filter(
            Q(titel__icontains=term) | Q(meta_description__icontains=term)
            | Q(focus_keyword__icontains=term) | Q(body_html__icontains=term)
        ).count()
        return min(n, 50)  # the /kennisbank/ results page shows at most 50
    path = link.strip("/")
    if path == "verzekeraars":
        return Verzekeraar.objects.filter(active=True).count()
    if path in ("", "kennisbank"):
        return pub.count()
    for h in HUBS:
        if h["prefix"] == path:
            return hub_children(path).count()
    return None


def _db_kb_categories():
    """Knowledge-base category tiles with LIVE counts. The admin-set 'aantal'
    string keeps its unit word ('profielen', 'bussen', …); only the number is
    swapped for the real figure (admin = source for the label, data for the count)."""
    import re

    from .models import ContentPagina, KennisbankCategorie
    try:
        cats = list(KennisbankCategorie.objects.all())
    except Exception:
        return None

    pub = ContentPagina.objects.filter(published=True)
    tiles = []
    for c in cats:
        try:
            n = _kb_real_count(c, pub)
        except Exception:
            n = None
        if n is None:
            aantal = c.aantal
        elif re.search(r"\d", c.aantal or ""):
            aantal = re.sub(r"\d[\d.]*", str(n), c.aantal, count=1)
        else:
            aantal = f"{n} {c.aantal}".strip()
        tiles.append({"naam": c.naam, "aantal": aantal, "icon": c.icon, "link": c.link})
    return tiles


_INSURER_STOP = re.compile(
    r"\b(?:bestelauto|bestelwagen|bestelbus|bedrijfsauto|autoverzekering|verzeker|"
    r"zakelijke?|grijs|eigen)|\b(?:en|met|voor|via|van|over)\b", re.I)
_INSURER_ALIAS = {"NN": "Nationale-Nederlanden"}


def _insurer_name(title):
    """Pull just the insurer brand from a long content-page title, e.g.
    'Allianz bestelautoverzekering met Tophersteller…' -> 'Allianz'."""
    t = title.split(",", 1)[0]                 # cut at first comma
    m = _INSURER_STOP.search(t)
    if m:
        t = t[:m.start()]
    name = t.strip(" ,-").strip() or title
    return _INSURER_ALIAS.get(name, name)


def verzekeraars_context():
    """Insurer overview cards + the imported per-insurer content pages (shown as
    compact brand tiles: only the insurer name + teaser)."""
    from .models import ContentPagina, Verzekeraar
    paginas = ContentPagina.objects.filter(
        slug__startswith="verzekeraars/", published=True).order_by("titel")
    return {
        "verzekeraars": list(Verzekeraar.objects.filter(active=True)),
        "verzekeraar_paginas": [
            {"naam": _insurer_name(p.titel), "excerpt": p.excerpt, "url": p.get_absolute_url()}
            for p in paginas
        ],
    }


def blog_context():
    """Blog overview: featured post + the rest, from the imported blog content."""
    cards = [_blog_card(cp) for cp in _blog_pages()]
    return {
        "featured_post": cards[0] if cards else None,
        "blog_posts": cards[1:],
    }


def kennisbank_context(request=None):
    """Knowledge-base overview: featured + popular articles + imported info pages.
    When the search box submits `?q=`, returns matching ContentPagina instead."""
    from django.db.models import Q

    from .models import ContentPagina, KennisbankArtikel

    query = (request.GET.get("q", "").strip() if request else "")
    if query:
        hits = ContentPagina.objects.filter(published=True).filter(
            Q(titel__icontains=query) | Q(meta_description__icontains=query)
            | Q(focus_keyword__icontains=query) | Q(body_html__icontains=query)
        ).order_by("titel")[:50]
        return {"kb_query": query, "kb_results": list(hits)}

    qs = KennisbankArtikel.objects.filter(active=True)
    return {
        "kb_featured": qs.filter(featured=True).first(),
        "kb_populair": list(qs.filter(featured=False)),
        # Top-level imported info pages (slug zonder prefix).
        "kb_infopaginas": list(ContentPagina.objects.filter(published=True)
                               .exclude(slug__contains="/").order_by("titel")),
    }


def dekkingen_context():
    """Imported dekkingen content pages + the coverage tiers (WA/WA+/Allrisk),
    the latter feeding the FinancialProduct/Offer structured data."""
    from .models import ContentPagina
    return {
        "dekking_paginas": list(ContentPagina.objects.filter(
            slug__startswith="dekkingen/", published=True).order_by("titel")),
        "dekkingstiers": _db_dekkingstiers(),
    }


def situaties_beroepen_context():
    """Situations + professions overview. Each profession card links to its real
    imported content page (falls back to the /beroep/ hub)."""
    from django.urls import reverse
    from django.utils.text import slugify

    from .models import Beroep, ContentPagina, Situatie

    beroep_pages = list(ContentPagina.objects.filter(
        slug__startswith="beroep/", published=True))
    hub_url = reverse("hub_beroep")

    def find_url(naam):
        key = slugify(naam)
        for p in beroep_pages:
            if key in p.slug:
                return p.get_absolute_url()
        return hub_url

    beroepen = [{
        "naam": b.naam, "premie_vanaf": b.premie_vanaf,
        "omschrijving": b.omschrijving, "url": find_url(b.naam),
    } for b in Beroep.objects.filter(active=True)]

    return {
        "situaties": list(Situatie.objects.filter(active=True)),
        "beroepen": beroepen,
        "beroep_hub_url": hub_url,
    }


REVIEWS = [
    {"quote": "Bus total loss op een maandag, dinsdag stond er een vervangende. Geen dag werk verloren. Precies waarvoor je verzekert.",
     "name": "Mark de Wit", "role": "Loodgieter · Ford Transit"},
    {"quote": "Eindelijk een verzekering die snapt dat mijn gereedschap meer waard is dan de bus zelf. Alles in één keer goed geregeld.",
     "name": "Samir El Idrissi", "role": "Elektricien · VW Crafter"},
    {"quote": "7 bussen op één polis, één overzicht in de app. Schade melden kost me twee minuten. Scheelt enorm in de planning.",
     "name": "Linda Boersma", "role": "Koeriersbedrijf · 7 bussen"},
]

FAQS = [
    {"q": "Ben ik verzekerd voor gereedschap in mijn bus?",
     "a": "Standaard niet, maar met onze inboeddekking verzeker je je complete inventaris tot € 25.000, ook bij diefstal buiten werktijd."},
    {"q": "Tellen negatieve schadevrije jaren mee?",
     "a": "Bij ons oplosbaar. We werken met verzekeraars die ondernemers met een minder verleden een eerlijke premie geven, zonder onnodige opslagen."},
    {"q": "Kan ik meerdere bestuurders meeverzekeren?",
     "a": "Ja. Voeg eenvoudig collega’s of personeel toe, ook wisselende bestuurders bij een wagenpark."},
    {"q": "Hoe snel ben ik verzekerd?",
     "a": "Bereken je premie in 2 minuten en sluit direct online af. Je bent vaak dezelfde dag nog gedekt."},
    {"q": "Verzekeren jullie ook elektrische bestelauto’s?",
     "a": "Zeker. Inclusief dekking voor de accu, laadkabel en laadpaalschade, speciaal voor de nieuwe generatie bussen."},
]

# Het echte redactie-/expertteam (gedeeld met zusje Autoverzekering.nl).
# photo_local verwijst naar media/experts/… zodat de {% picture %}-pipeline
# WebP/JPEG-varianten maakt. Bio's licht naar de bestelauto-context herschreven,
# feiten (startjaar, Wft-diploma's, Risk Groep) blijven ongewijzigd.
EXPERTS = [
    {"name": "Jerry", "role": "Expert verzekeringen",
     "bio": "Met zijn jarenlange ervaring (sinds 2017) kent Jerry de verzekeringsmarkt van "
            "binnenuit. Hij zorgt dat het aanbod in onze vergelijker zo volledig mogelijk is, "
            "zodat ondernemers zeker weten dat ze de beste deal hebben. Daarnaast controleert "
            "Jerry de content op de site op juistheid en geeft hij als veelgevraagd expert in de "
            "media praktisch advies aan ondernemers over hun verzekering.",
     "tags": ["Verzekeringsexpert", "Sinds 2017"],
     "photo_local": "experts/jerry.jpg",
     "photo_alt": "Jerry, expert verzekeringen bij Bestelautoverzekering.nl"},
    {"name": "Jean-Paul", "role": "Expert verzekeringen",
     "bio": "Met zijn achtergrond bij de Risk Groep begrijpt Jean-Paul de verzekeringsmarkt tot "
            "in detail. Sinds 2023 zorgt hij voor een scherp en volledig aanbod door direct met "
            "verzekeraars te onderhandelen over de premies. Hij bewaakt de feitelijke juistheid "
            "van de content en vertaalt eigen data-onderzoek naar heldere nieuwsberichten en "
            "advies over de juiste dekking.",
     "tags": ["Ex-Risk Groep", "Sinds 2023"],
     "photo_local": "experts/jean-paul.png",
     "photo_alt": "Jean-Paul, expert verzekeringen bij Bestelautoverzekering.nl"},
    {"name": "Alexandra", "role": "Happiness specialist",
     "bio": "Heb je een vraag over je bestelautoverzekering? Dan staat Alexandra voor je klaar. "
            "Als klantenservicemedewerker helpt ze je bij het kiezen van de juiste dekking en "
            "denkt ze graag met je mee als je er zelf niet uitkomt. Alexandra werkt al sinds 2016 "
            "in het team en heeft met haar Wft Basis en Wft Schade Particulier de kennis in huis "
            "om je van passend advies te voorzien.",
     "tags": ["Wft Basis", "Wft Schade Particulier"],
     "photo_local": "experts/alexandra.jpeg",
     "photo_alt": "Alexandra, happiness specialist bij Bestelautoverzekering.nl"},
]
