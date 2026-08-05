// spueler-card - Geschirrspueler: plastische Live-Grafik + volle Bedien-Oberflaeche (Metrology)
// REINER ASCII-Quelltext. Nicht-ASCII ausschliesslich als @NNN; -> D() oder als \uXXXX.
// D() NUR ueber statische Template-Teile, NIE ueber dynamische Sensor-Strings (esc()).
const D = s => s.replace(/@(\d+);/g, (m, n) => String.fromCharCode(+n));
const E = c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]);
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, E);

const T = {
  title: D('GESCHIRRSP@220;LER'),
  rest: 'RESTZEIT', prog: 'PROGRAMM', phase: 'PHASE', opts: 'OPTIONEN',
  delayLbl: 'STARTVORWAHL', ctrl: 'STEUERUNG',
  salt: 'SALZ', rinse: D('KLARSP@220;LER'), door: D('T@220;R'),
  run: D('l@228;uft'), done: 'fertig', off: 'aus', standby: 'Standby',
  pause: 'pausiert', idle: 'bereit', delayed: 'Vorwahl aktiv',
  dOpen: D('T@252;r offen'), dClosed: D('T@252;r geschlossen'),
  since: 'offen seit', ok: 'ok', low: 'niedrig', level: D('F@252;llstand'), demo: 'DEMO',
  warnIcon: D('@9888;'), lowRefill: D('niedrig \u2013 bitte nachf@252;llen'),
  oHyg: D('Hygiene-Sp@252;lung'), oDry: 'Extra-Trocknen', oZone: 'Intensivzone',
  aStart: 'Start', aPause: 'Pause', aResume: 'Fortsetzen', aStop: 'Stopp',
  qStart: D('Programm wirklich starten?'), qStop: D('Lauf wirklich abbrechen?'),
  yes: 'Ja', no: 'Abbrechen',
  remoteOff: D('Fernsteuerung am Ger@228;t nicht aktiviert'),
  remotePartial: D('Nur nicht-sicherheitsrelevante Befehle m@246;glich')
};

// Reihenfolge = Prioritaet (erste Regex gewinnt). Getestet gegen die ROHEN
// Enum-Keys der cyclePhase (PREWASH/MAINWASH/COLDRINSE/HOTRINSE/EXTRARINSE/
// DRYING/ADO_DRYING) plus deutsche Fallbacks fuer den Demo-Modus.
const PHASE_FRAC = [
  [/prewash|vor/i, 0.12], [/mainwash|haupt|main/i, 0.45],
  [/rinse|klar|spuel/i, 0.75], [/dry|trock/i, 0.98]
];

// Umgangssprachlicher Fallback fuer Phasen/Programm, falls hass.formatEntityState
// (der von HA in die Benutzersprache uebersetzte Anzeigewert) nicht verfuegbar
// ist. Keys = echte cyclePhase-Enums. Umlaute NUR ueber @NNN;+D().
const LOCALMAP = {
  PREWASH: D('Vorw@228;sche'), MAINWASH: D('Hauptw@228;sche'),
  COLDRINSE: D('Kaltsp@252;len'), HOTRINSE: D('Klarsp@252;len'),
  EXTRARINSE: D('Extra-Sp@252;len'), DRYING: 'Trocknen',
  ADO_DRYING: D('Trocknen (T@252;r-Auto)'), UNAVAILABLE: ''
};

