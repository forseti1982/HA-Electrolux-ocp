# Brain / Frontend: die drei mitgelieferten Karten

Alle drei liegen unter `custom_components/electrolux_ocp/frontend/` und werden
von `frontend.py` registriert. Kein HACS-Karten-Install, keine manuelle
Lovelace-Ressource.

| Datei | Custom-Element | Rolle |
|---|---|---|
| `electrolux-ocp-card.js` | `electrolux-ocp-card` | Geschirrspüler: plastische Live-Grafik + volle Bedien-Oberfläche |
| `electrolux-ocp-guides.js` | `electrolux-guides` | Beladen-Hilfe + Programmassistent, modaler Overlay |
| `coffee-machine-card.js` | `coffee-machine-card` | Home-Connect-Kaffeevollautomat (fremde Entitäten) |

## Der ASCII-Vertrag

**Der Quelltext der Karten ist reines ASCII.** Kein einziges Nicht-ASCII-Zeichen
— auch nicht in Kommentaren. Zwei erlaubte Wege, Umlaute in die Anzeige zu
bekommen:

1. `\uXXXX`-Escapes (Guides, Kaffee-Karte, teils Hauptkarte).
2. `@NNN;` + die Hilfsfunktion `D()` (Hauptkarte):
   `D('GESCHIRRSP@220;LER')`.

**`D()` ausschließlich über statische Template-Teile, NIE über dynamische
Sensor-Strings** — dynamische Werte laufen durch `esc()` (HTML-Escaping). Diese
Trennung ist eine Sicherheitsgrenze, keine Stilfrage.

Prüfung vor jedem Commit:

```bash
bash .claude/pruefen.sh
```

> **Nicht** mit `LC_ALL=C grep -n '[^\x00-\x7F]'` prüfen: ohne `-P` interpretiert
> grep die Escapes nicht und meldet jede Zeile als Treffer — der Test sieht dann
> aus, als sei alles kaputt. Das Prüfskript nutzt `str.isascii()`.

## Weitere Konventionen

- **Null externe Ressourcen.** Keine CDN-Skripte, keine Web-Fonts, keine
  Remote-Bilder. Alles inline.
- **Shadow-DOM**, eigenes Styling („Metrology"-Design).
- **Config-getrieben mit Demo-Fallback**: ohne `entities` zeigt die Karte eine
  Demo-Ansicht. Alle Felder optional — nur Vorhandenes wird angezeigt.
- **Karten-Picker**: jede Karte meldet sich über `window.customCards` an und
  liefert `static getStubConfig()`, damit sie im visuellen Picker erscheint.
- **Guard gegen Doppel-Definition**: `if (customElements.get('…')) return;`
- **Rückfragen bei riskanten Aktionen** (`qStart`, `qStop`, `qOff`) — ein
  laufendes Programm wird nie ohne Bestätigung abgebrochen.
- **Texte in Du-Ansprache**, kein Denglisch. Die Textbausteine stehen gebündelt
  im Objekt `T` am Dateikopf — dort ändern, nicht verstreut im Markup.

## Cache-Busting

`CARD_VERSION` in `const.py` hängt als `?v=…` an **allen drei**
`add_extra_js_url`-Aufrufen. **Wer eine Karte ändert, hebt `CARD_VERSION` an** —
sonst liefert der Browser die alte Datei aus und die Änderung wirkt nicht.

> Bekannte Unstimmigkeit: `CARD_VERSION` steht auf `0.2.5`, während die
> Integration bei 0.2.6 liegt. Siehe `.claude/brain/90-offene-fragen.md`.

## Reihenfolge der Registrierung

Guides → Kaffee-Karte → Hauptkarte. Bewusst deterministisch, damit
`<electrolux-guides>` definiert ist, bevor die Karte lädt (Custom Elements
upgraden zwar auch nachträglich). Fehlt eine Datei, wird sie mit `WARNING`
übersprungen und der Rest läuft weiter — rollback-sicher.

## Kopplung Karte ↔ Entitäten

Die Karte referenziert Entitäten über die YAML-Konfiguration (`entities:`), nicht
über feste IDs. Programm-Pills kommen aus `attributes.options` des
Select-Entities — deshalb wirkt der `_HIDDEN`-Filter aus `select.py` direkt in
die Karte hinein. Das Guides-Modul feuert `program-apply {prog, opt}`; die Karte
setzt das um.
