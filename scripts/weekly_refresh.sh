#!/usr/bin/env bash
set -euo pipefail

# Weekly ingestion helper: incrementally re-scrapes ideas (does NOT truncate the DB
# by default — see scripts/backfill_ideas.sh for the initial full-backlog sweep).
# Works locally (with/without psql) and in CI.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
source "$ROOT_DIR/scripts/lib_vic_scrape.sh"

DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_USER=${DB_USER:-postgres}
DB_PASSWORD=${DB_PASSWORD:-postgres}
DB_NAME=${DB_NAME:-ideas}
DATABASE_URL=${DATABASE_URL:-"postgresql+psycopg2://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"}
DB_WAIT_SECONDS=${DB_WAIT_SECONDS:-60}
# NOTE: RESET_DB now defaults to 0. The initial full-backlog crawl is owned by
# scripts/backfill_ideas.sh, which never truncates. Only set RESET_DB=1 here if you
# deliberately want to wipe and fully re-scrape everything in one (very long) run.
RESET_DB=${RESET_DB:-0}
RUN_SELENIUM=${RUN_SELENIUM:-0}
RUN_PROCESS_LINKS=${RUN_PROCESS_LINKS:-1}
START_DOCKER_DB=${START_DOCKER_DB:-0}
USE_DOCKER=${USE_DOCKER:-1}
DOCKER_SERVICE=${DOCKER_SERVICE:-api}
VENV=${VENV:-.venv}

export DATABASE_URL
export PGPASSWORD="$DB_PASSWORD"

if [ "$USE_DOCKER" -eq 1 ]; then
  vic_require_docker_compose
fi

if [ "$START_DOCKER_DB" -eq 1 ]; then
  echo "Starting database container via docker-compose..."
  docker-compose up -d db
fi

if [ "$USE_DOCKER" -eq 0 ]; then
  if [ ! -d "$VENV" ]; then
    if command -v uv >/dev/null 2>&1; then
      uv venv "$VENV"
    else
      PYTHON_EXEC=python
      if ! command -v python >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1; then
        PYTHON_EXEC=python3
      fi
      $PYTHON_EXEC -m venv "$VENV"
    fi
  fi
  # shellcheck disable=SC1090
  source "$VENV/bin/activate"
  if command -v uv >/dev/null 2>&1; then
    uv pip install -r requirements.txt
  else
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
  fi
fi

printf 'Waiting for database '
for i in $(seq 1 "$DB_WAIT_SECONDS"); do
  if vic_check_db_ready; then
    echo -e "\nDatabase is ready."
    break
  fi
  printf '.'
  sleep 1
done

if ! vic_check_db_ready; then
  echo -e "\nDatabase did not become ready within ${DB_WAIT_SECONDS}s." >&2
  exit 1
fi

vic_preflight_or_exit
vic_ensure_tables

if [ "$RESET_DB" -eq 1 ]; then
  echo "Truncating tables before re-scrape..."
  vic_run_sql "DO \$\$ DECLARE t text; existing text := ''; BEGIN FOREACH t IN ARRAY ARRAY['performance','catalyst','descriptions','ideas','companies','users'] LOOP IF to_regclass('public.' || t) IS NOT NULL THEN existing := existing || quote_ident(t) || ', '; END IF; END LOOP; IF existing <> '' THEN existing := left(existing, length(existing) - 2); EXECUTE 'TRUNCATE TABLE ' || existing || ' RESTART IDENTITY CASCADE'; END IF; END \$\$;"
fi

if [ "$RUN_SELENIUM" -eq 1 ]; then
  echo "Collecting fresh idea links with Selenium (scraper.py)..."
  vic_run_python scraper.py
else
  echo "Skipping Selenium link scrape (set RUN_SELENIUM=1 to enable)."
fi

if [ "$RUN_PROCESS_LINKS" -eq 1 ]; then
  echo "Deduplicating link files..."
  vic_run_python ProcessLinks.py
fi

echo "Running Scrapy spider to populate DB..."
vic_run_scrapy

echo "Weekly refresh complete."
