# Brain / Geräte-Wissen: Properties, Enums, offene VERIFY-Punkte

Die OCP-API liefert je Gerät und Firmware **unterschiedliche** Schlüssel. Die
Integration erzeugt Entitäten dynamisch — die Tabellen in `const.py` sind reine
Verschönerung. Dieses Dokument hält fest, was gesichert ist und was nicht.

## Gesichert

- Container-Struktur bei Slash-Keys (`userSelections/*`) — am Gerät belegt,
  siehe `.claude/brain/10-api-ocp.md`.
- Alarm-Codes `DISH_ALARM_SALT_MISSING`, `DISH_ALARM_RINSE_AID_LOW` aus
  `reported['alerts']` (v0.2.1, gegen echte Enums abgeglichen).
- Phasen-/Programm-Enums der Übersetzungen (v0.2.1: „Uebersetzungen auf echte
  Geraete-Enums (MAINWASH..) + Programmnamen").
- Klarspüler ist eine **Dosierstufe**, keine Füllstands-Prozentzahl.
- Versteckte Programme tragen `_HIDDEN` / `HIDDEN_TEST` im Options-Key.

## Kuratierte Sensor-Keys (`KNOWN_SENSOR_KEYS`)

| Key | device_class | Einheit | Diagnose |
|---|---|---|---|
| `applianceState`, `applianceMode`, `cyclePhase` | – | – | nein |
| `displayTemperature`, `targetTemperatureC`, `temperature` | temperature | °C | nein |
| `waterHardness`, `waterSoftenerMode` | – | – | **ja** |
| `rinseAidLevel`, `saltLevel`, `programUID` | – | – | nein |
| `timeToEnd`, `runningTime`, `startTime`, `remainingTime` | duration | s | nein |
| `waterConsumption` | water | L | **ja** |
| `energyConsumption` | energy | kWh | **ja** |
| `spinSpeed` | – | rpm | nein |

`waterConsumption` und `energyConsumption` stehen in `TOTAL_INCREASING_KEYS` →
`SensorStateClass.TOTAL_INCREASING`. Das ist nötig für die Langzeitstatistik
und vermeidet die HA-Warnung „energy + measurement".

## Kuratierte Binary-Keys (`KNOWN_BINARY_KEYS`)

`doorState`/`doorOpen` → `door` · `doorLock` → `lock` ·
`rinseAidState`/`saltState` → `problem` · `runningState` → `running`.

Wert-Interpretation (**# VERIFY**, genaue Enums geräteabhängig):
- `DOOR_OPEN_VALUES = {OPEN, OPENED, DOOR_OPEN, True, ON}`
- `PROBLEM_TRUE_VALUES = {LOW, EMPTY, NEEDS_REFILL, TRUE, True, ON}`
- Fallback für sonstige: `{ON, TRUE, OPEN, ACTIVE, RUNNING}`

## Aktive Zustände (`ACTIVE_APPLIANCE_STATES`)

`RUNNING`, `RUNNINGONDEMAND`, `RUNNING_ON_DEMAND`, `DELAYEDSTART`,
`DELAYED_START`, `PAUSED`, `CYCLEACTIVE`, `CYCLE_ACTIVE`.
Der Vergleich entfernt vorher Leerzeichen und schreibt groß. Unbekannt/leer =
**aktiv** (im Zweifel schnell pollen).

## Offene `# VERIFY`-Punkte

| Ort | Was ist unsicher |
|---|---|
| `const.py` (Kopf `KNOWN_SENSOR_KEYS`) | exakte Property-Schlüssel je Gerät/Firmware |
| `const.py` (`DOOR_OPEN_VALUES`, `PROBLEM_TRUE_VALUES`) | genaue Enum-Werte für Tür und Warnungen |
| `const.py` (i18n-Block) | Enum-Werte/Keys der Übersetzungen |
| `entity.py` (`get_reported`) | Struktur von `properties.reported` |
| `entity.py` (`get_capabilities`) | Capabilities-Struktur (beobachtet: flaches Dict) |
| `select.py`, `switch.py` (Modul-Docstring) | Schreib-Kommandos generell — **teilweise überholt**, siehe unten |

**Achtung, überholte Docstrings:** Die Kopf-Kommentare in `select.py` und
`switch.py` sagen noch „Body wird als `{key: value}` gesendet". Das stimmt seit
v0.2.2 nicht mehr — der Body wird über `build_command()` verschachtelt, und
genau das ist am Gerät belegt. Beim nächsten Anfassen dieser Dateien mit
korrigieren (Eintrag steht in `90-offene-fragen.md`).

## Wie ein VERIFY-Punkt geschlossen wird

Über einen **Diagnose-Export** vom echten Gerät (Gerät → drei Punkte →
„Diagnosen herunterladen"; Secrets sind darin redigiert). Ablauf: Skill
`ocp-verify` bzw. `/verify`. Das Ergebnis gehört in dieses Dokument — Zeile aus
„offen" nach „gesichert" verschieben, mit Datum und Gerätemodell.

## Geräte-Deckung

| Gerät | Stand |
|---|---|
| Geschirrspüler | Fokus. Karte, Guides, Alarme, Übersetzungen |
| Waschmaschine, Trockner | generisch abgedeckt (dynamische Entitäten), community-verifiziert |
| Luftreiniger, Klima | generisch abgedeckt |
| Kaffeevollautomat (Home Connect, Bosch/Siemens) | **nur die Karte** liegt bei — sie liest fremde Entitäten, die *nicht* aus dieser Integration stammen |
