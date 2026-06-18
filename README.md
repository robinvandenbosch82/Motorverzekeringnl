# Bestelautoverzekering.nl

Standalone Django site — de niche-authority voor het verzekeren van
bestelauto's van ondernemers (ZZP, aannemers, installateurs, koeriers,
wagenparken). Onafhankelijke vergelijker + tekstrijke kennisbank.

Zustersites met dezelfde conventies: **vliegtickets.com** (`:8000`) en
**cruises.nl** (`:8001`). Deze site draait op **`:8002`**.

> Het visuele ontwerp komt uit een Claude Design-handoff (claude.ai/design) en
> is hier 1-op-1 nagebouwd in een server-side gerenderde Django-stack.

---

## Stack

- **Django 5.1** · Python 3.12 · 100% server-side rendering (SSR) — geen SPA.
- **WhiteNoise** voor static files (gzip/brotli; manifest-hashing opt-in in prod).
- **python-dotenv** voor env-gedreven secrets.
- Geen frontend-buildstap: één `static/css/styles.css` (design-tokens +
  componentklassen) en één `static/js/site.js` (vanilla progressive enhancement).
- SQLite in dev; Postgres via `DATABASE_URL` in productie.

## Snel starten

```bash
cd C:\Users\robin\bestelautoverzekering
python -m venv .venv && .venv\Scripts\activate      # aanbevolen
pip install -r requirements.txt
copy .env.example .env                                # vul SECRET_KEY in, zet DEBUG=True
python manage.py migrate
python manage.py sync_pages          # maak een Page-rij per route
python manage.py seed_content        # vul SiteSettings + content-modellen
python manage.py createsuperuser     # admin-login
python manage.py runserver 8002
# → http://127.0.0.1:8002/  ·  admin → http://127.0.0.1:8002/admin/
```

## Admin / CMS

De Django-admin (`/admin/`) is de **bron van de content**. Structuur:
- **Site-instellingen** (singleton) — reviewcijfers, contact, AFM/KvK, footer.
- **Pagina's** — één rij per route (gesynct via `sync_pages`); per pagina
  SEO-titel/-omschrijving, OG-afbeelding, noindex en hero-tekst bewerkbaar.
- **Content-modellen** — FAQ, reviews, experts, dekkingstiers (+kenmerken),
  situaties, beroepen, verzekeraars, blogartikelen, kennisbank-categorieën/-artikelen.

