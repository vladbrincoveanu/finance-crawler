# Holdings Crawler Deploy + Minimal UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run DataromaSpider against the live site (5 investors) to populate investors/companies/holdings tables in Postgres, then add a minimal `/holdings` page in the frontend to view the data.

**Architecture:** Add an env-var-driven investor limit to the existing spider, run it live via docker-compose with `PIPELINE_MODE=holdings`, add one read-only FastAPI endpoint joining Holding+Investor+Company, and one flat-table React page consuming it — matching the existing `companies`/`users` endpoint and page patterns exactly.

**Tech Stack:** Scrapy, SQLAlchemy, FastAPI, Pydantic, React + react-query + Chakra UI, pytest, Playwright.

---

### Task 1: DataromaSpider investor limit

**Files:**
- Modify: `ValueInvestorsClub/ValueInvestorsClub/spiders/DataromaSpider.py`
- Test: `ValueInvestorsClub/tests/spiders/test_dataroma_spider.py`

- [ ] **Step 1: Write the failing test**

Add to `ValueInvestorsClub/tests/spiders/test_dataroma_spider.py`, reusing the existing `_response`/`FIXTURES` helper already defined at the top of the file (do not redefine them):

```python
def test_parse_home_respects_investor_limit(monkeypatch):
    monkeypatch.setenv("DATAROMA_INVESTOR_LIMIT", "2")
    spider = DataromaSpider()
    response = _response("home.html", "https://www.dataroma.com/m/home.php")

    requests = list(spider.parse_home(response))

    assert len(requests) == 2
```

