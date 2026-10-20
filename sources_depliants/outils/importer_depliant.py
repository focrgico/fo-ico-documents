#!/usr/bin/env python3
"""Importe un dépliant publié (PDF) dans le gabarit : écrit donnees/<slug>.json et les pictos, puis cale les
espacements pour que le rendu reprenne les positions du PDF d'origine.

Usage :
    python3 outils/importer_depliant.py chemin/Depliant_xxx_FO.pdf            # un dépliant
    python3 outils/importer_depliant.py dossier_des_PDF/ --sauf teletravail interessement

Les liens « accord complet (PDF) » du PDF d'origine doivent être des adresses du dépôt (BASE_PDF) : le chemin du
PDF signé est relevé dans l'adresse. Un rapport est imprimé : tout ce qui n'a pas pu être lu proprement y figure.
Il ne remplace pas la relecture des deux PDF côte à côte.
"""
import argparse, json, pathlib, re, statistics, sys, urllib.parse
import pymupdf as fitz

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "outils"))
import construire_depliant as C            # noqa: E402
from extraire_picto_depuis_pdf import exporter  # noqa: E402

RECTO = [(0, 277.5), (277.5, 559.5), (559.5, 900)]
VERSO = [(0, 280.5), (280.5, 561), (561, 900)]
LEFT = [34.0, 34.5, 34.5]          # début du texte dans chaque colonne (relatif au bord du volet)
PUCE_DX = 11.3
rapport = []


def hexc(c):
    return "%02x%02x%02x" % tuple(int(round(v * 255)) for v in c) if c is not None else None


def col_de(x, cols):
    for i, (a, b) in enumerate(cols):
        if a - 1 <= x < b:
            return i
    return len(cols) - 1


def norm(s):
    return re.sub(r"\s+", "", s).lower()


# ---------------------------------------------------------------- lecture des lignes
def lire_lignes(page):
    out = []
    for b in page.get_text("dict")["blocks"]:
        if b["type"] != 0:
            continue
        for l in b["lines"]:
            sp = [s for s in l["spans"] if s["text"] != ""]
            if not sp:
                continue
            out.append({"x0": min(s["bbox"][0] for s in sp), "y0": min(s["bbox"][1] for s in sp),
                        "y1": max(s["bbox"][3] for s in sp), "bl": sp[0]["origin"][1], "spans": sp,
                        "size": max(s["size"] for s in sp if not est_ref(s)) if any(not est_ref(s) for s in sp) else sp[0]["size"]})
    out.sort(key=lambda l: (round(l["bl"], 0), l["x0"]))
    return out


def est_ref(s):
    if "Italic" not in s["font"]:
        return False
    c = hexc_int(s["color"])
    if c == "8a93a3":
        return 4.0 < s["size"] < 8.9
    # volet bleu : références en 8fa0ba (les légendes, 7,5 à 8,2 pt, restent des légendes)
    return c == "8fa0ba" and (4.0 < s["size"] < 7.2 or 8.3 < s["size"] < 8.9)


def hexc_int(c):
    return "%06x" % c


def est_legende(s):
    return "Italic" in s["font"] and 7.5 <= s["size"] <= 8.2 and hexc_int(s["color"]) in ("5b6578", "8fa0ba")


def est_gras(s):
    return "Bold" in s["font"] and "Poppins" not in s["font"]


# ---------------------------------------------------------------- texte balisé
def balise(lignes, taille_base):
    """Lignes (avec spans) -> texte au balisage du gabarit (**gras**, {ref:...}, ^exp^)."""
    jetons = []
    for i, l in enumerate(lignes):
        for s in l["spans"]:
            t = s["text"]
            if est_ref(s):
                k = "ref"
                if s["size"] < 7.2:
                    t = "^" + t + "^"
            elif "Italic" not in s["font"] and t.strip() and (s["size"] < taille_base * 0.75 or (
                    t.strip() in ("er", "e", "ère", "re", "ème", "nd", "nde") and s["size"] < taille_base - 0.5)):
                k = "sup"
            elif est_gras(s):
                k = "b"
            else:
                k = "n"
            jetons.append([k, t])
        jetons.append(["j", ""])
    # jonctions de ligne : espace, sauf après un trait d'union
    res = []
    for k, t in jetons:
        if k == "j":
            prev = "".join(x[1] for x in res[-3:])
            res.append(["j", "" if prev.rstrip(" ").endswith("-") and not prev.endswith(" ") else " "])
        else:
            res.append([k, t])
    while res and res[-1][0] == "j":
        res.pop()
    # fusion des jetons de même nature séparés seulement par une jonction de ligne
    fus = []
    for k, t in res:
        if k == "j":
            fus.append([k, t])
            continue
        if fus and fus[-1][0] == "j" and len(fus) >= 2 and fus[-2][0] == k and k in ("b", "ref", "sup"):
            j = fus.pop()
            fus[-1][1] += j[1] + t
        else:
            fus.append([k, t])
    out = ""
    for k, t in fus:
        if k == "j":
            out += t
        elif k == "n":
            out += t
        elif k == "sup":
            out += "^" + t + "^"
        elif k == "ref":
            inner = t.strip()
            if inner.startswith("(") and inner.endswith(")"):
                inner = inner[1:-1]
            else:
                rapport.append(f"référence non parenthésée : {t!r}")
            out += "{ref:" + inner + "}"
        else:
            g = t.strip(" ")
            deb = t[:len(t) - len(t.lstrip(" "))]
            fin = t[len(t.rstrip(" ")):]
            out += deb + ("**" + g + "**" if g else "") + fin
    out = re.sub(r"\*\*(\s*)\*\*", r"\1", out)
    out = re.sub(r" {2,}", " ", out).strip()
    return out


