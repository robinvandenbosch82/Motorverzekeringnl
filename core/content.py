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
    """Build the homepage context for the Claude Design 'MV Homepage'.

    DB-coupled (admin = source of truth, with a static fallback so the page
    renders before seeding): the coverage tiers (Dekkingstier), reviews
    (Review), FAQ (Faq, page_key='home') and experts (Expert). The remaining
    presentational lists (why/docs/trust/info/contact) are authored content
    that lives here in code, they have no natural admin model yet and are
    rendered server-side just the same.
    """
    return {
        "secties": secties("home"),
        # ── DB-coupled blocks ──
        "dekkingstiers": _db_dekkingstiers() or TIER_CARDS_FALLBACK,
        "reviews": _db_reviews() or REVIEWS,
        "faqs": _db_faqs() or FAQS,
        "experts": [{**e, "initials": _initials(e["name"])}
                    for e in (_db_experts() or EXPERTS)],
        "blog_items": BLOG_ITEMS,
        # ── Card lists (admin = source: Kaart; static fallback below) ──
        "why_items": _cards("home_waarom", WHY_ITEMS),
        "doc_items": _cards("home_documenten", DOC_ITEMS),
        "trust_items": _cards("home_trust", TRUST_ITEMS),
        "info_groups": _cards("home_info", INFO_GROUPS),
        "contact_direct": _cards("home_contact_direct", CONTACT_DIRECT),
        "contact_channels": _cards("home_contact_kanaal", CONTACT_CHANNELS),
        "steps": _cards("home_stappen", STEPS),
    }


# ── Generic admin-content helpers (SectieTekst + Kaart, with static fallback) ─
def secties(pagina):
    """Dict of {sleutel: SectieTekst} for a page (admin = source of truth)."""
    from .models import SectieTekst
    try:
        return {s.sleutel: s for s in SectieTekst.objects.filter(pagina=pagina)}
    except Exception:
        return {}


def kaarten(blok):
    from .models import Kaart
    try:
        return list(Kaart.objects.filter(blok=blok, actief=True))
    except Exception:
        return []


def _cards(blok, fallback):
    """Return the admin-managed Kaart rows for `blok` (normalised to the dict
    shape the templates expect: tag/titel/tekst/meta/url + matrix flags), or the
    static fallback when the block is empty."""
    ks = kaarten(blok)
    if not ks:
        return fallback
    return [{"tag": k.tag, "titel": k.titel, "tekst": k.tekst, "meta": k.meta,
             "url": k.url, "incl_wa": k.incl_wa, "incl_waplus": k.incl_waplus,
             "incl_allrisk": k.incl_allrisk} for k in ks]


# ── Authored homepage content (fallback for the Kaart blocks; unified shape
#    tag/titel/tekst/meta so DB rows and fallback render through one template). ─
WHY_ITEMS = [
    {"tag": "EU", "titel": "Altijd hulp onderweg",
     "tekst": "24/7 alarmcentrale in heel Europa bij pech, schade of diefstal."},
    {"tag": "MAIL", "titel": "Direct je documenten",
     "tekst": "Na afsluiten ontvang je polis, voorwaarden en groene kaart meteen per e-mail."},
    {"tag": "FLEX", "titel": "Flexibel & vrij",
     "tekst": "Geen verplicht account en maandelijks opzegbaar, jij houdt de regie."},
]

DOC_ITEMS = [
    {"tag": "PDF", "titel": "Polisvoorwaarden", "meta": "Per dekking · download"},
    {"tag": "KAART", "titel": "Verzekeringskaart", "meta": "WA · WA+ · Allrisk"},
    {"tag": "MIJN", "titel": "Groene kaart & polisblad", "meta": "Direct na afsluiten"},
]

TRUST_ITEMS = [
    {"titel": "9,1/10", "tekst": "Klantbeoordeling · 2.314 reviews"},
    {"titel": "tot 80%", "tekst": "No-claim korting bij schadevrij rijden"},
    {"titel": "100.000+", "tekst": "Motorrijders verzekerd"},
    {"titel": "5 min", "tekst": "Gemiddeld online afgesloten"},
]

