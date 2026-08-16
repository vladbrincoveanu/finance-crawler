# Investment Data Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace direct source-to-legacy-table writes with an identity-first, provenance-preserving ingestion path, then prove Dataroma and HedgeFollow Berkshire holdings through curated APIs, UI, and local observability.

**Architecture:** Keep the existing VIC `companies`/`ideas`/`holdings` tables operational during the bridge, but add separate source, staging, quarantine, identity, and curated table families. Source adapters write immutable evidence and normalized observations; deterministic candidate search plus human-approved decisions promote only resolved rows to curated Company, Security, Investor, PortfolioManager, snapshot, and derived-event records.

**Tech Stack:** Python 3.11, SQLAlchemy 2, Alembic, PostgreSQL 14 with `pgvector` in Phase 2, Scrapy, FastAPI, Pydantic 2, React 18, TypeScript, React Query, Chakra UI, Playwright, pytest, Jest, Cypress, Docker Compose, OpenTelemetry, Prometheus, Loki, Tempo, Grafana, and Uptime Kuma.

---

## Scope and Execution Rules

- Tasks 1-9 are Phase 1 and must pass the acceptance gates in the design spec before Task 10 starts.
- Task 10 is the gated Phase 2 retrieval implementation, not an excuse to expose staging or unresolved rows earlier.
- Run each task test-first: write a test that fails for the stated reason, run it, implement the smallest change, rerun the focused test, then run the relevant regression set.
- Commit each task separately with the commit subject specified in that task.
- Never call `Base.metadata.create_all()` from a runtime crawler, API startup path, or runtime pipeline. Isolated tests may create temporary schemas; production and integration databases use Alembic.
- Never truncate a shared database from a crawler or promotion worker. Source-scoped locks and idempotent keys are required.
- Never place `DEEPINFRA_API_KEY` values in code, fixtures, prompts, logs, screenshots, or commits. Rotate the token exposed during design before any implementation request.
- DeepInfra is the only Phase 1 model provider. A timeout or outage leaves identity work pending for manual review; it never invokes LM Studio or another model.
- The graph scope flag is false, so no graph rebuild task is required.

## Current File Map

| Area | Existing boundary | Planned responsibility |
|---|---|---|
| Legacy ORM | `ValueInvestorsClub/ValueInvestorsClub/models/*.py` | Preserve VIC tables; add focused source/identity/curated models beside them. |
| Legacy persistence | `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/pipelines.py` and `holding_pipeline.py` | Keep VIC compatibility; route holdings through the new ingestion service and remove runtime schema creation. |
| Scrapy settings | `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/settings.py` | Add explicit `source` pipeline mode without changing the default VIC idea mode. |
| Dataroma | `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/spiders/DataromaSpider.py` | Emit source observations and immutable page evidence. |
| HedgeFollow | No existing spider | Add Berkshire fund, holdings, quarter, and trade/history adapter with fixtures. |
| API | `api/main.py`, `api/routes/`, `api/schemas/` | Serve curated holdings and protected identity/quarantine review endpoints. |
| Frontend | `frontend/src/pages/HoldingsPage.tsx`, `frontend/src/api/`, `frontend/src/hooks/` | Add source-specific curated pages, shared table, provenance, completeness, and review views. |
| Tests | `api/tests/`, `ValueInvestorsClub/tests/`, `frontend/src/tests/`, Cypress | Add migration, parser, quality, identity, API, UI, visual, and coverage gates. |
| Operations | `docker-compose.yml`, `api/database/connection.py` | Add migration command, health/readiness, direct OTLP, and observability profile. |

## Schema Contract

The initial migration must create the existing legacy tables plus these new tables. IDs use UUID strings (`String(36)`) rather than database-specific UUID columns so the isolated SQLite tests can exercise model relationships; PostgreSQL indexes and constraints remain authoritative for production.

| Table | Required columns and constraints |
|---|---|
| `ingestion_runs` | `id`, `source`, `target`, `status`, `parser_version`, `started_at`, `finished_at`, `rows_seen`, `rows_accepted`, `rows_rejected`, `rows_duplicate`, `error_message`; status values `running`, `complete`, `partial`, `failed`. |
| `source_documents` | `id`, `source`, `content_hash`, `canonical_url`, `content_type`, `status_code`, `body`, `fetched_at`; unique `(source, content_hash)`. |
| `source_fetches` | `id`, `run_id`, `document_id`, `url`, `status_code`, `fetched_at`, `parser_version`; foreign keys to run and document. |
| `source_investors` | `id`, `source`, `source_key`, `name_raw`, `name_normalized`, `profile_url`; unique `(source, source_key)`. |
| `source_portfolio_managers` | `id`, `source_investor_id`, `name_raw`, `name_normalized`, `source_url`; foreign key to source investor. |
| `source_securities` | `id`, `source`, `source_key`, `ticker_raw`, `company_name_raw`, `exchange`, `share_class`, `source_url`; unique `(source, source_key)`. |
| `source_holding_snapshots` | `id`, `run_id`, `source_investor_id`, `source_security_id`, `period`, `shares`, `value_usd`, `pct_portfolio`, `source_activity`, `source_observation_key`, `fetch_id`, `raw_payload`; unique `(source, source_observation_key)`. |
| `staging_holding_snapshots` | `id`, `run_id`, `source_snapshot_id`, normalized numeric fields, `validation_status`, `identity_status`, `reason_code`; unique `(run_id, source_snapshot_id)`. |
| `quarantine_records` | `id`, `run_id`, `source`, `record_type`, `source_record_id`, `reason_code`, `reason_detail`, `raw_payload`, `review_status`, `created_at`, `reviewed_at`; statuses `open`, `reprocessed`, `rejected`, `accepted`. |
| `curated_investors` | `id`, `display_name`, `normalized_name`, `status`, `created_at`; unique normalized identity. |
| `portfolio_managers` | `id`, `display_name`, `normalized_name`; unique normalized name. |
| `curated_investor_managers` | `investor_id`, `manager_id`, `source`, `evidence_id`; unique `(investor_id, manager_id, source)`. |
| `curated_companies` | `id`, `display_name`, `normalized_name`, `status`, `created_at`; unique normalized identity. |
| `curated_securities` | `id`, `company_id`, `primary_ticker`, `exchange`, `share_class`, `status`; foreign key to curated company. |
| `investor_aliases` | `source_investor_id`, `curated_investor_id`, `decision_id`; one current mapping per source investor. |
| `security_aliases` | `source_security_id`, `curated_security_id`, `decision_id`; one current mapping per source security. |
| `identity_candidates` | `id`, `run_id`, `entity_type`, `source_record_id`, `candidate_entity_id`, `deterministic_score`, `model_score`, `evidence_json`, `status`; retain all candidate calculations. |
| `identity_decisions` | `id`, `candidate_id`, `entity_type`, `decision`, `curated_entity_id`, `reviewer_id`, `model_name`, `model_version`, `prompt_version`, `created_at`; decisions `approve`, `reject`, `defer`, `create_new`. |
| `curated_holding_snapshots` | `id`, `source_snapshot_id`, `curated_investor_id`, `curated_security_id`, `period`, `shares`, `value_usd`, `pct_portfolio`, `source_activity`, `completeness`; unique `source_snapshot_id`. |
| `curated_holding_events` | `id`, `curated_investor_id`, `curated_security_id`, `period`, `event_type`, `evidence_snapshot_ids`, `confidence`; event values `open`, `add`, `reduce`, `hold`, `exit`, `unknown`. |

