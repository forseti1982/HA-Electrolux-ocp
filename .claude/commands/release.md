---
description: Neue Version veröffentlichen — Version anheben, prüfen, committen, taggen
argument-hint: "[neue Version, z. B. 0.2.7]"
---

Führe den Release-Ablauf aus. Folge dabei **genau** dem Skill
`.claude/skills/ocp-release/SKILL.md`.

Zielversion: $1 (fehlt sie, schlage anhand der Änderungen seit dem letzten Tag
eine Patch- oder Minor-Version vor und frag kurz nach).

Wichtig, in dieser Reihenfolge:

1. `manifest.json` **und** `CARD_VERSION` in `const.py` auf dieselbe Version.
2. Alle Prüfungen aus dem Skill durchlaufen lassen — vor allem den
   ASCII-Test der Karten-JS und die Secret-Suche im Diff.
3. README und Brain nachziehen, falls sich für Nutzer:innen etwas ändert.
4. Deutsche Commit-Nachricht im Bestandsstil: `vX.Y.Z: <Nutzen in einem Satz>`.
5. Push auf den aktuellen Arbeitszweig mit `git push -u origin <zweig>`.

**Nicht selbst taggen**, ohne dass der Stand auf `main` ist — sag mir stattdessen,
welcher Tag-Befehl fällig ist. Ein Tag löst sofort ein öffentliches Release aus.
