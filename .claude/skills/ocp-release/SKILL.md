---
name: ocp-release
description: Eine neue Version der Electrolux-OCP-Integration veröffentlichen — Version anheben, prüfen, committen, taggen, pushen; HACS-Release entsteht automatisch. Nutze dies bei "Release", "Version", "taggen", "veröffentlichen", "HACS-Update".
---

# Release

Der Tag ist die Auslieferung: `.github/workflows/release.yml` erzeugt bei jedem
Push eines Tags `v*` automatisch ein GitHub-Release mit generierten Notes. **HACS
zeigt Versionen aus Releases** — ohne Tag sieht niemand die neue Version.

## Versionsregeln

- Format ausschließlich `X.Y.Z`. **Keine Buchstaben-Suffixe** wie `0.2.6b`; HACS
  und `AwesomeVersion` erwarten `X.Y.Z`. Ein nachgeschobener Fix bekommt eine
  eigene Patch-Version.
- Der Tag heißt `v` + Version: `0.2.7` → `v0.2.7`.
- `manifest.json` → `"version"` ist die Wahrheit. Sie **muss** zum Tag passen.

## Ablauf

1. **Version festlegen** (Patch für Fixes, Minor für neue Fähigkeiten).

2. **Beide Versionen anheben.**
   ```bash
   NEU=0.2.7
   python3 - "$NEU" <<'PY'
   import json, pathlib, re, sys
   neu = sys.argv[1]
   m = pathlib.Path("custom_components/electrolux_ocp/manifest.json")
   d = json.loads(m.read_text(encoding="utf-8")); d["version"] = neu
   m.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
   c = pathlib.Path("custom_components/electrolux_ocp/const.py"); t = c.read_text(encoding="utf-8")
   c.write_text(re.sub(r'CARD_VERSION: Final = "[^"]+"', f'CARD_VERSION: Final = "{neu}"', t), encoding="utf-8")
   print("manifest + CARD_VERSION ->", neu)
   PY
   ```
   **`CARD_VERSION` immer mitziehen**, auch wenn die Karten unverändert blieben:
   sie ist das Cache-Busting aller drei Frontend-Dateien, und ein Auseinander-
   laufen hat schon einmal dazu geführt, dass Browser die alte Karte behielten.

3. **Prüfen** — muss mit Rückgabewert 0 durchlaufen:
   ```bash
   bash .claude/pruefen.sh
   ```
   Deckt ab: Syntax, JSON, ASCII-Vertrag der Karten, Vollständigkeit aller fünf
   Übersetzungsdateien, Gleichlauf von `manifest.json` und `CARD_VERSION`.
   Zusätzlich von Hand, weil ein Skript das nicht beurteilen kann:
   ```bash
   git diff | grep -Ei "eyJ|api[_-]?key|refresh[_-]?token|serialNumber"   # muss leer sein
   ```

4. **README nachziehen**, falls sich Funktionsumfang, Entitäten oder
   Karten-Konfiguration geändert haben.

5. **Brain nachziehen**: bindende Entscheidung nach
   `.claude/brain/30-entscheidungen.md`; erledigte Punkte in
   `.claude/brain/90-offene-fragen.md` nach „Geschlossen".

6. **Committen** — deutsche Nachricht im Bestandsstil
   (`vX.Y.Z: <was sich für Nutzer:innen ändert>`), erklärt *warum*, nicht *was*:
   ```bash
   git add -A
   git commit -m "v0.2.7: <Nutzen in einem Satz>"
   ```

7. **Push auf den Arbeitszweig** (nie direkt auf einen fremden Zweig):
   ```bash
   git push -u origin "$(git rev-parse --abbrev-ref HEAD)"
   ```

8. **Taggen und Tag pushen** — erst wenn der Stand auf `main` ist:
   ```bash
   git tag "v$NEU" && git push origin "v$NEU"
   ```
   Danach läuft der Release-Workflow. Prüfen, dass er grün ist und das Release
   erscheint.

## Was CI prüft

`.github/workflows/validate.yml` bei jedem Push und PR, zusätzlich täglich 04:00 UTC:

- **HACS-Validation** (`hacs/action@main`, Kategorie `integration`,
  `ignore: description topics` — das sind Repo-Metadaten aus dem GitHub-UI)
- **Hassfest** (`home-assistant/actions/hassfest`) — prüft `manifest.json` gegen
  die HA-Anforderungen

Schlägt Hassfest fehl, liegt es fast immer an `manifest.json`: Feldreihenfolge,
fehlende Pflichtfelder, oder eine `requirements`-Angabe ohne feste Version.

## Vor jedem Release kurz gegenprüfen

- [ ] `bash .claude/pruefen.sh` gibt 0 zurück (deckt Version/`CARD_VERSION`,
      ASCII, JSON und Übersetzungen ab)
- [ ] `manifest.json` `version` == geplanter Tag ohne `v`
- [ ] Keine Secrets im Diff: `git diff --cached | grep -Ei "eyJ|api[_-]?key|refresh[_-]?token"`
- [ ] README stimmt noch
- [ ] Brain nachgezogen (`30-entscheidungen.md`, `90-offene-fragen.md`)
