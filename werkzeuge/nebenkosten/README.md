# Nebenkosten-Werkzeug (Auslieferungspaket)

Dieser Ordner gehoert nicht zur Electrolux-Integration. Er liegt hier nur, weil
Home Assistant Dateien ueber `downloader.download_file` von einer HTTPS-Adresse
nach `/config` holen kann. Das Paket wird darueber installiert.

**Inhalt: ausschliesslich Programmcode.** Keine Abrechnungen, keine Betraege,
keine Adressen, keine Zugangsdaten. Die Daten des Mietverhaeltnisses werden
getrennt und nur im lokalen Netz uebertragen.

- `nebenkosten-ha-paket.zip` – das Archiv, das `shell_command.nk_setup` entpackt
- `fuer-config/` – derselbe Inhalt entpackt, zum Nachlesen
- `fuer-config/packages-nebenkosten-korrigiert.yaml` – das Package fuer `/config/packages/`
  mit dem gesuchten ZIP-Pfad und der gesaeuberten Jahresangabe

Installation: `ANLEITUNG.md` im Paket.
