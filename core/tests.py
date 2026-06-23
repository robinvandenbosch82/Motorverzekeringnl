"""
Tests for Motorverzekering.nl.

Covers the invariants that matter for a content/SEO site: every registered
page renders, carries correct & unique SEO metadata, includes the shared
chrome, and is discoverable via sitemap/robots. Data-driven from the PAGES
registry so new pages are covered automatically.
"""

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.utils.html import escape

from core.models import BlogArtikel, ContentPagina, Expert, Page, Review, SiteSettings
from core.views import PAGES


class PageRenderTests(TestCase):
    def test_all_pages_return_200(self):
        for page in PAGES:
            with self.subTest(page=page.name):
                resp = self.client.get(reverse(page.name))
                self.assertEqual(resp.status_code, 200)

    def test_pages_have_expected_seo_metadata(self):
        for page in PAGES:
            with self.subTest(page=page.name):
                html = self.client.get(reverse(page.name)).content.decode()
                # Titles/descriptions are HTML-escaped by the template engine.
                self.assertIn(f"<title>{escape(page.title)}</title>", html)
                self.assertIn(escape(page.description), html)
                self.assertIn('rel="canonical"', html)
                self.assertIn('property="og:title"', html)

    def test_titles_and_descriptions_are_unique(self):
        titles = [p.title for p in PAGES]
        descriptions = [p.description for p in PAGES]
        self.assertEqual(len(titles), len(set(titles)), "Duplicate <title> across pages")
        self.assertEqual(len(descriptions), len(set(descriptions)), "Duplicate meta descriptions")

    def test_pages_include_shared_chrome_and_structured_data(self):
        for page in PAGES:
            with self.subTest(page=page.name):
                html = self.client.get(reverse(page.name)).content.decode()
                self.assertIn("data-site-nav", html)
                self.assertIn("data-site-footer", html)
                self.assertIn("application/ld+json", html)

    def test_every_page_funnels_to_premie_tool(self):
        # Every page must funnel to the premie-tool — via the shared PremieWidget
        # band (legacy bestelauto pages) or the MV nav/CTA (redesigned pages).
        tool = reverse("premie_tool")
        for page in PAGES:
            with self.subTest(page=page.name):
                html = self.client.get(reverse(page.name)).content.decode()
                self.assertIn(tool, html)


class DiscoverabilityTests(TestCase):
    def test_sitemap_lists_every_page(self):
        xml = self.client.get("/sitemap.xml").content.decode()
        self.assertEqual(self.client.get("/sitemap.xml").status_code, 200)
        for page in PAGES:
            self.assertIn(reverse(page.name), xml)

    def test_robots_txt_points_to_sitemap_and_blocks_admin(self):
        resp = self.client.get("/robots.txt")
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        self.assertIn("Sitemap:", body)
        self.assertIn("Disallow: /admin/", body)


class CmsTests(TestCase):
    """The admin (DB) is the source of truth — edits must reach the page."""

    def test_page_seo_override_wins_over_registry_default(self):
        Page.objects.create(
            key="dekkingen", label="Dekkingen",
            seo_title="AANGEPASTE TITEL VIA ADMIN",
            seo_description="aangepaste omschrijving via admin")
        html = self.client.get(reverse("dekkingen")).content.decode()
        self.assertIn("AANGEPASTE TITEL VIA ADMIN", html)
        self.assertIn("aangepaste omschrijving via admin", html)

    def test_page_noindex_flag_sets_robots_meta(self):
        Page.objects.create(key="blog", label="Blog", noindex=True)
        html = self.client.get(reverse("blog")).content.decode()
        self.assertIn("noindex, follow", html)

    def test_page_hero_override_renders(self):
        Page.objects.create(key="dekkingen", label="V",
                            heading="MIJN EIGEN H1", intro="Mijn eigen introtekst.")
        html = self.client.get(reverse("dekkingen")).content.decode()
        self.assertIn("MIJN EIGEN H1", html)
        self.assertIn("Mijn eigen introtekst.", html)

    def test_sitesettings_value_reflects_on_page(self):
        s = SiteSettings.load()
        s.review_score = "8,7"
        s.afm_nummer = "99999999"
        s.save()
        html = self.client.get(reverse("home")).content.decode()
        self.assertIn("8,7", html)
        self.assertIn("99999999", html)

    def test_homepage_reviews_come_from_db(self):
        Review.objects.create(name="Testpersoon Janssen", role="Tester",
                              quote="Dit is een testreview uit de database.", order=0)
        html = self.client.get(reverse("home")).content.decode()
        self.assertIn("Testpersoon Janssen", html)
        self.assertIn("Dit is een testreview uit de database.", html)

    def test_admin_is_reachable(self):
        resp = self.client.get("/admin/")
        self.assertIn(resp.status_code, (200, 302))  # redirects to login


