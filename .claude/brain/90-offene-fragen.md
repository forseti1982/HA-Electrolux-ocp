# Brain / Offene Fragen und Backlog

Stand: 2026-08-22. Erledigtes nach unten unter „Geschlossen" verschieben, mit
Datum.

## Unstimmigkeiten im Bestand (klein, konkret)

1. **`CARD_VERSION` hinkt hinterher.**
   `const.py` → `CARD_VERSION = "0.2.5"`, `manifest.json` → `"version": "0.2.6"`.
   `CARD_VERSION` ist das Cache-Busting **aller drei** Frontend-Dateien. Solange
   sie unverändert bleiben, ist das folgenlos — beim nächsten Karten-Eingriff
   aber zwingend anzuheben. Vorschlag: `CARD_VERSION` im Release-Ablauf immer
   mit der Integrationsversion gleichziehen (Skill `ocp-release` sieht das vor).

2. **Die Version `0.2.6b` existiert nur in einer Commit-Nachricht.**
   Geprüft am 2026-08-22: Es gibt **keinen** Tag `v0.2.6b`. Der Tag `v0.2.6`
   zeigt auf `e451191` — also auf den Commit, der sich „v0.2.6b" nennt. Manifest
   (`0.2.6`), Tag (`v0.2.6`) und HACS-Release stimmen damit überein; nur die
   Commit-Nachricht führt eine Version, die es nicht gibt.
   **Regel ab jetzt: keine Buchstaben-Suffixe.** HACS und `AwesomeVersion`
   erwarten `X.Y.Z`; ein nachgeschobener Fix bekommt eine eigene Patch-Version.
   Nebenwirkung im Bestand: das Release `v0.2.6` enthält zwei Änderungen
   (Fehlerserien/Takt **und** Nachlauf), die als zwei Versionen gedacht waren.

3. **Überholte Docstrings in `select.py` und `switch.py`.**
   Beide Modul-Docstrings sagen noch, der Body werde als `{key: value}`
   gesendet. Seit v0.2.2 verschachtelt `build_command()`. Der Code ist richtig,
   nur der Text ist alt.

## Fachlich offen

4. **`# VERIFY`-Punkte am echten Gerät schließen.** Liste in
   `.claude/brain/20-geraete-wissen.md`. Ohne Diagnose-Export von echter
   Hardware bleiben Enums und Property-Schlüssel Vermutung. Ablauf: `/verify`.

5. **Keine automatisierten Tests.** Es gibt keinen `tests/`-Ordner; CI prüft nur
   HACS-Validation und Hassfest. Die reinen Funktionen in `entity.py`
   (`build_command`, `get_nested`, `slugify_key`, `humanize`) und `util.py`
   (`scrub_secrets`) sind ohne HA-Abhängigkeiten testbar — das wäre der billigste
   Anfang mit dem höchsten Ertrag (`build_command` ist der Fix, der schon einmal
   HTTP 500 verursacht hat).

6. **`number`- und `button`-Plattformen fehlen.** Die README-Beispielkonfiguration
   der Karte nennt `number.…startdelay` und `button.…start/pause/resume/stop`.
   `PLATFORMS` in `__init__.py` führt nur SENSOR, BINARY_SENSOR, SELECT, SWITCH.
   Startvorwahl und Start/Stopp laufen derzeit über `executeCommand` als Select.
   Zu entscheiden: eigene Plattformen bauen oder das README-Beispiel angleichen.

7. **Kaffee-Karte ohne Datenquelle im Projekt.** `coffee-machine-card.js` liest
   Home-Connect-Entitäten (Bosch/Siemens), die diese Integration nicht liefert.
   Das ist als Beigabe gedacht — sollte im README aber ausdrücklich dastehen,
   damit niemand eine Electrolux-Kaffeemaschinen-Anbindung erwartet.

## Geschlossen

- **2026-08-22 — `.gitignore` angelegt.** `custom_components/electrolux_ocp/__pycache__/*.pyc`
  lag untracked im Baum, es gab keine `.gitignore`. Jetzt ignoriert: Python-Artefakte,
  `.storage/`, `secrets.yaml`, `*.log`, `diagnostics*.json` (Diagnose-Exporte gehören
  nie ins Repo) und `.claude/settings.local.json` (die geteilte `settings.json` bleibt
  versioniert).
