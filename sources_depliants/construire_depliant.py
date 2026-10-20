#!/usr/bin/env python3
"""Construit un dépliant FO ICO (A4 paysage, 2 pages) à partir d'un fichier de données JSON.

Usage :
    python3 construire_depliant.py donnees/teletravail.json            # écrit sortie/<slug>.html et .pdf
    python3 construire_depliant.py donnees/teletravail.json --verifier # + contrôles automatiques
    python3 construire_depliant.py --tous                              # tous les fichiers de donnees/

Prérequis : Python 3, `pip install playwright` puis `playwright install chromium`
(ou un Chromium déjà installé : variable PLAYWRIGHT_BROWSERS_PATH).
Les polices (Poppins, Carlito) sont dans polices/ : rien à installer sur le poste.

Balisage dans les textes du JSON :
    **gras**           -> gras
    {ref:Art. 7.2}     -> (Art. 7.2) en italique gris 8,5 pt
    ^er^               -> exposant (1^er^ -> 1er)
"""
import argparse, html, json, pathlib, re, subprocess, sys, urllib.parse

RACINE = pathlib.Path(__file__).resolve().parent
MENTION = "Résumé établi par vos élus FO à l'ICO"

ICONE_ENVELOPPE = '<svg viewBox="0 0 9.4 9.4"><rect x="0" y="0.95" width="9.4" height="7.5" rx="0.9"/><path d="M0.4 1.6 L4.7 5.2 L9 1.6"/></svg>'
ICONE_TELEPHONE = ('<svg viewBox="0 0 9.4 9.4"><path d="M2.1 0.5 L3.6 0.5 L4.3 2.7 L3.3 3.5 C3.8 4.7 4.7 5.6 5.9 6.1 L6.7 5.1 L8.9 5.8 '
                   'L8.9 7.3 C8.9 8.1 8.3 8.7 7.5 8.7 C3.9 8.5 0.9 5.5 0.7 1.9 C0.7 1.1 1.3 0.5 2.1 0.5 Z"/></svg>')


def inline(s):
    """Texte du JSON -> HTML : échappement, gras, références d'articles, exposants, espace insécable avant ? ! ;"""
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\{ref:([^}]+)\}", r'<i class="art">(\1)</i>', s)
    s = re.sub(r"\^([^^]+)\^", r"<sup>\1</sup>", s)
    s = re.sub(r" ([?!;])", " \\1", s)
    return s


def picto(bloc, contexte, k=None):
    """Pictogramme (SVG du dossier pictos/) + légende. Réglages optionnels, en points :
    avant (espace au-dessus), ecart (espace entre le picto et sa légende), apres (espace en dessous),
    decalage_x (décalage horizontal), echelle (agrandissement)."""
    if bloc.get("svg"):
        chemin = RACINE / "pictos" / bloc["svg"]
        w, h = svg_dim(chemin)
        e = bloc.get("echelle", 1)
    # SVG en ligne (et non <img>) : les polices du gabarit s'appliquent aux textes du pictogramme
    img = "" if not bloc.get("svg") else re.sub(r'width="[\d.]+pt" height="[\d.]+pt"', f'width="{w * e:.2f}pt" height="{h * e:.2f}pt"', chemin.read_text(encoding="utf-8"), count=1)
    st = []
    if "avant" in bloc:
        st.append(f'margin-top:{bloc["avant"]}pt')
    if "apres" in bloc:
        st.append(f'margin-bottom:{bloc["apres"]}pt')
    if "decalage_x" in bloc and img:  # seul le dessin se décale : la légende reste centrée sur la colonne
        img = f'<div style="position:relative;left:{bloc["decalage_x"]}pt">{img}</div>'
    style = f' style="{";".join(st)}"' if st else ""
    lst = f' style="margin-top:{bloc["ecart"]}pt"' if "ecart" in bloc else ""
    kl = f' data-k="{k}L"' if k else ""
    leg = f'<div class="leg"{lst}{kl}>{inline(bloc["legende"])}</div>' if bloc.get("legende") else ""
    ka = f' data-k="{k}"' if k else ""
    return f'<div class="picto {contexte}"{style}{ka}>{img}{leg}</div>'


def svg_dim(chemin):
    m = re.search(r'width="([\d.]+)pt" height="([\d.]+)pt"', chemin.read_text(encoding="utf-8"))
    return float(m.group(1)), float(m.group(2))


def puces(items, numerote=False):
    li = []
    for i, it in enumerate(items, 1):
        pre = f"<b>{i}</b>  " if numerote else ""
        li.append(f"<li>{pre}{inline(it)}</li>")
    return '<ul class="puces">' + "".join(li) + "</ul>"


def marge(b):
    """Style de marge optionnel d'un bloc : avant / apres, en points."""
    st = []
    if "avant" in b:
        st.append(f'margin-top:{b["avant"]}pt')
    if "apres" in b:
        st.append(f'margin-bottom:{b["apres"]}pt')
    return f' style="{";".join(st)}"' if st else ""


