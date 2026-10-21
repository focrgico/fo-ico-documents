#!/usr/bin/env python3
"""Copie conforme d'un PDF en HTML : chaque texte, tracé et image est posé à sa position exacte (en points).

Le HTML contient une page par page du PDF, dans l'ordre. Les polices viennent du dossier `polices/` (même police
que le PDF, donc mêmes glyphes et mêmes largeurs). Les liens du PDF sont repris. Rien n'est recomposé : le
fichier n'est pas fait pour être modifié à la main, c'est une reproduction du PDF.

Usage :
    python3 outils/pdf_vers_html.py ../docs/accords-locaux/Depliants_FO            # tous les PDF du dossier
    python3 outils/pdf_vers_html.py fichier.pdf --sortie dossier_de_sortie
Les HTML sont écrits dans `sortie/html_copie/` par défaut, à côté d'un dossier `polices/` partagé.
"""
import argparse
import base64
import html
import pathlib
import shutil

import pymupdf as fitz

RACINE = pathlib.Path(__file__).resolve().parent.parent
POLICES = RACINE / "polices"


def hexc(c):
    return "#%02x%02x%02x" % tuple(int(round(v * 255)) for v in c)


def hexi(c):
    return "#%06x" % c


def police(nom):
    """Nom de police du PDF -> (famille CSS, graisse, style)."""
    n = nom.replace(" ", "-")
    if n.startswith("Poppins"):
        g = "700" if "Bold" in n else ("500" if "Medium" in n else "400")
        return "Poppins", g, "normal"
    if n.startswith("Carlito"):
        return "Carlito", ("700" if "Bold" in n else "400"), ("italic" if "Italic" in n else "normal")
    if n.startswith("Liberation"):
        return "'Liberation Sans', Arial, sans-serif", ("700" if "Bold" in n else "400"), ("italic" if "Italic" in n else "normal")
    return f"'{nom}', sans-serif", "400", "normal"


FONT_FACES = """
@font-face { font-family: "Carlito"; font-weight: 400; font-style: normal; src: url("polices/Carlito-Regular.ttf"); }
@font-face { font-family: "Carlito"; font-weight: 700; font-style: normal; src: url("polices/Carlito-Bold.ttf"); }
@font-face { font-family: "Carlito"; font-weight: 400; font-style: italic; src: url("polices/Carlito-Italic.ttf"); }
@font-face { font-family: "Carlito"; font-weight: 700; font-style: italic; src: url("polices/Carlito-BoldItalic.ttf"); }
@font-face { font-family: "Poppins"; font-weight: 400; src: url("polices/Poppins-Regular.ttf"); }
@font-face { font-family: "Poppins"; font-weight: 500; src: url("polices/Poppins-Medium.ttf"); }
@font-face { font-family: "Poppins"; font-weight: 700; src: url("polices/Poppins-Bold.ttf"); }
"""


def chemin_svg(dr):
    segs = []
    cur = None

    def mv(a):
        if cur is None or abs(cur.x - a.x) > 0.01 or abs(cur.y - a.y) > 0.01:
            segs.append(f"M{a.x:.3f} {a.y:.3f}")

    for it in dr["items"]:
        k = it[0]
        if k == "l":
            a, b = it[1], it[2]
            mv(a); segs.append(f"L{b.x:.3f} {b.y:.3f}"); cur = b
        elif k == "c":
            a, b, c, e = it[1:5]
            mv(a); segs.append(f"C{b.x:.3f} {b.y:.3f} {c.x:.3f} {c.y:.3f} {e.x:.3f} {e.y:.3f}"); cur = e
        elif k == "re":
            q = it[1]
            segs.append(f"M{q.x0:.3f} {q.y0:.3f}H{q.x1:.3f}V{q.y1:.3f}H{q.x0:.3f}Z"); cur = None
        elif k == "qu":
            q = it[1]
            segs.append("M" + "L".join(f"{pt.x:.3f} {pt.y:.3f}" for pt in (q.ul, q.ur, q.lr, q.ll)) + "Z"); cur = None
    if dr.get("closePath"):
        segs.append("Z")
    return " ".join(segs)


