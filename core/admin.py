"""
Django admin for the Bestelautoverzekering.nl CMS.

Goal: every page is visible and per-page content is editable here. Pages are
synced from the routing registry (see `sync_pages`), so the page list always
matches the live site; editors fill in SEO + copy, and manage the shared
content models (FAQ, reviews, experts, insurers, coverage tiers, situations,
professions, blog & knowledge-base articles).
"""

from django.contrib import admin

from .admin_mixins import PexelsPhotoMixin
from .models import (
    Berekening,
    Beroep,
    BlogArtikel,
    ContentPagina,
    DekkingFeature,
    Dekkingstier,
    Expert,
    Faq,
    KennisbankArtikel,
    KennisbankCategorie,
    MenuItem,
    Page,
    Review,
    Situatie,
    SiteSettings,
    TrustpilotProfile,
    TrustpilotReview,
    Verzekeraar,
)

admin.site.site_header = "Bestelautoverzekering.nl — beheer"
admin.site.site_title = "Bestelautoverzekering.nl"
admin.site.index_title = "Content & instellingen"


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Vertrouwen & cijfers", {"fields": ("review_score", "review_count",
                                             "ondernemers_verzekerd", "verzekeraars_label")}),
        ("Contact", {"fields": ("phone", "whatsapp", "email")}),
        ("Bedrijfsgegevens", {"fields": ("afm_nummer", "kvk_nummer")}),
        ("Vestigingsadres (optioneel, voor LocalBusiness-schema)",
         {"fields": ("adres_straat", "adres_postcode", "adres_plaats"),
          "classes": ("collapse",)}),
        ("Footer", {"fields": ("footer_blurb",)}),
        ("Merk & structured data (logo + social)",
         {"fields": ("logo", "sameas", "default_og_image")}),
        ("Integraties", {"fields": ("pexels_api_key",)}),
    )

    def has_add_permission(self, request):
        # Singleton: only one row allowed.
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("label", "key", "path", "noindex", "updated_at")
    list_filter = ("noindex",)
    search_fields = ("label", "key", "seo_title", "seo_description")
    readonly_fields = ("key", "path", "updated_at")
    fieldsets = (
        (None, {"fields": ("label", "key", "path", "updated_at")}),
        ("SEO", {"fields": ("seo_title", "seo_description", "og_image", "noindex")}),
        ("Hero / introtekst (waar de pagina dit ondersteunt)",
         {"fields": ("eyebrow", "heading", "intro"), "classes": ("collapse",)}),
        ("Byline (voor artikel-pagina's: blog, kennisbank, verzekeraar)",
         {"fields": ("author", "reviewer", "byline_date", "leestijd"),
          "classes": ("collapse",)}),
    )
    autocomplete_fields = ("author", "reviewer")

    def has_add_permission(self, request):
        # Pages are created by the sync_pages command, not by hand.
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Faq)
class FaqAdmin(admin.ModelAdmin):
    list_display = ("question", "page_key", "order", "active")
    list_filter = ("page_key", "active")
    list_editable = ("order", "active")
    search_fields = ("question", "answer")


@admin.register(Review)
class ReviewAdmin(PexelsPhotoMixin, admin.ModelAdmin):
    list_display = ("name", "role", "order", "active")
    list_editable = ("order", "active")
    search_fields = ("name", "role", "quote")
    readonly_fields = ("pexels_widget",)
    pexels_download_subdir = "photos/reviews"
    pexels_filename_prefix = "review"


@admin.register(Expert)
class ExpertAdmin(PexelsPhotoMixin, admin.ModelAdmin):
    list_display = ("name", "role", "order", "active")
    list_editable = ("order", "active")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "role", "bio")
    readonly_fields = ("pexels_widget",)
    pexels_download_subdir = "photos/experts"
    pexels_filename_prefix = "expert"


class DekkingFeatureInline(admin.TabularInline):
    model = DekkingFeature
    extra = 1


@admin.register(Dekkingstier)
class DekkingstierAdmin(admin.ModelAdmin):
    list_display = ("code", "naam", "prijs", "highlight", "order")
    list_editable = ("prijs", "highlight", "order")
    inlines = [DekkingFeatureInline]


@admin.register(Situatie)
class SituatieAdmin(PexelsPhotoMixin, admin.ModelAdmin):
    list_display = ("titel", "link", "featured", "order", "active")
    list_editable = ("link", "featured", "order", "active")
    search_fields = ("titel", "omschrijving")
    readonly_fields = ("pexels_widget",)
    pexels_download_subdir = "photos/situaties"
    pexels_filename_prefix = "situatie"


@admin.register(Beroep)
class BeroepAdmin(admin.ModelAdmin):
    list_display = ("naam", "premie_vanaf", "order", "active")
    list_editable = ("premie_vanaf", "order", "active")
    search_fields = ("naam",)


