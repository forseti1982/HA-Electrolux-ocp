<div align="center">

# 🧺 Electrolux OCP for Home Assistant

### Electrolux & AEG appliances via the official OCP Developer API.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![Version](https://img.shields.io/github/v/release/forseti1982/HA-Electrolux-ocp?style=for-the-badge&color=ff8a3c)](https://github.com/forseti1982/HA-Electrolux-ocp/releases)
[![Electrolux · AEG](https://img.shields.io/badge/Electrolux%20%C2%B7%20AEG-004B93?style=for-the-badge)](https://developer.electrolux.one)

Bringt deine **Electrolux-/AEG-Geräte** über die **offizielle OCP Developer-API** ([developer.electrolux.one](https://developer.electrolux.one)) in Home Assistant — mit **API Key + Access Token + Refresh Token**.
*Fokus Geschirrspüler, generisch für weitere Geräte. Kein Reverse-Engineering, keine App-Zugangsdaten.*

</div>

---

> [!WARNING]
> **🚧 BETA / experimentell.** Der Auth-/API-Flow ist gegen quelloffene Referenz-Clients belegt, aber einige gerätespezifische Feld- und Enum-Details sind im Code als `# VERIFY` markiert und **noch nicht gegen echte Hardware geprüft**. Bis dahin gilt: funktioniert grundsätzlich, kann aber je Gerät ungenaue Namen/Einheiten haben. [Diagnose-Export](#️-fehlerbehebung) hilft beim Verifizieren.

## 🧭 Was ist das?

Electrolux und AEG bieten für ihre vernetzten Geräte eine **offizielle Entwickler-API** an ([developer.electrolux.one](https://developer.electrolux.one)). Diese Integration nutzt genau diesen dokumentierten Weg — mit einem selbst erzeugten **API Key** sowie **Access-/Refresh-Token** — und bringt Zustand und Steuerung deiner Geräte in Home Assistant.

**Mehrbenutzer & generisch:** Jede:r trägt die **eigenen** Zugangsdaten ein (keine hartkodierten Werte, keine geteilten Credentials), mehrere Konten parallel möglich. Entitäten werden **dynamisch** aus den gemeldeten Geräte-Eigenschaften erzeugt — daher funktioniert die Integration über den Geschirrspüler-Fokus hinaus auch für Waschmaschinen, Trockner, Luftreiniger, Klimageräte und mehr.

## 🏗️ Wie es funktioniert

```mermaid
flowchart LR
  A["developer.electrolux.one<br/>API Key + Access + Refresh Token"] -->|Auto-Refresh| B[Electrolux OCP Coordinator]
  B -->|GET /appliances/&#123;id&#125;/state<br/>cloud polling| C["Sensoren / Binary-Sensoren"]
  B --> D["Select / Switch"]
  D -->|PUT /appliances/&#123;id&#125;/command| A
  C --> E[Dashboards & Automationen]
  D --> E
```

- **Coordinator** — ein gemeinsamer Poller hält alle Entitäten synchron und übersteht Ausfälle.
- **Token-Refresh** — der kurzlebige Access-Token wird automatisch über Refresh-Token + API Key erneuert; der rotierte Refresh-Token wird persistiert. Bei Ablauf startet HA automatisch einen **Reauth-Dialog**.
- **Entitäten** — lesende `sensor` / `binary_sensor` (Zustand, Programm, Phase, Restlaufzeit, Tür, Salz-/Klarspüler, Konnektivität) und schreibende `select` / `switch` (soweit die API Kommandos erlaubt).

## ✨ Features

- ☁️ **Offizielle OCP Developer-API** — sauber dokumentierter Weg, kein App-Reverse-Engineering.
- 🔁 **Automatischer Token-Refresh** + 🔐 **Reauth-Flow**.
- 👥 **Mehrbenutzer/generisch** — eigene Credentials, mehrere Konten, dynamische Entitäten.
- 🍽️ **Geschirrspüler-Fokus** — Zustand, Programm, Phase, Restlaufzeit, Tür, Salz-/Klarspüler-Warnung.
- 🎛️ **Lesen & Steuern** — `sensor`/`binary_sensor` + `select`/`switch`.
- 🩺 **Diagnose mit redigierten Secrets** — Tokens/Seriennummern/PII werden automatisch entfernt.
- 🌍 **Mehrsprachig** — Deutsch (Du) & Englisch.

## 📦 Installation

### Via HACS (empfohlen)

1. **HACS → Drei-Punkte-Menü → Custom repositories**.
2. URL `https://github.com/forseti1982/HA-Electrolux-ocp`, Kategorie **Integration**, hinzufügen.
3. In HACS **„Electrolux OCP"** suchen und installieren.
4. Home Assistant **neu starten**.

### Manuell

Ordner `custom_components/electrolux_ocp` nach `config/custom_components/` kopieren und HA neu starten.

## ⚙️ Einrichtung

1. Auf [developer.electrolux.one](https://developer.electrolux.one) mit dem **gleichen Konto** wie in der Electrolux-/AEG-App anmelden.
2. Im [Dashboard](https://developer.electrolux.one/dashboard) einen **API Key** erstellen sowie **Access Token** und **Refresh Token** erzeugen.
3. In HA: **Einstellungen → Geräte & Dienste → Integration hinzufügen → „Electrolux OCP"**, dann alle **drei** Werte eintragen.
4. Optional: **Abfrage-Intervall** in den Optionen anpassen (Default 60 s; die API ist rate-limitiert, ≥ 120 s empfohlen).

## ✅ Unterstützt

| Bereich | Status |
|---|---|
| Auth-Flow (API Key + Access + Refresh, Auto-Refresh, Reauth) | ✅ gegen Referenz-Clients belegt |
| Geschirrspüler (Zustand/Programm/Phase/Restzeit/Tür/Salz/Klarspüler) | 🟠 Fokus — Feldnamen `# VERIFY`, an echter Hardware zu prüfen |
| Waschmaschine / Trockner / Luftreiniger / Klima | 🟠 generisch abgedeckt, community-verifiziert |
| Schreibende Kommandos (`select`/`switch`) | 🟠 experimentell, `# VERIFY` |

## 📇 Mitgelieferte Karte

Die Integration bringt eine **plastische Geschirrspüler-Karte** mit
(Metrology-Design, 3 Zustände: aus / läuft / fertig, inkl. Tür-Animation und
Bedien-Oberfläche). Sie wird beim Setup **automatisch geladen** — kein separater
HACS-Karten-Install und kein manuelles Hinzufügen einer Lovelace-Ressource
nötig. Der Kartentyp `custom:electrolux-ocp-card` steht direkt zur Verfügung
(auch im visuellen Karten-Picker mit Vorschau).

> Nach der Installation ggf. **einmal den Browser-Cache leeren / hart neu laden**
> (Strg/Cmd+Shift+R), damit das Frontend die neue Karte kennt.

Die Karte ist **config-getrieben** und hat einen Demo-Fallback (zeigt ohne
`entities` eine Demo-Ansicht). Beispiel-Konfiguration:

```yaml
type: custom:electrolux-ocp-card
entities:
  state: sensor.geschirrspuler_appliancestate      # Betriebszustand
  running: binary_sensor.geschirrspuler_runningstate # läuft ja/nein
  progress: sensor.geschirrspuler_progress          # Fortschritt 0-100 (optional)
  phase: sensor.geschirrspuler_cyclephase           # aktuelle Phase
  time_remaining: sensor.geschirrspuler_timetoend   # Restlaufzeit
  door: binary_sensor.geschirrspuler_doorstate      # Türzustand
  salt: sensor.geschirrspuler_saltlevel             # Salz-Füllstand/-Warnung
  rinse: sensor.geschirrspuler_rinseaidlevel        # Klarspüler
  remote_control: binary_sensor.geschirrspuler_remotecontrol  # Fernsteuerung aktiv
  # --- Steuerung (nur falls die API Kommandos erlaubt) ---
  program_select: select.geschirrspuler_program     # Programmwahl (nutzt attributes.options)
  delay: number.geschirrspuler_startdelay           # Startvorwahl
  start_button: button.geschirrspuler_start
  pause_button: button.geschirrspuler_pause
  resume_button: button.geschirrspuler_resume
  stop_button: button.geschirrspuler_stop
  options:
    hygiene_rinse: switch.geschirrspuler_hygiene
    extra_dry: switch.geschirrspuler_extra_dry
    intensive_zone: switch.geschirrspuler_intensivzone
```

> [!NOTE]
> Die **exakten Entity-Suffixe** hängen an den `# VERIFY`-Punkten und werden am
> echten Gerät finalisiert (die Integration erzeugt Entitäten dynamisch aus den
> gemeldeten Properties). Obiges Mapping ist ein Beispiel — passe die
> Entity-IDs an die bei dir tatsächlich angelegten Entitäten an. Alle Felder
> sind optional; nur vorhandene werden angezeigt.

## ⚠️ Disclaimer

Inoffizielles Community-Projekt. Steht in **keiner** Verbindung zur Electrolux Group und wird von ihr weder unterstützt noch geprüft. „Electrolux" und „AEG" sind Marken ihrer jeweiligen Eigentümer. Nutzung auf eigene Verantwortung, ohne Gewähr.

## 🛠️ Fehlerbehebung

- **403 / 401:** API Key und Tokens prüfen (Tippfehler/Leerzeichen). Access Token ist kurzlebig — bei anhaltendem Fehler frische Tokens im [Dashboard](https://developer.electrolux.one/dashboard) erzeugen; HA startet bei Ablauf automatisch den Reauth-Dialog. Sicherstellen, dass das **gleiche Konto** wie in der App genutzt wird; bei hartnäckigem 403 einmal auf der regionalen Electrolux-/AEG-Website einloggen.
- **429 (Rate-Limit):** Poll-Intervall in den Optionen erhöhen (≥ 120 s).
- **Falsche/fehlende Werte:** Diagnose-Export erstellen (Gerät → drei Punkte → **„Diagnosen herunterladen"**; Secrets sind darin **redigiert**) und einem Issue anhängen — so lassen sich die `# VERIFY`-Punkte für dein Gerät schließen.

> 🔐 **Sicherheit:** API Key und Tokens geheim halten — niemals in Issues, Logs oder Screenshots einfügen. Dieses Repo enthält **keine** echten Zugangsdaten (nur Platzhalter).
