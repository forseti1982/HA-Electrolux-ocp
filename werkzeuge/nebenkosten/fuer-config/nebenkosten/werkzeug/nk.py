#!/usr/bin/env python3
"""nk.py – Nebenkosten Mietobjekt: Jahresdateien prüfen, importieren und Dashboard-Daten bauen.

Befehle
  python3 werkzeug/nk.py vorlage 2024/25           leere Importdatei aus dem Vorjahr erzeugen (vorlagen/)
  python3 werkzeug/nk.py pruefen  DATEI.json        nur prüfen, nichts speichern
  python3 werkzeug/nk.py import   DATEI.json [--ersetzen]
                                                    prüfen, nach daten/jahre/ übernehmen, alles neu bauen
  python3 werkzeug/nk.py build                      ausgabe/*.json aus daten/ neu erzeugen

Quelle der Wahrheit sind die Dateien in daten/ (jahre/*.json, stammdaten.json, miete.json, befunde.json).
ausgabe/ wird immer vollständig neu erzeugt – dort nie von Hand ändern.
Nur Python-Standardbibliothek, Python 3.9+.
"""
import json, re, sys, shutil, statistics, collections, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATEN, AUSGABE, VORLAGEN = ROOT / 'daten', ROOT / 'ausgabe', ROOT / 'vorlagen'
FORMAT = 'nk-mietobjekt/1'
KAT = ['Heizung', 'Warmwasser', 'Wasser/Abwasser', 'Allg. Nebenkosten', 'Lift', 'TV-Gebühren', 'Verwaltungshonorar']
TOL_OK, TOL_RUNDUNG = 0.05, 0.5


def r2(x):
    return round(x + 1e-9, 2)


def num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def jahr_key(y):
    return y.replace('/', '-')


# ---------------------------------------------------------------- Laden
def lade_alles():
    stamm = json.load(open(DATEN / 'stammdaten.json', encoding='utf-8'))
    jahre = [json.load(open(p, encoding='utf-8')) for p in sorted((DATEN / 'jahre').glob('*.json'))]
    jahre.sort(key=lambda d: d['jahr'])
    miete = json.load(open(DATEN / 'miete.json', encoding='utf-8'))
    befunde = json.load(open(DATEN / 'befunde.json', encoding='utf-8'))
    return stamm, jahre, miete, befunde


