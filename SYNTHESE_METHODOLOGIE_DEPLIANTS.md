# Synthèse — Méthodologie dépliants, résumés, site (FO ICO)

*Compilée le 21/09/2026, après plusieurs sessions de production et de correction.*

---

## 1. Dépliants (tryptiques PDF)

### L'outil qui marche : Playwright + Chromium réel

**Jamais** wkhtmltopdf ni WeasyPrint pour ce projet : les deux produisent des PDF structurellement valides (dimensions correctes, vérifiables), mais qu'Adobe Reader affiche mal (contenu tassé en haut de page, blanc en dessous) — défaut invisible avec d'autres outils de vérification (poppler/pdftoppm), donc facile à rater. Le fichier de référence (`Depliant_teletravail_FO.pdf`, dans les fichiers projet) a été produit avec un vrai Chromium (Creator: Chromium, Producer: Skia/PDF) — c'est la preuve qu'il faut viser.

**Script validé, à réutiliser tel quel** (fichier `render2f.py` joint) :
```python
from playwright.sync_api import sync_playwright
import pathlib, sys
src, out = sys.argv[1], sys.argv[2]
url = pathlib.Path(src).resolve().as_uri()
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1123, "height": 794})
    pg.goto(url)
    pg.wait_for_timeout(1000)
    pg.pdf(path=out, width="297mm", height="210mm", print_background=True,
           margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
    b.close()
```
Usage : `python3 render2f.py mon_depliant.html Depliant_sortie.pdf`

Deux détails non négociables dans ce script :
- **`viewport={"width": 1123, "height": 794}`** (≈ A4 à 96 dpi) fixé *avant* le chargement de la page — sans ça, les unités `mm` du CSS peuvent se résoudre différemment de la taille de page PDF réellement demandée.
- **`wait_for_timeout(1000)`** après `goto()` — laisse le temps aux images externes (le logo notamment) de finir de charger avant la capture. Sans cette pause, une image encore en cours de chargement peut être figée avec de mauvaises proportions au moment du rendu PDF.

Vérification systématique une fois le PDF produit : `pdfinfo` (Creator/Producer/Pages/Page size) doit correspondre au fichier de référence, et une comparaison visuelle directe (capture recadrée du logo, référence vs nouveau, empilées) plutôt qu'un simple coup d'œil au rendu complet.

### Piège CSS à connaître : flexbox étire les images

Si le logo (ou toute image) est un enfant direct d'un conteneur `display: flex; flex-direction: column`, le comportement par défaut (`align-items: stretch`) **étire sa largeur pour remplir le conteneur**, même avec `width: auto` sur l'image — ce qui ne se voit pas en testant l'image seule hors de ce conteneur. Toujours ajouter explicitement `align-self: flex-start;` (ou `center`) sur l'image du logo pour neutraliser cet étirement.

### Couleurs exactes (extraites pixel par pixel du fichier de référence)

À utiliser en priorité sur les valeurs du gabarit Markdown, qui sont approximatives :

| Élément | Couleur |
|---|---|
| Fond volet couverture (marine) | `#1B1F36` |
| Filet vertical + puces rouges | `#B91421` |
| Fond volets intérieurs | `#FDFDFD` |
| Fond des encadrés | `#F5F6F9` |

### Format et structure (gabarit validé, ne pas modifier sans accord explicite)

