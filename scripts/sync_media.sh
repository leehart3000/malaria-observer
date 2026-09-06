#!/usr/bin/env bash
#
# scripts/sync_media.sh
#
# Sync media files from the staging GCS bucket (the source of truth for
# anything uploaded through the CMS) to either the production bucket or
# the local dev Docker volume.
#
# Safety rules baked in:
#   - Staging is always the SOURCE. This script never writes to staging.
#   - Defaults to a dry run (no files copied) unless you pass --apply.
#   - Never deletes destination-only files by default (e.g. local test
#     uploads that were never pushed to staging are left alone). Pass
#     --delete-extraneous to mirror staging exactly, removing anything
#     on the target that staging doesn't have.
#
# Usage:
#   scripts/sync_media.sh --to=production [--apply] [--delete-extraneous]
#   scripts/sync_media.sh --to=local      [--apply] [--delete-extraneous]
#
# Requires: gcloud (authenticated, with access to both buckets), and for
# --to=local, docker compose.

set -euo pipefail

# ---- Config -----------------------------------------------------------

STAGING_BUCKET="gs://malaria-observer-staging-media"
PRODUCTION_BUCKET="gs://malaria-observer-production-media"
LOCAL_WEB_SERVICE="web"
LOCAL_MEDIA_PATH="/app/media"

# ---- Arg parsing --------------------------------------------------------

TO=""
APPLY="false"
DELETE_EXTRANEOUS="false"

for arg in "$@"; do
  case "$arg" in
    --to=*) TO="${arg#*=}" ;;
    --apply) APPLY="true" ;;
    --delete-extraneous) DELETE_EXTRANEOUS="true" ;;
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

if [[ "$TO" != "production" && "$TO" != "local" ]]; then
  echo "Error: --to=production or --to=local is required." >&2
  exit 1
fi

RSYNC_FLAGS=(--recursive)
if [[ "$APPLY" != "true" ]]; then
  RSYNC_FLAGS+=(--dry-run)
fi
if [[ "$DELETE_EXTRANEOUS" == "true" ]]; then
  RSYNC_FLAGS+=(--delete-unmatched-destination-objects)
fi

# ---- Main -----------------------------------------------------------------

if [[ "$TO" == "production" ]]; then
  echo "==> Syncing STAGING -> PRODUCTION media bucket..."
  if [[ "$APPLY" != "true" ]]; then
    echo "    (dry run -- pass --apply to actually copy)"
  fi
  gcloud storage rsync "$STAGING_BUCKET" "$PRODUCTION_BUCKET" "${RSYNC_FLAGS[@]}"

else
  echo "==> Syncing STAGING -> LOCAL media (via temporary download)..."
  if [[ "$APPLY" != "true" ]]; then
    echo "    (dry run -- pass --apply to actually copy)"
  fi

  if [[ "$APPLY" != "true" ]]; then
    # gcloud storage rsync's --dry-run works fine against a plain local
    # directory target too, so we can dry-run the actual download step
    # without needing a temp dir or touching the container at all.
    TMP_DIR="$(mktemp -d)"
    gcloud storage rsync "$STAGING_BUCKET" "$TMP_DIR" "${RSYNC_FLAGS[@]}"
    rm -rf "$TMP_DIR"
    echo "Dry run only. Re-run with --apply to actually copy into local media."
    exit 0
  fi

  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "$TMP_DIR"' EXIT

  gcloud storage rsync "$STAGING_BUCKET" "$TMP_DIR" "${RSYNC_FLAGS[@]}"

  echo "==> Copying downloaded media into the LOCAL web container..."
  docker compose cp "$TMP_DIR/." "$LOCAL_WEB_SERVICE:$LOCAL_MEDIA_PATH/"

  if [[ "$DELETE_EXTRANEOUS" == "true" ]]; then
    echo "Note: --delete-extraneous only affected the temporary download"
    echo "directory, not the container's media volume directly -- docker"
    echo "compose cp does not delete files. If you need an exact mirror"
    echo "inside the container, clear the volume first (e.g. via"
    echo "'docker compose down -v' for the media_data volume) before"
    echo "re-running this script."
  fi
fi

echo
echo "Done."