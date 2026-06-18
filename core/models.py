"""
CMS data models for Bestelautoverzekering.nl.

Design decision (2026-06-16, with Robin): a *structured* CMS where the Django
admin is the source of truth. Mirrors the cruises.nl pattern (SiteSettings +
per-page copy + dedicated content models).

- SiteSettings  — one editable row of global brand/contact/trust values.
- Page          — one row per route (synced from the PAGES registry), holding
                  per-page SEO + hero copy. Makes every page editable in admin.
- Content models — the repeatable/rich content (FAQ, reviews, experts,
                  insurers, coverage tiers, situations, professions, blog &
                  knowledge-base articles).

Templates read from these models with a fallback to the seeded defaults, so the
site renders identically before and after editing.
"""

from django.conf import settings
from django.db import models
from django.utils.text import slugify


def _photo_upload_to(instance, filename):
    """Per-model upload subdir, e.g. photos/verzekeraar/<file>."""
    return f"photos/{instance._meta.model_name}/{filename}"


class PhotoMixin(models.Model):
    """
    Reusable image block + resolver, ported 1-on-1 from the sibling sites
    (cruises.nl / vliegtickets). Lets an editor upload a photo, paste an
    external URL, or pick one via the admin Pexels-widget (which fills
    photo_url/photo_local/credit/pexels_id). get_photo_url() resolves the best
    available source: upload > locally-downloaded file > external URL.
    """
    photo_upload = models.ImageField("Foto uploaden", upload_to=_photo_upload_to, blank=True, null=True)
    photo_url = models.URLField("Foto URL (extern)", max_length=500, blank=True)
    photo_local = models.CharField("Foto lokaal pad", max_length=300, blank=True,
                                   help_text="Wordt automatisch ingevuld door de Pexels-widget.")
    photo_credit = models.CharField("Fotocredit", max_length=200, blank=True)
    photo_pexels_id = models.CharField("Pexels foto-ID", max_length=20, blank=True)
    photo_alt = models.CharField("Alt-tekst", max_length=300, blank=True,
                                 help_text="Beschrijf de foto voor SEO en screenreaders.")

    class Meta:
        abstract = True

    def get_photo_url(self):
        if self.photo_upload:
            return self.photo_upload.url
        if self.photo_local:
            return settings.MEDIA_URL + self.photo_local
        return self.photo_url

    def get_photo_source(self):
        """The value to pass to {% picture %}: local path (pipeline) or URL."""
        if self.photo_upload:
            return self.photo_upload.name
        return self.photo_local or self.photo_url

    def get_photo_alt(self):
        return self.photo_alt or self.default_photo_alt()

    def default_photo_alt(self):
        return str(self)


