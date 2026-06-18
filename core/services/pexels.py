"""
Pexels API service — foto's zoeken, ophalen en lokaal opslaan.
Documentatie: https://www.pexels.com/api/documentation/
"""

import logging
from pathlib import Path

import ssl
import certifi
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
from django.conf import settings


def _session() -> requests.Session:
    """
    Requests-sessie. Op Windows-dev omgevingen met corporate proxy/AV-interceptie
    falen standaard SSL-checks; we proberen certifi, dan verify=False als fallback.
    In productie (Linux) werkt standaard SSL gewoon.
    """
    s = requests.Session()
    # Probeer certifi; als dat ook mislukt doet de caller verify=False
    s.verify = certifi.where()
    return s

logger = logging.getLogger(__name__)

PEXELS_API_BASE = 'https://api.pexels.com/v1'
TIMEOUT = 15


def _get_api_key() -> str:
    """
    API-sleutel ophalen: SiteSettings (admin) heeft voorrang boven .env.
    """
    try:
        from core.models import SiteSettings
        key = SiteSettings.get().pexels_api_key
        if key:
            return key
    except Exception:
        pass
    return settings.PEXELS_API_KEY


def _headers() -> dict:
    return {'Authorization': _get_api_key()}


def search_photos(query: str, per_page: int = 15, page: int = 1, orientation: str = 'landscape') -> list[dict]:
    """
    Zoek foto's op Pexels. Geeft lijst met photo-dicts terug.
    Elke dict: {id, url, thumb, large, photographer, photographer_url, alt}
    """
    key = _get_api_key()
    if not key:
        logger.warning('Geen Pexels API-sleutel ingesteld (admin → Site-instellingen of .env PEXELS_API_KEY)')
        return []

    for verify in (certifi.where(), False):
        try:
            resp = requests.get(
                f'{PEXELS_API_BASE}/search',
                headers={'Authorization': key},
                params={
                    'query': query,
                    'per_page': per_page,
                    'page': page,
                    'orientation': orientation,
                },
                timeout=TIMEOUT,
                verify=verify,
            )
            resp.raise_for_status()
            return [_normalize(p) for p in resp.json().get('photos', [])]
        except requests.exceptions.SSLError:
            continue  # probeer volgende verify-optie
        except requests.RequestException as e:
            logger.error('Pexels search mislukt voor "%s": %s', query, e)
            return []
    logger.error('Pexels search mislukt voor "%s": SSL-fout ook met verify=False', query)
    return []


def get_photo(photo_id: int | str) -> dict | None:
    """Haal één foto op via ID."""
    key = _get_api_key()
    if not key:
        return None
    for verify in (certifi.where(), False):
        try:
            resp = requests.get(
                f'{PEXELS_API_BASE}/photos/{photo_id}',
                headers={'Authorization': key},
                timeout=TIMEOUT,
                verify=verify,
            )
            resp.raise_for_status()
            return _normalize(resp.json())
        except requests.exceptions.SSLError:
            continue
        except requests.RequestException as e:
            logger.error('Pexels get_photo(%s) mislukt: %s', photo_id, e)
            return None
    return None


def download_photo(photo: dict, save_dir: Path, filename: str) -> str | None:
    """
    Download een Pexels-foto en sla op als <save_dir>/<filename>.
    Geeft het relatieve media-pad terug (t.o.v. MEDIA_ROOT), bijv.
    'photos/landen/vliegtickets-naar-spanje.jpg', of None bij fout.
    """
    url = photo.get('large') or photo.get('url')
    if not url:
        return None

    try:
        resp = requests.get(url, timeout=30, stream=True, verify=False)
        resp.raise_for_status()

        save_dir.mkdir(parents=True, exist_ok=True)
        filepath = save_dir / filename

        with open(filepath, 'wb') as fh:
            for chunk in resp.iter_content(chunk_size=8192):
                fh.write(chunk)

        # Relatief pad t.o.v. MEDIA_ROOT
        media_root = Path(settings.MEDIA_ROOT)
        return str(filepath.relative_to(media_root)).replace('\\', '/')

    except (requests.RequestException, OSError) as e:
        logger.error('Download mislukt voor %s → %s: %s', url, filename, e)
        return None


def _normalize(p: dict) -> dict:
    """Normaliseert een Pexels photo-object naar ons formaat."""
    src = p.get('src', {})
    return {
        'id': str(p.get('id', '')),
        'url': src.get('large2x') or src.get('large') or src.get('original', ''),
        'thumb': src.get('medium') or src.get('small', ''),
        'large': src.get('large2x') or src.get('large', ''),
        'photographer': p.get('photographer', ''),
        'photographer_url': p.get('photographer_url', ''),
        'pexels_url': p.get('url', ''),
        'alt': p.get('alt', ''),
    }


def build_credit(photo: dict) -> str:
    """Geeft de vereiste Pexels-attributie-string terug."""
    return f"Foto door {photo['photographer']} via Pexels"
