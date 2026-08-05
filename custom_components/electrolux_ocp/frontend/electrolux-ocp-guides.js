// electrolux-guides - Zwei gefuehrte Flows fuer die Geschirrspueler-Karte (Metrology/Unison)
//   1) Beladen-Hilfe    : Uebersicht -> Kategorie -> beschriftete Schritte
//   2) Programmassistent: 3-Schritt-Wizard -> Empfehlung -> Programm einstellen
// Eigenstaendig, Shadow-DOM, modaler Overlay. Feuert 'program-apply' {prog,opt}.
// REINER ASCII-Quelltext: alle Umlaute/Gedankenstriche als \uXXXX (0 Non-ASCII).
(function () {
  if (typeof customElements !== 'undefined' && customElements.get('electrolux-guides')) return;

  // HTML-Escape fuer dynamisch injizierte Titel (enthalten '&' etc.).
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  /* =======================================================================
     TEIL A  -  BELADEN-HILFE  (Line-Art an die App-Illustrationen angelehnt)
     ===================================================================== */
  var ICON = {
    glas: '<path d="M14 13H30V27Q30 33 22 33Q14 33 14 27Z"/><path d="M30 17q6 1 6 6q0 5 -6 5"/>',
    teller: '<circle cx="22" cy="22" r="12"/><circle cx="22" cy="22" r="6"/>',
    besteck: '<path d="M15 10V16M18 10V16M21 10V16M18 16V34"/><path d="M29 10V34M26 13q3 1 3 6"/>',
    toepfe: '<path d="M12 18H32V30Q32 34 28 34H16Q12 34 12 30Z"/><path d="M12 22H7M32 22H37"/>'
  };

  function tines(y, h) { var s = '', x; for (x = 44; x <= 196; x += 19) { s += 'M' + x + ' ' + y + 'V' + (y - h); } return s; }
  function rack(kind, dim) {
    var f = kind === 'upper' ? 66 : 148, top = f - 14, h = kind === 'upper' ? 10 : 12;
    return '<g class="rk' + (dim ? ' dim' : '') + '">'
      + '<path d="M34 ' + f + 'H206 M34 ' + f + 'V' + top + ' M206 ' + f + 'V' + top + '"/>'
      + '<path class="tine" d="' + tines(f, h) + '"/></g>';
  }
  function scene(rackHint, inner) {
    return '<svg class="scene-svg" viewBox="0 0 240 176" xmlns="http://www.w3.org/2000/svg" role="img" aria-hidden="true">'
      + '<rect class="tub" x="16" y="10" width="208" height="156" rx="12"/>'
      + rack('upper', rackHint !== 'upper') + rack('lower', rackHint !== 'lower')
      + '<g class="hi">' + inner + '</g></svg>';
  }
  var cup = function (cx) { return '<path d="M' + (cx - 13) + ' 66V50Q' + (cx - 13) + ' 44 ' + (cx - 7) + ' 44H' + (cx + 7) + 'Q' + (cx + 13) + ' 44 ' + (cx + 13) + ' 50V66"/><path d="M' + (cx + 13) + ' 51q9 1 9 8"/>'; };
  var wine = function (cx) { return '<path d="M' + (cx - 11) + ' 66H' + (cx + 11) + '"/><path d="M' + cx + ' 66V53"/>' + '<path d="M' + (cx - 11) + ' 40Q' + (cx - 11) + ' 52 ' + cx + ' 54Q' + (cx + 11) + ' 52 ' + (cx + 11) + ' 40"/>'; };
  var plate = function (cx) { return '<ellipse cx="' + cx + '" cy="120" rx="5.5" ry="26"/>'; };
  var bowl = function (cx) { return '<path d="M' + (cx - 17) + ' 130Q' + cx + ' 98 ' + (cx + 17) + ' 130"/>' + '<path class="drip" d="M' + (cx - 6) + ' 134v6M' + (cx + 6) + ' 134v6"/>'; };

  var ART = {
    cups: [72, 120, 168].map(cup).join(''),
    wine: [88, 152].map(wine).join(''),
    plates: [63, 92, 121, 150, 179].map(plate).join(''),
    bowls: [90, 150].map(bowl).join(''),
    basket: '<path d="M84 108H156V144Q156 148 152 148H88Q84 148 84 144Z"/>'
      + '<path d="M108 108V148M132 108V148"/><path d="M100 108Q120 92 140 108"/>'
      + '<path d="M96 108V96M120 108V90M144 108V98"/>',
    cutlery: '<path d="M82 92q4 0 4 6V116q0 6 -4 6q-4 0 -4 -6V98q0 -6 4 -6"/>'
      + '<path d="M82 122L86 146H78Z"/><path class="dir" d="M77 86L82 81L87 86"/>'
      + '<ellipse cx="120" cy="99" rx="7" ry="10"/><path d="M120 109V146"/>'
      + '<path class="dir" d="M115 150L120 155L125 150"/>'
      + '<path d="M152 90V108M158 88V108M164 90V108M152 108H164"/><path d="M158 108V146"/>'
      + '<path class="dir" d="M153 150L158 155L163 150"/>',
    pot: '<g transform="rotate(-20 132 122)"><path d="M108 102V140Q108 146 114 146H150Q156 146 156 140V102"/>'
      + '<path d="M108 110H99M156 110H165"/></g><path class="drip" d="M150 150v6"/>'
  };

  var CATS = [
    { id: 'glas', label: 'GLAS', icon: ICON.glas, steps: [
      { rack: 'upper', title: 'Becher, Tassen & Gl\u00e4ser',
        text: 'Kopf\u00fcber an die Seiten des OBEREN Korbs. Kleine Teile auf oder unter die heruntergeklappten Tassenablagen.', art: ART.cups },
      { rack: 'upper', title: 'Stielgl\u00e4ser',
        text: 'In den OBEREN Korb \u2014 schonender. Tassenablage herunterklappen, Stiel in den Softgrip, leicht andr\u00fccken.', art: ART.wine }
    ] },
    { id: 'teller', label: 'TELLER & SCHALEN', icon: ICON.teller, steps: [
      { rack: 'lower', title: 'Teller',
        text: 'Zwischen die Zinken im UNTEREN Korb, Vertiefung zur Mitte. Nie mehrere Teller in dieselbe L\u00fccke \u2014 Untertassen nach oben.', art: ART.plates },
      { rack: 'lower', title: 'Schalen & Sch\u00fcsseln',
        text: 'Schr\u00e4g stellen, \u00d6ffnung nach unten \u2014 so fliesst das Wasser ab.', art: ART.bowls }
    ] },
    { id: 'besteck', label: 'BESTECK', icon: ICON.besteck, steps: [
      { rack: 'lower', title: 'Besteckkorb',
        text: 'In den UNTEREN Korb \u2014 ganz oder unterteilt. Zum Bef\u00fcllen herausnehmen und am Tisch beladen.', art: ART.basket },
      { rack: 'lower', title: 'Ausrichtung',
        text: 'Messer: Griff nach OBEN, Klinge nach unten. L\u00f6ffel & Gabeln: Griff nach unten. Bunt mischen, nichts verschachteln.', art: ART.cutlery }
    ] },
    { id: 'toepfe', label: 'T\u00d6PFE & PFANNEN', icon: ICON.toepfe, steps: [
      { rack: 'lower', title: 'T\u00f6pfe & Pfannen',
        text: 'Hinten in den UNTEREN Korb, Winkel nach unten \u2014 beste Reinigung und Wasserablauf. Zinken hinten herunterklappen f\u00fcr Halt.', art: ART.pot }
    ] }
  ];

  /* =======================================================================
     TEIL B  -  PROGRAMMASSISTENT
     ===================================================================== */
  var WICON = {
    mix: '<circle cx="17" cy="22" r="9"/><path d="M28 12V22M31 12V22M28 22V34"/>',
    fine: '<path d="M15 12Q15 20 22 21Q29 20 29 12Z"/><path d="M22 21V32"/><path d="M16 32H28"/>',
    pots: '<path d="M12 18H32V30Q32 34 28 34H16Q12 34 12 30Z"/><path d="M12 22H7M32 22H37"/>',
    energy: '<path d="M12 30C12 18 22 12 32 12C32 24 24 32 14 32Z"/><path d="M15 29Q22 24 27 18"/>',
    time: '<circle cx="22" cy="22" r="12"/><path d="M22 15V22L27 25"/>',
    hygiene: '<path d="M22 10L32 14V22C32 29 27 33 22 34C17 33 12 29 12 22V14Z"/><path d="M17 22L21 26L28 18"/>',
    quiet: '<path d="M29 25A9 9 0 1 1 19 12A7 7 0 0 0 29 25Z"/>',
    dry: '<circle cx="22" cy="22" r="6"/><path d="M22 8V12M22 32V36M8 22H12M32 22H36M13 13L15 15M31 31L29 29M31 13L29 15M13 31L15 29"/>',
    none: '<path d="M22 10L24 20L34 22L24 24L22 34L20 24L10 22L20 20Z"/>'
  };

  var WASH = [
    { id: 'mix', icon: WICON.mix, title: 'Geschirr', sub: 'Gemischte Beladung' },
    { id: 'fine', icon: WICON.fine, title: 'Feingeschirr', sub: 'Gl\u00e4ser & Empfindliches' },
    { id: 'pots', icon: WICON.pots, title: 'Kochgeschirr', sub: 'T\u00f6pfe & Pfannen' }
  ];
  var PRIO = [
    { id: 'energy', icon: WICON.energy, title: 'Energie sparen' },
    { id: 'time', icon: WICON.time, title: 'Schneller fertig' },
    { id: 'hygiene', icon: WICON.hygiene, title: 'Extra Hygiene' },
    { id: 'quiet', icon: WICON.quiet, title: 'Leiser' },
    { id: 'dry', icon: WICON.dry, title: 'Besser trocknen' },
    { id: 'none', icon: WICON.none, title: 'Keine Pr\u00e4ferenz' }
  ];

  /* Gueltige Optionen je Programm (Whitelist -> nie eine unmoegliche Kombi).
     Deckungsgleich mit PROG_OPTS der Karte (dort mit _option-Suffix). */
  var ALLOW = {
    ECO: ['extra_silent', 'xtra_dry'],
    AUTO: [],
    QUICK30: ['extra_power', 'glass_care', 'one_rack', 'sanitize', 'spray_zone', 'zone_clean'],
    QUICK60: ['extra_power', 'glass_care', 'one_rack', 'sanitize', 'spray_zone', 'zone_clean', 'xtra_dry'],
    NORMAL90: ['extra_power', 'extra_silent', 'glass_care', 'sanitize', 'spray_zone', 'xtra_dry', 'zone_clean'],
    '120_MIN': ['extra_power', 'extra_silent', 'glass_care', 'sanitize', 'spray_zone', 'xtra_dry', 'zone_clean']
  };
  var NAME = { ECO: 'Eco', AUTO: 'Auto', QUICK30: 'Quick 30', QUICK60: 'Quick 60', NORMAL90: 'Normal 90', '120_MIN': '120 Minuten' };
  var DUR = { ECO: 'ca. 3:50', AUTO: 'ca. 2:00', QUICK30: 'ca. 0:30', QUICK60: 'ca. 1:00', NORMAL90: 'ca. 1:30', '120_MIN': 'ca. 2:00' };
  var OPTNAME = { extra_silent: 'Leise', xtra_dry: 'Extra Trocknen', extra_power: 'Extra Power', glass_care: 'Glasschutz', one_rack: 'Ein Korb', sanitize: 'Hygiene-Sp\u00fclung', spray_zone: 'Spr\u00fchzone', zone_clean: 'Zonenreinigung' };

  function recommend(wash, prio) {
    var base = {
      mix: { prog: 'AUTO', opt: null, why: 'Auto erkennt die Beladung und dosiert selbst.' },
      fine: { prog: 'NORMAL90', opt: 'glass_care', why: 'Normal 90 mit Glasschutz sp\u00fclt Gl\u00e4ser schonend.' },
      pots: { prog: '120_MIN', opt: 'extra_power', why: '120 Minuten mit Extra Power l\u00f6st Eingebranntes.' }
    }[wash];
    var prog = base.prog, opt = base.opt, why = base.why, note = '';

    switch (prio) {
      case 'energy':
        prog = 'ECO'; opt = null; why = 'Eco braucht am wenigsten Strom und Wasser.';
        if (wash === 'fine') note = 'Glasschutz entf\u00e4llt \u2014 Eco l\u00e4uft ohnehin schonend.';
        if (wash === 'pots') note = 'Bei starkem Schmutz reinigt 120 Minuten gr\u00fcndlicher.';
        break;
      case 'time':
        prog = 'QUICK60';
        if (opt && ALLOW.QUICK60.indexOf(opt) < 0) opt = null;
        why = 'Quick 60 ist am schnellsten sauber fertig.';
        if (wash === 'pots') note = 'Stark Eingebranntes braucht eventuell l\u00e4nger.';
        break;
      case 'hygiene':
        prog = (wash === 'pots') ? '120_MIN' : 'NORMAL90'; opt = 'sanitize';
        why = 'Hygiene-Sp\u00fclung mit hoher Temperatur gegen Keime.';
        note = 'F\u00fcr Extra Hygiene empfehlen wir ' + NAME[prog] + '.';
        break;
      case 'quiet':
        prog = (wash === 'pots') ? '120_MIN' : 'NORMAL90'; opt = 'extra_silent';
        why = 'Leiser Betrieb \u2014 ideal f\u00fcr abends.';
        break;
      case 'dry':
        prog = (wash === 'pots') ? '120_MIN' : 'NORMAL90'; opt = 'xtra_dry';
        why = 'Extra Trocknen liefert trockenes Geschirr, auch Kunststoff.';
        break;
      default: break; /* Keine Praeferenz -> Basis behalten */
    }
    /* Sicherheitsnetz: niemals eine ungueltige Kombi ausliefern */
    if (opt && ALLOW[prog].indexOf(opt) < 0) opt = null;
    return { prog: prog, opt: opt, why: why, note: note };
  }

  /* =======================================================================
     STYLES  (modaler Overlay, kein Karten-Chrome)
     ===================================================================== */
  var CSS =
    ':host{all:initial;display:block;font-family:\'Segoe UI Variable\',\'Segoe UI\',system-ui,sans-serif;color:#f4f4f5;}'
    + '*{box-sizing:border-box;}'
    + 'button{font:inherit;}'
    /* Backdrop + zentrales Sheet */
    + '.ov{position:fixed;inset:0;z-index:2147483000;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;'
    + 'padding:16px;opacity:0;visibility:hidden;transition:opacity .18s ease,visibility .18s;}'
    + '.ov.open{opacity:1;visibility:visible;}'
    + '.sheet{position:relative;width:100%;max-width:420px;height:min(560px,86vh);background:#0a0a0b;'
    + 'border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:16px 18px 18px;display:flex;flex-direction:column;'
    + 'overflow:hidden;transform:translateY(8px);transition:transform .18s ease;}'
    + '.ov.open .sheet{transform:none;}'
    + '.ovtop{display:flex;align-items:center;justify-content:space-between;min-height:44px;gap:8px;flex:0 0 auto;}'
    + '.ib{width:44px;height:44px;flex:0 0 auto;display:flex;align-items:center;justify-content:center;'
    + 'background:none;border:none;color:#f4f4f5;font-size:20px;cursor:pointer;border-radius:10px;}'
    + '.ib:hover{background:rgba(255,255,255,.06);}.ib.hide{visibility:hidden;}'
    + '.rackpill{font-size:9.5px;letter-spacing:.16em;color:#4aa8ff;border:1px solid rgba(74,168,255,.35);border-radius:11px;padding:4px 10px;white-space:nowrap;}'
    + '.lead{font-size:23px;font-weight:250;line-height:1.16;letter-spacing:-.01em;margin:8px 2px 5px;}'
    + '.sub{font-size:12.5px;line-height:1.45;color:rgba(255,255,255,.5);margin:0 2px 16px;}'
    + '.kick{font-size:10px;letter-spacing:.18em;color:rgba(255,255,255,.4);margin:0 2px 11px;}'
    + '.mixhint{font-size:11.5px;line-height:1.5;color:rgba(255,255,255,.42);margin:14px 2px 0;}'
    + '.hidden{display:none!important;}'
    + '.body{flex:1;display:flex;flex-direction:column;min-height:0;overflow:auto;}'
    + 'button:focus-visible,.tile:focus-visible,.orow:focus-visible{outline:2px solid #4aa8ff;outline-offset:2px;}'
    /* Beladen: Kategorie-Raster */
    + '.grid{display:grid;grid-template-columns:1fr 1fr;gap:11px;}'
    + '.tile{display:flex;flex-direction:column;align-items:flex-start;gap:12px;padding:17px 15px;min-height:44px;'
    + 'background:rgba(255,255,255,.03);border:none;border-radius:13px;cursor:pointer;text-align:left;transition:background .15s ease;}'
    + '.tile:hover{background:rgba(255,255,255,.07);}'
    + '.mini{width:52px;height:44px;}'
    + '.mini *{fill:none;stroke:#4aa8ff;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;}'
    + '.tl{font-size:11px;letter-spacing:.13em;color:#f4f4f5;}'
    /* Beladen: sichtbare Schritt-Tabs (Metro) */
    + '.steptabs{display:flex;flex-wrap:wrap;gap:7px;margin:2px 0 8px;flex:0 0 auto;}'
    + '.stab{font-size:11px;letter-spacing:.02em;color:rgba(255,255,255,.6);background:rgba(255,255,255,.04);'
    + 'border:1px solid rgba(255,255,255,.1);border-radius:9px;min-height:40px;padding:8px 13px;cursor:pointer;}'
    + '.stab.on{color:#0a0a0b;background:#4aa8ff;border-color:#4aa8ff;font-weight:600;}'
    /* Beladen: Detail-Szene */
    + '.detail{flex:1;display:flex;flex-direction:column;min-height:0;}'
    + '.scene{flex:1;position:relative;display:flex;align-items:center;justify-content:center;min-height:150px;margin:2px 0;}'
    + '.scene-svg{width:100%;max-width:300px;height:auto;}'
    + '.scene-svg .tub{fill:none;stroke:rgba(255,255,255,.13);stroke-width:1.5;}'
    + '.scene-svg .rk path{fill:none;stroke:rgba(255,255,255,.30);stroke-width:1.6;stroke-linecap:round;}'
    + '.scene-svg .rk.dim{opacity:.22;}'
    + '.scene-svg .hi path,.scene-svg .hi ellipse{fill:none;stroke:#4aa8ff;stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round;}'
    + '.scene-svg .hi .drip{stroke:rgba(74,168,255,.5);stroke-width:1.6;}'
    + '.scene-svg .hi .dir{stroke:#ff1e6f;stroke-width:2;}'
    /* Nav-Pfeile: hoher Kontrast, 44px Hit-Area */
    + '.nav{position:absolute;top:50%;transform:translateY(-50%);width:44px;height:44px;border:none;'
    + 'background:rgba(255,255,255,.1);color:#f4f4f5;border-radius:50%;font-size:23px;line-height:1;cursor:pointer;'
    + 'display:flex;align-items:center;justify-content:center;}'
    + '.nav::before{content:"";position:absolute;inset:-2px;border-radius:50%;}'
    + '.nav:hover{background:rgba(255,255,255,.2);}.nav-l{left:-4px;}.nav-r{right:-4px;}.nav.off{display:none;}'
    + '.dtitle-row{display:flex;align-items:baseline;gap:10px;margin:6px 2px 4px;flex:0 0 auto;}'
    + '.dcount{font-size:12px;letter-spacing:.06em;color:#4aa8ff;font-variant-numeric:tabular-nums;font-weight:700;flex:none;}'
    + '.dtitle{font-size:19px;font-weight:300;}'
    + '.dtext{font-size:13px;line-height:1.5;color:rgba(255,255,255,.62);margin:0 2px;min-height:58px;flex:0 0 auto;}'
    /* Beladen: beschriftete Weiter/Zurueck-Buttons */
    + '.stepnav{display:flex;gap:9px;margin-top:12px;flex:0 0 auto;}'
    + '.snav{flex:1;min-height:48px;font-size:13px;color:#f4f4f5;background:rgba(255,255,255,.05);'
    + 'border:1px solid rgba(255,255,255,.12);border-radius:12px;padding:12px 14px;cursor:pointer;'
    + 'display:inline-flex;align-items:center;justify-content:center;gap:8px;text-align:center;}'
    + '.snav.fwd{background:rgba(74,168,255,.16);border-color:rgba(74,168,255,.42);color:#dbeeff;font-weight:600;}'
    + '.snav .sar{font-size:19px;line-height:1;color:#4aa8ff;flex:none;}'
    + '.snav:hover{filter:brightness(1.1);}'
    /* Wizard: Optionszeilen */
    + '.orow{display:flex;align-items:center;gap:14px;padding:14px 15px;min-height:44px;background:rgba(255,255,255,.03);'
    + 'border:none;border-radius:12px;cursor:pointer;text-align:left;width:100%;transition:background .15s ease;}'
    + '.orow+.orow{margin-top:9px;}.orow:hover{background:rgba(255,255,255,.07);}'
    + '.orow .mini{width:30px;height:30px;flex:0 0 auto;}'
    + '.ol{display:flex;flex-direction:column;gap:2px;}'
    + '.ol b{font-size:14px;font-weight:400;}'
    + '.ol i{font-size:11px;font-style:normal;color:rgba(255,255,255,.42);letter-spacing:.02em;}'
    /* Wizard: Stepper */
    + '.steps{display:flex;gap:6px;align-items:center;}'
    + '.seg{width:22px;height:3px;border-radius:2px;background:rgba(255,255,255,.18);}'
    + '.seg.on{background:#ff1e6f;}'
    /* Wizard: Empfehlung */
    + '.rec{flex:1;display:flex;flex-direction:column;min-height:0;}'
    + '.rkick{font-size:11px;letter-spacing:.14em;color:#4aa8ff;margin:6px 2px 6px;text-transform:uppercase;font-weight:600;}'
    + '.recprog{font-size:44px;font-weight:200;letter-spacing:-.02em;font-variant-numeric:tabular-nums;margin:0 2px;line-height:1.05;}'
    + '.recmeta{display:flex;align-items:center;gap:10px;margin:12px 2px 0;flex-wrap:wrap;}'
    + '.optpill{font-size:13px;letter-spacing:.02em;color:#dbeeff;background:rgba(74,168,255,.16);'
    + 'border:1px solid rgba(74,168,255,.45);border-radius:12px;padding:7px 13px;font-weight:600;}'
    + '.dur{font-size:13px;color:rgba(255,255,255,.55);font-variant-numeric:tabular-nums;}'
    + '.recwhy{font-size:13px;line-height:1.5;color:rgba(255,255,255,.62);margin:14px 2px 0;}'
    + '.recnote{font-size:12px;line-height:1.45;color:#ffb3cd;margin:10px 2px 0;}'
    + '.recprev{font-size:12.5px;line-height:1.5;color:rgba(255,255,255,.72);background:rgba(255,255,255,.03);'
    + 'border-left:2px solid #4aa8ff;padding:9px 12px;border-radius:0 8px 8px 0;margin:14px 2px 0;}'
    + '.recact{margin-top:auto;display:flex;flex-direction:column;gap:9px;padding-top:16px;}'
    + '.apply{min-height:48px;border:none;border-radius:12px;background:#ff1e6f;color:#fff;font-size:14px;'
    + 'letter-spacing:.02em;cursor:pointer;transition:filter .15s ease;padding:12px;}'
    + '.apply:hover{filter:brightness(1.08);}'
    + '.redo{min-height:44px;border:1px solid rgba(255,255,255,.14);border-radius:12px;background:none;color:rgba(255,255,255,.7);font-size:13px;cursor:pointer;padding:11px;}'
    + '.redo:hover{background:rgba(255,255,255,.05);}'
    /* Wizard: persistente Erfolgs-Bestaetigung */
    + '.okwrap{margin-top:auto;padding-top:16px;display:flex;flex-direction:column;gap:11px;}'
    + '.okline{font-size:13.5px;line-height:1.5;color:#f4f4f5;background:rgba(74,168,255,.12);'
    + 'border:1px solid rgba(74,168,255,.35);border-radius:12px;padding:14px 15px;}'
    + '.okline b{font-weight:600;}'
    + '.okbtn{min-height:48px;border:none;border-radius:12px;background:#ff1e6f;color:#fff;font-size:14px;cursor:pointer;padding:12px;}'
    + '.okbtn:hover{filter:brightness(1.08);}'
    /* Toast */
    + '.toast{position:absolute;left:18px;right:18px;bottom:18px;padding:13px 15px;border-radius:12px;'
    + 'background:rgba(255,30,111,.14);border:1px solid rgba(255,30,111,.4);color:#fff;font-size:13px;'
    + 'opacity:0;transform:translateY(8px);transition:opacity .18s ease,transform .18s ease;pointer-events:none;}'
    + '.toast.show{opacity:1;transform:none;}'
    + '@media (prefers-reduced-motion:reduce){.ov,.sheet,.tile,.orow,.nav,.toast,.apply{transition:none!important;}}';

  /* =======================================================================
     ELEMENT
     ===================================================================== */
  class Guides extends HTMLElement {
    connectedCallback() { this._ensure(); }

    _ensure() {
      if (this._b) return; this._b = true;
      this.cur = null; this.step = 0; this.wash = null; this.prio = null; this.wstep = 0; this._applied = false;
      var r = this.attachShadow({ mode: 'open' });

      var grid = ''; for (var i = 0; i < CATS.length; i++) {
        grid += '<button class="tile" data-i="' + i + '" aria-label="' + esc(CATS[i].label) + '">'
          + '<svg class="mini" viewBox="0 0 44 44">' + CATS[i].icon + '</svg>'
          + '<span class="tl">' + esc(CATS[i].label) + '</span></button>';
      }
      var washRows = ''; for (var w = 0; w < WASH.length; w++) {
        washRows += '<button class="orow" data-wash="' + WASH[w].id + '"><svg class="mini" viewBox="0 0 44 44">' + WASH[w].icon + '</svg>'
          + '<span class="ol"><b>' + esc(WASH[w].title) + '</b><i>' + esc(WASH[w].sub) + '</i></span></button>';
      }
      var prioRows = ''; for (var p = 0; p < PRIO.length; p++) {
        prioRows += '<button class="orow" data-prio="' + PRIO[p].id + '"><svg class="mini" viewBox="0 0 44 44">' + PRIO[p].icon + '</svg>'
          + '<span class="ol"><b>' + esc(PRIO[p].title) + '</b></span></button>';
      }

      r.innerHTML =
        '<style>' + CSS + '</style>'
        /* ---- Overlay Beladen-Hilfe ---- */
        + '<div class="ov" data-el="ovLoad" role="dialog" aria-label="Beladen - so geht es" aria-modal="true">'
        + '<div class="sheet">'
        + '<div class="ovtop">'
        + '<button class="ib" data-a="lback" aria-label="Zur\u00fcck">\u2039</button>'
        + '<span class="rackpill" data-el="pill"></span>'
        + '<button class="ib" data-a="lclose" aria-label="Schliessen">\u2715</button>'
        + '</div>'
        + '<div class="body">'
        + '<div class="cats" data-el="cats">'
        + '<div class="lead">Wie du deinen Geschirrsp\u00fcler bel\u00e4dst</div>'
        + '<div class="sub">Maximiere die Reinigung. Vorher pr\u00fcfen: ist das Geschirr sp\u00fclmaschinenfest?</div>'
        + '<div class="kick">KATEGORIE W\u00c4HLEN</div>'
        + '<div class="grid">' + grid + '</div>'
        + '<div class="mixhint">Gemischte Beladung? Grobe Reihenfolge: Teller &amp; T\u00f6pfe unten, Gl\u00e4ser &amp; Tassen oben, Besteck sortiert in den Korb.</div>'
        + '</div>'
        + '<div class="detail hidden" data-el="detail">'
        + '<div class="steptabs" data-el="steptabs"></div>'
        + '<div class="scene">'
        + '<button class="nav nav-l" data-a="prev" aria-label="Vorheriger Schritt">\u2039</button>'
        + '<div data-el="art"></div>'
        + '<button class="nav nav-r" data-a="next" aria-label="N\u00e4chster Schritt">\u203a</button>'
        + '</div>'
        + '<div class="dtitle-row"><span class="dcount" data-el="dcount"></span><span class="dtitle" data-el="dtitle"></span></div>'
        + '<div class="dtext" data-el="dtext"></div>'
        + '<div class="stepnav" data-el="stepnav"></div>'
        + '</div>'
        + '</div>'
        + '</div>'
        + '</div>'
        /* ---- Overlay Programmassistent ---- */
        + '<div class="ov" data-el="ovWiz" role="dialog" aria-label="Programmassistent" aria-modal="true">'
        + '<div class="sheet">'
        + '<div class="ovtop">'
        + '<button class="ib" data-a="wback" aria-label="Zur\u00fcck">\u2039</button>'
        + '<span class="steps"><span class="seg" data-seg="0"></span><span class="seg" data-seg="1"></span><span class="seg" data-seg="2"></span></span>'
        + '<button class="ib" data-a="wclose" aria-label="Abbrechen">\u2715</button>'
        + '</div>'
        + '<div class="body">'
        + '<div data-el="w0">'
        + '<div class="lead">Was w\u00e4schst Du?</div>'
        + '<div class="sub">Damit w\u00e4hlen wir das passende Grundprogramm.</div>' + washRows
        + '</div>'
        + '<div class="hidden" data-el="w1">'
        + '<div class="lead">Was ist Dir am wichtigsten?</div>'
        + '<div class="sub">Ein Kriterium gen\u00fcgt \u2014 wir stimmen das Programm darauf ab.</div>' + prioRows
        + '</div>'
        + '<div class="rec hidden" data-el="w2">'
        + '<div class="rkick" data-el="rkick"></div>'
        + '<div class="recprog" data-el="rprog"></div>'
        + '<div class="recmeta"><span class="optpill hidden" data-el="ropt"></span><span class="dur" data-el="rdur"></span></div>'
        + '<div class="recwhy" data-el="rwhy"></div>'
        + '<div class="recnote hidden" data-el="rnote"></div>'
        + '<div class="recprev" data-el="rprev"></div>'
        + '<div data-el="recfoot"></div>'
        + '</div>'
        + '</div>'
        + '<div class="toast" data-el="toast"></div>'
        + '</div>'
        + '</div>';

      this.$ = function (s) { return r.querySelector(s); };
      r.addEventListener('click', this._click.bind(this));
      r.addEventListener('keydown', function (e) { if (e.key === 'Escape') { this._closeAll(); } }.bind(this));

      // Wischen fuer Beladen-Detail
      var sc = this.$('.scene'), self = this, x0 = null;
      sc.addEventListener('pointerdown', function (e) { x0 = e.clientX; });
      sc.addEventListener('pointerup', function (e) {
        if (x0 === null) return; var dx = e.clientX - x0; x0 = null;
        if (Math.abs(dx) > 40) self._setStep(self.step + (dx < 0 ? 1 : -1));
      });
    }

    /* ---- oeffentliche API: von der Karte aufgerufen ---- */
    openLoad() { this._ensure(); this._openOv('ovLoad'); this._showCats(); }
    openWiz() { this._ensure(); this._restartWiz(); this._openOv('ovWiz'); this._renderWiz(); }

    _click(e) {
      // Klick auf den Backdrop (nicht das Sheet) schliesst den Flow.
      if (e.target.classList && e.target.classList.contains('ov')) { this._close(e.target.getAttribute('data-el')); return; }
      var t = e.target.closest('[data-a],[data-i],[data-wash],[data-prio],[data-k],[data-seg]'); if (!t) return;
      if (t.dataset.i !== undefined) { this._openCat(+t.dataset.i); return; }
      if (t.dataset.k !== undefined) { this._setStep(+t.dataset.k); return; }
      if (t.dataset.wash !== undefined) { this.wash = t.dataset.wash; this.wstep = 1; this._renderWiz(); return; }
      if (t.dataset.prio !== undefined) { this.prio = t.dataset.prio; this.wstep = 2; this._renderWiz(); return; }
      switch (t.dataset.a) {
        case 'lclose': this._close('ovLoad'); break;
        case 'lback': this.cur === null ? this._close('ovLoad') : this._showCats(); break;
        case 'prev': this._setStep(this.step - 1); break;
        case 'next': this._setStep(this.step + 1); break;
        case 'wclose': this._close('ovWiz'); break;
        case 'wback': this.wstep === 0 ? this._close('ovWiz') : (this.wstep--, this._renderWiz()); break;
        case 'wrestart': this._restartWiz(); this._renderWiz(); break;
        case 'apply': this._apply(); break;
      }
    }

    /* ---- gemeinsam ---- */
    _openOv(name) { this._closeAll(); this.$('[data-el="' + name + '"]').classList.add('open'); }
    _close(name) { if (!name) return; this.$('[data-el="' + name + '"]').classList.remove('open'); if (name === 'ovLoad') this.cur = null; }
    _closeAll() { this._close('ovLoad'); this._close('ovWiz'); }

    /* ---- Beladen-Hilfe ---- */
    _showCats() {
      this.cur = null;
      this.$('[data-el="cats"]').classList.remove('hidden');
      this.$('[data-el="detail"]').classList.add('hidden');
      this.$('[data-a="lback"]').classList.add('hide');
      this.$('[data-el="pill"]').textContent = '';
    }
    _openCat(i) {
      this.cur = i; this.step = 0;
      this.$('[data-el="cats"]').classList.add('hidden');
      this.$('[data-el="detail"]').classList.remove('hidden');
      this.$('[data-a="lback"]').classList.remove('hide');
      this._renderDetail();
    }
    _setStep(s) {
      if (this.cur === null) return; var n = CATS[this.cur].steps.length;
      if (s < 0 || s >= n) return; this.step = s; this._renderDetail();
    }
    _renderDetail() {
      var cat = CATS[this.cur], st = cat.steps[this.step], n = cat.steps.length;
      this.$('[data-el="pill"]').textContent = st.rack === 'upper' ? 'OBERER KORB' : 'UNTERER KORB';
      this.$('[data-el="art"]').innerHTML = scene(st.rack, st.art);
      this.$('[data-el="dcount"]').textContent = n > 1 ? (this.step + 1) + ' / ' + n : '';
      this.$('[data-el="dtitle"]').textContent = st.title;
      this.$('[data-el="dtext"]').textContent = st.text;
      // Sichtbare Schritt-Tabs (Metro) nur bei Mehrschritt-Kategorien.
      var tabs = '';
      if (n > 1) {
        for (var k = 0; k < n; k++) {
          tabs += '<button class="stab' + (k === this.step ? ' on' : '') + '" data-k="' + k + '" type="button" aria-pressed="' + (k === this.step) + '">' + esc(cat.steps[k].title) + '</button>';
        }
      }
      this.$('[data-el="steptabs"]').innerHTML = tabs;
      // Beschriftete Weiter/Zurueck-Buttons statt blasser Dots.
      var snav = '';
      if (n > 1) {
        if (this.step > 0) {
          snav += '<button class="snav back" data-a="prev" type="button"><span class="sar">\u2039</span> ' + esc(cat.steps[this.step - 1].title) + '</button>';
        }
        if (this.step < n - 1) {
          snav += '<button class="snav fwd" data-a="next" type="button">Weiter: ' + esc(cat.steps[this.step + 1].title) + ' <span class="sar">\u203a</span></button>';
        }
      }
      this.$('[data-el="stepnav"]').innerHTML = snav;
      this.$('.nav-l').classList.toggle('off', n < 2 || this.step === 0);
      this.$('.nav-r').classList.toggle('off', n < 2 || this.step === n - 1);
    }

    /* ---- Programmassistent ---- */
    _restartWiz() { this.wash = null; this.prio = null; this.wstep = 0; this._applied = false; }
    _renderWiz() {
      var s = this.wstep;
      this.$('[data-el="w0"]').classList.toggle('hidden', s !== 0);
      this.$('[data-el="w1"]').classList.toggle('hidden', s !== 1);
      this.$('[data-el="w2"]').classList.toggle('hidden', s !== 2);
      for (var i = 0; i < 3; i++) { this.$('[data-seg="' + i + '"]').classList.toggle('on', i <= s); }
      if (s === 2) this._renderRec();
    }
    _renderRec() {
      var rec = recommend(this.wash, this.prio);
      this._rec = rec;
      var prio = null; for (var i = 0; i < PRIO.length; i++) { if (PRIO[i].id === this.prio) { prio = PRIO[i]; break; } }
      // Gewaehltes Kriterium sichtbar zurueckspiegeln.
      this.$('[data-el="rkick"]').textContent = prio ? ('DEIN WUNSCH: ' + prio.title.toUpperCase()) : 'EMPFEHLUNG';
      this.$('[data-el="rprog"]').textContent = NAME[rec.prog];
      this.$('[data-el="rdur"]').textContent = DUR[rec.prog];
      var opt = this.$('[data-el="ropt"]');
      if (rec.opt) { opt.textContent = '+ ' + OPTNAME[rec.opt]; opt.classList.remove('hidden'); }
      else { opt.classList.add('hidden'); }
      this.$('[data-el="rwhy"]').textContent = rec.why;
      var note = this.$('[data-el="rnote"]');
      if (rec.note) { note.textContent = rec.note; note.classList.remove('hidden'); }
      else { note.classList.add('hidden'); }
      // Vorschau-/Wirkungszeile: eindeutig einstellen, nicht starten.
      this.$('[data-el="rprev"]').textContent = 'Stellt an der Maschine ein: ' + NAME[rec.prog]
        + (rec.opt ? (' + ' + OPTNAME[rec.opt]) : '') + ' \u2014 Du startest den Zyklus dann am Ger\u00e4t.';
      // Fuss: Aktion ODER persistente Erfolgs-Bestaetigung.
      var foot = this.$('[data-el="recfoot"]');
      if (this._applied) {
        foot.innerHTML = '<div class="okwrap"><div class="okline"><b>Eingestellt an der Maschine:</b> '
          + esc(NAME[rec.prog]) + (rec.opt ? (' + ' + esc(OPTNAME[rec.opt])) : '')
          + '. Den Zyklus startest Du am Ger\u00e4t.</div>'
          + '<button class="okbtn" data-a="wclose" type="button">Schliessen</button>'
          + '<button class="redo" data-a="wrestart" type="button">Neu w\u00e4hlen</button></div>';
      } else {
        foot.innerHTML = '<div class="recact"><button class="apply" data-a="apply" type="button">Programm einstellen</button>'
          + '<button class="redo" data-a="wrestart" type="button">Neu w\u00e4hlen</button></div>';
      }
    }
    _apply() {
      var rec = this._rec; if (!rec) return;
      // INTEGRATIONS-HOOK: die Karte hoert 'program-apply' und ruft die realen HA-Services.
      this.dispatchEvent(new CustomEvent('program-apply', { bubbles: true, composed: true, detail: rec }));
      // Persistente Bestaetigung: Overlay bleibt offen, bis der Nutzer schliesst.
      this._applied = true;
      this._renderRec();
      this._toast('Eingestellt: ' + NAME[rec.prog] + (rec.opt ? (' + ' + OPTNAME[rec.opt]) : ''));
    }
    _toast(msg) {
      var t = this.$('[data-el="toast"]'); t.textContent = msg; t.classList.add('show');
      clearTimeout(this._tt); var self = this;
      this._tt = setTimeout(function () { t.classList.remove('show'); }, 3200);
    }
  }

  if (typeof module !== 'undefined' && module.exports) {
    // Test-Hook (nur in node; im Browser ist module undefined). Erlaubt der
    // Matrix-Validierung den Zugriff auf recommend/ALLOW aus der echten Datei.
    module.exports = { recommend: recommend, ALLOW: ALLOW, NAME: NAME, OPTNAME: OPTNAME, WASH: WASH, PRIO: PRIO };
  }
  customElements.define('electrolux-guides', Guides);
})();