# ---------------------------------------------------------------- formes
def dessins(page):
    return [d for d in page.get_drawings() if not (d["rect"].height >= 560 or (d["rect"].width >= 270 and d["rect"].height >= 480))]


def est_barre_section(d):
    r = d["rect"]
    return d.get("fill") and hexc(d["fill"]) in ("c1121f", "ff0000") and d.get("color") is None and 2.8 < r.width < 3.2 and 16 < r.height < 17.6


def trouver_boites(dr):
    bo = []
    for d in dr:
        r = d["rect"]
        f = hexc(d.get("fill")) if d.get("fill") else None
        if f in ("fff6f6", "ffffff") and d.get("color") is None and 150 <= r.width <= 262 and r.height >= 18:
            barres = [e for e in dr if e.get("fill") and hexc(e["fill"]) in ("c1121f", "14203a") and abs(e["rect"].x0 - r.x0) < 0.7
                      and 1.9 < e["rect"].width < 2.6 and abs(e["rect"].y0 - r.y0) < 0.7 and abs(e["rect"].y1 - r.y1) < 0.7]
            if barres:
                bo.append({"rect": r, "style": "alerte" if f == "fff6f6" else "neutre", "barre": hexc(barres[0]["fill"])})
    return bo


def dans(r, b, m=0.9):
    return r.x0 >= b.x0 - m and r.x1 <= b.x1 + m and r.y0 >= b.y0 - m and r.y1 <= b.y1 + m


def grouper_pictos(dr, boites, ecart=14):
    reste = [d for d in dr if not est_barre_section(d) and not any(dans(d["rect"], b["rect"]) for b in boites)]
    reste.sort(key=lambda d: d["rect"].y0)
    groupes = []
    for d in reste:
        r = d["rect"]
        if groupes and r.y0 <= groupes[-1]["bbox"].y1 + ecart:
            groupes[-1]["bbox"] |= r
            groupes[-1]["n"] += 1
        else:
            groupes.append({"bbox": fitz.Rect(r), "n": 1})
    return groupes


