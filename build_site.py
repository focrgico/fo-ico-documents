#!/usr/bin/env python3
"""
build_site.py — Génère le site statique FO ICO à partir de catalogue/catalogue.json
et des résumés Markdown présents dans docs/.

USAGE (depuis la racine du dépôt fo-ico-documents, docs/ et catalogue/ doivent
être présents à côté de ce script) :
    python3 build_site.py

Nécessite le paquet "markdown" (pip install markdown --break-system-packages
si besoin).

Produit un dossier site/ contenant :
    site/index.html
    site/accords.html
    site/resumes.html
    site/depliants.html
    site/resumes/<id>.html      (une page par résumé, texte intégral)
    site/assets/style.css
    site/assets/logo.png

Les PDF (accords et dépliants) restent sur GitHub : les liens pointent vers
raw.githubusercontent.com, rien n'est dupliqué dans le site. Les résumés, en
revanche, sont lus directement dans docs/ et convertis en HTML à la
génération — ils ne renvoient plus vers GitHub.

Pour republier le site après une mise à jour du catalogue ou d'un résumé :
    python3 build_site.py
    git add site/
    git commit -m "Regeneration du site"
    git push
puis publication de site/ vers la branche gh-pages (site/ est dans .gitignore) :
    git worktree add /tmp/gh-pages-deploy gh-pages
    rm -rf /tmp/gh-pages-deploy/*
    cp -r site/* /tmp/gh-pages-deploy/
    cd /tmp/gh-pages-deploy && git add -A && git commit -m "Deploiement du site" && git push origin gh-pages
    cd -  &&  git worktree remove /tmp/gh-pages-deploy --force

Recherche (page accords.html) : plein texte sur la CCN ET sur tous les documents
du catalogue (accords locaux, NAO, DUE, élections), à partir de leur .md converti.
Chaque document a sa page de lecture site/textes/<id>.html (ancres #p<n>).
"""

import json
import os
import re
import shutil
import sys
from html.parser import HTMLParser
from urllib.parse import quote

try:
    import markdown as mdlib
except ImportError:
    sys.exit("Le paquet 'markdown' est requis : pip install markdown --break-system-packages")

try:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
except ImportError:
    sys.exit("Le paquet 'python-docx' est requis : pip install python-docx --break-system-packages")

REPO = "focrgico/fo-ico-documents"
BRANCH = "main"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/docs/"
BLOB_BASE = f"https://github.com/{REPO}/blob/{BRANCH}/docs/"

ROOT = os.path.dirname(os.path.abspath(__file__))
CATALOGUE_PATH = os.path.join(ROOT, "catalogue", "catalogue.json")
DOCS_DIR = os.path.join(ROOT, "docs")
OUT_DIR = os.path.join(ROOT, "site")
ASSETS_SRC = os.path.join(ROOT, "assets_src")  # logo.png, style.css attendus ici


def url_for(rel_path, blob=False):
    """Construit une URL GitHub à partir d'un chemin relatif à docs/."""
    if not rel_path:
        return None
    base = BLOB_BASE if blob else RAW_BASE
    return base + quote(rel_path, safe="/")


def pdf_list(a):
    """chemin_pdf peut être une chaîne (1 PDF) ou une liste (plusieurs accords
    signés séparément regroupés sous un même résumé, ex. compteur intermédiaire
    postés/non-postés). Retourne toujours une liste de chemins (peut être vide)."""
    v = a.get("chemin_pdf")
    if not v:
        return []
    return v if isinstance(v, list) else [v]


CATEGORY_COLORS = {
    "CCN": ("#AFC4EA", "#14203A"),          # bleu encore plus soutenu
    "Accord local": ("#F5E1E3", "#7A1F2B"), # bordeaux — net écart avec le rouge vif des boutons/liens
    "NAO": ("#E3F1EF", "#0F6B62"),          # vert-bleu sobre
    "Élections": ("#F5EEE1", "#7A6540"),    # or
    "DUE": ("#EEF1F6", "#5B6578"),          # gris-bleu (texte secondaire du gabarit)
}

PAGE_HEAD = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — FO ICO</title>
<link rel="icon" href="{base}assets/favicon.png" type="image/png">
<link rel="stylesheet" href="{base}assets/style.css">
</head>
<body class="{body_class}">
<header class="nav">
  <a href="{base}index.html" class="brand">
    <span class="brand-title">FO ICO</span>
    <span class="brand-sub">Base documentaire</span>
  </a>
  <nav>
    <a href="{base}index.html" class="{nav_home}">Accueil</a>
    <a href="{base}accords.html" class="{nav_accords}">Accords</a>
    <a href="{base}resumes.html" class="{nav_resumes}">Résumés</a>
    <a href="{base}depliants.html" class="{nav_depliants}">Dépliants</a>
  </nav>
</header>
"""

PAGE_FOOT = """
<footer class="site-footer">
  <div class="footer-left">
    <img src="{base}assets/logo.png" alt="Logo FO ICO" class="footer-logo">
    <span>FO ICO — Base documentaire</span>
  </div>
  <div class="footer-slogan"><span class="red">FO</span>, vos droits notre priorité</div>
</footer>
</body>
</html>
"""


def nav_classes(active):
    keys = ["nav_home", "nav_accords", "nav_resumes", "nav_depliants"]
    names = ["index.html", "accords.html", "resumes.html", "depliants.html"]
    return {k: ("active" if n == active else "") for k, n in zip(keys, names)}


def page_head(title, active, base="", body_class=""):
    return PAGE_HEAD.format(title=title, base=base, body_class=body_class, **nav_classes(active))


def page_foot(base=""):
    return PAGE_FOOT.format(base=base)


def load_catalogue():
    with open(CATALOGUE_PATH, encoding="utf-8") as f:
        return json.load(f)


def esc(s):
    if s is None:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


LINK_ATTR_RE = re.compile(r'(href|src)="([^"]+)"')


def fix_relative_links(html_fragment, resume_rel_path):
    """Réécrit les liens relatifs d'un résumé (relatifs à son propre dossier
    dans docs/) en URL absolues vers GitHub, pour qu'ils fonctionnent une
    fois le résumé sorti de son contexte d'origine."""
    resume_dir = os.path.dirname(resume_rel_path)

    def repl(m):
        attr, target = m.group(1), m.group(2)
        if target.startswith(("http://", "https://", "mailto:", "#")):
            return m.group(0)
        resolved = os.path.normpath(os.path.join(resume_dir, target)).replace("\\", "/")
        return f'{attr}="{url_for(resolved)}"'

    return LINK_ATTR_RE.sub(repl, html_fragment)


COUVERTURE_RE = re.compile(
    r"\n-{3,}\s*\n##\s*COUVERTURE.*?(?=\n-{3,}\s*\n|\Z)",
    re.DOTALL | re.IGNORECASE,
)


def strip_couverture_section(text):
    """Retire le bloc technique 'COUVERTURE — éléments clés' (métadonnées de
    mise en page du dépliant), pas destiné aux lecteurs du résumé en ligne."""
    return COUVERTURE_RE.sub("", text)


def render_resume_fragment(resume_rel_path):
    """Lit le résumé en local (docs/<resume_rel_path>) et le convertit en HTML."""
    local_path = os.path.join(DOCS_DIR, resume_rel_path)
    if not os.path.exists(local_path):
        return None
    with open(local_path, encoding="utf-8") as f:
        text = f.read()
    text = strip_couverture_section(text)
    html_fragment = mdlib.markdown(text, extensions=["tables", "sane_lists", "nl2br"])
    return fix_relative_links(html_fragment, resume_rel_path)


MARINE = RGBColor(0x14, 0x20, 0x3A)
ROUGE = RGBColor(0xC1, 0x12, 0x1F)
SECONDARY = RGBColor(0x5B, 0x65, 0x78)


class HtmlToDocx(HTMLParser):
    """Convertit le même fragment HTML affiché sur la page résumé en document
    Word — pour que le .docx téléchargé reprenne fidèlement cette présentation,
    pas un export brut du Markdown source."""

    def __init__(self, doc):
        super().__init__()
        self.doc = doc
        self.para = None
        self.bold = False
        self.italic = False
        self.list_stack = []
        self.in_cell = False
        self.cell_buf = ""
        self.cell_bold = False
        self.table_rows = None
        self.row_cells = None
        self.skip_depth = 0  # pour ignorer le contenu d'un <a> si besoin plus tard

    def handle_starttag(self, tag, attrs):
        if tag == "blockquote":
            self.skip_depth += 1
            self.para = None
            return
        if self.skip_depth > 0:
            return
        if tag == "h1":
            self.para = self.doc.add_heading(level=1)
        elif tag == "h2":
            self.para = self.doc.add_heading(level=2)
        elif tag == "h3":
            self.para = self.doc.add_heading(level=3)
        elif tag == "p":
            self.para = self.doc.add_paragraph()
        elif tag == "strong":
            self.bold = True
        elif tag == "em":
            self.italic = True
        elif tag in ("ul", "ol"):
            self.list_stack.append(tag)
        elif tag == "li":
            style = "List Bullet" if (self.list_stack and self.list_stack[-1] == "ul") else "List Number"
            self.para = self.doc.add_paragraph(style=style)
        elif tag == "hr":
            p = self.doc.add_paragraph("─" * 40)
            for run in p.runs:
                run.font.color.rgb = SECONDARY
                run.font.size = Pt(8)
        elif tag == "table":
            self.table_rows = []
        elif tag == "tr":
            self.row_cells = []
        elif tag in ("td", "th"):
            self.in_cell = True
            self.cell_buf = ""
            self.cell_bold = tag == "th"

    def handle_endtag(self, tag):
        if tag == "blockquote":
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.skip_depth > 0:
            return
        if tag in ("h1", "h2", "h3", "p", "li"):
            self.para = None
        elif tag == "strong":
            self.bold = False
        elif tag == "em":
            self.italic = False
        elif tag in ("ul", "ol"):
            if self.list_stack:
                self.list_stack.pop()
        elif tag in ("td", "th"):
            self.row_cells.append((self.cell_buf.strip(), self.cell_bold))
            self.in_cell = False
        elif tag == "tr":
            self.table_rows.append(self.row_cells)
            self.row_cells = None
        elif tag == "table":
            self._flush_table()
            self.table_rows = None

    def handle_data(self, data):
        if self.skip_depth > 0:
            return
        if self.in_cell:
            self.cell_buf += data
            return
        if self.para is None:
            return
        text = re.sub(r"\s+", " ", data)
        if not text or (text == " " and not self.para.runs):
            return
        run = self.para.add_run(text)
        run.bold = self.bold
        run.italic = self.italic
        if self.italic and not self.bold:
            run.font.color.rgb = SECONDARY

    def _flush_table(self):
        if not self.table_rows:
            return
        n_cols = max(len(r) for r in self.table_rows)
        t = self.doc.add_table(rows=len(self.table_rows), cols=n_cols)
        t.style = "Light Grid Accent 1"
        for i, row in enumerate(self.table_rows):
            for j, (text, is_bold) in enumerate(row):
                cell = t.cell(i, j)
                cell.text = ""
                run = cell.paragraphs[0].add_run(text)
                run.bold = is_bold
        self.doc.add_paragraph()


