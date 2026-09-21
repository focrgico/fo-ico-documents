#!/bin/bash
# A lancer depuis la racine du depot fo-ico-documents.
# Robuste : boucle sur les fichiers reellement presents, ignore index.md et
# tout fichier deja renomme (contenant "plus en vigueur"). Rejouable sans
# risque si une commande echoue en cours de route (pas de set -e).

cd docs/archive-accords-locaux || { echo "Dossier introuvable, lancez ce script depuis la racine du depot."; exit 1; }

count=0
for f in *.md *.pdf "Format word"/*.docx; do
  [ -e "$f" ] || continue
  base="$(basename "$f")"
  dir="$(dirname "$f")"
  [ "$base" = "index.md" ] && continue
  case "$base" in
    *"plus en vigueur"*) continue ;;
  esac
  name="${base%.*}"
  ext="${base##*.}"
  newname="${name} plus en vigueur.${ext}"
  if [ "$dir" = "." ]; then
    git mv "$base" "$newname" && count=$((count+1))
  else
    git mv "$dir/$base" "$dir/$newname" && count=$((count+1))
  fi
done

cd ../..
echo "$count fichier(s) renomme(s)."
if [ "$count" -gt 0 ]; then
  git commit -m "Archive : ajout de \"plus en vigueur\" aux fichiers restants"
  git push
else
  echo "Rien a committer."
fi
