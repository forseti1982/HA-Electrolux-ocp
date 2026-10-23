"""Regressionstests: python3 -m unittest discover -s tests   (aus dem Projektordner)

1. build() erzeugt exakt die geprüften Referenzdaten (referenz/*.json).
2. Jede Jahresdatei in daten/jahre/ besteht die Strukturprüfung.
3. Kaputte Importdateien werden abgelehnt.
4. Ein Import in eine Kopie des Projekts läuft durch und ändert die Altjahre nicht.
"""
import copy, json, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'werkzeug'))
import nk  # noqa: E402

GEPRUEFT = ['kosten', 'jahre', 'positionen', 'wasser', 'techem', 'liegenschaft', 'pruefungen', 'befunde', 'wohnkosten', 'miete_monat']

# Die Referenzdaten gehoeren zum Mietverhaeltnis und sind nicht Teil des Pakets.
# Fehlen sie, werden die zwei Vergleichstests uebersprungen statt zu scheitern.
HAT_REFERENZ = (ROOT / 'referenz' / 'kosten.json').exists()
OHNE_REFERENZ = 'referenz/ fehlt - Vergleichstest ausgelassen'


class TestNK(unittest.TestCase):
    @unittest.skipUnless(HAT_REFERENZ, OHNE_REFERENZ)
    def test_build_gleich_referenz(self):
        sets = nk.build(quiet=True)
        for n in GEPRUEFT:
            ref = json.load(open(ROOT / 'referenz' / f'{n}.json', encoding='utf-8'))
            self.assertEqual(ref, sets[n], f'{n} weicht von referenz/{n}.json ab')

    def test_jahresdateien_gueltig(self):
        for p in sorted((ROOT / 'daten' / 'jahre').glob('*.json')):
            F, _ = nk.validiere(json.load(open(p, encoding='utf-8')))
            self.assertEqual(F, [], f'{p.name}: {F}')

    def test_fehler_werden_erkannt(self):
        d = json.load(open(ROOT / 'daten' / 'jahre' / '2023-24.json', encoding='utf-8'))
        kaputt = copy.deepcopy(d)
        kaputt['jahr'] = '2023-24'
        kaputt['wohnung']['positionen'][0]['kategorie'] = 'Heizöl'
        kaputt['wohnung']['positionen'][1]['betrag'] = "1'418.05"
        kaputt['wasser']['umlage_pct_8_10_12'] = None
        F, _ = nk.validiere(kaputt)
        self.assertTrue(any('jahr' in f for f in F))
        self.assertTrue(any('Heizöl' in f for f in F))
        self.assertTrue(any('Zahl' in f for f in F))
        self.assertTrue(any('umlage' in f for f in F))

    @unittest.skipUnless(HAT_REFERENZ, OHNE_REFERENZ)
    def test_import_in_kopie(self):
        with tempfile.TemporaryDirectory() as tmp:
            kopie = Path(tmp) / 'p'
            shutil.copytree(ROOT, kopie, ignore=shutil.ignore_patterns('ausgabe', '__pycache__'))
            d = json.load(open(kopie / 'daten' / 'jahre' / '2023-24.json', encoding='utf-8'))
            d['jahr'] = '2024/25'; d['periode'] = {'von': '2024-10-01', 'bis': '2025-09-30'}
            f = Path(tmp) / 'neu.json'; json.dump(d, open(f, 'w', encoding='utf-8'), ensure_ascii=False)
            r = subprocess.run([sys.executable, str(kopie / 'werkzeug' / 'nk.py'), 'import', str(f)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            jahre = json.load(open(kopie / 'ausgabe' / 'jahre.json', encoding='utf-8'))
            self.assertEqual(jahre[-1]['jahr'], '2024/25')
            ref = json.load(open(ROOT / 'referenz' / 'jahre.json', encoding='utf-8'))
            self.assertEqual(jahre[:-1], ref)
            r2 = subprocess.run([sys.executable, str(kopie / 'werkzeug' / 'nk.py'), 'import', str(f)], capture_output=True, text=True)
            self.assertNotEqual(r2.returncode, 0, 'zweiter Import ohne --ersetzen muss abgelehnt werden')


if __name__ == '__main__':
    unittest.main()
