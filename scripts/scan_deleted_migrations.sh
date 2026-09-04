#!/usr/bin/env bash
#
# scripts/scan_deleted_migrations.sh
#
# Finds every migration file that has ever been deleted from git history
# and flags any that contained RunPython (data migration) logic, so you
# can confirm nothing but pure schema changes was lost in a migration reset.
#
# Usage: scripts/scan_deleted_migrations.sh

set -euo pipefail

FILES=$(git log --all --diff-filter=D --name-only -- '*/migrations/*.py' \
  | grep -E '/migrations/.*\.py$' \
  | sort -u)

FOUND_ANY="false"

for f in $FILES; do
  # Find the most recent commit that deleted this file.
  del_commit=$(git log --all --diff-filter=D --format=%H -- "$f" | head -1)
  if [[ -z "$del_commit" ]]; then
    continue
  fi

  prev_commit="${del_commit}^"

  # Get the file's content as it was just before deletion.
  content=$(git show "${prev_commit}:${f}" 2>/dev/null || true)
  if [[ -z "$content" ]]; then
    continue
  fi

  if grep -q "RunPython" <<< "$content"; then
    FOUND_ANY="true"
    echo "=== $f  (deleted in ${del_commit:0:8}, contains RunPython) ==="
    grep -n "RunPython\|^def " <<< "$content"
    echo
    echo "  Full recovery command:"
    echo "    git show ${prev_commit}:${f}"
    echo
  fi
done

if [[ "$FOUND_ANY" == "false" ]]; then
  echo "No deleted migration files containing RunPython were found."
fi