def dessin_svg(dr):
    attr = []
    if dr.get("fill") is not None:
        attr.append(f'fill="{hexc(dr["fill"])}"')
        if dr.get("fill_opacity", 1) != 1:
            attr.append(f'fill-opacity="{dr["fill_opacity"]:.3f}"')
        if dr.get("even_odd"):
            attr.append('fill-rule="evenodd"')
    else:
        attr.append('fill="none"')
    if dr.get("color") is not None:
        attr.append(f'stroke="{hexc(dr["color"])}" stroke-width="{(dr.get("width") or 0):.3f}"')
        if dr.get("stroke_opacity", 1) != 1:
            attr.append(f'stroke-opacity="{dr["stroke_opacity"]:.3f}"')
        cap = (dr.get("lineCap") or (0,))[0]
        attr.append(f'stroke-linecap="{["butt", "round", "square"][cap] if cap in (0, 1, 2) else "butt"}"')
        join = dr.get("lineJoin", 0)
        attr.append(f'stroke-linejoin="{["miter", "round", "bevel"][int(join)] if join in (0, 1, 2) else "miter"}"')
        if dr.get("dashes") and dr["dashes"] not in ("[] 0", "[] 0.0"):
            import re
            m = re.match(r"\[(.*?)\]\s*([\d.]+)", dr["dashes"])
            if m and m.group(1).strip():
                attr.append(f'stroke-dasharray="{m.group(1).replace(" ", ",")}" stroke-dashoffset="{m.group(2)}"')
    return f'<path d="{chemin_svg(dr)}" {" ".join(attr)}/>'


def texte_svg(span, ligne):
    """Un <text> par span. Les PDF viennent de Chromium avec ces mêmes polices : on laisse le moteur refaire la
    composition (ligatures « ti », « ft », crénage) et on impose seulement la largeur totale du span, mesurée dans le
    PDF, ce qui reproduit aussi l'espacement des lettres des surtitres."""
    chars = span["chars"]
    if not chars:
        return ""
    fam, g, st = police(span["font"])
    c = hexi(span["color"])
    dx, dy = ligne["dir"]
    txt = "".join(ch["c"] for ch in chars)
    if txt.strip() == "":
        return ""
    bb = span["bbox"]
    # espaces de tête et de queue : SVG les écrase, on décale donc le point de départ et on réduit la largeur
    i0 = next(i for i, ch in enumerate(chars) if ch["c"].strip())
    j0 = max(i for i, ch in enumerate(chars) if ch["c"].strip())
    txt = "".join(ch["c"] for ch in chars[i0:j0 + 1])
    ox, oy = chars[i0]["origin"]
    if abs(dx - 1) < 1e-3:
        fin = chars[j0 + 1]["origin"][0] if j0 + 1 < len(chars) else bb[2]
        larg = fin - ox
    else:
        import math
        ex, ey = (chars[j0 + 1]["origin"] if j0 + 1 < len(chars) else (bb[2], bb[3]))
        larg = math.hypot(ex - ox, ey - oy)
    marq = ""
    # ligature du PDF : le 2e caractère de la paire a une avance nulle (le suivant part de la même abscisse)
    paires = []
    sous = chars[i0:j0 + 1]
    for k in range(len(sous) - 1):
        if sous[k]["c"] + sous[k + 1]["c"] in ("ti", "tt", "ft", "fi", "fl", "ff", "tf", "th", "Th"):
            suiv = sous[k + 2]["origin"][0] if k + 2 < len(sous) else (chars[j0 + 1]["origin"][0] if j0 + 1 < len(chars) else bb[2])
            paires.append(suiv - sous[k + 1]["origin"][0] < 0.05 * span["size"])
    if paires and not all(paires):
        if any(paires):
            marq = ' data-mixte="1"'
        else:
            marq = ' style="font-variant-ligatures:none"' + ('' if abs(dx - 1) > 1e-3 else f' textLength="{larg:.3f}" lengthAdjust="spacing"')
    # espaces synthétiques (espacement de lettres) : un <text> par lettre, à sa position
    syn = any(ch["c"] == " " and k + 1 < len(chars)
              and abs(chars[k + 1]["origin"][0] - ch["origin"][0]) < 0.15 * span["size"] for k, ch in enumerate(chars))
    maj = len(txt) > 3 and not any(ch.islower() for ch in txt)   # capitales espacées : pas de ligatures
    if syn or maj or 'data-mixte' in marq:
        out = []
        for k, ch in enumerate(chars):
            if not ch["c"].strip():
                continue
            nxt = chars[k + 1]["origin"][0] if k + 1 < len(chars) else bb[2]
            rt = ""
            if abs(dx - 1) > 1e-3:
                import math
                rt = f' transform="rotate({math.degrees(math.atan2(dy, dx)):.3f} {ch["origin"][0]:.3f} {ch["origin"][1]:.3f})"'
            out.append(f'<text x="{ch["origin"][0]:.3f}" y="{ch["origin"][1]:.3f}" font-family="{fam}" font-weight="{g}" '
                       f'font-style="{st}" font-size="{span["size"]:.3f}" fill="{c}"{rt}>{html.escape(ch["c"])}</text>')
        return "".join(out)
    op = span.get("alpha", 255)
    extra = f' fill-opacity="{op / 255:.3f}"' if op not in (255, None) else ""
    rot = ""
    if abs(dx - 1) > 1e-3:
        import math
        rot = f' transform="rotate({math.degrees(math.atan2(dy, dx)):.3f} {ox:.3f} {oy:.3f})"'
    return (f'<text{marq} x="{ox:.3f}" y="{oy:.3f}" font-family="{fam}" font-weight="{g}" '
            f'font-style="{st}" font-size="{span["size"]:.3f}" fill="{c}"{extra}{rot}>{html.escape(txt)}</text>')