---

### Task 1: Establish the Alembic Migration Boundary

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/script.py.mako`
- Modify: `requirements.txt`
- Test: `api/tests/test_alembic_config.py`

- [ ] **Step 1: Capture the current database baseline before changing runtime schema behavior**

Run:

```bash
docker compose up -d db
docker compose exec -T db pg_dump -U postgres -d ideas --schema-only > /tmp/value-investors-club-before-alembic.sql
```

Expected: the dump is created outside the repository and contains the current legacy tables. Do not commit the dump.

- [ ] **Step 2: Write the Alembic configuration test**

Create `api/tests/test_alembic_config.py`:

```python
from alembic.config import Config
from pathlib import Path


def test_alembic_config_has_repo_script_location_and_default_url():
    config = Config("alembic.ini")
    assert Path(config.get_main_option("script_location")).name == "alembic"
    assert "postgresql+psycopg2" in config.get_main_option("sqlalchemy.url")
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `pytest api/tests/test_alembic_config.py::test_alembic_config_has_repo_script_location_and_default_url -q`

Expected: FAIL because `alembic.ini` does not exist yet.

- [ ] **Step 4: Implement the Alembic environment**

Use `alembic/env.py` to:

```python
from alembic import context
from sqlalchemy import engine_from_config, pool

from ValueInvestorsClub.ValueInvestorsClub.models.Base import Base

target_metadata = Base.metadata
```

The file must support offline and online modes and prefer the `DATABASE_URL` environment variable over the URL in `alembic.ini`. `alembic.ini` uses the local default `postgresql+psycopg2://postgres:postgres@localhost/ideas` only when the environment variable is absent. Task 2 adds the new model-module imports before metadata is read.

Add `alembic>=1.13.0` to `requirements.txt` so the API migration service and local command use the same installed version.

- [ ] **Step 5: Run the scaffold checks**

Run:

```bash
pytest api/tests/test_alembic_config.py -q
alembic --help
```

Expected: the configuration test passes and Alembic prints its command help. No database upgrade is run until the model metadata and initial revision exist in Task 2.

- [ ] **Step 6: Commit**

```bash
git add alembic.ini alembic/env.py alembic/script.py.mako requirements.txt api/tests/test_alembic_config.py
git commit -m "feat: establish Alembic migration boundary"
```

---

### Task 2: Add Focused Source, Identity, and Curated ORM Models

**Files:**
- Create: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/models/ingestion.py`
- Create: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/models/source.py`
- Create: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/models/identity.py`
- Create: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/models/curated.py`
- Create: `alembic/versions/20260816_0001_initial_identity_schema.py`
- Create: `api/tests/test_migrations.py`
- Modify: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/models/__init__.py`
- Modify: `api/models/__init__.py`
- Modify: `alembic/env.py`
- Modify: `api/tests/setup_test_db.py`
- Modify: `docker-compose.yml`
- Test: `api/tests/test_identity_models.py`
- Test: `ValueInvestorsClub/tests/models/test_identity_models.py`
- Test: `api/tests/test_migrations.py`

- [ ] **Step 1: Write relationship and constraint tests**

Create `api/tests/test_identity_models.py` with tests for:

```python
from datetime import date
from decimal import Decimal

from ValueInvestorsClub.ValueInvestorsClub.models.curated import (
    CuratedCompany,
    CuratedHoldingSnapshot,
    CuratedInvestor,
    CuratedSecurity,
)
from ValueInvestorsClub.ValueInvestorsClub.models.source import (
    SourceHoldingSnapshot,
    SourceInvestor,
    SourceSecurity,
)


def test_curated_security_belongs_to_company(db_session):
    company = CuratedCompany(display_name="Berkshire Hathaway", normalized_name="berkshire hathaway")
    security = CuratedSecurity(primary_ticker="BRK.B", company=company, share_class="B")
    investor = CuratedInvestor(display_name="Berkshire Hathaway", normalized_name="berkshire hathaway")
    db_session.add_all([company, security, investor])
    db_session.commit()

    assert security.company.display_name == "Berkshire Hathaway"
    assert investor.display_name == "Berkshire Hathaway"


def test_source_observation_retains_source_identity_and_period(db_session):
    source_investor = SourceInvestor(
        source="dataroma",
        source_key="BRK",
        name_raw="Warren Buffett - Berkshire Hathaway",
        name_normalized="warren buffett berkshire hathaway",
    )
    source_security = SourceSecurity(
        source="dataroma",
        source_key="AAPL",
        ticker_raw="AAPL",
        company_name_raw="Apple Inc.",
    )
    observation = SourceHoldingSnapshot(
        source="dataroma",
        source_investor=source_investor,
        source_security=source_security,
        period=date(2026, 6, 30),
        shares=227917808,
        value_usd=Decimal("65950296000.00"),
        pct_portfolio=Decimal("22.04"),
        source_activity="hold",
        source_observation_key="dataroma:BRK:AAPL:2026-06-30",
    )
    db_session.add(observation)
    db_session.commit()

    assert db_session.query(SourceHoldingSnapshot).count() == 1
    assert observation.source_observation_key.endswith("2026-06-30")
```

Add a test that inserting the same `(source, source_observation_key)` twice raises `IntegrityError`. Add a test that two `SourceSecurity` rows with the same source ticker but different source values remain distinct when their `source` differs.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest api/tests/test_identity_models.py ValueInvestorsClub/tests/models/test_identity_models.py -v`

Expected: FAIL because the new model modules and tables do not exist.

- [ ] **Step 3: Implement the models as four focused modules**

Keep module responsibilities separate:

- `ingestion.py`: `IngestionRun`, `SourceDocument`, `SourceFetch`, `StagingHoldingSnapshot`, and `QuarantineRecord`.
- `source.py`: `SourceInvestor`, `SourcePortfolioManager`, `SourceSecurity`, and `SourceHoldingSnapshot`.
- `identity.py`: `CuratedInvestor`, `PortfolioManager`, `CuratedCompany`, `CuratedSecurity`, aliases, candidates, and decisions.
- `curated.py`: `CuratedHoldingSnapshot` and `CuratedHoldingEvent`.

Use SQLAlchemy 2 `Mapped` annotations, `Numeric` for money and percentages, `Date` for reporting periods, `Text` for raw HTML, and `JSON` for parser payload/evidence. Use explicit `ForeignKey` columns and named `UniqueConstraint` objects. Do not add relationships from legacy `Company` to `CuratedCompany`; the bridge is an explicit service keyed by legacy ticker.