class ImageRenderingTests(TestCase):
    """Images must render as crawlable/accessible <img> with alt — never as a
    CSS background-image (no alt, not indexable, bad LCP)."""

    def test_blog_detail_uses_img_with_alt_not_background_image(self):
        from core.models import BlogArtikel
        art = BlogArtikel.objects.create(
            titel="Testartikel met beeld", categorie="Premie", excerpt="x",
            body_html="<p>Body.</p>", photo_url="img/motor/moto-11890953.jpg")
        html = self.client.get(art.get_absolute_url()).content.decode()
        self.assertIn("<img ", html, "blog-artikel heeft geen <img>")
        self.assertIn('alt="', html, "blog-artikel heeft geen alt-tekst")
        self.assertNotIn("background-image:url('http", html,
                         "blog-artikel gebruikt nog een CSS background-image i.p.v. <img>")

    def test_db_driven_blog_image_renders_as_img_with_alt(self):
        # The blog overview is driven by the BlogArtikel model (admin = source).
        from core.models import BlogArtikel
        BlogArtikel.objects.create(
            titel="Test motor artikel", categorie="Onderhoud", excerpt="Een testartikel.",
            photo_url="img/motor/moto-11890953.jpg")
        html = self.client.get(reverse("blog")).content.decode()
        self.assertIn("Test motor artikel", html)
        self.assertIn("<img ", html)
        self.assertIn('alt="Test motor artikel"', html)

    def test_uploaded_photo_alt_falls_back_to_default(self):
        # No explicit alt → get_photo_alt() uses the model's default_photo_alt().
        e = Expert.objects.create(name="Anna Test", role="Adviseur",
                                  bio="x", photo_url="https://img/x.jpg")
        self.assertEqual(e.get_photo_alt(), "Anna Test, Adviseur bij Motorverzekering.nl")


class ContentPaginaTests(TestCase):
    """Imported content-fabriek pages served by the catch-all route."""

    def test_content_page_renders_at_its_slug(self):
        ContentPagina.objects.create(
            slug="verzekeraars/test-verzekeraar", titel="Test Verzekeraar Pagina",
            meta_description="Test omschrijving", intro_html="<p>Intro hier.</p>",
            body_html="<h2 id='kop'>Een kop</h2><p>De bodytekst.</p>")
        resp = self.client.get("/verzekeraars/test-verzekeraar/")
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn("Test Verzekeraar Pagina", html)
        self.assertIn("De bodytekst.", html)
        self.assertIn("Test omschrijving", html)  # meta description

    def test_catchall_does_not_shadow_explicit_pages(self):
        # A ContentPagina with a slug colliding with an explicit route must not win.
        ContentPagina.objects.create(slug="dekkingen", titel="Mag niet winnen")
        resp = self.client.get(reverse("dekkingen"))
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("Mag niet winnen", resp.content.decode())
        self.assertIn("Wat is gedekt per verzekering?", resp.content.decode())  # the design page

    def test_unpublished_page_is_404(self):
        ContentPagina.objects.create(slug="schade/verborgen", titel="Verborgen", published=False)
        self.assertEqual(self.client.get("/schade/verborgen/").status_code, 404)

    def test_unknown_slug_is_404(self):
        self.assertEqual(self.client.get("/dit/bestaat/niet/").status_code, 404)


