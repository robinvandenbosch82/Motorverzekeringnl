/* Bestelautoverzekering.nl — progressive-enhancement interactions.
   Vanilla JS, no dependencies. Everything degrades gracefully without JS:
   content is server-rendered; this only adds interactivity. */
(function () {
  'use strict';

  var nlNum = function (n) { return n.toLocaleString('nl-NL'); };

  /* ── Mobile fullscreen menu ────────────────────────────────────────── */
  function initMobileMenu() {
    var menu = document.querySelector('[data-mobile-menu]');
    if (!menu) return;
    var openBtn = document.querySelector('[data-menu-open]');
    var accordions = menu.querySelectorAll('.mmenu__acc');
    var collapseAll = function () {
      accordions.forEach(function (a) {
        a.classList.remove('open');
        var h = a.querySelector('[data-acc-toggle]');
        if (h) h.setAttribute('aria-expanded', 'false');
      });
    };
    var setOpen = function (open) {
      menu.classList.toggle('open', open);
      menu.setAttribute('aria-hidden', open ? 'false' : 'true');
      if (openBtn) openBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
      document.body.style.overflow = open ? 'hidden' : '';
      if (!open) collapseAll();
    };
    if (openBtn) openBtn.addEventListener('click', function () { setOpen(true); });
    menu.querySelectorAll('[data-menu-close]').forEach(function (el) {
      el.addEventListener('click', function () { setOpen(false); });
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') setOpen(false);
    });
    // Accordion: tap a group header to expand it (only one open at a time).
    menu.querySelectorAll('[data-acc-toggle]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var acc = btn.closest('.mmenu__acc');
        var willOpen = !acc.classList.contains('open');
        collapseAll();
        if (willOpen) {
          acc.classList.add('open');
          btn.setAttribute('aria-expanded', 'true');
        }
      });
    });
  }

  /* ── Premie-teaser → echte tool (carry the typed kenteken across) ──── */
  function initToolCta() {
    document.querySelectorAll('[data-tool-cta]').forEach(function (cta) {
      cta.addEventListener('click', function (e) {
        var box = cta.closest('[data-calc]') || document;
        var plateEl = box.querySelector('[data-calc-kenteken]');
        var plate = plateEl ? plateEl.value.toUpperCase().replace(/[-\s]/g, '') : '';
        if (plate.length >= 4) {
          e.preventDefault();
          var base = cta.getAttribute('href');
          window.location.href = base + (base.indexOf('?') > -1 ? '&' : '?') + 'kenteken=' + encodeURIComponent(plate);
        }
        // else: let the link navigate to the tool normally (no kenteken yet).
      });
    });
  }

  /* ── Premie calculator (dummy outcome) ─────────────────────────────── */
  function initCalculators() {
    document.querySelectorAll('[data-calc]').forEach(function (root) {
      var type = 'ZZP';
      var toggle = root.querySelector('[data-calc-toggle]');
      var result = root.querySelector('[data-calc-result]');
      var amount = root.querySelector('[data-calc-amount]');
      var kenteken = root.querySelector('[data-calc-kenteken]');

      if (kenteken) {
        kenteken.addEventListener('input', function () {
          this.value = this.value.toUpperCase().slice(0, 9);
        });
      }
      if (toggle) {
        toggle.querySelectorAll('button').forEach(function (btn) {
          btn.addEventListener('click', function () {
            type = btn.getAttribute('data-type');
            toggle.querySelectorAll('button').forEach(function (b) { b.classList.remove('active'); });
            btn.classList.add('active');
          });
        });
      }
      var go = root.querySelector('[data-calc-go]');
      if (go && result && amount) {
        go.addEventListener('click', function () {
          var target = type === 'Wagenpark' ? 29 : 41;
          result.hidden = false;
          amount.textContent = '€ ' + target;  // direct, geen tel-animatie
        });
      }
    });
  }

  /* ── Stilstand-rekenmachine (live sliders) ─────────────────────────── */
  function initStilstand() {
    var root = document.querySelector('[data-stilstand]');
    if (!root) return;
    var omzet = root.querySelector('[data-omzet]');
    var dagen = root.querySelector('[data-dagen]');
    var omzetOut = root.querySelector('[data-omzet-out]');
    var dagenOut = root.querySelector('[data-dagen-out]');
    var verliesOut = root.querySelector('[data-verlies-out]');
    var update = function () {
      var o = +omzet.value, d = +dagen.value;
      omzetOut.textContent = '€ ' + nlNum(o);
      dagenOut.textContent = d + (d === 1 ? ' dag' : ' dagen');
      verliesOut.textContent = '€ ' + nlNum(o * d);
    };
    omzet.addEventListener('input', update);
    dagen.addEventListener('input', update);
    update();
  }

  /* ── FAQ accordion ─────────────────────────────────────────────────── */
  function initFaq() {
    document.querySelectorAll('[data-faq]').forEach(function (faq) {
      faq.querySelectorAll('.faq__q').forEach(function (q) {
        q.addEventListener('click', function () {
          var item = q.closest('.faq__item');
          var isOpen = item.classList.contains('open');
          faq.querySelectorAll('.faq__item').forEach(function (i) {
            i.classList.remove('open');
            var sign = i.querySelector('.faq__sign');
            if (sign) sign.textContent = '+';
          });
          if (!isOpen) {
            item.classList.add('open');
            var s = item.querySelector('.faq__sign');
            if (s) s.textContent = '–';
          }
        });
      });
    });
  }

  /* ── Sortable lists (vergelijken / verzekeraars) ───────────────────── */
  function initSort() {
    document.querySelectorAll('[data-sort-control]').forEach(function (control) {
      var targetSel = control.getAttribute('data-sort-target');
      var list = document.querySelector(targetSel);
      if (!list) return;
      control.addEventListener('change', function () {
        var key = control.value; // 'premie' | 'score'
        var items = Array.prototype.slice.call(list.querySelectorAll('[data-sort-item]'));
        items.sort(function (a, b) {
          var av = parseFloat(a.getAttribute('data-' + key));
          var bv = parseFloat(b.getAttribute('data-' + key));
          return key === 'score' ? bv - av : av - bv;
        });
        items.forEach(function (i) { list.appendChild(i); });
      });
    });
  }

  /* ── Stats + reveal: geen beweging meer, direct de eindwaarde tonen ─── */
  function initCountUp() {
    document.querySelectorAll('[data-countup]').forEach(function (el) {
      el.textContent = nlNum(parseInt(el.getAttribute('data-countup'), 10));
    });
  }

  function initReveal() {
    // Geen scroll-reveal/fade meer; alles meteen zichtbaar (CSS dekt dit ook af).
    document.querySelectorAll('.reveal').forEach(function (el) { el.classList.add('is-in'); });
  }

  document.addEventListener('DOMContentLoaded', function () {
    initMobileMenu();
    initToolCta();
    initCalculators();
    initStilstand();
    initFaq();
    initSort();
    initCountUp();
    initReveal();
  });
})();
