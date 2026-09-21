#!/bin/bash
# A lancer depuis la racine du depot fo-ico-documents.
cd "docs/accords-locaux/Accords locaux Format word" || { echo "Dossier introuvable"; exit 1; }

# 1. Supprimer le doublon (copie que j'avais uploadee, identique a "V finale.docx")
if [ -f "Accord_Forfait_Mobilite_Durable_V_finale_2024.docx" ]; then
  git rm "Accord_Forfait_Mobilite_Durable_V_finale_2024.docx"
  echo "supprime (doublon) : Accord_Forfait_Mobilite_Durable_V_finale_2024.docx"
fi

# 2. Archiver la vraie version 2024 (celle qui etait deja la, jamais archivee)
mkdir -p ../../archive-accords-locaux/"Format word"
for f in "Accord Forfait Mobilité Durable V finale.docx"; do
  [ -e "$f" ] && git mv "$f" "../../archive-accords-locaux/Format word/Accord Forfait Mobilite Durable V finale plus en vigueur.docx"
done

# "Accord Forfait Mobilité Durable Vfinale.docx" (la vraie version 2025) reste en place, ne pas y toucher

cd ../../..
git add -A
echo ""
git status --short
echo ""
echo "Verifiez, puis :"
echo '  git commit -m "Forfait Mobilite Durable : nettoyage des Word, conservation de la vraie version 2025"'
echo "  git push"
