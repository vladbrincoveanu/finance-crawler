#!/usr/bin/env bash
# Shared helpers for VIC scraping scripts (weekly_refresh.sh, backfill_ideas.sh).
# Callers must set DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME/USE_DOCKER/DOCKER_SERVICE
# before sourcing (this file only sets defaults for unset vars).

: "${DB_HOST:=localhost}"
: "${DB_PORT:=5432}"
: "${DB_USER:=postgres}"
: "${DB_PASSWORD:=postgres}"
: "${DB_NAME:=ideas}"
: "${USE_DOCKER:=1}"
: "${DOCKER_SERVICE:=api}"
: "${ROBOTSTXT_OBEY:=false}"
: "${CONCURRENT_REQUESTS_PER_DOMAIN:=1}"
: "${DOWNLOAD_DELAY:=12}"
: "${RANDOMIZE_DOWNLOAD_DELAY:=true}"
: "${RETRY_TIMES:=10}"
: "${DOWNLOAD_TIMEOUT:=120}"
: "${DNS_TIMEOUT:=60}"
: "${LOG_LEVEL:=INFO}"
: "${LOGSTATS_INTERVAL:=30}"
: "${AUTOTHROTTLE_ENABLED:=true}"
: "${AUTOTHROTTLE_START_DELAY:=10}"
: "${AUTOTHROTTLE_MAX_DELAY:=60}"
: "${AUTOTHROTTLE_TARGET_CONCURRENCY:=1.0}"
: "${HTTP_PROXY:=}"
: "${HTTPS_PROXY:=}"
: "${COOKIES_ENABLED:=true}"
: "${MODERN_USER_AGENT:=true}"
: "${IDEA_LINKS_START:=0}"
: "${IDEA_LINKS_LIMIT:=0}"
: "${IDEA_LINKS_MODE:=tail}"
: "${BAN_AWARE_THROTTLE_ENABLED:=true}"
: "${BAN_BACKOFF_BASE_SECONDS:=60}"
: "${BAN_BACKOFF_MAX_SECONDS:=900}"
: "${BAN_MAX_RETRIES_PER_REQUEST:=2}"
: "${BAN_ABORT_AFTER_HITS:=8}"
: "${ROBOTS_FAIL_FAST:=true}"
: "${PREFLIGHT_FAIL_FAST:=true}"
: "${VIC_USERNAME:=}"
: "${VIC_PASSWORD:=}"
: "${VIC_ENABLE_LOGIN:=false}"

vic_check_db_ready() {
  if command -v pg_isready >/dev/null 2>&1; then
    pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose exec -T -e PGPASSWORD="$DB_PASSWORD" db pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1
  else
    echo "Warning: No pg_isready or docker-compose found. Skipping check."
    return 0
  fi
}

vic_run_sql() {
  local CMD="$1"
  if command -v psql >/dev/null 2>&1; then
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$CMD"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose exec -T -e PGPASSWORD="$DB_PASSWORD" db psql -U "$DB_USER" -d "$DB_NAME" -c "$CMD"
  else
    echo "Error: Cannot run SQL (neither psql nor docker-compose found)." >&2
    exit 1
  fi
}

vic_require_docker_compose() {
  if ! command -v docker-compose >/dev/null 2>&1; then
    echo "Error: docker-compose is required when USE_DOCKER=1." >&2
    exit 1
  fi
}

vic_run_python() {
  if [ "$USE_DOCKER" -eq 1 ]; then
    docker-compose exec -T "$DOCKER_SERVICE" python "$@"
  else
    python "$@"
  fi
}

vic_run_python_stdin() {
  if [ "$USE_DOCKER" -eq 1 ]; then
    docker-compose exec -T "$DOCKER_SERVICE" python -
  else
    python -
  fi
}

