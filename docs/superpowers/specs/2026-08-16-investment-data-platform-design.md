---
title: Investment data platform, identity curation, and retrieval
date: 2026-08-16
status: design-review
ui_scope: true
graph_scope: false
test_scope: true
visual_companion: ./2026-08-16-investment-data-platform-design.html
excalidraw: ./2026-08-16-investment-data-platform-design.excalidraw
---

# Goal

Build a trustworthy investment-data foundation that can combine VIC ideas with Dataroma and HedgeFollow-style ownership evidence without polluting curated data with malformed rows, unresolved identities, duplicate entities, or unsupported LLM conclusions.

The first implementation milestone proves one Dataroma investor and one HedgeFollow fund through the available source path, database, API, UI, provenance links, and observability. RAG is a later consumer of curated data, not a shortcut around ingestion quality.

# Approved Decisions

- Local Docker PostgreSQL is the only database environment for this phase.
- Runtime schema changes use versioned Alembic migrations; tests may create isolated schemas automatically.
- `Company` is a canonical company-level chapter parent.
- `Security` is a tradable instrument belonging to a Company; ticker is an alias, not a Company identity.
- `Investor` is the reporting fund or institution; `PortfolioManager` is separate metadata.
- Source identities are preserved; curated entities are unique reviewed identities.
- Source, staging, quarantine, and curated data use separate physical table families.
- Every Phase 1 identity mapping requires human approval.
- DeepInfra is a review assistant for entity resolution only; it never writes mappings or blocks raw ingestion.
- DeepInfra requests use strict JSON Schema, temperature `0`, bounded output, minimal candidate evidence, and a stable cacheable prompt prefix.
- DeepInfra is the only Phase 1 model provider; there is no LM Studio, local-model, or alternate-provider fallback. An outage leaves the item pending for manual review.
- Curated facts are rebuilt from immutable source facts plus approved mappings.
- Partial promotion is allowed: valid resolved rows may promote while unresolved rows remain excluded and the run is marked partial.
- Public APIs and RAG read curated data only.
- The first HedgeFollow proof target is Berkshire Hathaway paired with Dataroma `BRK`; the source adapter crawls the selected fund page and history routes through the shared pipeline.
- The first instrument scope is common stock; options are a later Security extension.
- RAG starts with local embeddings in `pgvector`, PostgreSQL keyword search, rank fusion, and reranking.
- RAG answers are not persisted as domain facts in the initial design.

# Domain Model

The project glossary is maintained in [`CONTEXT.md`](../../../CONTEXT.md).

## Source identities

Source identities preserve what each website actually reported:

- `source_investors`: `(source, source_key)` plus raw and normalized names.
- `source_portfolio_managers`: source-specific person metadata associated with a source investor.
- `source_securities`: source ticker, company label, exchange/market data, share-class data, and source URL.
- `source_documents`: deduplicated raw HTML, JSON, or text payloads keyed by content hash.
- `source_fetches`: immutable fetch occurrences linking URL, status, timestamp, payload, parser version, and run.
- `source_holding_snapshots`: source investor, source security, period, raw values, source activity, and evidence links.

Source records may have duplicate-looking names across websites. That is expected and remains traceable until identity review.

## Curated identities

Curated identities are the only entities eligible for public APIs, company chapters, and retrieval:

- `curated_investors`: one reviewed reporting fund/institution per canonical identity.
- `curated_portfolio_managers`: optional people linked to curated investors.
- `curated_companies`: one reviewed company-level chapter parent.
- `curated_securities`: one reviewed tradable instrument linked to a Company; supports ticker, exchange, and share class.
- `investor_aliases` and `security_aliases`: approved source-to-canonical mappings.
- `identity_candidates`: ranked candidate matches with method, score, and evidence.
- `identity_decisions`: versioned human approve/reject/defer records.

Example: Dataroma `Warren Buffett - Berkshire Hathaway` and HedgeFollow `Berkshire Hathaway / Warren Buffett` become one curated Investor, one separate PortfolioManager, and source-specific aliases. `BRK.B`, `BRK-B`, `BRK.A`, and `BRK-A` are not merged as Companies; they require Security-level mapping.

## Holdings and history

- `curated_holding_snapshots` stores investor/security/period facts and retains `source_observation_id`.
- Cross-source reports remain separate facts even when they map to the same curated Investor and Security.
- Exact duplicates from the same source are deduplicated by source identity, security, period, and source observation key.
- `curated_holding_events` derives `open`, `add`, `reduce`, `hold`, `exit`, or `unknown` from ordered snapshots.
- Missing periods or source coverage gaps produce `unknown` and incomplete coverage, never an inferred sell.
- Source activity such as `Buy`, `Add`, and `Reduce` remains source evidence; derived events are separate facts.

