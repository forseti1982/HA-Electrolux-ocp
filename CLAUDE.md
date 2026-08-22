# Zentrale — Electrolux OCP für Home Assistant

Dies ist die **Kommandozentrale** dieses Projekts: ein Ort, an dem Gedächtnis
(Brain), Skills, Agents und Arbeitsabläufe zusammenlaufen. Wer hier arbeitet —
Mensch oder Claude — liest zuerst diese Datei.

## Was das Projekt ist

Eine Home-Assistant-Custom-Integration (`custom_components/electrolux_ocp`),
die Electrolux-/AEG-Geräte über die **offizielle OCP Developer-API**
(developer.electrolux.one) anbindet. Kein Reverse-Engineering, keine
App-Zugangsdaten — nur API Key + Access Token + Refresh Token, die jede:r
Nutzer:in selbst erzeugt. Fokus: Geschirrspüler. Aufbau: generisch, Entitäten
entstehen **dynamisch** aus den gemeldeten Geräte-Properties.

Auslieferung über HACS. Zusätzlich liegen drei Lovelace-Custom-Elements bei,
die die Integration beim Setup selbst registriert (installieren = Daten +
Grafik).

## Das Brain

Langzeitgedächtnis dieses Projekts. Zwei Dateien sind so tragend, dass sie
immer mitgeladen werden:

@.claude/brain/00-architektur.md
@.claude/brain/10-api-ocp.md

Bei Bedarf gezielt lesen (nicht automatisch geladen):

| Datei | Inhalt |
|---|---|
| `.claude/brain/20-geraete-wissen.md` | Property-Keys, Enums, offene `# VERIFY`-Punkte |
| `.claude/brain/30-entscheidungen.md` | Entscheidungs-Protokoll: was wurde warum so gebaut |
| `.claude/brain/40-frontend-karten.md` | Die drei Karten, ASCII-Vertrag, Cache-Busting |
| `.claude/brain/90-offene-fragen.md` | Backlog, bekannte Unstimmigkeiten |

**Regel:** Wer eine Entscheidung trifft, die künftige Arbeit bindet, schreibt
sie ins Brain — bevorzugt nach `30-entscheidungen.md`. Der Skill
`brain-pflegen` beschreibt das Format.

## Skills, Agents, Befehle

| Ort | Was |
|---|---|
| `.claude/skills/ocp-entity/` | Neue Entität / Plattform bauen oder erweitern |
| `.claude/skills/ocp-release/` | Version anheben, taggen, HACS-Release |
| `.claude/skills/ocp-card/` | An den Lovelace-Karten arbeiten (ASCII-Vertrag!) |
| `.claude/skills/ocp-verify/` | `# VERIFY`-Punkte aus einem Diagnose-Export schließen |
| `.claude/skills/brain-pflegen/` | Brain aktuell halten |
| `.claude/agents/ocp-reviewer.md` | Review speziell für HA-Integrationen |
| `.claude/agents/ocp-diagnose.md` | Diagnose-Export auswerten |
| `/zentrale` | Lagebericht: Version, offene VERIFY-Punkte, Brain-Stand |
| `/release` | Release-Ablauf starten |
| `/verify` | Diagnose-Export auswerten und VERIFY-Punkte schließen |

## Nicht verhandelbar

1. **Keine Secrets. Nirgends.** Kein API Key, kein Access-/Refresh-Token in
   Code, Commits, Logs, Issues, Tests oder Beispielen. Rohe Fremd-Fehlertexte
   laufen vor dem Logging durch `util.scrub_secrets()`. Diagnostics redigiert
   über `TO_REDACT` — und indexiert Geräte als `appliance_0`, weil
   `async_redact_data` nur Werte schwärzt, niemals Dict-**Keys**.
2. **`unique_id` ist unantastbar.** Sie leitet sich vom **Roh**-Key ab
   (`f"{appliance_id}_{key}"`). Automationen und Verlaufsdaten der Nutzer:innen
   hängen daran. Anzeigenamen dürfen sich ändern, `unique_id` nie.