# ---------------------------------------------------------------- blocs d'une colonne
def construire_blocs(lignes, page, rect_bornes, gauche, dans_boite=False, defaut_puces=11.5):
    """Lignes (déjà filtrées) d'une zone -> liste de blocs section / p / puces. rect_bornes sert à retrouver les repères."""
    marqueurs = [l for l in lignes if len(l["spans"]) == 1 and l["spans"][0]["text"].strip() == "●"]
    texte = [l for l in lignes if l not in marqueurs]
    debut_puce = set()
    for m in marqueurs:
        cands = [i for i, l in enumerate(texte) if -3.8 < l["y0"] - m["y0"] + 1.8 - 1.8 < 1.5 and l["x0"] > m["x0"] + 6]
        cands = [i for i, l in enumerate(texte) if abs(l["y0"] - (m["y0"] - 1.8)) < 2.6 and l["x0"] > m["x0"] + 6]
        if cands:
            debut_puce.add(min(cands, key=lambda i: abs(texte[i]["y0"] - (m["y0"] - 1.8))))
        else:
            rapport.append(f"puce sans texte à y={m['y0']:.0f}")
    blocs, cur = [], None
    texte.sort(key=lambda l: (l["bl"], l["x0"]))
    for i, l in enumerate(texte):
        s0 = l["spans"][0]
        if "Poppins" in s0["font"] and s0["size"] >= 14:
            if cur and cur["t"] == "section" and l["y0"] - cur["_y1"] < 12:
                cur["_l"].append(l); cur["_y1"] = l["y1"]
            else:
                cur = {"t": "section", "_l": [l], "_y1": l["y1"], "_ref": l}
                blocs.append(cur)
            continue
        if i in debut_puce:
            if cur and cur["t"] == "puces":
                cur["_items"].append([l])
            else:
                cur = {"t": "puces", "_items": [[l]], "_ref": l}
                blocs.append(cur)
            cur["_y1"] = l["y1"]
            continue
        if cur and cur["t"] == "puces" and l["x0"] > gauche + 4 and l["bl"] - cur["_items"][-1][-1]["bl"] < 20:
            cur["_items"][-1].append(l); cur["_y1"] = l["y1"]
            continue
        pitch = l["size"] * 1.24
        txt_l = "".join(x["text"] for x in l["spans"]).strip()
        est_note = all(est_ref(x) for x in l["spans"]) and len(txt_l) >= 28 and not txt_l.startswith("(")
        if cur and cur["t"] == "note" and 0 < l["bl"] - cur["_l"][-1]["bl"] <= pitch * 1.15 and all(est_ref(x) for x in l["spans"]):
            cur["_l"].append(l); cur["_y1"] = l["y1"]
            continue
        if est_note:
            cur = {"t": "note", "_l": [l], "_y1": l["y1"], "_ref": l}
            blocs.append(cur)
            continue
        if cur and cur["t"] == "p" and abs(l["x0"] - cur["_l"][0]["x0"]) < 4 and 0 < l["bl"] - cur["_l"][-1]["bl"] <= pitch * 1.15 \
                and abs(l["size"] - cur["_l"][0]["size"]) < 0.8:
            cur["_l"].append(l); cur["_y1"] = l["y1"]
            continue
        cur = {"t": "p", "_l": [l], "_y1": l["y1"], "_ref": l}
        blocs.append(cur)
    res = []
    for b in blocs:
        if b["t"] == "section":
            txt = balise(b["_l"], 14.5)
            res.append({"t": "section", "titre": txt, "_ref": b["_ref"]})
        elif b["t"] == "note":
            txt = balise([dict(l, spans=[dict(x, font=x["font"].replace("Italic", "Regular")) for x in l["spans"]]) for l in b["_l"]], 8.5)
            txt = re.sub(r"^\{ref:(.*)\}$", r"\1", txt, flags=re.S)
            res.append({"t": "note", "texte": txt, "_ref": b["_ref"]})
        elif b["t"] == "p":
            sz = round(statistics.mode([round(s["size"] * 2) / 2 for l in b["_l"] for s in l["spans"] if not est_ref(s)] or [11.5]), 1)
            txt = balise(b["_l"], sz)
            d = {"t": "p", "texte": txt, "_ref": b["_ref"]}
            defaut = 10.5 if dans_boite else 11.5
            if abs(sz - defaut) > 0.3:
                d["taille"] = sz
            res.append(d)
        else:
            items, num = [], []
            for it in b["_items"]:
                sp0 = it[0]["spans"]
                est_num = len(sp0) >= 2 and est_gras(sp0[0]) and re.fullmatch(r"\d+", sp0[0]["text"]) and sp0[1]["text"].startswith(("  ", "  "))
                num.append(bool(est_num))
                if est_num:
                    it = [dict(it[0], spans=[dict(sp0[1], text=sp0[1]["text"].lstrip("  "))] + sp0[2:])] + it[1:]
                items.append(balise(it, 11.5))
            d = {"t": "puces", "items": items, "_ref": b["_ref"]}
            tailles = [round(x["size"] * 2) / 2 for it in b["_items"] for l in it for x in l["spans"] if not est_ref(x) and x["text"].strip() not in ("●",) and x["size"] > 9]
            if tailles:
                sz = statistics.mode(tailles)
                if abs(sz - defaut_puces) > 0.3:
                    d["taille"] = sz
            if all(num) and num:
                d["numerote"] = True
            elif any(num):
                rapport.append("liste partiellement numérotée")
            res.append(d)
    return res


def lignes_de_colonne(lignes, a, b):
    return [l for l in lignes if a - 1 <= l["x0"] < b]


def sous_blocs_boite(lignes_boite, rect, style, page):
    titre_l = [l for l in lignes_boite if "Poppins" in l["spans"][0]["font"]]
    corps = [l for l in lignes_boite if l not in titre_l]
    titre = balise(titre_l, 11.5) if titre_l else ""
    sz_titre = titre_l[0]["spans"][0]["size"] if titre_l else 0
    bl = construire_blocs(corps, page, rect, rect.x0 + 11.55, dans_boite=True, defaut_puces=10.5 if style == "neutre" else 11.5)
    d = {"t": "encadre", "style": style, "titre": titre, "contenu": bl, "_rect": rect}
    if style == "neutre" and sz_titre > 12:
        d["titre_grand"] = True
    if style == "alerte" and 0 < sz_titre < 12:
        rapport.append(f"titre d'encadré alerte en {sz_titre:.1f} pt (gabarit : 12,5)")
    return d