# Data Quality Architecture

## Layers

1. **Source layer** stores immutable evidence and source-native observations.
2. **Staging layer** holds normalized candidates for one ingestion run.
3. **Quarantine layer** holds invalid, incomplete, or unresolved material with reasons and evidence.
4. **Identity layer** maps source records to canonical Investor, Company, and Security entities.
5. **Curated layer** holds only validated facts with approved identity mappings.
6. **Retrieval layer** later projects curated facts into typed company sections.

Quarantine does not feed public APIs or retrieval. It exists for human diagnosis and parser improvement.

## Ingestion flow

```text
source adapter
  -> immutable fetch/document
  -> parse source observation
  -> deterministic normalization
  -> source-specific validation
  -> source-key and content deduplication
  -> staging by ingestion_run
  -> candidate identity search
  -> DeepInfra suggestion, if needed
  -> human mapping decision
  -> partial or complete curated promotion
  -> derived event projection
```

The parser never asks an LLM to invent numeric facts, dates, tickers, or activity. LLM use is limited to ranked identity suggestions after deterministic candidate generation.

## Validation rules

- Required fields are source-specific and explicit.
- Numeric fields are parsed strictly; invalid values are quarantined, not defaulted to zero.
- Dates and reporting periods must parse to valid period boundaries.
- Activity values must map to an allowed source/derived enum or become `unknown`.
- Source URLs and fetch status are stored with each evidence record.
- A zero-row run fails unless the source explicitly proves the target is empty.
- Rejection thresholds are source-specific. A run above its threshold is unhealthy and cannot promote its rejected rows.
- Valid resolved rows may promote in a partial run; completeness is visible to API/UI consumers.
- A telemetry or DeepInfra outage does not block data capture; affected review items remain pending.

## Promotion and replay

Promotion is transactional per source/run. Mapping changes never rewrite source evidence. Rebuilding a curated projection from source observations plus approved mappings is the correction path.

All source workers are idempotent. No worker performs a global database truncate. Source-scoped locks prevent two promotions for the same source from racing while allowing independent source runs to coexist.

# Source Workflows

## Dataroma

1. Run a read-only baseline against one known investor before refactoring the current pipeline.
2. Use Berkshire `BRK` for the first cross-source identity test.
3. Capture current page, history pages, fetch metadata, and parsed quarterly observations.
4. Route observations through source/staging/identity/curated layers.
5. Verify the Dataroma page with real DOM data, provenance links, and non-empty history.

## HedgeFollow

The first target is `/funds/Berkshire+Hathaway`, paired with Dataroma `BRK`. The page exposes fund/manager metadata, common-stock holdings, quarters, trades, and ownership history. Options are excluded from the first proof and receive a later Security extension.

The adapter reads the selected fund page, holdings pages, and history routes. Fixtures are maintained alongside the live parser so validation stays deterministic while the live Berkshire proof verifies the complete crawl-to-UI path.

## VIC bridge

The current VIC pipeline writes ticker-backed legacy `companies` rows and `ideas.company_id` foreign keys. That path remains operational temporarily so another worker can continue crawling.

An explicit bridge maps legacy ticker records to curated Security and Company identities. New curated APIs and retrieval ignore unmapped legacy rows. A later migration moves VIC ingestion to the shared source/staging/promotion contract.

# Entity Resolution

Resolution is identity mapping, not data generation:

1. Normalize source names, tickers, suffixes, and punctuation.
2. Search exact identifiers, aliases, normalized strings, and trigram candidates.
3. Return up to five ranked candidates with evidence and scores.
4. Allow `no safe match` and `create new` outcomes.
5. Send only minimal candidate evidence and opaque IDs to DeepInfra.
6. Use a versioned static system prompt, strict JSON Schema, temperature `0`, bounded output, and candidate data in the variable tail.
7. Track `prompt_cache_key`, prompt version, model version, token counts, and cached-token counts.
8. Require human approval for every new Phase 1 mapping.
9. Persist the decision and rebuild affected curated projections.

If DeepInfra is unavailable, the deterministic candidate list and source observation remain available for manual review. No alternate model is invoked and ingestion of unrelated rows continues.

DeepInfra credentials are environment-only (`DEEPINFRA_API_KEY`). The exposed token from the design conversation must be revoked and rotated; it is not included anywhere in this repository.

# API and UI

## Public API

- `GET /holdings/?source=dataroma|hedgefollow` returns curated holding rows with source, Investor, Company, Security, period, activity, completeness, and provenance.
- `GET /companies/{curated_company_id}` returns Company, Securities, curated VIC ideas, and ownership history.
- `GET /investors/{curated_investor_id}` returns reporting-fund identity, manager metadata, source aliases, and holdings.
- Existing legacy endpoints remain available during the bridge period but are not the source for new retrieval.

