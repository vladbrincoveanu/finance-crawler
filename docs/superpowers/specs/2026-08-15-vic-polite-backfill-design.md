---
title: VIC Polite Full-Backlog Crawl
date: 2026-08-15
status: approved
ui_scope: false
graph_scope: false
test_scope: false
---

## Problem

The user asked whether the scraper described in the ValueInvestorsClub README actually
works, and wanted a plan to crawl all ~13,925 ideas politely without getting banned,
including a look at proxies.

## Investigation findings

1. **The site is not blocking us.** Direct `curl` to `https://www.valueinvestorsclub.com/`
   returns HTTP 200 with real content right now. `SOLUTION_OPTIONS.md` and the "CRITICAL:
   Site Blocking Detected" section of `SCRAPY_TUNING.md` (both untracked files already in
   the repo from an earlier session) assert the site is unreachable and recommend paid
   residential proxies / VPN / Tor. That diagnosis does not hold up against a live check
   and is being removed as part of this work — no proxy is needed.
2. **The scraper's politeness engineering is already solid**: `DOWNLOAD_DELAY` 10-12s
   (randomized ±50%), `CONCURRENT_REQUESTS_PER_DOMAIN=1`, Scrapy `AutoThrottle`, a
   `BanAwareThrottleMiddleware` that detects 403/429/503/captcha markers, backs off
   exponentially, and self-aborts the spider after repeated blocks, a realistic Chrome UA,
   and a full login flow (CSRF token → form POST → session cookie) for members-only full
   report text.
3. **The actual blocker was operational, not the site**: `idea_links_no_duplicates.txt`
   and all 8 dated raw-link files were deleted in the working tree (uncommitted). The
   spider had zero URLs to crawl. These are tracked files from the initial commit and
   were restored via `git checkout` during this session — no scraping was needed to
   recover them.
4. **Content is teaser-gated without login** (company/ticker/date/author visible; full
   thesis text hidden behind "sign up or log in"). The spider already has a login path
   implemented but untested against a live account.
5. **VIC's own `robots.txt` says `Disallow: /`.** `weekly_refresh.sh` already
   deliberately overrides this (`ROBOTSTXT_OBEY=false`) with a comment explaining why —
   this repo's purpose is scraping public idea listings for research, consistent with the
   README's stated intent, while remaining polite about load.

## Decisions (confirmed with user via clarifying questions)

- **Link files:** restore via `git checkout` (done). Do not currently re-run the
  Selenium link collector to pick up newer ideas — that's a follow-up, not blocking.
- **Crawl pacing:** at ~10s/request single-concurrency, a full 13,925-link crawl takes
  ~38-40 hours continuous. User chose **chunked resumable batches** over one long
  continuous run — crawl in daily/on-demand batches via a checkpoint file, not a single
  multi-day process.
- **Login:** user has a VIC account and wants **full report text via login**
  (`VIC_ENABLE_LOGIN=true` + `VIC_USERNAME`/`VIC_PASSWORD` env vars, never committed).
  This must be smoke-tested against a handful of real ideas before trusting it for the
  full backfill, since the login flow has not been exercised against a live session yet.

## Design

### Module: Login smoke test
- **Responsibility:** Prove the existing login flow (`IdeaSpider.parse_login` /
  `after_login` / `verify_login`) actually unlocks full report text, before relying on
  it for a 40-hour-equivalent backfill.
- **Interface:** Manual Docker Compose run against a 3-link scratch file with
  `VIC_ENABLE_LOGIN=true`; inspect spider log + one output file for full thesis text vs.
  a teaser stub.
- **Dependencies:** live VIC account credentials (user-supplied, env-only).
- **Size target:** verification only, no new code.

### Module: `scripts/lib_vic_scrape.sh` (shared helpers)
- **Responsibility:** Single source of truth for the docker-exec/scrapy-run/preflight/
  DB-readiness logic currently duplicated inline in `weekly_refresh.sh`, so a second
  script (`backfill_ideas.sh`) can reuse it without copy-pasting ~150 lines.
- **Interface:** Bash functions (`vic_check_db_ready`, `vic_run_sql`,
  `vic_require_docker_compose`, `vic_run_python`, `vic_run_python_stdin`,
  `vic_run_scrapy`, `vic_curl_head_ok`, `vic_curl_get_text`, `vic_preflight_or_exit`,
  `vic_ensure_tables`), driven by env vars the caller sets before sourcing.
- **Dependencies:** `docker-compose`, existing `scrapy crawl IdeaSpider` env-var
  contract (unchanged).
- **Size target:** ~200 lines, function definitions only, no top-level script logic.

### Module: `scripts/backfill_ideas.sh` (checkpointed chunked backfill)
- **Responsibility:** Crawl the full idea-link backlog in fixed-size batches, tracking
  progress in `data/backfill_checkpoint.json` (gitignored), resumable across runs/days,
  never truncating the database.
- **Interface:** `BACKFILL_BATCH_SIZE` env var (default 500); reads/advances
  `{"offset": N, "total": M}` in the checkpoint file; delegates the actual crawl to
  `vic_run_scrapy` with `IDEA_LINKS_START`/`IDEA_LINKS_LIMIT`/`IDEA_LINKS_MODE=head`
  computed from the checkpoint.
- **Dependencies:** `scripts/lib_vic_scrape.sh`, `idea_links_no_duplicates.txt`.
- **Size target:** ~80 lines, chunk math + checkpoint I/O only.

### Module: `weekly_refresh.sh` (incremental-only going forward)
- **Responsibility:** Stop truncating the whole DB every week now that
  `backfill_ideas.sh` owns the full sweep — `RESET_DB` default flips from `1` to `0`.
  Keeps its existing job of optionally re-collecting links (Selenium) and deduplicating
  before an incremental scrape.
- **Interface:** unchanged env-var contract, now sourcing the shared lib instead of
  defining its own copies of the same functions.
- **Dependencies:** `scripts/lib_vic_scrape.sh`.
- **Size target:** same file, function bodies removed (net smaller).

### Module: Docs cleanup
- **Responsibility:** Remove the incorrect "site is blocked, buy a proxy" narrative
  (`SOLUTION_OPTIONS.md` deleted; `SCRAPY_TUNING.md`'s critical-status section rewritten)
  so future sessions don't re-chase a nonexistent block or spend money on proxies that
  were never needed.

## Explicitly out of scope

- Proxy/VPN/Tor setup — not needed; the `BanAwareThrottleMiddleware` already exists as
  the correct response mechanism if real blocking is ever observed.
- CAPTCHA solving, fingerprint spoofing, or any other anti-detection tooling — not
  applicable, no such defenses are active on the target site.
- Concurrent-run locking between `weekly_refresh.sh` and `backfill_ideas.sh` — solo
  operator repo, YAGNI; documented as a caller responsibility instead.
- Re-running the Selenium link collector to find newer ideas — follow-up, not blocking
  the backfill of the already-known 13,925 links.

## Approval

Design was presented inline in conversation with three explicit clarifying questions
(link-file restoration approach, crawl pacing strategy, login vs. teaser-only scraping).
User answered all three via `AskUserQuestion`, selecting: restore via `git checkout`,
chunked resumable batches, and login-enabled full-text scraping. These answers
constitute approval of the design above. Implementation plan written to
`docs/superpowers/plans/2026-08-15-vic-polite-backfill.md`.
