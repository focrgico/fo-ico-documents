# FO ICO — Documents

Base de données centralisée FO ICO :
- Convention Collective Nationale des CLCC (IDCC 2046)
- Accords collectifs locaux ICO
- Accords UNICANCER

Les PV/ODJ des instances (CSE, CSEC, CSSCT, CSSCTC) ne sont **pas** stockés ici — ils vivent dans une base séparée (projet dédié).

## Structure

- `docs/ccn/` — Convention Collective Nationale des CLCC : texte intégral + grilles de rémunération vérifiées
- `docs/accords-locaux/` — Accords négociés au niveau ICO
- `docs/accords-unicancer/` — Accords de branche UNICANCER

## Ajouter ou mettre à jour un document

```
git pull
(ajouter/modifier le(s) fichier(s) .md)
git add .
git commit -m "Description du changement"
git push
```

## Historique

Chaque commit trace qui a changé quoi, et quand. Pas besoin de garder plusieurs fichiers datés pour une même convention : on écrase le fichier canonique et git conserve l'historique (`git log docs/ccn/ccn-clcc.md`).

## Site (MkDocs)

Ce dépôt est prévu pour être publié via MkDocs (`mkdocs.yml` à la racine). Pour prévisualiser en local :

```
pip install mkdocs mkdocs-material
mkdocs serve
```
