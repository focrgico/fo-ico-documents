#!/bin/bash
# A lancer depuis la racine du depot fo-ico-documents.
# Regroupe : renommage de l'accord de base, ajout du PDF de l'avenant 2023,
# et archivage de l'avenant 2021 (PDF + md, si le PDF est present localement).

cd docs/accords-locaux || { echo "Dossier introuvable, lancez ce script depuis la racine du depot."; exit 1; }

# 1. Accord de base : renommer PDF + md vers le nouveau nom
if [ -f "Accord d'entreprise intergenerationnel_signé.pdf" ]; then
  git mv "Accord d'entreprise intergenerationnel_signé.pdf" "Accord Intergénérationnel du 30 01 2020_signé.pdf"
fi
if [ -f "Accord d'entreprise intergenerationnel_signé.md" ]; then
  git mv "Accord d'entreprise intergenerationnel_signé.md" "Accord Intergenerationnel du 30 01 2020_signe.md"
fi

# 2. Avenant 2023 : ajouter le PDF s'il est present localement (le .md existe deja)
if [ -f "Avenant accord d'entreprise intergénérationnel_2023_Version signée.pdf" ]; then
  git add "Avenant accord d'entreprise intergénérationnel_2023_Version signée.pdf"
fi

# 3. Avenant 2021 : archiver le .md (renomme depuis son ancien nom) et le PDF si present
mkdir -p ../archive-accords-locaux
if [ -f "accord-intergenerationnel-avenant1-2021.md" ]; then
  git mv "accord-intergenerationnel-avenant1-2021.md" "../archive-accords-locaux/Accord intergenerationnel_Avenant n1_Signe plus en vigueur.md"
fi
if [ -f "Accord intergénérationnel_Avenant n1_Signé.pdf" ]; then
  git mv "Accord intergénérationnel_Avenant n1_Signé.pdf" "../archive-accords-locaux/Accord intergénérationnel_Avenant n1_Signé plus en vigueur.pdf"
fi

cd ../..
git status
echo ""
echo "Verifiez le statut ci-dessus, puis :"
echo '  git commit -m "Accord intergenerationnel : renommage base + ajout avenant 2023 + archivage avenant 2021"'
echo "  git push"