vic_run_scrapy() {
  local spider_name="${1:-IdeaSpider}"
  if [ "$USE_DOCKER" -eq 1 ]; then
    docker-compose exec -T \
      -e PYTHONPATH="/app/ValueInvestorsClub:/app" \
      -e ROBOTSTXT_OBEY="$ROBOTSTXT_OBEY" \
      -e CONCURRENT_REQUESTS_PER_DOMAIN="$CONCURRENT_REQUESTS_PER_DOMAIN" \
      -e DOWNLOAD_DELAY="$DOWNLOAD_DELAY" \
      -e RANDOMIZE_DOWNLOAD_DELAY="$RANDOMIZE_DOWNLOAD_DELAY" \
      -e RETRY_TIMES="$RETRY_TIMES" \
      -e DOWNLOAD_TIMEOUT="$DOWNLOAD_TIMEOUT" \
      -e DNS_TIMEOUT="$DNS_TIMEOUT" \
      -e LOG_LEVEL="$LOG_LEVEL" \
      -e LOGSTATS_INTERVAL="$LOGSTATS_INTERVAL" \
      -e AUTOTHROTTLE_ENABLED="$AUTOTHROTTLE_ENABLED" \
      -e AUTOTHROTTLE_START_DELAY="$AUTOTHROTTLE_START_DELAY" \
      -e AUTOTHROTTLE_MAX_DELAY="$AUTOTHROTTLE_MAX_DELAY" \
      -e AUTOTHROTTLE_TARGET_CONCURRENCY="$AUTOTHROTTLE_TARGET_CONCURRENCY" \
      -e HTTP_PROXY="$HTTP_PROXY" \
      -e HTTPS_PROXY="$HTTPS_PROXY" \
      -e COOKIES_ENABLED="$COOKIES_ENABLED" \
      -e MODERN_USER_AGENT="$MODERN_USER_AGENT" \
      -e IDEA_LINKS_START="$IDEA_LINKS_START" \
      -e IDEA_LINKS_LIMIT="$IDEA_LINKS_LIMIT" \
      -e IDEA_LINKS_MODE="$IDEA_LINKS_MODE" \
      -e BAN_AWARE_THROTTLE_ENABLED="$BAN_AWARE_THROTTLE_ENABLED" \
      -e BAN_BACKOFF_BASE_SECONDS="$BAN_BACKOFF_BASE_SECONDS" \
      -e BAN_BACKOFF_MAX_SECONDS="$BAN_BACKOFF_MAX_SECONDS" \
      -e BAN_MAX_RETRIES_PER_REQUEST="$BAN_MAX_RETRIES_PER_REQUEST" \
      -e BAN_ABORT_AFTER_HITS="$BAN_ABORT_AFTER_HITS" \
      -e VIC_USERNAME="$VIC_USERNAME" \
      -e VIC_PASSWORD="$VIC_PASSWORD" \
      -e VIC_ENABLE_LOGIN="$VIC_ENABLE_LOGIN" \
      -e PIPELINE_MODE="$PIPELINE_MODE" \
      "$DOCKER_SERVICE" sh -lc "cd ValueInvestorsClub && scrapy crawl $spider_name"
  else
    (cd ValueInvestorsClub && scrapy crawl "$spider_name")
  fi
}

vic_curl_head_ok() {
  local url="${1:-https://www.valueinvestorsclub.com/}"
  if [ "$USE_DOCKER" -eq 1 ]; then
    docker-compose exec -T "$DOCKER_SERVICE" sh -lc "curl -f -s -m 10 --head '$url' >/dev/null 2>&1"
  else
    curl -f -s -m 10 --head "$url" >/dev/null 2>&1
  fi
}

vic_curl_get_text() {
  local url="$1"
  if [ "$USE_DOCKER" -eq 1 ]; then
    docker-compose exec -T "$DOCKER_SERVICE" sh -lc "curl -s -m 10 '$url' || true"
  else
    curl -s -m 10 "$url" || true
  fi
}

vic_preflight_or_exit() {
  if [ "${SKIP_PREFLIGHT:-0}" -eq 0 ]; then
    echo "Checking connectivity to valueinvestorsclub.com..."
    if vic_curl_head_ok "https://www.valueinvestorsclub.com/"; then
      echo "Site is reachable."
    else
      echo "Warning: Cannot reach valueinvestorsclub.com from the spider execution environment (USE_DOCKER=${USE_DOCKER})." >&2
      echo "Set SKIP_PREFLIGHT=1 to skip this check." >&2
      if [ "${PREFLIGHT_FAIL_FAST}" != "false" ]; then
        echo "Error: preflight failed (PREFLIGHT_FAIL_FAST=${PREFLIGHT_FAIL_FAST}). Exiting early to avoid a long hang." >&2
        exit 3
      fi
    fi
  fi

  if [ "${VIC_ENABLE_LOGIN}" = "true" ] || [ "${VIC_ENABLE_LOGIN}" = "1" ]; then
    if [ -z "${VIC_USERNAME:-}" ] || [ -z "${VIC_PASSWORD:-}" ]; then
      echo "Error: VIC_ENABLE_LOGIN=true but VIC_USERNAME/VIC_PASSWORD are not set." >&2
      exit 4
    fi
  fi

  if [ "${ROBOTS_FAIL_FAST}" != "false" ] && [ "${ROBOTSTXT_OBEY}" = "true" ]; then
    local robots_txt
    robots_txt="$(vic_curl_get_text 'https://www.valueinvestorsclub.com/robots.txt')"
    if echo "$robots_txt" | grep -Eq 'Disallow:[[:space:]]*/[[:space:]]*$'; then
      echo "Error: ROBOTSTXT_OBEY=true but robots.txt disallows all crawling (Disallow: /)." >&2
      echo "Set ROBOTSTXT_OBEY=false to run the scraper, or leave it true to respect robots.txt." >&2
      exit 2
    fi
  fi
}

vic_ensure_tables() {
  vic_run_python_stdin <<'PY'
import os
from sqlalchemy import create_engine
try:
    from ValueInvestorsClub.models import Base  # noqa: F401
except ImportError:
    from ValueInvestorsClub.ValueInvestorsClub.models import Base  # noqa: F401
try:
    engine = create_engine(os.environ["DATABASE_URL"], future=True)
    meta = None
    if hasattr(Base, "Base") and hasattr(Base.Base, "metadata"):
        meta = Base.Base.metadata
    elif hasattr(Base, "metadata"):
        meta = Base.metadata
    else:
        raise RuntimeError(f"Could not locate SQLAlchemy metadata on Base={Base!r}")
    meta.create_all(engine)
except Exception as e:
    print(f"Error initializing tables: {e}")
PY
}