def html_fragment_to_docx(fragment_html, title, out_path):
    """Génère un .docx à partir du même fragment HTML que la page web,
    à la volée — aucun résumé Word pré-créé n'est nécessaire."""
    doc = Document()

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    title_p = doc.add_heading(level=0)
    run = title_p.add_run(title)
    run.font.color.rgb = MARINE

    parser = HtmlToDocx(doc)
    parser.feed(fragment_html)

    doc.save(out_path)


FACET_OPTIONS = {
    "statut": [("non-cadre", "Non-cadre"), ("cadre", "Cadre"), ("praticien", "Cadre praticien")],
    "modalite_horaire": [("forfait-jours", "Forfait jours"), ("forfait-heures", "Forfait heures")],
    "temps_travail": [("temps-plein", "Temps plein"), ("temps-partiel", "Temps partiel")],
    "type_contrat": [("cdi", "CDI"), ("cdd", "CDD")],
    "travail_nuit": [("nuit", "Oui")],
    "travail_poste": [("poste", "Posté"), ("non-poste", "Non posté")],
    "handicap": [("rqth", "Oui")],
    "situation_familiale": [
        ("grossesse", "Grossesse / maternité"), ("enfant", "Enfant malade ou handicapé"),
        ("proche-aidant", "Proche aidant"), ("parentalite", "Parentalité (naissance, adoption, congé parental)"),
    ],
}
FACET_LABELS = {
    "statut": "Statut",
    "modalite_horaire": "Modalité horaire", "temps_travail": "Temps de travail",
    "type_contrat": "Type de contrat", "travail_nuit": "Travail de nuit",
    "travail_poste": "Poste", "handicap": "Situation de handicap",
    "situation_familiale": "Situation familiale",
}
# Facettes à 1 seule valeur possible : rendues en Oui/Non plutôt qu'en
# Tous/[valeur unique], plus lisible pour une caractéristique personnelle
# binaire. "Non" reste techniquement équivalent à "Tous" (case vide, pas de
# filtre) — l'absence du tag ne veut pas dire "accord non applicable", donc
# on ne filtre pas non plus activement sur une exclusion.
BOOLEAN_FACETS = {"travail_nuit", "handicap"}


def situation_fields_html():
    """Génère les <label class="select-field">...</select></label> du formulaire
    'Décrivez votre situation' — factorisé car réutilisé sur la page d'accueil
    (qui redirige vers situation.html) et sur situation.html elle-même (qui permet
    de relancer la recherche avec d'autres critères sans repasser par l'accueil)."""
    html = ""
    for key, label in FACET_LABELS.items():
        wrapper_id = ""
        if key == "modalite_horaire":
            wrapper_id = ' id="field-modalite_horaire"'
        default_label = "Non" if key in BOOLEAN_FACETS else "Tous"
        html += f"""        <label class="select-field"{wrapper_id}>
          <span class="select-label">{esc(label)}</span>
          <select name="{key}" class="real-select">
            <option value="">{default_label}</option>
"""
        for value, opt_label in FACET_OPTIONS[key]:
            html += f'            <option value="{value}">{esc(opt_label)}</option>\n'
        html += "          </select>\n        </label>\n"
    return html


# Bascule Modalité horaire selon le Statut (affichée pour cadre/praticien
# seulement) — identique sur l'accueil et sur situation.html. Suppose que
# `situationForm` est déjà défini.
SITUATION_TOGGLE_JS = """
const statutSelect = situationForm.querySelector('select[name="statut"]');
const modaliteField = document.getElementById('field-modalite_horaire');
const modaliteSelect = modaliteField.querySelector('select[name="modalite_horaire"]');

function toggleModaliteField() {
  const isCadreOuPraticien = statutSelect.value === 'cadre' || statutSelect.value === 'praticien';
  modaliteField.style.display = isCadreOuPraticien ? '' : 'none';
  if (!isCadreOuPraticien) { modaliteSelect.value = ''; }
}
statutSelect.addEventListener('change', toggleModaliteField);
toggleModaliteField();
"""

# Bloc CCN (texte intégral + grille de rémunération concernée) affiché après chaque
# recherche. Suppose que `ccnData` est déjà défini (liste {id, titre, href, kind}
# avec kind parmi 'texte' | 'non-praticien' | 'praticien').
SITUATION_CCN_JS = """
function renderCcnBlock(statut) {
  const texte = ccnData.find(c => c.kind === 'texte');
  const grilles = ccnData.filter(c => c.kind !== 'texte');
  // Praticien = médecin (au sens de la CCN des CLCC) ; cadre et non-cadre relèvent
  // tous deux de la grille "non-praticien". Sans statut choisi, les deux grilles
  // sont proposées avec la grille non-praticien active par défaut (profil le plus courant).
  const defaultKind = statut === 'praticien' ? 'praticien' : 'non-praticien';
  let html = '<h4 class="situation-subheading">Convention collective (CCN)</h4><div class="situation-list">';
  if (texte) html += `<a class="situation-item" href="${texte.href}">${texte.titre} →</a>`;
  html += '</div>';
  if (grilles.length > 0) {
    html += '<div class="chips ccn-grille-chips">';
    grilles.forEach(g => {
      const label = g.kind === 'praticien' ? 'Grille de rémunération — praticiens' : 'Grille de rémunération — non-praticiens';
      const active = g.kind === defaultKind ? ' active' : '';
      html += `<a class="chip${active}" href="${g.href}" target="_blank" rel="noopener">${label}</a>`;
    });
    html += '</div>';
  }
  return html;
}
"""

# Calcule et affiche les accords spécifiques puis généraux dans #situation-results.
# Suppose que `situationData` et `situationResults` sont déjà définis.
SITUATION_RENDER_JS = """
function renderSituationResults(filters) {
  const ccnBlock = renderCcnBlock(filters.statut || '');
  const filterEntries = Object.entries(filters);
  // Spécifiques : l'accord est explicitement tagué avec chacun des critères choisis.
  const specifiques = situationData.filter(a =>
    filterEntries.every(([k, v]) => (a[k] || []).includes(v))
  );
  const specifiquesIds = new Set(specifiques.map(a => a.id));
  // Généraux : l'accord ne restreint aucun des critères choisis (champ vide = non tagué,
  // donc a priori applicable à tous), et n'est pas déjà dans les résultats spécifiques.
  const generaux = situationData.filter(a =>
    !specifiquesIds.has(a.id) &&
    filterEntries.every(([k, v]) => (a[k] || []).length === 0)
  );
  if (specifiques.length === 0 && generaux.length === 0) {
    situationResults.innerHTML = '<p class="note">Aucun accord tagué avec ces critères pour le moment — le classement est en cours. Essayez la <a href="accords.html">liste complète des accords</a>.</p>' + ccnBlock;
    return;
  }
  const renderList = a => `<a class="situation-item" href="${a.href}">${a.titre} →</a>`;
  // Pour chaque critère choisi qui correspond à un article vérifié sur cet accord
  // (a.justificatifs[critère][valeur]), affiche la citation avec un lien vers le
  // passage concerné (résumé ou texte intégral, avec surlignage ?q=...). Un accord
  // spécifique sans justificatif enregistré pour ce critère précis reste listé,
  // simplement sans citation détaillée — jamais de référence inventée.
  const renderCitations = a => {
    const lines = [];
    filterEntries.forEach(([k, v]) => {
      const j = a.justificatifs && a.justificatifs[k] && a.justificatifs[k][v];
      if (!j) return;
      const base = j.loc === 'textes' ? a.texteHref : a.resumeHref;
      const link = base ? base + '?q=' + encodeURIComponent(j.q) : a.href;
      lines.push('<li><a href="' + link + '">' + j.t + ' →</a></li>');
    });
    return lines.join('');
  };
  const renderSpecifique = a => {
    const cites = renderCitations(a);
    return '<div class="situation-match"><a class="situation-item" href="' + a.href + '">' + a.titre + ' →</a>' +
      (cites ? '<ul class="situation-citations">' + cites + '</ul>' : '') + '</div>';
  };
  let html = '';
  if (specifiques.length > 0) {
    html += '<h3>' + specifiques.length + ' accord(s) spécifique(s) à votre situation</h3><div class="situation-matches">' +
      specifiques.map(renderSpecifique).join('') + '</div>';
  }
  if (generaux.length > 0) {
    html += '<h4 class="situation-subheading">' + generaux.length + ' accord(s) général(aux), applicable(s) à tous les salariés</h4><div class="situation-list">' +
      generaux.map(renderList).join('') + '</div>';
  }
  situationResults.innerHTML = html + ccnBlock;
}
"""


def build_situation_data(cat):
    # La CCN est traitée à part (bloc dédié, cf. build_situation_ccn_data) : elle n'a
    # pas de résumé propre et son lien générique vers accords.html n'apportait rien ici.
    non_ccn = [a for a in cat["accords"] if a.get("categorie") != "CCN"]
    data = []
    for a in dedup_by_resume(non_ccn) + [
        a for a in non_ccn if not a.get("chemin_resume_md")
    ]:
        entry = {
            "id": a["id"],
            "titre": a["titre"],
            "href": f"resumes/{a['id']}.html" if a.get("chemin_resume_md") else "accords.html",
            "resumeHref": f"resumes/{a['id']}.html" if a.get("chemin_resume_md") else None,
            "texteHref": f"textes/{a['id']}.html" if a.get("chemin_source_md") else None,
        }
        if a.get("justificatifs"):
            entry["justificatifs"] = a["justificatifs"]
        for key in FACET_LABELS:
            entry[key] = a.get(key, [])
        data.append(entry)
    return data


# CCN CLCC : "praticien" = médecin ; cadre et non-cadre relèvent tous deux de la
# grille "non praticien" (terminologie de la CCN elle-même, cf. titres des documents
# sources dans catalogue.json).
CCN_ID_TO_KIND = {
    "ccn-clcc": "texte",
    "ccn-grille-non-praticiens": "non-praticien",
    "ccn-grille-praticiens": "praticien",
}


def build_situation_ccn_data(cat):
    data = []
    for a in cat["accords"]:
        kind = CCN_ID_TO_KIND.get(a["id"])
        if not kind:
            continue
        href = "ccn-texte.html" if kind == "texte" else (url_for(a.get("chemin_pdf")) or "ccn.html")
        data.append({"id": a["id"], "titre": a["titre"], "href": href, "kind": kind})
    return data


