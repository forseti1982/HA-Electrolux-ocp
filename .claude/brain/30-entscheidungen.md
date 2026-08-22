# Brain / Entscheidungs-Protokoll

Was wurde **warum** so gebaut. Neue Einträge oben anfügen. Format:
`## JJJJ-MM-TT — Titel` → *Problem · Entscheidung · Begründung · Folgen*.

---

## 2026-08-18 — Nachlauf nach jedem Befehl (`async_boost`, v0.2.6b)

**Problem.** Man startet eine Ladung; die API meldet im ersten Abruf noch den
alten Zustand („läuft nicht"), der Takt drosselt auf Leerlauf — der echte Start
fällt bis zu zehn Minuten in ein Loch. Ausdrückliche Anforderung: Beim Starten
einer Ladung muss es schnell gehen.

**Entscheidung.** `select`/`switch` rufen nach jedem Kommando
`coordinator.async_boost()`. Das setzt ein Zeitfenster
(`COMMAND_BOOST_SECONDS = 300`), in dem unabhängig vom gemeldeten Zustand
schnell gepollt wird, und aktualisiert sofort.

**Warum nicht `async_request_refresh()`?** Weil genau der eine Abruf noch den
alten Zustand sieht und die Takt-Anpassung danach auf Leerlauf stellt. Das
Fenster schlägt den gemeldeten Zustand.

---

## 2026-08-18 — Schluss mit der wöchentlichen Zwangs-Neuanmeldung (v0.2.6)

**Problem.** Ein einziger 401/403 führte sofort zu `ConfigEntryAuthFailed`, also
zur Neuanmeldung von Hand. Ein einzelner Aussetzer der Gegenstelle legte die
Integration bis zum nächsten Handgriff lahm — obwohl der Refresh-Token gültig
war.

**Entscheidung.** Fehlerserien statt Einzelfehler: 401 ab dem 3., 403 erst ab
dem 10. Mal in Folge. Jeder erfolgreiche Poll setzt zurück. Die Serien leben
modul-global unter der `entry_id`, nicht am Coordinator-Objekt.

**Begründung.** 403 heißt bei dieser API meist *Kontingent erschöpft*, nicht
*falsche Zugangsdaten* — das war die eigentliche Fehldiagnose. Und: Scheitert
bereits das Setup, verwirft HA den Coordinator; ein Zähler am Objekt erreichte
die Schwelle nie und hätte bei wirklich abgelaufenen Zugangsdaten endlos
wiederholt.

**Zusätzlich:** Log-Level auf `WARNING` — bei der Neuanmeldung am 18.08. stand
im Protokoll kein Grund. Ab jetzt ist der Status immer sichtbar.

---

## 2026-08-18 — Anpassender Poll-Takt (v0.2.6)

**Problem.** Ein fester schneller Takt rund um die Uhr verschwendet das
Tageskontingent. `DEFAULT_SCAN_INTERVAL` lag mit 60 s zudem unter der eigenen
Empfehlung.

**Entscheidung.** Default auf 120 s. Leerlauf-Takt 600 s, wenn kein Gerät ein
Programm fährt. Unbekannter Zustand gilt als aktiv.

**Folge (bewusst in Kauf genommen).** Der *Start* eines Programms wird bis zu
zehn Minuten spät bemerkt. Folgenlos, weil danach schnell gepollt wird und das
*Ende* auf zwei Minuten genau sitzt — und das Ende ist die Ansage. Für den von
Hand ausgelösten Start deckt der Nachlauf (oben) den Fall ab.

---

## 2026-08-06 — Test-/Diagnoseprogramme ausblenden (v0.2.4)

Options-Keys, die `_HIDDEN` oder `HIDDEN_TEST` enthalten
(`HIDDEN_OPTION_FRAGMENTS`), werden aus den Select-Optionen gefiltert — damit
verschwinden sie aus dem nativen Dropdown **und** aus den Programm-Pills der
Karte. Ist der aktuell gemeldete Wert eine gefilterte Option, liefert
`current_option` sauber `None` statt zu krachen.

---

## 2026-08-06 — `userSelections`-Write-Fix: verschachtelter Payload (v0.2.2)

**Problem.** Schalter für `userSelections/*` schlugen mit HTTP 500 fehl — auch
bei Optionen, die für das laufende Programm erlaubt sind.

**Ursache.** Die API erwartet **Container**: `{"userSelections":
{"extraSilentOption": true}}`. Der flache Body mit Slash-Key wird mit
`COMMAND_VALIDATION_ERROR: Capability not found` abgelehnt.

**Entscheidung.** `entity.build_command()` verschachtelt generisch von innen
nach außen; `entity.get_nested()` liest die Gegenrichtung. Details und Belege:
`.claude/brain/10-api-ocp.md`.

---

## 2026-08-05 — Feste Alarm-Sensoren aus `reported['alerts']` (v0.2.1)

Salz fehlt / Klarspüler niedrig werden **immer** als `binary_sensor` mit
`device_class: problem` angelegt, nicht nur bei aktivem Alarm. Grund:
Automationen und die Lovelace-Karte brauchen eine stabile Entität, auf die sie
zeigen können. `_alert_codes()` liest das Feld robust — es kann fehlen, `None`
oder eine Liste aus Strings **oder** Objekten (`code`/`alert`/`name`) sein.

---

## 2026-08-05 — i18n über `translation_key`, nicht über Namen

**Entscheidung.** Bekannte Slugs (`TRANSLATED_*_KEYS`) setzen
`_attr_translation_key`; HA übersetzt Name **und** Enum-States in fünf Sprachen.
Unbekannte Keys behalten den `humanize()`-Fallback.

**Nicht verhandelbar.** Bei gesetztem `translation_key` **kein** `_attr_name`
setzen (es gewönne). Und: `unique_id` bleibt am **Roh**-Key — Automationen der
Nutzer:innen hängen daran, Anzeigenamen dürfen wandern, IDs nie.

---

## 2026-08-05 — Restart-feste Token-Persistenz (v0.1.1)

**Problem.** `async_update_entry` schreibt **verzögert**. Ein Neustart kurz nach
einer Token-Rotation startete mit dem alten, verbrauchten Refresh-Token → 400/401
→ Zwangs-Reauth.

**Entscheidung.** Fünfschichtige Härtung: redundanter Sofort-Store,
Zeitstempel-Abgleich „frischester gewinnt", nie leere Tokens, loop-sicheres
Schreiben, nicht-fatale Store-Lesefehler. Details:
`.claude/brain/00-architektur.md`.

---

## 2026-08-05 — Auto-Release beim Tag-Push

HACS zeigt Versionen aus **Releases**. `.github/workflows/release.yml` erzeugt
bei jedem Tag `v*` automatisch ein Release mit generierten Notes — sonst ist
eine getaggte Version für Nutzer:innen unsichtbar.

---

## 2026-07-23 — Karte wird mitgeliefert und selbst registriert

**Entscheidung.** `frontend.py` registriert Static-Path + `add_extra_js_url`
einmalig pro HA-Prozess. Kein separater HACS-Karten-Install, kein manuelles
Hinzufügen einer Lovelace-Ressource: *installieren = Daten + Grafik*.

**Preis.** Beim Unload wird nicht deregistriert — es gibt keine stabile
öffentliche API dafür, und die Registrierung ist prozessweit geteilt. Sie ist
idempotent und überlebt bis zum HA-Neustart.

---

## 2026-07-23 — Diagnostics: Geräte anonym indexieren

`async_redact_data` schwärzt nur **Werte** anhand ihrer Keys, niemals Dict-Keys
selbst. Eine Appliance-ID als Dict-Key wäre also durchgerutscht. Deshalb
`appliance_0`, `appliance_1`, … in sortierter (deterministischer) Reihenfolge.
