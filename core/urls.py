"""Core URL patterns — generated from the PAGES registry (single source of truth)."""

from django.urls import path

from . import views, views_premie

urlpatterns = [
    path(page.path, views.make_view(page), name=page.name)
    for page in views.PAGES
]

# Premie-tool: the SSR wizard page + its JSON proxy endpoints (call RISK
# server-side). Explicit paths, so they win over the catch-all below.
urlpatterns += [
    path("motorverzekering-berekenen/", views_premie.tool_page, name="premie_tool"),
    path("premie/api/voertuig", views_premie.vehicle, name="premie_voertuig"),
    path("premie/api/bereken", views_premie.calculate, name="premie_bereken"),
    path("premie/api/aanvullend", views_premie.additional, name="premie_aanvullend"),
    path("premie/api/aanvraag", views_premie.aanvraag, name="premie_aanvraag"),
]

# Kennisbank- en blog-artikelen (één pagina per stuk, slug-based). Vóór de catch-all.
urlpatterns += [
    path("kennisbank/<slug:slug>/", views.kennisbank_artikel, name="kennisbank_artikel"),
    path("blog/<slug:slug>/", views.blog_artikel, name="blog_artikel"),
]

# Catch-all for imported content-fabriek pages — MUST stay last so the explicit
# pages above (and admin/sitemap/robots/media in config.urls) win first.
urlpatterns += [
    path("<path:slug>/", views.content_pagina, name="content_pagina"),
]