# ── Global settings (singleton) ────────────────────────────────────────────
class SiteSettings(models.Model):
    review_score = models.CharField("Reviewscore", max_length=10, default="9,1")
    review_count = models.CharField("Aantal reviews", max_length=20, default="2.840")
    ondernemers_verzekerd = models.PositiveIntegerField("Ondernemers verzekerd", default=18742)
    verzekeraars_label = models.CharField("Verzekeraars (label)", max_length=20, default="12+")

    phone = models.CharField("Telefoon", max_length=40, blank=True, default="")
    show_phone = models.BooleanField("Telefoonnummer tonen", default=False,
                                     help_text="Uit = nergens een telefoonnummer tonen.")
    whatsapp = models.CharField("WhatsApp-nummer", max_length=40, default="+3197010252701")
    email = models.EmailField("E-mail", default="hallo@bestelautoverzekering.nl")

    afm_nummer = models.CharField("AFM-vergunning", max_length=40, default="12012535")
    kvk_nummer = models.CharField("KvK-nummer", max_length=40, default="34331885")
    btw_nummer = models.CharField("BTW-nummer", max_length=40, default="NL820572937B01")
    kifid_nummer = models.CharField("Kifid-aansluitnummer", max_length=40, default="300.008506")

    footer_blurb = models.TextField(
        "Footer-tekst",
        default="De verzekeringsspecialist voor ondernemers waarvan de bus het bedrijf is. "
                "Onafhankelijk, snel en zonder verzekeraarstaal.",
    )

    pexels_api_key = models.CharField(
        "Pexels API-sleutel", max_length=100, blank=True,
        help_text="Gratis via pexels.com/api, heeft voorrang boven PEXELS_API_KEY in .env.")
    default_og_image = models.ImageField(
        "Standaard deelafbeelding (OG)", upload_to="og/", blank=True, null=True,
        help_text="Gebruikt als een pagina zelf geen OG-afbeelding heeft.")

    # ── Structured-data / Knowledge Graph ──
    logo = models.ImageField(
        "Logo (vierkant, ≥112px)", upload_to="brand/", blank=True, null=True,
        help_text="Gebruikt als Organization-logo in de JSON-LD (verplicht voor "
                  "artikel-rich-results) en in het Google Knowledge Panel.")
    sameas = models.TextField(
        "Social-profielen (sameAs)", blank=True,
        help_text="Eén volledige URL per regel: LinkedIn, Facebook, X, Trustpilot… "
                  "Verschijnen als sameAs in de Organization-graaf.")
    # Optioneel vestigingsadres — alleen ingevuld weergeven (geen lege PostalAddress).
    adres_straat = models.CharField("Vestiging · straat + nr.", max_length=160, blank=True)
    adres_postcode = models.CharField("Vestiging · postcode", max_length=16, blank=True)
    adres_plaats = models.CharField("Vestiging · plaats", max_length=120, blank=True)

    class Meta:
        verbose_name = "Site-instellingen"
        verbose_name_plural = "Site-instellingen"

    def __str__(self):
        return "Site-instellingen"

    def save(self, *args, **kwargs):
        self.pk = 1  # enforce singleton
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    # Alias used by the ported Pexels service.
    @classmethod
    def get(cls):
        return cls.load()

    @property
    def whatsapp_link(self):
        import re
        digits = re.sub(r"\D", "", self.whatsapp or "")
        return f"https://wa.me/{digits}" if digits else ""

    @property
    def sameas_list(self):
        """Social/profile URLs for the Organization.sameAs array (one per line)."""
        return [u.strip() for u in (self.sameas or "").splitlines() if u.strip().startswith("http")]


# ── Per-page record ─────────────────────────────────────────────────────────
class Page(models.Model):
    key = models.SlugField("Pagina-sleutel", max_length=60, unique=True,
                           help_text="Technische sleutel (= URL-naam). Niet wijzigen.")
    label = models.CharField("Naam", max_length=120)
    path = models.CharField("URL-pad", max_length=200, blank=True,
                            help_text="Alleen ter info, wordt door de routing bepaald.")

    seo_title = models.CharField("SEO-titel", max_length=200, blank=True)
    seo_description = models.TextField("SEO-omschrijving", max_length=320, blank=True)
    og_image = models.ImageField("Deelafbeelding (OG)", upload_to="og/", blank=True)
    noindex = models.BooleanField("Uitsluiten van Google (noindex)", default=False)

    # Optional hero copy overrides (used where the template supports it).
    eyebrow = models.CharField("Bovenkop", max_length=120, blank=True)
    heading = models.CharField("Titel (H1)", max_length=200, blank=True)
    intro = models.TextField("Intro", blank=True)

    # Byline (admin = source of truth; shown on article-style pages: blog,
    # kennisbank, verzekeraar). Author/reviewer reference the Expert team so a
    # name change in one place updates every byline. Empty = template fallback.
    author = models.ForeignKey("Expert", verbose_name="Auteur", on_delete=models.SET_NULL,
                               null=True, blank=True, related_name="+")
    reviewer = models.ForeignKey("Expert", verbose_name="Gecontroleerd door", on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name="+")
    byline_date = models.CharField("Datum (weergave)", max_length=40, blank=True,
                                   help_text="bijv. '12 juni 2026'")
    leestijd = models.CharField("Leestijd", max_length=20, blank=True, help_text="bijv. '5 min'")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pagina"
        verbose_name_plural = "Pagina's"
        ordering = ["label"]

    def __str__(self):
        return self.label

    def get_seo_title(self, default=""):
        return self.seo_title or default

    def get_seo_description(self, default=""):
        return self.seo_description or default