def colonne_generique(page, lignes, dr, cols, ci, pictos_dir, slug, compteur):
    """Retourne la liste des blocs de la colonne `ci`, dans l'ordre vertical."""
    a, b = cols[ci]
    gauche = a + LEFT[ci]
    lc = lignes_de_colonne(lignes, a, b)
    dc = [d for d in dr if a - 1 <= d["rect"].x0 < b]
    boites = trouver_boites(dc)
    gr = grouper_pictos(dc, boites)
    blocs = []
    util = []
    # petits libellés sous un picto (corps < 7,6 pt, hors légende) : ils font partie du picto
    for g in gr:
        for _ in range(2):
            bb = g["bbox"]
            for l in lc:
                if l["size"] > 9.2 or any(est_legende(s) for s in l["spans"]) or all(est_ref(s) for s in l["spans"]):
                    continue
                if any(bo["rect"].contains(fitz.Rect(l["x0"], l["y0"], l["x0"] + 1, l["y1"])) for bo in boites):
                    continue
                if bb.y0 - 14 <= l["y0"] and l["y1"] <= bb.y1 + 18 and bb.x0 - 30 <= l["x0"] <= bb.x1 + 30:
                    g["bbox"] |= fitz.Rect(l["x0"], l["y0"], max(s["bbox"][2] for s in l["spans"]), l["y1"])
    # pictos et leurs textes internes
    for g in gr:
        bb = g["bbox"]
        zone = fitz.Rect(bb.x0 - 1.5, bb.y0 - 1.5, bb.x1 + 1.5, bb.y1 + 1.5)
        txts = [l for l in lc if zone.contains(fitz.Rect(l["x0"], l["y0"], l["x0"] + 1, l["y1"])) and not any(est_legende(s) for s in l["spans"])]
        g["txts"] = txts
        g["lignes_internes"] = {id(l) for l in txts}
        if g["n"] == 1 and bb.height < 4 and bb.width < 4:
            rapport.append(f"point isolé ignoré à y={bb.y0:.0f}")
    gr = [g for g in gr if not (g["n"] == 1 and g["bbox"].height < 4 and g["bbox"].width < 4)]
    interne = set().union(*[g["lignes_internes"] for g in gr]) if gr else set()
    # légendes
    legendes = [l for l in lc if all(est_legende(s) for s in l["spans"])]
    # boîtes
    dans_boite = set()
    for bo in boites:
        r = bo["rect"]
        lb = [l for l in lc if r.x0 <= l["x0"] <= r.x1 and r.y0 - 0.5 <= l["y0"] and l["y1"] <= r.y1 + 0.5 and id(l) not in interne]
        for l in lb:
            dans_boite.add(id(l))
        blocs.append(("y", r.y0, sous_blocs_boite(lb, r, bo["style"], page)))
    # légendes : lignes italiques de 8 pt regroupées par proximité verticale
    groupes_leg = []
    for l in sorted(legendes, key=lambda l: l["bl"]):
        if groupes_leg and l["bl"] - groupes_leg[-1][-1]["bl"] < 14:
            groupes_leg[-1].append(l)
        else:
            groupes_leg.append([l])
    pris = set()
    for g in gr:
        bb = g["bbox"]
        compteur[0] += 1
        nom = f"{slug}_{compteur[0]}.svg"
        exporter(str(page.parent.name), page.number, (bb.x0 - 0.25, bb.y0 - 0.25, bb.x1 + 0.25, bb.y1 + 0.25), str(pictos_dir / nom))
        d = {"t": "picto", "svg": nom, "_bbox": bb, "_cx": bb.x0 + bb.width / 2}
        cands = [lg for lg in groupes_leg if id(lg[0]) not in pris and 0 <= lg[0]["y0"] - bb.y1 < 60 and a <= lg[0]["x0"] < b
                 and not any(h is not g and bb.y1 < h["bbox"].y0 < lg[0]["y0"] for h in gr)]
        if cands:
            lg = min(cands, key=lambda lg: lg[0]["y0"])
            pris.add(id(lg[0]))
            d["legende"] = balise(lg, 8)
            d["_leg"] = lg[0]
            for l in lg:
                pris.add(id(l))
        blocs.append(("y", bb.y0, d))
    for lg in groupes_leg:
        if id(lg[0]) in pris:
            continue
        blocs.append(("y", lg[0]["y0"], {"t": "picto", "legende": balise(lg, 8), "_leg": lg[0], "_bbox": None, "_cx": None}))
        for l in lg:
            pris.add(id(l))
    rest = [l for l in lc if id(l) not in interne and id(l) not in dans_boite and id(l) not in pris]
    for bl in construire_blocs(rest, page, None, gauche):
        blocs.append(("y", bl["_ref"]["y0"], bl))
    blocs.sort(key=lambda t: t[1])
    return [x[2] for x in blocs]


# ---------------------------------------------------------------- colonnes particulières
def eyebrow(ligne):
    font = fitz.Font(fontfile=str(RACINE / "polices" / "Poppins-Bold.ttf"))
    chars = []
    for s in ligne["_raw"]:
        for c in s["chars"]:
            if c["c"] != " ":
                chars.append((c["c"], c["origin"][0], s["size"]))
    if not chars:
        return ""
    res = [chars[0][0]]
    steps = [(chars[i + 1][1] - chars[i][1]) - font.glyph_advance(ord(chars[i][0])) * chars[i][2] for i in range(len(chars) - 1)]
    ls = statistics.median(steps)
    for i, st in enumerate(steps):
        if st > ls + 1.2:
            res.append(" ")
        res.append(chars[i + 1][0])
    return "".join(res)


def lire_page_raw(page):
    res = []
    for b in page.get_text("rawdict")["blocks"]:
        if b["type"] != 0:
            continue
        for l in b["lines"]:
            res.append(l)
    return res