The source snapshot model must retain `source_activity` exactly as normalized from the source and must never derive an event during insertion. The curated event model stores derived event type plus the source snapshot IDs used to derive it.

Export all new classes from both `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/models/__init__.py` and `api/models/__init__.py`. Update `alembic/env.py` to import the four new model modules before reading metadata. Add the one-shot `migrate` service to `docker-compose.yml`, make `api` depend on it completing successfully, and change `api/tests/setup_test_db.py` to run `alembic upgrade head` for Postgres integration setup while keeping `Base.metadata.create_all` only in isolated SQLite fixtures.

Generate the initial revision with:

```bash
DATABASE_URL=sqlite:///./migration-autogen.db alembic revision --autogenerate -m "initial identity schema"
```

Inspect the revision before applying it. It must create all existing legacy tables and every table listed in the Schema Contract; remove any accidental `drop_table`, global data delete, or runtime-only operation.

- [ ] **Step 4: Run focused model and migration tests**

Run:

```bash
pytest api/tests/test_identity_models.py ValueInvestorsClub/tests/models/test_identity_models.py -v
pytest api/tests/test_migrations.py -v
docker compose run --rm migrate
docker compose exec db psql -U postgres -d ideas -c '\dt'
```

Expected: all tests PASS, the Postgres migration exits `0`, and `\dt` lists both legacy and identity-first tables.

- [ ] **Step 5: Commit**

```bash
git add ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/models/ingestion.py ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/models/source.py ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/models/identity.py ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/models/curated.py ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/models/__init__.py api/models/__init__.py alembic/env.py alembic/versions/20260816_0001_initial_identity_schema.py api/tests/test_identity_models.py ValueInvestorsClub/tests/models/test_identity_models.py api/tests/test_migrations.py api/tests/setup_test_db.py docker-compose.yml
git commit -m "feat: add identity-first data models"
```

---

### Task 3: Implement Source Evidence, Validation, Quarantine, and Promotion

**Files:**
- Create: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/ingestion/__init__.py`
- Create: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/ingestion/contracts.py`
- Create: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/ingestion/evidence.py`
- Create: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/ingestion/quality.py`
- Create: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/ingestion/promotion.py`
- Create: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/ingestion/events.py`
- Modify: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/holding_pipeline.py`
- Modify: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/settings.py`
- Test: `ValueInvestorsClub/tests/ingestion/test_quality.py`
- Test: `ValueInvestorsClub/tests/ingestion/test_promotion.py`

- [ ] **Step 1: Define the adapter-neutral observation contract**

Create `ingestion/contracts.py` with strict Pydantic models matching these shapes:

```python
class SourcePage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Literal["dataroma", "hedgefollow"]
    url: AnyUrl
    status_code: int
    content_type: str
    body: bytes
    fetched_at: datetime
    parser_version: str


class SourceHoldingObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Literal["dataroma", "hedgefollow"]
    investor_key: str
    investor_name: str
    portfolio_manager_name: str | None = None
    security_key: str
    ticker: str
    company_name: str
    instrument_type: Literal["common_stock", "option"] = "common_stock"
    exchange: str | None = None
    share_class: str | None = None
    period: date
    shares: int | None = Field(default=None, ge=0)
    value_usd: Decimal | None = Field(default=None, ge=0)
    pct_portfolio: Decimal | None = Field(default=None, ge=0, le=100)
    source_activity: str | None = None
    source_url: AnyUrl
    source_observation_key: str
    document_hash: str
    raw_payload: dict[str, Any]
```

The model rejects empty source keys, invalid periods, negative numeric values, and unknown fields. It does not default invalid numeric text to zero.

- [ ] **Step 2: Write failing quality and promotion tests**

Create tests covering these exact cases:

```python
def test_invalid_numeric_value_goes_to_quarantine(service, run):
    result = service.stage_raw(run, raw_observation_with(value_usd="not-money"))
    assert result.status == "quarantined"
    assert result.reason_code == "invalid_numeric"


def test_duplicate_source_observation_is_counted_without_second_fact(service, run):
    first = service.stage(run, valid_observation("dataroma:BRK:AAPL:2026-06-30"))
    second = service.stage(run, valid_observation("dataroma:BRK:AAPL:2026-06-30"))
    assert first.status == "staged"
    assert second.status == "duplicate"
    assert service.count_source_snapshots(run.id) == 1


def test_promotion_excludes_unresolved_rows(service, approved_mapping, unresolved_row):
    promoted = service.promote(run_id="run-1", approved_mappings=[approved_mapping])
    assert promoted.accepted == 1
    assert promoted.pending_identity == 1
    assert service.public_curated_count() == 1


def test_event_projection_marks_missing_period_as_unknown(service):
    events = service.project_events([snapshot("2026-06-30"), snapshot("2025-12-31")])
    assert any(event.event_type == "unknown" for event in events)
```

Use factory functions in the test module for valid observations and rows; keep the factories deterministic and do not use network calls.

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest ValueInvestorsClub/tests/ingestion -v`

Expected: FAIL because the ingestion service and quality result types do not exist.

- [ ] **Step 4: Implement the ingestion service**

Implement these methods in `ingestion/evidence.py`, `quality.py`, and `promotion.py`:

```python
class IngestionService:
    def start_run(self, source: str, target: str, parser_version: str) -> IngestionRun: ...
    def record_document(self, run_id: str, page: SourcePage) -> SourceDocument: ...
    def stage_raw(self, run: IngestionRun, raw_observation: Mapping[str, Any]) -> StageResult: ...
    def stage(self, run: IngestionRun, observation: SourceHoldingObservation) -> StageResult: ...
    def promote(self, run_id: str, approved_mappings: list[ApprovedMapping]) -> PromotionResult: ...
    def project_events(self, snapshots: Sequence[CuratedHoldingSnapshot]) -> list[CuratedHoldingEvent]: ...
    def finish_run(self, run_id: str) -> IngestionRun: ...