def blocs(liste, contexte, pre=None):
    """Blocs d'une colonne. `pre` : préfixe des repères data-k (utilisés pour caler les marges, voir importer_depliant.py)."""
    out = []
    for i, b in enumerate(liste):
        t = b["t"]
        ka = f' data-k="{pre}{i}"' if pre is not None else ""
        if t == "section":
            out.append(f'<div class="sec"{marge(b)}{ka}>{inline(b["titre"])}</div>')
        elif t == "p":
            st = marge(b)
            if "taille" in b:  # paragraphe en corps réduit : {"taille": 10.5}
                extra = f"font-size:{b['taille']}pt;line-height:1.215"
                st = f' style="{extra}"' if not st else st[:-1] + ";" + extra + '"'
            out.append(f'<p{st}{ka}>{inline(b["texte"])}</p>')
        elif t == "puces":
            st = marge(b)
            if "taille" in b:  # puces en corps différent du défaut de l'encadré : {"taille": 11.5}
                extra = f"font-size:{b['taille']}pt;line-height:1.24;--pm:5.95pt"
                st = f' style="{extra}"' if not st else st[:-1] + ";" + extra + '"'
            out.append(puces(b["items"], b.get("numerote", False)).replace('<ul class="puces">', f'<ul class="puces"{st}{ka}>', 1))
        elif t == "encadre":
            cl = b.get("style", "neutre") if b.get("style") in ("alerte", "marine") else "neutre"
            if b.get("titre_grand"):
                cl += " grand"
            titre = f'<div class="box-titre">{inline(b["titre"])}</div>' if b.get("titre") else ""
            out.append(f'<div class="box {cl}"{marge(b)}{ka}>{titre}{blocs(b["contenu"], contexte)}</div>')
        elif t == "note":
            out.append(f'<p class="note"{marge(b)}{ka}>{inline(b["texte"])}</p>')
        elif t == "picto":
            out.append(picto(b, contexte, f"{pre}{i}" if pre is not None else None))
        elif t == "tableau":
            tete = "".join(f"<th>{inline(c)}</th>" for c in b["entetes"])
            corps = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in l) + "</tr>" for l in b["lignes"])
            out.append(f'<table class="tab"{marge(b)}{ka}><tr>{tete}</tr>{corps}</table>')
        else:
            raise ValueError(f"type de bloc inconnu : {t}")
    return "".join(out)


BASE_PDF = "https://github.com/focrgico/fo-ico-documents/raw/main/docs/"


def url_pdf(lien):
    """Adresse web d'un PDF signé : soit une URL complète (« url »), soit le chemin du PDF dans docs/ (« pdf »),
    tel qu'il figure dans catalogue/catalogue.json (champ chemin_pdf)."""
    if "url" in lien:
        return lien["url"]
    return BASE_PDF + urllib.parse.quote(lien["pdf"])


def construire_html(d):
    rec = d["recto"]
    c = rec["contact"]
    src = rec["source"]
    a_liens = [f'<a href="{html.escape(url_pdf(l))}">{inline(l["texte"])}</a>' for l in src["liens"]]
    seps = src.get("liens_sep") or [" ; "] * (len(a_liens) - 1)
    liens = a_liens[0] if a_liens else ""
    for sep, a in zip(seps, a_liens[1:]):
        liens += html.escape(sep) + a
    chiffre = ""
    chiffres = d.get("chiffres") or ([d["chiffre"]] if d.get("chiffre") else [])
    for n, ch in enumerate(chiffres):
        cl = "unite rouge" if ch.get("unite_rouge") else "unite"
        sep = '<div class="chiffre-sep"></div>' if n else ""
        aj = f' style="margin-top:calc({12.1 if n else 18.4}pt + {ch["ajust"]}pt)"' if ch.get("ajust") else ""
        chiffre += (f'{sep}<div class="chiffre" data-k="cv{n}"{aj}><span class="num">{inline(ch["valeur"])}</span>'
                    f'<span class="{cl}">{inline(ch["unite"])}</span></div>'
                    f'<div class="chiffre-libelle">{inline(ch["libelle"])}</div>')
    pastilles = "".join(f'<span class="pastille">{inline(p)}</span>' for p in d.get("pastilles", []))
    titre = "<br>".join(inline(l) for l in d["titre"])
    sous = "<br>".join(inline(l) for l in d["sous_titre"].split("\n"))
    ctc = (f'<div class="contact">{ICONE_ENVELOPPE}{html.escape(c["courriel"])}</div>'
           f'<div class="contact" data-k="r2_c">{ICONE_TELEPHONE}{html.escape(c["poste"])}</div>')
    marine = list(rec.get("marine", []))
    if c.get("picto"):  # ancien format : picto du volet marine rangé dans « contact »
        marine.insert(0, dict(c["picto"], t="picto"))
    pic_marine = blocs(marine, "marine", "r2_")
    v = d["verso"]
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>{html.escape(d.get("titre_pdf", " ".join(d["titre"])))}</title>
<link rel="stylesheet" href="{(RACINE / 'depliant.css').as_uri()}"></head><body>
<section class="page recto">
  <div class="volet r1">{blocs(rec["rabat"], "rabat", "r1_")}</div>
  <div class="volet r2">
    <div class="sec">Vos élus FO à l'ICO</div>
    <p class="accroche">{inline(c["accroche"])}</p>
    {ctc}
    {pic_marine}
    <div class="source"><div class="titre">Source</div>
      <p>{inline(src["texte"])}</p>
      <p class="renvoi">{inline(src["renvoi"])} {liens}.</p></div>
  </div>
  <div class="volet r3">
    <img class="logo" src="{(RACINE / 'assets' / 'logo.png').as_uri()}" alt="Logo FO ICO">
    <div class="eyebrow">{inline(d.get("surtitre", ""))}</div>
    <div class="titre">{titre}</div>
    <div class="filet"></div>
    <div class="sous-titre">{sous}</div>
    {chiffre}
    <div class="pastilles">{pastilles}</div>
    <div class="slogan">FO, <span>vos droits notre priorité</span></div>
  </div>