This reuses the same `home.html` fixture (83 investors) as `test_parse_home_yields_one_request_per_investor` — only the limit differs.

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec api pytest ValueInvestorsClub/tests/spiders/test_dataroma_spider.py::test_parse_home_respects_investor_limit -v`
Expected: FAIL — `assert 3 == 2` (limit not applied yet).

- [ ] **Step 3: Write minimal implementation**

In `ValueInvestorsClub/ValueInvestorsClub/spiders/DataromaSpider.py`, add `import os` at the top, and change `parse_home`:

```python
def parse_home(self, response):
    limit = int(os.getenv("DATAROMA_INVESTOR_LIMIT", "0"))
    links = response.xpath("//li/a[contains(@href, 'holdings.php?m=')]")
    if limit > 0:
        links = links[:limit]
    for link in links:
        href = link.xpath("./@href").get() or ""
        slug = href.split("m=", 1)[-1]
        name = (link.xpath("./text()").get() or "").strip()
        if not slug or not name:
            continue
        yield scrapy.Request(
            response.urljoin(href),
            callback=self.parse_holdings,
            meta={
                "investor_slug": slug,
                "investor_name": name,
                "investor_profile_url": response.urljoin(href),
            },
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec api pytest ValueInvestorsClub/tests/spiders/test_dataroma_spider.py -v`
Expected: all PASS (existing tests unaffected — limit defaults to 0 = no limit).

- [ ] **Step 5: Commit**

```
git add ValueInvestorsClub/ValueInvestorsClub/spiders/DataromaSpider.py ValueInvestorsClub/tests/spiders/test_dataroma_spider.py
git commit -m "feat: DataromaSpider caps investor count via DATAROMA_INVESTOR_LIMIT"
```

---

### Task 2: Register Investor/Holding in api/models

**Files:**
- Modify: `api/models/__init__.py`

- [ ] **Step 1: Write the failing test**

Add to `api/tests/test_schemas.py` (check existing imports at top first, add if missing):

```python
def test_investor_and_holding_models_importable():
    from api.models import Investor, Holding
    assert Investor.__tablename__ == "investors"
    assert Holding.__tablename__ == "holdings"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec api pytest api/tests/test_schemas.py::test_investor_and_holding_models_importable -v`
Expected: FAIL with `ImportError: cannot import name 'Investor' from 'api.models'`

- [ ] **Step 3: Write minimal implementation**

Replace `api/models/__init__.py` with:

```python
"""
Models package for the ValueInvestorsClub API.
Imports the SQLAlchemy models from the ValueInvestorsClub package.
"""
from ValueInvestorsClub.ValueInvestorsClub.models.Base import Base
from ValueInvestorsClub.ValueInvestorsClub.models.Idea import Idea
from ValueInvestorsClub.ValueInvestorsClub.models.Company import Company
from ValueInvestorsClub.ValueInvestorsClub.models.Description import Description
from ValueInvestorsClub.ValueInvestorsClub.models.User import User
from ValueInvestorsClub.ValueInvestorsClub.models.Catalysts import Catalysts
from ValueInvestorsClub.ValueInvestorsClub.models.Performance import Performance
from ValueInvestorsClub.ValueInvestorsClub.models.Investor import Investor
from ValueInvestorsClub.ValueInvestorsClub.models.Holding import Holding

__all__ = [
    "Base",
    "Idea",
    "Company",
    "Description",
    "User",
    "Catalysts",
    "Performance",
    "Investor",
    "Holding",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec api pytest api/tests/test_schemas.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```
git add api/models/__init__.py api/tests/test_schemas.py
git commit -m "feat: register Investor/Holding models in api.models"
```

---

### Task 3: HoldingResponse schema

**Files:**
- Modify: `api/schemas/schemas.py`
- Modify: `api/schemas/__init__.py` (check it re-exports from `schemas.py` — if it uses `from .schemas import *` or explicit names, add `HoldingResponse` to match)

- [ ] **Step 1: Write the failing test**

Add to `api/tests/test_schemas.py`:

```python
def test_holding_response_schema_fields():
    from api.schemas import HoldingResponse
    fields = HoldingResponse.model_fields.keys()
    for f in ["investor_name", "ticker", "company_name", "quarter_date", "shares", "value_usd", "pct_portfolio", "activity"]:
        assert f in fields
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec api pytest api/tests/test_schemas.py::test_holding_response_schema_fields -v`
Expected: FAIL — `ImportError: cannot import name 'HoldingResponse'`

- [ ] **Step 3: Write minimal implementation**

Append to `api/schemas/schemas.py`:

```python
from datetime import date as date_type


class HoldingResponse(BaseModel):
    """A single investor holding in a company for a given quarter."""
    investor_name: str
    ticker: str
    company_name: str
    quarter_date: date_type
    shares: int
    value_usd: float
    pct_portfolio: float
    activity: str

    model_config = {"from_attributes": True}
```

Check `api/schemas/__init__.py` — if it lists names explicitly (like `api/models/__init__.py` does), add `HoldingResponse` to both the import line and `__all__`. If it does `from .schemas import *`, no change needed there.

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec api pytest api/tests/test_schemas.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```
git add api/schemas/schemas.py api/schemas/__init__.py api/tests/test_schemas.py
git commit -m "feat: add HoldingResponse schema"
```

---

### Task 4: GET /holdings/ endpoint

**Files:**
- Create: `api/routes/holdings.py`
- Modify: `api/main.py`
- Test: `api/tests/test_holdings_api.py`

- [ ] **Step 1: Write the failing test**

Create `api/tests/test_holdings_api.py`:

```python
"""
Integration tests for the holdings API endpoint.
"""
from datetime import date

from ValueInvestorsClub.ValueInvestorsClub.models.Company import Company
from ValueInvestorsClub.ValueInvestorsClub.models.Investor import Investor
from ValueInvestorsClub.ValueInvestorsClub.models.Holding import Holding


def test_get_holdings_returns_joined_rows(client, db_session):
    company = Company(ticker="AAPL", company_name="Apple Inc.")
    investor = Investor(
        id="dataroma:BRK",
        name="Warren Buffett - Berkshire Hathaway",
        source="dataroma",
        source_slug="BRK",
        profile_url="https://www.dataroma.com/m/holdings.php?m=BRK",
    )
    db_session.add_all([company, investor])
    db_session.commit()

    holding = Holding(
        investor_id="dataroma:BRK",
        company_id="AAPL",
        quarter_date=date(2026, 6, 30),
        shares=227917808,
        value_usd=65950296000.0,
        pct_portfolio=22.04,
        activity="hold",
    )
    db_session.add(holding)
    db_session.commit()

    response = client.get("/holdings/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["investor_name"] == "Warren Buffett - Berkshire Hathaway"
    assert data[0]["ticker"] == "AAPL"
    assert data[0]["shares"] == 227917808


def test_get_holdings_empty_list_when_no_data(client, db_session):
    response = client.get("/holdings/")
    assert response.status_code == 200
    assert response.json() == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec api pytest api/tests/test_holdings_api.py -v`
Expected: FAIL with 404 (route doesn't exist yet).

- [ ] **Step 3: Write minimal implementation**

Create `api/routes/holdings.py`:

```python
"""
Routes for holdings in the ValueInvestorsClub API.
"""
from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from typing import List

from api.database import get_db
from api.models import Holding, Investor, Company
from api.schemas import HoldingResponse

router = APIRouter()


@router.get("/holdings/", response_model=List[HoldingResponse])
def get_holdings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
):
    """
    Get holdings, joined with investor and company info.
    """
    rows = (
        db.query(Holding, Investor, Company)
        .join(Investor, Holding.investor_id == Investor.id)
        .join(Company, Holding.company_id == Company.ticker)
        .order_by(Holding.quarter_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        HoldingResponse(
            investor_name=investor.name,
            ticker=company.ticker,
            company_name=company.company_name,
            quarter_date=holding.quarter_date,
            shares=holding.shares,
            value_usd=float(holding.value_usd),
            pct_portfolio=float(holding.pct_portfolio),
            activity=holding.activity,
        )
        for holding, investor, company in rows
    ]
```

In `api/main.py`, add the import and registration:

```python
from api.routes import health_router, ideas_router, companies_router, users_router, holdings_router
...
app.include_router(holdings_router)
```

Check `api/routes/__init__.py` for how the other routers are exported (e.g. `companies_router = companies.router`) and add the same pattern for `holdings_router`.

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec api pytest api/tests/test_holdings_api.py -v`
Expected: both tests PASS.

- [ ] **Step 5: Run the full suite to confirm nothing broke**

Run: `docker-compose exec api pytest -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```
git add api/routes/holdings.py api/routes/__init__.py api/main.py api/tests/test_holdings_api.py
git commit -m "feat: add GET /holdings/ endpoint joining Holding+Investor+Company"
```

---

### Task 5: Frontend types, API client, hook

**Files:**
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/api/apiService.ts`
- Create: `frontend/src/hooks/useHoldings.ts`

- [ ] **Step 1: Add the type**

In `frontend/src/types/api.ts`, add near the `Company`/`User` interfaces:

```typescript
export interface Holding {
  investor_name: string;
  ticker: string;
  company_name: string;
  quarter_date: string;
  shares: number;
  value_usd: number;
  pct_portfolio: number;
  activity: string;
}
```

- [ ] **Step 2: Add the API client method**

In `frontend/src/api/apiService.ts`, update the import line to include `Holding`, and add:

```typescript
// Holdings API
export const holdingsApi = {
  getHoldings: async (params: ListParams = {}): Promise<Holding[]> => {
    const response = await apiClient.get('/holdings/', { params });
    return response.data;
  },
};
```

- [ ] **Step 3: Add the hook**

Create `frontend/src/hooks/useHoldings.ts`:

```typescript
import { useQuery, UseQueryOptions } from 'react-query';
import { holdingsApi } from '../api/apiService';
import { Holding, ListParams } from '../types/api';

export function useHoldings(params: ListParams = {}, options?: UseQueryOptions<Holding[]>) {
  return useQuery<Holding[]>(
    ['holdings', params],
    () => holdingsApi.getHoldings(params),
    options
  );
}
```

- [ ] **Step 4: Type-check**

The `frontend` container is a prebuilt nginx image (no node/npx inside the running container) — `npm run build` runs `tsc && vite build` as part of the Docker build stage itself.

Run: `docker-compose build frontend`
Expected: build succeeds (a `tsc` type error fails the build with a compiler error, not a silent pass).

- [ ] **Step 5: Commit**

```
git add frontend/src/types/api.ts frontend/src/api/apiService.ts frontend/src/hooks/useHoldings.ts
git commit -m "feat: add Holding type, API client, and useHoldings hook"
```

---

### Task 6: HoldingsPage + route + nav link

**Files:**
- Create: `frontend/src/pages/HoldingsPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: Create the page**

Create `frontend/src/pages/HoldingsPage.tsx`:

```tsx
import React from 'react';
import {
  Box,
  Heading,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Spinner,
  Alert,
  AlertIcon,
} from '@chakra-ui/react';
import { useHoldings } from '../hooks/useHoldings';

const HoldingsPage: React.FC = () => {
  const { data: holdings, isLoading, isError, error } = useHoldings({ skip: 0, limit: 100 });

  return (
    <Box p={5}>
      <Heading mb={5}>Holdings</Heading>

      {isLoading && <Spinner data-testid="holdings-loading" />}

      {isError && (
        <Alert status="error" data-testid="holdings-error">
          <AlertIcon />
          {error instanceof Error ? error.message : 'Failed to load holdings'}
        </Alert>
      )}

      {!isLoading && !isError && (
        <Table data-testid="holdings-table">
          <Thead>
            <Tr>
              <Th>Investor</Th>
              <Th>Ticker</Th>
              <Th>Company</Th>
              <Th>Quarter</Th>
              <Th isNumeric>Shares</Th>
              <Th isNumeric>Value (USD)</Th>
              <Th isNumeric>% Portfolio</Th>
              <Th>Activity</Th>
            </Tr>
          </Thead>
          <Tbody>
            {(holdings ?? []).map((h, i) => (
              <Tr key={`${h.investor_name}-${h.ticker}-${h.quarter_date}-${i}`}>
                <Td>{h.investor_name}</Td>
                <Td>{h.ticker}</Td>
                <Td>{h.company_name}</Td>
                <Td>{h.quarter_date}</Td>
                <Td isNumeric>{h.shares.toLocaleString()}</Td>
                <Td isNumeric>{h.value_usd.toLocaleString()}</Td>
                <Td isNumeric>{h.pct_portfolio}</Td>
                <Td>{h.activity}</Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      )}
    </Box>
  );
};

export default HoldingsPage;
```

- [ ] **Step 2: Add the route**

In `frontend/src/App.tsx`, import `HoldingsPage` alongside the other page imports, and add inside `<Route path="/" element={<Layout />}>`:

```tsx
<Route path="holdings" element={<HoldingsPage />} />
```

- [ ] **Step 3: Add the nav link**

In `frontend/src/components/Layout.tsx`, add to the `NAV_ITEMS` array (after the `Users` entry):

```tsx
{
  label: 'Holdings',
  href: '/holdings',
},
```

- [ ] **Step 4: Visual verification (Playwright, real DOM)**

`frontend` is a prebuilt nginx image — rebuild it so the new page is actually served: `docker-compose up -d --build frontend`

Use `/playwright-pro` to navigate to `http://localhost:3010/holdings` (port 3010, per `docker-compose.yml` — not 3000) and assert on the real rendered DOM:
- `[data-testid="holdings-table"]` is visible (or `[data-testid="holdings-error"]` if the API has no data yet — acceptable at this point since Task 7 seeds real data).
- Nav bar contains a link with text "Holdings" pointing to `/holdings`.

Do not screenshot-only; assert selectors/text per this project's mandatory DOM-verification rule.

- [ ] **Step 5: Commit**

```
git add frontend/src/pages/HoldingsPage.tsx frontend/src/App.tsx frontend/src/components/Layout.tsx
git commit -m "feat: add minimal /holdings page with flat holdings table"
```

---

### Task 7: Deploy — live crawl + verify data end-to-end

**Files:**
- None created/modified — this is a run-and-verify task.

- [ ] **Step 1: Run the reachability probe**

Run: `bash scripts/probe_dataroma.sh`
Expected: `Dataroma reachable (HTTP 200).`
If it fails, stop — do not proceed to the live crawl.

- [ ] **Step 2: Run the live crawl, capped to 5 investors**

```bash
source scripts/lib_vic_scrape.sh
DATAROMA_INVESTOR_LIMIT=5 PIPELINE_MODE=holdings vic_run_scrapy DataromaSpider
```

Expected: scrapy log shows `'item_scraped_count'` > 0 and no unhandled tracebacks. This will make real HTTP requests to dataroma.com — respects the shared politeness settings (AUTOTHROTTLE, DOWNLOAD_DELAY) already wired into `vic_run_scrapy`.

- [ ] **Step 3: Verify rows landed in Postgres**

```bash
docker-compose exec -T db psql -U postgres -d ideas -c "SELECT count(*) FROM investors;"
docker-compose exec -T db psql -U postgres -d ideas -c "SELECT count(*) FROM holdings;"
docker-compose exec -T db psql -U postgres -d ideas -c "SELECT i.name, h.company_id, h.shares FROM holdings h JOIN investors i ON h.investor_id = i.id LIMIT 5;"
```

Expected: `investors` count = 5 (or fewer if some investors have zero parseable holdings), `holdings` count > 0.

- [ ] **Step 4: Hit the API directly**

```bash
curl -s http://localhost:8010/holdings/ | head -c 500
```

Expected: non-empty JSON array with the fields from `HoldingResponse`.

- [ ] **Step 5: Visual verification of real data (Playwright, real DOM)**

Use `/playwright-pro` to navigate to `http://localhost:3010/holdings` and assert:
- `[data-testid="holdings-table"]` visible.
- At least one `<tbody><tr>` row exists with non-empty ticker/investor text (not the empty-state).

If the row count is 0 despite Step 3 showing data, this is a bug — do not mark this task done until real seeded data renders.

- [ ] **Step 6: No commit** — this task runs existing code against the live site and a running DB; there is no code change to commit. If Step 5 uncovers a bug, fix it as an amendment to the relevant earlier task and re-run this task from Step 1.

---

### Task 8: Coverage measurement (test_scope gate)

**Files:**
- None modified — measurement only.

- [ ] **Step 1: Run coverage across the full suite**

Run: `docker-compose exec api pytest --cov=api --cov=ValueInvestorsClub/ValueInvestorsClub --cov-report=term-missing`

- [ ] **Step 2: Confirm no regression**

Compare against the last recorded baseline (`ValueInvestorsClub/ValueInvestorsClub` holdings modules were at 87-100% per-module as of the 2026-08-15 plan). New files this plan adds (`api/routes/holdings.py`, `frontend` — frontend isn't covered by this Python coverage run) must show no large uncovered blocks (i.e. `get_holdings` exercised by both `test_holdings_api.py` tests). Record the number in the commit message of the next task, or in a comment here if this is the final task.

Expected: `api/routes/holdings.py` shows >80% coverage (the two tests exercise both the joined-rows and empty-list branches).

- [ ] **Step 3: No commit** — measurement only, no code change.

---

## Self-Review

**Spec coverage:** Every spec section has a task — crawl limit (Task 1), API models/schema/endpoint (Tasks 2-4), frontend types/hook/page (Tasks 5-6), deploy/live-try (Task 7), coverage gate (Task 8). The pre-existing import bug fix was already committed separately before this plan (noted in the spec).

**Placeholder scan:** No TBD/TODO.

**Type consistency:** `HoldingResponse` fields match `Holding` interface (frontend) match `HoldingItem` fields (existing, Task 2 of prior plan) — `investor_name, ticker, company_name, quarter_date, shares, value_usd, pct_portfolio, activity` used consistently across Tasks 3, 4, 5, 6.
