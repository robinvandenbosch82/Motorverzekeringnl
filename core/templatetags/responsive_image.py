"""
Template-tag voor responsive <picture> met WebP srcset.

Gebruik:
    {% load responsive_image %}

    {# LCP hero — eager + preload #}
    {% picture post.hero_image_local sizes="100vw" alt=post.title loading="eager" fetchpriority="high" %}

    {# Lazy kaartje #}
    {% picture airport.photo_local sizes="(max-width:600px) 100vw, 33vw" alt=airport.city %}

    {# Externe URL (Pexels) — plain img met juiste attrs #}
    {% picture "https://images.pexels.com/…" alt="…" loading="eager" fetchpriority="high" %}

Output (lokaal bestand):
    <picture>
      <source type="image/webp" srcset="…_w400.webp 400w, …_w800.webp 800w, …" sizes="…">
      <source type="image/jpeg" srcset="…_w400.jpg 400w, …_w800.jpg 800w, …" sizes="…">
      <img src="…_w800.jpg" alt="…" width="800" height="533"
           loading="lazy" decoding="async">
    </picture>

Output (externe URL):
    <img src="…" alt="…" loading="lazy" decoding="async">
"""
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

from core.services.image_pipeline import get_variant_urls, DEFAULT_WIDTHS

register = template.Library()


@register.simple_tag
def picture(source, **kwargs):
    """Render <picture> met WebP/JPEG srcset voor lokale bestanden,
    of een plain <img> voor externe URLs.

    Keyword args:
        sizes        CSS sizes-attribuut (default '100vw')
        alt          alt-tekst
        class        CSS class op <img>
        widths       comma-sep breedte-lijst '400,800,1200' (default: pipeline-default)
        loading      'lazy' (default) | 'eager'
        decoding     'async' (default) | 'sync'
        fetchpriority 'high' | 'low' | 'auto'  (weglaten = geen attribuut)
        style        inline CSS op <img>
    """
    src = _normalize(source)
    alt = kwargs.get('alt', '')
    css_class = kwargs.get('class', '')
    sizes = kwargs.get('sizes', '100vw')
    loading = kwargs.get('loading', 'lazy')
    decoding = kwargs.get('decoding', 'async')
    fetchpriority = kwargs.get('fetchpriority', '')
    style = kwargs.get('style', '')

    widths_str = kwargs.get('widths')
    widths = None
    if widths_str:
        try:
            widths = tuple(int(w.strip()) for w in str(widths_str).split(','))
        except ValueError:
            pass
    widths = widths or DEFAULT_WIDTHS

    if not src:
        return mark_safe('')

    # ── Externe URL: geen pipeline mogelijk ──────────────────────────────────
    if src.startswith(('http://', 'https://', '//')):
        return mark_safe(
            f'<img {_attrs(src, alt, css_class, loading, decoding, fetchpriority, style=style)}>'
        )

    # ── Lokaal bestand via pipeline ───────────────────────────────────────────
    info = get_variant_urls(src, widths=widths)
    if not info:
        # Bestand niet gevonden — plain img, werkt zodra bestand aanwezig is
        url = src if src.startswith('/') else f'/media/{src}'
        return mark_safe(
            f'<img {_attrs(url, alt, css_class, loading, decoding, fetchpriority, style=style)}>'
        )

    sources = []
    for s in info['sources']:
        sources.append(
            f'<source type="{s["format"]}" '
            f'srcset="{escape(s["srcset"])}" '
            f'sizes="{escape(sizes)}">'
        )

    img_tag = (
        f'<img {_attrs(info["fallback_url"], alt, css_class, loading, decoding, fetchpriority, info["width"], info["height"], style=style)}>'
    )
    return mark_safe('<picture>\n' + '\n'.join(sources) + '\n' + img_tag + '\n</picture>')


@register.simple_tag
def preload_hint(source, sizes='100vw', widths=None):
    """Voeg een <link rel="preload"> toe voor de LCP-afbeelding.

    Gebruik in {% block head_extra %}:
        {% preload_hint post.hero_image_local sizes="100vw" %}

    Geeft lege string terug voor externe URLs (browser handelt dat zelf af).
    """
    src = _normalize(source)
    if not src or src.startswith(('http://', 'https://', '//')):
        return mark_safe('')

    info = get_variant_urls(src, widths=widths or DEFAULT_WIDTHS)
    if not info:
        return mark_safe('')

    # Gebruik WebP source voor de preload (beste compressie)
    webp_src = next(
        (s for s in info['sources'] if 'webp' in s['format']),
        None,
    )
    if not webp_src:
        return mark_safe('')

    return mark_safe(
        f'<link rel="preload" as="image" type="image/webp" '
        f'imagesrcset="{escape(webp_src["srcset"])}" '
        f'imagesizes="{escape(sizes)}">'
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _normalize(source):
    """Zet ImageFieldFile, str of None om naar een string."""
    if not source:
        return ''
    if hasattr(source, 'name'):
        return source.name or ''
    return str(source).strip()


def _attrs(src, alt, css_class, loading, decoding, fetchpriority,
           width=None, height=None, style=''):
    parts = [
        f'src="{escape(src)}"',
        f'alt="{escape(alt)}"',
    ]
    if css_class:
        parts.append(f'class="{escape(css_class)}"')
    if width:
        parts.append(f'width="{width}"')
    if height:
        parts.append(f'height="{height}"')
    if loading:
        parts.append(f'loading="{loading}"')
    if decoding:
        parts.append(f'decoding="{decoding}"')
    if fetchpriority:
        parts.append(f'fetchpriority="{fetchpriority}"')
    if style:
        parts.append(f'style="{escape(style)}"')
    return ' '.join(parts)
