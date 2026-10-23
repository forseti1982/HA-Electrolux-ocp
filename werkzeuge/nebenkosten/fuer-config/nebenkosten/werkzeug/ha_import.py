#!/usr/bin/env python3
"""Verarbeitet alle Jahresdateien im Eingangsordner und schreibt das Ergebnis als JSON.

Aufruf:
    ha_import.py pruefen              nur pruefen, nichts speichern
    ha_import.py import               pruefen und uebernehmen
    ha_import.py import --ersetzen    auch ein vorhandenes Jahr ueberschreiben

Erfolgreich importierte Dateien wandern nach eingang/erledigt/. Fehlerhafte bleiben
liegen, damit man sie korrigieren und erneut ablegen kann. Das Ergebnis landet in
ausgabe/ha_import_status.json und wird von einem command_line-Sensor gelesen.
Nur Standardbibliothek.
"""
import datetime
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EINGANG = ROOT / "eingang"
ERLEDIGT = EINGANG / "erledigt"
NK = ROOT / "werkzeug" / "nk.py"
STATUS = ROOT / "ausgabe" / "ha_import_status.json"

def schreibe(zustand: str, meldung: str, dateien: list) -> None:
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps({
        "zustand": zustand,
        "meldung": meldung,
        "dateien": dateien,
        "anzahl": len(dateien),
        "zeitpunkt": datetime.datetime.now().isoformat(timespec="seconds"),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def bundle_einlesen() -> list:
    """Stellt Daten aus einem Buendel in eingang/*.ndjson wieder her.

    Jede Zeile ist ein JSON-Objekt {"pfad": "daten/...json", "inhalt": {...}}.
    Zeilen, die kein JSON sind, werden uebergangen - so stoert auch eine
    Kopfzeile nicht, die ein Schreibkanal voranstellt. Erlaubt sind nur Pfade
    unterhalb von daten/ und referenz/, damit ein Buendel nichts ausserhalb
    ueberschreibt.
    """
    ergebnis = []
    for b in sorted(EINGANG.glob("*.ndjson")):
        geschrieben, uebersprungen = [], 0
        for zeile in b.read_text(encoding="utf-8").splitlines():
            zeile = zeile.strip()
            if not zeile.startswith("{"):
                uebersprungen += 1
                continue
            try:
                satz = json.loads(zeile)
            except json.JSONDecodeError:
                uebersprungen += 1
                continue
            pfad = str(satz.get("pfad", ""))
            erlaubt = pfad.startswith("daten/") or pfad.startswith("referenz/")
            if not erlaubt or ".." in pfad or not pfad.endswith(".json"):
                uebersprungen += 1
                continue
            ziel = ROOT / pfad
            ziel.parent.mkdir(parents=True, exist_ok=True)
            ziel.write_text(
                json.dumps(satz.get("inhalt"), ensure_ascii=False, indent=1) + "\n",
                encoding="utf-8",
            )
            geschrieben.append(pfad)
        ziel_b = ERLEDIGT / b.name
        if ziel_b.exists():
            ziel_b = ERLEDIGT / (b.stem + "_" + datetime.datetime.now().strftime("%Y%m%d%H%M%S") + b.suffix)
        b.rename(ziel_b)
        ergebnis.append({
            "datei": b.name,
            "modus": "buendel",
            "status": "ok" if geschrieben else "leer",
            "geschrieben": geschrieben,
            "anzahl_geschrieben": len(geschrieben),
            "uebersprungen": uebersprungen,
            "verschoben_nach": "eingang/erledigt/" + ziel_b.name,
        })
    return ergebnis


def main() -> int:
    modus = sys.argv[1] if len(sys.argv) > 1 else "pruefen"
    ersetzen = "--ersetzen" in sys.argv
    if modus not in ("pruefen", "import"):
        schreibe("fehler", "Unbekannter Modus: " + modus, [])
        return 2

    ERLEDIGT.mkdir(parents=True, exist_ok=True)
    buendel = bundle_einlesen()
    kandidaten = sorted(p for p in EINGANG.glob("*.json") if p.is_file())
    if not kandidaten:
        if buendel:
            n = sum(b["anzahl_geschrieben"] for b in buendel)
            schreibe("ok", f"{n} Datei(en) aus {len(buendel)} Buendel wiederhergestellt.", buendel)
            return 0
        schreibe("leer", "Keine Datei im Eingangsordner.", [])
        return 0

    dateien, fehler = list(buendel), 0
    for p in kandidaten:
        argv = [sys.executable, str(NK), modus, str(p)]
        if modus == "import" and ersetzen:
            argv.append("--ersetzen")
        lauf = subprocess.run(argv, capture_output=True, text=True, cwd=str(ROOT))
        text = (lauf.stdout + lauf.stderr).strip()
        gut = lauf.returncode == 0
        eintrag = {
            "datei": p.name,
            "modus": modus,
            "status": "ok" if gut else "fehler",
            "ausgabe": text[-1500:],
            "abweichungen": text.count("ABWEICHUNG"),
            "rundungen": text.count("Rundung"),
        }
        if gut and modus == "import":
            ziel = ERLEDIGT / p.name
            if ziel.exists():
                ziel = ERLEDIGT / (p.stem + "_" + datetime.datetime.now().strftime("%Y%m%d%H%M%S") + p.suffix)
            p.rename(ziel)
            eintrag["verschoben_nach"] = "eingang/erledigt/" + ziel.name
        if not gut:
            fehler += 1
        dateien.append(eintrag)

    if fehler:
        schreibe("fehler", f"{fehler} von {len(dateien)} Datei(en) fehlerhaft. Nichts uebernommen aus diesen.", dateien)
        return 1
    abw = sum(d.get("abweichungen", 0) for d in dateien)
    hinweis = f" {abw} ABWEICHUNG(en) gefunden - als Befund erfassen." if abw else ""
    schreibe("ok", f"{len(dateien)} Datei(en) {modus}: erfolgreich.{hinweis}", dateien)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
