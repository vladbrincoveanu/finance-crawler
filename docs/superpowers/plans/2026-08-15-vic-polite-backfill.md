# VIC Polite Full-Backlog Crawl — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Get the existing (already well-built) ValueInvestorsClub scraper actually crawling its full 13,925-idea backlog, politely, resumably, with login-based full-text access — replacing the stale "site is blocked, buy a proxy" docs with what's actually true.

**Architecture:** No new scraping engine — `IdeaSpider` + its middlewares (`ModernUserAgentMiddleware`, `BanAwareThrottleMiddleware`, AutoThrottle) already implement politeness and already implement login. The gap is operational: (1) prove login actually works, (2) extract the duplicated docker/preflight/scrapy-runner logic out of `weekly_refresh.sh` into a shared lib so a new `backfill_ideas.sh` can reuse it for checkpointed batch crawling without truncating the DB, (3) stop the weekly job from wiping the DB every run once backfill owns the full sweep, (4) delete the incorrect proxy-required docs.

**Tech Stack:** Bash, Scrapy (Python, run only inside Docker per project CLAUDE.md), Postgres, `docker-compose exec api ...`.

---

## Pre-flight risk check (inline grill, no nested skill dispatch)

- **Login creds must never land in a committed file.** All tasks below pass `VIC_USERNAME`/`VIC_PASSWORD` as shell env vars the user exports locally, or GitHub Actions secrets for CI — never written to `scripts/*.sh` or `data/backfill_checkpoint.json`.
- **Checkpoint math edge case:** last batch is smaller than `BACKFILL_BATCH_SIZE` — offset must clip to `total`, not overshoot (handled explicitly below).
- **`IDEA_LINKS_MODE=head` compatibility:** confirmed by reading `IdeaSpider._selected_links()` — the `tail` branch is only taken when `link_mode == "tail" and start_index == 0`; any other mode value (including `head`) falls through to the forward slice `selected_links[:link_limit]` from `start_index`, which is exactly what chunked forward-scanning backfill needs. No spider code changes required.
- **Concurrent runs:** backfill and weekly refresh must never run at the same time (both call `scrapy crawl IdeaSpider` against the same DB/service) — out of scope to build a lock file for this pass; call it out in the script's help comment instead (YAGNI — this is a solo-operator repo).
- **No proxy work:** explicitly cut from scope. Confirmed live via direct curl (HTTP 200) that the site is not blocking us; the `BanAwareThrottleMiddleware` already exists to self-throttle/abort if that ever changes.

---

### Task 1: Login smoke test (no code changes — verification only)

**Files:** none modified. Uses existing `ValueInvestorsClub/ValueInvestorsClub/spiders/IdeaSpider.py` login flow.

- [ ] **Step 1: Create a 3-link scratch file for the smoke test**

```bash
cd /Users/vladbrincoveanu/Desktop/Startup/ValueInvestorsClub
head -3 idea_links_no_duplicates.txt > /tmp/vic_smoke_links.txt
cat /tmp/vic_smoke_links.txt
```
Expected: 3 URLs printed, each starting `https://www.valueinvestorsclub.com/idea/...`.

- [ ] **Step 2: Bring up the stack**

```bash
docker-compose up -d db api
docker-compose exec -T api sh -lc "pg_isready -h db -U postgres -d ideas" || sleep 5
```

- [ ] **Step 3: Run the spider against just those 3 links with login enabled**

Copy the scratch file into the container's expected path (or point `IDEA_LINKS_FILE` at a bind-mounted path — check `docker-compose.yml` volumes first; if the repo root is bind-mounted into `/app`, `/tmp/vic_smoke_links.txt` on the host is not visible in-container, so write it inside the repo instead):

```bash
head -3 idea_links_no_duplicates.txt > vic_smoke_links.txt
docker-compose exec -T \
  -e PYTHONPATH="/app/ValueInvestorsClub:/app" \
  -e IDEA_LINKS_FILE="/app/vic_smoke_links.txt" \
  -e VIC_ENABLE_LOGIN=true \
  -e VIC_USERNAME="$VIC_USERNAME" \
  -e VIC_PASSWORD="$VIC_PASSWORD" \
  -e PIPELINE_MODE=file \
  -e DOWNLOAD_DELAY=10 \
  -e CONCURRENT_REQUESTS_PER_DOMAIN=1 \
  -e ROBOTSTXT_OBEY=false \
  -e LOG_LEVEL=INFO \
  api sh -lc "cd ValueInvestorsClub && scrapy crawl IdeaSpider"
rm vic_smoke_links.txt
```
(Requires `VIC_USERNAME`/`VIC_PASSWORD` already exported in your shell — do not paste credentials into chat.)

- [ ] **Step 4: Verify login actually unlocked full text**