# ── Shared / homepage content ───────────────────────────────────────────────
class Faq(models.Model):
    """Veelgestelde vraag. `page_key` groups FAQs per page (e.g. 'home')."""
    page_key = models.SlugField("Pagina", max_length=60, default="home")
    question = models.CharField("Vraag", max_length=255)
    answer = models.TextField("Antwoord")
    order = models.PositiveIntegerField("Volgorde", default=0)
    active = models.BooleanField("Actief", default=True)

    class Meta:
        verbose_name = "FAQ-item"
        verbose_name_plural = "FAQ-items"
        ordering = ["page_key", "order"]

    def __str__(self):
        return self.question


class Review(PhotoMixin):
    name = models.CharField("Naam", max_length=120)
    role = models.CharField("Functie / voertuig", max_length=160)
    quote = models.TextField("Review")
    order = models.PositiveIntegerField("Volgorde", default=0)
    active = models.BooleanField("Actief", default=True)

    class Meta:
        verbose_name = "Review"
        verbose_name_plural = "Reviews"
        ordering = ["order"]

    def __str__(self):
        return f"{self.name}, {self.role}"

    def default_photo_alt(self):
        return f"Foto van {self.name}, {self.role}"


class Expert(PhotoMixin):
    name = models.CharField("Naam", max_length=120)
    slug = models.SlugField("Slug", max_length=140, unique=True, blank=True,
                            help_text="Voor het Person-@id in de JSON-LD. Leeg = automatisch uit de naam.")
    role = models.CharField("Functie", max_length=160)
    bio = models.TextField("Bio")
    tags = models.CharField("Diploma's / tags", max_length=255, blank=True,
                            help_text="Komma-gescheiden, bijv. 'Wft Schade zakelijk, Wft Basis'.")
    sameas = models.TextField("Profielen (sameAs)", blank=True,
                              help_text="Eén URL per regel (LinkedIn enz.) voor de Person-entiteit / E-E-A-T.")
    order = models.PositiveIntegerField("Volgorde", default=0)
    active = models.BooleanField("Actief", default=True)

    class Meta:
        verbose_name = "Expert"
        verbose_name_plural = "Experts"
        ordering = ["order"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            base = slugify(self.name) or "expert"
            slug, n = base, 2
            while Expert.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def tags_list(self):
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    @property
    def sameas_list(self):
        return [u.strip() for u in (self.sameas or "").splitlines() if u.strip().startswith("http")]

    def person_id(self, origin=""):
        """Stable @id for this expert's Person entity (defined on /over-ons/)."""
        return f"{origin}/over-ons/#person-{self.slug}"

    def default_photo_alt(self):
        return f"{self.name}, {self.role} bij Bestelautoverzekering.nl"


# ── Coverage tiers (WA / WA+ / Allrisk) ─────────────────────────────────────
class Dekkingstier(models.Model):
    code = models.CharField("Code", max_length=20, help_text="WA, WA+, Allrisk")
    naam = models.CharField("Naam", max_length=120)
    prijs = models.CharField("Prijs vanaf (p/mnd)", max_length=20, help_text="Alleen het getal, bijv. 34")
    omschrijving = models.CharField("Korte omschrijving", max_length=255, blank=True)
    highlight = models.BooleanField("Uitgelicht (meest gekozen)", default=False)
    order = models.PositiveIntegerField("Volgorde", default=0)

    class Meta:
        verbose_name = "Dekkingstier"
        verbose_name_plural = "Dekkingstiers"
        ordering = ["order"]

    def __str__(self):
        return f"{self.code}, {self.naam}"


class DekkingFeature(models.Model):
    tier = models.ForeignKey(Dekkingstier, related_name="features", on_delete=models.CASCADE)
    label = models.CharField("Kenmerk", max_length=200)
    included = models.BooleanField("Inbegrepen", default=True)
    order = models.PositiveIntegerField("Volgorde", default=0)

    class Meta:
        verbose_name = "Dekkingskenmerk"
        verbose_name_plural = "Dekkingskenmerken"
        ordering = ["order"]

    def __str__(self):
        return self.label


# ── Situations & professions ────────────────────────────────────────────────
class Situatie(PhotoMixin):
    titel = models.CharField("Titel", max_length=120)
    omschrijving = models.TextField("Omschrijving")
    badge = models.CharField("Badge", max_length=30, blank=True, help_text="bijv. 'POPULAIR'")
    link = models.CharField("Link (pad of URL)", max_length=200, blank=True,
                            help_text="Waar de kaart naartoe gaat, bijv. '/beroep/'. "
                                      "Leeg = naar situaties & beroepen.")
    featured = models.BooleanField("Uitgelicht (grote kaart)", default=False)
    order = models.PositiveIntegerField("Volgorde", default=0)
    active = models.BooleanField("Actief", default=True)

    class Meta:
        verbose_name = "Situatie"
        verbose_name_plural = "Situaties"
        ordering = ["order"]

    def __str__(self):
        return self.titel

    def default_photo_alt(self):
        return f"{self.titel}, bestelautoverzekering"


class Beroep(models.Model):
    naam = models.CharField("Beroep", max_length=120)
    premie_vanaf = models.CharField("Premie vanaf", max_length=20, blank=True)
    omschrijving = models.CharField("Omschrijving", max_length=255, blank=True)
    order = models.PositiveIntegerField("Volgorde", default=0)
    active = models.BooleanField("Actief", default=True)

    class Meta:
        verbose_name = "Beroep"
        verbose_name_plural = "Beroepen"
        ordering = ["order"]

    def __str__(self):
        return self.naam


# ── Insurers ────────────────────────────────────────────────────────────────
class Verzekeraar(PhotoMixin):
    naam = models.CharField("Naam", max_length=120)
    slug = models.SlugField("Slug", max_length=140, unique=True, blank=True)
    score = models.CharField("Score (kop)", max_length=10, blank=True,
                             help_text="Hoofdscore naast het logo, bijv. '9,0'.")
    premie_vanaf = models.CharField("Premie vanaf (€)", max_length=20, blank=True)
    tags = models.CharField("Kenmerken (tags)", max_length=255, blank=True, help_text="Komma-gescheiden.")
    order = models.PositiveIntegerField("Volgorde", default=0)
    active = models.BooleanField("Actief", default=True)

    # ── Editorial verrijking voor de premie-vergelijker (admin = bron) ──
    omschrijving = models.TextField("Omschrijving", blank=True,
                                    help_text="Korte omschrijving van de verzekeraar.")
    review_count = models.CharField("Aantal reviews", max_length=20, blank=True, help_text="bijv. '4.587'")

    score_tevredenheid = models.CharField("Beoordeling · algemene tevredenheid", max_length=5, blank=True)
    score_klantgerichtheid = models.CharField("Beoordeling · klantgerichtheid", max_length=5, blank=True)
    score_deskundigheid = models.CharField("Beoordeling · deskundigheid", max_length=5, blank=True)
    score_duidelijkheid = models.CharField("Beoordeling · duidelijkheid", max_length=5, blank=True)
    score_vertrouwen = models.CharField("Beoordeling · vertrouwen", max_length=5, blank=True)
    score_prijs_kwaliteit = models.CharField("Beoordeling · prijs-kwaliteit", max_length=5, blank=True)
    score_contact = models.CharField("Beoordeling · contact met verzekeraar", max_length=5, blank=True)

    telefonisch_contact = models.BooleanField("Telefonisch contact mogelijk", default=False)
    dagelijks_opzegbaar = models.BooleanField("Dagelijks opzegbaar", default=False)
    aanschafwaarde = models.BooleanField("Aanschafwaarde-dekking", default=False)
    eenmalige_poliskosten = models.CharField("Eenmalige poliskosten", max_length=20, blank=True, help_text="bijv. '€ 0,00'")
    type_polis = models.CharField("Type polis", max_length=40, blank=True, help_text="bijv. 'Digitale polis'")
    bijzonderheden = models.CharField("Bijzonderheden", max_length=120, blank=True)

    class Meta:
        verbose_name = "Verzekeraar"
        verbose_name_plural = "Verzekeraars"
        ordering = ["order", "naam"]

    def __str__(self):
        return self.naam

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.naam)
        super().save(*args, **kwargs)

    @property
    def tags_list(self):
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    @property
    def score_dot(self):
        """Score with a decimal point, for the JS sort `data-score` attribute."""
        return self.score.replace(",", ".")

    @property
    def beoordeling_list(self):
        """Filled rating sub-scores as [(label, score)] for the breakdown."""
        rows = [
            ("Algemene tevredenheid", self.score_tevredenheid),
            ("Klantgerichtheid", self.score_klantgerichtheid),
            ("Deskundigheid", self.score_deskundigheid),
            ("Duidelijkheid", self.score_duidelijkheid),
            ("Vertrouwen", self.score_vertrouwen),
            ("Prijs-kwaliteit", self.score_prijs_kwaliteit),
            ("Contact met verzekeraar", self.score_contact),
        ]
        return [[label, s] for label, s in rows if s]

    @property
    def kenmerken_list(self):
        """Filled feature rows as [(label, value)] for the kenmerken table."""
        rows = [
            ("Telefonisch contact mogelijk", "Ja" if self.telefonisch_contact else ""),
            ("Dagelijks opzegbaar", "Ja" if self.dagelijks_opzegbaar else ""),
            ("Aanschafwaarde", "Ja" if self.aanschafwaarde else ""),
            ("Eenmalige poliskosten", self.eenmalige_poliskosten),
            ("Type polis", self.type_polis),
            ("Bijzonderheden", self.bijzonderheden),
        ]
        return [[label, v] for label, v in rows if v]

    def default_photo_alt(self):
        return f"Logo van {self.naam}"


