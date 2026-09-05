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
  django_migrations
  wagtailcore_apitoken
  wagtailusers_userprofile
)

# Django/Wagtail bootstrap tables: populated identically and deterministically
# by every environment's own migrations (content types, permissions, the
# default locale). These are safe to merge with ON CONFLICT DO NOTHING,
# since a "collision" here just means both sides already agree.
# Never put actual content (pages, datasets, articles, etc.) in this list --
# for real content, a PK collision means the TARGET's stale copy silently
# wins and the SOURCE's real edits get discarded with no error.
BOOTSTRAP_TABLES=(
  django_content_type
  auth_permission
  auth_group
  auth_group_permissions
  wagtailcore_locale
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

# Populates the global EXCL_ARGS array directly (no subshell/mapfile,
# for compatibility with the old Bash 3.2 shipped by default on macOS).
# Excludes both the permanent EXCLUDE_TABLES and the BOOTSTRAP_TABLES,
# since bootstrap tables are dumped/restored separately with merge semantics.
build_exclude_args() {
  EXCL_ARGS=()
  for t in "${EXCLUDE_TABLES[@]}"; do
    EXCL_ARGS+=(--exclude-table="$t")
  done
  for t in "${BOOTSTRAP_TABLES[@]}"; do
    EXCL_ARGS+=(--exclude-table="$t")
  done
}

# Populates BOOTSTRAP_INCLUDE_ARGS: --table=X for each bootstrap table,
# used for the small separate bootstrap dump/restore pass.
build_bootstrap_args() {
  BOOTSTRAP_INCLUDE_ARGS=()
  for t in "${BOOTSTRAP_TABLES[@]}"; do
    BOOTSTRAP_INCLUDE_ARGS+=(--table="$t")
  done
}

# Populates the global TBL_ARGS array directly.
build_table_filter_args() {
  TBL_ARGS=()
  if [[ -n "$TABLES_FILTER" ]]; then
    IFS=',' read -ra TBLS <<< "$TABLES_FILTER"
    for t in "${TBLS[@]}"; do
      TBL_ARGS+=(--table="$t")
    done
  fi
}

# Given a content-only dump file, extracts the real table names it contains
# and returns a "TRUNCATE TABLE a, b, c CASCADE;" statement as a string.
# This is what makes a pull/push a true replace rather than a merge --
# Wagtail's page tree and related content cannot be safely row-merged
# between two independently-bootstrapped trees.
build_truncate_statement() {
  local dump_file="$1"
  local tables
  tables=$(pg_restore -l "$dump_file" | awk '/TABLE DATA/ {print $7}' | sort -u)
  if [[ -z "$tables" ]]; then
    return 1
  fi
  local joined
  joined=$(printf '"%s", ' $tables)
  joined="${joined%, }"
  echo "TRUNCATE TABLE $joined CASCADE;"
}

truncate_content_tables_on_local() {
  local dump_file="$1"
  local stmt
  if ! stmt="$(build_truncate_statement "$dump_file")"; then
    echo "No content tables found to truncate -- skipping." >&2
    return 0
  fi
  echo "==> Truncating LOCAL content tables before replace-restore..."
  docker compose exec -T "$LOCAL_DB_SERVICE" \
    psql -U "$LOCAL_DB_USER" -d "$LOCAL_DB_NAME" -c "$stmt"
}

truncate_content_tables_on_staging() {
  local dump_file="$1"
  local stmt
  if ! stmt="$(build_truncate_statement "$dump_file")"; then
    echo "No content tables found to truncate -- skipping." >&2
    return 0
  fi
  echo "==> Truncating STAGING content tables before replace-restore..."
  psql "$STAGING_DATABASE_URL" -c "$stmt"
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
BOOTSTRAP_DUMP="$BACKUP_DIR/sync-bootstrap-${TIMESTAMP}.dump"

build_exclude_args
build_bootstrap_args
build_table_filter_args

if [[ "$TO" == "staging" ]]; then
  SOURCE_LABEL="local"
  TARGET_LABEL="staging"

  echo "==> Dumping bootstrap tables from LOCAL (merge-safe)..."
  docker compose exec -T "$LOCAL_DB_SERVICE" \
    pg_dump -U "$LOCAL_DB_USER" "$LOCAL_DB_NAME" \
      --data-only --format=custom --inserts --on-conflict-do-nothing \
      "${BOOTSTRAP_INCLUDE_ARGS[@]}" \
      -f /tmp/sync_bootstrap.dump
  docker compose cp "$LOCAL_DB_SERVICE:/tmp/sync_bootstrap.dump" "$BOOTSTRAP_DUMP"

  echo "==> Dumping content tables from LOCAL (excluding auth/session/bootstrap tables)..."
  docker compose exec -T "$LOCAL_DB_SERVICE" \
    pg_dump -U "$LOCAL_DB_USER" "$LOCAL_DB_NAME" \
      --data-only --format=custom \
      "${EXCL_ARGS[@]}" ${TBL_ARGS[@]+"${TBL_ARGS[@]}"} \
      -f /tmp/sync_source.dump
  docker compose cp "$LOCAL_DB_SERVICE:/tmp/sync_source.dump" "$SOURCE_DUMP"

else
  SOURCE_LABEL="staging"
  TARGET_LABEL="local"

  echo "==> Dumping bootstrap tables from STAGING (merge-safe)..."
  pg_dump "$STAGING_DATABASE_URL" \
    --data-only --format=custom --inserts --on-conflict-do-nothing \
    "${BOOTSTRAP_INCLUDE_ARGS[@]}" \
    -f "$BOOTSTRAP_DUMP"

  echo "==> Dumping content tables from STAGING (excluding auth/session/bootstrap tables)..."
  pg_dump "$STAGING_DATABASE_URL" \
    --data-only --format=custom \
    "${EXCL_ARGS[@]}" ${TBL_ARGS[@]+"${TBL_ARGS[@]}"} \
    -f "$SOURCE_DUMP"
fi

echo "==> Source dump written: $SOURCE_DUMP"
echo "==> Bootstrap dump written: $BOOTSTRAP_DUMP"
echo
echo "==> Contents of content dump (table-of-contents):"
pg_restore -l "$SOURCE_DUMP"
echo

if [[ "$APPLY" != "true" ]]; then
  echo "Dry run only (no --apply passed). Nothing was written to $TARGET_LABEL."
  echo "Review the table list above, then re-run with --apply to actually restore."
  echo "Note: content tables will be REPLACED (truncated then reloaded) on the"
  echo "target -- bootstrap tables are merged (existing rows kept on conflict)."
  exit 0
fi

echo "==> --apply passed. Proceeding to write into $TARGET_LABEL."
safety_dump_target "$TARGET_LABEL"

if [[ "$TO" == "staging" ]]; then
  echo "==> Merging bootstrap tables into STAGING..."
  pg_restore --data-only --disable-triggers \
    -d "$STAGING_DATABASE_URL" "$BOOTSTRAP_DUMP"

  truncate_content_tables_on_staging "$SOURCE_DUMP"

  echo "==> Replacing content tables in STAGING..."
  pg_restore --data-only --disable-triggers \
    -d "$STAGING_DATABASE_URL" "$SOURCE_DUMP"

  echo "==> Rebuilding Wagtail search index on staging..."
  echo "    (run separately, e.g.:)"
  echo "    gcloud run jobs execute migrate-staging --region=europe-west3 --project=malaria-observer \\"
  echo "      --command=python --args=manage.py,update_index --wait"
else
  echo "==> Merging bootstrap tables into LOCAL..."
  docker compose cp "$BOOTSTRAP_DUMP" "$LOCAL_DB_SERVICE:/tmp/sync_bootstrap_apply.dump"
  docker compose exec -T "$LOCAL_DB_SERVICE" \
    pg_restore --data-only --disable-triggers \
      -U "$LOCAL_DB_USER" -d "$LOCAL_DB_NAME" /tmp/sync_bootstrap_apply.dump

  truncate_content_tables_on_local "$SOURCE_DUMP"

  echo "==> Replacing content tables in LOCAL..."
  docker compose cp "$SOURCE_DUMP" "$LOCAL_DB_SERVICE:/tmp/sync_apply.dump"
  docker compose exec -T "$LOCAL_DB_SERVICE" \
    pg_restore --data-only --disable-triggers \
      -U "$LOCAL_DB_USER" -d "$LOCAL_DB_NAME" /tmp/sync_apply.dump

  echo "==> You may want to run 'docker compose exec web python manage.py update_index' now."
fi

echo
echo "Done. Content dump kept at: $SOURCE_DUMP"
echo "Bootstrap dump kept at: $BOOTSTRAP_DUMP"
echo "Target safety dump kept in: $BACKUP_DIR"