---
title: Deploy Dataroma holdings crawler + minimal holdings UI
date: 2026-08-16
status: approved
ui_scope: true
graph_scope: false
test_scope: true
---

## Scope

Two parts:

1. **Deploy/try:** run `DataromaSpider` against the live site via local docker-compose, capped to 5 investors first (`DATAROMA_INVESTOR_LIMIT`), `PIPELINE_MODE=holdings` so `HoldingPipeline` upserts into Postgres.
2. **UI:** one new page `/holdings` — flat table of investor + ticker + shares + value + quarter + activity, backed by one new API endpoint. No drill-down, no filters, no charts.

User confirmed via AskUserQuestion: small test batch (5 investors), one flat-table page, local docker-compose only (no CI/weekly_ingest.yml wiring this pass).

## Pre-existing bug found and fixed

Live-testing (`scrapy list` inside the api container) showed `DataromaSpider` failed to import (`ModuleNotFoundError: No module named 'ValueInvestorsClub.ValueInvestorsClub'`) — the spider and pipeline used double-nested imports (`ValueInvestorsClub.ValueInvestorsClub.x`) that only resolve under pytest's `pythonpath = .`. Scrapy's own runtime sets `PYTHONPATH=/app/ValueInvestorsClub:/app`, which needs single-level imports (`ValueInvestorsClub.x`) — this is the same convention the working `pipelines.py`/`items.py` already use. Fixed with a try/except import fallback in `DataromaSpider.py` and `holding_pipeline.py` (try single-level first, since that's the real deployment path; fall back to double-level for pytest). Verified both `scrapy list` and the full pytest suite (27/27) pass. Committed separately from this spec.

## Data flow

```
DataromaSpider (live crawl, 5 investors)
  -> HoldingItem
  -> HoldingPipeline (upsert)
  -> Postgres: investors, companies, holdings
  -> GET /holdings/ (api/routes/holdings.py)
  -> HoldingsPage.tsx (/holdings route)
```

## Crawl limit mechanism

New env var `DATAROMA_INVESTOR_LIMIT`, read in `parse_home`, same convention as `IDEA_LINKS_LIMIT` in `IdeaSpider.py`. Default `0` = no limit (full 83 investors). Set to `5` for this run via `vic_run_scrapy DataromaSpider` invocation env.

## API endpoint

`GET /holdings/?skip=0&limit=100` in new `api/routes/holdings.py`, mirroring `api/routes/companies.py`:
- Join `Holding` + `Investor` + `Company`.
- Response: `List[HoldingResponse]` — `investor_name, ticker, company_name, quarter_date, shares, value_usd, pct_portfolio, activity`.
- Requires: add `Investor`, `Holding` to `api/models/__init__.py` (currently missing); add `HoldingResponse` to `api/schemas/schemas.py`; register `holdings_router` in `api/main.py`.

## Frontend

- `frontend/src/types/api.ts`: add `Holding` interface.
- `frontend/src/api/apiService.ts`: add `holdingsApi.getHoldings(params)`, mirroring `companiesApi`.
- `frontend/src/hooks/useHoldings.ts`: new hook, mirrors `useCompanies.ts`.
- `frontend/src/pages/HoldingsPage.tsx`: plain Chakra `Table`, no search/filter UI (per "keep it really really simple" — even simpler than `CompaniesPage`, which has search).
- `frontend/src/App.tsx`: add `<Route path="holdings" element={<HoldingsPage />} />`.
- `frontend/src/components/Layout.tsx`: add nav link.

### Module: DataromaSpider investor-limit slicing
- **Responsibility:** cap how many investors get crawled per run via env var.
- **Interface:** reads `DATAROMA_INVESTOR_LIMIT` in `parse_home`, slices investor list before yielding requests.
- **Dependencies:** none new.
- **Size target:** +5 lines to existing spider.

### Module: api/routes/holdings.py
- **Responsibility:** read-only endpoint returning joined holding rows.
- **Interface:** `GET /holdings/` — query params skip/limit, returns `List[HoldingResponse]`.
- **Dependencies:** `api.database.get_db`, `api.models.Investor/Holding/Company`, `api.schemas.HoldingResponse`.
- **Size target:** ~30 lines, mirrors `companies.py`.

### Module: frontend/src/pages/HoldingsPage.tsx
- **Responsibility:** render holdings table.
- **Interface:** no props, fetches on mount via `useHoldings`, renders `<Table>`.
- **Dependencies:** `useHoldings` hook, Chakra UI components — same stack as `CompaniesPage.tsx`.
- **Size target:** under 100 lines.

## Error handling

- Crawl: existing ban-aware throttle/retry settings apply unchanged (shared `settings.py`). `scripts/probe_dataroma.sh` runs before the crawl; abort if it fails.
- API: standard FastAPI validation; empty list if no data yet (not a 404 — matches `companies`/`users` endpoints).

## Testing

`test_scope: true`.
- New: `api/tests/test_holdings_api.py` — endpoint returns joined rows, empty-list case (matches `test_ideas_api.py` conventions).
- Frontend: Playwright DOM check on `/holdings` — table renders with expected row count once seeded, per this project's mandatory per-cycle DOM-verification rule.

## Out of scope (explicitly)

- No GitHub Actions / `weekly_ingest.yml` wiring this pass.
- No investor detail page, no filters/search, no charts.
- No full 83-investor crawl this pass — 5 only, to verify the live pipeline first.