def image_uri(doc, info, smasks=None):
    xref = info.get("xref")
    if not xref:
        return None
    try:
        pix = fitz.Pixmap(doc, xref)
        sm = info.get("smask") or (smasks or {}).get(xref)
        if sm:
            pix = fitz.Pixmap(pix, fitz.Pixmap(doc, sm)) if pix.alpha == 0 else pix
        if pix.colorspace and pix.colorspace.n > 3:
            pix = fitz.Pixmap(fitz.csRGB, pix)
        data = pix.tobytes("png")
    except Exception:
        return None
    return "data:image/png;base64," + base64.b64encode(data).decode()


VERSO_BLANC = False   # --verso-blanc : la colonne centrale du verso (gris clair #F4F6F9) devient blanche


def page_html(doc, page):
    w, h = page.rect.width, page.rect.height
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.3f}pt" height="{h:.3f}pt" viewBox="0 0 {w:.3f} {h:.3f}" '
             f'xml:space="preserve" style="position:absolute;left:0;top:0;display:block">']
    pile = []   # (niveau, balise ouverte) : découpes et groupes actifs
    n_clip = 0
    for dr in page.get_drawings(extended=True):
        niv = dr.get("level", 0)
        while pile and pile[-1] >= niv:
            pile.pop()
            parts.append("</g>")
        t = dr["type"]
        if t == "clip":
            n_clip += 1
            rule = ' clip-rule="evenodd"' if dr.get("even_odd") else ""
            parts.append(f'<clipPath id="k{page.number}_{n_clip}"><path d="{chemin_svg(dr)}"{rule}/></clipPath><g clip-path="url(#k{page.number}_{n_clip})">')
            pile.append(niv)
        elif t == "group":
            op = dr.get("opacity")
            parts.append(f'<g opacity="{op:.3f}">' if op not in (None, 1, 1.0) else "<g>")
            pile.append(niv)
        else:
            if (VERSO_BLANC and page.number == 1 and dr.get("fill") and dr["rect"].width > 200 and dr["rect"].height > 500
                    and hexc(dr["fill"]) == "#f4f6f9"):
                dr = dict(dr, fill=(1.0, 1.0, 1.0))
            parts.append(dessin_svg(dr))
    parts.extend("</g>" for _ in pile)
    smasks = {i[0]: i[1] for i in page.get_images(full=True) if i[1]}
    for info in page.get_image_info(xrefs=True):
        uri = image_uri(doc, info, smasks)
        if uri:
            bb = info["bbox"]
            parts.append(f'<image x="{bb[0]:.3f}" y="{bb[1]:.3f}" width="{bb[2] - bb[0]:.3f}" height="{bb[3] - bb[1]:.3f}" '
                         f'preserveAspectRatio="none" href="{uri}"/>')
    for b in page.get_text("rawdict")["blocks"]:
        if b["type"] != 0:
            continue
        for l in b["lines"]:
            for s in l["spans"]:
                parts.append(texte_svg(s, l))
    parts.append("</svg>")
    liens = []
    for L in page.get_links():
        if L.get("kind") == fitz.LINK_URI and L.get("uri"):
            r = L["from"]
            liens.append(f'<a href="{html.escape(L["uri"])}" style="position:absolute;left:{r.x0:.3f}pt;top:{r.y0:.3f}pt;'
                         f'width:{r.width:.3f}pt;height:{r.height:.3f}pt" aria-label="lien"></a>')
    return f'<section class="page" style="width:{w:.3f}pt;height:{h:.3f}pt">{"".join(parts)}{"".join(liens)}</section>'