</section>
<section class="page verso">
  <div class="volet v1">{blocs(v[0], "verso", "v1_")}</div>
  <div class="volet v2">{blocs(v[1], "verso", "v2_")}</div>
  <div class="volet v3">{blocs(v[2], "verso", "v3_")}</div>
</section>
</body></html>"""


def rendre_pdf(chemin_html, chemin_pdf, mesures=None):
    """Rend le PDF avec Chromium. Si `mesures` est un dict, y range la position (haut, bas en pt, depuis le haut de
    sa page) de chaque élément portant un repère data-k."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        nav = p.chromium.launch()
        page = nav.new_page()
        page.goto(chemin_html.as_uri())
        page.evaluate("document.fonts.ready")
        if mesures is not None:
            res = page.evaluate("""() => [...document.querySelectorAll('[data-k]')].map(e => {
                const r = e.getBoundingClientRect(), pg = e.closest('.page').getBoundingClientRect();
                return [e.dataset.k, (r.top - pg.top) * 0.75, (r.bottom - pg.top) * 0.75, (r.left - pg.left) * 0.75, r.width * 0.75]; })""")
            for k, hau, bas, gau, lar in res:
                mesures[k] = (hau, bas, gau, lar)
        page.pdf(path=str(chemin_pdf), prefer_css_page_size=True, print_background=True)
        nav.close()


def verifier(chemin_pdf):
    """Contrôles automatiques. Retourne la liste des problèmes (vide = tout est bon)."""
    import pymupdf
    pb = []
    d = pymupdf.open(str(chemin_pdf))
    if len(d) != 2:
        pb.append(f"{len(d)} pages au lieu de 2")
    texte = " ".join(p.get_text() for p in d)
    if MENTION not in re.sub(r"\s+", " ", texte):
        pb.append("mention « Résumé établi par vos élus FO à l'ICO » absente")
    for p in d:
        for l in p.get_links():
            if l["kind"] != pymupdf.LINK_URI or not str(l.get("uri", "")).startswith("http"):
                pb.append(f"lien qui n'est pas une adresse web : {l}")
        for b in p.get_text("dict")["blocks"]:
            for lg in b.get("lines", []):
                for s in lg["spans"]:
                    if s["bbox"][2] > p.rect.width + 0.5 or s["bbox"][3] > p.rect.height + 0.5:
                        pb.append(f"texte hors page : {s['text'][:30]}")
    polices = subprocess.run(["pdffonts", str(chemin_pdf)], capture_output=True, text=True).stdout
    for f in ("Poppins-Bold", "Poppins-Medium", "Carlito"):
        if f not in polices:
            pb.append(f"police absente du PDF : {f}")
    return pb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("donnees", nargs="?")
    ap.add_argument("--tous", action="store_true")
    ap.add_argument("--verifier", action="store_true")
    ap.add_argument("--sortie", default=str(RACINE / "sortie"))
    a = ap.parse_args()
    fichiers = sorted((RACINE / "donnees").glob("*.json")) if a.tous else [pathlib.Path(a.donnees)]
    sortie = pathlib.Path(a.sortie)
    sortie.mkdir(exist_ok=True)
    code = 0
    for f in fichiers:
        d = json.loads(f.read_text(encoding="utf-8"))
        h = sortie / (d["slug"] + ".html")
        pdf = sortie / (d["slug"] + ".pdf")
        h.write_text(construire_html(d), encoding="utf-8")
        rendre_pdf(h, pdf)
        print("écrit", pdf)
        if a.verifier:
            pb = verifier(pdf)
            print("  contrôles :", "OK" if not pb else "")
            for x in pb:
                print("   -", x)
            code = code or (1 if pb else 0)
    sys.exit(code)


if __name__ == "__main__":
    main()