# ── Blog & knowledge base ───────────────────────────────────────────────────
class BlogArtikel(PhotoMixin):
    titel = models.CharField("Titel", max_length=200)
    slug = models.SlugField("Slug", max_length=220, unique=True, blank=True)
    categorie = models.CharField("Categorie", max_length=80, blank=True)
    leestijd = models.CharField("Leestijd", max_length=20, blank=True, help_text="bijv. '5 min'")
    datum = models.CharField("Datum (weergave)", max_length=40, blank=True)
    author = models.ForeignKey("Expert", verbose_name="Auteur", on_delete=models.SET_NULL,
                               null=True, blank=True, related_name="+")
    excerpt = models.TextField("Samenvatting", blank=True)
    featured = models.BooleanField("Uitgelicht", default=False)
    order = models.PositiveIntegerField("Volgorde", default=0)
    active = models.BooleanField("Actief", default=True)

    class Meta:
        verbose_name = "Blogartikel"
        verbose_name_plural = "Blogartikelen"
        ordering = ["order"]

    def __str__(self):
        return self.titel

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.titel)[:220]
        super().save(*args, **kwargs)

    def default_photo_alt(self):
        return self.titel


class KennisbankCategorie(models.Model):
    ICON_CHOICES = [
        ("square", "Vierkant (lijn)"), ("square-fill", "Vierkant (vol)"),
        ("triangle", "Driehoek"), ("pill", "Pil"), ("diamond", "Ruit"),
        ("bars", "Strepen"), ("ring", "Ring"),
    ]
    naam = models.CharField("Categorie", max_length=120)
    aantal = models.CharField("Aantal (weergave)", max_length=40, blank=True,
                              help_text="bijv. '214 artikelen'")
    icon = models.CharField("Icoon", max_length=20, choices=ICON_CHOICES, default="square")
    link = models.CharField("Link (pad of URL)", max_length=200, blank=True,
                            help_text="Waar de tegel naartoe gaat, bijv. '/beroep/' of '/verzekeraars/'. "
                                      "Leeg = naar de kennisbank.")
    order = models.PositiveIntegerField("Volgorde", default=0)

    class Meta:
        verbose_name = "Kennisbank-categorie"
        verbose_name_plural = "Kennisbank-categorieën"
        ordering = ["order"]

    def __str__(self):
        return self.naam