# ---------------------------------------------------------------- Prüfen (Struktur)
def validiere(d, stamm=None):
    """Gibt (fehler, warnungen) zurück. Fehler blockieren den Import, Warnungen nicht."""
    F, W = [], []
    def req(obj, key, path, typ=None, nullable=False):
        if not isinstance(obj, dict) or key not in obj:
            F.append(f'{path}.{key} fehlt'); return None
        v = obj[key]
        if v is None:
            if not nullable: F.append(f'{path}.{key} darf nicht leer sein')
            return None
        if typ == 'num' and not num(v): F.append(f'{path}.{key} muss eine Zahl sein (Punkt als Dezimalzeichen, kein Apostroph), ist {v!r}')
        if typ == 'str' and not isinstance(v, str): F.append(f'{path}.{key} muss Text sein')
        if typ == 'str' and key == 'quelle' and isinstance(v, str) and not v.strip():
            F.append(f'{path}.quelle fehlt (Beleg angeben, z. B. Seiten-ID «NK7-003-002» oder «Abrechnung Hesta 20.05.2026 S. 1»)')
        if typ == 'list' and not isinstance(v, list): F.append(f'{path}.{key} muss eine Liste sein')
        if typ == 'obj' and not isinstance(v, dict): F.append(f'{path}.{key} muss ein Objekt sein')
        return v

    if d.get('format') != FORMAT: F.append(f'format muss "{FORMAT}" sein')
    y = req(d, 'jahr', '', 'str')
    if y and not re.fullmatch(r'\d{4}/\d{2}', y): F.append('jahr im Format JJJJ/JJ, z. B. "2024/25"')
    elif y and int(y[2:4]) + 1 != int(y[5:7]) % 100 and not (y[2:4] == '99' and y[5:7] == '00'):
        F.append('jahr: zweite Jahreszahl muss auf die erste folgen')
    per = req(d, 'periode', '', 'obj')
    if per:
        for k in ('von', 'bis'):
            v = req(per, k, 'periode', 'str')
            if v:
                try: datetime.date.fromisoformat(v)
                except ValueError: F.append(f'periode.{k} als Datum JJJJ-MM-TT')
    req(d, 'zeitanteil', '', 'obj', nullable=True)
    req(d, 'erfasst', '', 'obj')
    hh = req(d, 'haushalt', '', 'obj')
    if hh: req(hh, 'personen', 'haushalt', 'num')

    w = req(d, 'wohnung', '', 'obj')
    if w:
        req(w, 'seiten', 'wohnung', 'list')
        pos = req(w, 'positionen', 'wohnung', 'list') or []
        if not pos: F.append('wohnung.positionen ist leer')
        for i, p in enumerate(pos):
            pp = f'wohnung.positionen[{i}]'
            req(p, 'label', pp, 'str'); req(p, 'quelle', pp, 'str')
            k = req(p, 'kategorie', pp, 'str')
            if k and k not in KAT: F.append(f'{pp}.kategorie "{k}" unbekannt – erlaubt: {", ".join(KAT)}')
            req(p, 'betrag', pp, 'num')
            for key in ('kostenpool', 'schluessel_mein', 'schluessel_total', 'davon_honorar'):
                req(p, key, pp, 'num', nullable=True)
            req(p, 'einheit', pp, 'str', nullable=True)
        h = req(w, 'honorar', 'wohnung', 'obj')
        if h:
            fmt = req(h, 'format', 'wohnung.honorar', 'str')
            if fmt and fmt not in ('separat', 'in_pools'): F.append('wohnung.honorar.format: "separat" oder "in_pools"')
            req(h, 'satz_pct', 'wohnung.honorar', 'num')
            req(h, 'mwst_pct', 'wohnung.honorar', 'num', nullable=True)
            pools = req(h, 'pools', 'wohnung.honorar', 'obj')
            if fmt == 'in_pools' and pools:
                labels = [p.get('label') for p in pos]
                for k in pools:
                    if k not in labels: F.append(f'wohnung.honorar.pools: "{k}" passt zu keinem Positions-label')
        req(w, 'total_gedruckt', 'wohnung', 'num'); req(w, 'akonto', 'wohnung', 'num'); req(w, 'saldo', 'wohnung', 'num')
        if all(num(w.get(k)) for k in ('total_gedruckt', 'akonto', 'saldo')) and abs(r2(w['total_gedruckt'] - w['akonto']) - w['saldo']) > 0.011:
            W.append('wohnung.saldo ≠ total_gedruckt − akonto (Vorzeichen: + Nachzahlung, − Guthaben)')
    for i, e in enumerate(req(d, 'einstellplaetze', '', 'list') or []):
        pp = f'einstellplaetze[{i}]'
        req(e, 'platz', pp, 'str'); req(e, 'quelle', pp, 'str')
        for k in ('kostenpool', 'anteil', 'total', 'akonto', 'saldo'): req(e, k, pp, 'num')
        if all(num(e.get(k)) for k in ('total', 'akonto', 'saldo')) and abs(r2(e['total'] - e['akonto']) - e['saldo']) > 0.011:
            W.append(f'{pp}.saldo ≠ total − akonto')
    t = req(d, 'techem', '', 'obj')
    if t:
        req(t, 'quelle', 'techem', 'str')
        for k in ('energie_kwh', 'hz_einh_total', 'hz_kwh_mein', 'ww_m3_total', 'ww_m3_mein', 'promille_total', 'ww_promille_total'):
            req(t, k, 'techem', 'num')
        for k in ('hz_zaehler', 'ww_zaehler'):
            v = t.get(k)
            if v is not None and not (isinstance(v, list) and len(v) == 2 and all(num(x) for x in v)):
                F.append(f'techem.{k} als [alt, neu]')
    wa = req(d, 'wasser', '', 'obj')
    if wa:
        req(wa, 'kosten_haeuser_8_10_12', 'wasser', 'num'); req(wa, 'warmwasser_pool', 'wasser', 'num'); req(wa, 'quelle', 'wasser', 'str')
        if wa.get('kosten_haeuser_14_16') is None and not num(wa.get('umlage_pct_8_10_12')):
            F.append('wasser: entweder kosten_haeuser_14_16 (aus Kostenzusammenstellung) oder umlage_pct_8_10_12 angeben')
    lg = req(d, 'liegenschaft', '', 'obj', nullable=True)
    if lg:
        for i, r in enumerate(req(lg, 'gruppen', 'liegenschaft', 'list') or []):
            req(r, 'gruppe', f'liegenschaft.gruppen[{i}]', 'str'); req(r, 'betrag', f'liegenschaft.gruppen[{i}]', 'num')
        req(lg, 'gesamttotal', 'liegenschaft', 'num'); req(lg, 'quelle', 'liegenschaft', 'list')
    st = req(d, 'strom', '', 'obj', nullable=True)
    if st:
        for k in ('periode', 'quelle'): req(st, k, 'strom', 'str')
        for k in ('kwh', 'total'): req(st, k, 'strom', 'num')
    req(d, 'notizen', '', 'str', nullable=True)
    return F, W


