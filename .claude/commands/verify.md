---
description: Diagnose-Export auswerten und offene VERIFY-Punkte schließen
argument-hint: "[Pfad zur diagnostics.json]"
---

Werte den Diagnose-Export aus: $1

Folge dem Skill `.claude/skills/ocp-verify/SKILL.md`.

Prüfe **zuerst**, ob der Export sauber redigiert ist (keine JWTs, keine
Seriennummer, keine echte Appliance-ID als Dict-Key). Ist er es nicht, ist das
der erste Befund — dann fehlt ein Key in `diagnostics.TO_REDACT`. Gib selbst
keine ungeschwärzten Werte wieder.

Liefere danach:
- gemeldete Property-Keys gegen `const.py` abgeglichen,
- beobachtete Enum-Werte gegen `DOOR_OPEN_VALUES` / `PROBLEM_TRUE_VALUES` /
  `ACTIVE_APPLIANCE_STATES`,
- schreibbare Capabilities und ob sie als `select` oder `switch` landen,
- konkrete Diffs für `const.py` und die fünf `translations/*.json`,
- welche Zeilen in `.claude/brain/20-geraete-wissen.md` von „offen" nach
  „gesichert" wandern (mit Datum und Modell).

Trenne strikt **belegt** von **vermutet**. Vermutungen bleiben `# VERIFY`.