@admin.register(Verzekeraar)
class VerzekeraarAdmin(PexelsPhotoMixin, admin.ModelAdmin):
    list_display = ("naam", "score", "premie_vanaf", "order", "active")
    list_editable = ("score", "premie_vanaf", "order", "active")
    prepopulated_fields = {"slug": ("naam",)}
    search_fields = ("naam", "tags")
    readonly_fields = ("pexels_widget",)
    pexels_download_subdir = "photos/verzekeraars"
    pexels_filename_prefix = "logo"
    fieldsets = (
        (None, {"fields": ("naam", "slug", "score", "premie_vanaf", "tags", "order", "active")}),
        ("Logo", {"classes": ("collapse",),
                  "fields": ("pexels_widget", "photo_upload", "photo_url", "photo_local",
                             "photo_credit", "photo_pexels_id", "photo_alt")}),
        ("Omschrijving & reviews (vergelijker)", {"fields": ("omschrijving", "review_count")}),
        ("Beoordeling — uitsplitsing (vergelijker)",
         {"fields": ("score_tevredenheid", "score_klantgerichtheid", "score_deskundigheid",
                     "score_duidelijkheid", "score_vertrouwen", "score_prijs_kwaliteit", "score_contact")}),
        ("Kenmerken (vergelijker)",
         {"fields": ("telefonisch_contact", "dagelijks_opzegbaar", "aanschafwaarde",
                     "eenmalige_poliskosten", "type_polis", "bijzonderheden")}),
    )


@admin.register(BlogArtikel)
class BlogArtikelAdmin(PexelsPhotoMixin, admin.ModelAdmin):
    list_display = ("titel", "categorie", "author", "datum", "featured", "order", "active")
    list_editable = ("featured", "order", "active")
    prepopulated_fields = {"slug": ("titel",)}
    search_fields = ("titel", "excerpt")
    autocomplete_fields = ("author",)
    readonly_fields = ("pexels_widget",)
    pexels_download_subdir = "photos/blog"
    pexels_filename_prefix = "blog"


@admin.register(ContentPagina)
class ContentPaginaAdmin(admin.ModelAdmin):
    list_display = ("titel", "contenttype", "slug", "published", "imported_at")
    list_filter = ("contenttype", "published", "gate_status")
    list_editable = ("published",)
    search_fields = ("titel", "slug", "focus_keyword", "meta_description")
    readonly_fields = ("imported_at",)
    fieldsets = (
        (None, {"fields": ("titel", "slug", "contenttype", "published", "imported_at")}),
        ("SEO", {"fields": ("meta_title", "meta_description", "focus_keyword", "zoekintentie")}),
        ("Afbeelding", {"fields": ("image_url", "image_alt", "image_credit", "image_credit_url")}),
        ("Inhoud (HTML)", {"fields": ("intro_html", "body_html", "faq_html", "conclusie_html",
                                      "cta_html", "interne_links_html")}),
        ("Geavanceerd", {"classes": ("collapse",),
                         "fields": ("toc", "schema_jsonld", "bronnen", "gate_status")}),
    )


@admin.register(KennisbankCategorie)
class KennisbankCategorieAdmin(admin.ModelAdmin):
    list_display = ("naam", "aantal", "link", "order")
    list_editable = ("aantal", "link", "order")


@admin.register(KennisbankArtikel)
class KennisbankArtikelAdmin(PexelsPhotoMixin, admin.ModelAdmin):
    list_display = ("titel", "categorie", "order", "active")
    list_editable = ("order", "active")
    prepopulated_fields = {"slug": ("titel",)}
    search_fields = ("titel", "excerpt")
    readonly_fields = ("pexels_widget",)
    pexels_download_subdir = "photos/kennisbank"
    pexels_filename_prefix = "kb"


@admin.register(Berekening)
class BerekeningAdmin(admin.ModelAdmin):
    """Read-only log of premie-tool sessions. Insight only — rows are written by
    the tool, not edited by hand. Contains personal data (kenteken, KvK, NAW):
    keep a bewaartermijn and a clear AVG-grondslag; do not export casually."""
    list_display = ("license_plate", "status", "coverage", "is_van",
                    "policy_number", "created_at", "updated_at")
    list_filter = ("status", "is_van", "coverage", "created_at")
    search_fields = ("license_plate", "policy_number", "session_id")
    date_hierarchy = "created_at"
    readonly_fields = ("session_id", "license_plate", "is_van", "coverage",
                       "vehicle_info", "business_details", "results", "selected_result",
                       "additional_coverages", "request_data", "policy_number",
                       "status", "current_step", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False  # view-only


class MenuChildInline(admin.TabularInline):
    model = MenuItem
    fk_name = "parent"
    extra = 1
    fields = ("label", "url", "order", "active")
    verbose_name = "Sub-item / link"
    verbose_name_plural = "Sub-items / links onder dit item"


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("label", "menu", "parent", "url", "order", "active")
    list_filter = ("menu", "active")
    list_editable = ("url", "order", "active")
    search_fields = ("label", "url")
    inlines = [MenuChildInline]

    def get_queryset(self, request):
        # Show only top-level rows in the list; children are managed inline.
        return super().get_queryset(request).filter(parent__isnull=True)


# ── Trustpilot (weekly API fetch; admin = read-mostly + manual fallback) ─────
@admin.register(TrustpilotProfile)
class TrustpilotProfileAdmin(admin.ModelAdmin):
    list_display = ("domain", "trust_score", "review_count", "last_fetched")
    readonly_fields = ("business_unit_id", "last_fetched")
    fieldsets = (
        ("Bron", {"fields": ("domain", "profile_url", "business_unit_id")}),
        ("Cijfers (wekelijks opgehaald, handmatig te overschrijven)",
         {"fields": ("trust_score", "stars", "review_count", "last_fetched")}),
    )

    def has_add_permission(self, request):
        return not TrustpilotProfile.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TrustpilotReview)
class TrustpilotReviewAdmin(admin.ModelAdmin):
    list_display = ("author", "rating", "title", "created_at", "order")
    list_editable = ("order",)
    list_filter = ("rating",)
    search_fields = ("author", "title", "text")
    readonly_fields = ("external_id", "fetched_at")
