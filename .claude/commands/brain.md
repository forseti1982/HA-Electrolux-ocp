---
description: Brain aktualisieren — Entscheidungen, Geräte-Wissen, offene Fragen
argument-hint: "[was gemerkt werden soll]"
---

Trage Folgendes ins Projekt-Brain ein: $ARGUMENTS

Folge dem Skill `.claude/skills/brain-pflegen/SKILL.md`:

1. Entscheide, **welche** Brain-Datei zuständig ist (Entscheidung → `30`,
   belegtes Geräte-Wissen → `20`, API-Erkenntnis → `10`, Struktur → `00`,
   Karten → `40`, offener Punkt → `90`).
2. Schreibe im Format der Datei, auf Deutsch, mit konkreten Konstantennamen und
   Zahlen. Neue Entscheidungen kommen **oben**.
3. Prüfe zum Schluss mit der Gegenprobe aus dem Skill, ob die im Brain zitierten
   Werte noch zum Code passen. Bei Abweichung: Code gewinnt, Brain korrigieren.

Ist nichts angegeben, sieh dir `git diff` und die letzten Commits an und schlage
vor, was aus dieser Sitzung ins Brain gehört — dann frag kurz nach, bevor du
schreibst.
