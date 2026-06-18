"""On-demand image-variant generator voor responsive <img srcset>.

Workflow:
  - Input: pad relatief tot MEDIA_ROOT (bv. 'photos/blog/mijn-foto.jpg')
  - Genereert varianten in 'cache/<original-path-with-suffix>':
      mijn-foto_w400.jpg, mijn-foto_w800.jpg, mijn-foto_w1200.jpg
      mijn-foto_w400.webp, mijn-foto_w800.webp, mijn-foto_w1200.webp
  - Idempotent — skip als variant al bestaat én niet ouder dan origineel
  - Behoudt aspect-ratio (alleen width-resize, height auto)

Compressie bij upload (via signals.py):
  - >2 MB → in-place comprimeren naar max 2400px wide @ JPEG q85
  - Alle uploads → responsive WebP + JPEG varianten pre-genereren

Gebruik:
  from core.services.image_pipeline import get_variant_urls
  variants = get_variant_urls('photos/blog/mijn-foto.jpg')
"""
import os
from io import BytesIO

from django.conf import settings


DEFAULT_WIDTHS = (400, 800, 1200, 1920)
DEFAULT_JPEG_QUALITY = 75   # JPEG: q75 is standaard web-kwaliteit
DEFAULT_WEBP_QUALITY = 65   # WebP: q65 ≈ JPEG q85 visueel, maar ~40% kleiner
DEFAULT_AVIF_QUALITY = 52   # AVIF: nog ~20-30% kleiner dan WebP bij gelijke kwaliteit
AVIF_SPEED = 6              # encoder-snelheid 0-10 (hoger = sneller, iets groter)
CACHE_DIR = 'cache'          # submap onder MEDIA_ROOT

COMPRESS_THRESHOLD_BYTES = 2 * 1024 * 1024  # >2 MB → in-place compress
COMPRESS_MAX_WIDTH = 2400
COMPRESS_JPEG_QUALITY = 82


# ─────────────────────────────────────────────────────────────────────────────
# Publieke API
# ─────────────────────────────────────────────────────────────────────────────

def compress_if_needed(abs_path: str) -> bool:
    """Comprimeer het bestand in-place als het groter is dan de drempel.

    Returns True als het bestand gecomprimeerd is, anders False.
    """
    try:
        if os.path.getsize(abs_path) <= COMPRESS_THRESHOLD_BYTES:
            return False
        _compress_in_place(abs_path)
        return True
    except (OSError, Exception):
        return False


