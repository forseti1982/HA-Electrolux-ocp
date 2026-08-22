---
name: ocp-card
description: An den mitgelieferten Lovelace-Karten arbeiten — electrolux-ocp-card (Geschirrspüler), electrolux-guides (Beladen-Hilfe/Programmassistent), coffee-machine-card. Nutze dies bei allem, was Frontend, Karte, Lovelace, Custom-Element, Kartentext, Animation oder Kartenregistrierung betrifft.
---

# Arbeiten an den Karten

Dateien: `custom_components/electrolux_ocp/frontend/`. Registrierung:
`frontend.py`. Hintergrund und Konventionen im Detail:
`.claude/brain/40-frontend-karten.md`.

## Zuerst: der ASCII-Vertrag

**Der Quelltext ist reines ASCII — auch die Kommentare.** Zwei erlaubte Wege für
Umlaute:

| Weg | Wo | Beispiel |
|---|---|---|
| `\uXXXX` | Guides, Kaffee-Karte, teils Hauptkarte | `'Läuft'` |
| `@NNN;` + `D()` | Hauptkarte | `D('GESCHIRRSP@220;LER')` |

**`D()` nur über statische Template-Teile, NIE über dynamische Sensor-Strings.**
Dynamische Werte laufen durch `esc()`. Das ist eine Sicherheitsgrenze: `D()`
schreibt roh ins Markup, `esc()` maskiert. Wer einen Sensorwert durch `D()`
schickt, öffnet eine Injection.

Nach **jeder** Änderung prüfen:
```bash
bash .claude/pruefen.sh
```

> Nicht mit `LC_ALL=C grep '[^\x00-\x7F]'` prüfen: **ohne `-P`** interpretiert
> grep die Escapes nicht und meldet dann jede Zeile als Treffer. Das Skript
> nutzt deshalb Python (`str.isascii()`).

## Zweitens: `CARD_VERSION` anheben

`const.py` → `CARD_VERSION` ist das Cache-Busting **aller drei** Dateien
(`?v=…`). Wer eine Karte ändert und die Version stehen lässt, liefert
Browsern die alte Datei aus — die Änderung wirkt scheinbar nicht.

## Konventionen

- **Null externe Ressourcen.** Kein CDN, keine Web-Fonts, keine Remote-Bilder.
- **Shadow-DOM**, „Metrology"-Design, alles inline.
- **Texte im `T`-Objekt am Dateikopf** ändern, nicht verstreut im Markup.
  Du-Ansprache, kein Denglisch.
- **Alle Config-Felder optional**, Demo-Fallback ohne `entities`.
- **Karten-Picker**: `window.customCards.push({type, name, description})` und
  `static getStubConfig()`.
- **Guard gegen Doppel-Definition**: `if (customElements.get('…')) return;`
- **Riskante Aktionen fragen zurück** (`qStart`, `qStop`, `qOff`). Ein laufendes
  Programm wird nie ohne Bestätigung abgebrochen.

## Eine vierte Karte mitliefern

1. Datei nach `frontend/` legen.
2. In `const.py`: `<X>_FILENAME` und `<X>_URL_PATH` (Muster:
   `/electrolux_ocp/<datei>.js`).
3. In `frontend.py` innerhalb `async_register_card` denselben Block wie für die
   Kaffee-Karte ergänzen: Existenz im Executor prüfen
   (`hass.async_add_executor_job(path.is_file)` — nie blockierend im Event-Loop),
   `async_register_static_paths`, `add_extra_js_url` mit `?v={CARD_VERSION}`.
   Fehlt die Datei: `WARNING` und weiterlaufen (rollback-sicher).
4. Reihenfolge beachten: Abhängigkeiten (wie `electrolux-guides`) werden **vor**
   der Karte registriert, die sie nutzt.

## Kopplung an die Entitäten

Die Karte referenziert Entitäten über die YAML-Konfiguration, nicht über feste
IDs — die exakten Suffixe hängen an offenen `# VERIFY`-Punkten. Programm-Pills
kommen aus `attributes.options` des Select-Entities; der `_HIDDEN`-Filter aus
`select.py` wirkt deshalb direkt in die Karte hinein. Das Guides-Modul feuert
`program-apply {prog, opt}`, die Karte setzt es um.

## Prüfen

Es gibt keinen JS-Build und keine JS-Tests. Was geht:

```bash
bash .claude/pruefen.sh                        # ASCII-Vertrag + CARD_VERSION
for f in custom_components/electrolux_ocp/frontend/*.js; do node --check "$f"; done   # falls node da ist
grep -n "customElements.define" custom_components/electrolux_ocp/frontend/*.js
```

Danach am echten HA: Browser hart neu laden (Strg/Cmd+Shift+R).