def couverture(page, lignes, dr, rapport_nom):
    a, b = RECTO[2]
    lc = lignes_de_colonne(lignes, a, b)
    raws = lire_page_raw(page)
    out = {"surtitre": ""}
    ey = [l for l in lc if "Poppins" in l["spans"][0]["font"] and 6.5 < l["spans"][0]["size"] < 7.5 and hexc_int(l["spans"][0]["color"]) == "b08d57"]
    if ey:
        raw = [r for r in raws if abs(r["bbox"][1] - ey[0]["y0"]) < 0.5 and abs(r["bbox"][0] - ey[0]["x0"]) < 0.5]
        ey[0]["_raw"] = raw[0]["spans"] if raw else []
        out["surtitre"] = eyebrow(ey[0])
    titres = [l for l in lc if "Poppins" in l["spans"][0]["font"] and 22 < l["spans"][0]["size"] < 24]
    out["titre"] = [balise([l], 23) for l in titres]
    st = [l for l in lc if l["spans"][0]["font"].startswith("Carlito") and abs(l["spans"][0]["size"] - 10.5) < 0.2 and hexc_int(l["spans"][0]["color"]) == "5b6578"]
    out["sous_titre"] = "\n".join(balise([l], 10.5) for l in st)
    gros = sorted([s for l in lc for s in l["spans"] if "Poppins" in s["font"] and 31 < s["size"] < 33], key=lambda s: s["origin"][1])
    chiffres = []
    for n, g in enumerate(gros):
        haut_suivant = gros[n + 1]["bbox"][1] if n + 1 < len(gros) else 1e9
        unite = [s for l in lc for s in l["spans"] if "Poppins" in s["font"] and abs(s["size"] - 12) < 0.3 and abs(s["origin"][1] - g["origin"][1]) < 2]
        ut = "".join(s["text"] for s in unite).strip()
        lib = [l for l in lc if l["spans"][0]["font"].startswith("Carlito") and abs(l["spans"][0]["size"] - 9.5) < 0.2
               and hexc_int(l["spans"][0]["color"]) == "5b6578" and g["bbox"][3] - 4 < l["y0"] < haut_suivant]
        chiffres.append({"_ref": g, "valeur": g["text"].strip(), "unite": ut, "unite_rouge": bool(unite) and hexc_int(unite[-1]["color"]) == "c1121f",
                         "libelle": balise(lib, 9.5)})
    if chiffres:
        out["chiffres"] = chiffres
    else:
        rapport.append("pas de chiffre clé sur la couverture (variante non gérée ?)")
    pas = sorted([s for l in lc for s in l["spans"] if "Poppins-Medium" in s["font"]], key=lambda s: (round(s["bbox"][1]), s["bbox"][0]))
    out["pastilles"] = [s["text"].strip() for s in pas]
    if any("Source" == s["text"].strip() and "Poppins" in s["font"] for l in lc for s in l["spans"]):
        rapport.append("encadré Source sur la couverture : variante non gérée")
    return out


def boites_marine(dc):
    """Encadrés du volet bleu : barre 8fa0ba de 2,25 pt de large + filets blancs. Le dernier est « Source »."""
    res = []
    for b in dc:
        r = b["rect"]
        if b.get("fill") and hexc(b["fill"]) == "8fa0ba" and 2.0 < r.width < 2.6 and r.height > 20:
            d2 = [e for e in dc if e.get("fill") and hexc(e["fill"]) == "ffffff" and e["rect"].width < 1.1 and e["rect"].height > 20
                  and abs(e["rect"].y0 - r.y0) < 1.2 and e["rect"].x0 > r.x0 + 100]
            res.append(fitz.Rect(r.x0, r.y0, d2[0]["rect"].x1 if d2 else r.x0 + 214.6, r.y1))
    return sorted(res, key=lambda r: r.y0)


