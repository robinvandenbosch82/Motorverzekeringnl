"""
Content hubs: per-content-type overview pages that list the imported
ContentPagina items by slug-prefix. Single source of truth — add a hub here and
it gets a route (core.urls), a nav entry (context_processors), and a sitemap
entry. Only prefixes WITHOUT an existing design page live here; verzekeraars and
dekkingen are woven into their existing overview pages instead.
"""

HUBS = [
    {
        "name": "hub_modellen", "prefix": "merk-model", "path": "merk-model/",
        "nav_group": "Verzekeren", "nav_label": "Per merk & model", "kort": True,
        "eyebrow": "Per merk & model",
        "titel": "Bestelauto verzekeren per merk en model",
        "intro": "Elk busmodel heeft zijn eigen risico's, van diefstalgevoeligheid tot "
                 "onderdeelprijzen. Kies je model en zie waar je op moet letten.",
        "seo_title": "Bestelauto verzekeren per merk & model | Bestelautoverzekering.nl",
        "seo_description": "Per bestelautomodel: premie, diefstalrisico en aandachtspunten "
                           "bij het verzekeren. Vind jouw model en bereken je premie.",
    },
    {
        "name": "hub_beroep", "prefix": "beroep", "path": "beroep/",
        "nav_group": "Verzekeren", "nav_label": "Per beroep", "kort": True,
        "eyebrow": "Per beroep",
        "titel": "Bestelautoverzekering per beroep",
        "intro": "Een koerier rijdt anders dan een aannemer. Vind de dekking en "
                 "aandachtspunten die passen bij jouw vak.",
        "seo_title": "Bestelautoverzekering per beroep | Bestelautoverzekering.nl",
        "seo_description": "Verzekering op maat per beroep, van koerier tot installateur. "
                           "Bekijk de risico's en dekking voor jouw vak.",
    },
    {
        "name": "hub_regio", "prefix": "regio", "path": "regio/",
        "nav_group": "Kennisbank", "nav_label": "Per regio", "kort": True,
        "eyebrow": "Per regio",
        "titel": "Bestelautoverzekering per regio",
        "intro": "Premie en risico verschillen per regio en stad. Bekijk wat dat voor "
                 "jouw bestelauto betekent.",
        "seo_title": "Bestelautoverzekering per regio & stad | Bestelautoverzekering.nl",
        "seo_description": "Wat kost een bestelautoverzekering in jouw regio? Premie en "
                           "risico per stad, helder uitgelegd.",
    },
    {
        "name": "hub_schade", "prefix": "schade", "path": "schade/",
        "nav_group": "Kennisbank", "nav_label": "Schade", "kort": True,
        "eyebrow": "Schade",
        "titel": "Schade aan je bestelauto",
        "intro": "Ruitschade, diefstal, total loss of inbraak, lees per schadesoort "
                 "wat gedekt is en hoe je het meldt.",
        "seo_title": "Schade aan je bestelauto: dekking & melden | Bestelautoverzekering.nl",
        "seo_description": "Per schadesoort: wat is gedekt en hoe meld je het? Ruitschade, "
                           "diefstal, total loss en meer.",
    },
    {
        "name": "hub_vergelijking", "prefix": "vergelijking", "path": "vergelijking/",
        "nav_group": "Kennisbank", "nav_label": "Vergelijkingen",
        "eyebrow": "Vergelijkingen",
        "titel": "Verzekeraars vergelijken",
        "intro": "Twee verzekeraars naast elkaar: dekking, premie en voorwaarden. "
                 "Zie welke beter past bij jouw bestelauto.",
        "seo_title": "Bestelautoverzekeraars vergelijken | Bestelautoverzekering.nl",
        "seo_description": "Verzekeraars één-op-één vergeleken op dekking, premie en "
                           "voorwaarden voor je bestelauto.",
    },
]

HUBS_BY_NAME = {h["name"]: h for h in HUBS}


def hub_children(prefix):
    """Published ContentPagina items under a slug-prefix, in import order."""
    from .models import ContentPagina
    return ContentPagina.objects.filter(
        slug__startswith=f"{prefix}/", published=True).order_by("titel")
