"""
Tests for Bestelautoverzekering.nl.

Covers the invariants that matter for a content/SEO site: every registered
page renders, carries correct & unique SEO metadata, includes the shared
chrome, and is discoverable via sitemap/robots. Data-driven from the PAGES
registry so new pages are covered automatically.
"""

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

    def test_content_pages_include_premie_widget_band(self):
        # The homepage embeds the calculator in the hero and suppresses the
        # band; every other page must carry the shared PremieWidget band.
        for page in PAGES:
            if page.name == "home":
                continue
            with self.subTest(page=page.name):
                html = self.client.get(reverse(page.name)).content.decode()
                self.assertIn("data-premie-widget", html)


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
        Page.objects.create(key="verzekeraars", label="V",
                            heading="MIJN EIGEN H1", intro="Mijn eigen introtekst.")
        html = self.client.get(reverse("verzekeraars")).content.decode()
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

    DETAIL_PAGES = [
        "blog_artikel", "kennisbank_artikel", "situatie_gereedschap",
        "beroep_timmerman", "dekkingen", "verzekeraar_asr",
    ]

    def test_detail_pages_use_img_with_alt_not_background_image(self):
        for name in self.DETAIL_PAGES:
            with self.subTest(page=name):
                html = self.client.get(reverse(name)).content.decode()
                self.assertIn("<img ", html, f"{name} heeft geen <img>")
                self.assertIn('alt="', html, f"{name} heeft geen alt-tekst")
                self.assertNotIn(
                    "background-image:url('http", html,
                    f"{name} gebruikt nog een CSS background-image i.p.v. <img>")

    def test_db_driven_blog_image_renders_as_img_with_alt(self):
        # The blog overview is driven by imported 'blog' ContentPagina entries.
        ContentPagina.objects.create(
            slug="test-ev-bus-artikel", titel="Test EV-bus artikel", contenttype="blog",
            published=True, image_url="https://images.example.com/ev.jpg",
            image_alt="Een elektrische bestelbus")
        html = self.client.get(reverse("blog")).content.decode()
        self.assertIn('<img src="https://images.example.com/ev.jpg"', html)
        self.assertIn('alt="Een elektrische bestelbus"', html)

    def test_uploaded_photo_alt_falls_back_to_default(self):
        # No explicit alt → get_photo_alt() uses the model's default_photo_alt().
        e = Expert.objects.create(name="Anna Test", role="Adviseur",
                                  bio="x", photo_url="https://img/x.jpg")
        self.assertEqual(e.get_photo_alt(), "Anna Test, Adviseur bij Bestelautoverzekering.nl")


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
        self.assertIn("data-premie-widget", resp.content.decode())  # the design page

    def test_unpublished_page_is_404(self):
        ContentPagina.objects.create(slug="schade/verborgen", titel="Verborgen", published=False)
        self.assertEqual(self.client.get("/schade/verborgen/").status_code, 404)

    def test_unknown_slug_is_404(self):
        self.assertEqual(self.client.get("/dit/bestaat/niet/").status_code, 404)


class TrustpilotTests(TestCase):
    """The homepage shows the cached Trustpilot score + reviews, and emits a
    matching aggregateRating/Review graph — only when data has been fetched."""

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

    def test_without_data_falls_back(self):
        html = self.client.get(reverse("home")).content.decode()
        self.assertNotIn("Geverifieerd via Trustpilot", html)
        self.assertNotIn("aggregateRating", html)

    def test_with_data_renders_reviews_and_jsonld(self):
        import json
        import re
        self._seed()
        html = self.client.get(reverse("home")).content.decode()
        # Visible cards
        self.assertIn("Geverifieerd via Trustpilot", html)
        self.assertIn("Jan Jansen 0", html)
        # Every JSON-LD block parses
        blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        nodes = [json.loads(b) for b in blocks]
        # aggregateRating on the org node with 4 reviews
        org = next(n for n in nodes if n.get("@type") == "Organization" and "aggregateRating" in n)
        self.assertEqual(org["aggregateRating"]["ratingValue"], "4.6")
        self.assertEqual(org["aggregateRating"]["ratingCount"], "2840")
        self.assertEqual(len(org["review"]), 4)
        self.assertEqual(org["review"][0]["reviewRating"]["bestRating"], "5")
