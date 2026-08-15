# Dataroma Holdings Crawler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Crawl Dataroma's 83 curated superinvestors and store investor × quarter × company holdings (shares, value, % of portfolio, activity) in Postgres, as a pipeline independent from the existing VIC idea-scraper.

**Architecture:** New `DataromaSpider` in the existing Scrapy project (`ValueInvestorsClub/ValueInvestorsClub/spiders/`) crawls `/m/home.php` (investor list) → `/m/holdings.php?m=<code>` (current holdings, gives full shares/value/pct + per-stock history links) → `/m/hist/hist.php?f=<code>&s=<ticker>` (per-holding quarterly history: shares/pct/activity per quarter, back to first filing). Yields `HoldingItem`s into a new `HoldingPipeline` that upserts `Investor`/`Company`/`Holding` rows.

**Tech Stack:** Scrapy (existing project), SQLAlchemy + Postgres (existing), pytest (existing, extended to cover the scrapy project).

**Spec:** `docs/superpowers/specs/2026-08-15-holdings-crawler-design.md`

**Real page structure captured Aug 15 2026** (fixtures saved under `ValueInvestorsClub/tests/fixtures/dataroma/`):
- `home.html` — investor list: `<li><a href="/m/holdings.php?m=vg">Viking Global Investors<span class="portb"> Updated 14 Aug 2026</span>...</a></li>`, 83 total.
- `holdings_brk.html` — current holdings table (`<table id="grid">`), one `<tr>` per holding: hist link, ticker+name, pct, activity text, shares, reported price, value. Portfolio date in `<p id="p2">Period: <span>Q2 2026</span>...Portfolio date: <span>30 Jun 2026</span>`.
- `hist_brk_aapl.html` — per-stock quarterly history (`<table id="grid">`), one `<tr>` per quarter: period ("2026 Q2"), shares, pct, activity text ("Add 0.04%" / "Reduce 4.32%" / "Buy " / blank=hold), reported price. This is the actual per-quarter source — `value_usd` is computed as `shares × reported_price` for historical quarters (verified against BRK/AAPL current quarter: matches holdings.php's value to within rounding).
- Activity text prefixes to parse: `Buy` (new position), `Add N%` (increase), `Reduce N%` (decrease), blank (unchanged/hold). Full exits aren't represented as rows — a fully-sold stock simply stops appearing; this plan does not attempt to infer sells from absence (documented limitation, not a task).

---

### Task 1: Investor and Holding models

**Files:**
- Create: `ValueInvestorsClub/ValueInvestorsClub/models/Investor.py`
- Create: `ValueInvestorsClub/ValueInvestorsClub/models/Holding.py`
- Modify: `ValueInvestorsClub/ValueInvestorsClub/models/__init__.py`
- Test: `ValueInvestorsClub/tests/models/test_holding_models.py`

- [ ] **Step 1: Write the failing test**

```python
# ValueInvestorsClub/tests/models/test_holding_models.py
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ValueInvestorsClub.models import Base, Company, Investor, Holding


def test_holding_links_investor_and_company():
    engine = create_engine("sqlite:///:memory:")
    Base.Base.metadata.create_all(engine)

    with Session(engine) as session:
        investor = Investor(id="dataroma:BRK", name="Warren Buffett - Berkshire Hathaway",
                             source="dataroma", source_slug="BRK",
                             profile_url="https://www.dataroma.com/m/holdings.php?m=BRK")
        company = Company(ticker="AAPL", company_name="Apple Inc.")
        holding = Holding(
            investor_id=investor.id,
            company_id=company.ticker,
            quarter_date=date(2026, 6, 30),
            shares=227917808,
            value_usd=65950296000,
            pct_portfolio=22.04,
            activity="hold",
        )
        session.add_all([investor, company, holding])
        session.commit()

        fetched = session.query(Holding).one()
        assert fetched.investor.name == "Warren Buffett - Berkshire Hathaway"
        assert fetched.company.company_name == "Apple Inc."
        assert fetched.quarter_date == date(2026, 6, 30)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec api pytest ValueInvestorsClub/tests/models/test_holding_models.py -v`
Expected: FAIL with `ImportError: cannot import name 'Investor' from 'ValueInvestorsClub.models'`

- [ ] **Step 3: Write minimal implementation**

```python
# ValueInvestorsClub/ValueInvestorsClub/models/Investor.py
try:
    from ValueInvestorsClub.models.Base import Base
except ImportError:
    from ValueInvestorsClub.ValueInvestorsClub.models.Base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String


class Investor(Base):
    __tablename__ = "investors"
    # id format: "<source>:<source_slug>", e.g. "dataroma:BRK" — keeps sources disjoint by construction.
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    source: Mapped[str] = mapped_column(String(32))
    source_slug: Mapped[str] = mapped_column(String(32))
    profile_url: Mapped[str] = mapped_column(String(256))

    holdings = relationship("Holding", backref="investor")

    def __repr__(self) -> str:
        return f"Investor(id={self.id!r}, name={self.name!r}, source={self.source!r})"
```

```python
# ValueInvestorsClub/ValueInvestorsClub/models/Holding.py
try:
    from ValueInvestorsClub.models.Base import Base
except ImportError:
    from ValueInvestorsClub.ValueInvestorsClub.models.Base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Date, BigInteger, Numeric, ForeignKey, UniqueConstraint


class Holding(Base):
    __tablename__ = "holdings"
    __table_args__ = (
        UniqueConstraint("investor_id", "company_id", "quarter_date", name="uq_holding_investor_company_quarter"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    investor_id: Mapped[str] = mapped_column(ForeignKey("investors.id"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.ticker"))
    quarter_date: Mapped[Date] = mapped_column(Date)
    shares: Mapped[int] = mapped_column(BigInteger)
    value_usd: Mapped[float] = mapped_column(Numeric(20, 2))
    pct_portfolio: Mapped[float] = mapped_column(Numeric(6, 2))
    activity: Mapped[str] = mapped_column(String(16))  # buy | add | reduce | hold

    company = relationship("Company", backref="holdings")

    def __repr__(self) -> str:
        return (f"Holding(investor_id={self.investor_id!r}, company_id={self.company_id!r}, "
                f"quarter_date={self.quarter_date!r}, shares={self.shares!r})")
```

Modify `ValueInvestorsClub/ValueInvestorsClub/models/__init__.py`:

```python
from . import Base
from .Company import Company
from .User import User
from .Idea import Idea
from .Description import Description
from .Catalysts import Catalysts
from .Performance import Performance
from .Investor import Investor
from .Holding import Holding

__all__ = [
    "Base",
    "Company",
    "User",
    "Idea",
    "Description",
    "Catalysts",
    "Performance",
    "Investor",
    "Holding",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec api pytest ValueInvestorsClub/tests/models/test_holding_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```
git add ValueInvestorsClub/ValueInvestorsClub/models/Investor.py ValueInvestorsClub/ValueInvestorsClub/models/Holding.py ValueInvestorsClub/ValueInvestorsClub/models/__init__.py ValueInvestorsClub/tests/models/test_holding_models.py
git commit -m "feat: add Investor and Holding models for holdings crawler"
```

---

### Task 2: HoldingItem

**Files:**
- Create: `ValueInvestorsClub/ValueInvestorsClub/holding_items.py`
- Test: `ValueInvestorsClub/tests/test_holding_items.py`

- [ ] **Step 1: Write the failing test**

```python
# ValueInvestorsClub/tests/test_holding_items.py
from ValueInvestorsClub.holding_items import HoldingItem


def test_holding_item_has_expected_fields():
    item = HoldingItem(
        investor_name="Warren Buffett - Berkshire Hathaway",
        investor_source="dataroma",
        investor_slug="BRK",
        investor_profile_url="https://www.dataroma.com/m/holdings.php?m=BRK",
        ticker="AAPL",
        company_name="Apple Inc.",
        quarter_date="2026-06-30",
        shares=227917808,
        value_usd=65950296000.0,
        pct_portfolio=22.04,
        activity="hold",
    )
    assert item["ticker"] == "AAPL"
    assert item["activity"] == "hold"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec api pytest ValueInvestorsClub/tests/test_holding_items.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ValueInvestorsClub.holding_items'`

- [ ] **Step 3: Write minimal implementation**

```python
# ValueInvestorsClub/ValueInvestorsClub/holding_items.py
import scrapy


class HoldingItem(scrapy.Item):
    investor_name = scrapy.Field()
    investor_source = scrapy.Field()
    investor_slug = scrapy.Field()
    investor_profile_url = scrapy.Field()

    ticker = scrapy.Field()
    company_name = scrapy.Field()

    quarter_date = scrapy.Field()  # ISO "YYYY-MM-DD"
    shares = scrapy.Field()
    value_usd = scrapy.Field()
    pct_portfolio = scrapy.Field()
    activity = scrapy.Field()  # buy | add | reduce | hold

    def __repr__(self):
        return repr({"investor_slug": self.get("investor_slug"), "ticker": self.get("ticker"),
                      "quarter_date": self.get("quarter_date")})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec api pytest ValueInvestorsClub/tests/test_holding_items.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```
git add ValueInvestorsClub/ValueInvestorsClub/holding_items.py ValueInvestorsClub/tests/test_holding_items.py
git commit -m "feat: add HoldingItem for the holdings crawler pipeline"
```

---

### Task 3: DataromaSpider — investor list parsing

**Files:**
- Create: `ValueInvestorsClub/ValueInvestorsClub/spiders/DataromaSpider.py`
- Test: `ValueInvestorsClub/tests/spiders/test_dataroma_spider.py`
- Fixture (already saved): `ValueInvestorsClub/tests/fixtures/dataroma/home.html`

- [ ] **Step 1: Write the failing test**

```python
# ValueInvestorsClub/tests/spiders/test_dataroma_spider.py
from pathlib import Path
from scrapy.http import HtmlResponse

from ValueInvestorsClub.spiders.DataromaSpider import DataromaSpider

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "dataroma"


def _response(name: str, url: str) -> HtmlResponse:
    body = (FIXTURES / name).read_bytes()
    return HtmlResponse(url=url, body=body)


def test_parse_home_yields_one_request_per_investor():
    spider = DataromaSpider()
    response = _response("home.html", "https://www.dataroma.com/m/home.php")

    requests = list(spider.parse_home(response))

    assert len(requests) == 83
    brk = next(r for r in requests if r.meta["investor_slug"] == "BRK")
    assert brk.url == "https://www.dataroma.com/m/holdings.php?m=BRK"
    assert brk.meta["investor_name"] == "Warren Buffett - Berkshire Hathaway"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec api pytest ValueInvestorsClub/tests/spiders/test_dataroma_spider.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ValueInvestorsClub.spiders.DataromaSpider'`

- [ ] **Step 3: Write minimal implementation**

```python
# ValueInvestorsClub/ValueInvestorsClub/spiders/DataromaSpider.py
import scrapy


class DataromaSpider(scrapy.Spider):
    name = "DataromaSpider"
    allowed_domains = ["dataroma.com"]
    start_urls = ["https://www.dataroma.com/m/home.php"]

    async def start(self):
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse_home)

    def parse_home(self, response):
        for link in response.xpath("//li/a[contains(@href, 'holdings.php?m=')]"):
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

    def parse_holdings(self, response):
        # Implemented in Task 4
        return
        yield  # pragma: no cover
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec api pytest ValueInvestorsClub/tests/spiders/test_dataroma_spider.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```
git add ValueInvestorsClub/ValueInvestorsClub/spiders/DataromaSpider.py ValueInvestorsClub/tests/spiders/test_dataroma_spider.py
git commit -m "feat: DataromaSpider parses superinvestor list from home.php"
```

---

### Task 4: DataromaSpider — current holdings parsing (quarter date, per-stock history links)

**Files:**
- Modify: `ValueInvestorsClub/ValueInvestorsClub/spiders/DataromaSpider.py`
- Test: `ValueInvestorsClub/tests/spiders/test_dataroma_spider.py`
- Fixture (already saved): `ValueInvestorsClub/tests/fixtures/dataroma/holdings_brk.html`

- [ ] **Step 1: Write the failing test**

```python
# append to ValueInvestorsClub/tests/spiders/test_dataroma_spider.py

def test_parse_holdings_yields_one_history_request_per_stock():
    spider = DataromaSpider()
    response = _response(
        "holdings_brk.html", "https://www.dataroma.com/m/holdings.php?m=BRK"
    )
    response.meta["investor_slug"] = "BRK"
    response.meta["investor_name"] = "Warren Buffett - Berkshire Hathaway"
    response.meta["investor_profile_url"] = "https://www.dataroma.com/m/holdings.php?m=BRK"

    requests = list(spider.parse_holdings(response))

    aapl = next(r for r in requests if r.meta["ticker"] == "AAPL")
    assert aapl.url == "https://www.dataroma.com/m/hist/hist.php?f=BRK&s=AAPL"
    assert aapl.meta["company_name"] == "Apple Inc."
    assert aapl.meta["investor_slug"] == "BRK"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec api pytest ValueInvestorsClub/tests/spiders/test_dataroma_spider.py -v`
Expected: FAIL — `parse_holdings` currently returns immediately, no requests yielded.

- [ ] **Step 3: Write minimal implementation**

Replace the `parse_holdings` stub in `DataromaSpider.py`:

```python
    def parse_holdings(self, response):
        investor_slug = response.meta["investor_slug"]
        for row in response.xpath("//table[@id='grid']/tbody/tr"):
            hist_href = row.xpath("./td[@class='hist']/a/@href").get()
            ticker = row.xpath("./td[@class='stock']/a/text()").get()
            company_name = row.xpath("./td[@class='stock']/a/span/text()").get() or ""
            if not hist_href or not ticker:
                continue
            yield scrapy.Request(
                response.urljoin(hist_href),
                callback=self.parse_stock_history,
                meta={
                    "investor_slug": investor_slug,
                    "investor_name": response.meta["investor_name"],
                    "investor_profile_url": response.meta["investor_profile_url"],
                    "ticker": ticker.strip(),
                    "company_name": company_name.lstrip("- ").strip(),
                },
            )

    def parse_stock_history(self, response):
        # Implemented in Task 5
        return
        yield  # pragma: no cover
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec api pytest ValueInvestorsClub/tests/spiders/test_dataroma_spider.py -v`
Expected: PASS (both tests in the file)

- [ ] **Step 5: Commit**

```
git add ValueInvestorsClub/ValueInvestorsClub/spiders/DataromaSpider.py ValueInvestorsClub/tests/spiders/test_dataroma_spider.py
git commit -m "feat: DataromaSpider parses current holdings table into per-stock history requests"
```

---

### Task 5: DataromaSpider — quarterly history parsing into HoldingItems

**Files:**
- Modify: `ValueInvestorsClub/ValueInvestorsClub/spiders/DataromaSpider.py`
- Test: `ValueInvestorsClub/tests/spiders/test_dataroma_spider.py`
- Fixture (already saved): `ValueInvestorsClub/tests/fixtures/dataroma/hist_brk_aapl.html`

- [ ] **Step 1: Write the failing test**

```python
# append to ValueInvestorsClub/tests/spiders/test_dataroma_spider.py

def test_parse_stock_history_yields_one_holding_item_per_quarter():
    spider = DataromaSpider()
    response = _response(
        "hist_brk_aapl.html", "https://www.dataroma.com/m/hist/hist.php?f=BRK&s=AAPL"
    )
    response.meta.update({
        "investor_slug": "BRK",
        "investor_name": "Warren Buffett - Berkshire Hathaway",
        "investor_profile_url": "https://www.dataroma.com/m/holdings.php?m=BRK",
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
    })

    items = list(spider.parse_stock_history(response))

    q2 = next(i for i in items if i["quarter_date"] == "2026-06-30")
    assert q2["shares"] == 227917808
    assert q2["pct_portfolio"] == 22.04
    assert q2["activity"] == "hold"
    assert round(q2["value_usd"]) == round(227917808 * 289.36)

    q4_2025 = next(i for i in items if i["quarter_date"] == "2025-12-31")
    assert q4_2025["activity"] == "reduce"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec api pytest ValueInvestorsClub/tests/spiders/test_dataroma_spider.py -v`
Expected: FAIL — `parse_stock_history` yields nothing.

- [ ] **Step 3: Write minimal implementation**

Add helpers and replace `parse_stock_history` in `DataromaSpider.py`:

```python
import re
from datetime import date
from ValueInvestorsClub.holding_items import HoldingItem

_QUARTER_END = {"Q1": (3, 31), "Q2": (6, 30), "Q3": (9, 30), "Q4": (12, 31)}


def _parse_period(text: str) -> str:
    # "2026 \xa0Q2" -> "2026-06-30"
    m = re.search(r"(\d{4}).*?(Q[1-4])", text or "")
    if not m:
        return ""
    year, quarter = int(m.group(1)), m.group(2)
    month, day = _QUARTER_END[quarter]
    return date(year, month, day).isoformat()


def _parse_money(text: str) -> float:
    return float((text or "").replace("$", "").replace(",", "") or 0)


def _parse_activity(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return "hold"
    if t.startswith("Buy"):
        return "buy"
    if t.startswith("Add"):
        return "add"
    if t.startswith("Reduce"):
        return "reduce"
    return "hold"
```

```python
    def parse_stock_history(self, response):
        for row in response.xpath("//table[@id='grid']/tbody/tr"):
            cells = row.xpath("./td")
            if len(cells) < 6:
                continue
            quarter_date = _parse_period(cells[0].xpath("string()").get())
            shares_text = (cells[1].xpath("string()").get() or "").replace(",", "").strip()
            if not quarter_date or not shares_text:
                continue
            shares = int(shares_text)
            pct = float((cells[2].xpath("string()").get() or "0").strip() or 0)
            activity = _parse_activity(cells[3].xpath("string()").get())
            price = _parse_money(cells[5].xpath("string()").get())

            yield HoldingItem(
                investor_name=response.meta["investor_name"],
                investor_source="dataroma",
                investor_slug=response.meta["investor_slug"],
                investor_profile_url=response.meta["investor_profile_url"],
                ticker=response.meta["ticker"],
                company_name=response.meta["company_name"],
                quarter_date=quarter_date,
                shares=shares,
                value_usd=shares * price,
                pct_portfolio=pct,
                activity=activity,
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec api pytest ValueInvestorsClub/tests/spiders/test_dataroma_spider.py -v`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Commit**

```
git add ValueInvestorsClub/ValueInvestorsClub/spiders/DataromaSpider.py ValueInvestorsClub/tests/spiders/test_dataroma_spider.py
git commit -m "feat: DataromaSpider parses per-quarter holding history into HoldingItems"
```

---

### Task 6: HoldingPipeline — upsert into Postgres

**Files:**
- Create: `ValueInvestorsClub/ValueInvestorsClub/holding_pipeline.py`
- Test: `ValueInvestorsClub/tests/test_holding_pipeline.py`

- [ ] **Step 1: Write the failing test**

```python
# ValueInvestorsClub/tests/test_holding_pipeline.py
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ValueInvestorsClub.models import Base, Investor, Holding, Company
from ValueInvestorsClub.holding_items import HoldingItem
from ValueInvestorsClub.holding_pipeline import HoldingPipeline


def test_process_item_upserts_investor_company_and_holding(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.Base.metadata.create_all(engine)

    pipeline = HoldingPipeline.__new__(HoldingPipeline)
    pipeline.engine = engine

    item = HoldingItem(
        investor_name="Warren Buffett - Berkshire Hathaway",
        investor_source="dataroma",
        investor_slug="BRK",
        investor_profile_url="https://www.dataroma.com/m/holdings.php?m=BRK",
        ticker="AAPL",
        company_name="Apple Inc.",
        quarter_date="2026-06-30",
        shares=227917808,
        value_usd=65950296000.0,
        pct_portfolio=22.04,
        activity="hold",
    )

    pipeline.process_item(item)
    pipeline.process_item(item)  # re-processing the same quarter must not duplicate

    with Session(engine) as session:
        assert session.query(Investor).count() == 1
        assert session.query(Company).count() == 1
        assert session.query(Holding).count() == 1
        holding = session.query(Holding).one()
        assert holding.investor_id == "dataroma:BRK"
        assert holding.shares == 227917808
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec api pytest ValueInvestorsClub/tests/test_holding_pipeline.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ValueInvestorsClub.holding_pipeline'`

- [ ] **Step 3: Write minimal implementation**

```python
# ValueInvestorsClub/ValueInvestorsClub/holding_pipeline.py
import os
from datetime import date as date_cls

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ValueInvestorsClub.models import Base, Investor, Company, Holding


class HoldingPipeline:
    """Upserts HoldingItems (Dataroma, HedgeFollow, ...) into Investor/Company/Holding tables."""

    def __init__(self):
        self.engine = create_engine(
            os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost/ideas")
        )
        Base.Base.metadata.create_all(self.engine)

    def process_item(self, item, spider=None):
        investor_id = f"{item['investor_source']}:{item['investor_slug']}"
        quarter_date = date_cls.fromisoformat(item["quarter_date"])

        with Session(self.engine) as session:
            investor = session.get(Investor, investor_id)
            if investor is None:
                investor = Investor(
                    id=investor_id,
                    name=item["investor_name"],
                    source=item["investor_source"],
                    source_slug=item["investor_slug"],
                    profile_url=item["investor_profile_url"],
                )
                session.add(investor)

            company = session.get(Company, item["ticker"])
            if company is None:
                company = Company(ticker=item["ticker"], company_name=item["company_name"])
                session.add(company)
            session.commit()

            holding = (
                session.query(Holding)
                .filter_by(investor_id=investor_id, company_id=item["ticker"], quarter_date=quarter_date)
                .first()
            )
            if holding is None:
                holding = Holding(
                    investor_id=investor_id,
                    company_id=item["ticker"],
                    quarter_date=quarter_date,
                )
                session.add(holding)

            holding.shares = item["shares"]
            holding.value_usd = item["value_usd"]
            holding.pct_portfolio = item["pct_portfolio"]
            holding.activity = item["activity"]
            session.commit()

        return item
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec api pytest ValueInvestorsClub/tests/test_holding_pipeline.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```
git add ValueInvestorsClub/ValueInvestorsClub/holding_pipeline.py ValueInvestorsClub/tests/test_holding_pipeline.py
git commit -m "feat: HoldingPipeline upserts Investor/Company/Holding rows, dedupes by quarter"
```

---

### Task 7: Wire settings, pytest config, and crawl runner

**Files:**
- Modify: `ValueInvestorsClub/ValueInvestorsClub/settings.py`
- Modify: `/Users/vladbrincoveanu/Desktop/Startup/ValueInvestorsClub/pytest.ini`
- Modify: `scripts/lib_vic_scrape.sh`

- [ ] **Step 1: Register the pipeline and domain-specific settings**

In `ValueInvestorsClub/ValueInvestorsClub/settings.py`, extend the existing `_pipelines` block (do not remove the VIC pipelines — this pipeline runs alongside them, keyed off `PIPELINE_MODE` the same way):

```python
if "holdings" in _pipeline_mode:
    _pipelines["ValueInvestorsClub.holding_pipeline.HoldingPipeline"] = 300
ITEM_PIPELINES = _pipelines
```

- [ ] **Step 2: Add the scrapy project's tests to pytest's testpaths**

Modify `pytest.ini`:

```ini
[pytest]
pythonpath = .
testpaths = api/tests ValueInvestorsClub/tests
python_files = test_*.py
markers =
    integration: mark a test as an integration test
    schema: mark a test as a schema validation test
```

- [ ] **Step 3: Run the full suite to confirm nothing broke**

Run: `docker-compose exec api pytest -v`
Expected: PASS — all `api/tests` tests plus the new `ValueInvestorsClub/tests` tests from Tasks 1–6.

- [ ] **Step 4: Add a spider-agnostic crawl runner to the shared shell lib**

Modify `scripts/lib_vic_scrape.sh` — generalize `vic_run_scrapy` to take a spider name instead of hardcoding `IdeaSpider` (keeps the existing call sites working by defaulting the arg):

```bash
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
```

Every existing caller of `vic_run_scrapy` (with no args) keeps working unchanged since it defaults to `IdeaSpider`.

- [ ] **Step 5: Commit**

```
git add ValueInvestorsClub/ValueInvestorsClub/settings.py pytest.ini scripts/lib_vic_scrape.sh
git commit -m "feat: wire HoldingPipeline into settings, pytest, and the shared crawl runner"
```

---

### Task 8: Live-site probe and coverage measurement (test_scope gate)

**Files:**
- Create: `scripts/probe_dataroma.sh`

- [ ] **Step 1: Encode the working WAF-bypass probe as a reusable script**

Dataroma's ModSecurity WAF returned "406 Not Acceptable" to a bare `curl` with no `-A`, but a Chrome-like UA + standard `Accept`/`Accept-Language` headers returned HTTP 200 (verified against `/m/home.php`, `/m/holdings.php?m=BRK`, `/m/hist/hist.php?f=BRK&s=AAPL` during design). Encode this as a preflight check before running the real spider, matching `vic_preflight_or_exit`'s pattern:

```bash
#!/usr/bin/env bash
# scripts/probe_dataroma.sh — verify Dataroma is reachable with browser-like headers
# before running DataromaSpider. Exits non-zero if blocked.
set -euo pipefail

UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

status=$(curl -s -o /dev/null -w "%{http_code}" \
  -A "$UA" \
  -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" \
  -H "Accept-Language: en-US,en;q=0.9" \
  --compressed \
  "https://www.dataroma.com/m/home.php")

if [ "$status" != "200" ]; then
  echo "Error: Dataroma probe failed (HTTP $status). Site may be blocking automated requests." >&2
  exit 1
fi
echo "Dataroma reachable (HTTP 200)."
```

- [ ] **Step 2: Run it to confirm it passes right now**

Run: `bash scripts/probe_dataroma.sh`
Expected: `Dataroma reachable (HTTP 200).`

- [ ] **Step 3: Measure coverage for the new code** (test_scope: true gate from the spec)

Run: `docker-compose exec api pytest --cov=ValueInvestorsClub/ValueInvestorsClub --cov-report=term-missing ValueInvestorsClub/tests -v`
Expected: All Task 1–6 modules (`models/Investor.py`, `models/Holding.py`, `holding_items.py`, `spiders/DataromaSpider.py`, `holding_pipeline.py`) show up in the report with no large uncovered blocks (`parse_home`, `parse_holdings`, `parse_stock_history`, `process_item` all exercised by the tests written above). Record the number; this plan does not lower it.

- [ ] **Step 4: Commit**

```
git add scripts/probe_dataroma.sh
git commit -m "feat: add Dataroma reachability probe script"
```

---

## Self-Review

**1. Spec coverage:** Data model (Task 1) ✓, crawl flow home→holdings→history (Tasks 3–5) ✓, pipeline/upsert with dedupe key (Task 6) ✓, politeness/probe risk from spec §4 (Task 8) ✓, testing §5 (fixtures + coverage gate, Tasks 1–8) ✓. HedgeFollowSpider is explicitly out of scope for this plan per the spec's build-order decision (Dataroma first) — a separate plan.

**2. Placeholder scan:** No TBD/TODO; every step has real code derived from live-fetched fixtures, not guessed markup.

**3. Type consistency:** `HoldingItem` fields (Task 2) match `HoldingPipeline.process_item` field access (Task 6) match `Holding` model columns (Task 1) — `quarter_date`/`shares`/`value_usd`/`pct_portfolio`/`activity` used identically throughout. `investor_id` format (`f"{source}:{slug}"`) is defined once in `Investor.__tablename__` docstring-equivalent comment and reused identically in `HoldingPipeline`.

## Plan Grill-Me

Stress-tested: (1) per-stock history requests scale to ~83 investors × ~20–30 holdings ≈ 2,000 requests for a full run — at `DOWNLOAD_DELAY=12s` (existing default) that's ~6.7 hours for one full Dataroma pass; flagged here rather than silently accepted — a future tuning pass (shorter delay once Dataroma's tolerance is empirically known, or checkpointed resume like the VIC backfill) may be needed but is out of scope for this first plan, which proves correctness on a small `CONCURRENT_REQUESTS_PER_DOMAIN=1`/small-slice run first. (2) `UniqueConstraint` on `Holding` plus manual get-or-create in the pipeline is redundant-safe: even if two rows race, the DB constraint stops silent duplication and the query-then-update pattern keeps the common case simple — accepted as adequate for a single-spider, single-process crawl (no concurrent writers).