def rabat_navy(page, lignes, dr, pictos_dir, slug, compteur):
    a, b = RECTO[1]
    lc = lignes_de_colonne(lignes, a, b)
    dc = [d for d in dr if a - 1 <= d["rect"].x0 < b]
    boites = boites_marine(dc)
    if boites:
        top_src = boites[-1].y0
    else:
        hauts = [d["rect"].y0 for d in dc if d.get("fill") and hexc(d["fill"]) == "ffffff" and d["rect"].height < 1.1 and d["rect"].width > 190]
        top_src = min(hauts) if hauts else 400
    accroche = [l for l in lc if l["spans"][0]["font"].startswith("Carlito") and abs(l["spans"][0]["size"] - 11.5) < 0.2
                and hexc_int(l["spans"][0]["color"]) == "e8edf5" and l["y0"] < top_src]
    contacts = [l for l in lc if est_gras(l["spans"][0]) and hexc_int(l["spans"][0]["color"]) == "ffffff" and l["y0"] < top_src and abs(l["size"] - 11.5) < 0.3]
    c = {"accroche": balise(accroche, 11.5)}
    cour = [l for l in contacts if "@" in l["spans"][0]["text"]]
    poste = [l for l in contacts if "@" not in l["spans"][0]["text"]]
    c["courriel"] = cour[0]["spans"][0]["text"].strip() if cour else ""
    c["poste"] = poste[0]["spans"][0]["text"].strip() if poste else ""
    if len(contacts) != 2:
        rapport.append(f"{len(contacts)} lignes de contact (2 attendues)")
    bas_contact = max([l["y1"] for l in contacts] or [150])
    marine = []
    # encadrés intermédiaires (tout sauf Source)
    for r in boites[:-1]:
        lb = [l for l in lc if l["y0"] >= r.y0 - 1 and l["y1"] <= r.y1 + 1]
        e = sous_blocs_boite(lb, r, "marine", page)
        e["_y"] = r.y0
        marine.append(e)
    # pictogrammes : tracés hors encadrés, entre les contacts et Source
    pd = [d for d in dc if d["rect"].y0 > bas_contact + 5 and d["rect"].y1 < top_src - 2 and not est_barre_section(d)
          and not any(dans(d["rect"], r) for r in boites)]
    gr = grouper_pictos(pd, [], ecart=20)
    gr = [g for g in gr if not (g["n"] == 1 and g["bbox"].height < 4 and g["bbox"].width < 4)]
    legs = [l for l in lc if all(est_legende(s) for s in l["spans"]) and l["y0"] < top_src and l["y0"] > bas_contact
            and not any(r.y0 - 1 <= l["y0"] <= r.y1 + 1 for r in boites)]
    for g in gr:
        bb = g["bbox"]
        compteur[0] += 1
        nom = f"{slug}_{compteur[0]}.svg"
        exporter(str(page.parent.name), page.number, (bb.x0 - 0.25, bb.y0 - 0.25, bb.x1 + 0.25, bb.y1 + 0.25), str(pictos_dir / nom))
        p = {"t": "picto", "svg": nom, "_bbox": bb, "_cx": bb.x0 + bb.width / 2, "_y": bb.y0}
        lg = [l for l in legs if bb.y1 - 1 <= l["y0"] <= bb.y1 + 34]
        if lg:
            p["legende"] = balise(lg, 8)
            p["_leg"] = lg[0]
            for l in lg:
                legs.remove(l)
        marine.append(p)
    for l in legs:  # légende sans dessin
        marine.append({"t": "picto", "legende": balise([l], 8), "_leg": l, "_bbox": None, "_cx": None, "_y": l["y0"]})
    marine.sort(key=lambda x: x["_y"])
    c["_marine"] = marine
    # source
    src = [l for l in lc if l["y0"] >= top_src - 0.5]
    deb_ren = next((i for i, l in enumerate(src) if "".join(x["text"] for x in l["spans"]).startswith("Les références")), None)
    texte = [l for i, l in enumerate(src) if (deb_ren is None or i < deb_ren) and "Poppins" not in l["spans"][0]["font"]
             and not (deb_ren is None and "Italic" in l["spans"][0]["font"])]
    ren = src[deb_ren:] if deb_ren is not None else [l for l in src if "Italic" in l["spans"][0]["font"]]
    out = {"texte": balise(texte, 9)}
    liens, seps = [], []
    liens_pdf = page.get_links()
    cur = None
    txt, sep_buf = "", ""
    for l in ren:
        for s in l["spans"]:
            if hexc_int(s["color"]) == "ffffff":
                if cur is None:
                    cur = {"texte": s["text"], "bbox": fitz.Rect(s["bbox"]), "b0": fitz.Rect(s["bbox"])}
                    if liens:
                        seps.append(sep_buf)
                    sep_buf = ""
                    liens.append(cur)
                else:
                    cur["texte"] += " " + s["text"]
                    cur["bbox"] |= fitz.Rect(s["bbox"])
            else:
                t = s["text"]
                if liens:
                    cur = None
                    sep_buf += t
                else:
                    txt += t + ("" if t.endswith(" ") else " ")
    out["renvoi"] = re.sub(r" {2,}", " ", txt).strip()
    if any(x != " ; " for x in seps):
        out["liens_sep"] = seps
    out["liens"] = []
    for lk in liens:
        uri = None
        for L in liens_pdf:
            if L["kind"] == fitz.LINK_URI and fitz.Rect(L["from"]).intersects(lk["b0"]):
                uri = L["uri"]
        if uri and uri.startswith(C.BASE_PDF):
            out["liens"].append({"texte": re.sub(r"\s+", " ", lk["texte"]).strip(), "pdf": urllib.parse.unquote(uri[len(C.BASE_PDF):])})
        else:
            rapport.append(f"lien non résolu : {lk['texte']!r} -> {uri}")
    out["texte"] = out["texte"]
    return c, out