def build_index(cat, out_dir):
    html = page_head("Accueil", "index.html", body_class="home")
    html += """
<section class="hero">
  <div class="hero-top">
    <div class="hero-logo-wrap">
      <img src="assets/logo.png" alt="Logo FO ICO" class="hero-logo">
    </div>
    <div class="hero-text">
      <div class="eyebrow">Base documentaire FO ICO</div>
      <h1>Vos droits, à portée de main</h1>
      <p class="hero-sub">Accords collectifs, résumés en langage clair et dépliants FO.</p>
      <div class="search-bar">
        <input type="text" id="site-search" placeholder="Rechercher un accord, un thème..." onkeydown="if(event.key==='Enter'){event.preventDefault();goSearch();}">
        <button type="button" onclick="goSearch()">Rechercher</button>
      </div>
    </div>
    <script>
      function goSearch() {
        const v = document.getElementById('site-search').value.trim();
        if (!v) return;
        location.href = 'accords.html?q=' + encodeURIComponent(v);
      }
    </script>
    <div class="hero-spacer" aria-hidden="true"></div>
  </div>
  <div class="hero-cards">
    <a class="card hero-card" href="accords.html">
      <h3>Accords</h3>
      <p>Les textes signés : CCN, accords locaux, NAO, élections, DUE — au format PDF.</p>
      <span class="link">Consulter →</span>
    </a>
    <a class="card hero-card" href="resumes.html">
      <h3>Résumés</h3>
      <p>L'essentiel de chaque accord, en langage clair, rédigé par vos élus FO.</p>
      <span class="link">Consulter →</span>
    </a>
    <a class="card hero-card" href="depliants.html">
      <h3>Dépliants</h3>
      <p>Le format tryptique, prêt à imprimer ou à consulter en ligne.</p>
      <span class="link">Consulter →</span>
    </a>
  </div>
</section>

<section class="situation" id="situation">
  <div class="situation-box">
    <div class="situation-grid">
      <div class="situation-text">
        <h2>Décrivez votre situation</h2>
        <p>Cadre au forfait jours, non-cadre à temps partiel... choisissez ce
        qui vous concerne.</p>
        <p class="note">Un critère sans résultat ne veut pas dire qu'aucun accord ne s'applique à vous.
        Voir aussi les <a href="accords.html">accords</a>.</p>
      </div>
      <form class="situation-form" id="situation-form">
""" + situation_fields_html() + """        <button type="submit" class="situation-btn">Voir les accords qui s'appliquent</button>
        <p class="note situation-empty-note" id="situation-empty-note" style="display:none;">Choisissez au moins un critère.</p>
      </form>
    </div>
  </div>
</section>

<script>
const situationForm = document.getElementById('situation-form');
""" + SITUATION_TOGGLE_JS + """
situationForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const fd = new FormData(situationForm);
  const params = new URLSearchParams();
  for (const [k, v] of fd.entries()) { if (v) params.set(k, v); }
  const emptyNote = document.getElementById('situation-empty-note');
  if ([...params.keys()].length === 0) {
    emptyNote.style.display = '';
    return;
  }
  emptyNote.style.display = 'none';
  // Les résultats s'affichent sur une page dédiée, avec le même formulaire, pour
  // permettre de relancer la recherche avec d'autres critères sans revenir ici.
  location.href = 'situation.html?' + params.toString();
});
</script>
"""
    html += page_foot()
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)


def build_situation_page(cat, out_dir):
    """Page dédiée aux résultats du filtre 'Ma situation' : reprend le même
    formulaire que l'accueil (pré-rempli depuis l'URL si on y arrive via l'accueil)
    pour que le salarié puisse relancer la recherche avec d'autres critères sans
    revenir en arrière."""
    html = page_head("Ma situation", "index.html")
    html += """
<section class="page-header">
  <img src="assets/logo.png" alt="Logo FO ICO" class="page-logo">
  <div>
    <div class="eyebrow-small">ACCUEIL / MA SITUATION</div>
    <h1>Décrivez votre situation</h1>
    <p>Cadre au forfait jours, non-cadre à temps partiel... choisissez ce qui vous concerne pour voir
    les accords qui s'appliquent. Vous pouvez changer vos critères et relancer la recherche autant de
    fois que nécessaire, directement depuis cette page.</p>
  </div>
</section>
<section class="list-page situation-page">
  <form class="situation-form situation-form-page" id="situation-form">
""" + situation_fields_html() + """        <button type="submit" class="situation-btn">Voir les accords qui s'appliquent</button>
  </form>
  <p class="note">Un critère sans résultat ne veut pas dire qu'aucun accord ne s'applique à vous.
  Voir aussi les <a href="accords.html">accords</a>.</p>
  <div id="situation-results" class="situation-results situation-results-page"></div>
</section>

<script id="situation-data" type="application/json">""" + json.dumps(build_situation_data(cat), ensure_ascii=False) + """</script>
<script id="situation-ccn-data" type="application/json">""" + json.dumps(build_situation_ccn_data(cat), ensure_ascii=False) + """</script>
<script>
const situationData = JSON.parse(document.getElementById('situation-data').textContent);
const ccnData = JSON.parse(document.getElementById('situation-ccn-data').textContent);
const situationForm = document.getElementById('situation-form');
const situationResults = document.getElementById('situation-results');
""" + SITUATION_TOGGLE_JS + SITUATION_CCN_JS + SITUATION_RENDER_JS + """
function runSituationSearch() {
  const fd = new FormData(situationForm);
  const filters = {};
  for (const [k, v] of fd.entries()) { if (v) filters[k] = v; }
  if (Object.keys(filters).length === 0) {
    situationResults.innerHTML = '<p class="note">Choisissez au moins un critère.</p>';
    return;
  }
  renderSituationResults(filters);
  // Met à jour l'URL (sans recharger la page) pour que le lien reste partageable
  // et que la recherche survive à un rafraîchissement de la page.
  history.replaceState(null, '', 'situation.html?' + new URLSearchParams(filters).toString());
}
situationForm.addEventListener('submit', (e) => { e.preventDefault(); runSituationSearch(); });

// Arrivée depuis l'accueil (ou lien partagé) : pré-remplit le formulaire depuis
// l'URL et lance la recherche automatiquement.
const initialParams = new URLSearchParams(location.search);
let hasInitialFilter = false;
for (const [key, value] of initialParams.entries()) {
  const field = situationForm.querySelector(`select[name="${key}"]`);
  if (field) { field.value = value; hasInitialFilter = true; }
}
toggleModaliteField();
if (hasInitialFilter) { runSituationSearch(); }
</script>
"""
    html += page_foot()
    with open(os.path.join(out_dir, "situation.html"), "w", encoding="utf-8") as f:
        f.write(html)


