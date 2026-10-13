/* Ruen Thai — progressive Enhancement. Alle Inhalte stehen im HTML; dieses Skript
   ergänzt nur Navigation, "Jetzt geöffnet", Animationen, Karte und Formular. */
(function () {
  'use strict';

  /* ---------- Mobile-Navigation ---------- */
  var toggle = document.getElementById('nav-toggle');
  var nav = document.getElementById('site-nav');
  if (toggle && nav) {
    var setOpen = function (open) {
      nav.classList.toggle('is-open', open);
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      toggle.setAttribute('aria-label', open ? 'Menü schliessen' : 'Menü öffnen');
      document.body.style.overflow = open ? 'hidden' : '';
    };
    toggle.addEventListener('click', function () { setOpen(toggle.getAttribute('aria-expanded') !== 'true'); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') setOpen(false); });
    nav.querySelectorAll('a').forEach(function (a) { a.addEventListener('click', function () { setOpen(false); }); });
  }

  /* ---------- "Jetzt geöffnet" (Zeit in Europe/Zurich) ---------- */
  var DAY_LONG = ['Sonntag', 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag'];
  var WEEKDAY = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
  var fmt = null;
  try { fmt = new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Zurich', weekday: 'short', hour: '2-digit', minute: '2-digit', hour12: false }); } catch (e) {}
  function zurichNow() {
    var d = new Date();
    if (!fmt) return { day: d.getDay(), min: d.getHours() * 60 + d.getMinutes() };
    var day = 0, h = 0, m = 0;
    fmt.formatToParts(d).forEach(function (p) {
      if (p.type === 'weekday') day = WEEKDAY[p.value];
      if (p.type === 'hour') h = parseInt(p.value, 10) % 24;
      if (p.type === 'minute') m = parseInt(p.value, 10);
    });
    return { day: day, min: h * 60 + m };
  }
  function toMin(s) { var p = s.split(':'); return parseInt(p[0], 10) * 60 + parseInt(p[1], 10); }
  function statusFor(hours, now) {
    var today = hours[now.day] || [];
    for (var i = 0; i < today.length; i++) {
      if (now.min >= toMin(today[i][0]) && now.min < toMin(today[i][1])) return { open: true, text: 'Jetzt geöffnet · bis ' + today[i][1] + ' Uhr' };
    }
    for (var j = 0; j < today.length; j++) {
      if (now.min < toMin(today[j][0])) return { open: false, text: 'Geschlossen · öffnet heute um ' + today[j][0] + ' Uhr' };
    }
    for (var d = 1; d <= 7; d++) {
      var di = (now.day + d) % 7, r = hours[di] || [];
      if (r.length) return { open: false, text: 'Geschlossen · öffnet ' + (d === 1 ? 'morgen' : DAY_LONG[di]) + ' um ' + r[0][0] + ' Uhr' };
    }
    return { open: false, text: 'Geschlossen' };
  }
  function refresh() {
    var now = zurichNow();
    document.querySelectorAll('[data-hours]').forEach(function (el) {
      var hours; try { hours = JSON.parse(el.getAttribute('data-hours')); } catch (e) { return; }
      var s = statusFor(hours, now);
      el.className = 'status ' + (s.open ? 'is-open' : 'is-closed');
      el.innerHTML = '<i></i>';
      el.appendChild(document.createTextNode(s.text));
    });
    document.querySelectorAll('tr[data-days]').forEach(function (tr) {
      tr.classList.toggle('is-today', tr.getAttribute('data-days').split(',').indexOf(String(now.day)) !== -1);
    });
  }
  refresh();
  window.setInterval(refresh, 60000);

  /* ---------- Einblend-Animation ---------- */
  var reveals = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window && reveals.length) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
    reveals.forEach(function (el) { io.observe(el); });
    // Sicherheitsnetz: nie dauerhaft unsichtbare Inhalte (z. B. Druck, exotische Browser)
    window.setTimeout(function () { reveals.forEach(function (el) { el.classList.add('in'); }); }, 4000);
  } else {
    reveals.forEach(function (el) { el.classList.add('in'); });
  }

  /* ---------- Google Maps erst nach Klick laden (Datenschutz) ---------- */
  document.querySelectorAll('[data-map-src]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var frame = btn.closest('.map__frame');
      if (!frame) return;
      var iframe = document.createElement('iframe');
      iframe.src = btn.getAttribute('data-map-src');
      iframe.title = btn.getAttribute('data-map-title') || 'Karte';
      iframe.loading = 'lazy';
      iframe.referrerPolicy = 'no-referrer-when-downgrade';
      frame.innerHTML = '';
      frame.appendChild(iframe);
    });
  });

  /* ---------- Reservationsformular ---------- */
  var form = document.querySelector('form[data-reserve-form]');
  if (form) {
    var status = form.querySelector('.form__status');
    var dateInput = form.querySelector('input[type="date"]');
    if (dateInput) dateInput.min = new Date().toISOString().slice(0, 10);
    form.addEventListener('submit', function (e) {
      if (!window.fetch) return; // ohne fetch: normales Absenden an anfrage.php
      e.preventDefault();
      status.textContent = 'Wird gesendet …';
      var btn = form.querySelector('button[type="submit"]'); btn.disabled = true;
      fetch(form.action, { method: 'POST', body: new FormData(form), headers: { 'Accept': 'application/json' } })
        .then(function (r) { return r.json().catch(function () { return { ok: false }; }); })
        .then(function (j) {
          status.textContent = j.ok ? 'Danke! Wir bestätigen Ihre Anfrage so rasch wie möglich.' : (j.message || 'Das hat leider nicht geklappt. Bitte rufen Sie uns an.');
          if (j.ok) form.reset();
        })
        .catch(function () { status.textContent = 'Das hat leider nicht geklappt. Bitte rufen Sie uns an.'; })
        .then(function () { btn.disabled = false; });
    });
  }
})();
