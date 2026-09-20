# Synthèse de session — Site web FO ICO (phase 4)

*Compilée le 20/09/2026, à partir de l'ensemble de la conversation.*

---

## 1. Décisions validées par David

| Décision | Contexte |
|---|---|
| Site **sur mesure en HTML/CSS**, pas MkDocs | Choisi explicitement plutôt que d'étendre l'outil existant |
| Hébergement prévu : **GitHub Pages**, branche `gh-pages` dédiée | Via `git subtree push --prefix site origin gh-pages` |
| Structure retenue : Accueil / Accords / Résumés / Dépliants + recherche | « Ma situation » retiré du menu (redondant avec la section du même nom sur l'accueil) |
| Le **catalogue de métadonnées est régénéré depuis le dépôt réel à chaque session**, jamais depuis une version mémorisée | Pour éviter toute divergence avec une édition manuelle |
| Palette et typographie : reprise du gabarit dépliant validé le 20/09/2026 (marine `#14203A`, rouge `#C1121F`, or `#B08D57`, Calibri) | Cohérence avec les dépliants FO déjà produits |

---

## 2. Le logo

- Fichier source : `Logo_FO_avec_ombre.png` (projet), fond blanc opaque, pas transparent à l'origine.
- **Détourage final retenu** : fond blanc retiré, ombre d'origine conservée mais rendue semi-transparente (dégradé d'opacité selon l'assombrissement, pas une suppression totale) — épouse exactement les coins arrondis du badge, sans résidu ni décalage.
- Méthode : détection par saturation des couleurs (chroma), pas par luminosité seule — la première méthode « mangeait » les reflets clairs du liseré doré et laissait des îlots gris déconnectés dans les coins.

---

## 3. Le catalogue de métadonnées (`catalogue/catalogue.json`)

- **33 accords recensés**, reconstruits à chaque vérification depuis le dépôt GitHub réel (pas depuis la mémoire).
- Champs par accord : catégorie, thème, année, chemin PDF, chemin résumé Markdown, chemin dépliant(s), tags `statut` / `site` / `modalite_horaire` / `temps_travail`.
- **Les tags de filtre restent volontairement vides** pour la quasi-totalité des accords : ils n'ont pas été déduits du contenu juridique de chaque texte (non relu article par article). Seuls quelques cas où le titre même de l'accord le rend certain sont renseignés (ex. « ATT cadres » → cadre).

### Corrections apportées pendant la session (vérifications, pas suppositions)
- **Chèques syndicaux vs Financement syndical** : correction d'une hypothèse erronée — c'est *Chèques syndicaux* (3 octobre 2022, 4 organisations signataires) qui est **en vigueur** ; *Financement syndical* (27 avril 2021) est l'accord antérieur, déjà archivé. C'est l'inverse de ce qui avait été supposé au départ.
- **Acquisition de CP pendant arrêt maladie (cadres et non-cadres)** : rattachées aux résumés ATT Cadres / ATT Non-Cadres existants, pas de résumé séparé.
- **Dépliant « Prime de pool de remplacement »** : vérifié en lisant le PDF — couvre bien les deux décisions unilatérales du 22/04/2024 (assistantes médicales **et** aides-soignants/IDE), pas seulement la version AM comme l'index du dépôt le laissait penser. Index corrigé en conséquence.
- **Accents/encodage dans les noms de fichiers GitHub** : vérifié non corrompus (le `#U00e9` observé venait de l'outil d'extraction local, pas du dépôt).

### Nettoyage du dépôt effectué (confirmé en ligne par vous)
- **14 fichiers `.md` en double** supprimés (identiques à leur copie déjà présente dans `archive-accords-locaux/`) : 3 repérés d'abord, puis 4 de plus trouvés dans `nao/` lors d'un balayage exhaustif du dépôt entier.
- Volontairement **conservé** : `nao/NAO 2026 _PV de desaccord signe.md` — document NAO actif, malgré l'absence de PDF à cet endroit.
- `Depliants_FO/index.md` : tableau cassé par une ligne vide corrigé ; ligne manquante (dépliant pool AS/IDE) ajoutée.

### Points encore ouverts dans le catalogue
- Tags « Ma situation » à compléter accord par accord (site, modalité horaire, temps de travail — quasiment tous vides).
- **Chèques syndicaux** : toujours sans résumé rédigé.
- Incohérences PDF déjà signalées, non résolues : ATT Cadres (pas de PDF de base), CET (3ᵉ fichier `Accord CET_vDéfinitive.pdf` sans `.md`), VAP (lien exact avec son avenant 2025 incertain), Forfait Mobilité Durable (PDF en ligne = version 2024, pas 2025), Prime USC (avenant 26/04/2024 sans Word reçu).

---

## 4. Le site généré (`build_site.py` + `assets_src/`)

Script Python qui lit `catalogue/catalogue.json` et le dossier `docs/` en local, et génère un dossier `site/` autonome.

**Pages produites :**
- `index.html` — accueil : logo, recherche, 3 cartes Accords/Résumés/Dépliants, bloc « Ma situation » (filtres réels par statut/site/modalité/temps, non encore concluants tant que les tags ne sont pas remplis). Tient sur un écran sans défilement (testé à 900 px et au-delà).
- `accords.html` — liste complète des 33 accords (toujours visible en entier, quelle que soit la recherche), filtrable par catégorie (couleurs désormais distinctes par catégorie), **recherche unifiée** : cherche à la fois dans les titres des accords et dans le texte intégral de la CCN, résultats CCN affichés directement sur la même page avec contexte (passage précédent/suivant) et lien vers l'emplacement exact.
- `resumes.html` + une page par résumé (`resumes/<id>.html`) — texte intégral converti depuis le Markdown source, avec téléchargements en bas (résumé, dépliant, PDF de l'accord).
- `depliants.html` — galerie des dépliants existants, liens directs vers les PDF sur GitHub.
- `ccn.html` — page de recherche dédiée dans la CCN (texte intégral, ~7200 passages indexés), avec repli automatique sur une recherche par mots séparés si la phrase exacte ne trouve rien.
- `ccn-texte.html` — texte intégral de la CCN, une ancre par passage, cible des liens « Voir dans la CCN ».

**Fonctionnement technique :**
- Aucun fichier dupliqué : les PDF (accords, dépliants) restent liés directement vers `raw.githubusercontent.com` ; seuls les résumés et le texte de la CCN sont lus et convertis localement à la génération.
- Recherche entièrement côté navigateur (JavaScript), sans serveur.
- Toutes les fonctionnalités interactives ont été testées avec Node.js/jsdom (exécution réelle du code produit, pas une simple relecture) avant chaque livraison.

**Pour republier après une mise à jour :**
```bash
python3 build_site.py
git add site/ catalogue/ build_site.py assets_src/
git commit -m "Mise a jour du site"
git push
git subtree push --prefix site origin gh-pages
```

---

## 5. Reste à faire (connu, pas caché)

1. Compléter les tags « Ma situation » (statut/site/modalité horaire/temps de travail) accord par accord — condition pour que le filtre de l'accueil devienne réellement utile.
2. Rédiger le résumé de Chèques syndicaux.
3. Trancher les incohérences PDF listées en section 3.
4. Mettre en ligne le site (configuration GitHub Pages sur la branche `gh-pages`), jamais fait dans cette session — seule la génération locale a été testée.
5. Décider si une version Word des résumés doit être produite (mentionnée dans le projet initial, pas encore traitée).