def build_accords(cat, out_dir, acc_docs=None, acc_passages=None):
    ccn = next((a for a in cat["accords"] if a["id"] == "ccn-clcc"), None)
    ccn_search_data = build_ccn_search_data(ccn.get("chemin_source_md")) if ccn else []
    acc_docs = acc_docs or {}
    acc_passages = acc_passages or []

    html = page_head("Accords", "accords.html")
    html += """
<section class="page-header">
  <img src="assets/logo.png" alt="Logo FO ICO" class="page-logo">
  <div>
    <div class="eyebrow-small" id="page-eyebrow">ACCUEIL / ACCORDS</div>
    <h1 id="page-title">Accords</h1>
    <p id="page-desc">Les textes signés : convention collective nationale, accords locaux, NAO, élections, DUE —
    au format PDF, tels que déposés sur le dépôt GitHub FO ICO. La recherche porte sur le texte
    intégral de tous les accords et de la CCN.</p>
  </div>
</section>

<section class="list-page">
  <div class="search-bar small">
    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="#5B6578" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"></circle><path d="M21 21l-4.3-4.3"></path></svg>
    <input type="text" id="filter-search" placeholder="Rechercher un mot dans les accords et la CCN (ex. formation, astreinte)...">
  </div>
  <div class="chips" id="category-chips">
    <span class="chip active" data-cat="all">Tous</span>
"""
    categories = sorted(set(a["categorie"] for a in cat["accords"]))
    for c in categories:
        _, fg = CATEGORY_COLORS.get(c, ("#F4F6F9", "#5B6578"))
        html += f'    <span class="chip" data-cat="{esc(c)}" style="--chip-color:{fg}">{esc(c)}</span>\n'
    html += """  </div>
  <div id="accords-empty" class="ccn-empty" style="display:none;"></div>
  <div class="doc-list" id="doc-list">
"""
    category_order = ["CCN", "Accord local", "NAO", "DUE", "Élections"]
    sorted_accords = sorted(
        cat["accords"],
        key=lambda a: (category_order.index(a["categorie"]) if a["categorie"] in category_order else len(category_order), a["titre"])
    )
    current_cat = None
    for a in sorted_accords:
        bg, fg = CATEGORY_COLORS.get(a["categorie"], ("#F4F6F9", "#5B6578"))
        if a["categorie"] != current_cat:
            current_cat = a["categorie"]
            html += f'    <div class="doc-group-label" data-cat="{esc(current_cat)}" style="color:{fg};background:{bg};">{esc(current_cat)}</div>\n'
        pdfs = pdf_list(a)
        if not pdfs:
            action = '<span class="muted">PDF non disponible</span>'
        elif len(pdfs) == 1:
            action = f'<a href="{esc(url_for(pdfs[0]))}" target="_blank" rel="noopener">Télécharger le PDF →</a>'
        else:
            action = " · ".join(
                f'<a href="{esc(url_for(p))}" target="_blank" rel="noopener">PDF {i + 1}/{len(pdfs)} →</a>'
                for i, p in enumerate(pdfs)
            )
        html += f"""    <div class="doc-row" data-id="{esc(a['id'])}" data-cat="{esc(a['categorie'])}" data-title="{esc(a['titre'].lower())}">
      <span class="tag" style="background:{bg};color:{fg}">{esc(a['categorie'])}</span>
      <span class="doc-title">{esc(a['titre'])}</span>
      <span class="doc-action">{action}</span>
    </div>
"""
    html += "  </div>\n"
    html += """
  <div id="acc-section" style="display:none; margin-top: 32px;">
    <div style="display:flex; align-items:center; gap:14px; margin-bottom:14px;">
      <span class="bar"></span>
      <h2 style="margin:0; font-size:18px; font-weight:700; color:var(--marine);">Dans le texte des accords</h2>
    </div>
    <div id="acc-count" class="ccn-count"></div>
    <div id="acc-results" class="ccn-results"></div>
  </div>

  <div id="ccn-section" style="display:none; margin-top: 32px;">
    <div style="display:flex; align-items:center; gap:14px; margin-bottom:14px;">
      <span class="bar"></span>
      <h2 style="margin:0; font-size:18px; font-weight:700; color:var(--marine);">Dans le texte de la CCN</h2>
    </div>
    <div id="ccn-count" class="ccn-count"></div>
    <div id="ccn-results" class="ccn-results"></div>
  </div>
</section>

<script id="ccn-data" type="application/json">""" + json.dumps(ccn_search_data, ensure_ascii=False) + """</script>
<script id="acc-docs" type="application/json">""" + json.dumps(acc_docs, ensure_ascii=False).replace("</", "<\\/") + """</script>
<script id="acc-data" type="application/json">""" + json.dumps(acc_passages, ensure_ascii=False).replace("</", "<\\/") + """</script>
<script>
const ccnData = JSON.parse(document.getElementById('ccn-data').textContent);
const accDocs = JSON.parse(document.getElementById('acc-docs').textContent);
const accData = JSON.parse(document.getElementById('acc-data').textContent);
const accSection = document.getElementById('acc-section');
const accResults = document.getElementById('acc-results');
const accCount = document.getElementById('acc-count');
const catColors = """ + json.dumps(CATEGORY_COLORS, ensure_ascii=False) + """;
const chips = document.querySelectorAll('.chip');
const rows = document.querySelectorAll('.doc-row');
const groupLabels = document.querySelectorAll('.doc-group-label');
const docList = document.getElementById('doc-list');
const search = document.getElementById('filter-search');
const accordsEmpty = document.getElementById('accords-empty');
const ccnSection = document.getElementById('ccn-section');
const ccnResults = document.getElementById('ccn-results');
const ccnCount = document.getElementById('ccn-count');
const pageEyebrow = document.getElementById('page-eyebrow');
const pageTitle = document.getElementById('page-title');
const pageDesc = document.getElementById('page-desc');
const params = new URLSearchParams(location.search);
if (params.get('q')) search.value = params.get('q');

function norm(s) {
  return s.toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g, '');
}
function escapeHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
// Un terme n'est retenu qu'en début de mot : « formation » trouve « formations »
// mais pas « information ».
function atWordStart(nt, i) { return i === 0 || !/[a-z0-9]/.test(nt[i - 1]); }
function hasTerm(nt, t) {
  let i = 0;
  while ((i = nt.indexOf(t, i)) !== -1) { if (atWordStart(nt, i)) return true; i += 1; }
  return false;
}
function highlightAll(text, terms) {
  const nt = norm(text);
  let marks = [];
  terms.forEach(t => {
    let idx = 0;
    while (true) {
      const found = nt.indexOf(t, idx);
      if (found === -1) break;
      if (atWordStart(nt, found)) marks.push([found, found + t.length]);
      idx = found + t.length;
    }
  });
  if (marks.length === 0) return escapeHtml(text);
  marks.sort((a, b) => a[0] - b[0]);
  const merged = [];
  for (const m of marks) {
    if (merged.length && m[0] <= merged[merged.length - 1][1]) {
      merged[merged.length - 1][1] = Math.max(merged[merged.length - 1][1], m[1]);
    } else {
      merged.push(m.slice());
    }
  }
  let out = '';
  let pos = 0;
  merged.forEach(([s, e]) => {
    out += escapeHtml(text.slice(pos, s)) + '<mark>' + escapeHtml(text.slice(s, e)) + '</mark>';
    pos = e;
  });
  out += escapeHtml(text.slice(pos));
  return out;
}

function runCcnSearch(raw) {
  if (raw.trim().length < 3) {
    ccnSection.style.display = 'none';
    ccnResults.innerHTML = '';
    ccnCount.innerHTML = '';
    return;
  }
  ccnSection.style.display = 'block';
  const q = norm(raw.trim());
  const words = q.split(/\\s+/).filter(w => w.length >= 2);
  let matches = ccnData.filter(p => hasTerm(norm(p.text), q));
  let mode = 'exact';
  if (matches.length === 0 && words.length > 1) {
    matches = ccnData.filter(p => { const t = norm(p.text); return words.every(w => hasTerm(t, w)); });
    mode = 'approx';
  }
  if (matches.length === 0) {
    ccnCount.innerHTML = '<div class="ccn-empty">Aucun résultat dans la CCN pour « ' + escapeHtml(raw.trim()) + ' ».</div>';
    ccnResults.innerHTML = '';
    return;
  }
  const shown = matches.slice(0, 40);
  let countMsg = shown.length + (shown.length > 1 ? ' passages trouvés' : ' passage trouvé');
  if (mode === 'approx') countMsg += ' — pas de correspondance exacte pour la phrase complète, résultats contenant tous les mots';
  if (matches.length > 40) countMsg += ' (limité aux 40 premiers sur ' + matches.length + ')';
  ccnCount.innerHTML = '<span class="note">' + countMsg + '</span>';
  const terms = mode === 'exact' ? [q] : words;
  ccnResults.innerHTML = shown.map(p => `
    <div class="ccn-result">
      ${p.label ? '<span class="ccn-label">' + escapeHtml(p.label) + '</span>' : ''}
      ${p.before ? '<p class="ccn-context">…' + escapeHtml(p.before) + '</p>' : ''}
      <p>${highlightAll(p.text, terms)}</p>
      ${p.after ? '<p class="ccn-context">' + escapeHtml(p.after) + '…</p>' : ''}
      <a class="ccn-jump" href="ccn-texte.html#p${p.idx}">Voir dans la CCN →</a>
    </div>
  `).join('');
}


// Recherche plein texte dans les accords hors CCN. Renvoie l'ensemble des id
// d'accords contenant le terme (pour afficher aussi leur ligne dans la liste).
accData.forEach(p => { p.n = norm(p.t); });
function runAccSearch(raw, cat) {
  const hits = new Set();
  if (raw.trim().length < 3) {
    accSection.style.display = 'none'; accResults.innerHTML = ''; accCount.innerHTML = '';
    return hits;
  }
  accSection.style.display = 'block';
  const q = norm(raw.trim());
  const words = q.split(/\\s+/).filter(w => w.length >= 2);
  const pool = accData.filter(p => cat === 'all' || accDocs[p.a].categorie === cat);
  let matches = pool.filter(p => hasTerm(p.n, q));
  let mode = 'exact';
  if (matches.length === 0 && words.length > 1) {
    matches = pool.filter(p => words.every(w => hasTerm(p.n, w)));
    mode = 'approx';
  }
  if (matches.length === 0) {
    accCount.innerHTML = '<div class="ccn-empty">Le mot « ' + escapeHtml(raw.trim()) + ' » n\\'apparaît dans le texte d\\'aucun accord' + (cat === 'all' ? '' : ' « ' + escapeHtml(cat) + ' »') + '.</div>';
    accResults.innerHTML = '';
    return hits;
  }
  const groups = {};
  matches.forEach(p => { (groups[p.a] = groups[p.a] || []).push(p); hits.add(p.a); });
  const ids = Object.keys(groups).sort((x, y) => groups[y].length - groups[x].length);
  let msg = matches.length + (matches.length > 1 ? ' passages' : ' passage') + ' dans ' + ids.length + (ids.length > 1 ? ' documents' : ' document');
  if (mode === 'approx') msg += ' — pas de correspondance exacte pour la phrase complète, résultats contenant tous les mots';
  accCount.innerHTML = '<span class="note">' + msg + '</span>';
  const terms = mode === 'exact' ? [q] : words;
  const qs = encodeURIComponent(raw.trim());
  const card = (d, p) => `
      <div class="ccn-result">
        ${p.l && !(p.t.length <= 95 && p.t.startsWith(p.l.slice(0, 80))) ? '<span class="ccn-label">' + escapeHtml(p.l) + '</span>' : ''}
        <p>${highlightAll(p.t.length > 600 ? p.t.slice(0, 600) + '…' : p.t, terms)}</p>
        <a class="ccn-jump" href="textes/${p.a}.html?q=${qs}#p${p.i}">Voir dans le texte →</a>
      </div>`;
  accResults.innerHTML = ids.map(id => {
    const d = accDocs[id], list = groups[id];
    const first = list.slice(0, 3).map(p => card(d, p)).join('');
    const rest = list.length > 3
      ? '<details><summary class="ccn-jump" style="cursor:pointer">Voir les ' + (list.length - 3) + ' autres passages</summary><div class="ccn-results" style="margin-top:10px">' + list.slice(3).map(p => card(d, p)).join('') + '</div></details>'
      : '';
    return `
    <div class="acc-group" style="display:flex;flex-direction:column;gap:10px;">
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
        <span class="tag" style="background:${(catColors[d.categorie]||['#F4F6F9','#5B6578'])[0]};color:${(catColors[d.categorie]||['#F4F6F9','#5B6578'])[1]}">${escapeHtml(d.categorie)}</span>
        <strong style="color:var(--marine)">${escapeHtml(d.titre)}</strong>
        <span class="note">${list.length} ${list.length > 1 ? 'passages' : 'passage'}</span>
        ${d.ocr ? '<span class="note">⚠️ texte OCR, à vérifier sur le PDF</span>' : ''}
        ${d.pdf ? '<a class="ccn-jump" style="margin-top:0" href="' + d.pdf + '" target="_blank" rel="noopener">PDF signé →</a>' : ''}
      </div>
      ${first}${rest}
    </div>`;
  }).join('');
  return hits;
}

function applyFilters() {
  const activeChip = document.querySelector('.chip.active').dataset.cat;
  const raw = search.value.trim();
  const q = raw.toLowerCase();

  if (activeChip === 'CCN') {
    const catRows = Array.from(rows).filter(r => r.dataset.cat === 'CCN');
    rows.forEach(r => { r.style.display = 'none'; });
    if (q) {
      docList.style.display = 'none';
    } else {
      docList.style.display = '';
      catRows.forEach(r => { r.style.display = 'flex'; });
    }
    accordsEmpty.style.display = 'none';
    runAccSearch('', 'CCN');
    runCcnSearch(raw);
  } else if (activeChip === 'all') {
    docList.style.display = '';
    const hits = runAccSearch(raw, 'all');
    const nq = norm(raw);
    const rowsToShow = q ? Array.from(rows).filter(r => norm(r.dataset.title).includes(nq)) : Array.from(rows);
    rows.forEach(r => { r.style.display = 'none'; });
    rowsToShow.forEach(r => { r.style.display = 'flex'; });
    runCcnSearch(raw);
    if (q && rowsToShow.length === 0 && hits.size === 0) {
      accordsEmpty.style.display = 'block';
      accordsEmpty.textContent = 'Aucun accord ne correspond à « ' + raw + ' », ni dans son titre ni dans son texte.';
    } else {
      accordsEmpty.style.display = 'none';
      accordsEmpty.textContent = '';
    }
  } else {
    docList.style.display = '';
    const catRows = Array.from(rows).filter(r => r.dataset.cat === activeChip);
    const hits = runAccSearch(raw, activeChip);
    const nq = norm(raw);
    const rowsToShow = q ? catRows.filter(r => norm(r.dataset.title).includes(nq)) : catRows;
    rows.forEach(r => { r.style.display = 'none'; });
    rowsToShow.forEach(r => { r.style.display = 'flex'; });
    ccnSection.style.display = 'none';
    ccnResults.innerHTML = '';
    ccnCount.innerHTML = '';
    if (q && rowsToShow.length === 0 && hits.size === 0) {
      accordsEmpty.style.display = 'block';
      accordsEmpty.textContent = 'Aucun accord « ' + activeChip + ' » ne correspond à « ' + raw + ' », ni dans son titre ni dans son texte.';
    } else {
      accordsEmpty.style.display = 'none';
      accordsEmpty.textContent = '';
    }
  }

  groupLabels.forEach(label => {
    const hasVisible = Array.from(rows).some(r => r.dataset.cat === label.dataset.cat && r.style.display !== 'none');
    label.style.display = hasVisible ? 'block' : 'none';
  });

  if (raw) {
    pageEyebrow.textContent = 'ACCUEIL / ACCORDS / RÉSULTATS';
    pageTitle.textContent = 'Résultats de recherche';
    pageDesc.textContent = 'Pour « ' + raw + ' » — dans les titres et le texte des accords, et dans le texte de la CCN.';
  } else {
    pageEyebrow.textContent = 'ACCUEIL / ACCORDS';
    pageTitle.textContent = 'Accords';
    pageDesc.textContent = "Les textes signés : convention collective nationale, accords locaux, NAO, élections, DUE — au format PDF, tels que déposés sur le dépôt GitHub FO ICO. La recherche porte sur le texte intégral de tous les accords et de la CCN.";
  }
}
chips.forEach(c => c.addEventListener('click', () => {
  chips.forEach(x => x.classList.remove('active'));
  c.classList.add('active');
  applyFilters();
}));
search.addEventListener('input', applyFilters);
search.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); applyFilters(); } });
applyFilters();
</script>
"""
    html += page_foot()
    with open(os.path.join(out_dir, "accords.html"), "w", encoding="utf-8") as f:
        f.write(html)


