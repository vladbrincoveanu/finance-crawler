---
title: Whole application teaching walkthrough
date: 2026-08-17
status: approved
ui_scope: false
graph_scope: false
test_scope: true
---

# Goal

Teach the current ValueInvestorsClub application from startup through dashboard reads and source ingestion, using observed behavior rather than treating approved architecture as implemented behavior.

# Scope

The first lesson covers Docker startup, the React-to-FastAPI read path, Dataroma live parsing, HedgeFollow live failure, fixture parsing, and the source/staging/curated boundary. It includes runnable no-database crawl commands and local HTML diagrams. Later lessons can address the HedgeFollow adapter, API/UI verification, promotion, and retrieval.

# Teaching decisions

- Use one large map plus short staged lessons rather than a single prose explanation.
- Run crawlers with pipelines disabled before testing database writes.
- Mark each boundary green, amber, or red based on direct evidence.
- Keep source facts, parser-derived values, staging rows, and curated rows visibly distinct.
- Link every claim to a file path, line range, command, or observed output.

### Module: Lesson HTML
- **Responsibility:** Present the step-by-step walkthrough, diagrams, code references, commands, and observed crawler results.
- **Interface:** Local browser URL; links to project files and the architecture reference.
- **Dependencies:** `assets/lesson.css`; no external runtime libraries.
- **Size target:** One self-contained lesson under 400 lines of HTML.

### Module: Architecture reference
- **Responsibility:** Provide a compact map for later navigation.
- **Interface:** Local browser URL linked from the lesson.
- **Dependencies:** `assets/lesson.css`.
- **Size target:** Under 150 lines of HTML.

### Module: Crawl verification lab
- **Responsibility:** Demonstrate parser boundaries without writing to Postgres.
- **Interface:** Scrapy command with `ITEM_PIPELINES='{}'`, bounded item count, and JSON feed output.
- **Dependencies:** Scrapy, source access, spider settings, source fixtures for offline comparison.
- **Size target:** Commands and expected output only; no new application abstraction.

# Verification

- `docker compose config` must parse.
- Dataroma bounded crawl must produce non-empty `HoldingItem` JSON.
- HedgeFollow fixture parser must produce common-stock observations.
- HedgeFollow live crawl result must be recorded honestly if the current adapter returns zero items or raises a protocol error.
- Frontend and Python test gaps must be shown instead of implied to pass.
