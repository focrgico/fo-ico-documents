#!/usr/bin/env bash
# Publication du site sur la branche gh-pages (celle qu'OVH deploie).
# Usage : bash publier_site.sh            -> simulation, rien n'est envoye
#         bash publier_site.sh --publier  -> publie vraiment
# Garde-fous : jamais de commit sur main, refus si des fichiers disparaissent.
set -euo pipefail
MODE="${1:-}"
REPO="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO"

[ "$(git branch --show-current)" = "main" ] || { echo "STOP : lancez ce script depuis la branche main."; exit 1; }
[ -z "$(git status --porcelain)" ] || { echo "STOP : des fichiers ne sont pas commites sur main :"; git status --short; exit 1; }
git fetch -q origin main
git fetch -q origin +gh-pages:refs/remotes/origin/gh-pages
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] || { echo "STOP : main local different de origin/main (commit ou push manquant, ou commit parasite)."; exit 1; }

python3 build_site.py | tail -1

WT="$(mktemp -d)"; trap 'git worktree remove --force "$WT" 2>/dev/null || true' EXIT
git worktree add -q --detach "$WT" origin/gh-pages
cd "$WT"
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name .nojekyll -exec rm -rf {} +
cp -a "$REPO/site/." .
# les Word des resumes ne sont pas regeneres a l'identique : on garde ceux deja publies
for f in $(git ls-tree -r --name-only origin/gh-pages | grep -E '^resumes/[^/]+\.docx$'); do git checkout -q origin/gh-pages -- "$f"; done
git add -A

AVANT=$(git ls-tree -r --name-only origin/gh-pages | wc -l)
SUPPR=$(git diff --cached --diff-filter=D --name-only | wc -l)
echo "Fichiers actuellement publies : $AVANT | supprimes par cette publication : $SUPPR"
git diff --cached --stat | tail -15
if [ "$SUPPR" -gt 5 ]; then echo "STOP : $SUPPR fichiers seraient supprimes, c'est anormal. Rien n'est publie."; git diff --cached --diff-filter=D --name-only | head -20; exit 1; fi

if [ "$MODE" != "--publier" ]; then echo "Simulation terminee. Rien n'a ete envoye. Relancez avec --publier."; exit 0; fi
git commit -q -m "Mise a jour du site"
git push origin HEAD:gh-pages
echo "Publie. Suivre le deploiement : gh api repos/focrgico/fo-ico-documents/actions/runs --jq '.workflow_runs[0]|.status,.conclusion'"
