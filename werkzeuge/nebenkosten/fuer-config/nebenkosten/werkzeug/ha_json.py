#!/usr/bin/env python3
"""Verpackt eine Datei aus ausgabe/ so, dass ein command_line-Sensor sie lesen kann.

Grund: json_attributes von Home Assistant erwartet ein JSON-OBJEKT. Die Dateien in
ausgabe/ sind JSON-ARRAYS. Dieses Skript legt das Array unter den Schluessel "rows"
und ergaenzt "n" mit der Zeilenzahl, die dann der Zustand des Sensors wird.
Nur Standardbibliothek, keine Abhaengigkeiten.
"""
import json
import sys

def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"rows": [], "n": 0, "fehler": "kein Pfad uebergeben"}))
        return 1
    pfad = sys.argv[1]
    try:
        with open(pfad, encoding="utf-8") as f:
            daten = json.load(f)
    except FileNotFoundError:
        print(json.dumps({"rows": [], "n": 0, "fehler": "Datei fehlt: " + pfad}))
        return 1
    except json.JSONDecodeError as e:
        print(json.dumps({"rows": [], "n": 0, "fehler": "kaputtes JSON: " + str(e)}))
        return 1
    if isinstance(daten, list):
        aus = {"rows": daten, "n": len(daten)}
    elif isinstance(daten, dict):
        aus = dict(daten)
        aus.setdefault("n", 1)
    else:
        aus = {"rows": [daten], "n": 1}
    print(json.dumps(aus, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