class KennisbankArtikel(PhotoMixin):
    titel = models.CharField("Titel", max_length=200)
    slug = models.SlugField("Slug", max_length=220, unique=True, blank=True)
    categorie = models.CharField("Categorie", max_length=80, blank=True)
    excerpt = models.TextField("Samenvatting", blank=True)
    leestijd = models.CharField("Leestijd", max_length=20, blank=True, help_text="bijv. '4 min'")
    gelezen = models.CharField("Aantal keer gelezen", max_length=20, blank=True, help_text="bijv. '12.4k'")
    featured = models.BooleanField("Uitgelicht", default=False)
    order = models.PositiveIntegerField("Volgorde", default=0)
    active = models.BooleanField("Actief", default=True)

    class Meta:
        verbose_name = "Kennisbank-artikel"
        verbose_name_plural = "Kennisbank-artikelen"
        ordering = ["order"]

    def __str__(self):
        return self.titel

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.titel)[:220]
        super().save(*args, **kwargs)

    def default_photo_alt(self):
        return self.titel


# ── Content-fabriek pages (imported from content-systeem CSV) ───────────────
class ContentPagina(models.Model):
    """
    A content page imported from the content-systeem (contentfabriek) WP-import
    CSV. Holds ready-to-render HTML (intro/body/faq/conclusie/cta/internal links)
    plus SEO metadata, image and JSON-LD. Served by a catch-all route on `slug`.
    """
    slug = models.SlugField("Slug (pad)", max_length=255, unique=True, allow_unicode=False,
                            help_text="Pad zonder voor-/achter-slash, bv. verzekeraars/unive-bestelautoverzekering")
    contenttype = models.CharField("Contenttype", max_length=40, blank=True)
    titel = models.CharField("Titel", max_length=300)
    focus_keyword = models.CharField("Focus-keyword", max_length=200, blank=True)
    zoekintentie = models.CharField("Zoekintentie", max_length=40, blank=True)

    meta_title = models.CharField("SEO-titel", max_length=300, blank=True)
    meta_description = models.TextField("SEO-omschrijving", blank=True)

    image_url = models.URLField("Afbeelding-URL", max_length=600, blank=True)
    image_local = models.CharField("Afbeelding lokaal pad", max_length=300, blank=True,
                                   help_text="Wordt gevuld door download_content_images; "
                                             "voert de {% picture %}-pipeline (WebP/JPEG).")
    image_alt = models.CharField("Afbeelding alt", max_length=400, blank=True)
    image_credit = models.CharField("Fotocredit", max_length=300, blank=True)
    image_credit_url = models.URLField("Fotocredit-URL", max_length=600, blank=True)

    intro_html = models.TextField("Intro (HTML)", blank=True)
    body_html = models.TextField("Body (HTML)", blank=True)
    faq_html = models.TextField("FAQ (HTML)", blank=True)
    conclusie_html = models.TextField("Conclusie (HTML)", blank=True)
    cta_html = models.TextField("CTA (HTML)", blank=True)
    interne_links_html = models.TextField("Interne links (HTML)", blank=True)

    toc = models.JSONField("Inhoudsopgave", default=list, blank=True)
    schema_jsonld = models.TextField("Schema JSON-LD", blank=True)
    bronnen = models.TextField("Bronnen", blank=True)

    gate_status = models.CharField("Gate-status", max_length=20, blank=True)
    published = models.BooleanField("Gepubliceerd", default=True)
    imported_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Content-pagina"
        verbose_name_plural = "Content-pagina's"
        ordering = ["contenttype", "slug"]
        indexes = [models.Index(fields=["contenttype"])]

    def __str__(self):
        return self.titel

    def get_absolute_url(self):
        return f"/{self.slug}/"

    def get_image_source(self):
        """Value for {% picture %}: the locally-downloaded path (optimised via the
        pipeline) when available, otherwise the original external URL."""
        return self.image_local or self.image_url

    def get_seo_title(self):
        return self.meta_title or self.titel

    def get_seo_description(self):
        return self.meta_description

    @property
    def excerpt(self):
        """Plain-text teaser from the intro (for hub/overview cards)."""
        import re
        text = re.sub(r"<[^>]+>", "", self.intro_html or "")
        text = re.sub(r"\s+", " ", text).strip()
        return (text[:150].rsplit(" ", 1)[0] + "…") if len(text) > 150 else text

    @property
    def tagline(self):
        """Short one-liner for compact cards (first ~70 chars of the intro)."""
        text = self.excerpt
        return (text[:70].rsplit(" ", 1)[0] + "…") if len(text) > 72 else text

    @property
    def korte_titel(self):
        """Display name derived from the slug, e.g. 'Koerier', 'Ford Transit'."""
        seg = self.slug.rsplit("/", 1)[-1]
        for pre in ("bestelautoverzekering-", "bestelauto-"):
            if seg.startswith(pre):
                seg = seg[len(pre):]
        for suf in ("-bestelautoverzekering", "-bestelautoverzekeren", "-verzekering",
                    "-verzekeren", "-bestelauto", "-bestelbus"):
            if seg.endswith(suf):
                seg = seg[: -len(suf)]
                break
        seg = seg.replace("-", " ").strip()
        return seg.title() if seg else self.titel