def ergaenze(d):
    """Leitet fehlende Werte ab, die sich eindeutig berechnen lassen (davon_honorar aus Pools)."""
    h = d['wohnung']['honorar']
    if h['format'] == 'in_pools':
        for p in d['wohnung']['positionen']:
            if p.get('davon_honorar') is None and p['label'] in h['pools'] and p.get('schluessel_mein') and p.get('schluessel_total'):
                p['davon_honorar'] = r2(h['pools'][p['label']] * p['schluessel_mein'] / p['schluessel_total'])
    return d


# ---------------------------------------------------------------- Nachrechnen
def pruefungen(jahre):
    out = []
    def chk(y, what, exp, got, src, tol=TOL_OK):
        dd = r2(got - exp) if exp is not None and got is not None else None
        st = 'ok' if dd is not None and abs(dd) <= tol else ('Rundung' if dd is not None and abs(dd) <= TOL_RUNDUNG else 'ABWEICHUNG')
        out.append(dict(jahr=y, pruefung=what, erwartet=r2(exp) if exp is not None else None, gedruckt=got, diff=dd, status=st, quelle=src))
    for d in jahre:
        y, w = d['jahr'], d['wohnung']; pos = w['positionen']; seiten = '/'.join(w['seiten'])
        for p in pos:
            if p['kostenpool'] and p['schluessel_mein'] and p['schluessel_total'] and p['kategorie'] != 'Verwaltungshonorar':
                chk(y, f"Anteil {p['label']}", p['kostenpool'] * p['schluessel_mein'] / p['schluessel_total'], p['betrag'], p['quelle'])
        total = sum(p['betrag'] for p in pos)
        chk(y, 'Summe Positionen = Total', total, w['total_gedruckt'], seiten)
        chk(y, 'Total − Akonto = Saldo', abs(w['total_gedruckt'] - w['akonto']), abs(w['saldo']), seiten)
        h = w['honorar']
        if h['format'] == 'separat' and h.get('mwst_pct') is not None:
            base = sum(p['betrag'] for p in pos if p['kategorie'] != 'Verwaltungshonorar')
            hon = sum(p['betrag'] for p in pos if p['kategorie'] == 'Verwaltungshonorar')
            chk(y, f"Verwaltungshonorar {h['satz_pct']:g} % + {h['mwst_pct']:g} % MWSt", base * h['satz_pct'] / 100 * (1 + h['mwst_pct'] / 100), hon, w['seiten'][-1])
    for d in jahre:
        lg = d.get('liegenschaft')
        if lg:
            rows = [r for r in lg['gruppen'] if not (r['gruppe'].lower().startswith('heizkosten') and r['betrag'] == 0)]
            chk(d['jahr'], 'Liegenschaft: Summe Gruppen = Gesamttotal', sum(r['betrag'] for r in rows), lg['gesamttotal'], lg['quelle'][-1])
    for d in jahre:
        y, t = d['jahr'], d['techem']
        if t.get('ww_zaehler'):
            chk(y, 'Warmwasserzähler neu − alt = Verbrauch', t['ww_zaehler'][1] - t['ww_zaehler'][0], t.get('ww_m3_mein'), t['quelle'])
        for p in d['wohnung']['positionen']:
            if p['kategorie'] == 'Warmwasser' and t.get('ww_promille_total'):
                chk(y, 'Hesta-WW-Schlüssel = Techem-WW-Promille', t['ww_promille_total'], p['schluessel_mein'], p['quelle'], tol=0.001)
            if p['kategorie'] == 'Heizung' and 'guthaben' not in p['label'].lower() and t.get('promille_total'):
                chk(y, 'Hesta-Heizschlüssel = Techem-Gesamtpromille', t['promille_total'], p['schluessel_mein'], p['quelle'], tol=0.001)
    for i, c in enumerate(out, 1):
        out[i - 1] = dict(nr=i, **c)
    return out


