"""Core URL patterns — generated from the PAGES registry (single source of truth)."""

from django.urls import path

from . import views, views_premie
from .hubs import HUBS

urlpatterns = [
    path(page.path, views.make_view(page), name=page.name)
    for page in views.PAGES
]

# Premie-tool: the SSR wizard page + its JSON proxy endpoints (call RISK
# server-side). Explicit paths, so they win over the catch-all below.
urlpatterns += [
    path("bestelautoverzekering-berekenen/", views_premie.tool_page, name="premie_tool"),
    path("premie/api/voertuig", views_premie.vehicle, name="premie_voertuig"),
    path("premie/api/bereken", views_premie.calculate, name="premie_bereken"),
    path("premie/api/aanvullend", views_premie.additional, name="premie_aanvullend"),
    path("premie/api/aanvraag", views_premie.aanvraag, name="premie_aanvraag"),
]

# Content-hub overview pages (per content-type listings).
urlpatterns += [
    path(hub["path"], views.make_hub_view(hub), name=hub["name"])
    for hub in HUBS
]

# Catch-all for imported content-fabriek pages — MUST stay last so the explicit
# pages and hubs above (and admin/sitemap/robots/media in config.urls) win first.
urlpatterns += [
    path("<path:slug>/", views.content_pagina, name="content_pagina"),
]