def dedup_by_resume(accords):
    """Plusieurs accords (ex. Acquisition CP maladie cadres/non-cadres) pointent
    vers le même résumé source (ex. ATT cadres/non-cadres) : on ne liste/génère
    qu'une seule fois par fichier résumé source, sous le premier titre rencontré."""
    seen = set()
    result = []
    for a in accords:
        path = a.get("chemin_resume_md")
        if not path or path in seen:
            continue
        seen.add(path)
        result.append(a)
    return result


THEME_COLORS = {
    "Temps de travail / organisation": ("#C7D5F0", "#14203A"),
    "Rémunération / épargne": ("#F5EEE1", "#7A6540"),
    "Carrière": ("#E3F1EF", "#0F6B62"),
    "Carrière / égalité": ("#E3F1EF", "#0F6B62"),
    "Congés": ("#F5E1E3", "#7A1F2B"),
    "Contrats de travail": ("#EEF1F6", "#5B6578"),
    "Instances / dialogue social": ("#F3E3EC", "#8A2A5E"),
    "Protection sociale": ("#E9F1E7", "#4A6B3E"),
    "Vie syndicale": ("#F5EEE1", "#7A6540"),
    "Convention collective": ("#C7D5F0", "#14203A"),
    "NAO": ("#F6E9DD", "#9C5B1F"),  # distinct des autres thèmes (roux/ambre), pas la même teinte que "Carrière"
}


def build_resumes(cat, out_dir, res_docs=None, res_passages=None):
    """Page de liste des résumés — chaque carte renvoie vers sa page locale
    site/resumes/<id>.html plutôt que vers GitHub."""
    entries = dedup_by_resume(cat["accords"])
    entries_sorted = sorted(entries, key=lambda a: (a["theme"], a["titre"]))
    themes = sorted(set(a["theme"] for a in entries_sorted))
    res_docs = res_docs or {}
    res_passages = res_passages or []

    html = page_head("Résumés", "resumes.html")
    html += """
<section class="page-header">
  <img src="assets/logo.png" alt="Logo FO ICO" class="page-logo">
  <div>
    <div class="eyebrow-small">ACCUEIL / RÉSUMÉS</div>
    <h1>Résumés</h1>
    <p>L'essentiel de chaque accord, rédigé en langage clair par vos élus FO.</p>
  </div>
</section>
<section class="list-page">
  <div class="search-bar small">
    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="#5B6578" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"></circle><path d="M21 21l-4.3-4.3"></path></svg>
    <input type="text" id="filter-search" placeholder="Rechercher un résumé ou un mot dans son texte...">
  </div>
  <div class="chips" id="theme-chips">
    <span class="chip active" data-theme="all">Tous</span>
"""
    for t in themes:
        _, t_fg = THEME_COLORS.get(t, ("#F4F6F9", "#5B6578"))
        html += f'    <span class="chip" data-theme="{esc(t)}" style="--chip-color:{t_fg}">{esc(t)}</span>\n'
    html += """  </div>
  <div id="res-empty" class="ccn-empty" style="display:none;"></div>
  <div class="cards-grid" id="doc-list">
"""
    current_theme = None
    for a in entries_sorted:
        bg, fg = THEME_COLORS.get(a["theme"], ("#F4F6F9", "#5B6578"))
        if a["theme"] != current_theme:
            current_theme = a["theme"]
            html += f'    <div class="doc-group-label full-row" data-theme="{esc(current_theme)}" style="color:{fg};background:{bg};">{esc(current_theme)}</div>\n'
        html += f"""    <div class="doc-card" data-id="{esc(a['id'])}" data-title="{esc(a['titre'].lower())}" data-theme="{esc(a['theme'])}">
      <span class="tag" style="background:{bg};color:{fg}">{esc(a['theme'])}</span>
      <h3>{esc(a['titre'])}</h3>
      <a href="resumes/{esc(a['id'])}.html" class="link">Lire le résumé →</a>
    </div>
"""
    html += "  </div>\n</section>\n"
    html += """
<div id="res-section" style="display:none; margin-top: 32px; max-width: 1100px;">
  <div style="display:flex; align-items:center; gap:14px; margin-bottom:14px;">
    <span class="bar"></span>
    <h2 style="margin:0; font-size:18px; font-weight:700; color:var(--marine);">Dans le texte des résumés</h2>
  </div>
  <div id="res-count" class="ccn-count"></div>
  <div id="res-results" class="ccn-results"></div>
</div>
</section>
<script id="res-docs" type="application/json">""" + json.dumps(res_docs, ensure_ascii=False).replace("</", "<\\/") + """</script>
<script id="res-data" type="application/json">""" + json.dumps(res_passages, ensure_ascii=False).replace("</", "<\\/") + """</script>
<script>
const resDocs = JSON.parse(document.getElementById('res-docs').textContent);
const resData = JSON.parse(document.getElementById('res-data').textContent);
const themeColors = """ + json.dumps(THEME_COLORS, ensure_ascii=False) + """;
const resSection = document.getElementById('res-section');
const resResults = document.getElementById('res-results');
const resCount = document.getElementById('res-count');
const resEmpty = document.getElementById('res-empty');
const search = document.getElementById('filter-search');
const cards = document.querySelectorAll('.doc-card');
const themeLabels = document.querySelectorAll('.doc-group-label');
const themeChips = document.querySelectorAll('#theme-chips .chip');
let activeTheme = 'all';

function norm(s) { return s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, ''); }
function escapeHtml(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function atWordStart(nt, i) { return i === 0 || !/[a-z0-9]/.test(nt[i - 1]); }
function hasTerm(nt, t) { let i = 0; while ((i = nt.indexOf(t, i)) !== -1) { if (atWordStart(nt, i)) return true; i += 1; } return false; }
function highlightAll(text, terms) {
  const nt = norm(text);
  let marks = [];
  terms.forEach(t => { let i = 0; while ((i = nt.indexOf(t, i)) !== -1) { if (atWordStart(nt, i)) marks.push([i, i + t.length]); i += t.length; } });
  if (!marks.length) return escapeHtml(text);
  marks.sort((a, b) => a[0] - b[0]);
  const merged = [];
  marks.forEach(m => { if (merged.length && m[0] <= merged[merged.length - 1][1]) merged[merged.length - 1][1] = Math.max(merged[merged.length - 1][1], m[1]); else merged.push(m.slice()); });
  let out = '', pos = 0;
  merged.forEach(([a, b]) => { out += escapeHtml(text.slice(pos, a)) + '<mark>' + escapeHtml(text.slice(a, b)) + '</mark>'; pos = b; });
  return out + escapeHtml(text.slice(pos));
}
resData.forEach(p => { p.n = norm(p.t); });

function runResSearch(raw, theme) {
  const hits = new Set();
  if (raw.trim().length < 3) { resSection.style.display = 'none'; resResults.innerHTML = ''; resCount.innerHTML = ''; return hits; }
  resSection.style.display = 'block';
  const q = norm(raw.trim());
  const words = q.split(/\s+/).filter(w => w.length >= 2);
  const pool = resData.filter(p => theme === 'all' || resDocs[p.a].categorie === theme);
  let matches = pool.filter(p => hasTerm(p.n, q));
  let mode = 'exact';
  if (matches.length === 0 && words.length > 1) { matches = pool.filter(p => words.every(w => hasTerm(p.n, w))); mode = 'approx'; }
  if (matches.length === 0) {
    resCount.innerHTML = '<div class="ccn-empty">Le mot « ' + escapeHtml(raw.trim()) + ' » n\\'apparaît dans le texte d\\'aucun résumé' + (theme === 'all' ? '' : ' « ' + escapeHtml(theme) + ' »') + '.</div>';
    resResults.innerHTML = '';
    return hits;
  }
  const groups = {};
  matches.forEach(p => { (groups[p.a] = groups[p.a] || []).push(p); hits.add(p.a); });
  const ids = Object.keys(groups).sort((x, y) => groups[y].length - groups[x].length);
  let msg = matches.length + (matches.length > 1 ? ' passages' : ' passage') + ' dans ' + ids.length + (ids.length > 1 ? ' résumés' : ' résumé');
  if (mode === 'approx') msg += ' — pas de correspondance exacte pour la phrase complète, résultats contenant tous les mots';
  resCount.innerHTML = '<span class="note">' + msg + '</span>';
  const terms = mode === 'exact' ? [q] : words;
  const qs = encodeURIComponent(raw.trim());
  const card = (p) => `
      <div class="ccn-result">
        ${p.l && !(p.t.length <= 95 && p.t.startsWith(p.l.slice(0, 80))) ? '<span class="ccn-label">' + escapeHtml(p.l) + '</span>' : ''}
        <p>${highlightAll(p.t.length > 600 ? p.t.slice(0, 600) + '…' : p.t, terms)}</p>
      </div>`;
  resResults.innerHTML = ids.map(id => {
    const d = resDocs[id], list = groups[id];
    const tc = themeColors[d.categorie] || ['#F4F6F9', '#5B6578'];
    const first = list.slice(0, 2).map(card).join('');
    const rest = list.length > 2 ? '<details><summary class="ccn-jump" style="cursor:pointer">Voir les ' + (list.length - 2) + ' autres passages</summary><div class="ccn-results" style="margin-top:10px">' + list.slice(2).map(card).join('') + '</div></details>' : '';
    return `
    <div style="display:flex;flex-direction:column;gap:10px;">
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
        <span class="tag" style="background:${tc[0]};color:${tc[1]}">${escapeHtml(d.categorie)}</span>
        <strong style="color:var(--marine)">${escapeHtml(d.titre)}</strong>
        <span class="note">${list.length} ${list.length > 1 ? 'passages' : 'passage'}</span>
        <a class="ccn-jump" style="margin-top:0" href="resumes/${id}.html?q=${qs}">Lire le résumé →</a>
      </div>
      ${first}${rest}
    </div>`;
  }).join('');
  return hits;
}

function applyFilters() {
  const raw = search.value.trim();
  const q = raw.trim().toLowerCase();
  const nq = norm(raw);
  const hits = runResSearch(raw, activeTheme);
  cards.forEach(c => {
    const themeOk = activeTheme === 'all' || c.dataset.theme === activeTheme;
    const qOk = !q || norm(c.dataset.title).includes(nq);
    c.style.display = (themeOk && qOk) ? 'flex' : 'none';
  });
  themeLabels.forEach(label => {
    const hasVisible = Array.from(cards).some(c => c.dataset.theme === label.dataset.theme && c.style.display !== 'none');
    label.style.display = hasVisible ? 'block' : 'none';
  });
  const anyVisible = Array.from(cards).some(c => c.style.display !== 'none');
  const noText = hits.size === 0;
  resEmpty.style.display = (q && !anyVisible && noText) ? 'block' : 'none';
  resEmpty.textContent = (q && !anyVisible && noText) ? 'Aucun résumé ne correspond à « ' + raw + ' », ni dans son titre ni dans son texte.' : '';
}
search.addEventListener('input', applyFilters);
themeChips.forEach(c => c.addEventListener('click', () => {
  themeChips.forEach(x => x.classList.remove('active'));
  c.classList.add('active');
  activeTheme = c.dataset.theme;
  applyFilters();
}));
</script>
"""
    html += page_foot()
    with open(os.path.join(out_dir, "resumes.html"), "w", encoding="utf-8") as f:
        f.write(html)


