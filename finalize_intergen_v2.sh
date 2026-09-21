#!/bin/bash
# A lancer depuis la racine du depot fo-ico-documents.
# Utilise des motifs generiques (*) sur la partie non accentuee des noms,
# pour eviter les problemes d'encodage rencontres avec les noms exacts.

cd docs/accords-locaux || { echo "Dossier introuvable, lancez ce script depuis la racine du depot."; exit 1; }

echo "=== Fichiers PDF/MD contenant 'interg' trouves ici : ==="
ls -1 *interg*.pdf *interg*.md 2>/dev/null
echo "========================================================"
echo ""

# 1. PDF de l'accord de base : cherche un fichier qui n'est pas deja bien nomme
for f in *interg*"du 30 01 2020"*.pdf *interg*"signe"*.pdf *interg*"signé"*.pdf; do
  [ -e "$f" ] || continue
  case "$f" in
    *"Avenant"*) continue ;;  # ne pas toucher aux avenants ici
    "Accord Intergénérationnel du 30 01 2020_signé.pdf") continue ;;  # deja bon nom
  esac
  echo "Renommage accord de base : $f"
  git mv "$f" "Accord Intergénérationnel du 30 01 2020_signé.pdf"
  break
done

# 2. PDF de l'avenant 2023 : cherche un fichier "Avenant...2023...pdf"
for f in *interg*"2023"*.pdf; do
  [ -e "$f" ] || continue
  echo "PDF avenant 2023 trouve : $f (deja au bon endroit, ajout au suivi git)"
  git add "$f"
  break
done

# 3. PDF de l'avenant 2021 : cherche un fichier "Avenant...n1...pdf" ou "...Avenant1...pdf"
mkdir -p ../archive-accords-locaux
for f in *interg*"n1"*.pdf *interg*"n 1"*.pdf *interg*"Avenant 1"*.pdf; do
  [ -e "$f" ] || continue
  echo "PDF avenant 2021 trouve, archivage : $f"
  git mv "$f" "../archive-accords-locaux/Accord intergenerationnel_Avenant n1_Signe plus en vigueur.pdf"
  break
done

cd ../..
echo ""
echo "=== git status ==="
git status --short
echo ""
echo "Verifiez ci-dessus. Si tout est correct :"
echo '  git commit -m "Accord intergenerationnel : finalisation des noms de fichiers PDF"'
echo "  git push"
echo ""
echo "Si un des 3 fichiers n'a PAS ete trouve (rien affiche pour lui ci-dessus),"
echo "c'est qu'il n'existe pas encore sous ce nom dans votre dossier local —"
echo "verifiez son nom exact avec : ls -la docs/accords-locaux/ | grep -i interg"
