"""
XML sitemap for Google Search Console.

Three sections, all forced onto the canonical production domain (SITE_ORIGIN)
and https — so the URLs are identical to the page canonicals regardless of how
the sitemap is fetched (www/non-www/dev host):

  * pages   — the design/landing pages from the PAGES registry + the premie tool,
              with admin-editable <lastmod>; noindex pages are excluded.
  * hubs    — the per-content-type overview pages.
  * content — every published ContentPagina (imported knowledge base).

Reachable at /sitemap.xml and advertised in robots.txt.
"""
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .views import PAGES


class _CanonicalSitemap(Sitemap):
    """Base that pins every URL to SITE_ORIGIN's host + https, instead of the
    request host. Keeps sitemap URLs equal to the on-page rel=canonical."""
    protocol = "https"

    def get_urls(self, page=1, site=None, protocol=None):
        host = urlparse(settings.SITE_ORIGIN).netloc

        class _Site:
            domain = host
            name = host

        return super().get_urls(page=page, site=_Site(), protocol=self.protocol)


class PageSitemap(_CanonicalSitemap):
    def __init__(self):
        # Cross-reference the editable Page model for <lastmod> and noindex.
        from .models import Page as PageModel
        try:
            rows = PageModel.objects.values_list("key", "updated_at", "noindex")
            self._lastmods = {k: u for k, u, _ in rows}
            self._noindex = {k for k, _, n in rows if n}
        except Exception:
            self._lastmods, self._noindex = {}, set()

    def items(self):
        # Never advertise a page we tell Google not to index.
        return [p for p in PAGES if p.name not in self._noindex]

    def location(self, page):
        return reverse(page.name)

    def priority(self, page):
        return page.sitemap_priority

    def changefreq(self, page):
        return page.sitemap_changefreq

    def lastmod(self, page):
        return self._lastmods.get(page.name)


class ExtraSitemap(_CanonicalSitemap):
    """Indexable routes that live outside the PAGES registry (the premie wizard
    is a key conversion page registered directly in core.urls)."""
    changefreq = "monthly"
    priority = 0.8

    def items(self):
        return ["premie_tool"]

    def location(self, name):
        return reverse(name)


class ContentPaginaSitemap(_CanonicalSitemap):
    changefreq = "monthly"
    priority = 0.6
    limit = 5000  # well under the 50k cap; future-proofs paging

    def items(self):
        from .models import ContentPagina
        return ContentPagina.objects.filter(published=True).order_by("slug")

    def location(self, obj):
        return obj.get_absolute_url()

    def lastmod(self, obj):
        return obj.imported_at


class KennisbankSitemap(_CanonicalSitemap):
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        from .models import KennisbankArtikel
        return KennisbankArtikel.objects.filter(active=True).order_by("order")

    def location(self, obj):
        return obj.get_absolute_url()


class BlogSitemap(_CanonicalSitemap):
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        from .models import BlogArtikel
        return BlogArtikel.objects.filter(active=True).order_by("order")

    def location(self, obj):
        return obj.get_absolute_url()


SITEMAPS = {
    "pages": PageSitemap,
    "extra": ExtraSitemap,
    "content": ContentPaginaSitemap,
    "kennisbank": KennisbankSitemap,
    "blog": BlogSitemap,
}