# ── Premie-tool: logging van berekeningen/aanvragen ─────────────────────────
class Berekening(models.Model):
    """One row per premie-tool session, logs every step for admin insight
    (mirrors the Lovable `calculations` table). Stores personal data (kenteken,
    KvK, NAW); see the privacy/retention note in the admin and apply a bewaar-
    termijn. Written server-side by the premie proxy views, never by the client."""

    STATUS_CHOICES = [
        ("started", "Gestart"),
        ("vehicle-lookup", "Kenteken opgezocht"),
        ("calculated", "Premies berekend"),
        ("additional", "Aanvullende dekkingen"),
        ("requested", "Aangevraagd (polis)"),
        ("failed", "Mislukt"),
    ]

    session_id = models.CharField("Sessie-ID", max_length=64, db_index=True)
    license_plate = models.CharField("Kenteken", max_length=12, blank=True)
    is_van = models.BooleanField("Bestelauto (van)", default=False)
    coverage = models.CharField("Dekking", max_length=4, blank=True)

    vehicle_info = models.JSONField("Voertuiggegevens", default=dict, blank=True)
    business_details = models.JSONField("Bedrijfsgegevens", default=dict, blank=True)
    results = models.JSONField("Premie-resultaten", default=list, blank=True)
    selected_result = models.JSONField("Gekozen verzekeraar", default=dict, blank=True)
    additional_coverages = models.JSONField("Aanvullende dekkingen", default=list, blank=True)
    request_data = models.JSONField("Aanvraaggegevens", default=dict, blank=True)

    policy_number = models.CharField("Polisnummer", max_length=60, blank=True)
    status = models.CharField("Status", max_length=20, choices=STATUS_CHOICES, default="started")
    current_step = models.CharField("Huidige stap", max_length=30, default="license-plate")

    created_at = models.DateTimeField("Aangemaakt", auto_now_add=True)
    updated_at = models.DateTimeField("Bijgewerkt", auto_now=True)

    class Meta:
        verbose_name = "Berekening"
        verbose_name_plural = "Berekeningen"
        ordering = ["-created_at"]

    def __str__(self):
        plate = self.license_plate or "—"
        return f"{plate} · {self.get_status_display()} · {self.created_at:%d-%m-%Y %H:%M}"


