"""
Content hubs: per-content-type overview pages that list the imported
ContentPagina items by slug-prefix. Single source of truth — add a hub here and
it gets a route (core.urls), a nav entry (context_processors), and a sitemap
entry. Only prefixes WITHOUT an existing design page live here; verzekeraars and
dekkingen are woven into their existing overview pages instead.
"""

# Leeg voor Motorverzekering.nl: de bestelauto-hubs (per beroep/merk/regio/schade/
# vergelijking) zijn verwijderd. Een eventuele motor-hub kan hier later toegevoegd
# worden; dan komen route (core.urls) + sitemap (core.sitemaps) automatisch mee.
HUBS = []

HUBS_BY_NAME = {h["name"]: h for h in HUBS}


def hub_children(prefix):
    """Published ContentPagina items under a slug-prefix, in import order."""
    from .models import ContentPagina
    return ContentPagina.objects.filter(
        slug__startswith=f"{prefix}/", published=True).order_by("titel")