def convertir(pdf, sortie):
    doc = fitz.open(str(pdf))
    w, h = doc[0].rect.width, doc[0].rect.height
    titre = doc.metadata.get("title") or pdf.stem
    corps = "\n".join(page_html(doc, p) for p in doc)
    doc_html = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>{html.escape(titre)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
{FONT_FACES}
@page {{ size: {w:.3f}pt {h:.3f}pt; margin: 0; }}
html, body {{ margin: 0; padding: 0; background: #e9ecf1; }}
.page {{ position: relative; overflow: hidden; background: #fff; margin: 0 auto 12pt; page-break-after: always; break-after: page; }}
.page:last-child {{ page-break-after: auto; break-after: auto; }}
.page a {{ display: block; }}
@media print {{ html, body {{ background: #fff; }} .page {{ margin: 0; zoom: 1 !important; }} }}
</style></head><body>
{corps}
<script>
/* écran étroit : la page garde ses proportions et se réduit à la largeur de la fenêtre (rien n'est recomposé) */
(function () {{
  function ajuster() {{
    var pages = document.querySelectorAll('.page');
    if (!pages.length) return;
    var w = pages[0].offsetWidth / (parseFloat(getComputedStyle(pages[0]).zoom) || 1);
    var z = Math.min(1, document.documentElement.clientWidth / w);
    pages.forEach(function (p) {{ p.style.zoom = z; }});
  }}
  window.addEventListener('resize', ajuster); ajuster();
}})();
</script>
</body></html>
"""
    out = sortie / (pdf.stem + ".html")
    out.write_text(doc_html, encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--sortie", default=str(RACINE / "sortie" / "html_copie"))
    ap.add_argument("--verso-blanc", action="store_true", help="colonne centrale du verso en blanc au lieu du gris clair")
    a = ap.parse_args()
    global VERSO_BLANC
    VERSO_BLANC = a.verso_blanc
    sortie = pathlib.Path(a.sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    pol = sortie / "polices"
    if not pol.exists():
        shutil.copytree(POLICES, pol)
    cible = pathlib.Path(a.pdf)
    for f in (sorted(cible.glob("*.pdf")) if cible.is_dir() else [cible]):
        print(convertir(f, sortie))


if __name__ == "__main__":
    main()