def build_resume_pages(cat, out_dir):
    """Une page HTML par résumé : texte intégral + téléchargements en bas
    (résumé Markdown source + dépliant(s) correspondant(s))."""
    resumes_dir = os.path.join(out_dir, "resumes")
    os.makedirs(resumes_dir, exist_ok=True)

    entries = dedup_by_resume(cat["accords"])
    skipped = []
    for a in entries:
        fragment = render_resume_fragment(a["chemin_resume_md"])
        if fragment is None:
            skipped.append(a["id"])
            continue

        html = page_head(a["titre"], "resumes.html", base="../")
        html += f"""
<section class="page-header">
  <img src="../assets/logo.png" alt="Logo FO ICO" class="page-logo">
  <div>
    <div class="eyebrow-small">ACCUEIL / RÉSUMÉS / {esc(a['titre'].upper())}</div>
    <h1>{esc(a['titre'])}</h1>
  </div>
</section>

<article class="resume-content" id="resume-article">
{fragment}
</article>
<script>
(function () {{
  const q = new URLSearchParams(location.search).get('q');
  if (!q || q.trim().length < 3) return;
  const norm = s => s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  const terms = norm(q.trim()).split(/\s+/).filter(w => w.length >= 2);
  let first = null;
  document.querySelectorAll('#resume-article p, #resume-article li, #resume-article td, #resume-article h2, #resume-article h3').forEach(el => {{
    const txt = el.textContent, nt = norm(txt);
    let marks = [];
    terms.forEach(t => {{ let i = 0; while ((i = nt.indexOf(t, i)) !== -1) {{ if (i === 0 || !/[a-z0-9]/.test(nt[i - 1])) marks.push([i, i + t.length]); i += 1; }} }});
    if (!marks.length) return;
    marks.sort((a, b) => a[0] - b[0]);
    const merged = [];
    marks.forEach(m => {{ if (merged.length && m[0] <= merged[merged.length - 1][1]) merged[merged.length - 1][1] = Math.max(merged[merged.length - 1][1], m[1]); else merged.push(m.slice()); }});
    let out = '', pos = 0;
    const esc = s => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    merged.forEach(([a, b]) => {{ out += esc(txt.slice(pos, a)) + '<mark>' + esc(txt.slice(a, b)) + '</mark>'; pos = b; }});
    el.innerHTML = out + esc(txt.slice(pos));
    if (!first) first = el;
  }});
  if (first) first.scrollIntoView({{ block: 'center' }});
}})();
</script>

<section class="download-box">
  <h2>Téléchargements</h2>
  <div class="download-links">
"""
        resume_raw_url = url_for(a["chemin_resume_md"])
        try:
            html_fragment_to_docx(fragment, a["titre"], os.path.join(resumes_dir, f"{a['id']}.docx"))
            html += f'    <a class="download-btn primary" href="{esc(a["id"])}.docx">Télécharger le résumé (.docx) →</a>\n'
        except Exception as e:
            print(f"ATTENTION : conversion .docx échouée pour {a['id']} ({e}) — repli sur le .md brut.")
            html += f'    <a class="download-btn" href="{esc(resume_raw_url)}" target="_blank" rel="noopener">Télécharger le résumé (.md) →</a>\n'

        dep = a.get("chemin_depliant")
        dep_list = dep if isinstance(dep, list) else ([dep] if dep else [])
        for i, d in enumerate(dep_list):
            label = "Télécharger le dépliant (PDF) →" if len(dep_list) == 1 else f"Télécharger le dépliant {i + 1}/{len(dep_list)} (PDF) →"
            html += f'    <a class="download-btn primary" href="{esc(url_for(d))}" target="_blank" rel="noopener">{label}</a>\n'
        if not dep_list:
            html += '    <span class="muted">Pas encore de dépliant pour cet accord.</span>\n'

        pdfs = pdf_list(a)
        for i, p in enumerate(pdfs):
            label = "Voir l'accord signé (PDF) →" if len(pdfs) == 1 else f"Voir l'accord signé {i + 1}/{len(pdfs)} (PDF) →"
            html += f'    <a class="download-btn" href="{esc(url_for(p))}" target="_blank" rel="noopener">{label}</a>\n'

        html += "  </div>\n</section>\n"
        html += page_foot(base="../")

        with open(os.path.join(resumes_dir, f"{a['id']}.html"), "w", encoding="utf-8") as f:
            f.write(html)

    if skipped:
        print(f"ATTENTION : résumé introuvable en local pour {skipped} — page(s) non générée(s).")


TOC_LINE_RE = re.compile(r"\.{3,}\s*\d+\s*$")
ARTICLE_LABEL_RE = re.compile(r"^(ARTICLE\s+\d+[\.\d]*|Article\s+\d+\.\d+\.?)\b(.*)$")


def build_ccn_search_data(md_relpath):
    """Découpe le texte intégral de la CCN en paragraphes cherchables, avec le
    dernier intitulé d'article rencontré comme repère (best-effort : le fichier
    source est une conversion automatique du PDF, cf. note en tête du document —
    les numéros d'article affichés ici ne remplacent pas une vérification sur le PDF).
    Chaque passage reçoit un idx stable, utilisé comme ancre (#p<idx>) vers la page
    ccn-texte.html, plus un peu de contexte (paragraphe précédent/suivant)."""
    local_path = os.path.join(DOCS_DIR, md_relpath)
    if not os.path.exists(local_path):
        return []
    with open(local_path, encoding="utf-8") as f:
        text = f.read()

    lines = [l for l in text.split("\n") if not TOC_LINE_RE.search(l)]
    text = "\n".join(lines)
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    results = []
    current_label = ""
    idx = 0
    for p in paras:
        useful = re.sub(r"[\d\s\x0c]", "", p)
        if len(useful) <= 3:
            continue
        m = ARTICLE_LABEL_RE.match(p.split("\n")[0].strip())
        if m:
            current_label = re.sub(r"\s+", " ", p.split("\n")[0].strip())[:90]
        snippet = re.sub(r"\s+", " ", p).strip()
        results.append({"idx": idx, "label": current_label, "text": snippet})
        idx += 1

    for i, r in enumerate(results):
        r["before"] = results[i - 1]["text"][-160:] if i > 0 else ""
        r["after"] = results[i + 1]["text"][:160] if i < len(results) - 1 else ""
    return results


LABEL_LINE_RE = re.compile(r"^(#{1,6}\s+\S|(?:\*\*)?\s*(ARTICLE|Article|TITRE|Titre|CHAPITRE|Chapitre|PREAMBULE|Préambule|PRÉAMBULE)\b)")


def clean_md_inline(s):
    """Retire la syntaxe Markdown/Pandoc la plus courante pour l'affichage en
    texte brut dans les résultats de recherche (le texte lui-même n'est pas modifié)."""
    s = re.sub(r"\{\.[a-z]+\}", "", s)            # {.underline}
    s = re.sub(r"\^([^^\s]+)\^", r"\1", s)        # 1^er^ -> 1er
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)  # liens [texte](url)
    s = re.sub(r"[\[\]]", "", s)
    s = s.replace("**", "").replace("__", "")
    s = re.sub(r"(^|\s)[*_]([^*_]+)[*_](?=\s|$|[.,;:])", r"\1\2", s)
    s = re.sub(r"^\s*#{1,6}\s*", "", s)
    s = re.sub(r"^\s*>\s?", "", s, flags=re.M)
    s = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", s, flags=re.M)
    s = re.sub(r"\s*\|\s*", " | ", s)
    s = re.sub(r"(?:\s*\|\s*[-:]{3,}\s*)+\|?", " ", s)
    s = re.sub(r"\\([^\w\s])", r"\1", s)       # d\'organisation -> d'organisation
    s = s.replace("--", "–")
    return re.sub(r"\s+", " ", s).strip(" |")


def build_doc_search_data(entries, path_key, group_key="categorie"):
    """Texte intégral cherchable d'une liste d'entrées du catalogue, découpé en
    paragraphes. path_key est le champ du chemin .md à indexer (chemin_source_md
    pour le texte intégral d'un accord, chemin_resume_md pour un résumé).

    Le bloc de métadonnées en tête de fichier (date, 'converti depuis...') est
    ignoré jusqu'au premier '---'. Retourne (docs, passages) :
      docs     = {id: {titre, categorie/theme, pdf, ocr, n}}
      passages = liste de {a: id, i: idx, l: repère, t: texte}
    Les entrées sans fichier trouvé sont silencieusement ignorées (juste un
    avertissement en console) plutôt que de faire échouer la génération."""
    docs = {}
    passages = []
    for a in entries:
        if group_key == "categorie" and a["categorie"] == "CCN":
            continue
        rel = a.get(path_key)
        if not rel:
            continue
        local_path = os.path.join(DOCS_DIR, rel)
        if not os.path.exists(local_path):
            print(f"ATTENTION : texte introuvable pour la recherche : docs/{rel}")
            continue
        with open(local_path, encoding="utf-8") as f:
            text = f.read()
        lines = text.split("\n")
        head = "\n".join(lines[:15])
        ocr = "OCR" in head
        # saute l'en-tête de métadonnées (titre + liste) jusqu'au premier ---
        for k, l in enumerate(lines[:20]):
            if l.strip() == "---":
                lines = lines[k + 1:]
                break
        body = "\n".join(l for l in lines if not TOC_LINE_RE.search(l))
        paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
        label = ""
        idx = 0
        for p in paras:
            first = p.split("\n")[0].strip()
            cleaned = clean_md_inline(p)
            if len(re.sub(r"[\W\d_]", "", cleaned)) <= 3:
                continue
            if LABEL_LINE_RE.match(first):
                label = clean_md_inline(first)[:90]
            passages.append({"a": a["id"], "i": idx, "l": label, "t": cleaned})
            idx += 1
        docs[a["id"]] = {
            "titre": a["titre"],
            "categorie": a.get(group_key, a["categorie"]),
            "pdf": url_for(pdf_list(a)[0]) if pdf_list(a) else None,
            "ocr": ocr,
            "n": idx,
        }
    return docs, passages


