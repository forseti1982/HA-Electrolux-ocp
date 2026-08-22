---
name: ocp-verify
description: Offene "# VERIFY"-Punkte mit einem Diagnose-Export vom echten Gerät schließen — Property-Schlüssel, Enum-Werte, Capabilities-Struktur belegen und den Code anpassen. Nutze dies bei "Diagnose", "diagnostics.json", "VERIFY", "falsche Werte", "Entität heißt komisch", "Enum stimmt nicht".
---

# `# VERIFY`-Punkte schließen

Die Integration wurde ohne echte Tokens gebaut. Alles, was ohne Hardware nicht
belegbar war, ist im Code mit `# VERIFY` markiert. Der einzige saubere Weg, das
zu schließen, ist ein **Diagnose-Export** von einem echten Gerät.

## Den Export beschaffen

In Home Assistant: **Einstellungen → Geräte & Dienste → Electrolux OCP → Gerät →
Drei-Punkte-Menü → „Diagnosen herunterladen"**.

Der Export ist **redigiert** (`diagnostics.py`, `TO_REDACT`): Tokens, API Key,
Seriennummern, IDs, MAC, E-Mail. Geräte erscheinen als `appliance_0`, `…_1`.
Trotzdem gilt: **vor dem Anhängen an ein Issue kurz durchsehen.** Findest du
etwas Ungeschwärztes, ist das ein Fehler in `TO_REDACT` — Key dort ergänzen,
bevor irgendetwas geteilt wird.

## Auswerten

Interessant sind vier Teile:

| Feld | Was es beantwortet |
|---|---|
| `appliances.appliance_N.reported` | Welche Property-Schlüssel meldet das Gerät wirklich? Welche Enum-Werte? |
| `…capabilities` | Was ist schreibbar (`access`)? Welcher `type`? Welche `values`? |
| `…info` | brand / model — für die Notiz im Brain |
| `…connectionState`, `…status` | Belegt die Werte, die `available` auswertet |

Schnellauswertung:

```bash
python3 - /pfad/zur/diagnostics.json <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
for name, a in (d.get("data", d)).get("appliances", {}).items():
    print("="*60); print(name, a.get("type"), (a.get("info") or {}).get("model"))
    print("-- reported --")
    for k, v in sorted((a.get("reported") or {}).items()):
        print(f"  {k:38} = {v!r}"[:120])
    print("-- schreibbare capabilities --")
    for k, c in sorted((a.get("capabilities") or {}).items()):
        if isinstance(c, dict) and "write" in str(c.get("access", "")).lower():
            vals = c.get("values")
            vals = list(vals)[:8] if isinstance(vals, (dict, list)) else vals
            print(f"  {k:38} type={c.get('type')} values={vals}")
PY
```

## Abgleichen und anpassen

1. **Property-Schlüssel** gegen `KNOWN_SENSOR_KEYS` / `KNOWN_BINARY_KEYS`
   halten. Gemeldete, aber unbekannte Keys → Metadaten ergänzen (Skill
   `ocp-entity`).
2. **Enum-Werte** gegen `DOOR_OPEN_VALUES`, `PROBLEM_TRUE_VALUES`,
   `ACTIVE_APPLIANCE_STATES` halten. Fehlende ergänzen — vorhandene **nicht
   entfernen**: andere Geräte/Firmwares melden andere Werte, die Mengen sind
   absichtlich großzügig.
3. **Slugs** über `slugify_key()` bilden und prüfen, ob sie in den
   `TRANSLATED_*_KEYS` stehen und in **allen fünf** `translations/*.json`
   auftauchen.
4. **`unique_id` niemals ändern** — auch nicht, wenn ein Key jetzt „schöner"
   heißen könnte. Der Anzeigename darf wandern, die ID nicht.

## Danach — der eigentliche Ertrag

Belegte Erkenntnisse gehören ins Brain, sonst waren sie umsonst:

- `.claude/brain/20-geraete-wissen.md`: Zeile aus „Offene `# VERIFY`-Punkte" nach
  „Gesichert" verschieben, **mit Datum und Gerätemodell**.
- Den `# VERIFY`-Kommentar im Code entfernen oder präzisieren — er ist eine
  Warnung an alle, die nach dir kommen, und darf nicht stehen bleiben, wenn die
  Sache belegt ist.
- Bei überraschendem Befund: Eintrag in `.claude/brain/30-entscheidungen.md`.