```

`record_document` calculates SHA-256 from the exact response body, upserts by `(source, content_hash)`, and records every fetch separately. `stage` normalizes names/tickers, validates values, writes source and staging rows in one transaction, and creates a quarantine record for every rejection. `promote` only reads rows with `validation_status=valid` and approved Investor/Security mappings, writes curated snapshots idempotently, and leaves unresolved rows pending. A zero-row run is failed unless the adapter explicitly marks its target empty. A run with accepted and pending rows is `partial`.

`project_events` compares ordered snapshots only when adjacent periods are known. A missing period emits `unknown`; it never emits `exit` from absence. Use source snapshot IDs in the event evidence JSON.

Remove `Base.Base.metadata.create_all(self.engine)` from `holding_pipeline.py`. Make the pipeline call `IngestionService` and preserve a compatibility mode that can populate legacy `Investor`/`Company`/`Holding` rows only from an explicit approved bridge command, never from raw input. Add `PIPELINE_MODE=source` to `settings.py`; leave `sql` as the current VIC idea default and `holdings` as a compatibility alias during migration.

- [ ] **Step 5: Run focused and regression tests**

Run:

```bash
pytest ValueInvestorsClub/tests/ingestion -v
pytest ValueInvestorsClub/tests/test_holding_pipeline.py ValueInvestorsClub/tests/models/test_holding_models.py -v
```

Expected: new quality tests pass, existing tests still pass after their assertions are updated to distinguish source/curated rows from legacy bridge rows.

- [ ] **Step 6: Commit**

```bash
git add ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/ingestion ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/holding_pipeline.py ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/settings.py ValueInvestorsClub/tests/ingestion ValueInvestorsClub/tests/test_holding_pipeline.py
git commit -m "feat: add source quality and promotion pipeline"
```

---

### Task 4: Add Deterministic Identity Resolution, Review Decisions, and DeepInfra Adjudication

**Files:**
- Create: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/identity/__init__.py`
- Create: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/identity/candidates.py`
- Create: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/identity/decisions.py`
- Create: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/identity/deepinfra.py`
- Create: `api/routes/review.py`
- Modify: `api/routes/__init__.py`
- Modify: `api/schemas/schemas.py`
- Modify: `requirements.txt`
- Modify: `requirements-dev.txt`
- Test: `ValueInvestorsClub/tests/identity/test_candidates.py`
- Test: `ValueInvestorsClub/tests/identity/test_deepinfra.py`
- Test: `api/tests/test_review_api.py`

- [ ] **Step 1: Write deterministic candidate tests**

Create `ValueInvestorsClub/tests/identity/test_candidates.py`:

```python
def test_security_candidates_normalize_ticker_aliases(candidate_search):
    candidates = candidate_search.security_candidates(
        source="hedgefollow",
        ticker="BRK-B",
        company_name="Berkshire Hathaway",
    )
    assert candidates[0].candidate_type == "security"
    assert candidates[0].reasons
    assert len(candidates) <= 5


def test_candidate_search_can_return_no_safe_match(candidate_search):
    assert candidate_search.security_candidates("dataroma", "UNKNOWN", "Unknown Co") == []
```

Candidate search must check exact source aliases, normalized identifiers, normalized names, and PostgreSQL trigram similarity in that order. It returns no more than five candidates and never creates a canonical row.

- [ ] **Step 2: Write the DeepInfra contract test with a mocked transport**

Create `ValueInvestorsClub/tests/identity/test_deepinfra.py`:

```python
def test_deepinfra_returns_strict_resolution_suggestion(httpx_mock, monkeypatch):
    monkeypatch.setenv("DEEPINFRA_API_KEY", "test-only")
    httpx_mock.add_response(
        url="https://api.deepinfra.com/v1/openai/chat/completions",
        json={
            "choices": [{"message": {"content": '{"decision":"approve","candidate_id":"security-1","confidence":0.99,"reason_codes":["ticker_alias"]}'}}],
            "usage": {"prompt_tokens": 120, "completion_tokens": 25, "prompt_tokens_details": {"cached_tokens": 90}},
        },
    )

    suggestion = DeepInfraAdjudicator().suggest(entity_type="security", source_record=record(), candidates=[candidate()])

    assert suggestion.decision == "approve"
    assert suggestion.candidate_id == "security-1"
    assert suggestion.cached_tokens == 90
```

Add tests for invalid JSON Schema output, HTTP 500, timeout, and missing `DEEPINFRA_API_KEY`. Every failure must return a pending result without selecting a fallback provider.

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest ValueInvestorsClub/tests/identity -v`

Expected: FAIL because candidate search, the adjudicator, and the structured result types do not exist.

Add `pytest-httpx>=0.30.0` to `requirements-dev.txt` before implementing the mocked transport tests.

- [ ] **Step 4: Implement candidate and decision services**

Use these stable interfaces:

```python
class CandidateSearch:
    def investor_candidates(self, source_record_id: str) -> list[IdentityCandidate]: ...
    def security_candidates(self, source: str, ticker: str, company_name: str) -> list[IdentityCandidate]: ...


class DeepInfraAdjudicator:
    model = "deepseek-ai/DeepSeek-V4-Flash-0731"
    base_url = "https://api.deepinfra.com/v1/openai"

    def suggest(
        self,
        entity_type: Literal["investor", "security"],
        source_record: dict[str, Any],
        candidates: Sequence[IdentityCandidate],
    ) -> ResolutionSuggestion: ...
```

The prompt system prefix contains the policy, schema, examples, model/prompt version, and the rules "identity suggestion only", "never invent facts", and "never write the database". Candidate evidence and opaque IDs appear in the variable tail. Send strict JSON Schema, temperature `0`, bounded output, and `prompt_cache_key=f"{model}:{prompt_version}:{entity_type}"`. Record prompt version, model version, prompt/completion/cached token counts, and request status. Use a short-lived `httpx.Client` per request and add `httpx` explicitly to `requirements.txt`.

Do not add an LM Studio client, a second provider, or retry-to-another-provider branch. On timeout, non-2xx response, invalid JSON, or schema mismatch, persist an `identity_candidates` row with `status=pending` and return control to human review.

Implement decision writes as append-only `identity_decisions`. Only an approved human decision creates/updates `investor_aliases` or `security_aliases`; `create_new` creates the canonical entity in the same transaction as the decision.

- [ ] **Step 5: Add protected review endpoints**

Add `GET /review/identity`, `POST /review/identity/{candidate_id}/decision`, `GET /review/quarantine`, and `POST /review/quarantine/{record_id}/reprocess` to `api/routes/review.py`. Require an env-only `REVIEW_ADMIN_TOKEN` and reject requests unless the API is bound to localhost in review mode. Return candidate evidence, deterministic scores, model suggestion metadata, and source links. Never return raw unresolved rows from public holdings routes.

- [ ] **Step 6: Run tests and commit**

Run:

```bash
pytest ValueInvestorsClub/tests/identity api/tests/test_review_api.py -v
```

Expected: all candidate, DeepInfra failure, decision-audit, and review-auth tests PASS.

```bash
git add ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/identity api/routes/review.py api/routes/__init__.py api/schemas/schemas.py requirements.txt requirements-dev.txt ValueInvestorsClub/tests/identity api/tests/test_review_api.py
git commit -m "feat: add reviewed identity resolution"
```

---

### Task 5: Move Dataroma Through the Shared Pipeline and Prove Berkshire