Templates lezen uit de DB met fallback naar de seed, dus bewerken in de admin is
direct zichtbaar op de site. Reeds live op de DB: per-pagina SEO + noindex (alle
14 pagina's), SiteSettings (footer/nav/widget) en de homepage-trust-content
(FAQ, reviews, experts, situaties). Nog te koppelen (modellen + admin bestaan al,
templates volgen): homepage dekkingen/kennisbank-tegels, de overzichtspagina's
(verzekeraars/blog/kennisbank/situaties) en de bodyteksten van detailpagina's.

Genereer een SECRET_KEY:
```bash
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

## Tests & smoke-test

```bash
python manage.py test            # unit tests (render, SEO, sitemap, robots)
python manage.py check_pages     # smoke-test: rendert elke pagina, checkt chrome + SEO
python manage.py check_pages --verbose
```

Draai `check_pages` **na elke template- of view-wijziging** (zoals bij cruises.nl).

## Afbeeldingen & Pexels (geport uit cruises.nl / vliegtickets)

Beeld is geen `background-image` maar **echte responsive `<img>`** met alt-tekst,
WebP/JPEG-srcset en LCP-prioriteit — net als de zustersites.

- **Per content-object** (Expert, Review, Situatie, Verzekeraar, BlogArtikel,
  KennisbankArtikel) zit een `PhotoMixin`: je kunt in de admin een foto **uploaden**,
  een **externe URL** plakken, of via de **Pexels-zoekwidget** zoeken + lokaal
  downloaden. `get_photo_url()` kiest de beste bron (upload > lokaal > URL);
  `get_photo_alt()` valt terug op een zinnige default.
- **Pexels-sleutel**: admin → *Site-instellingen* → Pexels API-sleutel (of
  `PEXELS_API_KEY` in `.env`). Gratis via pexels.com/api.
- **Responsive pipeline**: `core/services/image_pipeline.py` genereert WebP/JPEG-
  varianten in `media/cache/`; de `{% picture %}`-tag (`core/templatetags/
  responsive_image.py`) rendert het `<picture>`. Bij een upload pre-warmen
  `core/signals.py` de varianten.
- **Bulk vullen vanuit Pexels**:
  ```bash
  python manage.py fetch_pexels_photos --model all                 # vul URL's
  python manage.py fetch_pexels_photos --model situatie --download  # + lokaal opslaan
  python manage.py fetch_pexels_photos --model expert --dry-run
  ```
- **In dev** wordt `/media/` geserveerd door Django; in productie door de webserver.

## Projectstructuur

```
config/                  Django project (settings, urls, wsgi)
  settings.py            env-gedreven; security hardening alleen buiten DEBUG
  urls.py                admin, sitemap.xml, robots.txt, include(core)
core/
  views.py               PAGES-registry (single source of truth) + thin views
  urls.py                URL-patterns gegenereerd uit PAGES
  sitemaps.py            sitemap gegenereerd uit PAGES
  context_processors.py  NAV_ITEMS + FOOTER_COLUMNS + per-request SEO defaults
  content.py             prototype-content (wordt later vervangen door CSV-import)
  tests.py               render/SEO/discoverability tests
  management/commands/check_pages.py
templates/
  base.html              SEO-head (title/desc/canonical/OG/Twitter/JSON-LD) + chrome
  partials/
    site_nav.html        sticky desktop-nav met dropdowns + fullscreen mobiel menu
    site_footer.html     volledige footer (overal)
    premie_widget.html   herbruikbare "vergelijk & bereken"-band (auto vóór footer)
    _calc.html           de premie-calculator-kaart (hero + widget delen deze)
    _tier.html           WA / WA+ / Allrisk dekkingskaart
  pages/                 één template per pagina (14 stuks)
static/css/styles.css    design-systeem: tokens (CSS custom properties) + componenten
static/js/site.js        calculator, stilstand-sliders, FAQ, mobiel menu, count-up, reveal
```

## Architectuur-principes

- **PAGES-registry** (`core/views.py`) is de single source of truth: voeg een
  pagina één keer toe en URL-routing, sitemap én `check_pages` pikken 'm op.
- **Drielaags SEO** (conform de zustersites): view zet `seo_title`/
  `seo_description` → `base.html` rendert title/description/canonical/OG/Twitter
  → per pagina kan `{% block structured_data %}` extra JSON-LD toevoegen.
  Sitewide staan Organization + WebSite schema in `base.html`.
- **Gedeelde chrome via includes**: nav, footer en premie-widget zijn herbruikbaar
  en worden centraal beheerd (één wijziging = overal door).
- **Design-tokens** als CSS custom properties; oranje (`--orange`) uitsluitend
  voor CTA's, actieve staten en kerncijfers (merkregel).
- **Mobiel**: desktop is pixel-getrouw aan het ontwerp ≥ 880px; daaronder
  stapelt de layout via echte media queries (de prototype-tool had die niet).
- **Progressive enhancement**: alle content is SSR; JS voegt alleen interactie
  toe. Reveal-animaties zijn `.js`-gated zodat content zichtbaar blijft zonder JS.

## Productie (checklist)

- `.env`: `DEBUG=False`, echte `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`,
  `USE_MANIFEST_STATIC=True`, en `DATABASE_URL` (Postgres).
- `python manage.py collectstatic` (vereist als `USE_MANIFEST_STATIC=True`).
- Buiten DEBUG schakelen SSL-redirect, HSTS en secure cookies automatisch aan.
- Draai onder gunicorn + reverse proxy; zet `SECURE_PROXY_SSL_HEADER` (al voorzien).
- **Trustpilot wekelijks ophalen** (score + laatste 4 reviews → homepage + JSON-LD).
  Zet `TRUSTPILOT_API_KEY` in `.env` en plan `fetch_trustpilot` wekelijks. Cron:
  ```
  0 4 * * 1  cd /pad/naar/app && /pad/venv/bin/python manage.py fetch_trustpilot >> logs/trustpilot.log 2>&1
  ```
  Op de dev-machine draait dit al via Windows Taakplanner (`Bestelautoverzekering-Trustpilot`, ma 04:00).
  Zonder key is het commando een no-op; de site valt terug op de handmatige score in Site-instellingen.

## Deploy naar Render (Blueprint)

`render.yaml` zet web (gunicorn) + Postgres + persistente media-schijf + de
wekelijkse Trustpilot-cron in één keer op. Stappen:

1. **Blueprint koppelen** — Render → *New* → *Blueprint* → kies deze GitHub-repo.
   Render leest `render.yaml`, maakt de database, het web-service en de cron aan.
2. **Secrets invullen** — in de env-group `bestelauto-env` (dashboard) de `sync:false`-
   keys zetten: `DJANGO_SUPERUSER_PASSWORD`, `RISK_API_USERNAME`, `RISK_API_PASSWORD`,
   `RISK_BROKER_ID`, `TRUSTPILOT_API_KEY`. `SECRET_KEY` en `DATABASE_URL` vult Render zelf.
3. **Data + media gaan automatisch.** De `preDeployCommand` draait `migrate` +
   `bootstrap_site`, dat een verse host vult uit de meegeleverde seed:
   - `deploy/seed.json` (382 records: content, verzekeraars, situaties, menu's,
     Trustpilot-reviews, SiteSettings…) → in Postgres (idempotent, skipt als er al content is).
   - `deploy/seed_media/` (heroes + experts) → op de media-schijf.
   - superuser uit `DJANGO_SUPERUSER_*`; beeldvarianten voorverwarmd.
   Content-detailafbeeldingen vallen terug op hun externe URL tot je ze lokaliseert.
4. **(optioneel) content-afbeeldingen lokaliseren** — éénmalig in de Render *Shell*:
   `python manage.py bootstrap_site --localize` (downloadt de 241 content-images naar
   de schijf en verwerkt ze door de WebP/JPEG-pipeline).
5. **Domein** — koppel `bestelautoverzekering.nl` in Render; `ALLOWED_HOSTS` en
   `SITE_ORIGIN` staan al goed in de env-group. SSL/HSTS gaan buiten DEBUG vanzelf aan.

> De seed ververs je lokaal met `python manage.py dumpdata core --exclude core.berekening
> --indent 2 -o deploy/seed.json` (UTF-8: zet `PYTHONUTF8=1` op Windows). `core.berekening`
> blijft eruit — dat zijn premie-aanvragen met persoonsgegevens.

> Alternatieven met identieke aanpak: Railway (Nixpacks + Postgres-plugin) of
> Fly.io (`fly launch` + `fly postgres`). De codewijzigingen (DATABASE_URL,
> gunicorn, collectstatic) zijn hostonafhankelijk.

## Bekende technische schuld

| # | Beschrijving | Reden | Risico | Aanbevolen fix | Prioriteit |
|---|--------------|-------|--------|----------------|-----------|
| 1 | CMS-koppeling deels af: homepage-dekkingen/kennisbank-tegels, overzichtspagina's (verzekeraars/blog/kennisbank/situaties) en detail-bodyteksten lezen nog static | CMS in stappen opgebouwd; modellen + admin bestaan al, templates volgen | Die content nog niet via admin bewerkbaar (wel via code) | Resterende templates op de bestaande modellen aansluiten (loops i.p.v. hardcoded lijsten) | Hoog |
| 2 | Premie-calculator geeft dummy-uitkomst (€41 / €29) | Echte premie-logica/tarieven nog niet aangeleverd (Robin levert na) | Misleidende indicatie als live | Premie-engine koppelen zodra tarieven er zijn | Hoog |
| 3 | ✅ OPGELOST — Pexels-service + responsive `{% picture %}`-pipeline + upload-cascade geport uit de zustersites; alle beelden zijn nu `<img>` met alt. Restje: geseede demo-foto's wijzen nog naar Unsplash tot iemand ze upload/Pexels-downloadt (`fetch_pexels_photos --download`, vereist Pexels-key). | — | — | Key in admin zetten + `fetch_pexels_photos --download --overwrite` draaien voor zelf-hosting | Laag |
| 4 | ✅ OPGELOST — `import_content` haalt de contentfabriek-CSV's binnen in `ContentPagina` (248 pagina's live op hun slug via catch-all). Rest: content-pagina's nog niet in de site-navigatie/overzichten geweven (alleen via slug + interne links bereikbaar). | — | — | Overzichts-/hub-listings van `ContentPagina` per contenttype toevoegen | Laag |
| 5 | Zoekformulier kennisbank is nog niet functioneel | Buiten scope van de design-implementatie | Geen werkende zoek | Zoek-view + index toevoegen | Laag |

## Herkomst van het ontwerp

`C:\Users\robin\design_bestelauto\bestelautoverzekering-nl\` — Claude Design
bundel (README + 3 chat-transcripts + `*.dc.html` prototypes + screenshots).
De `.dc.html`-bestanden zijn React-achtige prototypes; hier vertaald naar Django
SSR met vanilla JS voor de interactie.