# ── Trustpilot: cached score + latest reviews (weekly fetch via API) ─────────
class TrustpilotProfile(models.Model):
    """Singleton cache of the autoverzekering.nl Trustpilot TrustScore + counts,
    refreshed weekly by `manage.py fetch_trustpilot`. The site renders from this
    row (never live per request). Editable in admin as a manual fallback."""

    domain = models.CharField("Trustpilot-domein", max_length=120, default="autoverzekering.nl")
    business_unit_id = models.CharField("Business-unit-ID", max_length=64, blank=True,
                                        help_text="Door de API opgehaald o.b.v. het domein; wordt gecachet.")
    profile_url = models.URLField("Profiel-URL", max_length=300,
                                  default="https://nl.trustpilot.com/review/autoverzekering.nl")
    trust_score = models.DecimalField("TrustScore (1–5)", max_digits=3, decimal_places=1, default=0)
    stars = models.DecimalField("Sterren (1–5)", max_digits=2, decimal_places=1, default=0)
    review_count = models.PositiveIntegerField("Aantal reviews", default=0)
    last_fetched = models.DateTimeField("Laatst opgehaald", null=True, blank=True)

    class Meta:
        verbose_name = "Trustpilot-profiel"
        verbose_name_plural = "Trustpilot-profiel"

    def __str__(self):
        return f"Trustpilot {self.domain} · {self.trust_score}/5 ({self.review_count})"

    def save(self, *args, **kwargs):
        self.pk = 1  # enforce singleton
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def has_data(self):
        return self.review_count > 0 and float(self.trust_score) > 0

    @property
    def score_display(self):
        """NL-format TrustScore, e.g. '4,6'."""
        return f"{self.trust_score:.1f}".replace(".", ",")

    @property
    def count_display(self):
        return f"{self.review_count:,}".replace(",", ".")

    @property
    def stars_rounded(self):
        """Nearest half-star (for ★ display)."""
        return round(float(self.stars or self.trust_score) * 2) / 2