**Files:**
- Modify: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/holding_items.py`
- Modify: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/spiders/DataromaSpider.py`
- Modify: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/settings.py`
- Create: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/ingestion/dataroma.py`
- Create: `scripts/run_dataroma_baseline.py`
- Test: `ValueInvestorsClub/tests/spiders/test_dataroma_spider.py`
- Test: `ValueInvestorsClub/tests/ingestion/test_dataroma_adapter.py`
- Modify: `ValueInvestorsClub/tests/test_holding_items.py`
- Fixture: `ValueInvestorsClub/tests/fixtures/dataroma/home.html`
- Fixture: `ValueInvestorsClub/tests/fixtures/dataroma/holdings_brk.html`
- Fixture: `ValueInvestorsClub/tests/fixtures/dataroma/hist_brk_aapl.html`

- [ ] **Step 1: Record the current BRK baseline before changing parser behavior**

Run the existing parser and persistence path with a fresh local run:

```bash
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost/ideas \
PIPELINE_MODE=holdings \
scrapy -s LOG_LEVEL=INFO crawl DataromaSpider -a investor_slug=BRK
```

The `investor_slug` argument is a selection-only filter and must be covered before this run; no field parser or persistence behavior changes before the baseline is recorded. Record the current row counts, investor slug, first and last periods, and AAPL shares/value in `/tmp/dataroma-brk-baseline.json`. This file remains outside the repository and is used only to detect accidental parser drift.

- [ ] **Step 2: Add source evidence fields and adapter tests**

Extend `HoldingItem` with `source_url`, `source_observation_key`, `document_hash`, `exchange`, `share_class`, `portfolio_manager_name`, and `raw_payload`. Add tests asserting the existing fixture still yields `dataroma:BRK:AAPL:2026-06-30`, source URL, and a stable document hash.

- [ ] **Step 3: Implement the shared Dataroma adapter**

Keep the existing selectors and parsing rules:

- `/m/home.php` yields investor links containing `holdings.php?m=`.
- `/m/holdings.php?m=BRK` yields history links from `table#grid` rows.
- `/m/hist/hist.php?f=BRK&s=AAPL` parses period, shares, percentage, activity, and reported price.
- Blank activity becomes source activity `hold`; no missing row becomes `exit`.

Add the selection-only filter used by the baseline:

```python
requested_slug = (getattr(self, "investor_slug", "") or "").strip()
if requested_slug and slug != requested_slug:
    continue
```

For each response, emit one immutable source page item and source holding observations with deterministic keys. Pass the observations to `IngestionService`; do not write legacy `companies` or `holdings` directly. Keep `PIPELINE_MODE=holdings` as a compatibility alias that runs the new source path plus the explicit legacy bridge only when `LEGACY_HOLDINGS_BRIDGE=true`.

- [ ] **Step 4: Run fixture tests and the real one-investor proof**

Run:

```bash
pytest ValueInvestorsClub/tests/spiders/test_dataroma_spider.py ValueInvestorsClub/tests/ingestion/test_dataroma_adapter.py -v
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost/ideas \
PIPELINE_MODE=source scrapy crawl DataromaSpider -a investor_slug=BRK
```

Expected: fixture tests PASS; the real run records `source_documents`, `source_fetches`, source identities, staging rows, and curated rows after reviewed Berkshire mappings. The run status is `complete` or `partial`, never silently successful with zero rows.

- [ ] **Step 5: Verify API-level provenance and compare to baseline**

Query the curated API and database for `dataroma:BRK`, AAPL, first/last period, source URL, and completeness. Compare the result to `/tmp/dataroma-brk-baseline.json`. Any numeric change must be attributable to an explicit parser test update; an unreviewed difference fails the task.

- [ ] **Step 6: Commit**

```bash
git add ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/holding_items.py ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/spiders/DataromaSpider.py ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/settings.py ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/ingestion/dataroma.py scripts/run_dataroma_baseline.py ValueInvestorsClub/tests/spiders/test_dataroma_spider.py ValueInvestorsClub/tests/ingestion/test_dataroma_adapter.py ValueInvestorsClub/tests/test_holding_items.py
git commit -m "feat: route Dataroma through curated ingestion"
```

---

### Task 6: Add HedgeFollow Berkshire Crawl and Common-Stock Fixtures

**Files:**
- Create: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/spiders/HedgeFollowSpider.py`
- Create: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/ingestion/hedgefollow.py`
- Create: `ValueInvestorsClub/tests/fixtures/hedgefollow/fund_berkshire.html`
- Create: `ValueInvestorsClub/tests/fixtures/hedgefollow/fund_holdings_berkshire.json`
- Create: `ValueInvestorsClub/tests/fixtures/hedgefollow/fund_history_berkshire.json`
- Create: `ValueInvestorsClub/tests/spiders/test_hedgefollow_spider.py`
- Create: `ValueInvestorsClub/tests/ingestion/test_hedgefollow_adapter.py`
- Modify: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/settings.py`

- [ ] **Step 1: Capture the live Berkshire page and identify dynamic data requests**

Use the selected target `https://hedgefollow.com/funds/Berkshire+Hathaway`. The static page contract currently exposes:

- `table.fundSummary` with Berkshire Hathaway and Warren Buffett.
- `#tabTopHolders` and `#topHolders` for holdings.
- `#fund_holdings_equities` for common-stock holdings.
- `#fund_holdings_options` as a separate table that is excluded from Phase 1.
- `select[data-id="quarter"][name="quarter"]` and hidden quarter values such as `latest` and `2026-03-31`.
- `#tabLargestTrades`, `#dgBuyers`, `#dgSellers`, and `#tabLatestTrades` for activity evidence.
- `/funds/Berkshire+Hathaway/Performance-History` for the optional history link.
- Inline `requestId: 'fund_holdings'` and field definitions for `symbol`, `stockName`, `PP`, `adjustedShares`, `value`, `trade_value`, `percentChange`, `ownHistory`, `priceHistory`, and `quarter`.

Inspect the page JavaScript request helper once and capture the JSON response shape in the committed fixture. The parser must consume the JSON endpoint directly after the initial fund page rather than depend on browser execution.

- [ ] **Step 2: Write parser tests against committed fixtures**

Add tests asserting:

```python
def test_parse_fund_page_extracts_berkshire_identity():
    result = parse_fund_page(fixture("fund_berkshire.html"))
    assert result.investor_key == "Berkshire Hathaway"
    assert result.investor_name == "Berkshire Hathaway"
    assert result.portfolio_manager_name == "Warren Buffett"


def test_parse_equity_payload_excludes_options():
    rows = parse_holdings_payload(fixture_json("fund_holdings_berkshire.json"))
    assert rows
    assert all(row.instrument_type == "common_stock" for row in rows)
    assert {row.ticker for row in rows} >= {"AAPL", "KO"}


def test_parse_history_preserves_quarter_and_source_activity():
    rows = parse_history_payload(fixture_json("fund_history_berkshire.json"))
    assert any(row.period.isoformat() == "2026-03-31" for row in rows)
    assert any(row.source_activity in {"Buy", "Add", "Reduce", "Hold", None} for row in rows)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest ValueInvestorsClub/tests/spiders/test_hedgefollow_spider.py ValueInvestorsClub/tests/ingestion/test_hedgefollow_adapter.py -v`

