# Script de nettoyage - a executer depuis la racine du depot fo-ico-documents
# Supprime tout .md a la racine de ces dossiers qui n'est PAS dans la liste des noms corrects
# Ne touche jamais aux .pdf ni aux sous-dossiers Word

$keep_accords_locaux = @(
    'ACCORD FORFAIT MOBILITE DURABLE_Version signee.md',
    'ACCORD INTERESSEMENT 2024_Version signee.md',
    'ACCORDS_Egalite femmes hommes_2023_Version signee.md',
    'Accord ATT NC_Avenant n1_Signe.md',
    'Accord CET_Avenant n1_signe.md',
    'Accord Conge Humanitaire (2026).md',
    'Accord PVA_2022_Signe.md',
    'Accord Parcours Phycisiens_2022_Signe.md',
    'Accord Reprise Experience professionnelle MER-AS-IDE_2022_Signe.md',
    'Accord compteur intermediaire salarie poste_signe.md',
    'Accord d''entreprise relatif a l''interessement (2026).md',
    'Accord egalite FH 2026.md',
    'Accord egalite HF_Avenant signe.md',
    'Accord interessement 2025 - Version signee.md',
    'Accord parcours IDE et MER_Version signee.md',
    'Accord prime USC signe.md',
    'Accord prime chaussure version signee.md',
    'Accord relatif a la repartition de la BIC_Version signee.md',
    'Accord relatif au parcours des assistantes medicales_Version signee.md',
    'Accord sur la validation des acquis professionnels _Version signee.md',
    'Accord sur le supplement d''interessement au tire de l''exercice 2025 - Version signee.md',
    'Accord travail de nuit - 2026.md',
    'Accord-Cheques syndicaux_v signee.md',
    'Avenant accord d''entreprise intergenerationnel_2023_Version signee.md',
    'accord-acquisition-cp-maladie-cadres-2025.md',
    'accord-acquisition-cp-maladie-non-cadres-2025.md',
    'accord-cdd-objet-defini-2021.md',
    'accord-cet-2021.md',
    'accord-compteur-intermediaire-non-postes-2024.md',
    'accord-duree-att-cadres-2021.md',
    'accord-duree-att-non-cadres-2020.md',
    'accord-financement-syndical-2021.md',
    'accord-intergenerationnel-avenant1-2021.md',
    'accord-percol-2021.md',
    'accord-supplement-interessement-2023.md',
    'accord-teletravail-2021.md',
    'index.md',
)
Get-ChildItem -Path "docs\accords-locaux" -Filter "*.md" -File | Where-Object { $keep_accords_locaux -notcontains $_.Name } | ForEach-Object { Write-Host "Suppression: $($_.FullName)"; Remove-Item $_.FullName }

$keep_nao = @(
    'Accord de methode NAO au titre de 2026.md',
    'NAO 2024 - PV Desaccord.md',
    'NAO 2026 _PV de desaccord signe.md',
    'accord-methode-nao-2024.md',
    'accord-methode-nao-2025.md',
    'index.md',
    'pv-desaccord-nao-2025.md',
)
Get-ChildItem -Path "docs\nao" -Filter "*.md" -File | Where-Object { $keep_nao -notcontains $_.Name } | ForEach-Object { Write-Host "Suppression: $($_.FullName)"; Remove-Item $_.FullName }

$keep_elections = @(
    'ACCORD VOTE ELECTRONIQUE _ Elections professionnelles 2026.md',
    'ACCORDS_Dialogue social_2023_Version signee.md',
    'Accord dialogue social 2026.md',
    'accord-vote-electronique-2022.md',
    'index.md',
)
Get-ChildItem -Path "docs\elections" -Filter "*.md" -File | Where-Object { $keep_elections -notcontains $_.Name } | ForEach-Object { Write-Host "Suppression: $($_.FullName)"; Remove-Item $_.FullName }

$keep_DUE = @(
    'DUE Parcours techs de laboratoire-macroscopie_Version signee.md',
    'DUE_Prime de retour inopine.md',
    'due-complementaire-frais-sante.md',
    'due-prime-pool-remplacement-am.md',
    'due-prime-pool-remplacement-soignants.md',
    'index.md',
)
Get-ChildItem -Path "docs\DUE" -Filter "*.md" -File | Where-Object { $keep_DUE -notcontains $_.Name } | ForEach-Object { Write-Host "Suppression: $($_.FullName)"; Remove-Item $_.FullName }
