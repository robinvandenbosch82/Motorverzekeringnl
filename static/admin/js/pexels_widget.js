/* Pexels foto-zoekwidget voor Django admin — v2 */
(function () {
  'use strict';

  function init() {
    const widget = document.getElementById('pexels-widget');
    if (!widget) return;

    const searchUrl   = widget.dataset.searchUrl;
    const downloadUrl = widget.dataset.downloadUrl;
    const queryInput  = document.getElementById('pexels-query');
    const resultsEl   = document.getElementById('pexels-results');
    const loadingEl   = document.getElementById('pexels-loading');
    const previewImg  = document.getElementById('pexels-current-preview');

    // Form fields — resolved from data attributes
    function field(id) { return id ? document.getElementById(id) : null; }
    const fUrl      = field(widget.dataset.fieldUrl);
    const fCredit   = field(widget.dataset.fieldCredit);
    const fPexelsId = field(widget.dataset.fieldPexelsId);
    const fLocal    = field(widget.dataset.fieldLocal);
    const fAlt      = field(widget.dataset.fieldAlt);

    if (!searchUrl || !queryInput) return;

    // Tracking the currently selected photo
    let selectedPhoto = null;

    queryInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); doSearch(); }
    });

    window.pexelsSearch = doSearch;
    window.pexelsClear  = clearPhoto;

    function doSearch() {
      const q = queryInput.value.trim();
      if (!q) return;
      loadingEl.style.display = 'block';
      resultsEl.innerHTML = '';
      selectedPhoto = null;
      hideFeedback();

      fetch(searchUrl + '?q=' + encodeURIComponent(q))
        .then(r => r.json())
        .then(data => {
          loadingEl.style.display = 'none';
          renderResults(data.photos || []);
        })
        .catch(() => {
          loadingEl.style.display = 'none';
          resultsEl.innerHTML = '<p style="color:#c00;font-size:13px">Fout bij ophalen — controleer PEXELS_API_KEY</p>';
        });
    }

    function renderResults(photos) {
      if (!photos.length) {
        resultsEl.innerHTML = '<p style="color:#999;font-size:13px">Geen resultaten gevonden.</p>';
        return;
      }
      resultsEl.innerHTML = photos.map(function (p) {
        return (
          '<div class="pexels-thumb"' +
          ' data-id="'          + p.id + '"' +
          ' data-url="'         + escapeAttr(p.large) + '"' +
          ' data-thumb="'       + escapeAttr(p.thumb) + '"' +
          ' data-credit="'      + escapeAttr('Foto door ' + p.photographer + ' via Pexels') + '"' +
          ' data-alt="'         + escapeAttr(p.alt || p.photographer) + '"' +
          ' title="'            + escapeAttr(p.alt || p.photographer) + '">' +
          '<img src="'          + escapeAttr(p.thumb) + '" alt="' + escapeAttr(p.alt) + '" loading="lazy">' +
          '<span class="pexels-thumb-credit">' + escapeHtml(p.photographer) + '</span>' +
          '</div>'
        );
      }).join('');

      resultsEl.querySelectorAll('.pexels-thumb').forEach(function (el) {
        el.addEventListener('click', function () {
          selectedPhoto = {
            id:     el.dataset.id,
            url:    el.dataset.url,
            thumb:  el.dataset.thumb,
            credit: el.dataset.credit,
            alt:    el.dataset.alt,
          };
          resultsEl.querySelectorAll('.pexels-thumb').forEach(t => t.classList.remove('selected'));
          el.classList.add('selected');
          selectPhoto(selectedPhoto);
        });
      });
    }

    function selectPhoto(p) {
      // Fill URL field (external)
      if (fUrl)      fUrl.value      = p.url;
      if (fCredit)   fCredit.value   = p.credit;
      if (fPexelsId) fPexelsId.value = p.id;
      if (fAlt && !fAlt.value) fAlt.value = p.alt;

      // Clear local field — user chose external URL
      if (fLocal) fLocal.value = '';

      // Update preview
      if (previewImg) { previewImg.src = p.url; previewImg.style.display = 'block'; }

      showFeedback(
        '✓ Foto geselecteerd (externe URL ingevuld).' +
        (downloadUrl
          ? ' <button type="button" class="pexels-btn pexels-btn-download" onclick="pexelsDownload()" style="margin-left:10px">⬇ Download lokaal</button>'
          : '') +
        ' Klik <strong>Opslaan</strong> om te bewaren.',
        'info'
      );
    }

    window.pexelsDownload = function () {
      if (!selectedPhoto || !downloadUrl) return;
      showFeedback('⏳ Downloaden naar server…', 'info');

      // Pass a hint for the filename (use the alt text or query)
      const hint = (fAlt && fAlt.value) || queryInput.value || 'foto';
      const url  = downloadUrl + '?pexels_id=' + encodeURIComponent(selectedPhoto.id)
                               + '&filename_hint=' + encodeURIComponent(hint);

      fetch(url)
        .then(r => r.json())
        .then(data => {
          if (data.success) {
            if (fLocal)  fLocal.value  = data.local_path;
            if (fUrl)    fUrl.value    = '';        // clear external URL — local takes precedence
            if (fCredit) fCredit.value = data.credit;
            if (previewImg) { previewImg.src = data.media_url; previewImg.style.display = 'block'; }
            showFeedback('✅ Foto lokaal opgeslagen als <code>' + escapeHtml(data.local_path) + '</code>. Klik <strong>Opslaan</strong>.', 'success');
          } else {
            showFeedback('❌ Download mislukt: ' + escapeHtml(data.error || 'onbekende fout'), 'error');
          }
        })
        .catch(() => showFeedback('❌ Verbindingsfout bij downloaden.', 'error'));
    };

    function clearPhoto() {
      if (fUrl)      fUrl.value      = '';
      if (fCredit)   fCredit.value   = '';
      if (fPexelsId) fPexelsId.value = '';
      if (fLocal)    fLocal.value    = '';
      if (previewImg) { previewImg.src = ''; previewImg.style.display = 'none'; }
      selectedPhoto = null;
      resultsEl.innerHTML = '';
      hideFeedback();
    }

    function showFeedback(html, type) {
      const fb = document.getElementById('pexels-feedback');
      if (!fb) return;
      fb.innerHTML = html;
      fb.className = 'pexels-feedback-' + (type || 'info');
      fb.style.display = 'block';
    }

    function hideFeedback() {
      const fb = document.getElementById('pexels-feedback');
      if (fb) fb.style.display = 'none';
    }

    function escapeHtml(s)  { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
    function escapeAttr(s)  { return String(s).replace(/"/g,'&quot;'); }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
