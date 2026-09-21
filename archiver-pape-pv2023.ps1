# A executer depuis la racine du depot fo-ico-documents
# Encodage : UTF-8 avec BOM (pour PowerShell)

git mv "docs/elections/Accord préparatoire PAPE 2022_Signé.pdf" "docs/archive-accords-locaux/Accord preparatoire PAPE 2022_Signe.pdf"

git mv "docs/nao/PV Désaccord NAO 2023.pdf" "docs/archive-accords-locaux/PV Desaccord NAO 2023.pdf"

Write-Host "Termine. Verifie avec git status puis :"
Write-Host 'git add -A'
Write-Host 'git commit -m "Archivage PAPE 2022 et PV desaccord NAO 2023"'
Write-Host 'git push'
