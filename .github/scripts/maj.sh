#!/usr/bin/env bash
# Met à jour les données (mode markets | full | news) et les publie sur la branche « data ».
# Deux tâches peuvent tourner en même temps (marchés en continu + revue de presse / collecte complète) :
# chaque publication part des dernières données publiées, et si l'autre tâche a publié entre-temps,
# on reprend depuis ses données et on recommence (jusqu'à 3 fois).
set -uo pipefail
mode="$1"
root="${GITHUB_WORKSPACE:-$(pwd)}"
data="$root/data"

for essai in 1 2 3; do
  # 1. Repartir des données publiées
  if git -C "$root" ls-remote --exit-code --heads origin data >/dev/null; then
    git -C "$root" fetch -q --depth=1 origin data || { sleep 10; continue; }
    base=$(git -C "$root" rev-parse FETCH_HEAD)
    if [ -e "$data/.git" ]; then
      git -C "$data" reset -q --hard "$base" && git -C "$data" clean -fdq
    else
      git -C "$root" worktree add -q -B data "$data" "$base"
    fi
  else
    base=""
    [ -e "$data/.git" ] || git -C "$root" worktree add -q --orphan -b data "$data"
  fi

  # 2. Collecter et recalculer
  (cd "$root/pipeline" && DATA_DIR="$data" python run.py --mode "$mode") || exit 1

  # 3. Publier (un seul commit gardé sur la branche data, pour qu'elle reste légère)
  git -C "$data" add -A
  if git -C "$data" diff --cached --quiet; then echo "Rien de neuf"; exit 0; fi
  msg="Données $mode $(date -u +%FT%TZ)"
  if git -C "$data" rev-parse --verify -q HEAD >/dev/null; then
    git -C "$data" commit --amend -q -m "$msg"
  else
    git -C "$data" commit -q -m "$msg"
  fi
  if [ -n "$base" ]; then
    git -C "$data" push -q --force-with-lease="data:$base" origin data && { echo "Publié : $msg"; exit 0; }
  else
    git -C "$data" push -q origin data && { echo "Publié : $msg"; exit 0; }
  fi
  echo "Une autre mise à jour vient d'être publiée : nouvel essai ($essai/3)"
  sleep $((essai * 5))
done
echo "::warning::Publication impossible après 3 essais"
exit 1
