#!/usr/bin/env bash
set -euo pipefail

# One-time (well, repeated-daily) backlog sweep: crawls idea_links_no_duplicates.txt
# in fixed-size batches, tracking progress in a checkpoint file so it can be re-run
# (locally, via cron, or via a scheduled GH Actions job) until the whole backlog is
# scraped. Unlike weekly_refresh.sh, this NEVER truncates the database.
#
# Backfill and weekly_refresh.sh must not run concurrently — both drive the same
# spider against the same DB/service and there is no lock file guarding this.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
source "$ROOT_DIR/scripts/lib_vic_scrape.sh"

DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_USER=${DB_USER:-postgres}
DB_PASSWORD=${DB_PASSWORD:-postgres}
DB_NAME=${DB_NAME:-ideas}
DATABASE_URL=${DATABASE_URL:-"postgresql+psycopg2://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"}
USE_DOCKER=${USE_DOCKER:-1}
DOCKER_SERVICE=${DOCKER_SERVICE:-api}

LINKS_FILE=${IDEA_LINKS_FILE_HOST:-"$ROOT_DIR/idea_links_no_duplicates.txt"}
CHECKPOINT_FILE=${BACKFILL_CHECKPOINT_FILE:-"$ROOT_DIR/data/backfill_checkpoint.json"}
BATCH_SIZE=${BACKFILL_BATCH_SIZE:-500}

export DATABASE_URL
export PGPASSWORD="$DB_PASSWORD"

if [ ! -f "$LINKS_FILE" ]; then
  echo "Error: $LINKS_FILE not found. Run ProcessLinks.py (or restore it from git) first." >&2
  exit 1
fi

mkdir -p "$(dirname "$CHECKPOINT_FILE")"
TOTAL_LINKS=$(wc -l < "$LINKS_FILE" | tr -d ' ')

if [ ! -f "$CHECKPOINT_FILE" ]; then
  printf '{"offset": 0, "total": %s}' "$TOTAL_LINKS" > "$CHECKPOINT_FILE"
fi

OFFSET=$(python3 -c "import json; print(json.load(open('$CHECKPOINT_FILE'))['offset'])")

if [ "$OFFSET" -ge "$TOTAL_LINKS" ]; then
  echo "Backfill already complete: offset=$OFFSET total=$TOTAL_LINKS"
  exit 0
fi

echo "Backfill batch: offset=$OFFSET size=$BATCH_SIZE total=$TOTAL_LINKS"

RESET_DB=0
export RESET_DB
export IDEA_LINKS_START="$OFFSET"
export IDEA_LINKS_LIMIT="$BATCH_SIZE"
export IDEA_LINKS_MODE=head

if [ "$USE_DOCKER" -eq 1 ]; then
  vic_require_docker_compose
fi

vic_preflight_or_exit
vic_ensure_tables
vic_run_scrapy

NEW_OFFSET=$(( OFFSET + BATCH_SIZE ))
if [ "$NEW_OFFSET" -gt "$TOTAL_LINKS" ]; then
  NEW_OFFSET=$TOTAL_LINKS
fi
python3 -c "import json; json.dump({'offset': $NEW_OFFSET, 'total': $TOTAL_LINKS}, open('$CHECKPOINT_FILE', 'w'))"
echo "Backfill checkpoint advanced to offset=$NEW_OFFSET/$TOTAL_LINKS"

if [ "$NEW_OFFSET" -ge "$TOTAL_LINKS" ]; then
  echo "Backfill complete! All $TOTAL_LINKS ideas have been crawled."
fi