## Public pages

- `/holdings/dataroma`
- `/holdings/hedgefollow`
- `/holdings`
- Future `/companies/{id}` company chapter page

All holdings pages share one table component. Each row exposes canonical Company and Security, reporting Investor, source, period, activity, completeness, and a source link with last-verified status.

## Review pages

Review endpoints and UI require an env-only admin token and localhost binding. Public pages never show unresolved or quarantined rows.

- Identity review: top candidates, scores, evidence, approve/reject/defer.
- Quarantine review: reason, raw evidence, parser output, reprocess.
- Every review action is auditable.

# Observability

The observability stack is a Docker Compose profile, configured and tested from day one but not forced into every normal app boot:

- Direct OpenTelemetry SDK export from application code; no collector daemon.
- Prometheus for metrics, with OTLP receiver enabled locally.
- Loki for operational logs.
- Tempo for traces.
- Grafana for dashboards and alerts.
- Uptime Kuma for API, frontend, database, and crawler-heartbeat checks.
- One configurable outbound webhook for alerts; secrets remain environment-only.
- Seven-day retention for telemetry stores.
- Durable ingestion audit, source evidence, and quarantine remain in PostgreSQL.
- Telemetry failures fail open; data paths continue and emit health signals.
- Optional external crash tracking is limited to uncaught application exceptions.

Phase 1 spans and metrics cover crawler fetch/parse/validate/promote, FastAPI requests and database calls, Postgres health, and frontend uncaught errors. GenAI semantic conventions begin when the agent/RAG phase starts.

# RAG Phase 2

RAG is built only after Phase 1 data gates pass:

1. Project each curated Company into a non-embedded parent chapter.
2. Generate deterministic typed child sections for VIC ideas, investor ownership timelines/events, and Company/Security metadata.
3. Store local embeddings in PostgreSQL `pgvector`.
4. Apply structured metadata filters first when a query names Company, Investor, Security, source, period, or event type.
5. Run PostgreSQL full-text keyword search (`tsvector` and `ts_rank_cd`) and vector search. Keep a provider-neutral keyword interface so a local true-BM25 extension can replace or augment the initial FTS baseline without changing the retrieval contract.
6. Normalize scores and fuse rankings with reciprocal rank fusion.
7. Apply a reranker behind a provider-neutral interface.
8. Assemble a capped prompt containing only top evidence sections, metadata, and citation IDs.
9. Use a read-only agent that cites retrieved evidence and abstains when evidence is missing or incomplete.
10. Log retrieval runs and simple human usefulness/citation-correctness labels for evaluation. Generated answers remain transient; do not persist synthesis, auto-train, or auto-rewrite curated data.

No persisted LLM synthesis or agent memory is part of the initial RAG scope.

# Implementation Streams

The umbrella design decomposes into separate plans:

1. **Foundation and identity**: Alembic, source/staging/quarantine/curated schema, Company/Security/Investor identities, legacy bridge, direct OTel profile.
2. **Dataroma validation**: baseline, adapter contract, Berkshire proof, promotion, API, DOM, provenance, and quality metrics.
3. **HedgeFollow validation**: fund-page/history adapter, Berkshire UI, common-stock Security contract, deterministic fixtures, and source-specific tests.
4. **VIC coexistence and review**: legacy bridge verification, identity review UI, quarantine UI, DeepInfra adjudication, and rebuild workflow.
5. **RAG**: local embeddings, pgvector, PostgreSQL keyword search, fusion, reranking, prompt assembly, and retrieval evaluation.

# Phase 1 Acceptance Gates

- Empty local PostgreSQL reaches the target schema through one versioned migration command.
- Existing Dataroma baseline is recorded before the new pipeline changes behavior.
- One Dataroma Berkshire investor passes fetch, staging, validation, identity review, curated promotion, API, DOM, and provenance-link checks.
- One HedgeFollow Berkshire crawl passes the same path for common-stock holdings.
- Curated output has one reviewed Company and one reviewed reporting Investor, with Security-level ticker aliases and no duplicate canonical identities.
- Invalid and unresolved rows are absent from public APIs and RAG inputs and visible in review storage.
- Partial runs expose completeness instead of pretending to be full history.
- VIC bridge and holdings runs coexist without global truncation or duplicate source facts.
- Grafana dashboards show run status, accepted/rejected/duplicate counts, latency, errors, and database health.
- Uptime checks and configurable alerts fire on database-down, run-failed, and quality-threshold conditions.
- No secret or API token is present in tracked files, docs, fixtures, prompts, or logs.

RAG is not considered complete in Phase 1. It starts only after these gates pass.