# ---------------------------------------------------------------- Datensätze
def norm_gruppe(g):
    l = g.lower()
    if l.startswith('heizkosten') or 'guthaben' in l: return 'Heizung (alle Häuser)'
    if 'warmwasser' in l: return 'Warmwasser (alle Häuser)'
    if l.startswith('wasser/abwasser ii'): return 'Wasser/Abwasser Häuser 14/16'
    if l.startswith('wasser/abwasser'): return 'Wasser/Abwasser Häuser 8/10/12'
    if 'häuser 8' in l or 'hauser 8' in l: return 'Allg. NK Häuser 8/10/12'
    if '14' in l and 'allgemeine' in l: return 'Allg. NK Häuser 14/16'
    if 'lift' in l: return 'Lifte'
    if 'tv' in l: return 'TV-Gebühren'
    if 'garage' in l: return 'Garage'
    if 'mieterwechsel' in l: return 'Mieterwechsel'
    return g


def ds_wasser(d, S):
    y, w, t, wa = d['jahr'], d['wohnung'], d['techem'], d['wasser']
    A_I, A_II, A_ALL, A_W = S['flaeche_haeuser_8_10_12_m2'], S['flaeche_haeuser_14_16_m2'], S['flaeche_alle_m2'], 100
    pw = [p for p in w['positionen'] if p['kategorie'] == 'Wasser/Abwasser'][0]
    WI = wa['kosten_haeuser_8_10_12']
    WII = wa['kosten_haeuser_14_16'] if wa['kosten_haeuser_14_16'] is not None else round(WI / (wa['umlage_pct_8_10_12'] / 100) - WI, 2)
    WW = wa['warmwasser_pool']; wwm, wwt = t['ww_m3_mein'], t['ww_m3_total']
    tot = WI + WII; share = wwm / wwt; paid = pw['betrag']
    fair_c = share * tot; fair_a = A_W / A_ALL * tot
    z = d.get('zeitanteil')
    fair_a_out = r2(round(fair_a, 2) * z['tage_mieter'] / z['tage_periode']) if z else round(fair_a, 2)
    price = WW / wwt
    return dict(jahr=y, W_I=round(WI, 2), W_II=round(WII, 2), W_total=round(tot, 2), anteil_I_pct=round(100 * WI / tot, 1),
                chf_m2_I=round(WI / A_I, 2), chf_m2_II=round(WII / A_II, 2), WW_pool=WW, ww_m3_total=wwt, ww_m3_mein=wwm,
                ww_anteil_pct=round(100 * share, 3), flaechenanteil_pct=round(100 * A_W / A_ALL, 3),
                verbrauchsfaktor=round(share / (A_W / A_ALL), 3), bezahlt=paid, fair_verbrauch=round(fair_c, 2),
                fair_flaeche_alle=fair_a_out, mehr_vs_verbrauch=round(paid - fair_c, 2), mehr_vs_flaeche=r2(paid - fair_a_out) if z else round(paid - fair_a, 2),
                preis_m3=round(price, 2), kaltwasser_m3_geschaetzt=round(tot / price), quelle=wa['quelle'], bezahlt_quelle=pw['quelle'])