if (!customElements.get('electrolux-ocp-card')) {
  class SpuelerCard extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: 'open' });
      this._sig = null; this._open = null; this._ctrl = false; this._confirm = null; this._wasOpen = false;
      this.shadowRoot.addEventListener('click', e => this._tap(e));
      this.shadowRoot.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this._tap(e); }
      });
    }

    setConfig(cfg) {
      this._cfg = cfg || {};
      this._ent = this._cfg.entities || {};
      this._demo = !this._ent || Object.keys(this._ent).length === 0;
      this._progList = [D('Eco 50@176;'), D('Intensiv 70@176;'), 'Auto', D('Glas 45@176;'), D('Schnell 60@176;')];
      this._demoSel = this._progList[0];
      this._demoOpt = [true, true, false];
      this._demoDly = 0;
      this._sig = null; this._open = null; this._ctrl = false; this._confirm = null; this._wasOpen = false;
      this._render();
    }
    getCardSize() { return 9; }
    set hass(h) {
      this._hass = h;
      const sig = JSON.stringify(this._model().sig);
      if (sig === this._sig) return;
      this._sig = sig; this._render();
    }
    get hass() { return this._hass; }
    _rerender() { this._sig = null; this._render(); }

    _st(key) {
      const id = this._ent[key], h = this._hass;
      if (!h || !h.states || !id) return null;
      const o = h.states[id];
      if (!o) return null;
      const s = o.state;
      if (s == null || s === 'unavailable' || s === 'unknown' || s === '') return null;
      return o;
    }
    _sv(key) { const o = this._st(key); return o ? o.state : null; }
    // Von HA uebersetzter Anzeigewert (z.B. "Vorwaesche" statt "PREWASH").
    // formatEntityState liefert den in der HA-Sprache uebersetzten State; als
    // Fallback greift der interne LOCALMAP, sonst der rohe Wert.
    _disp(key) {
      const id = this._ent[key];
      const stateObj = (this._hass && this._hass.states && id) ? this._hass.states[id] : null;
      if (!stateObj) return null;
      const raw = stateObj.state;
      if (raw == null || raw === 'unavailable' || raw === 'unknown' || raw === '') return null;
      const disp = (this._hass && this._hass.formatEntityState)
        ? this._hass.formatEntityState(stateObj)
        : (LOCALMAP[String(raw).toUpperCase()] || raw);
      return (disp == null || disp === '') ? null : disp;
    }
    // Klarspueler als schlichte Zahl (kein Prozent, keine Warn-Logik).
    _rinseVal() {
      const o = this._st('rinse');
      if (!o) return null;
      const raw = String(o.state).trim();
      const n = parseFloat(raw.replace(',', '.'));
      if (raw !== '' && isFinite(n)) return String(Math.round(n));
      return raw || null;
    }
    _bool(s) { return ['on', 'true', '1', 'enabled', 'open', 'offen'].indexOf(String(s).toLowerCase()) > -1; }
    // Optionaler Niedrig-Warnsensor (binary_sensor). true nur bei 'on'.
    _binOn(key) { const o = this._st(key); return o ? this._bool(o.state) : false; }
    // Grafische Niedrig-Warnung: Warn-Icon + optionaler Wert + Klartext.
    _warnVal(levelTag) {
      return '<span class="warncell"><span class="wi" aria-hidden="true">' + T.warnIcon + '</span>' +
        (levelTag ? '<span class="tag w">' + levelTag + '</span>' : '') +
        '<span class="wtxt">' + T.lowRefill + '</span></span>';
    }
    _level(key, demo) {
      if (this._demo) return demo;
      const o = this._st(key);
      if (!o) return null;
      const raw = String(o.state).trim();
      const n = parseFloat(raw.replace('%', '').replace(',', '.'));
      if (raw !== '' && isFinite(n) && /^[\d.,%\s]+$/.test(raw)) {
        const pct = Math.max(0, Math.min(100, Math.round(n)));
        return { pct, warn: pct <= 15, txt: pct + '%' };
      }
      const lo = /low|empty|leer|niedrig|nachf/i.test(raw);
      return { pct: lo ? 12 : 82, warn: lo, txt: lo ? T.low : T.ok };
    }
    _since(key) {
      const o = this._st(key);
      if (!o || !o.last_changed) return null;
      const min = (Date.now() - new Date(o.last_changed).getTime()) / 60000;
      if (!isFinite(min) || min < 0) return null;
      return min < 60 ? Math.round(min) + ' Min' : Math.floor(min / 60) + ' h';
    }
    _fmtTime(v) {
      if (v == null) return null;
      const s = String(v).trim();
      if (s.indexOf(':') > -1) { const p = s.split(':'); return p[0] + ':' + (p[1] || '00').padStart(2, '0'); }
      const n = parseFloat(s);
      if (!isFinite(n)) return null;
      const min = Math.max(0, Math.round(n));
      return Math.floor(min / 60) + ':' + String(min % 60).padStart(2, '0');
    }

    _model() {
      const dm = this._demo, en = this._ent;
      if (dm) {
        const opts = [{ label: T.oHyg, on: this._demoOpt[0] }, { label: T.oDry, on: this._demoOpt[1] }, { label: T.oZone, on: this._demoOpt[2] }];
        return {
          demo: true, bucket: 'run', running: true, doorOpen: false, doorSince: null,
          program: this._demoSel, phase: D('Hauptw@228;sche'), timeTxt: '1:47', progress: 0.45,
          stateLabel: T.run, salt: { pct: 74, warn: false, txt: T.ok }, saltShown: true, saltLow: false,
          rinse: '8', rinseShown: true, rinseLow: true,
          remote: true, remoteMode: 'enabled', cmd: null, hasCtrl: true, prog: { current: this._demoSel, list: this._progList },
          opts, delay: { idx: this._demoDly },
          sig: 'demo|' + this._demoSel + '|' + this._demoOpt.join('') + '|' + this._demoDly + '|' + this._open + '|' + this._ctrl + '|' + this._confirm
        };
      }
      const rawState = (this._sv('state') || '').toLowerCase();
      const runEnt = this._sv('running');
      const timeTxt = this._fmtTime(this._sv('time_remaining'));
      const program = this._sv('program');
      const programDisp = this._disp('program');
      const phase = this._sv('phase');
      const phaseDisp = this._disp('phase');
      const doorOpen = this._bool((this._sv('door') || '').toLowerCase());
      const runByEnt = ['on', 'true', 'running'].indexOf(String(runEnt).toLowerCase()) > -1;

      let bucket = 'idle';
      if (/finish|end|fertig|complet|clean|ready_ended/.test(rawState)) bucket = 'done';
      else if (/pause/.test(rawState)) bucket = 'pause';
      else if (/delay/.test(rawState)) bucket = 'delayed';
      else if (/run|wash|active|drying|rinsing/.test(rawState) || runByEnt) bucket = 'run';
      else if (/standby/.test(rawState)) bucket = 'standby';
      else if (/off|aus/.test(rawState) || (!rawState && !runEnt && !timeTxt)) bucket = 'off';
      if (bucket !== 'run' && (runByEnt || (phase && timeTxt && timeTxt !== '0:00'))) bucket = 'run';

      let progress = 0;
      const pn = parseFloat(this._sv('progress'));
      if (isFinite(pn)) progress = Math.max(0, Math.min(1, pn > 1 ? pn / 100 : pn));
      else if (phase) { const hit = PHASE_FRAC.find(p => p[0].test(phase)); progress = hit ? hit[1] : 0.3; }
      if (bucket === 'done') progress = 1;

      // remote_control ist ein STRING (ENABLED / NOT_SAFETY_RELEVANT_ENABLED /
      // DISABLED). Fuer Rueckwaertskompatibilitaet wird auch eine bool-artige
      // Fernsteuerung (on/off) korrekt interpretiert.
      let remote = true, remoteMode = 'enabled';
      if (en.remote_control) {
        const o = this._st('remote_control');
        const rv = (o ? String(o.state) : '').toUpperCase();
        if (rv.indexOf('NOT_SAFETY') > -1) { remote = true; remoteMode = 'partial'; }
        else if (rv === 'ENABLED' || rv === 'ON' || rv === 'TRUE' || rv === '1') { remote = true; remoteMode = 'enabled'; }
        else { remote = false; remoteMode = 'disabled'; }
      }

      let prog = null;
      if (en.program_select) {
        const o = this._st('program_select');
        prog = o ? { current: o.state, list: (o.attributes && Array.isArray(o.attributes.options)) ? o.attributes.options : [] } : { current: null, list: [] };
      }
      // Optionen: bevorzugt generische Liste option_switches:[{entity,label}];
      // Fallback auf das alte options:{...}-Objekt (Rueckwaertskompatibilitaet).
      let opts;
      if (Array.isArray(en.option_switches)) {
        opts = en.option_switches.filter(x => x && x.entity).map(x => {
          const o = this._hass && this._hass.states[x.entity];
          return { label: x.label || x.entity, entity: x.entity, on: o ? this._bool(o.state) : false };
        });
      } else {
        const oc = en.options || {};
        const map = [['hygiene_rinse', T.oHyg], ['extra_dry', T.oDry], ['intensive_zone', T.oZone]];
        opts = map.filter(x => oc[x[0]]).map(x => {
          const o = this._hass && this._hass.states[oc[x[0]]];
          return { label: x[1], entity: oc[x[0]], on: o ? this._bool(o.state) : false };
        });
      }
      this._optRefs = opts;
      let delay = null;
      if (en.delay) { const o = this._st('delay'); let idx = 0; if (o) { const n = parseFloat(o.state); if (isFinite(n)) idx = n <= 0 ? 0 : (n <= 60 ? 1 : 2); } delay = { idx }; }

      // command_select: EIN Select fuer Start/Pause/Fortsetzen/Stopp. Es werden
      // nur die tatsaechlich vorhandenen Kommando-Optionen aufgeloest.
      let cmd = null;
      if (en.command_select) {
        cmd = { start: this._cmdOption('start'), pause: this._cmdOption('pause'), resume: this._cmdOption('resume'), stop: this._cmdOption('stop') };
      }

      const hasCtrl = !!(en.program_select || opts.length || en.delay || en.command_select || en.start_button || en.pause_button || en.resume_button || en.stop_button);
      const labels = { run: T.run, done: T.done, off: T.off, standby: T.standby, pause: T.pause, idle: T.idle, delayed: T.delayed };

      // Klarspueler-/Salz-Niedrigwarnung. Bevorzugt dedizierter binary_sensor
      // (rinse_low/salt_low == 'on'); fuer Klarspueler ohne solchen Sensor als
      // Heuristik der numerische Wert <= 2.
      const salt = this._level('salt', null);
      const rinse = this._rinseVal();
      const rinseLow = en.rinse_low
        ? this._binOn('rinse_low')
        : (rinse != null && isFinite(parseFloat(rinse)) && parseFloat(rinse) <= 2);
      const saltLow = en.salt_low ? this._binOn('salt_low') : false;
      // SALZ nur zeigen, wenn ein Salz-Wert ODER ein salt_low-Sensor da ist.
      const saltShown = !!(salt || en.salt_low);
      const rinseShown = !!(rinse != null || en.rinse_low);

      const m = {
        demo: false, bucket, running: bucket === 'run', doorOpen,
        doorSince: doorOpen ? this._since('door') : null,
        program: programDisp || (prog && prog.current) || null, phase: phaseDisp || null, timeTxt, progress,
        stateLabel: doorOpen ? T.dOpen : labels[bucket],
        salt, saltShown, saltLow, rinse, rinseShown, rinseLow,
        remote, remoteMode, cmd, hasCtrl, prog, opts, delay
      };
      m.sig = [bucket, doorOpen, timeTxt, m.program, phase, Math.round(progress * 100),
        m.salt && m.salt.pct, m.salt && m.salt.warn, saltShown, saltLow, m.rinse, rinseShown, rinseLow,
        remoteMode, prog && prog.current, opts.map(o => o.on ? 1 : 0).join(''), delay && delay.idx,
        cmd && [cmd.start, cmd.pause, cmd.resume, cmd.stop].map(c => c ? 1 : 0).join(''),
        this._open, this._ctrl, this._confirm].join('|');
      return m;
    }

    _actList(m) {
      const dm = this._demo, en = this._ent, b = m.bucket, cmd = m.cmd;
      // Eine Aktion ist "verdrahtet", wenn sie ueber command_select verfuegbar
      // ist ODER eine (Legacy-)Button-Entity konfiguriert ist ODER im Demo.
      const wired = (ck, cmdKey) => dm || !!(cmd && cmd[cmdKey]) || !!en[ck];
      const mk = (key, label, ck, cmdKey, buckets, crit) => ({
        key, label, cmdKey,
        show: wired(ck, cmdKey),
        enabled: buckets.indexOf(b) > -1 && m.remote,
        crit
      });
      // Zustandsabhaengige Freigabe (Buckets):
      //   START  bei OFF/IDLE/READY_TO_START/END_OF_CYCLE
      //   PAUSE  bei RUNNING
      //   RESUME bei PAUSED
      //   STOP   bei RUNNING/PAUSED/DELAYED_START/END_OF_CYCLE
      return [
        mk('as', T.aStart, 'start_button', 'start', ['idle', 'off', 'ready', 'done'], true),
        mk('ap', T.aPause, 'pause_button', 'pause', ['run'], false),
        mk('ar', T.aResume, 'resume_button', 'resume', ['pause'], false),
        mk('ax', T.aStop, 'stop_button', 'stop', ['run', 'pause', 'delayed', 'done'], true)
      ].filter(a => a.show);
    }
    _actEntity(k) { const e = this._ent; return { as: e.start_button, ap: e.pause_button, ar: e.resume_button, ax: e.stop_button }[k]; }
    // Loese das tatsaechliche command_select-Options-Wort fuer ein logisches
    // Kommando auf (Gross-/Kleinschreibung robust; kleine Alias-Liste).
    _cmdOption(cmdKey) {
      const id = this._ent.command_select, o = id && this._hass && this._hass.states[id];
      const opts = (o && o.attributes && Array.isArray(o.attributes.options)) ? o.attributes.options : [];
      const aliases = { start: ['START'], pause: ['PAUSE'], resume: ['RESUME'], stop: ['STOPRESET', 'STOP', 'RESET', 'ABORT'] }[cmdKey] || [];
      for (let i = 0; i < aliases.length; i++) {
        const hit = opts.find(x => String(x).toUpperCase() === aliases[i]);
        if (hit != null) return hit;
      }
      return null;
    }
    _call(id, service, extra) {
      if (!this._hass || !id || String(id).indexOf('.') < 0) return;
      const dom = id.split('.')[0];
      try { this._hass.callService(dom, service, Object.assign({ entity_id: id }, extra || {})); } catch (e) { /* ruhig */ }
    }
    _runAct(k) {
      if (this._demo) return;
      const cmdKey = { as: 'start', ap: 'pause', ar: 'resume', ax: 'stop' }[k];
      const cs = this._ent.command_select;
      if (cs && cmdKey) {
        const opt = this._cmdOption(cmdKey);
        if (opt != null) { this._call(cs, 'select_option', { option: opt }); return; }
      }
      // Fallback: Legacy-Button-Entities (button.press)
      const id = this._actEntity(k);
      if (id) this._call(id, 'press');
    }
    _pickProg(i) {
      if (this._demo) { this._demoSel = this._progList[i]; return; }
      const id = this._ent.program_select, o = id && this._hass && this._hass.states[id];
      const list = (o && o.attributes && o.attributes.options) || [];
      if (list[i] != null) this._call(id, 'select_option', { option: list[i] });
    }
    _pickDelay(i) {
      if (this._demo) { this._demoDly = i; return; }
      const id = this._ent.delay; if (!id) return;
      if (id.split('.')[0] === 'number') this._call(id, 'set_value', { value: [0, 60, 180][i] });
      else this._call(id, 'select_option', { option: ['Aus', '+1 Std', '+3 Std'][i] });
    }
    _toggleOpt(i) {
      if (this._demo) { this._demoOpt[i] = !this._demoOpt[i]; return; }
      const r = this._optRefs && this._optRefs[i]; if (r && r.entity) this._call(r.entity, 'toggle');
    }
    _tap(e) {
      let n = e.target, act = null;
      while (n && n !== this.shadowRoot) { if (n.dataset && n.dataset.act) { act = n.dataset.act; break; } n = n.parentNode; }
      if (!act) return;
      if (act === 'ct') { this._ctrl = !this._ctrl; return this._rerender(); }
      if (['door', 'prog', 'time', 'salt', 'rinse'].indexOf(act) > -1) { this._open = this._open === act ? null : act; return this._rerender(); }
      if (!this._model().remote) return;
      if (act === 'cn') { this._confirm = null; return this._rerender(); }
      if (act === 'cy') { const k = this._confirm; this._confirm = null; this._runAct(k); return this._rerender(); }
      if (act[0] === 'p') { this._pickProg(+act.slice(1)); return this._rerender(); }
      if (act[0] === 'd') { this._pickDelay(+act.slice(1)); return this._rerender(); }
      if (act[0] === 'o') { this._toggleOpt(+act.slice(1)); return this._rerender(); }
      if (act === 'as' || act === 'ax') { this._confirm = act; return this._rerender(); }
      if (act === 'ap' || act === 'ar') { this._runAct(act); return this._rerender(); }
    }

    // ---- Plastische Grafik: gemeinsame Gradienten/Filter einmal in <defs> ----
    _defs() {
      return '<defs>' +
        '<linearGradient id="gb" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#343941"/><stop offset="0.5" stop-color="#1a1e24"/><stop offset="1" stop-color="#0c0e11"/></linearGradient>' +
        '<linearGradient id="gs" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#454b54"/><stop offset="1" stop-color="#20242a"/></linearGradient>' +
        '<linearGradient id="gh" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0.30"/><stop offset="0.45" stop-color="#fff" stop-opacity="0"/></linearGradient>' +
        '<radialGradient id="gi" cx="0.5" cy="0.3" r="0.85"><stop offset="0" stop-color="#525a64"/><stop offset="1" stop-color="#101216"/></radialGradient>' +
        '<linearGradient id="gd" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3a404a"/><stop offset="1" stop-color="#22262c"/></linearGradient>' +
        '<filter id="sh" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="5"/></filter>' +
        // Geschirr-Symbole (einmal definiert, per <use> vervielfacht -> sparsam)
        '<ellipse id="pl" rx="2.6" ry="16" fill="#d3dae2" fill-opacity="0.22" stroke="#eef2f7" stroke-width="0.8"/>' +
        '<path id="gl" d="M-5 0L5 0L3.4 -12L-3.4 -12Z" fill="#bcd6ea" fill-opacity="0.20" stroke="#e6f0f8" stroke-width="0.8" stroke-linejoin="round"/>' +
        '<g id="pt"><rect x="-12" y="-13" width="24" height="15" rx="2.5" fill="#c9d0d9" fill-opacity="0.22" stroke="#eef2f7" stroke-width="1"/><path d="M-12 -8h-4M12 -8h4" stroke="#eef2f7" stroke-width="1" fill="none"/></g>' +
        '<path id="bw" d="M-11 -7A11 8 0 0 0 11 -7" fill="#c9d0d9" fill-opacity="0.22" stroke="#eef2f7" stroke-width="1" stroke-linejoin="round"/>' +
        '</defs>';
    }
    // TUER ZU: solide, glaenzende Front
    _closedSvg(m) {
      const run = m.running;
      const disp = run ? (m.timeTxt || '0:00') : (m.bucket === 'off' ? '' : '--:--');
      const dCol = run ? '#ff5c95' : '#5b626c';
      const pw = run ? '#ff1e6f' : (m.bucket === 'off' ? '#2a2e34' : '#41474f');
      const salt = ((m.salt && m.salt.warn) || m.saltLow) ? '#ff4d6a' : '#3a3f47';
      const rinse = m.rinseLow ? '#ff4d6a' : '#3a3f47';
      return '<ellipse cx="120" cy="322" rx="94" ry="12" fill="#000" opacity="0.55" filter="url(#sh)"/>' +
        '<rect x="40" y="14" width="160" height="300" rx="12" fill="url(#gb)" stroke="#4a505a" stroke-width="1.2"/>' +
        '<rect x="40" y="14" width="160" height="44" rx="12" fill="url(#gs)"/>' +
        '<rect x="40" y="52" width="160" height="6" fill="#000" opacity="0.25"/>' +
        // Display
        '<rect x="118" y="24" width="68" height="22" rx="3.5" fill="#07080b" stroke="#000"/>' +
        (run ? '<rect x="118" y="24" width="68" height="22" rx="3.5" fill="#ff1e6f" opacity="0.10"/>' : '') +
        '<text x="152" y="40" text-anchor="middle" font-family="Segoe UI,sans-serif" font-size="14" font-weight="300" letter-spacing="1.5" fill="' + dCol + '">' + esc(disp) + '</text>' +
        // Status-LEDs (Power / Salz / Klarspueler)
        '<circle cx="58" cy="36" r="3.4" fill="' + pw + '"/><circle cx="74" cy="36" r="3.4" fill="' + salt + '"/><circle cx="90" cy="36" r="3.4" fill="' + rinse + '"/>' +
        // Fortschritts-LED-Leiste
        (run ? '<rect x="50" y="62" width="140" height="2.4" rx="1.2" fill="#fff" opacity="0.08"/><rect x="50" y="62" width="' + Math.round(140 * m.progress) + '" height="2.4" rx="1.2" fill="#ff1e6f"/>' : '') +
        // Griff-Leiste mit Highlight
        '<rect x="58" y="72" width="124" height="9" rx="4.5" fill="url(#gs)"/><rect x="60" y="73" width="120" height="2" rx="1" fill="#fff" opacity="0.22"/>' +
        // Glas-Glanz (Reflexion)
        '<rect x="48" y="90" width="144" height="150" rx="8" fill="url(#gh)" opacity="0.5"/>' +
        '<polygon points="150,90 176,90 120,240 96,240" fill="#fff" opacity="0.04"/>' +
        // Boden-Kante / Sockel
        '<rect x="40" y="300" width="160" height="14" rx="6" fill="#000" opacity="0.22"/>' +
        (run ? '<rect x="52" y="306" width="136" height="4" rx="2" fill="#ff1e6f" opacity="0.16"/>' : '');
    }
    // TUER OFFEN: klar aufgeklappt, Blick in beleuchteten Innenraum mit Geschirr (immer STATISCH).
    _openSvg(m, pop) {
      // Perspektivische Wanne - man blickt in die beleuchtete Tiefe hinein
      let s = '<ellipse cx="120" cy="338" rx="106" ry="12" fill="#000" opacity="0.5" filter="url(#sh)"/>' +
        '<rect x="38" y="12" width="164" height="250" rx="10" fill="url(#gb)" stroke="#4a505a" stroke-width="1.2"/>' +
        '<rect x="72" y="46" width="96" height="164" fill="url(#gi)"/>' +
        '<polygon points="50,24 190,24 168,46 72,46" fill="#fff" opacity="0.07"/>' +
        '<polygon points="50,248 190,248 168,210 72,210" fill="#000" opacity="0.14"/>' +
        '<polygon points="50,24 72,46 72,210 50,248" fill="#000" opacity="0.24"/>' +
        '<polygon points="190,24 168,46 168,210 190,248" fill="#000" opacity="0.24"/>' +
        '<ellipse cx="120" cy="72" rx="58" ry="22" fill="#fff" opacity="0.06"/>' +
        '<rect x="50" y="24" width="140" height="224" rx="6" fill="none" stroke="#4a505a" stroke-width="1.2"/>';
      // Drahtkoerbe + statischer Sprueharm (kein Betrieb bei offener Tuer)
      s += '<g fill="none" stroke="#c8ced7" stroke-width="1" opacity="0.4">' +
        '<rect x="80" y="104" width="82" height="24" rx="3"/>' +
        '<rect x="64" y="176" width="114" height="42" rx="3"/>' +
        '<line x1="120" y1="230" x2="120" y2="246"/><line x1="98" y1="238" x2="142" y2="238"/></g>';
      // Geschirr: oben Glaeser (umgedreht) + Schuessel, unten Topf + Teller hochkant (vorn)
      s += '<g>';
      for (let x = 92; x <= 152; x += 15) s += '<use href="#gl" x="' + x + '" y="125"/>';
      s += '<use href="#bw" x="96" y="188"/><use href="#pt" x="142" y="187"/>';
      for (let x = 74; x <= 166; x += 11) s += '<use href="#pl" x="' + x + '" y="202"/>';
      s += '</g>';
      // Besteckkorb vorn
      s += '<g fill="none" stroke="#c8ced7" stroke-width="1" opacity="0.5"><rect x="100" y="222" width="40" height="20" rx="2"/><line x1="110" y1="225" x2="110" y2="239"/><line x1="120" y1="225" x2="120" y2="239"/><line x1="130" y1="225" x2="130" y2="239"/></g>';
      // Aufgeklappte Tuer (Innenseite mit Spuelmittel-Fach; Feder-Pop nur beim Uebergang zu offen)
      s += '<g class="door' + (pop ? ' pop' : '') + '">' +
        '<polygon points="50,248 190,248 212,326 28,326" fill="url(#gd)" stroke="#4a505a" stroke-width="1.1"/>' +
        '<polygon points="50,248 190,248 188,257 52,257" fill="#fff" opacity="0.12"/>' +
        '<g fill="#000" fill-opacity="0.18" stroke="#c8ced7" stroke-width="0.9" opacity="0.6">' +
        '<rect x="96" y="278" width="46" height="20" rx="2.5"/><circle cx="156" cy="292" r="5" fill="none"/></g>' +
        '</g>';
      return s;
    }
    _svg(m) {
      const pop = m.doorOpen && this._justOpened;
      const body = m.doorOpen ? this._openSvg(m, pop) : this._closedSvg(m);
      return '<svg viewBox="0 0 240 350" role="img" aria-label="' + esc(T.title + ' - ' + m.stateLabel) + '">' + this._defs() + body + '</svg>';
    }

    _bar(pct, warn) {
      const w = Math.max(3, Math.min(100, pct == null ? 0 : pct));
      return '<span class="gauge"><i style="width:' + w + '%' + (warn ? ';background:#ff9d2f' : '') + '"></i></span>';
    }
    _detail(m) {
      const k = this._open; if (!k) return '';
      let t = '';
      if (k === 'door') t = (m.doorOpen ? T.dOpen : T.dClosed) + (m.doorSince ? ' \u2013 ' + T.since + ' ' + esc(m.doorSince) : '');
      else if (k === 'prog') t = T.prog + ': ' + esc(m.program || '\u2014') + '  \u2013  ' + T.phase + ': ' + esc(m.phase || '\u2014');
      else if (k === 'time') t = m.running ? (T.rest + ': ' + esc(m.timeTxt || '\u2014')) : esc(m.stateLabel);
      else if (k === 'salt') t = T.salt + (m.salt ? ' \u2013 ' + T.level + ': ' + esc(m.salt.txt) : '') + (m.saltLow ? ' \u2013 ' + T.lowRefill : '');
      else if (k === 'rinse') t = T.rinse + ': ' + (m.rinse ? esc(m.rinse) : '\u2014') + (m.rinseLow ? ' \u2013 ' + T.lowRefill : '');
      return '<div class="det">' + t + '</div>';
    }
    _row(act, k, inner, cls) {
      const open = this._open === act;
      return '<div class="row" data-act="' + act + '" role="button" tabindex="0" aria-expanded="' + open + '">' +
        '<span class="k">' + k + '</span><span class="' + (cls || 'v') + '">' + inner + '</span></div>';
    }
    _seg(list, current, prefix) {
      return '<div class="seg">' + list.map((o, i) => '<button class="chip' + (o === current ? ' on' : '') + '" data-act="' + prefix + i + '" type="button">' + esc(o) + '</button>').join('') + '</div>';
    }
    _grp(label, inner) { return '<div class="grp"><span class="glbl">' + label + '</span>' + inner + '</div>'; }

    _ctrlBlock(m) {
      if (!m.hasCtrl) return '';
      const open = this._ctrl;
      let inner = '';
      if (open) {
        const off = !m.remote;
        let body = '';
        if (off) body += '<div class="hint"><span class="dot warn"></span>' + T.remoteOff + '</div>';
        else if (m.remoteMode === 'partial') body += '<div class="hint soft">' + T.remotePartial + '</div>';
        if (m.prog && m.prog.list && m.prog.list.length) body += this._grp(T.prog, this._seg(m.prog.list, m.prog.current, 'p'));
        if (m.opts && m.opts.length) {
          const tg = m.opts.map((o, i) => '<div class="tgl" data-act="o' + i + '" role="button" tabindex="0" aria-pressed="' + o.on + '"><span class="k">' + esc(o.label) + '</span><span class="sw' + (o.on ? ' on' : '') + '"><i></i></span></div>').join('');
          body += this._grp(T.opts, tg);
        }
        if (m.delay) body += this._grp(T.delayLbl, this._seg(['Aus', '+1 Std', '+3 Std'], ['Aus', '+1 Std', '+3 Std'][m.delay.idx], 'd'));
        if (this._confirm) {
          const q = this._confirm === 'ax' ? T.qStop : T.qStart;
          body += '<div class="ctrlbar"><span class="ask">' + q + '</span><button class="cbtn no" data-act="cn" type="button">' + T.no + '</button><button class="cbtn yes" data-act="cy" type="button">' + T.yes + '</button></div>';
        } else {
          const acts = this._actList(m);
          if (acts.length) body += '<div class="acts">' + acts.map(a => '<button class="abtn' + (a.crit ? ' crit' : '') + (a.enabled ? '' : ' dis') + '"' + (a.enabled ? ' data-act="' + a.key + '"' : ' disabled') + ' type="button">' + esc(a.label) + '</button>').join('') + '</div>';
        }
        inner = '<div class="ctrl' + (off ? ' off' : '') + '">' + body + '</div>';
      }
      return '<div class="ctrl-hd" data-act="ct" role="button" tabindex="0" aria-expanded="' + open + '"><span class="k">' + T.ctrl + '</span><span class="chev">' + (open ? '\u2013' : '+') + '</span></div>' + inner;
    }

    _render() {
      const sr = this.shadowRoot; if (!sr) return;
      const m = this._model();
      this._justOpened = m.doorOpen && this._wasOpen === false;
      this._wasOpen = m.doorOpen;
      const heroBig = m.running;
      const hero = m.running ? esc(m.timeTxt || '\u2014') : esc(m.stateLabel);
      const dotCls = m.bucket === 'run' ? 'run' : ((m.doorOpen || m.rinseLow || m.saltLow || (m.salt && m.salt.warn)) ? 'warn' : '');
      const pill = m.doorOpen ? T.dOpen : m.stateLabel;
      // SALZ: bei Niedrigwarnung grafische Warnung, sonst Fuellstands-Gauge (falls
      // ein Salz-Wert vorliegt), sonst schlichtes "ok" (nur salt_low konfiguriert).
      let saltV;
      if (m.saltLow) saltV = this._warnVal(m.salt ? esc(m.salt.txt) : '');
      else if (m.salt) saltV = this._bar(m.salt.pct, m.salt.warn) + '<span class="tag' + (m.salt.warn ? ' w' : '') + '">' + esc(m.salt.txt) + '</span>';
      else saltV = '<span class="tag">' + T.ok + '</span>';
      // KLARSPUELER: schlichte Zahl; bei Niedrigwarnung grafische Warnung.
      const rinseV = m.rinseLow
        ? this._warnVal(m.rinse ? esc(m.rinse) : '')
        : (m.rinse ? ('<span class="tag">' + esc(m.rinse) + '</span>') : '\u2014');

      sr.innerHTML =
        '<style>' + this._css() + '</style>' +
        '<div class="card">' +
        '<div class="hd"><span class="ttl">' + T.title + '</span>' +
        '<span class="pill">' + (m.demo ? '<span class="demo">' + T.demo + '</span>' : '') +
        '<span class="dot ' + dotCls + '"></span>' + esc(pill) + '</span></div>' +
        '<div class="wrap">' +
        '<div class="art" data-act="door" role="button" tabindex="0" aria-label="' + esc(T.door) + '">' + this._svg(m) + '</div>' +
        '<div class="col">' +
        '<div class="lbl">' + (m.running ? T.rest : 'STATUS') + '</div>' +
        '<div class="hero' + (heroBig ? '' : ' sm') + '">' + hero + '</div>' +
        '<div class="bar"><i style="width:' + Math.round(m.progress * 100) + '%"></i></div>' +
        '<div class="rows">' +
        this._row('prog', T.prog, esc(m.program || '\u2014')) +
        this._row('time', T.phase, esc(m.phase || '\u2014'), m.running ? 'v acc' : 'v') +
        (m.saltShown ? this._row('salt', T.salt, saltV, 'fv') : '') +
        (m.rinseShown ? this._row('rinse', T.rinse, rinseV, 'fv') : '') +
        '</div></div></div>' +
        this._detail(m) +
        this._ctrlBlock(m) +
        '</div>';
    }

    _css() {
      return D(
        ":host{display:block;font-family:'Segoe UI Variable Text','Segoe UI',system-ui,sans-serif;color:#f4f4f6}" +
        "*{box-sizing:border-box}" +
        ".card{background:#0b0b0d;border:1px solid rgba(255,255,255,.06);border-radius:16px;padding:18px 20px 16px}" +
        ".hd{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}" +
        ".ttl{font-size:12px;letter-spacing:2px;font-weight:600;color:#8f8f96}" +
        ".pill{display:flex;align-items:center;gap:8px;font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:#c7c7cd}" +
        ".dot{width:8px;height:8px;border-radius:50%;background:#4c4c52;flex:none}" +
        ".dot.run{background:#ff1e6f;box-shadow:0 0 9px #ff1e6f}.dot.warn{background:#ff9d2f}" +
        ".demo{font-size:9px;letter-spacing:1.5px;color:#0b0b0d;background:#ff9d2f;padding:2px 6px;border-radius:4px;font-weight:800}" +
        ".wrap{display:grid;grid-template-columns:160px 1fr;gap:24px;align-items:center}" +
        "@media(max-width:470px){.wrap{grid-template-columns:1fr;gap:14px;justify-items:center}.col{width:100%}}" +
        ".art{cursor:pointer;border-radius:8px;outline:none}.art svg{width:100%;height:auto;display:block;max-height:280px}" +
        ".door{transform-box:fill-box;transform-origin:top center}" +
        ".door.pop{animation:dpop .32s cubic-bezier(.34,1.56,.64,1) both}" +
        "@keyframes dpop{0%{transform:scaleY(.06)}100%{transform:scaleY(1)}}" +
        ".col{min-width:0}.lbl,.glbl{font-size:10px;letter-spacing:2.5px;color:#6e6e75;text-transform:uppercase}" +
        ".hero{font-size:68px;line-height:.86;font-weight:200;font-variant-numeric:tabular-nums;letter-spacing:-2px;margin:3px 0 12px}" +
        ".hero.sm{font-size:34px;font-weight:300;letter-spacing:0;text-transform:capitalize}" +
        ".bar{height:4px;border-radius:3px;background:rgba(255,255,255,.09);overflow:hidden}" +
        ".bar>i{display:block;height:100%;background:#ff1e6f;border-radius:3px;transition:width .3s ease}" +
        ".rows{margin-top:14px;display:flex;flex-direction:column}" +
        ".row{display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:44px;padding:6px 0;border-bottom:1px solid rgba(255,255,255,.05);cursor:pointer;outline:none}" +
        ".row:last-child{border-bottom:none}" +
        ".k{font-size:11px;letter-spacing:1.5px;color:#7d7d84;text-transform:uppercase;flex:none}" +
        ".v{font-size:16px;font-weight:300;text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.v.acc{color:#ff1e6f}" +
        ".fv{display:flex;align-items:center;gap:10px}" +
        ".gauge{width:56px;height:5px;border-radius:3px;background:rgba(255,255,255,.09);overflow:hidden;flex:none}" +
        ".gauge>i{display:block;height:100%;background:#dcdce0;border-radius:3px}" +
        ".tag{font-size:12px;letter-spacing:.5px;color:#a9a9af;min-width:34px;text-align:right}.tag.w{color:#ff4d6a}" +
        ".warncell{display:flex;align-items:center;gap:8px;justify-content:flex-end;color:#ff4d6a;min-width:0}" +
        ".warncell .wi{font-size:15px;line-height:1;flex:none}" +
        ".warncell .wtxt{font-size:11.5px;letter-spacing:.2px;color:#ff4d6a;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}" +
        ".det{margin-top:12px;font-size:13px;color:#c2c2c8;background:rgba(255,255,255,.03);border-left:2px solid #ff1e6f;padding:10px 13px;border-radius:0 8px 8px 0;line-height:1.5}" +
        ".ctrl-hd{display:flex;align-items:center;justify-content:space-between;margin-top:8px;min-height:44px;padding:8px 0;border-top:1px solid rgba(255,255,255,.07);cursor:pointer;outline:none}" +
        ".chev{color:#7d7d84;font-size:20px;font-weight:300;line-height:1}" +
        ".ctrl{display:flex;flex-direction:column;gap:16px;padding-top:4px}.ctrl.off{opacity:.42;pointer-events:none}" +
        ".hint{font-size:12px;letter-spacing:.3px;color:#ff9d2f;display:flex;gap:8px;align-items:center}" +
        ".hint.soft{color:#8f8f96}" +
        ".grp{display:flex;flex-direction:column;gap:8px}" +
        ".seg{display:flex;flex-wrap:wrap;gap:8px}" +
        ".chip{font:inherit;font-size:13px;letter-spacing:.3px;color:#c7c7cd;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.1);border-radius:9px;padding:9px 14px;min-height:40px;cursor:pointer}" +
        ".chip.on{color:#0b0b0d;background:#ff1e6f;border-color:#ff1e6f;font-weight:600}" +
        ".tgl{display:flex;align-items:center;justify-content:space-between;min-height:44px;cursor:pointer;outline:none}" +
        ".sw{width:44px;height:24px;border-radius:13px;background:rgba(255,255,255,.13);position:relative;flex:none;transition:background .2s}" +
        ".sw.on{background:#ff1e6f}.sw>i{position:absolute;top:3px;left:3px;width:18px;height:18px;border-radius:50%;background:#fff;transition:left .2s}.sw.on>i{left:23px}" +
        ".acts{display:flex;flex-wrap:wrap;gap:10px}" +
        ".abtn,.cbtn{font:inherit;font-size:13px;letter-spacing:1px;text-transform:uppercase;color:#f4f4f6;background:transparent;border:1px solid rgba(255,255,255,.16);border-radius:9px;min-height:44px;cursor:pointer}" +
        ".abtn{flex:1;min-width:calc(50% - 5px);padding:12px}.cbtn{padding:11px 16px}" +
        ".abtn.crit,.cbtn.yes{color:#ff1e6f;border-color:rgba(255,30,111,.5)}.abtn.dis{opacity:.3;cursor:not-allowed;pointer-events:none}" +
        ".ctrlbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.ask{font-size:13px;color:#ff9d2f;flex:1;min-width:130px}.cbtn.no{opacity:.8}" +
        "[data-act]:focus-visible{outline:2px solid #ff1e6f;outline-offset:2px;border-radius:6px}" +
        "@media(prefers-reduced-motion:reduce){.door.pop{animation:none}.bar>i,.sw,.sw>i{transition:none}}"
      );
    }
  }
  customElements.define('electrolux-ocp-card', SpuelerCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: 'electrolux-ocp-card',
    name: D('Electrolux OCP - Geschirrsp@252;ler'),
    description: D('Plastische Live-Grafik + Bedien-Oberfl@228;che f@252;r Electrolux/AEG Geschirrsp@252;ler (Metrology).'),
    preview: true
  });
}
