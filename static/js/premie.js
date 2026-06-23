/* Motorverzekering.nl — premie-wizard (particulier, RISK V9).
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

  var VZ = {};
  try { var _vzEl = document.getElementById('vz-data'); if (_vzEl) VZ = JSON.parse(_vzEl.textContent); } catch (e) {}
  function vzNorm(s) { return String(s || '').toLowerCase().replace(/[^a-z0-9]/g, ''); }
  function vzFor(name) {
    var n = vzNorm(name); if (!n) return null;
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

  var COVERAGE = {
    '1': { title: 'WA', feats: ['Schade aan anderen', 'Inclusief groene kaart'] },
    '2': { title: 'WA + Casco', feats: ['Schade aan anderen', 'Diefstal & brand', 'Ruitschade', 'Storm & natuur'] },
    '3': { title: 'Allrisk', feats: ['Schade aan anderen', 'Diefstal & brand', 'Ruitschade', 'Schade aan eigen motor', 'Nieuwwaarderegeling'] },
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
    vehicle: null, segs: {}, coverage: '2', paymentPeriod: '1',
    available: {}, results: [], selected: null, addons: [], selectedAddons: {},
  };

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
    if (state.vehicle && state.vehicle.LicensePlate) d.LicensePlate = state.vehicle.LicensePlate;
    if (d.licensePlate) { d.LicensePlate = d.LicensePlate || d.licensePlate; delete d.licensePlate; }
    if (state.vehicle && state.vehicle.MotorSignCode && !d.CarSignCode) d.CarSignCode = state.vehicle.MotorSignCode;
    d.Coverage = state.coverage;
    d.PaymentPeriod = state.paymentPeriod;
    d.CommencingDate = new Date().toISOString().split('T')[0];
    // Verzekeringnemer = regelmatige bestuurder (zelfde persoon).
    if (d.Name) d.DriverName = d.Name;
    if (d.Initials) d.DriverInitials = d.Initials;
    if (d.NameInfix) d.DriverNameInfix = d.NameInfix;
    if (d.Gender) d.DriverGender = d.Gender;
    if (d.DriverZipCode) d.ZipCode = d.DriverZipCode;
    if (d.DriverHouseNumber) d.HouseNumber = d.DriverHouseNumber;
    if (d.DriverHouseNumberAddition) d.HouseNumberAddition = d.DriverHouseNumberAddition;
    if (d.DriverBirthdate) d.Birthdate = d.DriverBirthdate;
    return d;
  }

  /* ── navigation ── */
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

  /* ── segmented toggles ── */
  $all('[data-seg]').forEach(function (seg) {
    state.segs[seg.dataset.seg] = seg.dataset.default || '';
    seg.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-val]'); if (!btn) return;
      state.segs[seg.dataset.seg] = btn.dataset.val;
      $all('[data-val]', seg).forEach(function (b) { b.classList.toggle('is-on', b === btn); });
    });
  });

  /* ── STEP 1 — kenteken lookup ── */
  var lookupBtn = $('[data-lookup]');
  lookupBtn.addEventListener('click', function () {
    var plate = ($('#pl').value || '').toUpperCase().replace(/[-\s]/g, '');
    var out = $('[data-vehicle-out]'), err = $('[data-vehicle-err]');
    show(out, false); show(err, false);
    if (plate.length < 4) { err.textContent = 'Voer een geldig kenteken in.'; show(err, true); return; }
    this.disabled = true; this.textContent = '…';
    var self = this;
    post(URLS.voertuig, { licensePlate: plate }).then(function (res) {
      self.disabled = false; self.textContent = 'Zoek';
      if (!res.ok) { err.textContent = res.data.error || 'Kenteken niet gevonden.'; show(err, true); return; }
      var v = res.data; state.vehicle = v;
      out.textContent = [v.Brand, v.Model, v.Type].filter(Boolean).join(' ') +
        (v.CylinderCapacity ? ' · ' + v.CylinderCapacity + ' cc' : '') +
        (v.ManufacturingYear ? ' · ' + v.ManufacturingYear : '');
      show(out, true);
      if (v.Coverage && COVERAGE[String(v.Coverage)]) state.coverage = String(v.Coverage);
      if (v.MotorSignCode) { var msc = $('#msc'); if (msc && !msc.value) msc.value = v.MotorSignCode; }
    });
  });
  $('#pl').addEventListener('input', function () { this.value = this.value.toUpperCase().slice(0, 9); });

  /* ── STEP 2 — coverage availability + conditional inputs ── */
  function toggleConditionals(cov) {
    show($('[data-cond="dayvalue"]'), cov === '2');
    show($('[data-cond="accessories"]'), cov === '2' || cov === '3');
    show($('[data-cond="helm"]'), cov === '3');
  }
  function checkCoverages() {
    var list = $('[data-coverage-list]'), err = $('[data-coverage-err]');
    show(err, false);
    list.innerHTML = '<p class="wz-sub">Beschikbaarheid controleren…</p>';
    var base = collectDetails();
    Promise.all(['1', '2', '3'].map(function (cov) {
      var probe = Object.assign({}, base, { Coverage: cov });
      // Casco/Allrisk-probe heeft een dagwaarde nodig; pak die van het voertuig als
      // de bezoeker er nog geen invulde, anders valt Casco ('Meest gekozen') weg.
      if (cov !== '1' && !probe.DayValue && state.vehicle && state.vehicle.DayValue) {
        probe.DayValue = state.vehicle.DayValue;
      }
      return post(URLS.bereken, { details: probe })
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
        card.className = 'wz-cover__card' + (r.cov === '2' ? ' is-rec' : '');
        card.dataset.cov = r.cov;
        card.innerHTML =
          (r.cov === '2' ? '<span class="wz-cover__badge">Meest gekozen</span>' : '') +
          '<div class="wz-cover__title">' + c.title + '</div>' +
          '<div class="wz-cover__price">v.a. ' + money(cheapest) + '<span>/mnd</span></div>' +
          '<ul class="wz-cover__feats">' + c.feats.map(function (f) { return '<li>✓ ' + f + '</li>'; }).join('') + '</ul>';
        card.addEventListener('click', function () { selectCoverage(r.cov); });
        list.appendChild(card);
      });
      if (!any) { err.textContent = 'Er zijn helaas geen verzekeringen beschikbaar voor deze gegevens. Controleer je postcode en geboortedatum.'; show(err, true); }
      else {
        var pref = (state.available[state.coverage] && state.available[state.coverage].length) ? state.coverage
          : Object.keys(state.available).find(function (k) { return state.available[k].length; });
        selectCoverage(pref);
      }
    });
  }
  function selectCoverage(cov) {
    if (!cov) return;
    state.coverage = cov;
    $all('[data-cov]').forEach(function (c) { c.classList.toggle('is-sel', c.dataset.cov === cov); });
    var btn = $('[data-need-coverage]'); if (btn) btn.disabled = false;
    toggleConditionals(cov);
  }

  /* ── STEP 3 — comparison ── */
  var compToken = 0;
  function runComparison() {
    var box = $('[data-results]');
    box.innerHTML = '<p class="wz-sub">Premies ophalen…</p>';
    show($('[data-addons]'), false);
    state.selected = null; $('[data-need-selection]').hidden = true;
    var my = ++compToken;
    post(URLS.bereken, { details: collectDetails() }).then(function (res) {
      if (my !== compToken) return;
      if (!res.ok) { box.innerHTML = '<p class="wz-error">' + (res.data.error || 'Er ging iets mis.') + '</p>'; return; }
      state.results = res.data.results || [];
      renderResults();
    });
  }
  function buildDetails(r, vz) {
    var per = state.paymentPeriod === '12' ? 'per jaar' : 'per maand';
    var rows = [];
    if (r.NetPremium) rows.push(['Nettopremie', money(r.NetPremium)]);
    if (r.Taxes) rows.push(['Assurantiebelasting', money(r.Taxes)]);
    if (r.TotalCosts) rows.push(['Poliskosten', money(r.TotalCosts)]);
    rows.push(['Totaal ' + per, money(r.Premium)]);
    var cost = '<div class="wz-ins__dh">Premie-opbouw</div>' + rows.map(function (x) {
      return '<div class="wz-dl"><span>' + x[0] + '</span><strong>' + x[1] + '</strong></div>';
    }).join('');
    var desc = (vz && vz.omschrijving)
      ? '<div class="wz-ins__dh">Over ' + esc(vz.naam) + '</div><p style="font-size:14px;color:#5C5E54;line-height:1.55;margin:0">' + esc(vz.omschrijving) + '</p>' : '';
    // RISK levert polisvoorwaarden (ConditionUrls) + verzekeringskaart
    // (InsuranceCards), beide als arrays van {URL, Description}.
    var docLinks = [].concat(r.ConditionUrls || [], r.InsuranceCards || [])
      .filter(function (c) { return c && c.URL; });
    var docs = docLinks.length
      ? '<div class="wz-ins__docs">' + docLinks.map(function (c) {
          return '<a href="' + esc(c.URL) + '" target="_blank" rel="noopener">' +
            esc(c.Description || 'Voorwaarden') + ' ↗</a>';
        }).join('') + '</div>'
      : '';
    return desc + cost + docs;
  }
  function buildCard(r, cheapest) {
    var per = state.paymentPeriod === '12' ? 'per jaar' : 'per maand';
    var cov = COVERAGE[String(r.Coverage)] || COVERAGE[state.coverage] || { title: '', feats: [] };
    var vz = vzFor(r.CompanyName);
    var sel = state.selected && state.selected.Identifier === r.Identifier;
    var badge = cheapest ? '<span class="wz-ins__rank">Goedkoopste</span>' : '';
    var card = document.createElement('div');
    card.className = 'wz-ins' + (sel ? ' is-sel' : '');
    card.innerHTML = badge +
      '<div class="wz-ins__top">' +
        '<div class="wz-ins__brand">' +
          (r.CompanyLogoUrl ? '<img class="wz-ins__logo" src="' + esc(r.CompanyLogoUrl) + '" alt="' + esc(r.CompanyName) + '">'
                            : '<span class="wz-ins__name">' + esc(r.CompanyName || r.ProductDescription || 'Verzekeraar') + '</span>') +
          (vz && vz.score ? '<div class="wz-ins__rating"><span class="wz-star">★</span> ' + esc(vz.score) + ' / 10</div>' : '') +
        '</div>' +
        '<div class="wz-ins__mid">' +
          '<span class="wz-ins__cov">' + esc(cov.title) + '</span>' +
          '<ul class="wz-ins__feats">' + cov.feats.slice(0, 3).map(function (f) { return '<li>✓ ' + esc(f) + '</li>'; }).join('') + '</ul>' +
        '</div>' +
        '<div class="wz-ins__pricecol">' +
          '<div class="wz-ins__amount">' + money(r.Premium) + '</div>' +
          '<div class="wz-ins__per">' + per + ' · incl. belasting</div>' +
          '<button type="button" class="mv-btn-indigo" style="width:100%;justify-content:center;border:0;cursor:pointer;padding:11px" data-pick>' + (sel ? 'Gekozen ✓' : 'Kies') + '</button>' +
        '</div>' +
      '</div>' +
      '<button type="button" class="wz-ins__more" data-more>Meer informatie ▾</button>' +
      '<div class="wz-ins__details" hidden>' + buildDetails(r, vz) + '</div>';
    card.querySelector('[data-pick]').addEventListener('click', function () { pickInsurer(r); });
    card.querySelector('[data-more]').addEventListener('click', function () {
      var det = card.querySelector('.wz-ins__details');
      det.hidden = !det.hidden;
      this.textContent = det.hidden ? 'Meer informatie ▾' : 'Minder informatie ▴';
    });
    return card;
  }
  function renderResults() {
    var box = $('[data-results]');
    if (!state.results.length) {
      box.innerHTML = '<p class="wz-sub">Geen premies gevonden voor deze gegevens. Controleer je postcode en geboortedatum, of kies een andere dekking.</p>';
      var ce = $('[data-results-count]'); if (ce) ce.textContent = '';
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
    show($('[data-addons]'), true);
    $('[data-addons-list]').innerHTML = '<p class="wz-sub">Aanvullende dekkingen ophalen…</p>';
    post(URLS.aanvullend, { details: collectDetails(), identifier: r.Identifier }).then(function (res) {
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
      row.innerHTML = '<input type="checkbox" data-addon="' + i + '"><span class="wz-addon__txt">' +
        esc(a.Description || a.Type) + '</span><span class="wz-addon__price">+ ' + money(a.Premium) + '</span>';
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
      state.paymentPeriod = btn.dataset.val;
      runComparison();
    });
  });
  $('[data-sort]').addEventListener('change', renderResults);

  /* ── STEP 4 — request ── */
  function prepRequest() {
    var box = $('[data-acceptance]');
    if (!box.dataset.built) {
      ACCEPTANCE.forEach(function (q) {
        var f = document.createElement('div');
        f.className = 'wz-field';
        f.innerHTML = '<label>' + esc(q[1]) + '</label><textarea name="' + q[0] + '" rows="2" placeholder="Laat leeg als niet van toepassing"></textarea>';
        box.appendChild(f);
      });
      box.dataset.built = '1';
    }
  }
  $('[data-submit-request]').addEventListener('click', function () {
    var err = $('[data-request-err]'); show(err, false);
    if (!state.selected) { err.textContent = 'Kies eerst een verzekeraar.'; show(err, true); goStep(3); return; }
    if (!$('[data-agreement]').checked) { err.textContent = 'Je moet akkoord gaan met de slotverklaring.'; show(err, true); return; }
    var bad4 = validateStep4();
    $all('.is-invalid').forEach(function (e) { e.classList.remove('is-invalid'); });
    if (bad4.length) {
      bad4.forEach(function (sel) { var e = $(sel); if (e) e.classList.add('is-invalid'); });
      err.textContent = 'Vul je naam, e-mail, mobiel nummer en IBAN correct in.';
      show(err, true);
      var f4 = $(bad4[0]); if (f4) f4.focus();
      return;
    }
    var payload = collectDetails();
    payload.selectedIdentifier = state.selected.Identifier;
    payload.Identifier = state.selected.Identifier;
    payload.Agreement = 'J';
    payload.additionalCoverages = Object.keys(state.selectedAddons).map(function (k) {
      return { Type: state.selectedAddons[k].Type, Identifier: state.selectedAddons[k].Identifier };
    });
    var btn = this; btn.disabled = true; btn.textContent = 'Versturen…';
    post(URLS.aanvraag, { data: payload }).then(function (res) {
      btn.disabled = false; btn.textContent = 'Verzekering aanvragen';
      if (!res.ok) { err.textContent = res.data.error || 'Het afsluiten is niet gelukt.'; show(err, true); return; }
      $('[data-policy]').textContent = res.data.PolicyNumber || '—';
      show($('[data-request-form]'), false);
      show($('[data-confirmation]'), true);
      window.scrollTo({ top: app.getBoundingClientRect().top + window.pageYOffset - 80, behavior: 'smooth' });
    });
  });

  /* ── step 1 validation ── */
  function validateStep1() {
    var bad = [];
    ['#zip', '#hn', '#bd', '#cfy'].forEach(function (sel) {
      var el = $(sel); if (el && !(el.value || '').trim()) bad.push(sel);
    });
    return bad;
  }
  ['#zip', '#hn', '#bd', '#cfy'].forEach(function (sel) {
    var el = $(sel); if (el) el.addEventListener('input', function () { el.classList.remove('is-invalid'); });
  });

  /* ── step 4 validation (spiegelt de verplichte velden in views_premie.aanvraag) ── */
  function validateStep4() {
    var bad = [];
    ['#vn', '#em', '#mb', '#iban'].forEach(function (sel) {
      var el = $(sel); if (el && !(el.value || '').trim()) bad.push(sel);
    });
    var em = $('#em');
    if (em && em.value.trim() && bad.indexOf('#em') < 0 &&
        !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(em.value.trim())) bad.push('#em');
    return bad;
  }
  ['#vn', '#em', '#mb', '#iban'].forEach(function (sel) {
    var el = $(sel); if (el) el.addEventListener('input', function () { el.classList.remove('is-invalid'); });
  });

  /* ── wire next/prev ── */
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
          var first = $(bad[0]); if (first) first.focus();
          return;
        }
        show(err1, false);
      }
      goStep(Number(b.dataset.next));
    });
  });
  $all('[data-prev]').forEach(function (b) { b.addEventListener('click', function () { goStep(Number(b.dataset.prev)); }); });
  var needCov = $('[data-need-coverage]'); if (needCov) needCov.disabled = true;

  /* Prefill from the homepage teasers (?kenteken/postcode/huisnummer/toevoeging/
     geboortedatum) zodat de bezoeker stap 1 niet opnieuw hoeft in te vullen. */
  (function () {
    var q = new URLSearchParams(window.location.search);
    var set = function (sel, val) { var el = $(sel); if (el && val) el.value = val; };
    set('#zip', q.get('postcode'));
    set('#hn', q.get('huisnummer'));
    set('#hna', q.get('toevoeging'));
    // Geboortedatum: home stuurt DD-MM-JJJJ; het date-veld wil JJJJ-MM-DD.
    var bd = (q.get('geboortedatum') || '').trim();
    if (bd) {
      var dm = /^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$/.exec(bd);
      if (dm) bd = dm[3] + '-' + ('0' + dm[2]).slice(-2) + '-' + ('0' + dm[1]).slice(-2);
      else if (!/^\d{4}-\d{2}-\d{2}$/.test(bd)) bd = '';
      set('#bd', bd);
    }
    // Kenteken: invullen + meteen opzoeken.
    var plate = (q.get('kenteken') || '').toUpperCase().replace(/[-\s]/g, '').slice(0, 9);
    if (plate.length >= 4) { $('#pl').value = plate; lookupBtn.click(); }
  })();
})();