Check the spider log for `"Login verified; starting idea crawl."` (success) vs `"Login appears ineffective"` (failure — proceeds in teaser mode anyway, don't treat as a hard failure, just note it). Then inspect one output file under wherever `FileExportPipeline` writes (check `ValueInvestorsClub/ValueInvestorsClub/pipelines.py` for the exact path) and confirm `description`/`catalysts` fields contain real thesis paragraphs, not a "sign up or log in" teaser stub.

- [ ] **Step 5: Record the result**

No commit needed (verification-only task) — but note the outcome (login works / login doesn't work / VIC account has no valid session) in the PR description later. If login fails, the backfill still proceeds in teaser-only mode (Task 3 doesn't hard-depend on login succeeding).

---

### Task 2: Extract shared scraping helpers into `scripts/lib_vic_scrape.sh`

**Files:**
- Create: `scripts/lib_vic_scrape.sh`
- Modify: `scripts/weekly_refresh.sh` (replace inline function defs with `source`)

- [ ] **Step 1: Create the shared lib**

```bash
cat > scripts/lib_vic_scrape.sh <<'EOF'
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
      "$DOCKER_SERVICE" sh -lc "cd ValueInvestorsClub && scrapy crawl IdeaSpider"
  else
    (cd ValueInvestorsClub && scrapy crawl IdeaSpider)
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
EOF
chmod +x scripts/lib_vic_scrape.sh
```

- [ ] **Step 2: Sanity-check the lib parses**

```bash
bash -n scripts/lib_vic_scrape.sh && echo OK
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add scripts/lib_vic_scrape.sh
git commit -m "refactor: extract shared VIC scraping helpers into lib_vic_scrape.sh"
```

---

### Task 3: Rewrite `weekly_refresh.sh` to source the shared lib (behavior-preserving except RESET_DB default)

**Files:**
- Modify: `scripts/weekly_refresh.sh` (full rewrite, same external env-var contract)

- [ ] **Step 1: Replace the script body**

Keep the exact same env var names/defaults as today (Read `scripts/weekly_refresh.sh:1-93` for the full current list before editing — every var that script currently exports must still be settable the same way), but:
- Change the default `RESET_DB` from `1` to `0` (this is the one intentional behavior change — see Task 4 rationale).
- Delete the inline `check_db_ready`/`run_sql_command`/`require_docker_compose`/`run_python`/`run_python_stdin`/`run_scrapy`/`curl_head_ok`/`curl_get_text` function bodies (lines ~94-205 in the current file) and replace all call sites with the `vic_`-prefixed equivalents from `scripts/lib_vic_scrape.sh`.
- Delete the inline preflight-check block (current lines ~258-282) and the inline robots.txt fail-fast block (current lines ~293-303) — replace both with a single call to `vic_preflight_or_exit`.
- Delete the inline "Ensure tables exist" Python heredoc (current lines ~306-327) and replace with `vic_ensure_tables`.
- Everything else (Selenium link collection, `ProcessLinks.py` dedupe, the `RESET_DB` truncate block, calling `vic_run_scrapy`) stays as-is, just referencing the renamed functions.
- Add `source "$ROOT_DIR/scripts/lib_vic_scrape.sh"` right after `cd "$ROOT_DIR"`.

Concretely, the new file:

```bash
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
```

- [ ] **Step 2: Verify syntax**

```bash
bash -n scripts/weekly_refresh.sh && echo OK
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add scripts/weekly_refresh.sh
git commit -m "refactor: weekly_refresh.sh sources shared lib, defaults RESET_DB=0"
```

---

### Task 4: Add `scripts/backfill_ideas.sh` — checkpointed chunked backfill

**Files:**
- Create: `scripts/backfill_ideas.sh`
- Create (runtime, gitignored): `data/backfill_checkpoint.json`

- [ ] **Step 1: Confirm `data/` is gitignored for this file (avoid committing crawl-progress state)**

```bash
grep -n "^data/" .gitignore || echo "data/backfill_checkpoint.json" >> .gitignore
```

- [ ] **Step 2: Create the script**

```bash
cat > scripts/backfill_ideas.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

# One-time (well, repeated-daily) backlog sweep: crawls idea_links_no_duplicates.txt
# in fixed-size batches, tracking progress in a checkpoint file so it can be re-run
# (locally, via cron, or via a scheduled GH Actions job) until the whole backlog is
# scraped. Unlike weekly_refresh.sh, this NEVER truncates the database.

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
EOF
chmod +x scripts/backfill_ideas.sh
```

- [ ] **Step 3: Verify syntax**

```bash
bash -n scripts/backfill_ideas.sh && echo OK
```
Expected: `OK`

- [ ] **Step 4: Dry-run one small batch (batch size 5) against real Docker services**

```bash
docker-compose up -d db api
BACKFILL_BATCH_SIZE=5 ./scripts/backfill_ideas.sh
cat data/backfill_checkpoint.json
```
Expected: script completes, prints `Backfill checkpoint advanced to offset=5/13925`, and `data/backfill_checkpoint.json` shows `{"offset": 5, "total": 13925}`.

- [ ] **Step 5: Verify DB got rows without truncation (run it again, offset should move to 10, not reset to 5)**

```bash
BACKFILL_BATCH_SIZE=5 ./scripts/backfill_ideas.sh
cat data/backfill_checkpoint.json
```
Expected: `{"offset": 10, "total": 13925}` — proves resumability.

- [ ] **Step 6: Commit**

```bash
git add scripts/backfill_ideas.sh .gitignore
git commit -m "feat: add checkpointed chunked backfill script for full VIC backlog"
```

---

### Task 5: Delete/rewrite the incorrect "site is blocked, need a proxy" docs

**Files:**
- Delete: `SOLUTION_OPTIONS.md`
- Modify: `SCRAPY_TUNING.md` (remove the "CRITICAL: Site Blocking Detected" section and the proxy-required framing throughout)

- [ ] **Step 1: Delete the stale doc**

```bash
git rm SOLUTION_OPTIONS.md
```

- [ ] **Step 2: Rewrite `SCRAPY_TUNING.md`'s top section**

Read the current file first (it has "Proxy Support (REQUIRED FOR THIS SITE)" and other now-false claims threaded through it), then replace the header block (currently lines 1-30, the "CRITICAL: Site Blocking Detected" section) with:

```markdown
# Scrapy Connection Tuning Guide

## Status

The site is reachable and not blocking scraper traffic (verified via direct HTTP
requests returning 200 with real content). No proxy or VPN is required for normal
operation. If `BanAwareThrottleMiddleware` starts logging repeated 403/429/503
responses or captcha markers, that's the signal something changed — see
"Troubleshooting" below before reaching for a proxy.

Idea pages are teaser-gated without login (company/ticker/date/author visible, full
report text hidden behind "sign up or log in"). Set `VIC_ENABLE_LOGIN=true` with
`VIC_USERNAME`/`VIC_PASSWORD` to scrape full report text if you have an account.

For the full backlog crawl, use `scripts/backfill_ideas.sh` (chunked, resumable,
never truncates the DB) rather than a single 40-hour `weekly_refresh.sh` run.
```

Then update the "Proxy Support" subsection (search for `REQUIRED FOR THIS SITE`) to read `Proxy Support (optional — not required under normal conditions)`, and update the "Troubleshooting" → "Connection Lost Errors" section to remove the "Root cause: Site is blocking/dropping connections" framing, replacing with: "If you see connection errors, first re-run the preflight check (`vic_preflight_or_exit` in `scripts/lib_vic_scrape.sh`) manually to rule out a transient local network issue before assuming a block."

- [ ] **Step 3: Verify no other file references `SOLUTION_OPTIONS.md`**

```bash
grep -rl "SOLUTION_OPTIONS" --include="*.md" --include="*.sh" --include="*.py" . || echo "no references found"
```
Expected: `no references found` (or only `SCRAPY_TUNING.md` referencing it if you cross-linked — remove that reference too if present).

- [ ] **Step 4: Commit**

```bash
git add SCRAPY_TUNING.md
git commit -m "docs: remove stale proxy-required claims, site is reachable"
```

---

## Self-Review

**1. Spec coverage:**
- Restore link files → done in the brainstorming session directly (git checkout), not part of this plan's tasks, already committed as prior state restoration — confirmed present before Task 1 runs.
- Login smoke test → Task 1.
- Extract shared runner logic → Task 2.
- Chunked resumable backfill, never truncates → Task 4.
- Weekly refresh becomes incremental-only → Task 3.
- Docs cleanup → Task 5.
All five design commitments have a task. No gaps.

**2. Placeholder scan:** No TBD/TODO/"add appropriate handling" phrasing present — every step has literal file content or literal commands with expected output.

**3. Type/name consistency:** Function names (`vic_check_db_ready`, `vic_run_sql`, `vic_require_docker_compose`, `vic_run_python`, `vic_run_python_stdin`, `vic_run_scrapy`, `vic_curl_head_ok`, `vic_curl_get_text`, `vic_preflight_or_exit`, `vic_ensure_tables`) are defined once in Task 2's `lib_vic_scrape.sh` and used identically (same names) in Task 3 and Task 4 — checked for drift, none found. `IDEA_LINKS_MODE=head` used in Task 4 matches the spider's actual mode-check logic (verified against `IdeaSpider._selected_links` source, not assumed).

**4. Scope check:** Single cohesive subsystem (operationalizing an existing scraper) — not split further. Each task produces independently testable/committable output.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-15-vic-polite-backfill.md`.