STEPS = [
    {"tag": "01", "titel": "Kenteken invoeren",
     "tekst": "We herkennen je motor direct en vullen de gegevens vast voor je in."},
    {"tag": "02", "titel": "Premie & dekking kiezen",
     "tekst": "Je ziet je premie en kiest WA, WA+ of Allrisk met de opties die je wilt."},
    {"tag": "03", "titel": "Direct verzekerd",
     "tekst": "Sluit online af zonder verplicht account. Je groene kaart en polis komen meteen per e-mail."},
]

# info-groups: tekst = one link per line.
INFO_GROUPS = [
    {"titel": "Dekking & voorwaarden",
     "tekst": "Dekking motorverzekering\nAanvullende dekkingen\nSchadevrije jaren\nEigen risico\nART- en SCM-beveiliging"},
    {"titel": "Je verzekering aanpassen",
     "tekst": "Motorverzekering opzeggen\nStopzetten in de winter\nMotor verkocht\nVerhuizen doorgeven"},
]

CONTACT_DIRECT = [
    {"titel": "Schade melden"}, {"titel": "Mijn verzekering"},
    {"titel": "Verzekering wijzigen"}, {"titel": "Overstappen naar ons"},
]
CONTACT_CHANNELS = [
    {"tag": "CHAT", "titel": "Chat met ons", "meta": "Direct antwoord, ma,zo"},
    {"tag": "APP", "titel": "WhatsApp", "meta": "Reactie binnen ~15 min"},
    {"tag": "BEL", "titel": "Bel ons", "meta": "Werkdagen 8:00,20:00"},
]

# Homepage blog teasers (bundled motor images, served from static). Used as the
# fallback when no imported blog ContentPagina's exist yet.
BLOG_ITEMS = [
    {"title": "Maak je motor rijklaar", "image": "img/motor/moto-11890953.jpg",
     "desc": "Na de winterstop weer veilig de weg op? Met deze checklist voorkom je schade en verrassingen."},
    {"title": "Preventietips voor onderweg", "image": "img/motor/moto-2519374.jpg",
     "desc": "Goede preventie scheelt ellende: onderhoud, zichtbaarheid en de juiste beschermende kleding."},
    {"title": "Welk ART-slot heb je nodig?", "image": "img/motor/moto-1413412.jpg",
     "desc": "Klasse 3 of 4? We leggen uit welk slot je verzekeraar vraagt en hoe het je premie verlaagt."},
]

# Coverage-tier summary cards shown on the homepage, used as a fallback before
# the Dekkingstier rows are seeded. The DB rows (with features) are the real
# source; these mirror their key fields (code/naam/prijs/omschrijving/highlight).
TIER_CARDS_FALLBACK = [
    {"code": "WA", "naam": "Wettelijk verplicht", "prijs": "6", "highlight": False,
     "omschrijving": "Schade aan anderen, inclusief groene kaart. De wettelijke basis."},
    {"code": "WA + Casco", "naam": "Beperkt casco", "prijs": "12", "highlight": True,
     "omschrijving": "Plus diefstal, brand, ruit, storm en aanrijding met een dier."},
    {"code": "Allrisk", "naam": "Maximale dekking", "prijs": "19", "highlight": False,
     "omschrijving": "Ook schade aan je eigen motor en een nieuwwaarderegeling."},
]

# ── Coverage-tier feature matrix (motor), consumed by seed_content to fill the
#    Dekkingstier + DekkingFeature rows. (label, in_wa, in_waplus, in_allrisk). ─
TIER_FEATURES = [
    ("Aansprakelijkheid, schade aan anderen", True, True, True),
    ("Inclusief groene kaart", True, True, True),
    ("Diefstal & brand", False, True, True),
    ("Ruitschade", False, True, True),
    ("Storm, natuur & aanrijding met dier", False, True, True),
    ("Schade aan je eigen motor", False, False, True),
    ("Nieuwwaarderegeling eerste jaren", False, False, True),
]