def build_accords_search_data(cat):
    """Texte intégral cherchable de tous les documents du catalogue HORS CCN
    (accords locaux, NAO, DUE, élections). Voir build_doc_search_data."""
    return build_doc_search_data(cat["accords"], "chemin_source_md")


def build_resumes_search_data(entries):
    """Texte intégral cherchable des résumés salariés (un par accord, après
    dédoublonnage). Voir build_doc_search_data."""
    return build_doc_search_data(entries, "chemin_resume_md", group_key="theme")


def build_accord_textes(docs, passages, out_dir):
    """Une page de lecture par document (site/textes/<id>.html), ancre #p<idx>
    sur chaque paragraphe : cible des liens 'Voir dans le texte' des résultats."""
    os.makedirs(os.path.join(out_dir, "textes"), exist_ok=True)
    by_doc = {}
    for p in passages:
        by_doc.setdefault(p["a"], []).append(p)
    for doc_id, d in docs.items():
        html = page_head(d["titre"], "accords.html", base="../")
        pdf = (f'<a href="{esc(d["pdf"])}" target="_blank" rel="noopener">le PDF signé</a>'
               if d["pdf"] else "le PDF signé")
        warn = ""
        if d["ocr"]:
            warn = ('<p class="ccn-empty">⚠️ Texte issu d\'une reconnaissance de caractères (OCR) '
                    'sur un PDF scanné : des mots peuvent être mal transcrits.</p>')
        html += f"""
<section class="page-header">
  <img src="../assets/logo.png" alt="Logo FO ICO" class="page-logo">
  <div>
    <div class="eyebrow-small">ACCUEIL / ACCORDS / {esc(d['categorie'].upper())} / TEXTE</div>
    <h1>{esc(d['titre'])}</h1>
    <p>Texte converti, pour la lecture et la recherche. Pour une citation officielle,
    référez-vous toujours à {pdf}.</p>
  </div>
</section>
<article class="resume-content ccn-texte">
{warn}
"""
        for p in by_doc.get(doc_id, []):
            if p["l"] and p["t"] == p["l"]:
                html += f'<h3 id="p{p["i"]}">{esc(p["t"])}</h3>\n'
            else:
                html += f'<p id="p{p["i"]}">{esc(p["t"])}</p>\n'
        html += """</article>
<script>
// Surligne le terme recherché (?q=...) dans le texte
(function () {
  const q = new URLSearchParams(location.search).get('q');
  if (!q || q.trim().length < 3) return;
  const norm = s => s.toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g, '');
  const terms = norm(q.trim()).split(/\\s+/).filter(w => w.length >= 3);
  document.querySelectorAll('.ccn-texte p, .ccn-texte h3').forEach(el => {
    const txt = el.textContent, nt = norm(txt);
    let marks = [];
    terms.forEach(t => { let i = 0; while ((i = nt.indexOf(t, i)) !== -1) { if (i === 0 || !/[a-z0-9]/.test(nt[i - 1])) marks.push([i, i + t.length]); i += t.length; } });
    if (!marks.length) return;
    marks.sort((a, b) => a[0] - b[0]);
    let out = '', pos = 0;
    const esc = s => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    marks.forEach(([a, b]) => { if (a < pos) return; out += esc(txt.slice(pos, a)) + '<mark>' + esc(txt.slice(a, b)) + '</mark>'; pos = b; });
    el.innerHTML = out + esc(txt.slice(pos));
  });
  if (location.hash) { const t = document.querySelector(location.hash); if (t) t.scrollIntoView(); }
})();
</script>
"""
        html += page_foot(base="../")
        with open(os.path.join(out_dir, "textes", f"{doc_id}.html"), "w", encoding="utf-8") as f:
            f.write(html)


def build_ccn_texte(md_relpath, search_data, out_dir):
    """Page de lecture du texte intégral de la CCN, avec une ancre #p<idx> sur
    chaque passage — cible des liens 'Voir dans la CCN' depuis les résultats de
    recherche. Un seul long fichier, volontairement : la CCN n'a pas de découpage
    fiable en chapitres dans le texte source (cf. note du dépôt)."""
    html = page_head("Texte intégral CCN", "accords.html", base="")
    html += """
<section class="page-header">
  <img src="assets/logo.png" alt="Logo FO ICO" class="page-logo">
  <div>
    <div class="eyebrow-small">ACCUEIL / ACCORDS / CCN / TEXTE</div>
    <h1>CCN — texte intégral</h1>
    <p>Défilement du texte converti, avec repères d'articles indicatifs. Pour une citation officielle,
    référez-vous toujours au PDF signé.</p>
  </div>
</section>
<article class="resume-content ccn-texte">
"""
    for r in search_data:
        html += f'<p id="p{r["idx"]}">{esc(r["text"])}</p>\n'
    html += "</article>\n"
    html += page_foot()
    with open(os.path.join(out_dir, "ccn-texte.html"), "w", encoding="utf-8") as f:
        f.write(html)


def build_ccn(cat, out_dir):
    ccn = next((a for a in cat["accords"] if a["id"] == "ccn-clcc"), None)
    if not ccn:
        return
    search_data = build_ccn_search_data(ccn.get("chemin_source_md") or "ccn/ccn-clcc.md")
    build_ccn_texte(ccn.get("chemin_source_md") or "ccn/ccn-clcc.md", search_data, out_dir)

    html = page_head("Recherche CCN", "accords.html")
    html += f"""
<section class="page-header">
  <img src="assets/logo.png" alt="Logo FO ICO" class="page-logo">
  <div>
    <div class="eyebrow-small">ACCUEIL / ACCORDS / CCN</div>
    <h1>Rechercher dans la CCN</h1>
    <p>Convention collective nationale des CLCC — texte intégral (à jour au 1er février 2026).
    Recherche dans le texte narratif ; pour les grilles de rémunération, utilisez le PDF ou la page dédiée.</p>
  </div>
</section>

<section class="list-page">
  <div class="search-bar small" style="max-width: 640px;">
    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="#5B6578" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"></circle><path d="M21 21l-4.3-4.3"></path></svg>
    <input type="text" id="ccn-search" placeholder="Rechercher un mot, une expression (ex. préavis, congés payés, forfait jours)...">
  </div>
  <p class="note" style="margin: -10px 0 20px;">Découpage automatique en passages à partir du texte converti — les numéros
  d'article affichés sont indicatifs (conversion automatique du PDF, cf. dépôt) ; vérifiez toujours sur le
  <a href="{esc(url_for(ccn.get('chemin_pdf')))}" target="_blank" rel="noopener">PDF signé</a> pour une citation officielle.</p>
  <div id="ccn-count" class="ccn-count"></div>
  <div id="ccn-results" class="ccn-results"></div>
</section>

<script id="ccn-data" type="application/json">{json.dumps(search_data, ensure_ascii=False)}</script>
<script>
const ccnData = JSON.parse(document.getElementById('ccn-data').textContent);
const ccnSearch = document.getElementById('ccn-search');
const ccnResults = document.getElementById('ccn-results');
const ccnCount = document.getElementById('ccn-count');

function norm(s) {{
  return s.toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g, '');
}}
function escapeHtml(s) {{
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}}
function highlightAll(text, terms) {{
  const nt = norm(text);
  let marks = [];
  terms.forEach(t => {{
    let idx = 0;
    while (true) {{
      const found = nt.indexOf(t, idx);
      if (found === -1) break;
      marks.push([found, found + t.length]);
      idx = found + t.length;
    }}
  }});
  if (marks.length === 0) return escapeHtml(text);
  marks.sort((a, b) => a[0] - b[0]);
  const merged = [];
  for (const m of marks) {{
    if (merged.length && m[0] <= merged[merged.length - 1][1]) {{
      merged[merged.length - 1][1] = Math.max(merged[merged.length - 1][1], m[1]);
    }} else {{
      merged.push(m.slice());
    }}
  }}
  let out = '';
  let pos = 0;
  merged.forEach(([s, e]) => {{
    out += escapeHtml(text.slice(pos, s)) + '<mark>' + escapeHtml(text.slice(s, e)) + '</mark>';
    pos = e;
  }});
  out += escapeHtml(text.slice(pos));
  return out;
}}

function runCcnSearch() {{
  const raw = ccnSearch.value.trim();
  if (raw.length < 3) {{
    ccnResults.innerHTML = '';
    ccnCount.innerHTML = raw.length > 0 ? '<span class="note">Tapez au moins 3 caractères.</span>' : '';
    return;
  }}
  const q = norm(raw);
  const words = q.split(/\\s+/).filter(w => w.length >= 2);

  let matches = ccnData.filter(p => norm(p.text).includes(q));
  let mode = 'exact';

  if (matches.length === 0 && words.length > 1) {{
    matches = ccnData.filter(p => {{
      const t = norm(p.text);
      return words.every(w => t.includes(w));
    }});
    mode = 'approx';
  }}

  if (matches.length === 0) {{
    ccnCount.innerHTML = '<div class="ccn-empty">Aucun résultat pour « ' + escapeHtml(raw) + ' ». Essayez avec moins de mots, un seul mot-clé, ou une autre formulation (singulier/pluriel, synonyme).</div>';
    ccnResults.innerHTML = '';
    return;
  }}

  const shown = matches.slice(0, 80);
  let countMsg = shown.length + (shown.length > 1 ? ' passages trouvés' : ' passage trouvé');
  if (mode === 'approx') countMsg += ' — aucune correspondance exacte pour la phrase complète, résultats contenant tous les mots recherchés';
  if (matches.length > 80) countMsg += ' (affichage limité aux 80 premiers sur ' + matches.length + ')';
  ccnCount.innerHTML = '<span class="note">' + countMsg + '</span>';

  const terms = mode === 'exact' ? [q] : words;
  ccnResults.innerHTML = shown.map(p => `
    <div class="ccn-result">
      ${{p.label ? '<span class="ccn-label">' + escapeHtml(p.label) + '</span>' : ''}}
      ${{p.before ? '<p class="ccn-context">…' + escapeHtml(p.before) + '</p>' : ''}}
      <p>${{highlightAll(p.text, terms)}}</p>
      ${{p.after ? '<p class="ccn-context">' + escapeHtml(p.after) + '…</p>' : ''}}
      <a class="ccn-jump" href="ccn-texte.html#p${{p.idx}}">Voir dans la CCN →</a>
    </div>
  `).join('');
}}

ccnSearch.addEventListener('input', runCcnSearch);
ccnSearch.addEventListener('keydown', (e) => {{ if (e.key === 'Enter') {{ e.preventDefault(); runCcnSearch(); }} }});
window.addEventListener('DOMContentLoaded', () => {{ if (ccnSearch.value.trim().length >= 3) runCcnSearch(); }});
</script>
"""
    html += page_foot()
    with open(os.path.join(out_dir, "ccn.html"), "w", encoding="utf-8") as f:
        f.write(html)


