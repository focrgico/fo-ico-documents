#!/bin/bash
# A lancer depuis la racine du depot fo-ico-documents.
# Utilise des motifs generiques pour eviter les problemes d'encodage accentue.

cd docs/accords-locaux || { echo "Dossier introuvable, lancez depuis la racine du depot."; exit 1; }

echo "=== 1. Suppression du fichier CET vDefinitive (PDF + Word) ==="
for f in *CET*vD*finitive*.pdf; do
  [ -e "$f" ] && echo "suppression : $f" && git rm "$f"
done
for f in "Accords locaux Format word"/*CET*vD*finitive*.docx; do
  [ -e "$f" ] && echo "suppression : $f" && git rm "$f"
done

echo ""
echo "=== 2. Archivage du PDF 2024 (le .md existant contient deja le bon texte 2025, ne pas y toucher) ==="
mkdir -p ../archive-accords-locaux
for f in *FORFAIT*MOBILITE*DURABLE*.pdf; do
  [ -e "$f" ] && echo "archivage (PDF, contenu reel = 2024) : $f" && git mv "$f" "../archive-accords-locaux/${f%.*} plus en vigueur.${f##*.}"
done
# Word 2024 transmis separement (a placer dans accords-locaux/ avant de lancer ce script)
if [ -f "Accord_Forfait_Mobilite_Durable_V_finale_2024.docx" ]; then
  mv "Accord_Forfait_Mobilite_Durable_V_finale_2024.docx" "../archive-accords-locaux/Accord_Forfait_Mobilite_Durable_V_finale_2024 plus en vigueur.docx"
  echo "archivage : Accord_Forfait_Mobilite_Durable_V_finale_2024.docx"
fi

echo ""
echo "=== 3. Ajout du PDF ATT Cadres ==="
# Placez le fichier "Accord Durée et ATT Cadres_signé.pdf" dans docs/accords-locaux/ AVANT de lancer ce script
if [ -f "Accord Durée et ATT Cadres_signé.pdf" ]; then
  git add "Accord Durée et ATT Cadres_signé.pdf"
  echo "ajoute : Accord Durée et ATT Cadres_signé.pdf"
else
  echo "ATTENTION : fichier ATT Cadres non trouve a cet emplacement, a ajouter manuellement"
fi

cd ../..
git add -A
echo ""
echo "=== git status ==="
git status --short
echo ""
echo "Verifiez ci-dessus, puis :"
echo '  git add catalogue/catalogue.json'
echo '  git commit -m "ATT Cadres: ajout PDF ; CET vDefinitive: suppression ; FMD 2024: archivage"'
echo "  git push"
