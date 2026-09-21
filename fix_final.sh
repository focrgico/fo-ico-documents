#!/bin/bash
set -e

# 1. Remplacer le catalogue par la version corrigee (pas l'ajouter a cote)
mv catalogue/catalogue_intergenerationnel_maj2.json catalogue/catalogue.json

# 2. Remplacer le resume par la version corrigee
mv docs/accords-locaux/resumes-accords-locaux/resume-intergenerationnel-corrige.md \
   docs/accords-locaux/resumes-accords-locaux/resume-intergenerationnel.md

# 3. Remplacer le depliant par la version corrigee
mv docs/accords-locaux/Depliants_FO/Depliant_intergenerationnel_FO_corrige.pdf \
   docs/accords-locaux/Depliants_FO/Depliant_intergenerationnel_FO.pdf

# 4. Retirer le doublon de l'avenant 2023 encore present en archive (il est actif, pas archive)
cd docs/archive-accords-locaux
for f in *interg*"2023"*.pdf; do
  [ -e "$f" ] && git rm "$f"
done
cd ../..

git add -A
git status --short | grep -i interg
git status --short | grep -i catalogue

echo ""
echo "Verifiez la liste ci-dessus, puis :"
echo '  git commit -m "Accord intergenerationnel : correction finale (catalogue, resume, depliant, doublon archive)"'
echo "  git push"