def load_depliant_labels():
    """Lit docs/accords-locaux/Depliants_FO/index.md et retourne {nom_fichier: libellé
    réel de la colonne 'Accord'} — pour afficher le vrai intitulé de chaque dépliant
    (ex. 'Non-cadres — travail de nuit') plutôt qu'un numéro générique 1/4, 2/4..."""
    index_path = os.path.join(DOCS_DIR, "accords-locaux", "Depliants_FO", "index.md")
    labels = {}
    if not os.path.exists(index_path):
        return labels
    with open(index_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip().startswith("|") or "---" in line:
                continue
            cols = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cols) < 2:
                continue
            m_file = re.search(r"\]\(([^)]+\.pdf)\)", cols[1])
            if m_file:
                labels[m_file.group(1)] = cols[0]
    return labels


PRINCIPAL_OVERRIDES = {
    "att-cadres-2021": "Aménagement du temps de travail des cadres",
    "att-non-cadres-2020": "Aménagement du temps de travail des non-cadres",
}


def build_depliants(cat, out_dir, res_docs=None, res_passages=None):
    res_docs = res_docs or {}
    res_passages = res_passages or []
    depliant_labels = load_depliant_labels()
    entries = dedup_by_resume(cat["accords"]) + [a for a in cat["accords"] if not a.get("chemin_resume_md")]
    entries = [a for a in entries if a.get("chemin_depliant")]
    entries_sorted = sorted(entries, key=lambda a: (a["theme"], a["titre"]))
    themes = sorted(set(a["theme"] for a in entries_sorted))

    html = page_head("Dépliants", "depliants.html")
    html += """
<section class="page-header">
  <img src="assets/logo.png" alt="Logo FO ICO" class="page-logo">
  <div>
    <div class="eyebrow-small">ACCUEIL / DÉPLIANTS</div>
    <h1>Dépliants</h1>
    <p>Le format tryptique, prêt à imprimer ou à consulter en ligne — un dépliant par accord.</p>
  </div>
</section>
<section class="list-page">
  <div class="search-bar small">
    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="#5B6578" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"></circle><path d="M21 21l-4.3-4.3"></path></svg>
    <input type="text" id="filter-search" placeholder="Rechercher un dépliant ou un mot dans son texte...">
  </div>
  <div class="chips" id="theme-chips">
    <span class="chip active" data-theme="all">Tous</span>
"""
    for t in themes:
        _, t_fg = THEME_COLORS.get(t, ("#F4F6F9", "#5B6578"))
        html += f'    <span class="chip" data-theme="{esc(t)}" style="--chip-color:{t_fg}">{esc(t)}</span>\n'
    html += """  </div>
  <div id="leaflet-empty" class="ccn-empty" style="display:none;"></div>
  <div id="leaflet-text-section" style="display:none; margin-bottom: 18px;">
    <div style="display:flex; align-items:center; gap:14px; margin-bottom:8px;">
      <span class="bar"></span>
      <h2 style="margin:0; font-size:16px; font-weight:700; color:var(--marine);">Dans le texte des dépliants</h2>
    </div>
    <div id="leaflet-hits" class="ccn-count"></div>
  </div>
  <div class="leaflet-grid" id="leaflet-grid">
"""
    current_theme = None
    for a in entries_sorted:
        if a["theme"] != current_theme:
            current_theme = a["theme"]
            t_bg, t_fg = THEME_COLORS.get(current_theme, ("#F4F6F9", "#5B6578"))
            html += f'    <div class="doc-group-label full-row" data-theme="{esc(current_theme)}" style="color:{t_fg};background:{t_bg};">{esc(current_theme)}</div>\n'

        dep = a["chemin_depliant"]
        dep_list = dep if isinstance(dep, list) else [dep]
        theme_bg, theme_fg = THEME_COLORS.get(a["theme"], ("#F4F6F9", "#5B6578"))

        for i, d in enumerate(dep_list):
            filename = os.path.basename(d)
            real_label = depliant_labels.get(filename, a["titre"])
            if " — " in real_label:
                prefix, secondaire = real_label.split(" — ", 1)
            else:
                prefix, secondaire = real_label, ""
            principal = PRINCIPAL_OVERRIDES.get(a["id"], prefix)
            secondaire = secondaire[:1].upper() + secondaire[1:] if secondaire else ""

            counter = f'<span class="leaflet-counter">{i + 1}/{len(dep_list)}</span>' if len(dep_list) > 1 else ""
            dep_url = url_for(d)
            html += f"""    <a class="leaflet-card" data-id="{esc(a['id'])}" data-title="{esc(real_label.lower())}" data-theme="{esc(a['theme'])}" href="{esc(dep_url)}" target="_blank" rel="noopener">
      <div class="leaflet-cover">
        <div class="leaflet-top">
          <div class="leaflet-top-left">
            <span class="leaflet-eyebrow">Accord local ICO</span>
            <span class="leaflet-theme-tag" style="background:{theme_bg};color:{theme_fg}">{esc(a['theme'])}</span>
          </div>
          {counter}
        </div>
        <div class="leaflet-title-block">
          <span class="leaflet-title-main">{esc(principal)}</span>
          {f'<span class="leaflet-title-sub">{esc(secondaire)}</span>' if secondaire else ''}
        </div>
        <span class="leaflet-slogan"><span class="red">FO</span>, vos droits notre priorité</span>
      </div>
      <span class="leaflet-caption">Télécharger le PDF →</span>
    </a>
"""
    html += "  </div>\n"
    html += """
</section>
<script id="dep-res-data" type="application/json">""" + json.dumps(res_passages, ensure_ascii=False).replace("</", "<\\/") + """</script>
<script>
const depResData = JSON.parse(document.getElementById('dep-res-data').textContent);
const themeChips = document.querySelectorAll('#theme-chips .chip');
const leafletCards = document.querySelectorAll('.leaflet-card');
const leafletLabels = document.querySelectorAll('#leaflet-grid .doc-group-label');
const search = document.getElementById('filter-search');
const leafletEmpty = document.getElementById('leaflet-empty');
const leafletHits = document.getElementById('leaflet-hits');
let activeTheme = 'all';

function norm(s) { return s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, ''); }
function atWordStart(nt, i) { return i === 0 || !/[a-z0-9]/.test(nt[i - 1]); }
function hasTerm(nt, t) { let i = 0; while ((i = nt.indexOf(t, i)) !== -1) { if (atWordStart(nt, i)) return true; i += 1; } return false; }
depResData.forEach(p => { p.n = norm(p.t); });

let lastAccMsg = '';
function textHits(raw) {
  const hits = new Set();
  lastAccMsg = '';
  if (raw.trim().length < 3) return hits;
  const q = norm(raw.trim());
  const words = q.split(/\s+/).filter(w => w.length >= 2);
  let matches = depResData.filter(p => hasTerm(p.n, q));
  if (matches.length === 0 && words.length > 1) matches = depResData.filter(p => words.every(w => hasTerm(p.n, w)));
  matches.forEach(p => hits.add(p.a));
  if (matches.length) lastAccMsg = matches.length + (matches.length > 1 ? ' passages' : ' passage') + ' dans ' + hits.size + (hits.size > 1 ? ' documents' : ' document');
  return hits;
}

function applyFilters() {
  const raw = search.value.trim();
  const nq = norm(raw);
  const hits = textHits(raw);
  leafletCards.forEach(card => {
    const themeOk = activeTheme === 'all' || card.dataset.theme === activeTheme;
    const qOk = !raw || norm(card.dataset.title).includes(nq) || hits.has(card.dataset.id);
    card.style.display = (themeOk && qOk) ? 'inline-flex' : 'none';
  });
  leafletLabels.forEach(label => {
    const hasVisible = Array.from(leafletCards).some(card => card.dataset.theme === label.dataset.theme && card.style.display !== 'none');
    label.style.display = hasVisible ? 'block' : 'none';
  });
  const anyVisible = Array.from(leafletCards).some(c => c.style.display !== 'none');
  leafletEmpty.style.display = (raw && !anyVisible) ? 'block' : 'none';
  leafletEmpty.textContent = (raw && !anyVisible) ? 'Aucun dépliant ne contient « ' + raw + ' », ni dans son titre ni dans le texte du résumé associé.' : '';
  document.getElementById('leaflet-text-section').style.display = (raw && lastAccMsg) ? 'block' : 'none';
  leafletHits.innerHTML = lastAccMsg ? '<span class="note">' + lastAccMsg + '</span>' : '';
}
search.addEventListener('input', applyFilters);
themeChips.forEach(c => c.addEventListener('click', () => {
  themeChips.forEach(x => x.classList.remove('active'));
  c.classList.add('active');
  activeTheme = c.dataset.theme;
  applyFilters();
}));
</script>
"""
    html += page_foot()
    with open(os.path.join(out_dir, "depliants.html"), "w", encoding="utf-8") as f:
        f.write(html)


def main():
    if not os.path.exists(CATALOGUE_PATH):
        sys.exit(f"Catalogue introuvable : {CATALOGUE_PATH}")
    if not os.path.isdir(DOCS_DIR):
        sys.exit(f"Dossier docs/ introuvable à {DOCS_DIR} — lancez ce script depuis la racine du dépôt.")

    cat = load_catalogue()

    if os.path.exists(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    os.makedirs(os.path.join(OUT_DIR, "assets"))

    logo_src = os.path.join(ASSETS_SRC, "logo.png")
    if os.path.exists(logo_src):
        shutil.copy(logo_src, os.path.join(OUT_DIR, "assets", "logo.png"))
    else:
        print(f"ATTENTION : logo introuvable à {logo_src} — copiez-le manuellement dans site/assets/logo.png")

    favicon_src = os.path.join(ASSETS_SRC, "favicon.png")
    if os.path.exists(favicon_src):
        shutil.copy(favicon_src, os.path.join(OUT_DIR, "assets", "favicon.png"))
    else:
        print(f"ATTENTION : favicon introuvable à {favicon_src} — copiez-le manuellement dans site/assets/favicon.png")

    style_src = os.path.join(ASSETS_SRC, "style.css")
    shutil.copy(style_src, os.path.join(OUT_DIR, "assets", "style.css"))

    build_index(cat, OUT_DIR)
    build_situation_page(cat, OUT_DIR)
    acc_docs, acc_passages = build_accords_search_data(cat)
    build_accords(cat, OUT_DIR, acc_docs, acc_passages)
    build_accord_textes(acc_docs, acc_passages, OUT_DIR)
    build_ccn(cat, OUT_DIR)
    res_docs, res_passages = build_resumes_search_data(dedup_by_resume(cat["accords"]))
    build_resumes(cat, OUT_DIR, res_docs, res_passages)
    build_resume_pages(cat, OUT_DIR)
    build_depliants(cat, OUT_DIR, res_docs, res_passages)

    print(f"Site généré dans {OUT_DIR} ({len(cat['accords'])} accords).")


if __name__ == "__main__":
    main()
