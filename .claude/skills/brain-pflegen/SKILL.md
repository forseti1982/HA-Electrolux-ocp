---
name: brain-pflegen
description: Das Projekt-Brain unter .claude/brain aktuell halten — Entscheidungen protokollieren, gesichertes Geräte-Wissen eintragen, offene Fragen pflegen. Nutze dies, wenn eine bindende Entscheidung gefallen ist, ein VERIFY-Punkt geschlossen wurde, oder wenn jemand sagt "merk dir das" / "ins Brain".
---

# Das Brain pflegen

Das Brain (`.claude/brain/`) ist das Langzeitgedächtnis. Es beantwortet, was
weder Code noch README hergeben: **warum** etwas so ist, was schon einmal
schiefging, und was bewusst offen blieb.

## Was hineingehört — und was nicht

| Gehört ins Brain | Gehört **nicht** ins Brain |
|---|---|
| Warum eine Schwelle 3 und nicht 1 ist | Was eine Funktion tut (das steht im Docstring) |
| Ein Fehler, der Nutzer:innen getroffen hat, und die Gegenmaßnahme | Erledigte Kleinigkeiten ohne Nachwirkung |
| Am Gerät belegte Enums und Property-Keys | Vermutungen ohne Beleg (die bleiben `# VERIFY`) |
| Bewusst in Kauf genommene Nachteile | Beschreibung der Ordnerstruktur (steht in `CLAUDE.md`) |
| Bekannte Unstimmigkeiten mit konkretem nächsten Schritt | Ideen ohne Bezug zu diesem Projekt |

Faustregel: **Wenn jemand in sechs Monaten die Zeile ändern will und sich fragt
„warum steht das so da?" — dann ins Brain.**

## Wohin genau

| Anlass | Datei |
|---|---|
| Bindende Entscheidung | `30-entscheidungen.md` (**oben** anfügen) |
| Am Gerät belegtes Wissen | `20-geraete-wissen.md` (von „offen" nach „gesichert") |
| Neue API-Erkenntnis | `10-api-ocp.md` |
| Struktur geändert | `00-architektur.md` |
| Karten-Konvention | `40-frontend-karten.md` |
| Offener Punkt / Unstimmigkeit | `90-offene-fragen.md` |

## Format für `30-entscheidungen.md`

```markdown
## JJJJ-MM-TT — Kurzer, konkreter Titel (vX.Y.Z)

**Problem.** Was war kaputt oder unbefriedigend — aus Sicht der Nutzer:innen,
nicht aus Sicht des Codes.

**Entscheidung.** Was jetzt gilt, mit den konkreten Werten/Namen.

**Begründung.** Warum diese und nicht die naheliegende Alternative.

**Folgen.** Was das kostet, was bewusst in Kauf genommen wurde.
```

Deutsch, Du-Ansprache, konkrete Konstantennamen und Zahlen. Kein Marketing.
Neue Einträge kommen **oben** — die Datei liest sich von jung nach alt.

## Wenn `00` oder `10` wächst

`00-architektur.md` und `10-api-ocp.md` werden über `CLAUDE.md` bei **jeder**
Sitzung mitgeladen. Sie sind Kontext-Budget. Halte sie dicht: was nur gelegentlich
gebraucht wird, wandert in eine der bei Bedarf gelesenen Dateien und wird von dort
verlinkt. Die restlichen Brain-Dateien dürfen ausführlich sein.

## Aufräumen

- `90-offene-fragen.md`: Erledigtes nach „Geschlossen" **mit Datum** — nicht
  löschen. Warum ein Punkt vom Tisch ist, ist oft wertvoller als der Punkt.
- Widerspricht eine Brain-Aussage dem Code, gewinnt der Code — und die Zeile
  wird sofort korrigiert. Ein falsches Gedächtnis ist schlimmer als keines.
- Prüfe beim Anfassen einer Brain-Datei kurz, ob die zitierten Konstanten noch
  so heißen und dieselben Werte tragen.

## Gegenprobe

```bash
bash .claude/pruefen.sh
grep -rn "VERIFY" custom_components/electrolux_ocp/*.py | wc -l   # Stand gegen 20-geraete-wissen.md halten
grep -n "DEFAULT_SCAN_INTERVAL\|IDLE_SCAN_INTERVAL\|COMMAND_BOOST_SECONDS\|CARD_VERSION" \
     custom_components/electrolux_ocp/const.py
grep -n "_AUTH_FAILURES_BEFORE_REAUTH\|_FORBIDDEN_FAILURES_BEFORE_REAUTH" \
     custom_components/electrolux_ocp/coordinator.py
```

Weichen die Werte von dem ab, was im Brain steht: Brain korrigieren.
