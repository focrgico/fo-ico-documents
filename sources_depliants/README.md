# Sources des dépliants FO ICO

Gabarit reconstruit le 20/10/2026 à partir des PDF publiés (mesures sur `Depliant_teletravail_FO.pdf` et `Depliant_interessement_FO.pdf`) et des règles du projet, après la perte des sources HTML d'origine. Il remplace ces sources : on modifie un fichier de données, on relance, on obtient le PDF.

## Contenu du dossier

| Élément | Rôle |
|---|---|
| `depliant.css` | Mise en page commune : volets, couleurs, polices, encadrés, pastilles. Tout est en points. |
| `construire_depliant.py` | Lit un fichier de `donnees/`, écrit l'HTML et le PDF (Chromium), puis contrôle le résultat. |
| `donnees/*.json` | Un fichier par dépliant : textes, chiffre clé, pastilles, source, contenu des trois colonnes du verso. |
| `pictos/*.svg` | Pictogrammes. Ceux de Télétravail et d'Intéressement sont repris des PDF publiés. |
| `polices/` | Poppins (Regular, Medium, Bold) et Carlito (Regular, Bold, Italic, Bold Italic). Licence SIL OFL. |
| `assets/logo.png` | Logo FO ICO (copie de `assets_src/logo.png`). |
| `outils/extraire_picto_depuis_pdf.py` | Copie une zone d'un PDF existant en SVG, pour récupérer un pictogramme. |
| `sortie/` | Résultats générés (non versionnés). |

## Utilisation

Prérequis : Python 3, `pip install playwright pymupdf`, puis `playwright install chromium`. Les polices sont dans le dossier, rien à installer sur le poste. Il faut aussi `pdffonts` (paquet poppler) pour le contrôle des polices.

```
cd sources_depliants
python3 construire_depliant.py donnees/teletravail.json --verifier
python3 construire_depliant.py --tous --verifier
```

Le PDF est écrit dans `sortie/`. Pour l'utiliser, le copier dans `docs/accords-locaux/Depliants_FO/` en gardant le nom du fichier existant.

Le contrôle (`--verifier`) vérifie : 2 pages exactement, mention « Résumé établi par vos élus FO à l'ICO » présente, tous les liens sont des adresses web (http ou https), aucun texte hors page, polices Poppins et Carlito incorporées.

## Écrire un nouveau dépliant

1. Copier `donnees/teletravail.json` sous un autre nom et remplacer les textes.
2. Le contenu du verso est une liste de 3 colonnes. Blocs possibles : `section`, `p`, `puces`, `encadre` (style `neutre` ou `alerte`), `picto`, `tableau`.
3. Balisage dans les textes : `**gras**`, `{ref:Art. 7.2}` pour une référence d'article, `^er^` pour un exposant. Une espace insécable est ajoutée avant `?`, `!` et `;`.
4. Le lien « accord complet (PDF) » se renseigne par `"pdf": "accords-locaux/<nom du PDF signé>.pdf"`, tel que dans `chemin_pdf` du catalogue. Le gabarit en fait une adresse GitHub.
5. Pictogramme : prendre un SVG de `pictos/` ou en extraire un d'un PDF avec l'outil. Les espaces autour se règlent bloc par bloc : `avant` (au-dessus), `ecart` (entre le picto et sa légende), `apres` (en dessous), `decalage_x`.
6. Un paragraphe en corps réduit : `"taille": 10.5`. Un titre d'encadré en 12,5 pt : `"titre_grand": true`.

## Ce qui est mesuré et ce qui ne l'est pas

Mesuré sur les PDF publiés : largeurs des volets, couleurs, polices et tailles, positions des titres, encadrés, filets, pastilles, source, pied de page. Sur les deux dépliants de contrôle, aucun texte ne s'écarte de plus de 1,6 pt de sa position dans le PDF publié, et les retours à la ligne sont identiques. Chromium arrondit au pixel : on ne vise pas le pixel exact.

Non mesuré ou non couvert :

- Tableaux : style proposé, jamais comparé à un PDF publié.
- Couverture avec un encadré « Source » à la place du chiffre clé (cas prévu par le gabarit Word du 20/09/2026) : pas dans ce gabarit, je n'ai pas vérifié si un dépliant publié l'utilise.
- Plusieurs chiffres clés sur la couverture.
- Prévoyance AXA et Assistances AXA : leur structure de pages est différente des 30 autres, elles ne se génèrent pas avec ce gabarit.
- Les pictogrammes des 28 autres dépliants : à extraire des PDF publiés au fur et à mesure.

## Écarts entre les notes du projet et les PDF publiés

Le gabarit suit les PDF, qui sont ce qui est imprimé. Sont en désaccord avec les notes :

- Volet central du verso : gris clair `#F4F6F9` dans les 30 PDF de ce type, alors que `Regles du projet FO ICO` le donne blanc.
- Largeurs du verso : 280,5 / 280,5 / 280,9 pt dans les PDF, alors que les notes donnent 282,42 / 282,0 / 277,5.
- Interligne du texte courant : 14,25 pt pour 11,5 pt (mesuré), alors que les notes donnent 17,25 pt.
- Les PDF publiés arrêtent la barre du slogan à 837 pt, ce qui laisse une bande blanche de 5 pt à droite de la page. Le gabarit la prolonge jusqu'au bord.
- Pas d'espace insécable avant « : », comme dans les PDF publiés (les deux-points peuvent donc tomber en début de ligne).