def monate(a, b):
    y, m = map(int, a.split('-')); yb, mb = map(int, b.split('-')); out = []
    while (y, m) <= (yb, mb):
        out.append(f'{y:04d}-{m:02d}'); m += 1
        if m == 13: y, m = y + 1, 1
    return out


def ds_miete(stamm, jahre, miete):
    ak_w, ak_ep = stamm['akonto_monat']['wohnung_nk'], stamm['akonto_monat']['einstellplatz_nk']
    ref = sorted(stamm['referenzzinssatz_bwo'], key=lambda r: r['ab'])
    def refz(mo):
        v = None
        for r in ref:
            if mo >= r['ab'][:7]: v = r['pct']
        return v
    bel = collections.defaultdict(dict)
    for b in miete['belegt']:
        for mo in monate(b['von'], b['bis']): bel[b['objekt']][mo] = (b['brutto'], b['quelle'])
    start = stamm['objekt']['mietbeginn'][:7]
    alle = monate(start, miete['fortschreiben_bis'])
    eps = stamm['einstellplaetze']
    letzte = {}
    # Startwert je Objekt = erster belegter Betrag (für Monate vor dem ersten Beleg)
    for o, mm in bel.items(): letzte[o] = mm[min(mm)][0]
    monat = []
    for mo in alle:
        row = dict(monat=mo)
        if mo in bel['Wohnung']:
            br, q = bel['Wohnung'][mo]; st = 'belegt'; letzte['Wohnung'] = br
        else:
            br, q, st = letzte['Wohnung'], '', 'fortgeschrieben'
        row.update(brutto=br, netto=r2(br - ak_w), status=st, quelle=q)
        for e in eps:
            o = e['platz']; key = o.replace(' ', '').lower()
            aktiv = mo >= e['ab']
            if mo in bel[o]: b, s = bel[o][mo][0], 'belegt'; letzte[o] = b
            else: b, s = letzte.get(o), 'fortgeschrieben'
            row[f'{key}_aktiv'] = aktiv
            row[f'{key}_brutto'] = b if aktiv else None
            row[f'{key}_status'] = s if aktiv else None
        row['referenzzins'] = refz(mo)
        monat.append(row)
    ep_tot = [e['total'] for d in jahre for e in d['einstellplaetze']]
    ep_mittel = statistics.mean(ep_tot) if ep_tot else 0
    wk = []
    for d in jahre:
        y0 = int(d['jahr'][:4]); ms = [m for m in monat if f'{y0}-10' <= m['monat'] <= f'{y0 + 1}-09']
        tot_whg = sum(p['betrag'] for p in d['wohnung']['positionen'])
        r = dict(jahr=d['jahr'], monate=len(ms), monate_belegt=sum(m['status'] == 'belegt' for m in ms),
                 miete_whg_belegt=r2(sum(m['netto'] for m in ms if m['status'] == 'belegt')),
                 miete_whg_fort=r2(sum(m['netto'] for m in ms if m['status'] != 'belegt')),
                 nk_whg=r2(tot_whg), miete_ep_belegt=0.0, miete_ep_fort=0.0,
                 nk_ep_belegt=r2(sum(e['total'] for e in d['einstellplaetze'])), nk_ep_fort=0.0)
        for e in eps:
            key = e['platz'].replace(' ', '').lower()
            for m in ms:
                if not m[f'{key}_aktiv']: continue
                v = r2(m[f'{key}_brutto'] - ak_ep)
                r['miete_ep_belegt' if m[f'{key}_status'] == 'belegt' else 'miete_ep_fort'] += v
            aktiv_im_jahr = any(m[f'{key}_aktiv'] for m in ms)
            if aktiv_im_jahr and not any(x['platz'] == e['platz'] for x in d['einstellplaetze']):
                r['nk_ep_fort'] += ep_mittel
        for k in ('miete_ep_belegt', 'miete_ep_fort', 'nk_ep_fort'): r[k] = r2(r[k])
        r['total'] = r2(sum(r[k] for k in ('miete_whg_belegt', 'miete_whg_fort', 'nk_whg', 'miete_ep_belegt', 'miete_ep_fort', 'nk_ep_belegt', 'nk_ep_fort')))
        r['belegt'] = r2(r['miete_whg_belegt'] + r['nk_whg'] + r['miete_ep_belegt'] + r['nk_ep_belegt'])
        r['anteil_nk'] = round((r['nk_whg'] + r['nk_ep_belegt'] + r['nk_ep_fort']) / r['total'], 4) if r['total'] else None
        wk.append(r)
    return wk, monat