class TrustpilotReview(models.Model):
    """One fetched Trustpilot review. The latest N are kept and fully replaced on
    each weekly fetch (upsert on external_id)."""

    external_id = models.CharField("Trustpilot-ID", max_length=64, unique=True)
    author = models.CharField("Auteur", max_length=160)
    rating = models.PositiveSmallIntegerField("Sterren", default=5)
    title = models.CharField("Titel", max_length=300, blank=True)
    text = models.TextField("Tekst", blank=True)
    language = models.CharField("Taal", max_length=8, blank=True)
    review_url = models.URLField("Review-URL", max_length=400, blank=True)
    created_at = models.DateTimeField("Datum review")
    fetched_at = models.DateTimeField("Opgehaald op", auto_now=True)
    order = models.PositiveSmallIntegerField("Volgorde", default=0)

    class Meta:
        verbose_name = "Trustpilot-review"
        verbose_name_plural = "Trustpilot-reviews"
        ordering = ["order", "-created_at"]

    def __str__(self):
        return f"{self.author} · {self.rating}★"

    @property
    def created_iso(self):
        return self.created_at.date().isoformat() if self.created_at else ""


# ── Admin-editable menus (main nav + footer) ────────────────────────────────
class MenuItem(models.Model):
    """One navigation/footer entry. Top-level rows (parent empty) are the nav
    items / footer columns; their children are the dropdown links / column
    links. Read by core.context_processors (with a hardcoded fallback)."""

    MENU_CHOICES = [("nav", "Hoofdmenu (bovenbalk)"), ("footer", "Footer")]

    menu = models.CharField("Menu", max_length=10, choices=MENU_CHOICES, default="nav")
    parent = models.ForeignKey("self", verbose_name="Valt onder", null=True, blank=True,
                               on_delete=models.CASCADE, related_name="children")
    label = models.CharField("Label", max_length=80)
    url = models.CharField("Link (pad of URL)", max_length=200, blank=True,
                           help_text="bijv. '/dekkingen/'. Leeg = alleen kop "
                                     "(footer-kolom of dropdown-groep zonder eigen link).")
    order = models.PositiveIntegerField("Volgorde", default=0)
    active = models.BooleanField("Actief", default=True)

    class Meta:
        verbose_name = "Menu-item"
        verbose_name_plural = "Menu's (nav + footer)"
        ordering = ["menu", "order", "id"]

    def __str__(self):
        return f"[{self.get_menu_display()}] {'↳ ' if self.parent_id else ''}{self.label}"

    def save(self, *args, **kwargs):
        if self.parent_id:  # children always live in the same menu as their parent
            self.menu = self.parent.menu
        super().save(*args, **kwargs)