Expected: FAIL because the spider, JSON parser, and fixtures do not exist.

- [ ] **Step 4: Implement the adapter and spider**

Start at `/funds/Berkshire+Hathaway`, store the exact page evidence, request the equity dataset for `latest` and each available quarter, and optionally request the largest-buys/largest-sells datasets when their request IDs are present. Map each equity row to `SourceHoldingObservation` with `source=hedgefollow`, `security_key=symbol`, common-stock type, source URL, quarter, and a deterministic observation key.

The parser must identify columns by the page's declared field names, not by numeric column position. Missing fields become validation failures or `unknown`; options are dropped from the Phase 1 common-stock stream with an explicit count. Preserve the raw JSON response and source URL for every observation.

- [ ] **Step 5: Run fixture tests and the live Berkshire proof**

Run:

```bash
pytest ValueInvestorsClub/tests/spiders/test_hedgefollow_spider.py ValueInvestorsClub/tests/ingestion/test_hedgefollow_adapter.py -v
PIPELINE_MODE=source scrapy crawl HedgeFollowSpider -a fund="Berkshire Hathaway"
```

Expected: fixture tests PASS; the live run stores Berkshire source evidence, maps the reporting Investor to the Dataroma `BRK` canonical identity after review, creates Security aliases for `BRK.B`/`BRK-B`-style values, and promotes common-stock snapshots without including options.

- [ ] **Step 6: Commit**

```bash
git add ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/spiders/HedgeFollowSpider.py ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/ingestion/hedgefollow.py ValueInvestorsClub/tests/fixtures/hedgefollow ValueInvestorsClub/tests/spiders/test_hedgefollow_spider.py ValueInvestorsClub/tests/ingestion/test_hedgefollow_adapter.py ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/settings.py
git commit -m "feat: add HedgeFollow Berkshire ingestion"
```

---

### Task 7: Expose Curated Holdings, Company, Investor, and Review APIs

**Files:**
- Modify: `api/routes/holdings.py`
- Modify: `api/routes/companies.py`
- Create: `api/routes/investors.py`
- Modify: `api/routes/__init__.py`
- Modify: `api/schemas/schemas.py`
- Modify: `api/validate_schema.py`
- Modify: `api/schema/openapi.json`
- Test: `api/tests/test_curated_holdings_api.py`
- Test: `api/tests/test_investors_api.py`
- Test: `api/tests/test_review_api.py`

- [ ] **Step 1: Write the response contract tests**

Define `CuratedHoldingResponse` with these required fields and test the exact JSON keys:

```python
class CuratedHoldingResponse(BaseModel):
    source: str
    investor_id: str
    investor_name: str
    portfolio_manager_name: str | None
    company_id: str
    company_name: str
    security_id: str
    ticker: str
    period: date
    shares: int | None
    value_usd: float | None
    pct_portfolio: float | None
    source_activity: str | None
    completeness: str
    source_url: str
```

Add tests for `source=dataroma`, `source=hedgefollow`, pagination, incomplete rows, and the rule that unresolved/quarantined rows do not appear. Add an API test that two source facts with different values remain two rows with separate `source_url` values.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest api/tests/test_curated_holdings_api.py api/tests/test_investors_api.py -v`

Expected: FAIL because the curated schemas and endpoints do not exist.

- [ ] **Step 3: Implement curated query routes**

Change `GET /holdings/` to query `curated_holding_snapshots` joined to curated Investor, Company, Security, and the retained source snapshot/document. Accept `source`, `investor_id`, `company_id`, `security_id`, `period_start`, `period_end`, `skip`, and `limit`. Return `completeness` and source provenance for every row.

Add:

- `GET /companies/{curated_company_id}` with Securities, curated VIC ideas, ownership snapshots/events, and source links.
- `GET /investors/{curated_investor_id}` with reporting-fund identity, PortfolioManager metadata, aliases, holdings, and coverage.
- The protected review routes from Task 4.

Keep legacy list endpoints available during the bridge, but do not use legacy `companies` or `holdings` as the data source for the new curated response.

- [ ] **Step 4: Regenerate and validate OpenAPI**

Run:

```bash
python -m api.validate_schema
pytest api/tests/test_curated_holdings_api.py api/tests/test_investors_api.py api/tests/test_review_api.py -v
```

Expected: OpenAPI contains `/holdings/`, `/companies/{curated_company_id}`, `/investors/{curated_investor_id}`, review routes, and `CuratedHoldingResponse`; all focused tests PASS. Extend `api/validate_schema.py` so missing curated endpoints or fields fail locally rather than only printing a warning.

- [ ] **Step 5: Commit**

```bash
git add api/routes/holdings.py api/routes/companies.py api/routes/investors.py api/routes/__init__.py api/schemas/schemas.py api/validate_schema.py api/schema/openapi.json api/tests/test_curated_holdings_api.py api/tests/test_investors_api.py api/tests/test_review_api.py
git commit -m "feat: expose curated investment APIs"
```

---

### Task 8: Build Source-Specific Holdings UI and Complete Visual Verification

**Files:**
- Create: `frontend/src/components/CuratedHoldingsTable.tsx`
- Modify: `frontend/src/pages/HoldingsPage.tsx`
- Create: `frontend/src/pages/SourceHoldingsPage.tsx`
- Create: `frontend/src/pages/IdentityReviewPage.tsx`
- Create: `frontend/src/pages/QuarantineReviewPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Layout.tsx`
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/api/apiService.ts`
- Create: `frontend/src/hooks/useCuratedHoldings.ts`
- Create: `frontend/src/hooks/useReviewQueue.ts`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Create: `frontend/playwright.config.ts`
- Create: `frontend/e2e/holdings.visual.spec.ts`
- Create: `.frontend-design/baselines/holdings.visual.spec.ts-snapshots/holdings-dataroma-375.png`
- Create: `.frontend-design/baselines/holdings.visual.spec.ts-snapshots/holdings-dataroma-768.png`
- Create: `.frontend-design/baselines/holdings.visual.spec.ts-snapshots/holdings-dataroma-1280.png`
- Test: `frontend/src/tests/curatedHoldings.test.tsx`

- [ ] **Step 1: Write the component and API contract tests**

Add a typed `CuratedHolding` interface matching `CuratedHoldingResponse`. Add tests for loading, API error, empty/partial coverage, source label, canonical Company/Security/Investor labels, source link, and quarantine exclusion. Use mocked `holdingsApi` responses; do not call the live sources from Jest.

- [ ] **Step 2: Run the frontend tests to verify they fail**

Run: `cd frontend && npm test -- --runInBand src/tests/curatedHoldings.test.tsx`

Expected: FAIL because the shared table, hook, and source routes do not exist.

- [ ] **Step 3: Implement the shared UI contract**

