"""
PexelsPhotoMixin — admin widget to search Pexels and fill a model's photo fields.

Ported 1-on-1 from vliegtickets.com (test-claude-code/core/admin.py). Defaults
are aligned to this project's PhotoMixin field names (photo_url / photo_credit /
photo_pexels_id / photo_local / photo_alt + get_photo_url). Add the mixin to a
ModelAdmin and put 'pexels_widget' in readonly_fields.
"""

from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.urls import path
from django.utils.html import format_html
from django.utils.text import slugify

from core.services import pexels as pexels_service


class PexelsPhotoMixin:
    """Voegt een Pexels zoek-widget toe aan een ModelAdmin."""

    pexels_url_field = "photo_url"
    pexels_credit_field = "photo_credit"
    pexels_id_field = "photo_pexels_id"
    pexels_local_field = "photo_local"
    pexels_alt_field = "photo_alt"
    pexels_preview_fn = "get_photo_url"
    pexels_download_subdir = "photos/algemeen"
    pexels_filename_prefix = "foto"

    def get_urls(self):
        app = self.model._meta.app_label
        model = self.model._meta.model_name
        urls = super().get_urls()
        custom = [
            path("pexels-search/", self.admin_site.admin_view(self._pexels_search_view),
                 name=f"{app}_{model}_pexels_search"),
            path("pexels-download/", self.admin_site.admin_view(self._pexels_download_view),
                 name=f"{app}_{model}_pexels_download"),
        ]
        return custom + urls

    def _pexels_search_view(self, request):
        q = request.GET.get("q", "").strip()
        if not q:
            return JsonResponse({"photos": []})
        return JsonResponse({"photos": pexels_service.search_photos(q, per_page=12)})

    def _pexels_download_view(self, request):
        pexels_id = request.GET.get("pexels_id", "").strip()
        filename_hint = request.GET.get("filename_hint", "foto").strip()
        if not pexels_id:
            return JsonResponse({"success": False, "error": "Geen pexels_id opgegeven"})
        photo = pexels_service.get_photo(pexels_id)
        if not photo:
            return JsonResponse({"success": False, "error": "Foto niet gevonden op Pexels"})

        slug_hint = slugify(filename_hint)[:40] or "foto"
        filename = f"{self.pexels_filename_prefix}-{slug_hint}.jpg"
        save_dir = Path(settings.MEDIA_ROOT) / self.pexels_download_subdir
        local_path = pexels_service.download_photo(photo, save_dir, filename)
        if not local_path:
            return JsonResponse({"success": False, "error": "Download mislukt"})

        return JsonResponse({
            "success": True,
            "local_path": local_path,
            "media_url": settings.MEDIA_URL + local_path,
            "credit": pexels_service.build_credit(photo),
            "url": photo.get("large", ""),
        })

    def _get_pexels_preview_url(self, obj):
        if obj is None:
            return ""
        fn = getattr(obj, self.pexels_preview_fn, None)
        return (fn() or "") if callable(fn) else ""

    def pexels_widget(self, obj):
        app = self.model._meta.app_label
        model = self.model._meta.model_name
        search_url = f"/admin/{app}/{model}/pexels-search/"
        download_url = f"/admin/{app}/{model}/pexels-download/"
        preview_url = self._get_pexels_preview_url(obj)
        credit_text = getattr(obj, self.pexels_credit_field, "") if obj else ""

        current_html = (
            f'<img id="pexels-current-preview" src="{preview_url}" '
            f'style="max-width:100%;max-height:220px;border-radius:6px;margin-bottom:12px;'
            f'display:block;object-fit:cover">'
            if preview_url else '<img id="pexels-current-preview" style="display:none">'
        )
        credit_html = (
            f'<p style="font-size:12px;color:#666;margin:0 0 10px">{credit_text}</p>'
            if credit_text else ""
        )
        data_attrs = (
            f'data-search-url="{search_url}" data-download-url="{download_url}" '
            f'data-field-url="id_{self.pexels_url_field}" '
            f'data-field-credit="id_{self.pexels_credit_field}" '
            f'data-field-pexels-id="id_{self.pexels_id_field}" '
            f'data-field-local="id_{self.pexels_local_field}" '
            f'data-field-alt="{f"id_{self.pexels_alt_field}" if self.pexels_alt_field else ""}"'
        )

        return format_html(
            '''
            <div id="pexels-widget" {}>
                <h4 style="margin:0 0 10px;font-size:12px;color:#FF6B2C;
                           text-transform:uppercase;letter-spacing:.08em;font-weight:600">
                    📸 Pexels fotobibliotheek
                </h4>
                {}{}
                <div class="pexels-search-row">
                    <input type="text" id="pexels-query" placeholder="Zoek bijv. &quot;bestelbus gereedschap&quot;">
                    <button type="button" class="pexels-btn pexels-btn-search" onclick="pexelsSearch()">Zoeken</button>
                    <button type="button" class="pexels-btn pexels-btn-clear" onclick="pexelsClear()">✕ Wis foto</button>
                </div>
                <div id="pexels-loading" style="display:none;font-size:13px;color:#888">Zoeken…</div>
                <div id="pexels-results"></div>
                <div id="pexels-feedback"></div>
                <p class="pexels-attribution">
                    Foto&#39;s via <a href="https://www.pexels.com" target="_blank" rel="noopener">Pexels</a> —
                    gebruik vereist naamsvermelding van de fotograaf.
                </p>
            </div>
            ''',
            format_html(data_attrs), format_html(current_html), format_html(credit_html),
        )
    pexels_widget.short_description = "Pexels foto zoeken"

    class Media:
        css = {"all": ("admin/css/pexels_widget.css",)}
        js = ("admin/js/pexels_widget.js",)
