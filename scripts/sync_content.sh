#!/usr/bin/env bash
#
# scripts/sync_content.sh
#
# Safely transfer data-only Postgres content between local dev (Docker Compose)
# and the staging environment (Neon), in either direction.
#
# Safety rules baked in:
#   - Always dumps --data-only (schema must already be up to date via migrations
#     on the TARGET before you restore into it).
#   - Always excludes auth/session/secret-bearing tables, so credentials never
#     cross environments.
#   - Always takes a safety dump of the TARGET before writing to it.
#   - Defaults to a dry run (--list) unless you pass --apply.
#   - Optional --tables allowlist, so once staging becomes the Wagtail
#     "source of truth" you can restrict local->staging pushes to only the
#     non-Wagtail data-import tables you actually intend to move.
#
# Usage:
#   scripts/sync_content.sh --to=staging --tables=table1,table2 [--apply]
#   scripts/sync_content.sh --to=staging --allow-full-push [--apply]   (bootstrap only)
#   scripts/sync_content.sh --to=local   [--tables=table1,table2] [--apply]
#
# Policy (staging Wagtail = source of truth):
#   - local -> staging pushes MUST be restricted with --tables to your
#     data-import tables, day to day. An unfiltered local -> staging push
#     is only for the one-off initial bootstrap and requires the explicit
#     --allow-full-push flag as well as --apply, so it can't happen by
#     accident once staging holds real editor content.
#   - staging -> local pulls are unrestricted by default (that's the
#     intended steady-state direction for Wagtail content).
#
# Requires: docker compose (for the "local" side), psql/pg_dump/pg_restore
# client tools matching your Postgres major version, and STAGING_DATABASE_URL
# set in the environment (e.g. sourced from .env.staging).

set -euo pipefail

# ---- Config -----------------------------------------------------------

LOCAL_DB_SERVICE="db"
LOCAL_DB_USER="myproject"
LOCAL_DB_NAME="myproject"

BACKUP_DIR="${BACKUP_DIR:-../malaria-observer_resources/data_backups}"

# Tables that must NEVER cross environments in either direction.
EXCLUDE_TABLES=(
  auth_user
  auth_user_groups
  auth_user_user_permissions
  django_session
  django_admin_log
  wagtailcore_apitoken
  wagtailusers_userprofile
)

# ---- Arg parsing --------------------------------------------------------

TO=""
APPLY="false"
TABLES_FILTER=""
ALLOW_FULL_PUSH="false"

for arg in "$@"; do
  case "$arg" in
    --to=*) TO="${arg#*=}" ;;
    --apply) APPLY="true" ;;
    --tables=*) TABLES_FILTER="${arg#*=}" ;;
    --allow-full-push) ALLOW_FULL_PUSH="true" ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      exit 1
      ;;
  esac
done

if [[ "$TO" != "staging" && "$TO" != "local" ]]; then
  echo "Error: --to=staging or --to=local is required." >&2
  exit 1
fi

if [[ "$TO" == "staging" && -z "$TABLES_FILTER" && "$ALLOW_FULL_PUSH" != "true" ]]; then
  echo "Error: an unfiltered local -> staging push was requested." >&2
  echo "Staging Wagtail content is the source of truth, so day-to-day pushes" >&2
  echo "must be restricted with --tables=<your data-import tables>." >&2
  echo "If this really is the one-off initial bootstrap, re-run with --allow-full-push." >&2
  exit 1
fi

if [[ -z "${STAGING_DATABASE_URL:-}" ]]; then
  echo "Error: STAGING_DATABASE_URL is not set." >&2
  echo "e.g. export STAGING_DATABASE_URL=\$(grep DATABASE_URL .env.staging | cut -d= -f2-)" >&2
  exit 1
fi

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# ---- Helpers ------------------------------------------------------------

exclude_args() {
  local args=()
  for t in "${EXCLUDE_TABLES[@]}"; do
    args+=(--exclude-table="$t")
  done
  printf '%s\n' "${args[@]}"
}

