---
description: Lagebericht der Zentrale — Version, Takt-Werte, offene VERIFY-Punkte, Brain-Stand, Arbeitszweig
---

Erstelle einen **Lagebericht** dieses Projekts. Führe die folgenden Befehle aus
und fasse das Ergebnis auf Deutsch in einer knappen Übersicht zusammen — keine
Rohausgaben abladen, sondern einordnen.

```bash
echo "=== Version ==="
grep '"version"' custom_components/electrolux_ocp/manifest.json
grep 'CARD_VERSION' custom_components/electrolux_ocp/const.py
git describe --tags --abbrev=0 2>/dev/null || echo "(kein Tag)"

echo "=== Zweig & Stand ==="
git rev-parse --abbrev-ref HEAD
git status --short
git log --oneline -5

echo "=== Takt & Schwellen ==="
grep -n "DEFAULT_SCAN_INTERVAL\|IDLE_SCAN_INTERVAL\|MIN_SCAN_INTERVAL\|COMMAND_BOOST_SECONDS" custom_components/electrolux_ocp/const.py
grep -n "_AUTH_FAILURES_BEFORE_REAUTH\|_FORBIDDEN_FAILURES_BEFORE_REAUTH" custom_components/electrolux_ocp/coordinator.py

echo "=== Offene VERIFY-Punkte ==="
grep -rn "VERIFY" custom_components/electrolux_ocp/*.py | wc -l

echo "=== Entitäts-Plattformen ==="
grep -n "Platform\." custom_components/electrolux_ocp/__init__.py

echo "=== Alle Pruefungen ==="
bash .claude/pruefen.sh
```

Bewerte anschließend:

1. **Stimmen `manifest.json`-Version und `CARD_VERSION` überein?** Wenn nicht:
   sag, warum das zählt (Cache-Busting der Karten).
2. **Weichen die Takt-/Schwellenwerte von dem ab, was im Brain steht?** Vergleich
   gegen `.claude/brain/00-architektur.md`. Bei Abweichung: Brain korrigieren.
3. **Was steht in `.claude/brain/90-offene-fragen.md`** ganz oben an? Nenne die
   nächsten zwei sinnvollen Schritte — nicht die ganze Liste.
4. **Uncommittete Änderungen?** Kurz einordnen, ob sie release-reif sind.

Halte dich kurz. Der Lagebericht soll in dreißig Sekunden lesbar sein.