3. **Die API ist rate-limitiert.** Default-Poll 120 s, Leerlauf 600 s. Nichts
   einbauen, was den Takt dauerhaft beschleunigt. HTTP 403 heißt bei dieser API
   meist *Kontingent erschöpft*, **nicht** *Zugangsdaten falsch*.
4. **Ein einzelner Fehler erzwingt nie eine Neuanmeldung.** Erst Fehlerserien
   (401: 3×, 403: 10×) führen zu `ConfigEntryAuthFailed`. Diese Schwellen nicht
   ohne Not senken — sie sind die Antwort auf die wöchentliche
   Zwangs-Neuanmeldung.
5. **Karten-JS ist reines ASCII.** Umlaute nur als `\uXXXX` bzw. `@NNN;` +
   `D()`. Siehe `.claude/brain/40-frontend-karten.md`.
6. **Kein Reverse-Engineering.** Nur dokumentierte OCP-Developer-API. Das ist
   das Alleinstellungsmerkmal dieses Projekts gegenüber anderen Integrationen.

## Sprache und Stil

- **Deutsch, Du-Ansprache** — in Code-Kommentaren, Docstrings, UI-Strings,
  Commit-Nachrichten und im Brain. Der gesamte Bestand ist so geschrieben.
- Kommentare erklären **warum**, nicht was. Der Bestand tut das ausführlich und
  mit Datum bei Härtungen — dieser Ton wird fortgeführt.
- Typisierung: `from __future__ import annotations`, moderne Syntax
  (`str | None`), `Final` für Konstanten.
- Defensiv lesen: Die API-Struktur ist geräteabhängig. Zugriffe auf
  `reported`/`capabilities` laufen über die Helfer in `entity.py`, die im
  Zweifel ein leeres Dict liefern statt zu werfen.

## Prüfen vor dem Festschreiben

```bash
bash .claude/pruefen.sh
```

Ein Skript, fünf Prüfungen: Python-Syntax, JSON, ASCII-Vertrag der Karten,
Vollständigkeit der fünf Übersetzungsdateien, Gleichlauf von `manifest.json`
und `CARD_VERSION`. Rückgabewert 0 = sauber.

> Zwei Fallen, die das Skript für dich erledigt: Die Integration nutzt
> PEP-695-Syntax (`type X = ...`) und braucht **Python 3.12+** — das System-
> `python` ist oft älter. Und `grep '[^\x00-\x7F]'` interpretiert die Escapes
> **ohne `-P` nicht** und meldet dann jede Zeile als Treffer; der ASCII-Test
> läuft deshalb über Python.

CI prüft zusätzlich **HACS-Validation** und **Hassfest** (`.github/workflows/validate.yml`).
Ein Push eines Tags `vX.Y.Z` erzeugt automatisch ein GitHub-Release.

## Repo-Karte

| Datei | Rolle |
|---|---|
| `__init__.py` | Setup/Unload des Config-Entry, Plattform-Forwarding, Karten-Registrierung |
| `const.py` | Alle Konstanten, kuratierte Property-Metadaten, i18n-Slug-Mengen |
| `coordinator.py` | Poller, Fehlerserien-Logik, anpassender Takt, `async_boost` |
| `token_manager.py` | Restart-feste, doppelte Token-Persistenz (Entry + Sofort-Store) |
| `config_flow.py` | Einrichtung, Reauth, Options-Flow (Intervall) |
| `entity.py` | Basisklasse + Helfer: `get_reported`, `get_capabilities`, `build_command`, `get_nested`, `slugify_key` |
| `sensor.py` / `binary_sensor.py` | Lesende Entitäten (dynamisch + feste Alarm-Sensoren) |
| `select.py` / `switch.py` | Schreibende Entitäten aus schreibbaren Capabilities |
| `diagnostics.py` | Redigierter Diagnose-Dump |
| `frontend.py` | Registriert die drei Custom-Elements einmalig pro HA-Prozess |
| `frontend/*.js` | Geschirrspüler-Karte, Guides-Modul, Kaffee-Karte |
| `translations/*.json` | DE/EN/FR/IT/ES — Namen **und** Enum-States |
