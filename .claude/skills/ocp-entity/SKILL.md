---
name: ocp-entity
description: Entitäten der Electrolux-OCP-Integration bauen oder ändern — Sensor, Binary-Sensor, Select, Switch, neue Plattformen, Property-Metadaten, Übersetzungen. Nutze dies, sobald eine Entität, ein Property-Key, ein translation_key, eine unique_id, device_class oder ein Kommando-Body im Spiel ist.
---

# Entitäten in dieser Integration

## Das Grundprinzip zuerst

Es gibt **keine fest verdrahtete Entitätsliste**. Entitäten entstehen zur
Laufzeit aus dem, was das Gerät meldet:

- `reported` (aus `properties.reported`) → `sensor` / `binary_sensor`
- `capabilities` mit `access` enthält `write` → `select` / `switch`

Eine „neue Entität hinzufügen" heißt deshalb fast nie *eine Klasse schreiben*,
sondern meist: **Metadaten für einen Key ergänzen**.

## Ablauf: Property schöner darstellen

1. Key in `const.py` eintragen:
   - Skalar → `KNOWN_SENSOR_KEYS[key] = (device_class, unit, icon, diagnostic)`
   - Boolesch/Zustand → `KNOWN_BINARY_KEYS[key] = (device_class, icon, diagnostic)`
   - Kumulativer Verbrauch → zusätzlich in `TOTAL_INCREASING_KEYS`
     (sonst warnt HA bei `energy` + `measurement`)
2. Übersetzen: `slugify_key(key)` gedanklich anwenden (`applianceState` →
   `appliance_state`), den Slug in die passende `TRANSLATED_*_KEYS`-Menge legen
   **und** in **alle fünf** `translations/*.json` eintragen (de, en, fr, it, es).
   Fehlt eine Sprache, zeigt HA den rohen Enum-Wert — nie schlechter als vorher,
   nur unübersetzt.
3. Nichts weiter. Die Plattform findet den Key von selbst.

## Die drei Fallen

**Falle 1 — `unique_id`.** Sie leitet sich vom **Roh**-Key ab
(`f"{appliance_id}_{key}"`, bei select/switch mit Suffix `_select`/`_switch`).
Automationen und Verlaufsdaten der Nutzer:innen hängen daran. Anzeigenamen
dürfen wandern, `unique_id` **nie**. Wer sie ändert, zerstört fremde
Installationen.

**Falle 2 — `translation_key` und `_attr_name` schließen sich aus.** Ist der Slug
in `TRANSLATED_*_KEYS`, wird `_attr_translation_key` gesetzt und **kein**
`_attr_name` — sonst gewinnt der Name über die Übersetzung. Das Muster steht
identisch in allen vier Plattformen; halte dich daran.

**Falle 3 — Slash-Keys.** `userSelections/extraSilentOption` liegt im
`reported`-State **verschachtelt**. Lies mit `get_nested(reported, key)`, nie mit
`reported.get(key)`. Und schreibe mit `build_command(key, value)`, nie mit einem
flachen Dict — der flache Body wird von der API abgelehnt
(`Capability not found`, am Gerät als HTTP 500). Details:
`.claude/brain/10-api-ocp.md`.

## Neue Plattform anlegen (z. B. `number`, `button`)

1. `custom_components/electrolux_ocp/<plattform>.py` nach dem Muster von
   `switch.py` bauen: `async_setup_entry` iteriert `coordinator.data`, filtert
   Capabilities, hängt Entitäten an.
2. Klasse erbt von `ElectroluxEntity` **und** der HA-Entity-Klasse — in dieser
   Reihenfolge.
3. `Platform.<NAME>` in `PLATFORMS` in `__init__.py` ergänzen.
4. Schreibende Aktion: nach `appliance.send_command(build_command(...))`
   **immer** `await self.coordinator.async_boost()` — nicht
   `async_request_refresh()`. Grund im Brain, Eintrag 2026-08-18.
5. Fehler beim Senden → `HomeAssistantError` mit deutschem Text, nie roher
   Fremdtext in die UI.
6. `strings.json` **und** alle fünf `translations/*.json` ergänzen.

## Defensiv lesen — immer

Struktur und Schlüssel sind geräte- und firmwareabhängig. Zugriff **nur** über
die Helfer aus `entity.py`: `get_reported`, `get_capabilities`, `get_nested`,
`is_writable`. Sie liefern im Zweifel leer statt zu werfen. Ein `KeyError` in
einer Property nimmt sonst die ganze Entität mit.

## Prüfen

```bash
bash .claude/pruefen.sh
```

Prüfung 4 des Skripts vergleicht die fünf `translations/*.json` gegeneinander.
Fehlt in einer Sprache ein Schlüssel, fällt das dort auf — sonst fehlt still ein
Name und HA zeigt den rohen Enum-Wert.

## Danach

Bindende Entscheidung getroffen? → `.claude/brain/30-entscheidungen.md`.
Enum/Property am Gerät belegt? → `.claude/brain/20-geraete-wissen.md`.