# (code, subtitle, prijs vanaf p/m, highlight, omschrijving), seed source.
TIER_META = [
    ("WA", "Wettelijk verplicht", "6", False,
     "Schade aan anderen, inclusief groene kaart. De wettelijke basis."),
    ("WA + Casco", "Beperkt casco", "12", True,
     "Plus diefstal, brand, ruit, storm en aanrijding met een dier."),
    ("Allrisk", "Maximale dekking", "19", False,
     "Ook schade aan je eigen motor en een nieuwwaarderegeling."),
]


def _initials(name):
    """Avatar initials: first letter of each word (max 3), or the first two
    letters for a single-word name. 'Jean-Paul de Vries' → 'JD', 'Jerry' → 'Je'."""
    parts = [p for p in re.split(r"[\s-]+", (name or "").strip()) if p]
    if len(parts) >= 2:
        return "".join(p[0] for p in parts[:3]).upper()
    return (parts[0][:2].capitalize() if parts else "")


def over_ons_context():
    """Onze experts page: experts (Expert model) + editable section copy and the
    redactieproces / family card lists (admin = source, static fallback)."""
    return {
        "experts": [{**e, "initials": _initials(e["name"])}
                    for e in (_db_experts() or EXPERTS)],
        "secties": secties("over_ons"),
        "proces": _cards("over_ons_proces", OVER_ONS_PROCES),
        "familie": _cards("over_ons_familie", OVER_ONS_FAMILIE),
    }


OVER_ONS_PROCES = [
    {"tag": "01", "titel": "Geschreven door experts",
     "tekst": "Elk artikel komt van iemand met kennis van verzekeren én van motorrijden."},
    {"tag": "02", "titel": "Gecontroleerd door WFT-adviseurs",
     "tekst": "Een gecertificeerd adviseur controleert de inhoud op juistheid en wetgeving."},
    {"tag": "03", "titel": "Onderbouwd met bronnen",
     "tekst": "We verwijzen naar officiële bronnen zoals de RDW en de verzekeraars zelf."},
    {"tag": "04", "titel": "Regelmatig bijgewerkt",
     "tekst": "Verandert er iets in de markt of regelgeving? Dan passen we de content aan."},
]

OVER_ONS_FAMILIE = [
    {"titel": "Finckers & Risk"}, {"titel": "Overstappen.nl"}, {"titel": "Autoverzekering.nl"},
]


# ── DB-backed accessors (admin = source of truth, static = fallback) ─────────
# Seed-only data for models that feed OTHER (not-yet-redesigned) pages. Kept as
# module constants so seed_content does not depend on home_context()'s shape.
SITUATIE_SMALL = [
    {"title": "Meerdere bestuurders", "text": "Wisselend personeel achter het stuur? Verzeker iedereen in één keer."},
    {"title": "Negatieve schadevrije jaren", "text": "Minder mooi verleden? Wij vinden verzekeraars die je een eerlijke kans geven."},
    {"title": "Wagenpark", "text": "Van 2 tot 200 bussen op één polis. Eén overzicht, één aanspreekpunt."},
    {"title": "Koeriersdiensten", "text": "Veel kilometers, strakke deadlines. Dekking die meebeweegt met je ritten."},
]

# Knowledge-base category tiles (feed the KennisbankCategorie model / kennisbank
# page). (title, count, icon-key).
KB_CATEGORIES = [
    {"title": "Vragen & antwoorden", "count": "214 artikelen"},
    {"title": "Verzekeraars", "count": "32 profielen"},
    {"title": "Beroepen", "count": "48 beroepen"},
    {"title": "Modellen", "count": "76 bussen"},
    {"title": "Schade", "count": "63 artikelen"},
    {"title": "Regelgeving", "count": "39 artikelen"},
    {"title": "Elektrisch", "count": "27 artikelen"},
]