table_filter_args() {
  # If --tables was given, restrict pg_dump to ONLY those tables.
  if [[ -n "$TABLES_FILTER" ]]; then
    local args=()
    IFS=',' read -ra TBLS <<< "$TABLES_FILTER"
    for t in "${TBLS[@]}"; do
      args+=(--table="$t")
    done
    printf '%s\n' "${args[@]}"
  fi
}

safety_dump_target() {
  local target="$1" # "local" or "staging"
  local out="$BACKUP_DIR/pre-sync-${target}-${TIMESTAMP}.dump"
  echo "Taking safety dump of TARGET ($target) before writing: $out"
  if [[ "$target" == "local" ]]; then
    docker compose exec -T "$LOCAL_DB_SERVICE" \
      pg_dump -U "$LOCAL_DB_USER" "$LOCAL_DB_NAME" --format=custom -f /tmp/pre_sync_target.dump
    docker compose cp "$LOCAL_DB_SERVICE:/tmp/pre_sync_target.dump" "$out"
  else
    pg_dump "$STAGING_DATABASE_URL" --format=custom -f "$out"
  fi
  echo "Safety dump written: $out"
}

# ---- Main -----------------------------------------------------------------

SOURCE_DUMP="$BACKUP_DIR/sync-source-${TIMESTAMP}.dump"

mapfile -t EXCL_ARGS < <(exclude_args)
mapfile -t TBL_ARGS < <(table_filter_args)

if [[ "$TO" == "staging" ]]; then
  SOURCE_LABEL="local"
  TARGET_LABEL="staging"

  echo "==> Dumping data-only content from LOCAL (excluding auth/session tables)..."
  docker compose exec -T "$LOCAL_DB_SERVICE" \
    pg_dump -U "$LOCAL_DB_USER" "$LOCAL_DB_NAME" \
      --data-only --format=custom \
      "${EXCL_ARGS[@]}" "${TBL_ARGS[@]}" \
      -f /tmp/sync_source.dump
  docker compose cp "$LOCAL_DB_SERVICE:/tmp/sync_source.dump" "$SOURCE_DUMP"

else
  SOURCE_LABEL="staging"
  TARGET_LABEL="local"

  echo "==> Dumping data-only content from STAGING (excluding auth/session tables)..."
  pg_dump "$STAGING_DATABASE_URL" \
    --data-only --format=custom \
    "${EXCL_ARGS[@]}" "${TBL_ARGS[@]}" \
    -f "$SOURCE_DUMP"
fi

echo "==> Source dump written: $SOURCE_DUMP"
echo
echo "==> Contents of source dump (table-of-contents):"
pg_restore -l "$SOURCE_DUMP"
echo

if [[ "$APPLY" != "true" ]]; then
  echo "Dry run only (no --apply passed). Nothing was written to $TARGET_LABEL."
  echo "Review the table list above, then re-run with --apply to actually restore."
  exit 0
fi

echo "==> --apply passed. Proceeding to write into $TARGET_LABEL."
safety_dump_target "$TARGET_LABEL"

if [[ "$TO" == "staging" ]]; then
  echo "==> Restoring into STAGING..."
  pg_restore --data-only --disable-triggers -d "$STAGING_DATABASE_URL" "$SOURCE_DUMP"
  echo "==> Rebuilding Wagtail search index on staging..."
  echo "    (run separately, e.g.:)"
  echo "    gcloud run jobs execute migrate-staging --region=europe-west3 --project=malaria-observer \\"
  echo "      --command=python --args=manage.py,update_index --wait"
else
  echo "==> Restoring into LOCAL..."
  docker compose cp "$SOURCE_DUMP" "$LOCAL_DB_SERVICE:/tmp/sync_apply.dump"
  docker compose exec -T "$LOCAL_DB_SERVICE" \
    pg_restore --data-only --disable-triggers -U "$LOCAL_DB_USER" -d "$LOCAL_DB_NAME" /tmp/sync_apply.dump
  echo "==> You may want to run 'docker compose exec web python manage.py update_index' now."
fi

echo
echo "Done. Source dump kept at: $SOURCE_DUMP"
echo "Target safety dump kept in: $BACKUP_DIR"