# ---------------------------------------------------------------- import complet
def importer(pdf, slug=None):
    global rapport
    rapport = []
    pdf = pathlib.Path(pdf)
    slug = slug or pdf.stem
    doc = fitz.open(str(pdf))
    if len(doc) != 2:
        raise SystemExit(f"{pdf.name} : {len(doc)} pages")
    pictos_dir = RACINE / "pictos"
    compteur = [0]
    p0, p1 = doc[0], doc[1]
    l0, l1 = lire_lignes(p0), lire_lignes(p1)
    d0, d1 = dessins(p0), dessins(p1)
    d = {"slug": slug, "titre_pdf": doc.metadata.get("title") or slug}
    cov = couverture(p0, l0, d0, slug)
    d.update(cov)
    d["titre_pdf"] = " ".join(cov["titre"])
    rabat = colonne_generique(p0, l0, d0, RECTO, 0, pictos_dir, slug, compteur)
    contact, source = rabat_navy(p0, l0, d0, pictos_dir, slug, compteur)
    marine = contact.pop("_marine", [])
    d["recto"] = {"rabat": rabat, "contact": contact, "source": source}
    if marine:
        d["recto"]["marine"] = marine
    d["verso"] = [colonne_generique(p1, l1, d1, VERSO, i, pictos_dir, slug, compteur) for i in range(3)]
    return d, doc, rapport


def nettoyer(d):
    if isinstance(d, dict):
        return {k: nettoyer(v) for k, v in d.items() if not k.startswith("_")}
    if isinstance(d, list):
        return [nettoyer(x) for x in d]
    return d



# ---------------------------------------------------------------- calage des espacements
def spans_sortie(pdf):
    doc = fitz.open(str(pdf))
    res = []
    for pi, p in enumerate(doc):
        for b in p.get_text("dict")["blocks"]:
            if b["type"] != 0:
                continue
            for l in b["lines"]:
                for s in l["spans"]:
                    res.append((pi, norm(s["text"]), s["bbox"][0], s["bbox"][1]))
    return res


def trouver(spans, pi, txt, x, y):
    c = [s for s in spans if s[0] == pi and s[1] == norm(txt) and abs(s[2] - x) < 14]
    return min(c, key=lambda s: abs(s[3] - y)) if c else None


def colonnes_cles(d):
    """[(préfixe de repère, page, liste de blocs)] dans l'ordre vertical."""
    cols = [("r1_", 0, d["recto"]["rabat"])]
    if d["recto"].get("marine"):
        cols.append(("r2_", 0, d["recto"]["marine"]))
    for i in range(3):
        cols.append((f"v{i + 1}_", 1, d["verso"][i]))
    return cols


def caler(d, slug, iterations=3):
    sortie = RACINE / "sortie"
    sortie.mkdir(exist_ok=True)
    h, pdf = sortie / (slug + ".html"), sortie / (slug + ".pdf")
    gap0 = {}
    for it in range(iterations):
        mes = {}
        h.write_text(C.construire_html(nettoyer(d)), encoding="utf-8")
        C.rendre_pdf(h, pdf, mes)
        sp = spans_sortie(pdf)
        for pre, pi, blocs in colonnes_cles(d):
            prev_fin_cible = mes["r2_c"][1] if pre == "r2_" and "r2_c" in mes else 34.3
            prev_h_change = False
            prev_blk = None
            for i, blk in enumerate(blocs):
                k = f"{pre}{i}"
                if k not in mes:
                    rapport.append(f"repère absent {k}")
                    continue
                hau, bas, gau, lar = mes[k]
                dernier = mes.get(f"{pre}{i - 1}")
                if it == 0:
                    debut = mes["r2_c"][1] if pre == "r2_" and "r2_c" in mes else 34.3
                    gap0[k] = hau - (dernier[1] if dernier else debut)
                t = blk["t"]
                cible = None
                if t == "encadre":
                    cible = blk["_rect"].y0
                elif t == "picto" and blk.get("svg"):
                    cible = blk["_bbox"].y0 - 0.25
                else:
                    ref = blk["_leg"]["spans"][0] if t == "picto" else blk["_ref"]["spans"][0]
                    m = trouver(sp, pi, ref["text"], ref["bbox"][0], ref["bbox"][1])
                    if m:
                        kk = k + ("L" if t == "picto" else "")
                        cible = ref["bbox"][1] - (m[3] - mes[kk][0])
                    else:
                        rapport.append(f"{k} : texte de calage introuvable ({ref['text'][:20]!r})")
                if cible is None:
                    cible = hau
                hauteur = bas - hau
                delta = 0.0
                if t == "picto" and blk.get("svg") and blk.get("legende") and blk.get("_leg"):
                    ref = blk["_leg"]["spans"][0]
                    m = trouver(sp, pi, ref["text"], ref["bbox"][0], ref["bbox"][1])
                    if m and f"{k}L" in mes:
                        w_svg, h_svg = C.svg_dim(RACINE / "pictos" / blk["svg"])
                        cible_leg = ref["bbox"][1] - (m[3] - mes[f"{k}L"][0])
                        ecart_new = cible_leg - cible - h_svg * blk.get("echelle", 1)
                        ecart_now = mes[f"{k}L"][0] - hau - h_svg * blk.get("echelle", 1)
                        delta = ecart_new - ecart_now
                        if abs(delta) > 0.3 or "ecart" in blk:
                            blk["ecart"] = round(ecart_new, 2)
                        else:
                            delta = 0.0
                if t == "picto" and blk.get("svg") and blk.get("_cx") is not None:
                    decal_now = blk.get("decalage_x", 0.0)
                    centre = gau + lar / 2
                    dx = blk["_cx"] - centre
                    if abs(dx) > 0.4:
                        blk["decalage_x"] = round(dx, 1)
                    else:
                        blk.pop("decalage_x", None)
                gap = cible - prev_fin_cible
                explicite = abs(gap - gap0[k]) >= 0.4 or prev_h_change
                if explicite:
                    if gap < -1:
                        rapport.append(f"{k} : espace négatif {gap:.1f}")
                    blk["avant"] = round(gap, 2)
                    if prev_blk is not None:
                        prev_blk["apres"] = 0
                else:
                    blk.pop("avant", None)
                    if prev_blk is not None and not prev_blk.get("_apres_force"):
                        prev_blk.pop("apres", None)
                prev_fin_cible = cible + hauteur + delta
                prev_h_change = abs(delta) > 0.3
                prev_blk = blk
        # chiffres clés de la couverture
        decalage = 0.0
        for n, ch in enumerate(d.get("chiffres", [])):
            k = f"cv{n}"
            if k in mes and "_ref" in ch:
                g = ch["_ref"]
                m = trouver(sp, 0, g["text"], g["bbox"][0], g["bbox"][1])
                if m:
                    # le haut du texte mesuré dans la sortie est m[3] ; la référence est g["bbox"][1]
                    delta = g["bbox"][1] - m[3] - decalage
                    if abs(delta) > 0.15:
                        ch["ajust"] = round(ch.get("ajust", 0.0) + delta, 2)
                        decalage += delta
        # picto du volet marine
        p = d["recto"]["contact"].get("picto")
        if p and "r2_p" in mes and "r2_c" in mes:
            hau, bas, gau, lar = mes["r2_p"]
            if p.get("svg"):
                cible = p["_bbox"].y0 - 0.25
                w_svg, h_svg = C.svg_dim(RACINE / "pictos" / p["svg"])
                if p.get("legende") and "r2_pL" in mes:
                    ref = p["_leg"]["spans"][0]
                    m = trouver(sp, 0, ref["text"], ref["bbox"][0], ref["bbox"][1])
                    if m:
                        cible_leg = ref["bbox"][1] - (m[3] - mes["r2_pL"][0])
                        p["ecart"] = round(cible_leg - cible - h_svg, 2)
                centre = gau + lar / 2
                dx = p["_cx"] - centre
                if abs(dx) > 0.4:
                    p["decalage_x"] = round(dx, 1)
                else:
                    p.pop("decalage_x", None)
            else:
                ref = p["_leg"]["spans"][0]
                m = trouver(sp, 0, ref["text"], ref["bbox"][0], ref["bbox"][1])
                cible = ref["bbox"][1] - (m[3] - hau) if m else hau
            p["avant"] = round(cible - mes["r2_c"][1], 2)
    h.write_text(C.construire_html(nettoyer(d)), encoding="utf-8")
    C.rendre_pdf(h, pdf)
    return pdf


