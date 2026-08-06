// coffee-machine-card - Home-Connect Kaffeevollautomat (Bosch/Siemens)
// Plastisches, animiertes Metrology-Objekt. REINER ASCII-Quelltext:
// alle Umlaute/Sonderzeichen ausschliesslich als \uXXXX. 0 externe Ressourcen.
// Kommentare bewusst umlautfrei formuliert (ASCII-Vertrag der Auslieferung).

const E = c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]);
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, E);
const isNum = v => v != null && v !== '' && isFinite(parseFloat(String(v).replace(',', '.')));
const num = v => (isNum(v) ? parseFloat(String(v).replace(',', '.')) : null);

// ---- Textbausteine (Du-Ansprache, kein Denglisch, echte Umlaute als \u) ----
const T = {
  title: 'KAFFEEVOLLAUTOMAT',
  run: 'L\u00e4uft', ready: 'Bereit', done: 'Fertig', off: 'Aus', pause: 'Pausiert', idle: '\u2014',
  connOk: 'Verbunden', connBad: 'Getrennt', connUnk: '\u2014',
  allGood: 'Alles bereit', noMaint: 'Keine Wartung f\u00e4llig',
  settings: 'EINSTELLUNGEN', control: 'STEUERUNG', diag: 'VERBINDUNG & DIAGNOSE',
  more: 'weitere', remHint: 'Fernstart am Ger\u00e4t aktivieren', remOn: 'Fernstart aktiv',
  aStop: 'Stopp', aResume: 'Fortsetzen', aOn: 'Einschalten', aOff: 'Ausschalten',
  on: 'Ein', offS: 'Aus', yes: 'Ja', no: 'Abbrechen',
  qStop: 'Lauf wirklich abbrechen?', qOff: 'Ger\u00e4t wirklich ausschalten?',
  device: 'Ger\u00e4t', warmer: 'Tassenw\u00e4rmer', lock: 'Kindersicherung',
  light: 'Innenbeleuchtung', local: 'Lokale Steuerung', remote: 'Fernstart',
  descaleIn: 'Entkalken in', cups: 'Tassen', loading: 'Laden \u2026', demo: 'DEMO',
  overdue: '\u00fcberf\u00e4llig', recommended: 'empfohlen',
  fill: 'F\u00fcllmenge', temp: 'Kaffee-Temperatur', ratio: 'Kaffee-Milch-Verh\u00e4ltnis',
  flow: 'Durchflussrate', hwTemp: 'Heisswasser-Temperatur', beans: 'Bohnenbeh\u00e4lter'
};

// Getraenk: langer Home-Connect-Enum -> sauberes deutsches Label.
// Schluessel = Suffix nach 'beverage_' (bzw. bereits deutsches Wort, kleingeschrieben).
const BEV = {
  espresso: 'Espresso', ristretto: 'Ristretto', espresso_macchiato: 'Espresso Macchiato',
  espresso_doppio: 'Doppel-Espresso', coffee: 'Kaffee', xl_coffee: 'XL-Kaffee', coffee_xl: 'XL-Kaffee',
  cappuccino: 'Cappuccino', latte_macchiato: 'Latte Macchiato', caffe_latte: 'Caffe Latte',
  milk_froth: 'Milchschaum', warm_milk: 'Warme Milch', hot_water: 'Heisswasser',
  americano: 'Americano', flat_white: 'Flat White', kaffee: 'Kaffee', heisswasser: 'Heisswasser',
  milchschaum: 'Milchschaum'
};
function bevLabel(raw) {
  if (raw == null) return null;
  let s = String(raw).toLowerCase().trim();
  const i = s.lastIndexOf('beverage_');
  if (i >= 0) s = s.slice(i + 9);
  else s = s.replace('consumer_products_coffee_maker_program_', '');
  s = s.trim();
  if (!s) return null;
  if (BEV[s]) return BEV[s];
  return s.split(/[_\s]+/).filter(Boolean).map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ') || null;
}

// Wartungs-Katalog: Config-Key -> [key, sev, text]. sev: 'crit' (rot) / 'warn' (orange).
// Reihenfolge = Prioritaet fuer die Banner-Primary-Auswahl.
const MAINT = [
  ['water_empty', 'crit', 'Wassertank f\u00fcllen'],
  ['beans_empty', 'crit', 'Bohnen nachf\u00fcllen'],
  ['tray_full', 'crit', 'Tropfschale leeren'],
  ['descale_block', 'crit', 'Ger\u00e4t blockiert \u2013 entkalken'],
  ['calc_block', 'crit', 'Verstopfung \u2013 Calc\u2019n\u2019Clean'],
  ['descale_over', 'crit', 'Entkalken \u00fcberf\u00e4llig'],
  ['calc_over', 'crit', 'Calc\u2019n\u2019Clean \u00fcberf\u00e4llig'],
  ['clean_over', 'crit', 'Reinigung \u00fcberf\u00e4llig'],
  ['descale_rec', 'warn', 'Entkalken empfohlen'],
  ['calc_rec', 'warn', 'Calc\u2019n\u2019Clean empfohlen'],
  ['clean_rec', 'warn', 'Reinigung empfohlen'],
  ['milk_cool', 'warn', 'Milchtank k\u00fchl halten']
];

