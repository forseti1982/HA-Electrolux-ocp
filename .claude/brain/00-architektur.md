# Brain / Architektur

## Datenfluss

```
developer.electrolux.one  ──(API Key + Access + Refresh)──►  ConfigEntryTokenManager
          ▲                                                          │
          │ PUT /appliances/{id}/command                             ▼
   select / switch  ◄──────────────  ElectroluxDataUpdateCoordinator  ──►  sensor / binary_sensor
                                     (ein Poller je Config-Entry)
```

Ein Config-Entry = **ein OCP-Konto**. Mehrere Konten parallel sind vorgesehen
(mehrere Entries), deshalb ist jede prozessweite Registrierung (Frontend)
idempotent und jede Entry-bezogene Zustandshaltung an der `entry_id` verankert.

## Coordinator (`coordinator.py`)

- `_async_setup()` läuft **einmal**: Token-Abgleich (`async_prime`), API-Client
  bauen, Geräteliste laden. Die `Appliance`-Objekte werden über den gesamten
  Lebenszyklus **wiederverwendet** — Geräte-Info und Capabilities kosten so nur
  einen Abruf, pro Zyklus wird ausschließlich der State erneuert.
- `_async_update_data()` aktualisiert jedes Gerät, passt danach den Takt an und
  setzt die Fehlerserien zurück.
- **Timeout** je API-Interaktion: `API_TIMEOUT = 30` s.

### Anpassender Takt

Drei Zustände, Priorität von oben nach unten:

| Zustand | Takt | Warum |
|---|---|---|
| Nachlauf nach Befehl (`COMMAND_BOOST_SECONDS = 300`) | schnell | Nach `select`/`switch` liefert die API oft noch den **alten** Zustand. Ohne Nachlauf fiele der echte Start in ein Leerlauf-Loch. |
| Irgendein Gerät aktiv (`ACTIVE_APPLIANCE_STATES`) | schnell (= eingestelltes Intervall, Default 120 s) | Die Fertig-Ansage muss sitzen. |
| Alles still | `IDLE_SCAN_INTERVAL = 600` s | Salz, Klarspüler, Restzeit vertragen jede Trägheit. |

Unbekannter/leerer Zustand gilt **bewusst als aktiv** — im Zweifel lieber ein
paar Abrufe zu viel als eine verpasste Meldung.

Rechnung für einen Tag mit zwei Stunden Betrieb: 60 s durchgehend = 1440
Abrufe · 120 s durchgehend = 720 · anpassend (600/120) = ~190.

`_gemeldeter_zustand()` liegt **absichtlich lokal** in `coordinator.py` und wird
nicht aus `entity.py` importiert: `entity.py` importiert den Coordinator, der
Gegenimport erzeugt einen Ringschluss und die Integration lädt nicht mehr.

### Fehlerserien

`_STREAKS` ist ein **Modul-globales** Dict, keyed auf `entry_id` — und das mit
Absicht: Scheitert bereits das Setup, verwirft HA den Coordinator und baut bei
jedem Versuch einen neuen. Ein Zähler am Objekt startete dann jedes Mal bei null
und erreichte die Schwelle **nie** — bei wirklich abgelaufenen Zugangsdaten
würde endlos wiederholt und nie zur Neuanmeldung aufgefordert. Der Inhalt
überlebt einen HA-Neustart bewusst nicht: danach beginnt wieder volle Geduld.

Schwellen: `_AUTH_FAILURES_BEFORE_REAUTH = 3` (401), `_FORBIDDEN_FAILURES_BEFORE_REAUTH = 10` (403).

Ein `ValueError` aus `pyelectroluxgroup` ist **nicht automatisch** ein
Anmeldeproblem — die Bibliothek wirft ihn auch bei kaputtem JSON. Nur wenn der
(gescrubbte) Text `token`/`refresh`/`auth`/`credential`/`unauthor` enthält,
zählt er auf die Auth-Serie; sonst schlichtes `UpdateFailed`.

## Token-Persistenz (`token_manager.py`)

Die OCP-API **rotiert den Refresh-Token bei jedem Refresh mit**. Fünf Schichten
gegen den Neustart-Race:

1. Redundanter Sofort-Store (`helpers.storage.Store`, `async_delay_save(..., 0)`)
   neben dem debounced schreibenden Config-Entry.
2. „Frischester gewinnt" beim Setup (`async_prime`) über `CONF_TOKEN_TS`: der
   jüngere von Entry und Store gewinnt, der ältere wird nachgezogen.
3. Leere/`None`-Tokens werden **nie** persistiert.
4. Persistieren ist loop-sicher (`call_soon_threadsafe`), falls die Bibliothek
   `update()` je aus einem Executor-Thread aufruft.
5. Store-Lesefehler sind nicht fatal — Fallback auf den Config-Entry.

Der Konstruktor ruft bewusst **kein** `super().__init__()` auf: das würde sofort
persistieren.

## Entitäten

**Dynamische Erzeugung** ist das Grundprinzip — es gibt keine fest verdrahtete
Entitätsliste:

- `sensor.py`: jeder skalare (`str|int|float`) Eintrag aus `reported`, außer
  Bools und Keys aus `KNOWN_BINARY_KEYS`.
- `binary_sensor.py`: Bools + `KNOWN_BINARY_KEYS`, plus **immer** ein
  Konnektivitäts-Sensor und die festen Alarm-Sensoren aus `reported['alerts']`
  (`ALERT_SENSORS`) — fest angelegt, damit Automationen und die Karte stabil
  darauf zeigen können, auch wenn gerade kein Alarm ansteht.
- `select.py`: schreibbare Capabilities mit Werteliste (`_values_list`).
- `switch.py`: schreibbare boolesche Capabilities (`_is_boolean_cap`).

`KNOWN_SENSOR_KEYS` / `KNOWN_BINARY_KEYS` sind reine **Verschönerung**
(device_class, Einheit, Icon, Diagnose-Kategorie). Unbekannte Properties
entstehen trotzdem — nur generisch.

### i18n-Mechanik

`slugify_key(roh_key)` erzeugt den HA-Slug (`applianceState` →
`appliance_state`, `userSelections/extraPowerOption` →
`user_selections_extra_power_option`). Liegt der Slug in der passenden
`TRANSLATED_*_KEYS`-Menge, wird `_attr_translation_key` gesetzt und HA übersetzt
Name **und** Enum-States. Sonst greift `humanize()` als Fallback.

**Wichtig:** Bei gesetztem `translation_key` darf `_attr_name` **nicht** gesetzt
werden — es gewönne über die Übersetzung. Die `unique_id` bleibt in **jedem**
Fall am Roh-Key.

## Frontend-Registrierung (`frontend.py`)

Guards über `hass.data[f"{DOMAIN}_frontend_registered"]`, damit mehrere Entries
nicht mehrfach registrieren. Reihenfolge ist deterministisch gewählt: Guides →
Kaffee-Karte → Hauptkarte, damit `<electrolux-guides>` definiert ist, bevor die
Karte lädt. Fehlt eine Datei, läuft der Rest weiter (rollback-sicher).

Beim Unload wird **nicht** deregistriert: weder `async_register_static_paths`
noch `add_extra_js_url` bieten dafür eine stabile öffentliche API, und die
Registrierung ist prozessweit geteilt — ein Entfernen bräche andere Entries.
