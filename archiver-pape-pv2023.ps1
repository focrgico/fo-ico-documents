# Script - a executer depuis la racine du depot fo-ico-documents
# Deplace PAPE 2022 et le PV de desaccord NAO 2023 vers l'archive, en retirant les accents du nom (convention du depot)

git mv "docs\elections\Accord préparatoire PAPE 2022_Signé.pdf" "docs\archive-accords-locaux\Accord preparatoire PAPE 2022_Signe.pdf"
git mv "docs\nao\PV Désaccord NAO 2023.pdf" "docs\archive-accords-locaux\PV Desaccord NAO 2023.pdf"

Write-Host ""
Write-Host "Termine. Verifie avec git status avant de committer."
