# Brain / Die OCP Developer-API

Quelle: **developer.electrolux.one** — die *offizielle*, dokumentierte
Entwickler-API der Electrolux Group (Marken Electrolux und AEG). Zugang über
das [Dashboard](https://developer.electrolux.one/dashboard): API Key erzeugen,
Access Token und Refresh Token erzeugen. Es muss **dasselbe Konto** sein wie in
der Hersteller-App.

Client-Bibliothek: `pyelectroluxgroup==0.2.7` (siehe `manifest.json`). Wir
sprechen die API **nicht** direkt an, sondern über `ElectroluxHubAPI` und
`Appliance`.

## Authentifizierung

Drei Werte, alle vom Nutzer selbst erzeugt, nichts hartkodiert:

| Feld | Konstante | Bemerkung |
|---|---|---|
| API Key | `CONF_API_KEY` | langlebig |
| Access Token | `CONF_ACCESS_TOKEN` | kurzlebig, JWT (`eyJ…`) |
| Refresh Token | `CONF_REFRESH_TOKEN` | **rotiert bei jedem Refresh mit** |
| Zeitstempel | `CONF_TOKEN_TS` | unser eigenes Feld für „frischester gewinnt" |

Die Rotation ist der Kern aller Härtung: Wer den neuen Refresh-Token verliert,
verliert den Zugang. Siehe `.claude/brain/00-architektur.md` → Token-Persistenz.

## HTTP-Status: Bedeutung in diesem Kontext

| Status | Bedeutung hier | Reaktion im Code |
|---|---|---|
| **401** | Recht eindeutig Anmeldung — aber ein Einzelfall ist ein Aussetzer | Serie zählen, ab 3× `ConfigEntryAuthFailed`, sonst `UpdateFailed` |
| **403** | **Meist erschöpftes Kontingent**, nicht falsche Zugangsdaten | Serie zählen, ab 10× Reauth, sonst `UpdateFailed` mit Rate-Limit-Text |
| **429** | Rate-Limit | sofort `UpdateFailed`, Intervall erhöhen |
| Timeout | Gegenstelle träge | `UpdateFailed` |

**403 als „Anmeldedaten kaputt" zu deuten war die eigentliche Fehldiagnose**
hinter der wöchentlichen Zwangs-Neuanmeldung. Diese Zeile bitte nie zurückbauen.

Alle UI-Meldungen sind generisch und secret-frei (`_MSG_AUTH`, `_MSG_RATE`,
`_MSG_TIMEOUT`). Detail geht nur gescrubbt ins Debug-Log.

## Rate-Limit

Die API ist dokumentiert kontingentiert. Referenz-Clients
(`homebridge-electrolux-devices`) warnen ausdrücklich vor Intervallen unter
120 s.

- `DEFAULT_SCAN_INTERVAL = 120` (am 18.08.2026 von 60 angehoben)
- `MIN_SCAN_INTERVAL = 30` (Untergrenze im Options-Flow)
- `RECOMMENDED_MIN_SCAN_INTERVAL = 120`
- `IDLE_SCAN_INTERVAL = 600`

## Datenstruktur

```
appliance.initial_data   -> {"applianceName": ..., "applianceType": ...}
appliance.info_data      -> {"brand": ..., "model": ..., "serialNumber": ...}
appliance.state_data     -> {"connectionState": ..., "status": ...,
                             "properties": {"reported": { … }}}
appliance.capabilities_data -> {property_name: {access, type, values?, min?, max?, step?}}
```

Zugriff **immer** über die defensiven Helfer in `entity.py`
(`get_reported`, `get_capabilities`) — nie direkt indexieren. Struktur und
Schlüssel sind geräte- und firmwareabhängig.

`connectionState` gilt als verbunden bei `connected` / `online` / `true`
(case-insensitiv).

## Kommandos — die Container-Regel

**Das ist die wichtigste API-Erkenntnis dieses Projekts.**

Ein Capability-Key mit Slash, z. B. `userSelections/extraSilentOption`, **muss**
verschachtelt gesendet werden:

```python
{"userSelections": {"extraSilentOption": value}}     # richtig
{"userSelections/extraSilentOption": value}          # wird abgelehnt
```

Der flache Body führt zu `COMMAND_VALIDATION_ERROR: Capability not found` und
äußert sich am Gerät als **HTTP 500** — auch bei Optionen, die für das laufende
Programm ausdrücklich erlaubt sind. Top-Level-Keys ohne Slash
(`executeCommand`, `waterHardness`) bleiben flach.

`entity.build_command(key, value)` erledigt das generisch (von innen nach außen
verschachteln). Die Gegenrichtung ist `entity.get_nested(reported, key)`: der
`reported`-State spiegelt dieselbe Container-Struktur, ein flaches
`reported.get(slash_key)` liefert fälschlich `None`.

Beleg (verifiziert 2026-08):
- `pyelectroluxgroup==0.2.7` → `appliance.send_command` sendet `json=command`
  unverändert an `appliances/{id}/command`.
- `TTLucian/ha-electrolux` RELEASE_NOTES v3.4.8 + `switch.py`/`select.py`/`button.py`:
  `command = {entity_source: {entity_attr: value}}`, Split am `/`.

## Nach jedem Kommando

`select`/`switch` rufen `coordinator.async_boost()` — **nicht**
`async_request_refresh()`. Grund: Die API liefert unmittelbar nach dem Befehl
oft noch den alten Zustand; ein reiner Refresh stellte den Takt danach
fälschlich auf Leerlauf, und der echte Start fiele bis zu zehn Minuten in ein
Loch.

## Was diese Integration bewusst NICHT tut

- Keine App-Zugangsdaten, kein Reverse-Engineering der Mobile-App-API.
- Keine hartkodierten Keys, keine geteilten Credentials.
- Kein Push/WebSocket — die Developer-API ist Cloud-Polling
  (`iot_class: cloud_polling`).
