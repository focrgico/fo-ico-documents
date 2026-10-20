#!/usr/bin/env python3
"""Extrait une zone d'un PDF (formes vectorielles + petits textes) en SVG, pour récupérer un pictogramme.

Usage : python3 extraire_picto_depuis_pdf.py fichier.pdf PAGE X0 Y0 X1 Y1 sortie.svg
  PAGE : numéro de page à partir de 0 ; X0 Y0 X1 Y1 : zone en points PDF (origine en haut à gauche).
Seuls les éléments entièrement contenus dans la zone sont repris. Vérifier ensuite le résultat à l'œil.
"""
import sys
import pymupdf as fitz


def hexc(c):
    return "#%02x%02x%02x" % tuple(int(round(v * 255)) for v in c)


def exporter(pdf, page, region, sortie):
    d = fitz.open(pdf)
    p = d[page]
    x0, y0, x1, y1 = region
    parts = []
    for dr in p.get_drawings():
        r = dr["rect"]
        if not (r.x0 >= x0 - 0.5 and r.x1 <= x1 + 0.5 and r.y0 >= y0 - 0.5 and r.y1 <= y1 + 0.5):
            continue
        segs = []
        cur = None

        def mv(a):
            nonlocal cur
            if cur is None or abs(cur.x - a.x) > 0.02 or abs(cur.y - a.y) > 0.02:
                segs.append(f"M{a.x - x0:.2f} {a.y - y0:.2f}")

        for it in dr["items"]:
            k = it[0]
            if k == "l":
                a, b = it[1], it[2]
                mv(a); segs.append(f"L{b.x - x0:.2f} {b.y - y0:.2f}"); cur = b
            elif k == "c":
                a, b, c, e = it[1:5]
                mv(a); segs.append(f"C{b.x - x0:.2f} {b.y - y0:.2f} {c.x - x0:.2f} {c.y - y0:.2f} {e.x - x0:.2f} {e.y - y0:.2f}"); cur = e
            elif k == "re":
                q = it[1]
                segs.append(f"M{q.x0 - x0:.2f} {q.y0 - y0:.2f}H{q.x1 - x0:.2f}V{q.y1 - y0:.2f}H{q.x0 - x0:.2f}Z"); cur = None
            elif k == "qu":
                q = it[1]
                segs.append("M" + "L".join(f"{pt.x - x0:.2f} {pt.y - y0:.2f}" for pt in (q.ul, q.ur, q.lr, q.ll)) + "Z"); cur = None
        if dr.get("closePath"):
            segs.append("Z")
        fill = hexc(dr["fill"]) if dr.get("fill") else "none"
        stroke = hexc(dr["color"]) if dr.get("color") else "none"
        attr = f'fill="{fill}" stroke="{stroke}"'
        if dr.get("color") is not None:
            attr += f' stroke-width="{(dr.get("width") or 0):.3f}" stroke-linecap="round" stroke-linejoin="round"'
        parts.append(f'<path d="{" ".join(segs)}" {attr}/>')
    for b in p.get_text("dict")["blocks"]:
        if b["type"] != 0:
            continue
        for l in b["lines"]:
            for s in l["spans"]:
                bb = s["bbox"]
                if bb[0] >= x0 - 0.5 and bb[2] <= x1 + 0.5 and bb[1] >= y0 - 0.5 and bb[3] <= y1 + 0.5 and s["text"].strip():
                    fam = "Poppins" if s["font"].startswith("Poppins") else "Carlito"
                    gras = "700" if "Bold" in s["font"] else ("500" if "Medium" in s["font"] else "400")
                    ital = "italic" if "Italic" in s["font"] else "normal"
                    parts.append(f'<text x="{s["origin"][0] - x0:.2f}" y="{s["origin"][1] - y0:.2f}" font-family="{fam}" font-weight="{gras}" '
                                 f'font-style="{ital}" font-size="{s["size"]:.2f}" fill="{hexc([((s["color"] >> 16) & 255) / 255, ((s["color"] >> 8) & 255) / 255, (s["color"] & 255) / 255])}">{s["text"].strip()}</text>')
    W, H = x1 - x0, y1 - y0
    open(sortie, "w", encoding="utf-8").write(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.2f} {H:.2f}" width="{W:.2f}pt" height="{H:.2f}pt">\n' + "\n".join(parts) + "\n</svg>\n")
    print(sortie, len(parts), "éléments", f"{W:.1f} x {H:.1f} pt")


if __name__ == "__main__":
    pdf, page, a, b, c, e, out = sys.argv[1:8]
    exporter(pdf, int(page), (float(a), float(b), float(c), float(e)), out)
