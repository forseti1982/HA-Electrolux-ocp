#!/usr/bin/env bash
# Alle lokalen Pruefungen dieses Projekts an EINER Stelle.
# Aufruf:  bash .claude/pruefen.sh
# Rueckgabe: 0 = alles sauber, sonst Anzahl der Befunde.
# Bewusst umlautfrei (laeuft auch in Umgebungen ohne UTF-8-Locale).

set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
BEFUNDE=0
melde() { echo "  FEHLER: $*"; BEFUNDE=$((BEFUNDE + 1)); }

# Die Integration nutzt PEP-695-Syntax ("type X = ...") und braucht daher
# Python 3.12+. Das System-"python" ist oft aelter -> gezielt suchen.
PY=""
for c in python3.13 python3.12 python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys;sys.exit(0 if sys.version_info>=(3,12) else 1)' 2>/dev/null; then
    PY="$c"; break
  fi
done

echo "== 1/5 Python-Syntax =="
if [ -z "$PY" ]; then
  echo "  UEBERSPRUNGEN: kein Python >= 3.12 gefunden (PEP 695 in coordinator.py)"
else
  echo "  Interpreter: $PY ($("$PY" -V 2>&1))"
  "$PY" -m compileall -q custom_components/electrolux_ocp >/dev/null 2>&1 || melde "Syntaxfehler in custom_components/"
fi

echo "== 2/5 JSON =="
"${PY:-python3}" - <<'PY' || melde "ungueltiges JSON"
import json, pathlib, sys
rc = 0
paths = list(pathlib.Path("custom_components/electrolux_ocp").rglob("*.json"))
paths += [p for p in (pathlib.Path("hacs.json"), pathlib.Path(".claude/settings.json")) if p.exists()]
for p in paths:
    try:
        json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  {p}: {e}"); rc = 1
sys.exit(rc)
PY

echo "== 3/5 ASCII-Vertrag der Karten =="
# Achtung: 'grep [^\x00-\x7F]' ohne -P interpretiert die Escapes NICHT und
# matcht dann jede Zeile. Deshalb Python statt grep.
"${PY:-python3}" - <<'PY' || melde "Nicht-ASCII im Karten-JS"
import pathlib, sys
rc = 0
for p in sorted(pathlib.Path("custom_components/electrolux_ocp/frontend").glob("*.js")):
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if not line.isascii():
            print(f"  {p}:{i}: {line.strip()[:70]}"); rc = 1
sys.exit(rc)
PY

echo "== 4/5 Uebersetzungen vollstaendig =="
"${PY:-python3}" - <<'PY' || melde "Uebersetzungsschluessel weichen ab"
import json, pathlib, sys
def flach(d, pre=""):
    out = set()
    for k, v in d.items():
        out |= flach(v, f"{pre}{k}.") if isinstance(v, dict) else {pre + k}
    return out
dateien = sorted(pathlib.Path("custom_components/electrolux_ocp/translations").glob("*.json"))
mengen = {p.name: flach(json.loads(p.read_text(encoding="utf-8"))) for p in dateien}
alle = set().union(*mengen.values()) if mengen else set()
rc = 0
for name, keys in mengen.items():
    fehlt = alle - keys
    if fehlt:
        print(f"  {name}: {len(fehlt)} Schluessel fehlen, z.B. {sorted(fehlt)[:4]}"); rc = 1
sys.exit(rc)
PY

echo "== 5/5 Version und CARD_VERSION =="
"${PY:-python3}" - <<'PY' || melde "Version und CARD_VERSION laufen auseinander"
import json, pathlib, re, sys
v = json.loads(pathlib.Path("custom_components/electrolux_ocp/manifest.json").read_text(encoding="utf-8"))["version"]
m = re.search(r'CARD_VERSION: Final = "([^"]+)"', pathlib.Path("custom_components/electrolux_ocp/const.py").read_text(encoding="utf-8"))
c = m.group(1) if m else "?"
print(f"  manifest={v}  CARD_VERSION={c}")
if v != c:
    print("  -> Karten-Cache-Busting haengt hinterher (siehe .claude/brain/90-offene-fragen.md)")
    sys.exit(1)
PY

echo
if [ "$BEFUNDE" -eq 0 ]; then echo "Alles sauber."; else echo "$BEFUNDE Befund(e)."; fi
exit "$BEFUNDE"