def comparer(ref_pdf, out_pdf, seuil=1.6):
    """Compare les textes des deux PDF : retourne (nb spans, nb absents, nb écarts > seuil, liste des pires)."""
    def spans(path):
        out = {}
        for pi, p in enumerate(fitz.open(str(path))):
            for b in p.get_text("dict")["blocks"]:
                if b["type"] != 0:
                    continue
                for l in b["lines"]:
                    for s in l["spans"]:
                        t = norm(s["text"])
                        if t:
                            out.setdefault((pi, t), []).append((s["bbox"][0], s["bbox"][1]))
        return out
    a, b = spans(ref_pdf), spans(out_pdf)
    n = ab = ec = 0
    pires = []
    for k, v in a.items():
        pool = list(b.get(k, []))
        for r in v:
            n += 1
            if not pool:
                ab += 1
                pires.append((999, k[0], k[1][:30]))
                continue
            m = min(pool, key=lambda q: abs(q[0] - r[0]) + abs(q[1] - r[1]))
            pool.remove(m)
            dy, dx = m[1] - r[1], m[0] - r[0]
            if abs(dy) > seuil or abs(dx) > 1.0:
                ec += 1
                pires.append((round(max(abs(dy), abs(dx)), 1), k[0], k[1][:30]))
    pires.sort(reverse=True)
    return n, ab, ec, pires[:6]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--sauf", nargs="*", default=[])
    a = ap.parse_args()
    cible = pathlib.Path(a.pdf)
    fichiers = sorted(cible.glob("*.pdf")) if cible.is_dir() else [cible]
    for f in fichiers:
        if any(x.lower() in f.name.lower() for x in a.sauf):
            continue
        d, doc, rap = importer(f)
        pdf = caler(d, d["slug"])
        (RACINE / "donnees" / f"{d['slug']}.json").write_text(json.dumps(nettoyer(d), ensure_ascii=False, indent=1), encoding="utf-8")
        n, ab, ec, pires = comparer(f, pdf)
        print(f"{f.name}: {n} textes, {ab} absents, {ec} écarts > 1,6 pt | rapport: {rapport or 'rien'}")
        if pires:
            print("   pires :", pires)