Implement `CuratedHoldingsTable` with these columns: Source, Investor, Portfolio Manager, Company, Security/Ticker, Period, Activity, Shares, Value, Portfolio %, Completeness, and Source. Use a horizontally scrollable table on small screens, preserve numeric alignment, show `Unknown coverage` rather than inventing a sell, and link the final column to the immutable source URL.

Implement `SourceHoldingsPage` with a `source` prop and routes:

- `/holdings` aggregate curated view.
- `/holdings/dataroma` filtered Dataroma view.
- `/holdings/hedgefollow` filtered HedgeFollow view.
- `/review/identity` protected identity queue.
- `/review/quarantine` protected quarantine queue.

Keep existing navigation and add source-specific links without removing Ideas, Companies, Users, or Articles. Use the existing Chakra UI and React Query patterns; do not add a new UI framework.

- [ ] **Step 4: Add visual verification tooling**

Add `@playwright/test` as a frontend dev dependency and create `frontend/playwright.config.ts` with a snapshot path under `.frontend-design/baselines/`. The visual spec must exercise these viewports:

```typescript
const viewports = [
  { name: '375', width: 375, height: 812 },
  { name: '768', width: 768, height: 1024 },
  { name: '1280', width: 1280, height: 720 },
];
```

For each viewport, visit `/holdings/dataroma`, assert the page heading, table, completeness label, and source link, then call `expect(page).toHaveScreenshot(...)`. Start the API and frontend with Docker Compose so the test exercises the actual route and API proxy.

- [ ] **Step 5: Generate and compare baseline screenshots**

Run:

```bash
npm --prefix frontend install
npx --prefix frontend playwright install chromium
docker compose up -d db api frontend
(cd frontend && npx playwright test e2e/holdings.visual.spec.ts --update-snapshots)
(cd frontend && npx playwright test e2e/holdings.visual.spec.ts)
```

Expected: the first command creates the three committed baseline screenshots; the second run passes with zero visual diffs at 375, 768, and 1280 pixels. A changed screenshot must be reviewed and committed only when the UI change is intentional.

- [ ] **Step 6: Run frontend tests and commit**

Run: `cd frontend && npm test -- --runInBand && npm run build && npm run lint`

Expected: Jest, TypeScript/Vite build, and ESLint all exit `0`.

```bash
git add frontend/src/components/CuratedHoldingsTable.tsx frontend/src/pages/HoldingsPage.tsx frontend/src/pages/SourceHoldingsPage.tsx frontend/src/pages/IdentityReviewPage.tsx frontend/src/pages/QuarantineReviewPage.tsx frontend/src/App.tsx frontend/src/components/Layout.tsx frontend/src/types/api.ts frontend/src/api/apiService.ts frontend/src/hooks/useCuratedHoldings.ts frontend/src/hooks/useReviewQueue.ts frontend/package.json frontend/package-lock.json frontend/playwright.config.ts frontend/e2e/holdings.visual.spec.ts .frontend-design/baselines frontend/src/tests/curatedHoldings.test.tsx
git commit -m "feat: add curated holdings views"
```

---

### Task 9: Add Direct OpenTelemetry, Local Observability, and Coverage Gates

**Files:**
- Create: `api/observability.py`
- Create: `api/telemetry.py`
- Create: `observability/prometheus/prometheus.yml`
- Create: `observability/loki/loki.yml`
- Create: `observability/tempo/tempo.yml`
- Create: `observability/grafana/provisioning/datasources/datasources.yml`
- Create: `observability/grafana/provisioning/dashboards/dashboards.yml`
- Create: `observability/grafana/dashboards/ingestion.json`
- Create: `observability/README.md`
- Modify: `docker-compose.yml`
- Modify: `requirements.txt`
- Modify: `api/main.py`
- Modify: `api/routes/health.py`
- Test: `api/tests/test_observability.py`
- Create: `docs/superpowers/plans/coverage-results.md`

- [ ] **Step 1: Capture coverage baselines before instrumentation/UI changes**

Run:

```bash
pytest api/tests ValueInvestorsClub/tests --cov=api --cov=ValueInvestorsClub --cov-report=term-missing --cov-report=json:/tmp/vic-backend-coverage.json
cd frontend && npm run test:coverage -- --runInBand --coverageReporters=json-summary
```

Record the total percentages and test commands in `docs/superpowers/plans/coverage-results.md`. This file must contain the baseline before Task 9 changes and the final Phase 1 percentages after all tasks.

- [ ] **Step 2: Write observability tests**

Add tests asserting that:

```python
def test_health_live_does_not_require_database(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_health_ready_reports_database_failure(client, monkeypatch):
    monkeypatch.setattr("api.routes.health.database_is_ready", lambda: False)
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"


def test_ingestion_metrics_fail_open_when_exporter_is_down():
    metrics = build_metrics(exporter_url="http://127.0.0.1:1")
    metrics.record("ingestion_rows_total", 1)
    assert metrics.local_value("ingestion_rows_total") == 1
```

- [ ] **Step 3: Implement direct SDK telemetry**

Add `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http`, and `prometheus-client` to `requirements.txt`. Configure traces, metrics, and logs directly from application code using environment endpoints; do not add an OpenTelemetry Collector service.

Instrument spans named `crawler.fetch`, `crawler.parse`, `ingestion.validate`, `ingestion.promote`, `api.request`, and `db.query`. Add metrics:

- `ingestion_runs_total{source,status}`
- `ingestion_rows_total{source,outcome}`
- `ingestion_run_duration_seconds{source}`
- `ingestion_rejection_ratio{source}`
- `database_ready`

Use structured logs with `run_id`, `source`, `parser_version`, `source_observation_key`, and `correlation_id`. Exporter failures log a health warning and never roll back the data transaction.

Add `/health/live` and `/health/ready`; readiness performs a `SELECT 1` through the configured SQLAlchemy engine. Keep `/health` as a compatibility alias to the live response.

- [ ] **Step 4: Add the Compose observability profile**

Add services behind `profiles: ["observability"]` for Prometheus, Loki, Tempo, Grafana, and Uptime Kuma. Configure seven-day retention in each telemetry store, local bind mounts under `data/observability/`, Grafana datasources, an ingestion dashboard, and webhook alert routing. Add Uptime Kuma monitor targets for `/health/live`, `/health/ready`, frontend port `3010`, PostgreSQL readiness, and a crawler heartbeat endpoint.

Run:

```bash
docker compose --profile observability config
docker compose --profile observability up -d
curl -fsS http://localhost:8010/health/live
curl -fsS http://localhost:8010/health/ready
```

Expected: Compose config validates, all observability containers become healthy, both health endpoints return the expected status, and the Grafana dashboard shows ingestion/run/database panels after a source test run.

- [ ] **Step 5: Measure final coverage and commit**

Run the same backend and frontend coverage commands from Step 1. Append the final percentages and a pass/fail comparison to `docs/superpowers/plans/coverage-results.md`. Fail the task if either total drops below its recorded baseline. Run `pytest api/tests ValueInvestorsClub/tests -q` and `cd frontend && npm test -- --runInBand`.

