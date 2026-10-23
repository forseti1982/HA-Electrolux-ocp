# Nebenkosten in Home Assistant – Einbau und Bedienung

## A. Einmalig einrichten

1. **Ordner kopieren.** Den Ordner `nebenkosten/` aus diesem Archiv nach `/config/`
   legen, sodass `/config/nebenkosten/werkzeug/nk.py` existiert.
   Weg: Samba-Freigabe, File-Editor-Add-on oder Terminal & SSH.

2. **Package kopieren.** `packages/nebenkosten.yaml` nach `/config/packages/`.
   Gibt es den Ordner `packages` noch nicht, zuerst anlegen.

3. **Einmal in `configuration.yaml`**, falls noch nicht vorhanden:

   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```

4. **Konfiguration prüfen** unter Entwicklerwerkzeuge → YAML → Konfiguration prüfen,
   danach **Home Assistant neu starten**.

5. Danach existieren zwölf Sensoren `sensor.nk_*`. Zeigen sie die Anzahl der
   erfassten Jahre und Prüfungen, ist der Einbau korrekt.

## B. Ein neues Abrechnungsjahr importieren

1. Im Dashboard auf **Vorlage nächstes Jahr** tippen. Das erzeugt
   `/config/nebenkosten/vorlagen/abrechnung_JJJJ-JJ.json` aus dem Vorjahr.
2. Die Vorlage ausfüllen: jedes `null` und jedes leere `quelle` ersetzen.
   Regeln in `IMPORT_FORMAT.md`, Beispiel in `daten/jahre/2023-24.json`.
3. Die fertige Datei nach `/config/nebenkosten/eingang/` legen.
4. Im Dashboard **Prüfen** tippen. Es wird nichts gespeichert. Das Ergebnis steht
   in der Statuskarte und als Mitteilung.
5. Ist alles grün, **Importieren** tippen. Erfolgreiche Dateien wandern nach
   `eingang/erledigt/`, fehlerhafte bleiben liegen.
6. Ein Jahr erneut einspielen geht nur über **Importieren (ersetzen)** mit
   Rückfrage. Die alte Fassung bleibt als `.bak` liegen.

Eine `ABWEICHUNG` blockiert den Import nicht – sie ist ein möglicher Fehler von
Hesta und gehört als neuer Befund nach `daten/befunde.json`.

## C. Was wo liegt

| Pfad | Inhalt |
|---|---|
| `/config/nebenkosten/daten/` | Quelle der Wahrheit, eine Datei je Jahr |
| `/config/nebenkosten/ausgabe/` | was das Dashboard zeigt, nie von Hand ändern |
| `/config/nebenkosten/eingang/` | hier die neue Jahresdatei ablegen |
| `/config/nebenkosten/werkzeug/nk.py` | das Werkzeug selbst |
| `/config/nebenkosten/werkzeug/ha_json.py` | verpackt ausgabe/ für die Sensoren |
| `/config/nebenkosten/werkzeug/ha_import.py` | verarbeitet den Eingangsordner |

**Nichts davon liegt unter `/config/www`.** Miete und Nebenkosten sind damit nicht
ohne Anmeldung abrufbar.

## D. Wenn etwas klemmt

- Sensoren `unknown`: Entwicklerwerkzeuge → Protokolle nach `command_line` durchsuchen.
  Meist stimmt ein Pfad nicht oder `/config/nebenkosten/` fehlt.
- Zahlen veraltet: **Importieren** erneut, oder `shell_command.nk_build` aufrufen
  und danach `homeassistant.update_entity` auf die `sensor.nk_*`.
- Nach Änderungen von Hand in `daten/` immer `nk_build` aufrufen.
