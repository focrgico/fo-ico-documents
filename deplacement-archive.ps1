# Script de deplacement vers l'archive - a executer depuis la racine du depot fo-ico-documents
mkdir docs\archive-accords-locaux -ErrorAction SilentlyContinue

# NOTE : accord-financement-syndical-2021.md n'est PAS deplace ici car il n'existe plus
# dans accords-locaux (perdu precedemment) - il arrive directement via le zip, voir instructions.

git mv "docs\accords-locaux\accord-intergenerationnel-avenant1-2021.md" "docs\archive-accords-locaux\accord-intergenerationnel-avenant1-2021.md"
git mv "docs\accords-locaux\accord-supplement-interessement-2023.md" "docs\archive-accords-locaux\accord-supplement-interessement-2023.md"
git mv "docs\accords-locaux\ACCORDS_Egalite femmes hommes_2023_Version signee.md" "docs\archive-accords-locaux\ACCORDS_Egalite femmes hommes_2023_Version signee.md"
git mv "docs\accords-locaux\Accord egalite HF_Avenant signe.md" "docs\archive-accords-locaux\Accord egalite HF_Avenant signe.md"
git mv "docs\accords-locaux\ACCORD INTERESSEMENT 2024_Version signee.md" "docs\archive-accords-locaux\ACCORD INTERESSEMENT 2024_Version signee.md"
git mv "docs\accords-locaux\Accord interessement 2025 - Version signee.md" "docs\archive-accords-locaux\Accord interessement 2025 - Version signee.md"
git mv "docs\accords-locaux\Avenant accord d'entreprise intergenerationnel_2023_Version signee.md" "docs\archive-accords-locaux\Avenant accord d'entreprise intergenerationnel_2023_Version signee.md"
git mv "docs\accords-locaux\Accord sur le supplement d'interessement au tire de l'exercice 2025 - Version signee.md" "docs\archive-accords-locaux\Accord sur le supplement d'interessement au tire de l'exercice 2025 - Version signee.md"
git mv "docs\elections\accord-vote-electronique-2022.md" "docs\archive-accords-locaux\accord-vote-electronique-2022.md"
git mv "docs\elections\ACCORDS_Dialogue social_2023_Version signee.md" "docs\archive-accords-locaux\ACCORDS_Dialogue social_2023_Version signee.md"
git mv "docs\nao\accord-methode-nao-2024.md" "docs\archive-accords-locaux\accord-methode-nao-2024.md"
git mv "docs\nao\accord-methode-nao-2025.md" "docs\archive-accords-locaux\accord-methode-nao-2025.md"
git mv "docs\nao\pv-desaccord-nao-2025.md" "docs\archive-accords-locaux\pv-desaccord-nao-2025.md"
git mv "docs\nao\NAO 2024 - PV Desaccord.md" "docs\archive-accords-locaux\NAO 2024 - PV Desaccord.md"
git mv "docs\nao\NAO 2026 _PV de desaccord signe.md" "docs\archive-accords-locaux\NAO 2026 _PV de desaccord signe.md"