// Statistik-Kacheln: [Config-Key, Label, Format].
const STATS = [
  ['stat_coffees', 'KAFFEES', 'int'],
  ['stat_coffee_milk', 'KAFFEE & MILCH', 'int'],
  ['stat_milk', 'MIT MILCH', 'int'],
  ['stat_hotwater_cups', 'HEISSWASSER', 'int'],
  ['stat_hotwater_ml', 'WASSERMENGE', 'liter']
];

// Einstellungen: [Config-Key, Label] (nur wenn Entity konfiguriert).
const SETTINGS = [
  ['set_temp', T.temp], ['set_ratio', T.ratio], ['set_flow', T.flow],
  ['set_hwtemp', T.hwTemp], ['set_beans', T.beans], ['set_fill', T.fill]
];

if (!customElements.get('coffee-machine-card')) {
  class CoffeeMachineCard extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: 'open' });
      this._sig = null; this._open = null; this._confirm = null; this._built = false;
      this.shadowRoot.addEventListener('click', e => this._tap(e));
      this.shadowRoot.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this._tap(e); }
      });
    }
    setConfig(cfg) {
      this._cfg = cfg || {};
      this._ent = this._cfg.entities || {};
      this._demo = !this._ent || Object.keys(this._ent).length === 0;
      this._sig = null; this._open = null; this._confirm = null;
      const m = this._model();
      this._sig = m.sig; this._render(m);
    }
    getCardSize() { return 8; }
    static getStubConfig() { return { entities: {} }; }

    set hass(h) {
      this._hass = h;
      if (!this._cfg) return;
      const m = this._model();
      if (m.sig !== this._sig) { this._sig = m.sig; this._render(m); }
      else this._tick(m);
    }
    get hass() { return this._hass; }
    _rerender() { const m = this._model(); this._sig = m.sig; this._render(m); }

    _obj(k) { const id = this._ent[k], h = this._hass; if (!h || !h.states || !id) return null; return h.states[id] || null; }
    _st(k) {
      const o = this._obj(k); if (!o) return null;
      const s = o.state;
      if (s == null || s === 'unavailable' || s === 'unknown' || s === '') return null;
      return o;
    }
    _sv(k) { const o = this._st(k); return o ? o.state : null; }
    _disp(k) {
      const o = this._st(k); if (!o) return null;
      const d = (this._hass && this._hass.formatEntityState) ? this._hass.formatEntityState(o) : o.state;
      return (d == null || d === '') ? o.state : d;
    }
    _bool(s) { return ['on', 'true', '1', 'present', 'confirmed', 'yes', 'open', 'offen', 'active'].indexOf(String(s).toLowerCase()) > -1; }
    _binOn(k) { if (this._demo) return false; const o = this._st(k); return o ? this._bool(o.state) : false; }

    _remaining() {
      const o = this._st('end_time'); if (!o) return null;
      const raw = String(o.state).trim();
      const t = Date.parse(raw);
      if (isFinite(t)) {
        const diff = t - Date.now();
        if (diff <= 30000) return 'gleich fertig';
        const min = Math.round(diff / 60000);
        return 'noch ' + (min < 1 ? '<1' : min) + ' Min';
      }
      return null;
    }

    _model() {
      const dm = this._demo, en = this._ent;
      // Ladezustand: Entities gesetzt, aber hass noch nicht da.
      if (!dm && (!this._hass || !this._hass.states)) {
        return { loading: true, bucket: 'idle', sig: 'loading' };
      }
      if (dm) {
        const stats = [
          { val: '184', label: 'KAFFEES' }, { val: '640', label: 'KAFFEE & MILCH' },
          { val: '17', label: 'MIT MILCH' }, { val: '313', label: 'HEISSWASSER' },
          { val: '77,8 L', label: 'WASSERMENGE' }
        ];
        return {
          demo: true, bucket: 'run', stateLabel: T.run, bev: 'Cappuccino',
          frac: 0.63, indet: false, pct: 63, remTxt: 'noch 1 Min',
          maint: { sev: 'ok', items: [], primary: T.allGood, extra: 0 },
          remoteOn: true, conn: { s: 'ok', label: T.connOk },
          controls: [{ key: 'power', label: T.device, on: true }, { key: 'warmer', label: T.warmer, on: false }, { key: 'lock', label: T.lock, on: false }],
          settings: [{ key: 'set_temp', label: T.temp, val: 'Normal' }, { key: 'set_ratio', label: T.ratio, val: '50 %' }, { key: 'set_fill', label: T.fill, val: '120 mL' }],
          diag: [{ label: T.light, val: T.on }, { label: T.local, val: T.on }, { label: T.remote, val: T.on }, { label: T.descaleIn, val: '42 ' + T.cups }],
          stats, sig: 'demo|' + this._open + '|' + this._confirm
        };
      }

      const raw = String(this._sv('state') || '').toLowerCase();
      let bucket = 'idle';
      // Reihenfolge zaehlt: 'inactive' enthaelt den Teilstring 'active' und darf
      // NICHT im run-Zweig landen -> Aus/Inaktiv wird vor run geprueft.
      if (raw === '') bucket = 'idle';
      else if (/finish|fertig|done|complete/.test(raw)) bucket = 'done';
      else if (/pause/.test(raw)) bucket = 'pause';
      else if (/inactive|inaktiv|off|aus|standby/.test(raw)) bucket = 'off';
      else if (/ready|bereit/.test(raw)) bucket = 'ready';
      else if (/run|lauf|active|brew|delayed|dispens/.test(raw)) bucket = 'run';
      else bucket = 'ready';
      const running = bucket === 'run';

      // Getraenk: bei Lauf das aktive Programm, sonst das ausgewaehlte.
      const bev = bevLabel((running ? this._sv('program_active') : null) || this._sv('program_selected') || this._sv('program_active'));

      // Fortschritt: oft unavailable -> indeterminate-Animation.
      const pn = num(this._sv('progress'));
      const determinate = pn != null;
      let frac, pct = null, indet = false;
      if (bucket === 'done') { frac = 1; }
      else if (running) {
        if (determinate) { frac = Math.max(0, Math.min(1, pn / 100)); pct = Math.round(pn); }
        else { frac = 0.55; indet = true; }
      } else if (bucket === 'pause') { frac = determinate ? Math.max(0, Math.min(1, pn / 100)) : 0.5; if (determinate) pct = Math.round(pn); }
      else frac = 0;
      const remTxt = running ? this._remaining() : null;

      const stateLabel = { run: T.run, ready: T.ready, done: T.done, off: T.off, pause: T.pause, idle: T.idle }[bucket];

      // Wartung intelligent verdichten: nur aktive Handlungen; hoechste Schwere fuehrt.
      const items = [];
      for (let i = 0; i < MAINT.length; i++) {
        const kk = MAINT[i];
        if (en[kk[0]] && this._binOn(kk[0])) items.push({ sev: kk[1], text: kk[2] });
      }
      let sev = 'ok', primary = T.allGood, extra = 0;
      if (items.length) {
        const crit = items.filter(x => x.sev === 'crit');
        const lead = crit.length ? crit[0] : items[0];
        sev = lead.sev; primary = lead.text; extra = items.length - 1;
      }
      const maint = { sev, items, primary, extra };

      // Verbindung (Kopf-Punkt besitzt diese Wahrheit).
      let conn = { s: 'unk', label: T.connUnk };
      if (en.connectivity) { const on = this._binOn('connectivity'); conn = on ? { s: 'ok', label: T.connOk } : { s: 'bad', label: T.connBad }; }

      const remoteOn = this._binOn('remote_start');

      // Steuerung (nur konfigurierte Schalter).
      const controls = [];
      if (en.power) controls.push({ key: 'power', label: T.device, on: this._binOn('power') });
      if (en.cup_warmer) controls.push({ key: 'warmer', label: T.warmer, on: this._binOn('cup_warmer') });
      if (en.child_lock) controls.push({ key: 'lock', label: T.lock, on: this._binOn('child_lock') });

      // Einstellungen (nur konfigurierte, mit gueltigem Wert).
      const settings = [];
      for (let i = 0; i < SETTINGS.length; i++) {
        const kk = SETTINGS[i];
        if (!en[kk[0]]) continue;
        let v = this._disp(kk[0]);
        if (v == null) continue;
        if (kk[0] === 'set_fill' && isNum(v)) v = Math.round(num(v)) + ' mL';
        settings.push({ key: kk[0], label: kk[1], val: v });
      }

      // Diagnose: Verbindungs-Detailwerte + Entkalk-Countdown + volle Wartungsliste.
      const diag = [];
      const dv = (k, label) => { if (en[k]) diag.push({ label, val: this._binOn(k) ? T.on : T.offS }); };
      dv('light', T.light); dv('local_control', T.local);
      if (en.remote_start) diag.push({ label: T.remote, val: remoteOn ? T.on : T.offS });
      const dc = num(this._sv('descale_in'));
      if (dc != null) diag.push({ label: T.descaleIn, val: Math.round(dc) + ' ' + T.cups });

      // Statistik.
      const stats = [];
      for (let i = 0; i < STATS.length; i++) {
        const kk = STATS[i]; if (!en[kk[0]]) continue;
        const v = num(this._sv(kk[0])); if (v == null) continue;
        stats.push({ val: kk[2] === 'liter' ? (v / 1000).toFixed(1).replace('.', ',') + ' L' : String(Math.round(v)), label: kk[1] });
      }

      const m = {
        loading: false, demo: false, bucket, stateLabel, bev, frac, indet, pct, remTxt,
        maint, remoteOn, conn, controls, settings, diag, stats
      };
      // Struktur-Signatur OHNE frac/pct/remTxt (diese aktualisiert _tick weich -> keine Anim-Neustarts).
      m.sig = [bucket, bev, indet, sev, primary, extra, remoteOn, conn.s,
        controls.map(c => c.key + (c.on ? 1 : 0)).join(','),
        settings.map(s => s.key + s.val).join(','),
        diag.map(d => d.label + d.val).join(','),
        stats.map(s => s.label + s.val).join(','),
        this._open, this._confirm].join('|');
      return m;
    }

    _call(id, service, extra) {
      if (!this._hass || !id || String(id).indexOf('.') < 0) return;
      try { this._hass.callService(id.split('.')[0], service, Object.assign({ entity_id: id }, extra || {})); } catch (e) { /* ruhig */ }
    }
    _moreInfo(id) {
      if (!id) return;
      this.dispatchEvent(new CustomEvent('hass-more-info', { detail: { entityId: id }, bubbles: true, composed: true }));
    }
    _doConfirmed(k) {
      if (this._demo) return;
      if (k === 'stop') this._call(this._ent.stop_button, 'press');
      else if (k === 'off') this._call(this._ent.power, 'turn_off');
    }
    _tap(e) {
      let n = e.target, act = null;
      while (n && n !== this.shadowRoot) { if (n.dataset && n.dataset.act) { act = n.dataset.act; break; } n = n.parentNode; }
      if (!act) return;
      const remoteOn = this._demo ? true : this._binOn('remote_start');
      if (act.slice(0, 4) === 'acc:') { const key = act.slice(4); this._open = this._open === key ? null : key; return this._rerender(); }
      if (act.slice(0, 3) === 'mi:') { return this._moreInfo(this._ent[act.slice(3)]); }
      if (act === 'cfn') { this._confirm = null; return this._rerender(); }
      if (act === 'cfy') { const k = this._confirm; this._confirm = null; this._doConfirmed(k); return this._rerender(); }
      // Gesteuerte Aktionen: nur bei aktivem Fernstart (sonst Hinweis).
      if (!remoteOn) return;
      if (this._demo && (act.slice(0, 4) === 'act:' || act.slice(0, 4) === 'ctl:')) return;
      if (act === 'act:stop') { this._confirm = 'stop'; return this._rerender(); }
      if (act === 'act:resume') { this._call(this._ent.resume_button, 'press'); return this._rerender(); }
      if (act === 'ctl:power') {
        if (this._binOn('power')) { this._confirm = 'off'; return this._rerender(); }
        this._call(this._ent.power, 'turn_on'); return this._rerender();
      }
      if (act === 'ctl:warmer') { this._call(this._ent.cup_warmer, 'toggle'); return this._rerender(); }
      if (act === 'ctl:lock') { this._call(this._ent.child_lock, 'toggle'); return this._rerender(); }
    }

    // ---- Plastische, animierte Maschinen-Grafik ----
    _defs() {
      return '<defs>' +
        '<linearGradient id="gb" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3a4048"/><stop offset="0.5" stop-color="#1c2027"/><stop offset="1" stop-color="#0d0f13"/></linearGradient>' +
        '<linearGradient id="gs" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4a515b"/><stop offset="1" stop-color="#22262c"/></linearGradient>' +
        '<linearGradient id="gh" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0.28"/><stop offset="0.5" stop-color="#fff" stop-opacity="0"/></linearGradient>' +
        '<radialGradient id="gi" cx="0.5" cy="0.25" r="0.9"><stop offset="0" stop-color="#3d444e"/><stop offset="1" stop-color="#0b0d10"/></radialGradient>' +
        '<radialGradient id="gg" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#ff1e6f" stop-opacity="0.85"/><stop offset="1" stop-color="#ff1e6f" stop-opacity="0"/></radialGradient>' +
        '<linearGradient id="gcup" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0.10"/><stop offset="0.45" stop-color="#fff" stop-opacity="0.26"/><stop offset="1" stop-color="#fff" stop-opacity="0.06"/></linearGradient>' +
        '<linearGradient id="gcof" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8a5a30"/><stop offset="0.5" stop-color="#5a3618"/><stop offset="1" stop-color="#2e1a0d"/></linearGradient>' +
        '<clipPath id="cupc"><path d="M80 152 H120 L116 188 Q115 190 112 190 H88 Q85 190 84 188 Z"/></clipPath>' +
        '</defs>';
    }
    _svg(m) {
      const b = m.bucket, run = b === 'run';
      const ty = ((1 - (m.frac == null ? 0 : m.frac)) * 36).toFixed(1);
      const led = run ? '#ff1e6f' : (b === 'ready' || b === 'done' ? '#35d07f' : '#3a3f47');
      return '<svg viewBox="0 0 200 236" role="img" aria-label="' + esc(T.title + ' \u2013 ' + (m.stateLabel || '')) + '">' + this._defs() +
        '<ellipse cx="100" cy="224" rx="82" ry="10" fill="#000" opacity="0.5"/>' +
        '<rect x="30" y="14" width="140" height="196" rx="18" fill="url(#gb)" stroke="#474d57" stroke-width="1.2"/>' +
        '<rect x="52" y="10" width="96" height="22" rx="11" fill="url(#gs)"/>' +
        '<path d="M84 12 H116 L110 26 H90 Z" fill="#14181d" stroke="#3a3f47" stroke-width="0.8"/>' +
        '<rect x="36" y="20" width="42" height="182" rx="12" fill="url(#gh)" opacity="0.5"/>' +
        '<rect x="48" y="40" width="104" height="20" rx="5" fill="#06070a" stroke="#000"/>' +
        '<circle cx="60" cy="50" r="3" fill="' + led + '"/>' +
        (run ? '<rect x="74" y="48" width="66" height="4" rx="2" fill="#fff" opacity="0.07"/><rect class="dsheen" x="74" y="48" width="20" height="4" rx="2" fill="#ff1e6f" opacity="0.55"/>' : '') +
        '<rect x="62" y="100" width="76" height="110" rx="10" fill="url(#gi)"/>' +
        '<rect x="62" y="100" width="76" height="12" fill="#000" opacity="0.35"/>' +
        '<rect x="84" y="102" width="32" height="16" rx="4" fill="url(#gs)"/>' +
        '<rect x="90" y="118" width="6" height="15" rx="3" fill="#1c2026"/><rect x="104" y="118" width="6" height="15" rx="3" fill="#1c2026"/>' +
        '<ellipse class="glow" cx="100" cy="172" rx="42" ry="34" fill="url(#gg)" opacity="0"/>' +
        '<g class="stream"><rect x="92" y="133" width="2.4" height="18" rx="1.2" fill="#6b4423"/><rect x="106" y="133" width="2.4" height="18" rx="1.2" fill="#6b4423"/></g>' +
        '<path d="M78 150 H122 L117 188 Q116 191 112 191 H88 Q84 191 83 188 Z" fill="url(#gcup)" stroke="#d8dee6" stroke-width="1.2" stroke-opacity="0.5"/>' +
        '<path d="M122 156 Q140 158 138 170 Q136 182 120 182" fill="none" stroke="#d8dee6" stroke-width="3" stroke-opacity="0.42"/>' +
        '<g clip-path="url(#cupc)"><g class="coffeeWrap" style="transform:translateY(' + ty + 'px)"><rect x="78" y="152" width="44" height="40" fill="url(#gcof)"/><ellipse cx="100" cy="152" rx="20" ry="2.6" fill="#9a6636" opacity="0.9"/></g></g>' +
        '<ellipse cx="100" cy="150" rx="22" ry="3.4" fill="none" stroke="#eef2f7" stroke-width="1" stroke-opacity="0.38"/>' +
        '<circle class="donering" cx="100" cy="170" r="26" fill="none" stroke="#ff1e6f" stroke-width="2" opacity="0"/>' +
        '<g class="steam" fill="none" stroke="#cfd6de" stroke-width="2.4" stroke-linecap="round" opacity="0"><path class="sp" d="M92 148 q-5 -8 0 -16 q5 -8 0 -16"/><path class="sp" d="M100 150 q-5 -9 0 -18 q5 -9 0 -18"/><path class="sp" d="M108 148 q5 -8 0 -16 q-5 -8 0 -16"/></g>' +
        '<g stroke="#3a3f47" stroke-width="1"><line x1="72" y1="204" x2="128" y2="204"/><line x1="72" y1="207" x2="128" y2="207"/></g>' +
        '</svg>';
    }

    _heroRight(m) {
      let h = '<div class="read">';
      h += '<div class="state">' + esc(m.stateLabel) + '</div>';
      if (m.bev && m.bucket !== 'off') h += '<div class="bev">' + esc(m.bev) + '</div>';
      if (m.bucket === 'run' && m.pct != null) h += '<div class="prog"><span class="pctNum">' + m.pct + '</span><span class="u">%</span></div>';
      if (m.remTxt) h += '<div class="rem"><span class="remTime">' + esc(m.remTxt) + '</span></div>';
      else if (m.bucket === 'run') h += '<div class="rem"><span class="remTime"></span></div>';
      // Wartung: ruhiger Sammelstatus, nur Handlungsbedarf laut.
      if (m.bucket !== 'off') {
        h += '<div class="maint ' + m.maint.sev + '"><span class="md"></span><span class="mt">' + esc(m.maint.primary) + '</span>' +
          (m.maint.extra > 0 ? '<span class="mx">+' + m.maint.extra + ' ' + T.more + '</span>' : '') + '</div>';
      }
      // Kontextuelle Primaer-Aktion.
      h += this._heroAction(m);
      h += '</div>';
      return h;
    }
    _heroAction(m) {
      if (this._confirm) {
        const q = this._confirm === 'stop' ? T.qStop : T.qOff;
        return '<div class="cf"><span class="cq">' + esc(q) + '</span><div class="cfb">' +
          '<button class="btn no" type="button" data-act="cfn">' + T.no + '</button>' +
          '<button class="btn crit" type="button" data-act="cfy">' + T.yes + '</button></div></div>';
      }
      let btn = null;
      if (m.bucket === 'run' && this._ent.stop_button) btn = { act: 'act:stop', label: T.aStop, cls: 'crit' };
      else if (m.bucket === 'pause' && this._ent.resume_button) btn = { act: 'act:resume', label: T.aResume, cls: 'go' };
      if (!btn) return '';
      if (!m.remoteOn) return '<div class="rhint"><span class="dot"></span>' + T.remHint + '</div>';
      return '<div class="act"><button class="btn ' + btn.cls + '" type="button" data-act="' + btn.act + '">' + btn.label + '</button></div>';
    }

    _stats(m) {
      if (!m.stats || !m.stats.length) return '';
      return '<div class="stats">' + m.stats.map(s =>
        '<div class="stat"><b>' + esc(s.val) + '</b><span>' + esc(s.label) + '</span></div>').join('') + '</div>';
    }

    _acc(key, label, body) {
      if (!body) return '';
      const op = this._open === key;
      return '<div class="acc"><div class="ah' + (op ? ' op' : '') + '" role="button" tabindex="0" aria-expanded="' + op + '" data-act="acc:' + key + '">' +
        '<span>' + label + '</span><span class="ch">\u203a</span></div>' +
        (op ? '<div class="ab">' + body + '</div>' : '') + '</div>';
    }
    _settingsBody(m) {
      if (!m.settings || !m.settings.length) return '';
      return m.settings.map(s =>
        '<div class="row" role="button" tabindex="0" data-act="mi:' + s.key + '"><span class="rk">' + esc(s.label) + '</span><span class="rv">' + esc(s.val) + ' \u203a</span></div>').join('');
    }
    _controlBody(m) {
      if (!m.controls || !m.controls.length) return '';
      let h = '';
      if (!m.remoteOn) h += '<div class="rhint"><span class="dot"></span>' + T.remHint + '</div>';
      h += m.controls.map(c => {
        const act = 'ctl:' + c.key;
        return '<div class="row"><span class="rk">' + esc(c.label) + '</span>' +
          '<button class="tgl' + (c.on ? ' on' : '') + (m.remoteOn ? '' : ' dis') + '" type="button"' + (m.remoteOn ? ' data-act="' + act + '"' : ' aria-disabled="true"') +
          ' role="switch" aria-checked="' + c.on + '" aria-label="' + esc(c.label) + '"><span class="kn"></span></button></div>';
      }).join('');
      return h;
    }
    _diagBody(m) {
      let rows = [];
      if (m.maint.items && m.maint.items.length) {
        rows = rows.concat(m.maint.items.map(it =>
          '<div class="row"><span class="rk"><span class="sd ' + it.sev + '"></span>' + esc(it.text) + '</span><span class="rv">' + (it.sev === 'crit' ? T.overdue : T.recommended) + '</span></div>'));
      } else {
        rows.push('<div class="row"><span class="rk"><span class="sd ok"></span>' + T.noMaint + '</span><span class="rv"></span></div>');
      }
      rows = rows.concat((m.diag || []).map(d =>
        '<div class="row"><span class="rk">' + esc(d.label) + '</span><span class="rv">' + esc(d.val) + '</span></div>'));
      return rows.join('');
    }

    _render(m) {
      m = m || this._model();
      if (m.loading) {
        this.shadowRoot.innerHTML = this._css() + '<div class="card"><div class="hd"><span class="ttl">' + T.title + '</span></div><div class="skel"><div class="sk sk1"></div><div class="sk sk2"></div><div class="sk sk3"></div></div></div>';
        this._built = true; return;
      }
      const connCls = m.conn.s === 'ok' ? 'ok' : (m.conn.s === 'bad' ? 'bad' : '');
      const head = '<div class="hd"><span class="ttl">' + T.title + '</span><div class="hdr">' +
        (m.demo ? '<span class="demo">' + T.demo + '</span>' : '') +
        ((this._ent.connectivity || m.demo) ? '<span class="conn"><span class="cdot ' + connCls + '"></span>' + esc(m.conn.label) + '</span>' : '') +
        '</div></div>';
      const hero = '<div class="hero"><div class="machine">' + this._svg(m) + '</div>' + this._heroRight(m) + '</div>';
      const settings = this._acc('set', T.settings, this._settingsBody(m));
      const control = this._acc('ctl', T.control, this._controlBody(m));
      const diag = this._acc('diag', T.diag, this._diagBody(m));
      this.shadowRoot.innerHTML = this._css() +
        '<div class="card s-' + m.bucket + (m.indet ? ' indet' : '') + '">' +
        head + hero + this._stats(m) + settings + control + diag + '</div>';
      this._built = true;
    }
    // Weiches Update von Fortschritt/Restzeit ohne innerHTML-Neuaufbau (kein Anim-Neustart).
    _tick(m) {
      const r = this.shadowRoot; if (!r) return;
      const w = r.querySelector('.coffeeWrap');
      if (w && !m.indet && m.frac != null) w.style.transform = 'translateY(' + ((1 - m.frac) * 36).toFixed(1) + 'px)';
      const p = r.querySelector('.pctNum'); if (p && m.pct != null) p.textContent = m.pct;
      const t = r.querySelector('.remTime'); if (t) t.textContent = m.remTxt || '';
    }

    _css() {
      return '<style>' +
        ':host{display:block}*{box-sizing:border-box}' +
        ".card{position:relative;font-family:'Segoe UI Variable','Segoe UI',system-ui,-apple-system,sans-serif;color:#eef2f7;background:radial-gradient(120% 90% at 50% 0,#15181d 0,#0b0d10 55%,#070809 100%);border-radius:20px;padding:18px 18px 14px;overflow:hidden}" +
        '.hd{display:flex;align-items:center;justify-content:space-between;gap:12px}' +
        '.ttl{font-size:12px;font-weight:600;letter-spacing:2px;color:#aab1bb}' +
        '.hdr{display:flex;align-items:center;gap:10px}' +
        '.demo{font-size:10px;letter-spacing:2px;font-weight:600;color:#ff1e6f;border:1px solid rgba(255,30,111,.35);border-radius:6px;padding:2px 6px}' +
        '.conn{display:flex;align-items:center;gap:6px;font-size:11px;color:#8b929c}' +
        '.cdot{width:8px;height:8px;border-radius:50%;background:#5b626c}' +
        '.cdot.ok{background:#35d07f;box-shadow:0 0 8px rgba(53,208,127,.6)}.cdot.bad{background:#ff4d6a}' +
        '.hero{display:flex;gap:14px;align-items:stretch;margin-top:8px}' +
        '.machine{flex:0 0 44%;max-width:196px}.machine svg{width:100%;height:auto;display:block}' +
        '.read{flex:1;display:flex;flex-direction:column;justify-content:center;min-width:0}' +
        '.state{font-size:40px;font-weight:200;line-height:1;letter-spacing:.5px;color:#dfe4ea}' +
        '.s-run .state{color:#fff}.s-off .state{color:#6b727c}' +
        '.bev{font-size:17px;font-weight:300;color:#ff5c95;margin-top:5px}.s-off .bev,.s-idle .bev{color:#8b929c}' +
        '.prog{font-size:44px;font-weight:200;font-variant-numeric:tabular-nums;line-height:1;margin-top:10px;color:#fff}' +
        '.prog .u{font-size:20px;color:#8b929c;margin-left:2px}' +
        '.rem{font-size:13px;color:#aab1bb;margin-top:3px;letter-spacing:.4px}' +
        '.maint{display:flex;align-items:center;gap:8px;margin-top:12px;padding:8px 10px;border-radius:12px;font-size:13px;background:rgba(255,255,255,.04)}' +
        '.maint .md{width:9px;height:9px;border-radius:50%;flex:0 0 auto}' +
        '.maint.ok{color:#bfe6d2}.maint.ok .md{background:#35d07f}' +
        '.maint.warn{color:#ffd8a3;background:rgba(255,157,47,.09)}.maint.warn .md{background:#ff9d2f;box-shadow:0 0 8px rgba(255,157,47,.5)}' +
        '.maint.crit{color:#ffc2cd;background:rgba(255,77,106,.10)}.maint.crit .md{background:#ff4d6a;box-shadow:0 0 8px rgba(255,77,106,.5)}' +
        '.maint .mx{color:#8b929c;font-size:11px;margin-left:auto;white-space:nowrap}' +
        '.act{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}' +
        '.btn{font:inherit;font-size:14px;font-weight:400;border:none;border-radius:10px;padding:9px 16px;min-height:40px;cursor:pointer;color:#fff;letter-spacing:.3px}' +
        '.btn.crit{background:linear-gradient(180deg,#ff3b6a,#e01e52)}.btn.go{background:linear-gradient(180deg,#38d888,#1fae67);color:#06231a}.btn.no{background:rgba(255,255,255,.08);color:#c7ccd3}' +
        '.btn:focus-visible{outline:2px solid #ff1e6f;outline-offset:2px}' +
        '.rhint{display:flex;align-items:center;gap:8px;margin-top:12px;font-size:12px;color:#ffd8a3;background:rgba(255,157,47,.08);padding:8px 10px;border-radius:10px}' +
        '.rhint .dot{width:7px;height:7px;border-radius:50%;background:#ff9d2f;flex:0 0 auto}' +
        '.cf{margin-top:12px;padding:10px 12px;border-radius:12px;background:rgba(255,77,106,.10)}' +
        '.cq{display:block;font-size:13px;color:#ffc2cd;margin-bottom:8px}.cfb{display:flex;gap:8px}' +
        '.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(86px,1fr));gap:10px 8px;margin-top:16px;border-top:1px solid rgba(255,255,255,.06);padding-top:14px}' +
        '.stat{display:flex;flex-direction:column;min-width:0}' +
        '.stat b{font-size:26px;font-weight:200;font-variant-numeric:tabular-nums;line-height:1;color:#eef2f7}' +
        '.stat span{font-size:10px;letter-spacing:1.4px;color:#8b929c;margin-top:5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
        '.acc{border-top:1px solid rgba(255,255,255,.06)}' +
        '.ah{display:flex;align-items:center;justify-content:space-between;padding:13px 2px;cursor:pointer;font-size:12px;letter-spacing:1.8px;color:#aab1bb}' +
        '.ah:focus-visible{outline:2px solid #ff1e6f;outline-offset:-2px;border-radius:6px}' +
        '.ah .ch{transition:transform .18s ease;color:#6b727c;font-size:18px}.ah.op .ch{transform:rotate(90deg);color:#ff5c95}' +
        '.ab{padding:0 2px 8px}' +
        '.row{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:11px 0;font-size:14px;border-top:1px solid rgba(255,255,255,.05);min-height:44px}' +
        '.row[data-act]{cursor:pointer}.row .rk{color:#c7ccd3;display:flex;align-items:center;gap:8px}.row .rv{color:#8b929c;font-weight:300;white-space:nowrap}' +
        '.sd{width:8px;height:8px;border-radius:50%;flex:0 0 auto}.sd.ok{background:#35d07f}.sd.warn{background:#ff9d2f}.sd.crit{background:#ff4d6a}' +
        '.tgl{position:relative;width:46px;height:26px;border-radius:14px;border:none;background:rgba(255,255,255,.12);cursor:pointer;padding:0;flex:0 0 auto}' +
        '.tgl .kn{position:absolute;top:3px;left:3px;width:20px;height:20px;border-radius:50%;background:#eef2f7;transition:left .16s ease}' +
        '.tgl.on{background:#ff1e6f}.tgl.on .kn{left:23px}.tgl.dis{opacity:.4;cursor:not-allowed}.tgl:focus-visible{outline:2px solid #ff1e6f;outline-offset:2px}' +
        '.skel{margin-top:16px}.sk{height:16px;border-radius:8px;background:linear-gradient(90deg,#14181d,#1e242b,#14181d);background-size:200% 100%;animation:shim 1.3s linear infinite;margin-bottom:12px}.sk1{width:60%;height:44px}.sk2{width:85%}.sk3{width:40%}' +
        '.steam .sp,.donering{transform-box:fill-box;transform-origin:center}' +
        '.stream,.donering{opacity:0}' +
        '@keyframes steam{0%{opacity:0;transform:translateY(6px) scaleX(.7)}30%{opacity:.5}100%{opacity:0;transform:translateY(-20px) scaleX(1.35)}}' +
        '@keyframes glowp{0%,100%{opacity:.22}50%{opacity:.6}}' +
        '@keyframes breathe{0%,100%{opacity:.10}50%{opacity:.28}}' +
        '@keyframes streamf{0%{opacity:.2}50%{opacity:.95}100%{opacity:.2}}' +
        '@keyframes brew{0%{transform:translateY(28px)}100%{transform:translateY(7px)}}' +
        '@keyframes donep{0%{opacity:.85;transform:scale(.7)}100%{opacity:0;transform:scale(1.7)}}' +
        '@keyframes sheen{0%{transform:translateX(0)}100%{transform:translateX(46px)}}' +
        '@keyframes shim{0%{background-position:200% 0}100%{background-position:-200% 0}}' +
        '.s-run .steam .sp{animation:steam 2.6s ease-in infinite}.s-run .steam .sp:nth-child(2){animation-delay:.85s}.s-run .steam .sp:nth-child(3){animation-delay:1.6s}' +
        '.s-run .stream{opacity:1}.s-run .stream rect{animation:streamf 1.05s ease-in-out infinite}' +
        '.s-run .glow{animation:glowp 2.4s ease-in-out infinite}.s-run .dsheen{animation:sheen 1.6s ease-in-out infinite alternate}' +
        '.s-ready .glow{animation:breathe 4.6s ease-in-out infinite}' +
        '.s-run.indet .coffeeWrap{animation:brew 3.2s ease-in-out infinite alternate}' +
        '.s-done .donering{opacity:1;animation:donep 1.1s ease-out 3}.s-done .glow{animation:glowp 1.2s ease-in-out 3}' +
        '.s-off .machine{filter:grayscale(.6) brightness(.62);opacity:.72}' +
        '@media(prefers-reduced-motion:reduce){.card *{animation:none!important}.steam{opacity:0!important}}' +
        '@media(max-width:420px){.hero{flex-direction:column}.machine{max-width:150px;align-self:center}.read{text-align:center;align-items:center}.maint,.act,.cf,.rhint{align-self:stretch}}' +
        '</style>';
    }
  }
  customElements.define('coffee-machine-card', CoffeeMachineCard);
  window.customCards = window.customCards || [];
  window.customCards.push({ type: 'coffee-machine-card', name: 'Kaffeevollautomat', description: 'Home-Connect Kaffeevollautomat \u2013 plastische, animierte Metrology-Karte' });
}