```bash
git add api/observability.py api/telemetry.py observability docker-compose.yml requirements.txt api/main.py api/routes/health.py api/tests/test_observability.py docs/superpowers/plans/coverage-results.md
git commit -m "feat: add local ingestion observability"
```

---

### Task 10: Build the Gated Company-Chapter Retrieval Baseline

**Files:**
- Create: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/models/retrieval.py`
- Create: `alembic/versions/20260816_0002_retrieval_schema.py`
- Create: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/retrieval/chunking.py`
- Create: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/retrieval/keyword.py`
- Create: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/retrieval/vector.py`
- Create: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/retrieval/ranking.py`
- Create: `ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/retrieval/service.py`
- Create: `api/routes/search.py`
- Modify: `api/routes/__init__.py`
- Modify: `requirements.txt`
- Modify: `docker-compose.yml`
- Test: `ValueInvestorsClub/tests/retrieval/test_chunking.py`
- Test: `ValueInvestorsClub/tests/retrieval/test_ranking.py`
- Test: `api/tests/test_search_api.py`

- [ ] **Step 1: Confirm all Phase 1 acceptance gates before adding retrieval**

Run the complete Phase 1 verification:

```bash
pytest api/tests ValueInvestorsClub/tests -q
cd frontend && npm test -- --runInBand
npx playwright test frontend/e2e/holdings.visual.spec.ts
docker compose --profile observability ps
```

Expected: migrations, Dataroma BRK, HedgeFollow Berkshire, curated APIs, UI screenshots, no-truncate coexistence, dashboards, and coverage gates all pass. If any gate fails, return to its task instead of creating retrieval tables.

- [ ] **Step 2: Add pgvector and retrieval schema**

Add `pgvector>=0.3.0` and `sentence-transformers>=3.0.0` to `requirements.txt`, switch the local database image to `pgvector/pgvector:pg14`, and enable the `vector` extension in `alembic/versions/20260816_0002_retrieval_schema.py`. Add:

- `company_chapters`: one non-embedded parent per curated Company.
- `evidence_chunks`: typed section, company/security/investor metadata, period bounds, source snapshot IDs, citation URLs, `tsvector`, and `vector(384)` embedding.
- `retrieval_runs`: query, filters, candidate IDs, rank signals, model versions, latency, and created time.
- `retrieval_feedback`: retrieval run ID, usefulness label, citation-correctness label, and retrieved citation IDs. Do not store the generated answer as a domain fact.

Use the local `sentence-transformers/all-MiniLM-L6-v2` model for 384-dimensional embeddings. No remote embedding provider or LM Studio fallback is used.

- [ ] **Step 3: Implement deterministic chunking and hybrid ranking tests**

Create typed child sections for curated VIC ideas, ownership snapshots/events, and Company/Security metadata. Add tests that assert:

```python
def test_company_chunking_preserves_source_citations():
    chunks = build_company_chunks(curated_company_fixture())
    assert {chunk.section_type for chunk in chunks} >= {"ideas", "ownership", "metadata"}
    assert all(chunk.citation_ids for chunk in chunks)


def test_rrf_combines_keyword_and_vector_ranks():
    result = reciprocal_rank_fusion(
        keyword_ids=["a", "b"],
        vector_ids=["b", "c"],
        k=60,
    )
    assert result[0].chunk_id == "b"
```

- [ ] **Step 4: Implement search order and read-only API**

Apply structured metadata filters first, then PostgreSQL FTS using `tsvector`/`ts_rank_cd`, vector cosine search, normalized reciprocal rank fusion, and a provider-neutral local reranker. Keep a true-BM25 adapter boundary so a local PostgreSQL BM25 extension can replace or augment FTS without changing the service contract.

Expose `GET /search` with query, Company/Investor/Security/source/period filters, result limit, evidence text, and citations. The agent-facing service is read-only, uses a capped prompt context, cites evidence IDs, and abstains when the result set is empty or incomplete. Persist retrieval run metadata and feedback labels only; generated answers remain transient.

- [ ] **Step 5: Run retrieval tests and commit**

Run:

```bash
pytest ValueInvestorsClub/tests/retrieval api/tests/test_search_api.py -v
python -m api.validate_schema
```

Expected: chunk citations, RRF ordering, metadata filtering, empty-result abstention, and search response schema tests PASS.

```bash
git add ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/models/retrieval.py alembic/versions/20260816_0002_retrieval_schema.py ValueInvestorsClub/ValueInvestorsClub/ValueInvestorsClub/retrieval api/routes/search.py api/routes/__init__.py requirements.txt docker-compose.yml ValueInvestorsClub/tests/retrieval api/tests/test_search_api.py
git commit -m "feat: add curated hybrid retrieval"
```

---

## Design Spec Coverage Map

| Design requirement | Plan coverage |
|---|---|
| Source, staging, quarantine, identity, curated layers | Tasks 1-3 |
| Company/Security/Investor/PortfolioManager identity model | Task 2 and Task 4 |
| Human-reviewed candidates and DeepInfra-only adjudication | Task 4 |
| Dataroma baseline and Berkshire proof | Task 5 |
| HedgeFollow Berkshire crawl, common stocks, and source JSON | Task 6 |
| Curated APIs, provenance, review queues | Task 7 |
| Source-specific UI and visual verification | Task 8; satisfies `ui_scope: true` |
| Direct OTLP observability, dashboards, alerts, seven-day telemetry | Task 9 |
| Coverage baseline and no-drop gate | Task 9; satisfies `test_scope: true` |
| Company chapters, pgvector, FTS/BM25, RRF, citations, transient answers | Task 10 after Phase 1 gates |
| Graph rebuild | Intentionally omitted because `graph_scope: false` |

## Phase 1 Completion Checklist

- [ ] Empty local PostgreSQL reaches the schema through Alembic only.
- [ ] Existing Dataroma BRK baseline is captured and explained after the shared-pipeline change.
- [ ] Dataroma BRK passes fetch, evidence, staging, validation, reviewed identity, curated promotion, API, DOM, and provenance checks.
- [ ] HedgeFollow Berkshire passes the same path for common-stock holdings, with options excluded and source JSON retained.
- [ ] One curated Investor, separate PortfolioManager, one Company, and Security-level ticker aliases exist without duplicate canonical identities.
- [ ] Invalid, duplicate, and unresolved observations are quarantined or pending and absent from public APIs.
- [ ] Partial runs expose completeness; missing quarters never become inferred sells.
- [ ] VIC legacy and new source runs coexist without global truncation or source-fact overwrite.
- [ ] Grafana, Prometheus, Loki, Tempo, and Uptime Kuma show source/run/database health with seven-day telemetry retention.
- [ ] Backend and frontend coverage meet or exceed the captured baseline.
- [ ] Playwright visual checks pass at 375, 768, and 1280 pixels with reviewed baselines.
- [ ] No secrets are tracked or logged, and the exposed DeepInfra token has been revoked and rotated.
