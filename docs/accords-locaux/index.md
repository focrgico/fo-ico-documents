# Accords collectifs locaux ICO

Chaque accord existe en deux formats dans ce dossier :
- **`.md`** — texte lisible et cherchable (converti depuis la version Word de travail définitive avant signature)
- **`.pdf`** — version scannée signée, preuve juridique de référence

## Accords disponibles (41, par ordre chronologique)

| Accord | Signature | Fichier |
|---|---|---|
| Durée et ATT — Non Cadre | 14/09/2020 | `accord-duree-att-non-cadres-2020.md` |
| CET (Compte Épargne Temps) | 19/03/2021 | `accord-cet-2021.md` |
| PERCOL (Épargne Retraite Collective) | 19/03/2021 | `accord-percol-2021.md` |
| Financement syndical | 27/04/2021 | `accord-financement-syndical-2021.md` |
| Télétravail | 27/04/2021 | `accord-teletravail-2021.md` |
| Durée et ATT — Cadres | 12/05/2021 | `accord-duree-att-cadres-2021.md` |
| Intergénérationnel — Avenant (temps partiel senior) | 30/06/2021 | `accord-intergenerationnel-avenant1-2021.md` |
| CDD à objet défini | 13/08/2021 | `accord-cdd-objet-defini-2021.md` |
| Avenant n°1 — Durée/ATT Non Cadre (CET heures sup.) | 31/01/2022 | `accord-duree-att-non-cadres-avenant1-2022.md` |
| Avenant n°1 — CET | 31/01/2022 | `accord-cet-avenant1-2022.md` |
| Parcours Physiciens médicaux | 19/05/2022 | `accord-physiciens-medicaux-2022.md` |
| PVA (Part Variable Additionnelle — praticiens) | 19/05/2022 | `accord-pva-2022.md` |
| Reprise d'ancienneté MER/IDE/AS | 19/05/2022 | `accord-reprise-anciennete-mer-ide-as-2022.md` |
| Chèques syndicaux | 03/10/2022 | `accord-cheques-syndicaux-2022.md` |
| Vote électronique (cycle 2022) | 12/10/2022 | `accord-vote-electronique-2022.md` |
| Prime chaussures | 21/06/2023 | `accord-prime-chaussures-2023.md` |
| Égalité F/H (2023) | 26/05/2023 | `accord-egalite-fh-2023.md` |
| Dialogue social (2023) | 26/05/2023 | `accord-dialogue-social-2023.md` |
| Intergénérationnel — Avenant (fin de carrière) | 15/09/2023 | `accord-intergenerationnel-avenant-2023.md` |
| Égalité F/H — Avenant | 15/12/2023 | `accord-egalite-fh-avenant-2023.md` |
| Accord de méthode NAO 2024 | 10/11/2023 | `accord-methode-nao-2024.md` |
| Prime USC | 01/12/2023 | `accord-prime-usc-2023.md` |
| Compteur intermédiaire — personnel non posté | 23/03/2024 | `accord-compteur-intermediaire-non-postes-2024.md` |
| Intéressement 2024 | 26/04/2024 | `accord-interessement-2024.md` |
| Supplément d'intéressement — exercice 2023 | 26/04/2024 | `accord-supplement-interessement-2023.md` |
| Compteur intermédiaire — personnel posté | 21/06/2024 | `accord-compteur-intermediaire-salaries-postes-2024.md` |
| Validation des Acquis Professionnels (VAP) | 25/02/2025 | `accord-vap-2025.md` |
| Répartition de la BIC | 11/03/2025 | `accord-repartition-bic-2025.md` |
| Parcours professionnel Assistant Médical | 11/03/2025 | `accord-parcours-am-2025.md` |
| Parcours professionnel IDE et MER | 28/03/2025 | `accord-parcours-ide-mer-2025.md` |
| Intéressement 2025 | 17/04/2025 | `accord-interessement-2025.md` |
| Accord de méthode NAO 2025 | 28/05/2025 | `accord-methode-nao-2025.md` |
| Acquisition CP sur maladie — Non Cadres | 31/12/2025 | `accord-acquisition-cp-maladie-non-cadres-2025.md` |
| Acquisition CP sur maladie — Cadres | 31/12/2025 | `accord-acquisition-cp-maladie-cadres-2025.md` |
| Forfait Mobilité Durable — version en vigueur | 24/10/2025 | `accord-forfait-mobilite-durable-2025.md` |
| Accord de méthode NAO 2026 | 22/01/2026 | `accord-methode-nao-2026.md` |
| Dialogue social 2026 | 13/03/2026 | `accord-dialogue-social-2026.md` |
| Congé humanitaire | 31/03/2026 | `accord-conge-humanitaire-2026.md` |
| Personnel de nuit (maintien compétences) | 19/05/2026 | `accord-nuit-2026.md` |
| Égalité Femmes-Hommes (2026) | 29/05/2026 | `accord-egalite-fh-2026.md` |
| Intéressement 2026 | 29/05/2026 | `accord-interessement-2026.md` |

*21ᵉ accord du tout premier lot (thème encore inconnu) toujours en attente.*

## Encore manquants

| Accord | Statut |
|---|---|
| Avenant accord d'intéressement 2025 | David va vérifier — rappel demandé |
| Avenant accord prime USC | David va vérifier — rappel demandé |
| Supplément d'intéressement — exercice 2025 | David va vérifier — rappel demandé |
| DUE Parcours techs de laboratoire-macroscopie | À demander séparément, fourniture ultérieure |
| DUE Prime de retour inopiné | À demander séparément, fourniture ultérieure |

## Nommage des fichiers

`accord-[theme]-[annee].md` — un avenant se nomme `accord-[theme]-avenant[n]-[annee].md`.

## Ajouter un accord

1. Convertir le Word en Markdown (`pandoc -t markdown fichier.docx -o fichier.md`) si le Word d'origine est disponible ; sinon OCR sur le PDF scanné, à relire.
2. Créer le fichier `.md` dans ce dossier, garder le PDF signé à côté.
3. `git add`, `commit`, `push`.
