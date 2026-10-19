⚠️ Dossier temporaire — pas intégré au site ni au catalogue

Ce dossier contient les résumés et dépliants des 4 nouveaux accords ajoutés le 19/10/2026 :

- Plan d'Épargne d'Entreprise (PEE, 2019)
- Avenant indemnité de restauration (2016)
- Don de jours de repos non pris (2015)
- DUE — Charte sur le droit à la déconnexion (2018)

Les 4 PDF signés source sont scannés (pas de version Word retrouvée pour l'instant) : les résumés et dépliants ci-dessous ont donc été rédigés à partir d'une transcription OCR relue visuellement, et non du texte natif du document. C'est pourquoi ils restent ici plutôt que d'être poussés dans `resumes-accords-locaux/` et `Depliants_FO/` avec les autres.

**À faire une fois le Word retrouvé pour chaque accord :**
1. Revérifier le résumé et le dépliant correspondants contre le texte Word (en particulier les points déjà signalés ci-dessous)
2. Déplacer le `.md` vers `docs/accords-locaux/resumes-accords-locaux/` (en ajoutant l'entrée dans `index.md`) et le `.pdf` vers `docs/accords-locaux/Depliants_FO/`
3. Mettre à jour `chemin_resume_md` et `chemin_depliant` dans `catalogue/catalogue.json` pour l'accord concerné
4. Reconstruire le site (`build_site.py`)

**Points déjà signalés à vérifier en priorité sur le Word :**
- **PEE** : l'article 2 du règlement renvoie à un « abondement » défini à l'article 3, mais l'article 3 ne décrit que la prise en charge des frais de tenue de compte — aucun montant d'abondement n'est chiffré. À clarifier.
- **Avenant indemnité de restauration** : le montant de l'indemnité n'est pas dans cet avenant — il doit figurer dans l'accord de base du 19/12/2013, non retrouvé à ce jour. Le résumé et le dépliant le signalent explicitement plutôt que d'inventer un montant. La transcription OCR passe aussi directement de l'Article 2 à l'Article 4 (pas d'Article 3 identifié) — à vérifier.
- **Don de jours de repos** : l'en-tête de chaque page du PDF porte « Projet accord - 19 novembre 2014 » alors que le document est signé et daté du 9 janvier 2015 — probablement un en-tête de modèle non mis à jour, sans incidence apparente.

Les dépliants ont été générés avec un gabarit HTML/CSS reconstruit par inspection visuelle des dépliants déjà en production (`docs/accords-locaux/Depliants_FO/`), le script d'origine n'étant pas dans le dépôt. Même structure à 6 volets (pli lettre), mêmes couleurs et polices (Baloo 2 / Nunito).