def get_variant_urls(relative_path, widths=None, formats=('webp', 'jpg')):
    """Lever dict met srcset-klare variant-URLs.

    Returns dict:
        {
          'orig_url':     '/media/photos/blog/foto.jpg',
          'fallback_url': '/media/cache/photos/blog/foto_w800.jpg',
          'width': 800, 'height': 533,
          'sources': [
              {'format': 'image/webp', 'srcset': '... 400w, ... 800w, ...'},
              {'format': 'image/jpeg', 'srcset': '... 400w, ... 800w, ...'},
          ],
        }
    of None als bronbestand niet bestaat of een externe URL is.
    """
    if not relative_path:
        return None
    widths = widths or DEFAULT_WIDTHS

    # Externe of static URL — geen pipeline
    if relative_path.startswith(('http://', 'https://', '//', '/static/', 'static/')):
        return None

    # Strip leading '/media/'
    rel = relative_path.lstrip('/')
    if rel.startswith('media/'):
        rel = rel[len('media/'):]

    abs_src = os.path.join(settings.MEDIA_ROOT, rel)
    if not os.path.exists(abs_src):
        return None

    try:
        src_w, src_h = _get_image_size(abs_src)
    except Exception:
        return None

    # Geen upscaling
    target_widths = [w for w in widths if w <= src_w] or [src_w]

    sources = []
    for fmt in formats:
        urls = []
        for w in target_widths:
            variant_path = _ensure_variant(abs_src, rel, w, fmt)
            if variant_path:
                url = settings.MEDIA_URL + variant_path.replace(os.sep, '/')
                urls.append(f'{url} {w}w')
        if urls:
            mime = {'avif': 'image/avif', 'webp': 'image/webp'}.get(fmt, 'image/jpeg')
            sources.append({'format': mime, 'srcset': ', '.join(urls)})

    # Fallback: middelste breedte, jpg
    fallback_w = target_widths[len(target_widths) // 2]
    fallback_rel = _ensure_variant(abs_src, rel, fallback_w, 'jpg')
    fallback_url = (
        settings.MEDIA_URL + fallback_rel.replace(os.sep, '/')
        if fallback_rel
        else settings.MEDIA_URL + rel
    )

    ratio = src_h / src_w if src_w else 1
    return {
        'orig_url':     settings.MEDIA_URL + rel.replace(os.sep, '/'),
        'fallback_url': fallback_url,
        'width':        fallback_w,
        'height':       int(fallback_w * ratio),
        'sources':      sources,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Interne helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_image_size(path):
    from PIL import Image
    with Image.open(path) as img:
        return img.size  # (width, height)


def _ensure_variant(abs_src, rel_src, width, fmt):
    """Maak variant aan als die niet bestaat of verouderd is.
    Returns relatief pad t.o.v. MEDIA_ROOT, of '' bij fout.
    """
    base, _ = os.path.splitext(rel_src)
    ext = fmt if fmt in ('webp', 'avif') else 'jpg'
    variant_rel = os.path.join(CACHE_DIR, f'{base}_w{width}.{ext}')
    variant_abs = os.path.join(settings.MEDIA_ROOT, variant_rel)

    # Idempotent: skip als variant nieuwer dan origineel
    if os.path.exists(variant_abs):
        try:
            if os.path.getmtime(variant_abs) >= os.path.getmtime(abs_src):
                return variant_rel
        except OSError:
            pass

    os.makedirs(os.path.dirname(variant_abs), exist_ok=True)
    try:
        _render_variant(abs_src, variant_abs, width, fmt)
        return variant_rel
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            'Image-variant mislukt voor %s @%dw/%s: %s', rel_src, width, fmt, exc
        )
        return ''


def _render_variant(src_abs, dst_abs, target_width, fmt):
    """Resize + opslaan als JPEG of WebP."""
    from PIL import Image, ImageOps
    with Image.open(src_abs) as img:
        img = ImageOps.exif_transpose(img)
        if img.mode == 'P':
            img = img.convert('RGBA')
        elif img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGB')

        src_w, src_h = img.size
        if target_width < src_w:
            ratio = target_width / src_w
            img = img.resize((target_width, int(round(src_h * ratio))), Image.LANCZOS)

        if fmt == 'avif':
            # AVIF keeps an alpha channel; no white-matte needed.
            img.save(dst_abs, 'AVIF', quality=DEFAULT_AVIF_QUALITY, speed=AVIF_SPEED)
        elif fmt == 'webp':
            save_kw = {'quality': DEFAULT_WEBP_QUALITY, 'method': 4}
            if img.mode == 'RGBA':
                img.save(dst_abs, 'WEBP', **save_kw)
            else:
                img.convert('RGB').save(dst_abs, 'WEBP', **save_kw)
        else:
            if img.mode == 'RGBA':
                bg = Image.new('RGB', img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[3])
                img = bg
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(dst_abs, 'JPEG',
                     quality=DEFAULT_JPEG_QUALITY, optimize=True, progressive=True)


def _compress_in_place(path):
    """Resize naar max 2400px + JPEG q85, overschrijf origineel."""
    import shutil
    from PIL import Image, ImageOps
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)
        if img.mode == 'P':
            img = img.convert('RGBA')
        elif img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGB')
        w, h = img.size
        if w > COMPRESS_MAX_WIDTH:
            ratio = COMPRESS_MAX_WIDTH / w
            img = img.resize((COMPRESS_MAX_WIDTH, int(h * ratio)), Image.LANCZOS)
        if img.mode == 'RGBA':
            bg = Image.new('RGB', img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            img = bg
        tmp = path + '.tmp'
        img.save(tmp, 'JPEG', quality=COMPRESS_JPEG_QUALITY,
                 optimize=True, progressive=True)
        shutil.move(tmp, path)