- A4 paysage 297×210 mm, marges de page 12 mm haut/bas, 0 mm gauche/droite
- 6 volets : recto 99,5 / 99,5 / 98 mm — verso 98 / 99,5 / 99,5 mm (le volet qui se replie à l'intérieur est le plus étroit)
- Marges de cellule : 13 mm en haut, 9 mm côté pli, 12 mm côté bord de feuille
- Logo : haut gauche du panneau sombre, hauteur 29 mm, **fichier transparent sans fond blanc** (ombre conservée en semi-transparence), jamais de contour ni de pastille autour
- Calibri partout — 23 pt titre de couverture, 14,5 pt titres de section, 11,5 pt texte courant, 10,5 pt encadrés, 8,5 pt références d'articles, 7 pt bloc Source
- Structure des 6 volets : **1** couverture (logo, titre, encadré Source *ou* chiffre clé, bandeau slogan) — **2** dos (« Vos élus FO à l'ICO » + encadré « Une question ? », sans nom ni fonction de délégué) — **3** « Qui est concerné ? » (fond marine) — **4 à 6** contenu (filet rouge à gauche des titres, puces rondes rouges, étapes numérotées cerclées)
- Slogan couverture : « FO » en rouge vif `#FF0000`, la virgule et la suite en blanc

### Règles de contenu

- Toujours commencer par « Qui est concerné ? »
- Jamais de contexte historique, de contentieux ni de grève ; ne pas définir les termes évidents pour un salarié
- La source (date, signataires) se cite **une seule fois** dans le dépliant
- Un tableau du résumé devient un vrai tableau dans le dépliant, jamais de la prose
- Les colonnes/panneaux colorés vont jusqu'en bas de la page même si le contenu est court
- Un dépliant tient sur un seul jeu de 6 volets ; au-delà, plusieurs dépliants séparés et autonomes plutôt qu'un format multi-pages qui casserait le pliage

---

## 2. Résumés (texte source des dépliants)

- Toujours la **version la plus récente** d'un accord ; si un avenant modifie l'accord de base, ses nouveautés sont intégrées directement dans le résumé de l'accord de base (référence à l'article de l'avenant ET de l'accord), **pas de résumé séparé** pour l'avenant
- Exception confirmée : les **PV de désaccord NAO** ne suivent pas cette règle — chaque année reste un document à part, avec son propre résumé (ce ne sont pas des avenants à un accord de base)
- Chaque référence à la CCN dans un résumé doit citer l'article correspondant de la CCN
- **Pas de liens cliquables en dur** dans le texte des résumés — ils citent seulement les références (n° d'article) ; les liens sont gérés par le site
- Si un accord passe « plus en vigueur » et part en archive, son résumé est retiré (remplacé par celui de la version en vigueur si elle existe, sinon simplement supprimé)

---

## 3. Site (build_site.py)

- Génère un site statique HTML depuis `catalogue/catalogue.json` + `docs/` — jamais de contenu écrit à la main dans le HTML généré
- Convertit aussi chaque résumé en `.docx` à la volée (à partir du même HTML que la page web, pas d'un second fichier à maintenir)
- Recherche plein texte dans la CCN intégrée à la page Accords
- Catégories et thèmes colorés (`CATEGORY_COLORS`, `THEME_COLORS` dans `build_site.py`) — toujours dérivés de la charte FO (marine/rouge/or), jamais de teinte hors charte sans validation

---

## 4. Erreurs récurrentes à ne pas reproduire

- **Toujours remplacer un fichier livré à son emplacement cible** — ne jamais l'ajouter sous son nom de téléchargement à côté (cause récurrente de fichiers fantômes et de catalogue pointant vers l'ancienne version)
- **Toujours revérifier le dépôt réel** (retélécharger l'archive GitHub) avant de conclure qu'une action a réussi — ne jamais se fier à un « c'est bon » sans un contrôle direct
- **Noms de fichiers accentués** : dans un script bash, utiliser des motifs génériques (`*interg*2023*.pdf`) plutôt que des noms exacts codés en dur — un `git mv` sur un nom accentué tapé à la main échoue souvent silencieusement (problème d'encodage entre ce que je tape et le nom réel du fichier), et avec `set -e` ça arrête tout le script sans prévenir sur ce qui suit
- **Ne jamais valider une mise en page seulement par un rendu que je génère moi-même** — comparer numériquement (mesure de ratio, dimensions) contre le fichier de référence quand un doute existe, pas seulement à l'œil
