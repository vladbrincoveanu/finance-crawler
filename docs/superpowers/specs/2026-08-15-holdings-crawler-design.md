---
title: Holdings Crawler — Dataroma + HedgeFollow
date: 2026-08-15
status: approved
ui_scope: false
graph_scope: false
test_scope: true
---

# Holdings Crawler Design — Dataroma + HedgeFollow

Companion pipeline to the existing VIC idea-scraper. Full diagrams: `2026-08-15-holdings-crawler-design.html` (open locally).

## 1. Why a separate pipeline from VIC

VIC scrapes dated idea writeups (one author, one stock thesis, one date). Dataroma and HedgeFollow are 13F holdings aggregators: investor × quarter × company snapshots. Different shape, different cadence. Decision: two independent pipelines sharing infra (Scrapy project, DB, politeness helpers) but not the data model. Optional future join: by ticker/investor-name only, not a schema dependency.

## 2. Architecture

New spiders (`DataromaSpider.py`, `HedgeFollowSpider.py`) live alongside `IdeaSpider.py` in the same Scrapy project. They yield a new `HoldingItem` (separate from `ValueinvestorsclubItem`) into a new `HoldingPipeline`, which writes to new `Investor`/`Holding` tables. Existing `Company` table is reused (create-if-missing by ticker). No changes to `Idea`/`Description`/`Catalysts`/`Performance`/`User`.

## 3. Data model

- `Investor`: id, name, source (`dataroma`|`hedgefollow`), source_slug, profile_url
- `Holding`: id, investor_id FK, company_id FK, quarter_date, shares, value_usd, pct_portfolio, activity
- `Company`: existing table, reused

Dedup key for `Holding` upserts: `(investor_id, company_id, quarter_date)`.

**Investor identity across sources:** Dataroma and HedgeFollow are separate `Investor` rows even for the same real-world fund (e.g. Berkshire Hathaway) — no automatic merge. HedgeFollow's curated-subset selection will attempt name matching against Dataroma's list for crawl-list construction only (manual/fuzzy match, reviewed by hand, not a runtime join). This avoids silent misattribution if names don't line up exactly (e.g. "Berkshire Hathaway" vs "Warren Buffett - Berkshire Hathaway Inc").

## 4. Crawl flow & scope

Dataroma first, then HedgeFollow.

| Site | Scope v1 | Order | Known blocker |
|---|---|---|---|
| Dataroma | 83 curated superinvestors, via `/m/home.php` → `/m/holdings.php?m=CODE` (current) + `/m/hist/p_hist.php?f=CODE` (quarter history) | 1st | ModSecurity WAF rejects plain `curl` — needs browser-like headers, same class of issue as VIC's blocking |
| HedgeFollow | Curated subset (~80–200, name-matched to Dataroma where feasible) | 2nd | Untested at scale; full 10,000+ fund directory is out of scope for v1 |

Politeness: reuse `lib_vic_scrape.sh` patterns — browser-like UA/headers, conservative rate limit, checkpointed/resumable crawl.

**Known risk carried over from VIC:** the VIC scraper is currently blocked by its target site (ConnectionLost on all requests). First implementation step for each new spider is a manual probe (Scrapy shell / browser-header curl) to confirm access before writing full spider logic.

**Accepted risk — ToS not reviewed:** robots.txt for both sites is permissive (no Disallow rules found), but each site's Terms of Service page (linked in footer) was not read for scraping-specific restrictions. Proceeding on the same terms as the existing VIC scraper (public data, conservative rate limits, non-commercial research use). Flagging so this can be revisited if either site's ToS text turns out to explicitly prohibit automated collection.

## 5. Testing

- Unit tests: fixture HTML → parsed `HoldingItem`, mirroring existing VIC spider test style.
- Schema validation script extended to cover `Investor`/`Holding` tables.
- No UI/frontend surface in this spec — backend/data pipeline only.

## Module design blocks

### Module: DataromaSpider
- **Responsibility:** Crawl Dataroma's 83 superinvestor list + per-investor current + historical holdings pages, yield `HoldingItem`s
- **Interface:** Standard Scrapy spider; output → `HoldingPipeline`
- **Dependencies:** Shared politeness config (rate limit, UA/headers), `HoldingItem`
- **Size target:** <200 lines; parsing helpers factored out if needed

### Module: HedgeFollowSpider
- **Responsibility:** Crawl curated subset of HedgeFollow funds, same output shape as DataromaSpider
- **Interface:** Standard Scrapy spider; output → `HoldingPipeline`
- **Dependencies:** Curated fund list (Dataroma investor names + HedgeFollow fund directory, hand-reviewed match), shared politeness config
- **Size target:** <200 lines

### Module: HoldingPipeline
- **Responsibility:** Upsert `Investor`/`Company`/`Holding` rows from `HoldingItem`s, dedupe by `(investor_id, company_id, quarter_date)`
- **Interface:** Scrapy item pipeline; reads `HoldingItem`, writes via SQLAlchemy session
- **Dependencies:** SQLAlchemy models (`Investor`, `Holding`, existing `Company`)
- **Size target:** <200 lines
