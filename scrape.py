"""Compétitions féminines d'Alsace (départemental + régional Grand Est) -> data/data.json
Local : pip install playwright && playwright install chromium && python scrape.py
DEBUG=1 python scrape.py : sauvegarde le HTML brut dans debug/."""
import json, os, re, datetime, pathlib
from playwright.sync_api import sync_playwright

cfg = json.load(open("config.json", encoding="utf-8"))
DEBUG = os.environ.get("DEBUG")
pathlib.Path("debug").mkdir(exist_ok=True) if DEBUG else None
slug = lambda s: re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]
LIGNE = re.compile(r"(-?\d+)\s+(\d+)\s+(\d+)\s+-\s+(\d+)\s+-\s+(\d+)\s+(\d+)\s+(\d+)\s+(-?\d+)((?:\s+[VNDP?])*)")

def aller(page, url, nom="page"):
    page.goto(url, wait_until="networkidle", timeout=60000); page.wait_for_timeout(1200)
    if DEBUG: pathlib.Path(f"debug/{slug(nom)}.html").write_text(page.content(), encoding="utf-8")

def liens(page):
    return [(a.inner_text().strip(), a.evaluate("e => e.href")) for a in page.query_selector_all("a[href]") if a.inner_text().strip()]

def trouver_poules(page, url, filtre, profondeur=3, vus=None):
    """Suit les pages 'niveaux-' depuis url et renvoie [(nom, url)] des pages /competitions/."""
    vus = vus if vus is not None else set(); out = []
    if url in vus or profondeur < 0: return out
    vus.add(url); aller(page, url, "nav-" + url[-20:])
    for t, h in liens(page):
        if "/football/competitions/" in h and h not in vus: vus.add(h); out.append((t, h))
        elif "/football/niveaux-" in h and h not in vus and "Ancienne saison" not in t \
             and (profondeur == 3 or True) and any(f.lower() in t.lower() for f in filtre + [""] if f or profondeur < 3):
            out += trouver_poules(page, h, filtre, profondeur - 1, vus)
    return out

def classement(texte):
    m = re.search(r"équipes\s+(.*?)\s+pts\s+jo", texte, re.S | re.I)
    if not m: return []
    noms = re.findall(r"^\s*\d+\s*\n\s*(.+?)\s*$", m.group(1), re.M)
    reste = texte[m.end():]
    stats = LIGNE.findall(reste.split("Matchs")[0])
    return [{"rang": i + 1, "equipe": n, "pts": s[0], "j": s[1], "g": s[2], "n": s[3], "p": s[4],
             "bp": s[5], "bc": s[6], "diff": s[7], "forme": s[8].split()} for i, (n, s) in enumerate(zip(noms, stats))]

def lire_poule(page, nom, url):
    aller(page, url, nom); texte = page.inner_text("body")
    matchs = texte.split("Matchs", 1)[1].split("Fonctionnalités")[0].strip() if "Matchs" in texte else ""
    return {"nom": nom, "url": url, "classement": classement(texte), "matchs_texte": matchs}

data = {"mis_a_jour": datetime.datetime.utcnow().isoformat() + "Z", "competitions": []}
with sync_playwright() as p:
    b = p.chromium.launch(); page = b.new_page(locale="fr-FR")
    cibles = []  # (zone, nom, url)
    try:
        for t, h in trouver_poules(page, cfg["alsace"]["page"], cfg["alsace"]["filtre"]):
            if any(f in t for f in cfg["alsace"]["filtre"]): cibles.append(("Départemental", t, h))
    except Exception as e: print("ERREUR alsace", e)
    for t, h in cfg["poules_supplementaires"]: cibles.append(("Régional", t, h))
    alsace_cibles = [c for c in cibles]
    lus = {}
    for zone, t, h in alsace_cibles:
        try: lus[h] = (zone, lire_poule(page, t, h)); print("OK", t)
        except Exception as e: print("ERREUR", t, e)
    clubs = {r["equipe"] for z, c in lus.values() if z == "Départemental" for r in c["classement"]}
    reg = cfg["regional"]
    try:
        aller(page, reg["accueil"], "accueil")
        ligue = next(h for t, h in liens(page) if reg["nom_ligue"].lower() in t.lower() and "/football/ligues-" in h)
        aller(page, ligue, "ligue")
        niveaux = [(t, h) for t, h in liens(page) if "/football/niveaux-" in h and any(f.lower() in t.lower() for f in reg["filtre"])]
        vus = set()
        for tn, hn in niveaux:
            for t, h in trouver_poules(page, hn, reg["filtre"], 2, vus):
                if h in lus: continue
                try:
                    c = lire_poule(page, t, h)
                    if reg["garder_seulement_poules_avec_clubs_alsaciens"] and clubs and \
                       not any(r["equipe"] in clubs for r in c["classement"]): continue
                    lus[h] = ("Régional", c); print("OK régional", t)
                except Exception as e: print("ERREUR", t, e)
    except StopIteration: print("ERREUR : page de la ligue Grand EST introuvable (voir poules_supplementaires)")
    except Exception as e: print("ERREUR régional", e)
    b.close()
for zone, c in lus.values(): data["competitions"].append({"zone": zone, **c})
pathlib.Path("data").mkdir(exist_ok=True)
json.dump(data, open("data/data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
