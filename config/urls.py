"""Root URL configuration for Bestelautoverzekering.nl."""

from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from django.urls import include, path, re_path
from django.views.static import serve as _serve_static

from core.sitemaps import SITEMAPS


def media_serve(request, path, document_root=None):
    """Serve a media file + set a Cache-Control header (Django's static serve
    sets none, which shows up in Lighthouse as 'Cache-TTL: None'). Variants under
    /media/cache/ are immutable (the width is baked into the filename), so they
    get a far-future cache; originals can change, so they get a shorter TTL."""
    response = _serve_static(request, path, document_root=document_root)
    if path.startswith("cache/"):
        response["Cache-Control"] = "public, max-age=31536000, immutable"
    else:
        response["Cache-Control"] = "public, max-age=604800"
    return response


# AI-crawlers die we expliciet welkom heten: de kennisbank, blog en FAQ zijn
# bedoeld om geciteerd te worden in AI Overviews, ChatGPT, Claude en Perplexity.
# NB: een eventuele blokkade kan ook op CDN-niveau staan (Cloudflare AI-bot-
# blocking / Content-Signal: ai-train=no) — die moet je daar uitzetten.
_AI_CRAWLERS = [
    "GPTBot", "OAI-SearchBot", "ChatGPT-User",          # OpenAI
    "ClaudeBot", "anthropic-ai", "Claude-Web",          # Anthropic
    "Google-Extended",                                  # Google (AI Overviews-grounding)
    "PerplexityBot", "Perplexity-User",                 # Perplexity
    "CCBot",                                            # Common Crawl (voedt veel LLM's)
    "Applebot-Extended", "meta-externalagent",          # Apple, Meta
    "Bytespider", "Amazonbot",                          # ByteDance, Amazon
]


def robots_txt(request):
    # Advertise the sitemap on the canonical origin (host-independent), keep
    # crawlers out of the admin + JSON proxy, and expliciet AI-crawlers toestaan.
    origin = settings.SITE_ORIGIN
    disallow = ["Disallow: /admin/", "Disallow: /premie/api/"]
    lines = ["User-agent: *", "Allow: /", *disallow, ""]
    for bot in _AI_CRAWLERS:
        lines += [f"User-agent: {bot}", "Allow: /", *disallow, ""]
    lines += [
        f"Sitemap: {origin}/sitemap.xml",
        f"# LLM-gids: {origin}/llms.txt",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def llms_txt(request):
    """`/llms.txt` — een gestructureerde gids voor LLM's (GEO). Geeft AI-
    assistenten een schone routekaart naar onze kerncontent mét per-pagina
    context, los van HTML/CDN. Volledig live uit de modellen, dus altijd
    actueel: elk nieuw/actief artikel verschijnt automatisch."""
    import re
    from django.urls import reverse
    from core.models import BlogArtikel, KennisbankArtikel, SiteSettings

    s = SiteSettings.load()
    o = settings.SITE_ORIGIN

    def desc(text, limit=180):
        t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text or "")).strip()
        if len(t) > limit:
            t = t[:limit].rsplit(" ", 1)[0].rstrip(".,;:") + "…"
        return t

    out = [
        f"# {settings.SITE_NAME}",
        "",
        "> Onafhankelijk motorverzekeringen vergelijken en direct online afsluiten "
        "(WA, WA+ en Allrisk), zonder tussenpersoon. Nederlandstalig, volledig "
        "server-side gerenderd. Feitelijke, door WFT-experts gecontroleerde content "
        "over dekkingen, premie, schade en regelgeving rond de motorverzekering.",
        "",
        "## Belangrijkste pagina's",
        f"- [Motorverzekering vergelijken]({o}/): home; vergelijk WA, WA+ en Allrisk en bereken je premie met je kenteken.",
        f"- [Premie berekenen]({o}{reverse('premie_tool')}): premies van meerdere verzekeraars vergelijken en direct online afsluiten.",
        f"- [Dekkingen]({o}{reverse('dekkingen')}): wat WA, WA+ en Allrisk dekken, plus aanvullende dekkingen (pechhulp, opzittenden, rechtsbijstand, vervangend vervoer).",
        f"- [Kennisbank]({o}{reverse('kennisbank')}): veelgestelde vragen over de motorverzekering, feitelijk beantwoord.",
        f"- [Blog]({o}{reverse('blog')}): uitleg en achtergrond over verzekeren, premie, schade en regelgeving voor motorrijders.",
        f"- [Klantenservice]({o}{reverse('klantenservice')}): contact, openingstijden en hulp.",
        "",
        "## Kennisbank",
    ]
    for a in KennisbankArtikel.objects.filter(active=True).order_by("order"):
        d = desc(a.kort_antwoord or a.excerpt)
        out.append(f"- [{a.titel}]({o}{a.get_absolute_url()})" + (f": {d}" if d else ""))
    out += ["", "## Blog"]
    for b in BlogArtikel.objects.filter(active=True).order_by("order"):
        d = desc(b.excerpt)
        out.append(f"- [{b.titel}]({o}{b.get_absolute_url()})" + (f": {d}" if d else ""))
    out += [
        "",
        "## Over Motorverzekering.nl",
        f"- Handelsnaam van {s.legal_naam}, gevestigd aan {s.adres_straat}, {s.adres_postcode} {s.adres_plaats}.",
        f"- AFM-vergunning {s.afm_nummer}; ingeschreven bij de KvK onder {s.kvk_nummer}.",
        "- Execution only: een vergelijkingsplatform en bemiddelaar, geen verzekeraar. Je sluit zelf online af, zonder persoonlijk advies.",
        "- Onafhankelijk en zonder tussenpersoon. Content is geschreven door verzekeringsexperts en gecontroleerd door WFT-gecertificeerde adviseurs.",
        "",
    ]
    return HttpResponse("\n".join(out), content_type="text/plain; charset=utf-8")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS},
         name="django.contrib.sitemaps.views.sitemap"),
    path("robots.txt", robots_txt, name="robots_txt"),
    path("llms.txt", llms_txt, name="llms_txt"),
]

# Serve uploaded/generated media directly from Django, in dev AND production —
# BEFORE the core catch-all so /media/ is never shadowed by the content-page
# route. WhiteNoise only serves /static/, and the image pipeline writes WebP/JPEG
# variants to disk at runtime, so serving must be dynamic (per-request disk read)
# rather than a startup scan. On a single instance with a persistent volume this
# is fine; front it with object storage + a CDN if traffic ever warrants it.
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", media_serve, {"document_root": settings.MEDIA_ROOT}),
]

urlpatterns += [path("", include("core.urls"))]
