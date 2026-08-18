---
title: VIC comments and source crawl views
date: 2026-08-18
status: pending-review
ui_scope: true
---

# Goal

Expose comments already crawled for each ValueInvestorsClub idea, and make the three existing local source views unambiguous for checking extracted data:

- ValueInvestorsClub ideas: `/articles`
- HedgeFollow holdings: `/holdings/hedgefollow`
- Dataroma holdings: `/holdings/dataroma`

`/sources` remains the verification hub for the latest crawl run, parser counters, accepted sample, and links to those public UI views.

The main product dashboard is `/` (`HomePage`). Telemetry is a separate operations surface: Grafana at `http://localhost:3001/d/vic-ingestion` when the Compose `observability` profile is running.

# Current Evidence

The crawler and persistence path already contains the required VIC comment data:

- `ValueInvestorsClub/ValueInvestorsClub/spiders/IdeaSpider.py::_extract_comments()` extracts comment blocks when VIC exposes them.
- `ValueInvestorsClub/ValueInvestorsClub/items.py` carries `comments` on each scraped item.
- `ValueInvestorsClub/ValueInvestorsClub/pipelines.py::SqlPipeline.process_item()` writes each item comment to `comments`.
- `ValueInvestorsClub/ValueInvestorsClub/models/Comment.py` stores `idea_id`, `author`, `posted_at`, and `text`.
- `alembic/versions/20260816_0001_initial_identity_schema.py` defines `comments.idea_id` as a foreign key to `ideas.id`.

The missing path is after persistence:

- `api/models/__init__.py` does not import `Comment`.
- `api/schemas/schemas.py::IdeaDetailResponse` has no comments field.
- `api/routes/ideas.py::get_idea_detail()` does not query comments.
- `frontend/src/types/api.ts` and `IdeaDetailPage.tsx` have no comment contract or view.

The source verification route and source-specific public routes already exist:

- `api/routes/crawl.py` returns exactly three source records and their `public_route` values.
- `frontend/src/pages/SourcesPage.tsx` renders those records.
- `frontend/src/pages/SourceHoldingsPage.tsx` queries curated rows by `source`.

Telemetry is implemented outside the React app:

- `api/routes/health.py` exposes `/metrics`.
- Prometheus scrapes `api:8010/metrics`.
- Grafana loads `observability/grafana/dashboards/ingestion.json`.
- OpenTelemetry request export is conditional on `OTEL_EXPORTER_OTLP_ENDPOINT`.
- The React app has no telemetry page or navigation link today.

# Design

## Comment Data Contract

Use the existing relational ownership. A comment belongs to one VIC idea through `comments.idea_id`; it is not embedded in a holding record or shared across ideas.

Add an additive response model:

```text
CommentResponse
  id: string
  author: string
  posted_at: string
  text: string
```

Add `comments: list[CommentResponse]` to `IdeaDetailResponse`, using a default factory so every successful response contains an array. The detail route explicitly maps `Comment` rows with `Comment.idea_id == idea_id`, orders deterministically by `posted_at.asc()` and `id.asc()`, and returns an empty list when no rows exist.

The endpoint is part of the existing unauthenticated read-only API. This change exposes only comments already stored from the public crawl; it adds no posting, moderation, or identity resolution. Stored comment text is cleaned and capped by the existing ingestion path; the UI preserves the newlines that survive persistence but does not claim to restore raw source formatting.

No database migration is needed. The table and foreign key already exist.

## Idea Detail UI

Render an `Investor discussion` section on both `/articles/:id` and `/ideas/:id`, below the thesis and catalysts content. Show:

- comment count in the section heading;
- author, when available;
- posted timestamp, when available;
- stored cleaned text with any surviving newlines preserved;
- an explicit `No comments were captured for this crawl` empty state.

The empty state distinguishes absent crawled comments from an API error. If VIC hides comments because authentication is unavailable, the UI reports the observed empty result rather than inventing or inferring discussion.

## Source Crawl Views

Keep source provenance boundaries intact:

- `/sources` is the crawl verification hub.
- `/articles` and `/articles/:id` are the local VIC crawled-idea views, with comments on the detail page.
- `/holdings/hedgefollow` is the local curated HedgeFollow view.
- `/holdings/dataroma` is the local curated Dataroma view.

Make each source card show its literal local path alongside an exact matching CTA href. Source-specific holdings pages continue requesting `/holdings/?source=<source>` and display curated rows only. Public holdings are cumulative curated data; `/sources` reports the latest crawl run separately. Staged, unresolved, and quarantined source records remain outside public tables.

Add an operations link to the main product dashboard for the Grafana ingestion dashboard. The link is external to React and may be unavailable until the observability Compose profile is started. The product dashboard remains `/`; Grafana is the telemetry dashboard, not a replacement for the product UI or `/sources`.

# Error Handling

- Detail API failure continues to use the existing error state and back link.
- Successful detail responses always include `comments`, including `[]`.
- Missing comments never fail the idea detail request.
- Source crawl warnings continue to use the existing `partial`, `failed`, empty-run, and no-run states.
- No new crawler execution is triggered by the UI change.
- If Grafana is unavailable, the product dashboard remains usable and the link does not turn telemetry absence into a product-data error.

# Testing

Add or update tests for:

- API model import and schema serialization of `Comment`.
- `GET /ideas/{id}` returning comments tied to the requested `idea_id`, preserving text and deterministic order.
- `GET /ideas/{id}` returning an empty comments list when an idea has no comments.
- TypeScript API contract compatibility.
- Idea detail rendering of comments and the empty state.
- Source verification cards showing and linking the exact three local routes.
- Existing HedgeFollow and Dataroma source filters remaining intact, including exclusion of pending, invalid, and quarantined rows.
- Main dashboard rendering the Grafana telemetry link without making telemetry availability a hard dependency.
- `/metrics` export and the existing Grafana dashboard configuration remaining discoverable.

Run targeted backend and frontend tests first, then Docker-based project tests, schema validation, lint/build checks, and Playwright screenshots at 375px, 768px, and 1280px widths.

# Acceptance Criteria

1. A stored VIC comment appears only on the detail page of its owning idea.
2. `GET /ideas/{id}` returns the owning idea's comments with no extra request from the frontend.
3. Ideas without comments show a truthful empty state.
4. `/sources` links clearly to `/articles`, `/holdings/hedgefollow`, and `/holdings/dataroma`.
5. HedgeFollow and Dataroma pages continue showing curated, source-filtered data with source URLs.
6. `/` is identified as the main product dashboard and links to the Grafana ingestion dashboard.
7. API, frontend, schema, lint, build, and visual verification pass, or any pre-existing failure is reported explicitly.

# Non-Goals

- No new comments table or migration.
- No comment author identity resolution.
- No comment editing, moderation, or posting.
- No cross-source search or merged VIC/holding table.
- No attempt to bypass VIC authentication or recover comments that the source did not expose.

# Rollback

The change is additive. Removing the comments field and detail section restores current behavior without changing stored data or crawler output. Source routes and curated holding boundaries remain unchanged.