def build(quiet=False):
    stamm, jahre, miete, befunde = lade_alles()
    S = stamm['schluessel']
    jahre = [ergaenze(d) for d in jahre]
    kosten, jr, pos, wasser, techem, lieg = [], [], [], [], [], []
    for d in jahre:
        y, w = d['jahr'], d['wohnung']
        k = collections.OrderedDict((c, 0.0) for c in KAT)
        for p in w['positionen']:
            h = p.get('davon_honorar') or 0
            k[p['kategorie']] += p['betrag'] - h; k['Verwaltungshonorar'] += h
        for c, v in k.items(): kosten.append(dict(jahr=y, kategorie=c, chf=r2(v)))
        eps = d['einstellplaetze']; st = d.get('strom')
        if eps: kosten.append(dict(jahr=y, kategorie='Einstellplätze', chf=r2(sum(e['total'] for e in eps))))
        if st: kosten.append(dict(jahr=y, kategorie='Strom Wohnung', chf=st['total']))
        total = r2(sum(p['betrag'] for p in w['positionen']))
        jr.append(dict(jahr=y, nebenkosten=total, akonto=w['akonto'], saldo=r2(total - w['akonto']),
                       einstellplaetze=r2(sum(e['total'] for e in eps)) if eps else None,
                       strom=st['total'] if st else None, strom_kwh=st['kwh'] if st else None, quelle=', '.join(w['seiten'])))
        for i, p in enumerate(w['positionen'], 1):
            pos.append(dict(id=f'{y}-{i}', jahr=y, position=p['label'], kategorie=p['kategorie'], kostenpool=p['kostenpool'],
                            schluessel=f"{p['schluessel_mein']} / {p['schluessel_total']} {p['einheit']}" if p['schluessel_mein'] is not None else (p['einheit'] or ''),
                            betrag=p['betrag'], davon_honorar=p.get('davon_honorar'), quelle=p['quelle']))
        for e in eps:
            pos.append(dict(id=f"{y}-{e['platz']}", jahr=y, position=f"Einstellplatz {e['platz']} (1/{S['einstellplaetze_total']}, inkl. Honorar)",
                            kategorie='Einstellplätze', kostenpool=e['kostenpool'], schluessel=f"1 / {S['einstellplaetze_total']}",
                            betrag=e['total'], davon_honorar=None, quelle=e['quelle']))
        if st:
            pos.append(dict(id=f'{y}-strom', jahr=y, position=f"Strom {st['periode']}, {st['kwh']} kWh", kategorie='Strom Wohnung',
                            kostenpool=None, schluessel='eigener Zähler', betrag=st['total'], davon_honorar=None, quelle=st['quelle']))
        wasser.append(ds_wasser(d, S))
        t = d['techem']
        techem.append(dict(jahr=y, waerme_kwh=t['hz_kwh_mein'], waerme_objekt=t['hz_einh_total'],
                           waerme_kwh_m2=round(t['hz_kwh_mein'] / 100, 1), waerme_objekt_m2=round(t['hz_einh_total'] / S['flaeche_alle_m2'], 1),
                           ww_m3=t['ww_m3_mein'], ww_m3_objekt=t['ww_m3_total'], ww_m3_pro_100m2_objekt=round(t['ww_m3_total'] / S['flaeche_alle_m2'] * 100, 2),
                           promille=t['promille_total'], fernwaerme_kwh=t['energie_kwh'], quelle=t['quelle']))
        if d.get('liegenschaft'):
            agg = collections.OrderedDict()
            for r in d['liegenschaft']['gruppen']:
                n = norm_gruppe(r['gruppe']); agg[n] = r2(agg.get(n, 0) + r['betrag'])
            lieg += [dict(jahr=y, gruppe=g, chf=v) for g, v in agg.items()]
    wk, monat = ds_miete(stamm, jahre, miete)
    pr = pruefungen(jahre)
    last = jr[-1]; lw = wasser[-1]
    kennz = [dict(letztes_jahr=last['jahr'], nebenkosten=last['nebenkosten'], akonto=last['akonto'], saldo=last['saldo'],
                  einstellplaetze=last['einstellplaetze'], wasser_bezahlt=lw['bezahlt'], wasser_anteil_8_10_12_pct=lw['anteil_I_pct'],
                  wasser_verbrauchsfaktor=lw['verbrauchsfaktor'], nebenkosten_summe=r2(sum(r['nebenkosten'] for r in jr)),
                  pruefungen=len(pr), abweichungen=sum(c['status'] == 'ABWEICHUNG' for c in pr), rundungen=sum(c['status'] == 'Rundung' for c in pr),
                  letzte_nettomiete=[m for m in monat if m['status'] == 'belegt'][-1]['netto'], referenzzins_aktuell=monat[-1]['referenzzins'],
                  gebaut_am=datetime.datetime.now().isoformat(timespec='seconds'))]
    AUSGABE.mkdir(exist_ok=True)
    sets = dict(kosten=kosten, jahre=jr, positionen=pos, wasser=wasser, techem=techem, liegenschaft=lieg, pruefungen=pr,
                befunde=befunde, wohnkosten=wk, miete_monat=monat, kennzahlen=kennz)
    for n, v in sets.items():
        json.dump(v, open(AUSGABE / f'{n}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if not quiet:
        print(f'Gebaut: {len(jahre)} Jahre, {len(pr)} Prüfungen ({kennz[0]["abweichungen"]} Abweichungen, {kennz[0]["rundungen"]} Rundungen) -> {AUSGABE}')
    return sets


# ---------------------------------------------------------------- Vorlage / Import
def vorlage(jahr):
    if not re.fullmatch(r'\d{4}/\d{2}', jahr): sys.exit('Jahr im Format JJJJ/JJ, z. B. 2024/25')
    stamm, jahre, _, _ = lade_alles()
    prev = jahre[-1]; y0 = int(jahr[:4])
    leer = lambda p: dict(label=p['label'], kategorie=p['kategorie'], kostenpool=None, schluessel_mein=None,
                          schluessel_total=p['schluessel_total'], einheit=p['einheit'], betrag=None, davon_honorar=None, quelle='')
    h = prev['wohnung']['honorar']
    d = dict(format=FORMAT, jahr=jahr, periode=dict(von=f'{y0}-10-01', bis=f'{y0 + 1}-09-30'), zeitanteil=None,
             erfasst=dict(am=datetime.date.today().isoformat(), von='', geprueft=False),
             haushalt=dict(personen=prev['haushalt']['personen'], hinweis=None),
             wohnung=dict(seiten=[], positionen=[leer(p) for p in prev['wohnung']['positionen']],
                          honorar=dict(format=h['format'], satz_pct=h['satz_pct'], mwst_pct=h.get('mwst_pct'),
                                       pools={k: None for k in h.get('pools', {})}),
                          total_gedruckt=None, akonto=prev['wohnung']['akonto'], saldo=None),
             einstellplaetze=[dict(platz=e['platz'], kostenpool=None, anteil=None, total=None, akonto=e['akonto'], saldo=None, quelle='')
                              for e in prev['einstellplaetze']],
             techem={k: None for k in prev['techem']} | dict(quelle=''),
             wasser=dict(kosten_haeuser_8_10_12=None, kosten_haeuser_14_16=None, umlage_pct_8_10_12=None, warmwasser_pool=None, quelle=''),
             liegenschaft=None, strom=None, notizen=None)
    VORLAGEN.mkdir(exist_ok=True)
    f = VORLAGEN / f'abrechnung_{jahr_key(jahr)}.json'
    json.dump(d, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'Vorlage geschrieben: {f}\nAlle null-Werte und leeren quelle-Felder ausfüllen, dann: nk.py import {f}')


def bericht(d, alle_pr):
    eig = [c for c in alle_pr if c['jahr'] == d['jahr']]
    print(f"\nPrüfungen {d['jahr']}: {len(eig)} – " + ', '.join(f'{s}: {sum(c["status"] == s for c in eig)}' for s in ('ok', 'Rundung', 'ABWEICHUNG')))
    for c in eig:
        if c['status'] != 'ok': print(f"  {c['status']:10} {c['pruefung']}: erwartet {c['erwartet']}, gedruckt {c['gedruckt']} (Δ {c['diff']}) [{c['quelle']}]")


def importiere(pfad, ersetzen=False, nur_pruefen=False):
    d = json.load(open(pfad, encoding='utf-8'))
    stamm = json.load(open(DATEN / 'stammdaten.json', encoding='utf-8'))
    F, W = validiere(d, stamm)
    for w in W: print('Warnung:', w)
    if F:
        print('Nicht importiert – Fehler:'); [print('  -', f) for f in F]; sys.exit(1)
    d = ergaenze(d)
    ziel = DATEN / 'jahre' / f"{jahr_key(d['jahr'])}.json"
    _, jahre, _, _ = lade_alles()
    test = [x for x in jahre if x['jahr'] != d['jahr']] + [d]; test.sort(key=lambda x: x['jahr'])
    bericht(d, pruefungen(test))
    if nur_pruefen:
        print('\nStruktur ok. Nichts gespeichert (nur prüfen).'); return
    if ziel.exists() and not ersetzen:
        sys.exit(f'\n{ziel.name} existiert schon. Mit --ersetzen überschreiben (alte Fassung wird als .bak gesichert).')
    if ziel.exists(): shutil.copy2(ziel, ziel.with_suffix('.json.bak'))
    json.dump(d, open(ziel, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'\nÜbernommen: {ziel}')
    build()


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a or a[0] in ('-h', '--help', 'hilfe'): print(__doc__)
    elif a[0] == 'build': build()
    elif a[0] == 'vorlage' and len(a) > 1: vorlage(a[1])
    elif a[0] == 'pruefen' and len(a) > 1: importiere(a[1], nur_pruefen=True)
    elif a[0] == 'import' and len(a) > 1: importiere(a[1], ersetzen='--ersetzen' in a)
    else: print(__doc__); sys.exit(2)