class TrustpilotTests(TestCase):
    """Trustpilot model/cache still loads. NB: the MV homepage redesign no longer
    surfaces a Trustpilot section or aggregateRating on the homepage — its
    reviews come from the Review model. The fetch command + admin model remain
    for later use (e.g. re-introducing aggregateRating). These tests pin the
    current behaviour: no Trustpilot markup on the home, and the home's JSON-LD
    stays valid."""

    def _seed(self):
        import datetime
        from decimal import Decimal
        from django.utils import timezone
        from core.models import TrustpilotProfile, TrustpilotReview
        p = TrustpilotProfile.load()
        p.trust_score = Decimal("4.6")
        p.stars = Decimal("4.5")
        p.review_count = 2840
        p.save()
        base = timezone.now()
        for i in range(4):
            TrustpilotReview.objects.create(
                external_id=f"tp{i}", author=f"Jan Jansen {i}", rating=5,
                title=f"Titel {i}", text="Snel geregeld en duidelijk.",
                created_at=base - datetime.timedelta(days=i), order=i)

    def test_homepage_has_no_trustpilot_section(self):
        self._seed()
        html = self.client.get(reverse("home")).content.decode()
        self.assertNotIn("Geverifieerd via Trustpilot", html)
        self.assertNotIn("aggregateRating", html)

    def test_homepage_jsonld_still_parses(self):
        import json
        import re
        self._seed()
        html = self.client.get(reverse("home")).content.decode()
        blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        nodes = [json.loads(b) for b in blocks]  # every block must parse
        self.assertTrue(nodes)
        # The homepage emits an Organization graph + a FAQPage.
        types = {n.get("@type") for n in nodes}
        self.assertIn("FAQPage", types)


class SeoTitleBrandingTests(TestCase):
    """ContentPagina (juridische pagina's) krijgen de merknaam in de SERP-title."""

    def test_get_seo_title_appends_brand_when_missing(self):
        cp = ContentPagina(slug="disclaimer", titel="Disclaimer")
        self.assertEqual(cp.get_seo_title(), f"Disclaimer | {settings.SITE_NAME}")

    def test_get_seo_title_does_not_double_brand(self):
        cp = ContentPagina(slug="x", titel="X",
                           meta_title=f"Iets moois | {settings.SITE_NAME}")
        self.assertEqual(cp.get_seo_title(), f"Iets moois | {settings.SITE_NAME}")

    def test_legal_page_renders_branded_title(self):
        ContentPagina.objects.create(slug="disclaimer", titel="Disclaimer",
                                     meta_description="Test.", body_html="<p>x</p>")
        html = self.client.get("/disclaimer/").content.decode()
        self.assertIn(escape(f"Disclaimer | {settings.SITE_NAME}"), html)


class HomePremieFormTests(TestCase):
    """De 'Nog geen kenteken'-tab is verwijderd (RISK kan niet zonder kenteken
    offreren); de premiekaart is puur kenteken-gebaseerd."""

    def test_home_premie_form_is_kenteken_only(self):
        html = self.client.get(reverse("home")).content.decode()
        self.assertIn('name="kenteken"', html)
        self.assertNotIn("Nog geen kenteken", html)
        self.assertNotIn('name="merk"', html)
        self.assertNotIn('name="bouwjaar"', html)


class ErrorPageTests(TestCase):
    """Gebrande 404 (Django gebruikt templates/404.html bij DEBUG=False, ook in
    tests) houdt de bezoeker op de site i.p.v. een kale Django-foutpagina."""

    def test_unknown_url_renders_branded_404(self):
        resp = self.client.get("/deze-pagina-bestaat-echt-niet-xyz/")
        self.assertEqual(resp.status_code, 404)
        html = resp.content.decode()
        self.assertIn("Pagina niet gevonden", html)
        self.assertIn(reverse("premie_tool"), html)  # funnel terug naar de tool
