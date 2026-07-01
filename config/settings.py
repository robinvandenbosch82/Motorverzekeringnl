"""
Django settings for Motorverzekering.nl.

Standalone Django site (eigen domein) for the niche motor-insurance
authority. Conventions are shared with the sibling projects cruises.nl and
vliegtickets.com: 100% server-side rendering, env-driven secrets, WhiteNoise
for static files, and security hardening that only switches on in production.

Secrets NEVER live in this file — they are read from the environment (.env in
development, real env vars in production). See .env.example.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env (development convenience). In production the real environment wins.
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: str = "False") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


# ──────────────────────────────────────────────────────────────────────────
# Core / security
# ──────────────────────────────────────────────────────────────────────────
DEBUG = env_bool("DEBUG", "False")

# In development we allow a throwaway key so the project runs out of the box.
# In production a real SECRET_KEY is mandatory — fail hard if it is missing.
SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-insecure-key-do-not-use-in-production"
    else:
        raise RuntimeError("SECRET_KEY environment variable is required in production.")

ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]

CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if o.strip()
]

# Railway: the platform healthcheck reaches the app via this host, and the live
# URL is exposed as RAILWAY_PUBLIC_DOMAIN. Always allow the healthcheck host (so
# deploys pass), plus the public domain + its CSRF origin when present — so the
# site and admin work without manually editing ALLOWED_HOSTS.
if "healthcheck.railway.app" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("healthcheck.railway.app")
_railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()
if _railway_domain and _railway_domain not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_railway_domain)
    CSRF_TRUSTED_ORIGINS.append(f"https://{_railway_domain}")

# Custom domein: sta zowel de apex (motorverzekering.nl) als de www-variant toe op
# basis van SITE_DOMAIN, zodat beide werken zonder ALLOWED_HOSTS handmatig bij te
# houden. Voeg ook de bijbehorende CSRF-origins toe (nodig voor admin-login en
# formulieren over het custom domein).
_site_domain = os.getenv("SITE_DOMAIN", "motorverzekering.nl").strip().lower()
if _site_domain:
    _apex = _site_domain[4:] if _site_domain.startswith("www.") else _site_domain
    for _host in (_apex, f"www.{_apex}"):
        if _host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(_host)
        _origin = f"https://{_host}"
        if _origin not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(_origin)

# ──────────────────────────────────────────────────────────────────────────
# Applications
# ──────────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.gzip.GZipMiddleware",  # compress dynamic HTML responses
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.site_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ──────────────────────────────────────────────────────────────────────────
# Database — SQLite in dev, DATABASE_URL (Postgres) in production
# ──────────────────────────────────────────────────────────────────────────
# SQLite in development; Postgres in production via DATABASE_URL (Render/Railway/
# etc. inject it). The dj-database-url import is guarded so dev/tests run without
# the production dependency installed.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
_database_url = os.getenv("DATABASE_URL", "").strip()
if _database_url:
    import dj_database_url

    DATABASES["default"] = dj_database_url.parse(
        _database_url, conn_max_age=600, ssl_require=True
    )

# ──────────────────────────────────────────────────────────────────────────
# Password validation
# ──────────────────────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ──────────────────────────────────────────────────────────────────────────
# Internationalisation — Dutch / Europe-Amsterdam
# ──────────────────────────────────────────────────────────────────────────
LANGUAGE_CODE = "nl-nl"
TIME_ZONE = "Europe/Amsterdam"
USE_I18N = True
USE_TZ = True

# ──────────────────────────────────────────────────────────────────────────
# Static / media (WhiteNoise)
# ──────────────────────────────────────────────────────────────────────────
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Manifest storage gives hashed, far-future-cacheable filenames but requires
# `collectstatic` to have run (so it would break tests/dev). Opt in for
# production via USE_MANIFEST_STATIC=True; everywhere else use the compressed
# (non-manifest) WhiteNoise storage, which needs no build step.
# Manifest storage = hashed, immutable, far-future-cacheable filenames. It needs
# `collectstatic` to have run, so we enable it automatically in production
# (DEBUG off) but never during tests (which don't collect static).
_running_tests = "test" in sys.argv
_USE_MANIFEST_STATIC = env_bool("USE_MANIFEST_STATIC", "False") or (not DEBUG and not _running_tests)
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
            if _USE_MANIFEST_STATIC
            else "whitenoise.storage.CompressedStaticFilesStorage"
        )
    },
}

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Ensure next-gen image variants are served with the right Content-Type
# (Python's mimetypes doesn't know .webp; some setups also miss .avif).
import mimetypes  # noqa: E402
mimetypes.add_type("image/webp", ".webp", strict=True)
mimetypes.add_type("image/avif", ".avif", strict=True)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ──────────────────────────────────────────────────────────────────────────
# Caching — LocMem in dev (swap for Redis in production)
# ──────────────────────────────────────────────────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "TIMEOUT": 900,
    }
}

# ──────────────────────────────────────────────────────────────────────────
# Brand / SEO defaults (single source of truth, consumed by base.html)
# ──────────────────────────────────────────────────────────────────────────
SITE_NAME = "Motorverzekering.nl"
SITE_DOMAIN = os.getenv("SITE_DOMAIN", "motorverzekering.nl")
# Canonical origin for structured-data @id's and canonical/OG URLs. NEVER use
# request.get_host() for @id — it is host-dependent (www vs non-www, dev port)
# and would make the entity graph's identifiers unstable across pages.
# De canonieke host is altijd de WWW-variant: sitemap, canonical, robots en de
# entity-graph @id's staan zo consistent op https://www.<domein>, ongeacht of
# de env de apex of de www aanlevert.
_origin = os.getenv("SITE_ORIGIN", f"https://{SITE_DOMAIN}").rstrip("/")
_scheme, _sep, _host = _origin.rpartition("://")
if _host and not _host.startswith("www."):
    _host = "www." + _host
SITE_ORIGIN = f"{_scheme}{_sep}{_host}" if _sep else _origin
DEFAULT_SEO_TITLE = "Motorverzekering vergelijken | Motorverzekering.nl"
DEFAULT_SEO_DESCRIPTION = (
    "Dé specialist in motorverzekeringen. Vergelijk verzekeraars en bereken je "
    "premie in 2 minuten."
)

# ── E-mail (SMTP via env) ────────────────────────────────────────────────────
# Zet EMAIL_HOST + credentials in de env (Railway) om echt te versturen; zonder
# host valt het terug op de console-backend (logt de mail, verstuurt niet) zodat
# er nooit een crash is. Aanvraag-notificaties gaan naar het adres dat in de
# admin staat (SiteSettings.aanvraag_notify_email), niet naar een hardcoded adres.
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "1") not in ("0", "false", "False", "")
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "0") in ("1", "true", "True")
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL", "Motorverzekering.nl <noreply@motorverzekering.nl>")
EMAIL_BACKEND = ("django.core.mail.backends.smtp.EmailBackend" if EMAIL_HOST
                 else "django.core.mail.backends.console.EmailBackend")

# Third-party API keys (used by image/content tooling, never hardcoded)
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# RISK Insurance API — powers the premie-vergelijker/afsluit-tool. Credentials
# live ONLY here (server-side); the browser never sees them. The Django proxy
# views in core.views_premie authenticate with Basic Auth and call RISK.
RISK_API_BASE = os.getenv("RISK_API_BASE", "https://api.acc.risk.nl/InsuranceAPI")
RISK_API_USERNAME = os.getenv("RISK_API_USERNAME", "")
RISK_API_PASSWORD = os.getenv("RISK_API_PASSWORD", "")
RISK_BROKER_ID = os.getenv("RISK_BROKER_ID", "")
# v10 is the active default. Rollback is instant and code-free: set the env var
# RISK_API_VERSION=9.0 in the environment (Railway) to fall back to the v9 flow.
RISK_API_VERSION = os.getenv("RISK_API_VERSION", "10")
# Product version (PP_PRDVERS) that RISK requires in the calculate body. RISK
# provides the exact value with the motor account; set it in .env.
RISK_MOTOR_PRODUCT_VERSION = os.getenv("RISK_MOTOR_PRODUCT_VERSION", "")
# Hard timeout (seconds) for every outbound RISK call.
RISK_API_TIMEOUT = int(os.getenv("RISK_API_TIMEOUT", "20"))

# Trustpilot Public API — weekly fetch of the TrustScore + latest reviews for
# autoverzekering.nl (rendered on the homepage + Review/aggregateRating JSON-LD).
# The API key is a secret (lives in .env only); domain/business-unit are config.
# Without a key the fetch command is a graceful no-op (site falls back to the
# manually-entered SiteSettings review score).
TRUSTPILOT_API_BASE = os.getenv("TRUSTPILOT_API_BASE", "https://api.trustpilot.com/v1")
TRUSTPILOT_API_KEY = os.getenv("TRUSTPILOT_API_KEY", "")
TRUSTPILOT_DOMAIN = os.getenv("TRUSTPILOT_DOMAIN", "autoverzekering.nl")
TRUSTPILOT_BUSINESS_UNIT_ID = os.getenv("TRUSTPILOT_BUSINESS_UNIT_ID", "")
TRUSTPILOT_API_TIMEOUT = int(os.getenv("TRUSTPILOT_API_TIMEOUT", "20"))

# ──────────────────────────────────────────────────────────────────────────
# Security hardening — only switches on outside DEBUG
# ──────────────────────────────────────────────────────────────────────────
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    # The platform healthcheck hits /robots.txt over plain HTTP from inside the
    # network (no X-Forwarded-Proto: https), which SECURE_SSL_REDIRECT would 301
    # to HTTPS — and the healthchecker doesn't follow redirects. Exempt that path
    # (regex matched against the path without the leading slash) so it stays 200.
    SECURE_REDIRECT_EXEMPT = [r"^robots\.txt$"]
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ──────────────────────────────────────────────────────────────────────────
# Logging — structured to console + rotating error file (observability)
# ──────────────────────────────────────────────────────────────────────────
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{asctime} {levelname} {name} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "error.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "level": "ERROR",
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console", "error_file"], "level": "INFO"},
}
