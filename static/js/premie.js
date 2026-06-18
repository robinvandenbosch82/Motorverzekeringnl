/* Bestelautoverzekering.nl — premie-wizard.
   Drives the 4-step tool. All premium data comes from RISK via our own Django
   proxy endpoints; this script only collects input, calls those endpoints and
   renders the responses. No premium logic lives here. */
(function () {
  'use strict';
  var app = document.getElementById('premie-app');
  if (!app) return;

  var URLS = {
    voertuig: app.dataset.urlVoertuig,
    bereken: app.dataset.urlBereken,
    aanvullend: app.dataset.urlAanvullend,
    aanvraag: app.dataset.urlAanvraag,
  };
  var CSRF = (app.querySelector('[name=csrfmiddlewaretoken]') || {}).value || '';

  // Per-insurer editorial enrichment (score + kenmerken) from our CMS, keyed by
  // a normalised name. Adds our layer on top of RISK's premie/dekking data.
  var VZ = {};
  try { var _vzEl = document.getElementById('vz-data'); if (_vzEl) VZ = JSON.parse(_vzEl.textContent); } catch (e) {}
  function vzNorm(s) { return String(s || '').toLowerCase().replace(/[^a-z0-9]/g, ''); }
  function vzFor(name) {
    var n = vzNorm(name);
    if (!n) return null;
    if (VZ[n]) return VZ[n];
    var keys = Object.keys(VZ);
    for (var i = 0; i < keys.length; i++) {
      if (keys[i] && (n.indexOf(keys[i]) === 0 || keys[i].indexOf(n) === 0)) return VZ[keys[i]];
    }
    return null;
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  var VEHICLE_USE = {
    van: [['X', 'Vervoer van eigen goederen'], ['G', 'Vervoer van goederen'],
          ['D', 'Koerier / bezorgdienst'], ['Z', 'Overig zakelijk']],
    car: [['M', 'Particulier en zakelijk'], ['Z', 'Overig zakelijk']],
  };
  var COVERAGE = {
    '1': { title: 'WA', feats: ['Schade aan anderen'] },
    '2': { title: 'WA+', feats: ['Schade aan anderen', 'Brand & natuur', 'Diefstal & inbraak', 'Ruitschade'] },
    '3': { title: 'All Risk', feats: ['Schade aan anderen', 'Brand & natuur', 'Diefstal & inbraak', 'Ruitschade', 'Schade aan eigen bus', 'Vandalisme'] },
  };
  var ACCEPTANCE = [
    ['Cancelled', 'Werd u, of een andere belanghebbende, in de laatste acht jaar een verzekering opgezegd, geweigerd of aangeboden op beperkte en/of verzwarende voorwaarden?'],
    ['Convicted', 'Bent u, of een andere belanghebbende, in de laatste acht jaar in aanraking geweest met politie of justitie?'],
    ['Damage', 'Heeft u in de afgelopen vijf jaar meer dan één schade geleden?'],
    ['FinancialProblems', 'Bent u in de afgelopen acht jaar failliet verklaard of in een schuldsanering betrokken?'],
    ['Fraud', 'Bent u in de afgelopen acht jaar betrokken geweest bij verzekeringsfraude?'],
    ['Seizure', 'Heeft de deurwaarder op dit moment beslag gelegd op inkomsten of bezittingen?'],
    ['DisqualificationFromDriving', 'Werd u in de afgelopen acht jaar de rijbevoegdheid ontzegd?'],
  ];

  var state = {
    vehicle: null, isVan: false, segs: {},
    coverage: '3', paymentPeriod: '1',
    available: {}, results: [], selected: null,
    addons: [], selectedAddons: {},
  };

  /* ── utilities ─────────────────────────────────────────────── */
  function money(n) { return '€ ' + (Number(n) || 0).toFixed(2).replace('.', ','); }
  function $(sel, root) { return (root || app).querySelector(sel); }
  function $all(sel, root) { return Array.prototype.slice.call((root || app).querySelectorAll(sel)); }
  function show(el, on) { if (el) el.hidden = !on; }

  function post(url, body) {
    return fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body: JSON.stringify(body || {}),
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (data) {
        return { ok: r.ok, status: r.status, data: data };
      });
    });
  }

  function collectDetails() {
    var d = {};
    $all('[name]').forEach(function (el) {
      if (el.name === 'csrfmiddlewaretoken') return;
      if (el.type === 'checkbox') { d[el.name] = el.checked ? 'J' : ''; return; }
      if (el.value !== '') d[el.name] = el.value;
    });
    Object.keys(state.segs).forEach(function (k) { d[k] = state.segs[k]; });
    if (state.vehicle) d.LicensePlate = state.vehicle.LicensePlate || d.licensePlate;
    if (d.licensePlate) { d.LicensePlate = d.LicensePlate || d.licensePlate; delete d.licensePlate; }
    if (state.vehicle && state.vehicle.TheftProtectionClass) d.TheftProtectionClass = state.vehicle.TheftProtectionClass;
    d.Coverage = state.coverage;
    d.PaymentPeriod = state.paymentPeriod;
    d.CommencingDate = new Date().toISOString().split('T')[0];
    return d;
  }

  /* ── navigation ────────────────────────────────────────────── */
  function goStep(n) {
    $all('[data-panel]').forEach(function (p) { p.classList.toggle('is-active', p.dataset.panel === String(n)); });
    $all('[data-step-dot]').forEach(function (s) {
      var done = Number(s.dataset.stepDot) < n;
      s.classList.toggle('is-active', s.dataset.stepDot === String(n));
      s.classList.toggle('is-done', done);
    });
    window.scrollTo({ top: app.getBoundingClientRect().top + window.pageYOffset - 80, behavior: 'smooth' });
    if (n === 2) checkCoverages();
    if (n === 3) runComparison();
    if (n === 4) prepRequest();
  }

  /* ── segmented toggles ─────────────────────────────────────── */
  $all('[data-seg]').forEach(function (seg) {
    state.segs[seg.dataset.seg] = seg.dataset.default || '';
    seg.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-val]'); if (!btn) return;
      state.segs[seg.dataset.seg] = btn.dataset.val;
      $all('[data-val]', seg).forEach(function (b) { b.classList.toggle('is-on', b === btn); });
      if (seg.dataset.seg === 'DriverOne') toggleDriver(btn.dataset.val === 'J');
    });
  });
  function toggleDriver(on) {
    show($('[data-driver-block]'), on);
    show($('[data-driver-note]'), !on);
    var df = $('[data-driver-fields]'); if (df) df.style.display = on ? '' : 'none';
  }

  /* ── STEP 1 — kenteken lookup ──────────────────────────────── */
  function fillUseOptions(isVan) {
    var sel = $('[data-van-options]'); if (!sel) return;
    sel.innerHTML = '';
    (isVan ? VEHICLE_USE.van : VEHICLE_USE.car).forEach(function (o) {
      var opt = document.createElement('option');
      opt.value = o[0]; opt.textContent = o[1]; sel.appendChild(opt);
    });
  }
  $('[data-lookup]').addEventListener('click', function () {
    var plate = ($('#pl').value || '').toUpperCase().replace(/[-\s]/g, '');
    var out = $('[data-vehicle-out]'), err = $('[data-vehicle-err]');
    show(out, false); show(err, false);
    if (plate.length < 4) { err.textContent = 'Voer een geldig kenteken in.'; show(err, true); return; }
    this.disabled = true; this.textContent = '…';
    var self = this;
    post(URLS.voertuig, { licensePlate: plate }).then(function (res) {
      self.disabled = false; self.textContent = 'Zoek';
      if (!res.ok) { err.textContent = res.data.error || 'Kenteken niet gevonden.'; show(err, true); return; }
      state.vehicle = res.data; state.isVan = !!res.data.isVan;
      fillUseOptions(state.isVan);
      var v = res.data;
      out.textContent = '✓ ' + [v.Brand, v.Model, v.ManufacturingYear].filter(Boolean).join(' ') +
                        (state.isVan ? ' · bestelauto' : ' · personenauto');
      show(out, true);
    });
  });
  $('#pl').addEventListener('input', function () { this.value = this.value.toUpperCase().slice(0, 9); });

  /* ── STEP 2 — coverage availability ────────────────────────── */
  function checkCoverages() {
    var list = $('[data-coverage-list]'), err = $('[data-coverage-err]');
    show(err, false);
    list.innerHTML = '<p class="wz-sub">Beschikbaarheid controleren…</p>';
    var base = collectDetails();
    Promise.all(['1', '2', '3'].map(function (cov) {
      return post(URLS.bereken, { details: Object.assign({}, base, { Coverage: cov }), isVan: state.isVan })
        .then(function (res) { return { cov: cov, results: (res.ok && res.data.results) || [] }; });
    })).then(function (all) {
      list.innerHTML = '';
      var any = false;
      all.forEach(function (r) {
        state.available[r.cov] = r.results;
        if (!r.results.length) return;
        any = true;
        var cheapest = r.results.reduce(function (m, x) { return x.Premium < m ? x.Premium : m; }, Infinity);
        var c = COVERAGE[r.cov];
        var card = document.createElement('button');
        card.type = 'button';
        card.className = 'wz-cover__card' + (r.cov === '3' ? ' is-rec' : '');
        card.dataset.cov = r.cov;
        card.innerHTML =
          (r.cov === '3' ? '<span class="wz-cover__badge">Ons advies</span>' : '') +
          '<div class="wz-cover__title">' + c.title + '</div>' +
          '<div class="wz-cover__price">v.a. ' + money(cheapest) + '<span>/mnd</span></div>' +
          '<ul class="wz-cover__feats">' + c.feats.map(function (f) { return '<li>✓ ' + f + '</li>'; }).join('') + '</ul>';
        card.addEventListener('click', function () { selectCoverage(r.cov); });
        list.appendChild(card);
      });
      if (!any) { err.textContent = 'Er zijn helaas geen verzekeringen beschikbaar voor dit voertuig. Neem contact met ons op.'; show(err, true); }
      else { selectCoverage(state.available['3'] && state.available['3'].length ? '3' : Object.keys(state.available).find(function (k) { return state.available[k].length; })); }
    });
  }
  function selectCoverage(cov) {
    if (!cov) return;
    state.coverage = cov;
    $all('[data-cov]').forEach(function (c) { c.classList.toggle('is-sel', c.dataset.cov === cov); });
    var btn = $('[data-need-coverage]'); if (btn) btn.disabled = false;
    var group = $('[data-filter-pills="Coverage"]');
    if (group) $all('[data-val]', group).forEach(function (b) { b.classList.toggle('is-on', b.dataset.val === cov); });
  }

  /* ── STEP 3 — comparison ───────────────────────────────────── */
  var compToken = 0;
  function runComparison() {
    var box = $('[data-results]');
    box.innerHTML = '<p class="wz-sub">Premies ophalen…</p>';
    show($('[data-addons]'), false);
    state.selected = null; $('[data-need-selection]').hidden = true;
    var my = ++compToken;
    post(URLS.bereken, { details: collectDetails(), isVan: state.isVan }).then(function (res) {
      if (my !== compToken) return;
      if (!res.ok) { box.innerHTML = '<p class="wz-error">' + (res.data.error || 'Er ging iets mis.') + '</p>'; return; }
      state.results = res.data.results || [];
      renderResults();
    });
  }
  function eigenRisico(r) {
    if (r.CascoDeductables) return '€ ' + r.CascoDeductables;
    return String(r.Coverage) === '1' ? 'n.v.t. (WA)' : '€ 0';
  }

  function ratingBar(label, score, isAvg) {
    var num = parseFloat(String(score).replace(',', '.')) || 0;
    var pct = Math.max(0, Math.min(100, num * 10));
    return '<div class="wz-rate' + (isAvg ? ' wz-rate--avg' : '') + '">' +
      '<span class="wz-rate__l">' + esc(label) + '</span>' +
      '<span class="wz-rate__bar"><i style="width:' + pct + '%"></i></span>' +
      '<span class="wz-rate__s">' + esc(score) + '</span></div>';
  }

  function buildDetails(r, vz) {
    var per = state.paymentPeriod === '12' ? 'per jaar' : 'per maand';

    // ── Premie-opbouw (RISK) ──
    var rows = [];
    if (r.NetPremium) rows.push(['Nettopremie', money(r.NetPremium)]);
    if (r.Taxes) rows.push(['Assurantiebelasting (21%)', money(r.Taxes)]);
    if (r.TotalCosts) rows.push(['Eenmalige poliskosten', money(r.TotalCosts)]);
    rows.push(['Totaal ' + per, money(r.Premium)]);
    var cost = '<div class="wz-ins__dh">Premie-opbouw</div>' + rows.map(function (x) {
      return '<div class="wz-dl"><span>' + x[0] + '</span><strong>' + x[1] + '</strong></div>';
    }).join('');

    // ── Omschrijving + kenmerken (ons CMS) ──
    var desc = (vz && vz.omschrijving)
      ? '<div class="wz-ins__dh">Over ' + esc(vz.naam) + '</div><p class="wz-ins__desc">' + esc(vz.omschrijving) + '</p>'
      : '';
    var kenm = '';
    if (vz && vz.kenmerken && vz.kenmerken.length) {
      kenm = '<div class="wz-ins__dh">Kenmerken</div><div class="wz-ins__kenm">' +
        vz.kenmerken.map(function (k) { return '<div class="wz-kv"><span>' + esc(k[0]) + '</span><strong>' + esc(k[1]) + '</strong></div>'; }).join('') +
        '</div>';
    }

    // ── Beoordeling (ons CMS) ──
    var beo = '';
    if (vz && vz.beoordeling && vz.beoordeling.length) {
      var nums = vz.beoordeling.map(function (b) { return parseFloat(String(b[1]).replace(',', '.')) || 0; });
      var avg = nums.reduce(function (a, b) { return a + b; }, 0) / nums.length;
      var avgStr = avg.toFixed(1).replace('.', ',');
      beo = '<div class="wz-ins__dh">Beoordeling</div>' +
        vz.beoordeling.map(function (b) { return ratingBar(b[0], b[1], false); }).join('') +
        ratingBar('Gemiddelde', avgStr, true) +
        (vz.reviewCount ? '<div class="wz-ins__reviews">Op basis van ' + esc(vz.reviewCount) + ' reviews</div>' : '');
    }

    // ── Dekking & voorwaarden (RISK) ──
    var dek = '<div class="wz-ins__dh">Dekking &amp; voorwaarden</div>' +
      '<ul class="wz-ins__feats wz-ins__feats--full">' +
        (r.LegalLiabilityDescription ? '<li>' + esc(r.LegalLiabilityDescription) + '</li>' : '') +
        (r.CascoDescription ? '<li>' + esc(r.CascoDescription) + '</li>' : '') +
        '<li>Eigen risico: ' + esc(eigenRisico(r)) + '</li>' + '</ul>';
    if (r.Conditions && r.Conditions.length) {
      dek += '<div class="wz-ins__docs">' + r.Conditions.map(function (c) {
        return c.URL ? '<a href="' + esc(c.URL) + '" target="_blank" rel="noopener">' +
          esc(c.Description || 'Polisvoorwaarden') + ' ↗</a>' : '';
      }).join('') + '</div>';
    }

    var tags = (vz && vz.tags && vz.tags.length)
      ? '<div class="wz-ins__tags">' + vz.tags.map(function (t) { return '<span class="tag">' + esc(t) + '</span>'; }).join('') + '</div>'
      : '';

    // ── Tabbed disclosure: Samenvatting (default) · Beoordeling · Voorwaarden ──
    var samenvatting = '<div class="wz-ins__detgrid">' +
        '<div>' + (desc || '<div class="wz-ins__dh">Samenvatting</div><p class="wz-ins__desc">Premie en dekking voor jouw bestelauto.</p>') + kenm + '</div>' +
        '<div>' + cost + '</div>' +
      '</div>';
    var voorwaarden = dek + tags;

    var tabs = '<div class="wz-tabs">' +
        '<button type="button" class="wz-tab is-on" data-tab="sam">Samenvatting</button>' +
        (beo ? '<button type="button" class="wz-tab" data-tab="beo">Beoordeling</button>' : '') +
        '<button type="button" class="wz-tab" data-tab="vw">Voorwaarden</button>' +
      '</div>';
    return tabs +
      '<div class="wz-tabpane is-on" data-pane="sam">' + samenvatting + '</div>' +
      (beo ? '<div class="wz-tabpane" data-pane="beo">' + beo + '</div>' : '') +
      '<div class="wz-tabpane" data-pane="vw">' + voorwaarden + '</div>';
  }

  function buildCard(r, cheapest) {
    var per = state.paymentPeriod === '12' ? 'per jaar' : 'per maand';
    var cov = COVERAGE[String(r.Coverage)] || COVERAGE[state.coverage] || { title: '', feats: [] };
    var vz = vzFor(r.CompanyName);
    var sel = state.selected && state.selected.Identifier === r.Identifier;
    var feats = [];
    if (r.LegalLiabilityDescription) feats.push(r.LegalLiabilityDescription);
    if (r.CascoDescription) feats.push(r.CascoDescription);
    if (!feats.length) feats = cov.feats || [];

    var badge = cheapest ? '<span class="wz-ins__rank">Goedkoopste</span>'
      : (String(r.Coverage) === '3' ? '<span class="wz-ins__rank wz-ins__rank--advies">Ons advies</span>' : '');

    var card = document.createElement('div');
    card.className = 'wz-ins' + (sel ? ' is-sel' : '');
    card.innerHTML = badge +
      '<div class="wz-ins__top">' +
        '<div class="wz-ins__brand">' +
          (r.CompanyLogoUrl ? '<img class="wz-ins__logo" src="' + esc(r.CompanyLogoUrl) + '" alt="' + esc(r.CompanyName) + '">'
                            : '<span class="wz-ins__name">' + esc(r.CompanyName || 'Verzekeraar') + '</span>') +
          (vz && vz.score ? '<div class="wz-ins__rating"><span class="wz-star">★</span> ' + esc(vz.score) + '<span> / 10</span></div>' : '') +
        '</div>' +
        '<div class="wz-ins__mid">' +
          '<span class="wz-ins__cov">' + esc(cov.title) + '</span>' +
          '<ul class="wz-ins__feats">' +
            feats.slice(0, 3).map(function (f) { return '<li>' + esc(f) + '</li>'; }).join('') +
            '<li class="wz-ins__er">Eigen risico: <strong>' + esc(eigenRisico(r)) + '</strong></li>' +
          '</ul>' +
        '</div>' +
        '<div class="wz-ins__pricecol">' +
          '<div class="wz-ins__amount">' + money(r.Premium) + '</div>' +
          '<div class="wz-ins__per">' + per + ' · incl. 21% bel.</div>' +
          '<button type="button" class="btn btn--primary btn--block" data-pick>' + (sel ? 'Gekozen ✓' : 'Kies') + '</button>' +
        '</div>' +
      '</div>' +
      '<button type="button" class="wz-ins__more" data-more aria-expanded="false">Meer informatie <span>▾</span></button>' +
      '<div class="wz-ins__details" hidden>' + buildDetails(r, vz) + '</div>';

    card.querySelector('[data-pick]').addEventListener('click', function () { pickInsurer(r); });
    card.querySelector('[data-more]').addEventListener('click', function () {
      var det = card.querySelector('.wz-ins__details');
      var open = det.hidden;
      det.hidden = !open;
      this.setAttribute('aria-expanded', open ? 'true' : 'false');
      this.classList.toggle('is-open', open);
      this.firstChild.nodeValue = open ? 'Minder informatie ' : 'Meer informatie ';
    });
    $all('.wz-tab', card).forEach(function (tab) {
      tab.addEventListener('click', function () {
        var name = tab.getAttribute('data-tab');
        $all('.wz-tab', card).forEach(function (t) { t.classList.toggle('is-on', t === tab); });
        $all('.wz-tabpane', card).forEach(function (p) { p.classList.toggle('is-on', p.getAttribute('data-pane') === name); });
      });
    });
    return card;
  }

  function renderResults() {
    var box = $('[data-results]');
    if (!state.results.length) {
      box.innerHTML = '<p class="wz-sub">Geen premies gevonden voor deze gegevens. Controleer je postcode, huisnummer en KvK-nummer, of probeer een andere dekking (bijv. WA).</p>';
      $('[data-results-count]') && ($('[data-results-count]').textContent = '');
      return;
    }
    var sort = $('[data-sort]').value;
    var list = state.results.slice().sort(function (a, b) {
      return sort === 'name' ? String(a.CompanyName).localeCompare(b.CompanyName) : a.Premium - b.Premium;
    });
    var cheapestId = state.results.reduce(function (m, x) { return x.Premium < m.Premium ? x : m; }).Identifier;
    var countEl = $('[data-results-count]');
    if (countEl) countEl.textContent = list.length + (list.length === 1 ? ' verzekeraar' : ' verzekeraars');
    box.innerHTML = '';
    list.forEach(function (r) { box.appendChild(buildCard(r, r.Identifier === cheapestId)); });
  }
  function pickInsurer(r) {
    state.selected = r; state.selectedAddons = {};
    renderResults();
    var addons = $('[data-addons]'); show(addons, true);
    $('[data-addons-list]').innerHTML = '<p class="wz-sub">Aanvullende dekkingen ophalen…</p>';
    post(URLS.aanvullend, { details: collectDetails(), identifier: r.Identifier, isVan: state.isVan }).then(function (res) {
      state.addons = (res.ok && res.data.coverages) || [];
      renderAddons();
    });
    $('[data-need-selection]').hidden = false;
    updateTotal();
  }
  function renderAddons() {
    var box = $('[data-addons-list]');
    if (!state.addons.length) { box.innerHTML = '<p class="wz-sub">Geen aanvullende dekkingen beschikbaar.</p>'; return; }
    box.innerHTML = '';
    state.addons.forEach(function (a, i) {
      var row = document.createElement('label');
      row.className = 'wz-addon';
      row.innerHTML = '<input type="checkbox" data-addon="' + i + '">' +
        '<span class="wz-addon__txt">' + (a.Description || a.Type) + '</span>' +
        '<span class="wz-addon__price">+ ' + money(a.Premium) + '</span>';
      row.querySelector('input').addEventListener('change', function () {
        if (this.checked) state.selectedAddons[i] = a; else delete state.selectedAddons[i];
        updateTotal();
      });
      box.appendChild(row);
    });
  }
  function updateTotal() {
    var base = state.selected ? Number(state.selected.Premium) || 0 : 0;
    var add = Object.keys(state.selectedAddons).reduce(function (s, k) { return s + (Number(state.selectedAddons[k].Premium) || 0); }, 0);
    $('[data-total]').textContent = money(base + add);
  }
  $all('[data-filter-pills]').forEach(function (group) {
    group.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-val]'); if (!btn) return;
      $all('[data-val]', group).forEach(function (b) { b.classList.toggle('is-on', b === btn); });
      if (group.getAttribute('data-filter-pills') === 'Coverage') state.coverage = btn.dataset.val;
      else state.paymentPeriod = btn.dataset.val;
      runComparison();
    });
  });
  $('[data-sort]').addEventListener('change', renderResults);

  /* ── STEP 4 — request ──────────────────────────────────────── */
  function prepRequest() {
    var box = $('[data-acceptance]');
    if (!box.dataset.built) {
      ACCEPTANCE.forEach(function (q) {
        var f = document.createElement('div');
        f.className = 'wz-field';
        f.innerHTML = '<label>' + q[1] + '</label><textarea name="' + q[0] + '" rows="2" placeholder="Laat leeg als niet van toepassing"></textarea>';
        box.appendChild(f);
      });
      box.dataset.built = '1';
    }
    toggleDriver(state.segs.DriverOne === 'J');
  }
  $('[data-submit-request]').addEventListener('click', function () {
    var err = $('[data-request-err]'); show(err, false);
    if (!state.selected) { err.textContent = 'Kies eerst een verzekeraar.'; show(err, true); goStep(3); return; }
    if (!$('[data-agreement]').checked) { err.textContent = 'Je moet akkoord gaan met de slotverklaring.'; show(err, true); return; }
    var payload = collectDetails();
    payload.selectedIdentifier = state.selected.Identifier;
    payload.Identifier = state.selected.Identifier;
    payload.Agreement = 'J';
    payload.additionalCoverages = Object.keys(state.selectedAddons).map(function (k) {
      return { Type: state.selectedAddons[k].Type, Identifier: state.selectedAddons[k].Identifier };
    });
    var btn = this; btn.disabled = true; btn.textContent = 'Versturen…';
    post(URLS.aanvraag, { data: payload, isVan: state.isVan }).then(function (res) {
      btn.disabled = false; btn.textContent = 'Verzekering aanvragen';
      if (!res.ok) { err.textContent = res.data.error || 'Het afsluiten is niet gelukt.'; show(err, true); return; }
      $('[data-policy]').textContent = res.data.PolicyNumber || '—';
      show($('[data-request-form]'), false);
      show($('[data-confirmation]'), true);
      window.scrollTo({ top: app.getBoundingClientRect().top + window.pageYOffset - 80, behavior: 'smooth' });
    });
  });

  /* ── Step 1 validation (prevent the confusing "geen aanbod") ── */
  function validateStep1() {
    var bad = [];
    if (($('#kvk').value || '').replace(/\D/g, '').length !== 8) bad.push('#kvk');
    if (!($('#cfy').value || '').trim()) bad.push('#cfy');
    if (state.segs.DriverOne === 'J') {
      if (!($('#zip').value || '').trim()) bad.push('#zip');
      if (!($('#hn').value || '').trim()) bad.push('#hn');
      if (!($('#bd').value || '').trim()) bad.push('#bd');
    }
    return bad;
  }
  // Clear the red marking as soon as the user edits a marked field.
  ['#kvk', '#cfy', '#zip', '#hn', '#bd'].forEach(function (sel) {
    var el = $(sel);
    if (el) el.addEventListener('input', function () { el.classList.remove('is-invalid'); });
  });

  /* ── wire next/prev + initial state ────────────────────────── */
  $all('[data-next]').forEach(function (b) {
    b.addEventListener('click', function () {
      if (b.hasAttribute('data-need-vehicle') && !state.vehicle) {
        var err = $('[data-vehicle-err]'); err.textContent = 'Zoek eerst je kenteken op.'; show(err, true); return;
      }
      if (b.dataset.next === '2') {
        var bad = validateStep1();
        $all('.is-invalid').forEach(function (e) { e.classList.remove('is-invalid'); });
        var err1 = $('[data-step1-err]');
        if (bad.length) {
          bad.forEach(function (sel) { var e = $(sel); if (e) e.classList.add('is-invalid'); });
          err1.textContent = 'Vul de gemarkeerde velden in om verder te gaan.';
          show(err1, true);
          var first = $(bad[0]); if (first) { first.focus(); }
          return;
        }
        show(err1, false);
      }
      goStep(Number(b.dataset.next));
    });
  });
  $all('[data-prev]').forEach(function (b) { b.addEventListener('click', function () { goStep(Number(b.dataset.prev)); }); });
  $('[data-need-coverage]').disabled = true;
  fillUseOptions(true);
  toggleDriver(true);

  /* Prefill + auto-lookup when arriving from a teaser with ?kenteken=XXX. */
  (function () {
    var m = /[?&]kenteken=([^&]+)/.exec(window.location.search);
    if (!m) return;
    var plate = decodeURIComponent(m[1]).toUpperCase().replace(/[-\s]/g, '').slice(0, 9);
    if (plate.length < 4) return;
    $('#pl').value = plate;
    $('[data-lookup]').click();
  })();
})();