def _faqs_for(page):
    """FAQ items for a page (Faq model, page_key=page). admin = source."""
    from .models import Faq
    try:
        rows = [{"q": f.question, "a": f.answer}
                for f in Faq.objects.filter(page_key=page, active=True)]
        return rows or None
    except Exception:
        return None


def _db_faqs():
    return _faqs_for("home")


def _db_reviews():
    from .models import Review
    try:
        return [{"text": r.quote, "name": r.name, "place": r.role,
                 "score": r.score, "date": r.datum,
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


def klantenservice_context():
    """Klantenservice page: live open/closed status, opening hours (today
    highlighted), contact channels (from SiteSettings) and self-service links."""
    from django.utils import timezone

    from .models import SiteSettings
    site = SiteSettings.load()
    now = timezone.localtime()
    wd = now.weekday()                     # Mon=0 … Sun=6
    mins = now.hour * 60 + now.minute
    is_open = wd <= 4 and 510 <= mins < 1020   # ma,vr 08:30,17:00
    days = [("Maandag", "08:30, 17:00"), ("Dinsdag", "08:30, 17:00"),
            ("Woensdag", "08:30, 17:00"), ("Donderdag", "08:30, 17:00"),
            ("Vrijdag", "08:30, 17:00"), ("Zaterdag", "Gesloten"), ("Zondag", "Gesloten")]
    return {
        "secties": secties("klantenservice"),
        "weten": _cards("klantenservice_weten", KLANTENSERVICE_WETEN),
        "ks_open": is_open,
        "ks_status": ("Nu open · gemiddelde reactietijd 5 minuten" if is_open
                      else "Nu gesloten · bereikbaar ma,vr vanaf 08:30"),
        "ks_rows": [{"d": d, "t": t, "today": i == wd} for i, (d, t) in enumerate(days)],
        "ks_contacts": [
            {"tag": "CHAT", "title": "Live chat", "sub": "Start een gesprek met ons team",
             "meta": "Gemiddelde reactie binnen 5 min", "cta": "Start chat", "href": "#"},
            {"tag": "APP", "title": "WhatsApp", "sub": site.whatsapp,
             "meta": "Reactie binnen enkele minuten", "cta": "Open WhatsApp",
             "href": site.whatsapp_link or "#"},
            {"tag": "MAIL", "title": "E-mail", "sub": site.email,
             "meta": "Reactie binnen 2 uur", "cta": "Stuur een e-mail",
             "href": "mailto:" + site.email},
        ],
    }


KLANTENSERVICE_WETEN = [
    {"titel": "WFT-gecertificeerde medewerkers"},
    {"titel": "14 dagen bedenktijd na het afsluiten"},
    {"titel": "100% onafhankelijk advies"},
    {"titel": "Klanten beoordelen ons met een 9,1"},
]


def blog_context(request=None):
    """Blog overview (DB-coupled to BlogArtikel): a featured post + a grid the
    visitor can filter by category via ?cat=. Admin = source of truth."""
    from .models import BlogArtikel
    sec = secties("blog")
    qs = list(BlogArtikel.objects.filter(active=True))
    if not qs:
        return {"secties": sec, "featured_post": None, "blog_cards": [],
                "blog_cats": ["Alles"], "blog_active_cat": "Alles"}
    featured = next((b for b in qs if b.featured), qs[0])
    rest = [b for b in qs if b.pk != featured.pk]
    cats = ["Alles"] + list(dict.fromkeys(b.categorie for b in rest if b.categorie))
    active = (request.GET.get("cat", "").strip() if request else "") or "Alles"
    if active not in cats:
        active = "Alles"
    grid = rest if active == "Alles" else [b for b in rest if b.categorie == active]

    def card(b):
        return {"titel": b.titel, "excerpt": b.excerpt, "leestijd": b.leestijd,
                "categorie": b.categorie, "image": b.get_photo_source(),
                "url": b.get_absolute_url()}
    return {
        "secties": sec,
        "featured_post": card(featured),
        "blog_cards": [card(b) for b in grid],
        "blog_cats": cats,
        "blog_active_cat": active,
    }


# Knowledge-base categories (Claude Design): title → short mono tag, in order.
KB_CAT_TAGS = {
    "Verzekering afsluiten": "START", "Dekkingen": "DEK", "Premie & korting": "€",
    "Schade": "SCHADE", "Wijzigen & opzeggen": "WIJZIG", "Beveiliging & diefstal": "ART",
}


def kennisbank_context(request=None):
    """Kennisbank (Claude Design): category cards + a question list the visitor
    can filter by category (?cat=) and search (?q=), all server-side. Questions
    are DB-coupled to KennisbankArtikel (admin = source of truth)."""
    from .models import KennisbankArtikel
    qs = list(KennisbankArtikel.objects.filter(active=True))

    counts = {}
    for a in qs:
        counts[a.categorie] = counts.get(a.categorie, 0) + 1
    cats = [{"title": c, "tag": KB_CAT_TAGS.get(c, "?"), "count": counts[c]}
            for c in KB_CAT_TAGS if counts.get(c)]

    query = (request.GET.get("q", "").strip() if request else "")
    active = (request.GET.get("cat", "").strip() if request else "")
    if active not in counts:
        active = ""
    results = qs
    if active:
        results = [a for a in results if a.categorie == active]
    if query:
        ql = query.lower()
        results = [a for a in results
                   if ql in a.titel.lower() or ql in (a.categorie or "").lower()]

    if query:
        n = len(results)
        list_title = f'{n} {"resultaat" if n == 1 else "resultaten"} voor "{query}"'
    elif active:
        list_title = active
    else:
        list_title = "Meestgestelde vragen"

    return {
        "secties": secties("kennisbank"),
        "kb_cats": cats,
        "kb_results": results,
        "kb_query": query,
        "kb_active_cat": active,
        "kb_list_title": list_title,
        "kb_empty": not results,
    }


def blog_artikel_context():
    """Single demo blog article: the editorial body is admin-managed rich HTML
    (SectieTekst pagina='blog_artikel'); the chrome stays in the template."""
    return {"secties": secties("blog_artikel")}


def kennisbank_artikel_context():
    """Single demo kennisbank article: kort-antwoord + body + bronnen are
    admin-managed rich HTML (SectieTekst pagina='kennisbank_artikel')."""
    return {"secties": secties("kennisbank_artikel")}


def dekkingen_context():
    """Dekkingen page (Claude Design): three tier cards (DB-coupled to
    Dekkingstier, with an authored 'beste voor' line), the coverage matrix, the
    optional extras and the page FAQ."""
    tiers = _db_dekkingstiers() or TIER_CARDS_FALLBACK
    cards = []
    for t in tiers:
        get = (lambda k: getattr(t, k)) if not isinstance(t, dict) else (lambda k: t.get(k))
        cards.append({
            "code": get("code"), "naam": get("naam"), "prijs": get("prijs"),
            "omschrijving": get("omschrijving"), "highlight": get("highlight"),
            "best_for": TIER_BEST_FOR.get(get("code"), ""),
        })
    return {
        "secties": secties("dekkingen"),
        "dekking_cards": cards,
        "cov_features": _cards("dekkingen_matrix", DEKKINGEN_MATRIX),
        "extras": _cards("dekkingen_extra", DEKKINGEN_EXTRAS),
        "eigenrisico": _cards("dekkingen_eigenrisico", DEKKINGEN_EIGENRISICO),
        "dekkingen_faqs": _faqs_for("dekkingen") or DEKKINGEN_FAQS,
    }


TIER_BEST_FOR = {
    "WA": "Oudere motoren met een lagere dagwaarde.",
    "WA + Casco": "De meeste motorrijders met een courante motor.",
    "Allrisk": "Nieuwe en duurdere motoren.",
}

# Unified-shape fallbacks for the Kaart blocks on the Dekkingen page.
DEKKINGEN_EXTRAS = [
    {"tag": "+", "titel": "Pechhulp Europa", "tekst": "24/7 hulp bij pech, thuis en in heel Europa.",
     "url": "/blog/pechhulp-voor-je-motor-in-nederland-en-heel-europa/"},
    {"tag": "+", "titel": "Accessoiredekking", "tekst": "Koffers, navigatie en accessoires meeverzekerd.",
     "url": "/blog/zijn-helm-motorkleding-en-accessoires-meeverzekerd/"},
    {"tag": "+", "titel": "Opzittenden", "tekst": "Dekking voor letselschade van je passagier.",
     "url": "/blog/opzittendenverzekering-voor-je-motor-wat-dekt-het/"},
    {"tag": "+", "titel": "Motorkleding & helm", "tekst": "Vergoeding voor je gear na een ongeval.",
     "url": "/blog/zijn-helm-motorkleding-en-accessoires-meeverzekerd/"},
    {"tag": "+", "titel": "Rechtsbijstand", "tekst": "Juridische hulp bij een verkeersconflict.",
     "url": "/blog/rechtsbijstand-bij-je-motorverzekering-wanneer-nodig/"},
    {"tag": "+", "titel": "Vervangend vervoer", "tekst": "Mobiel blijven terwijl je motor wordt hersteld.",
     "url": "/blog/vervangend-vervoer-bij-motorschade-hoe-zit-het/"},
]

# Coverage matrix rows (titel + per-tier inclusion), from the motor feature set.
DEKKINGEN_MATRIX = [
    {"titel": f[0], "incl_wa": f[1], "incl_waplus": f[2], "incl_allrisk": f[3]}
    for f in TIER_FEATURES
]

DEKKINGEN_EIGENRISICO = [
    {"titel": "€ 0 eigen risico", "meta": "hoogste premie"},
    {"titel": "€ 150 eigen risico", "meta": "standaard"},
    {"titel": "€ 300 eigen risico", "meta": "laagste premie"},
]

DEKKINGEN_FAQS = [
    {"q": "Is WA echt verplicht voor mijn motor?",
     "a": "Ja. Zodra een motor op jouw naam staat, moet die minimaal WA-verzekerd zijn, ook als je er niet mee rijdt. Zonder verzekering riskeer je een boete van € 500."},
    {"q": "Wat is het verschil tussen WA + Casco en Allrisk?",
     "a": "WA + Casco dekt schade aan je eigen motor door diefstal, brand, storm en ruit. Allrisk dekt daarbovenop ook schade door eigen schuld of een ongeval, plus een nieuwwaarderegeling in de eerste jaren."},
    {"q": "Kan ik later van dekking wisselen?",
     "a": "Ja, je kunt je dekking aanpassen. Een hogere dekking gaat doorgaans direct in; bij verlagen gelden soms voorwaarden. Onze klantenservice helpt je hierbij."},
    {"q": "Hoe wordt mijn premie bepaald?",
     "a": "Je premie hangt af van je motor, je postcode, je leeftijd en je schadevrije jaren. Bereken je premie met je kenteken om een persoonlijk bedrag te zien."},
]


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


# Homepage reviews (fallback before the Review rows are seeded). Keys mirror
# _db_reviews(): score/date/text/name/place.
REVIEWS = [
    {"score": "10", "date": "4 juni 2026",
     "text": "Binnen tien minuten geregeld en mijn groene kaart stond meteen in mijn mail. Top.",
     "name": "Mark V.", "place": "Utrecht"},
    {"score": "9", "date": "28 mei 2026",
     "text": "Eindelijk een motorverzekering die ik snap. Heldere dekkingen, geen tussenpersoon-gedoe.",
     "name": "Sanne D.", "place": "Eindhoven"},
    {"score": "10", "date": "19 mei 2026",
     "text": "Premie vergeleken en direct online afgesloten. Mijn no-claim is netjes overgenomen.",
     "name": "Joost K.", "place": "Groningen"},
]

FAQS = [
    {"q": "Wanneer moet mijn motor verzekerd zijn?",
     "a": "Zodra de motor op jouw naam staat. Een onverzekerde motor levert een boete van € 500 op, dus regel je dekking meteen."},
    {"q": "Wat is een meldcode?",
     "a": "Een code die bij je kenteken hoort en die nodig is om je verzekering definitief te regelen. In de aanvraag laten we precies zien waar je die vindt."},
    {"q": "Welk slot heb ik nodig?",
     "a": "Meestal minimaal een ART-goedgekeurd slot van klasse 3, in grote steden vaak klasse 4. Een goedgekeurd slot verlaagt je premie én is voorwaarde voor vergoeding bij diefstal."},
    {"q": "Kan ik in de winter stoppen met rijden?",
     "a": "Met de winterstop-optie betaal je minder in de maanden dat je niet rijdt. Je blijft dan beperkt verzekerd tegen diefstal en brand."},
    {"q": "Heb ik mijn schadevrije jaren nodig?",
     "a": "Hoe meer schadevrije jaren, hoe lager je premie. Je hoeft ze niet zelf op te zoeken, wij vragen ze voor je op."},
]

# Het echte redactie-/expertteam (gedeeld met zusje Autoverzekering.nl).
# photo_local verwijst naar media/experts/… zodat de {% picture %}-pipeline
# WebP/JPEG-varianten maakt. Bio's naar de motor-context herschreven; feiten
# (startjaar, Wft-diploma's, Risk Groep) blijven ongewijzigd.
EXPERTS = [
    {"name": "Jerry", "role": "Expert verzekeringen",
     "bio": "Met zijn jarenlange ervaring (sinds 2017) kent Jerry de verzekeringsmarkt van "
            "binnenuit. Hij zorgt dat het aanbod in onze vergelijker zo volledig mogelijk is, "
            "zodat motorrijders zeker weten dat ze de beste deal hebben. Daarnaast controleert "
            "Jerry de content op de site op juistheid en geeft hij als veelgevraagd expert in de "
            "media praktisch advies over de motorverzekering.",
     "tags": ["Verzekeringsexpert", "Sinds 2017"],
     "photo_local": "experts/jerry.jpg",
     "photo_alt": "Jerry, expert verzekeringen bij Motorverzekering.nl"},
    {"name": "Jean-Paul", "role": "Expert verzekeringen",
     "bio": "Met zijn achtergrond bij de Risk Groep begrijpt Jean-Paul de verzekeringsmarkt tot "
            "in detail. Sinds 2023 zorgt hij voor een scherp en volledig aanbod door direct met "
            "verzekeraars te onderhandelen over de premies. Hij bewaakt de feitelijke juistheid "
            "van de content en vertaalt eigen data-onderzoek naar heldere nieuwsberichten en "
            "advies over de juiste dekking.",
     "tags": ["Ex-Risk Groep", "Sinds 2023"],
     "photo_local": "experts/jean-paul.png",
     "photo_alt": "Jean-Paul, expert verzekeringen bij Motorverzekering.nl"},
    {"name": "Alexandra", "role": "Happiness specialist",
     "bio": "Heb je een vraag over je motorverzekering? Dan staat Alexandra voor je klaar. "
            "Als klantenservicemedewerker helpt ze je bij het kiezen van de juiste dekking en "
            "denkt ze graag met je mee als je er zelf niet uitkomt. Alexandra werkt al sinds 2016 "
            "in het team en heeft met haar Wft Basis en Wft Schade Particulier de kennis in huis "
            "om je van passend advies te voorzien.",
     "tags": ["Wft Basis", "Wft Schade Particulier"],
     "photo_local": "experts/alexandra.jpeg",
     "photo_alt": "Alexandra, happiness specialist bij Motorverzekering.nl"},
]
