# Repository Guidelines

## Project Structure & Module Organization
- `api/`: FastAPI backend (`main.py`, `routes/`, `schemas/`, `database/`) plus backend tests in `api/tests/`.
- `ValueInvestorsClub/`: Scrapy project (`spiders/IdeaSpider.py`, pipelines, and SQLAlchemy models in `models/`).
- `frontend/`: Vite + React + TypeScript app. UI code lives in `src/components/`, `src/pages/`, `src/hooks/`, API client code in `src/api/`, unit tests in `src/tests/`, and E2E specs in `cypress/e2e/`.
- Root-level scripts and infra: `run_tests.sh`, `startScript.sh`, `docker-compose*.yml`, plus data/assets in `data/`, `pics/`, and `idea_links*.txt`.

## Build, Test, and Development Commands
- `uv venv .venv && source .venv/bin/activate`: Create and activate Python environment.
- `uv pip install -r requirements.txt` (or `requirements-dev.txt`): Install backend dependencies.
- `docker-compose up -d && ./startScript.sh`: Start and initialize Postgres.
- `python -m api.main`: Run API locally.
- `cd frontend && npm ci && npm run dev`: Run frontend locally.
- `./run_tests.sh`: Full backend + schema + frontend + optional E2E flow.
- `pytest -xvs api/tests/`: Backend tests only.
- `cd frontend && npm test` or `npm run test:coverage`: Frontend unit tests.
- `ruff check . && mypy api/ && cd frontend && npm run lint`: Match CI linting checks.

## Coding Style & Naming Conventions
- Python: 4-space indentation, `snake_case` for functions/modules, `PascalCase` for classes, and type hints for new API-facing code.
- TypeScript/React: follow existing 2-space indentation, `PascalCase` component/page names (`IdeaCard.tsx`), and `useX.ts` for hooks.
- Keep imports and formatting compatible with `black`, `isort`, `ruff`, `mypy`, and frontend `eslint`.

## Testing Guidelines
- Backend uses `pytest` (`pytest.ini`): test files must match `test_*.py`; markers include `integration` and `schema`.
- Frontend unit tests use Jest (`src/**/*.test.(ts|tsx)`); E2E uses Cypress (`cypress/e2e/**/*.cy.{ts,tsx}`).
- Add tests with every behavior change; run targeted tests first, then `./run_tests.sh` before opening a PR.

## Commit & Pull Request Guidelines
- Prefer short, imperative commit subjects (examples from history style: `Fix ...`, `Add ...`, `Improve ...`), scoped to one change.
- Avoid vague commit messages; include context in the body when touching API contracts or DB behavior.
- PRs should include: purpose, affected paths, test commands run, linked issue (if any), and screenshots for frontend UI changes.
- Ensure CI passes (`lint` and Docker-based tests) before requesting review.

## Codebase Exploration

Default to `graphify query "<question>"` over `grep` for codebase exploration questions if this repo has `graphify-out/graph.json` (build it with `/graphify .` — one-time cost amortized across all future questions). Skip straight to grep if the graph is missing, stale (>7 days old with newer commits), an exact string/regex match is needed, or graph queries return 0 results after retrying with synonyms.

## Agent Delegation

- Always use subagents for implementation, investigation, testing, and code review whenever a suitable subagent is available.
- Keep the main agent focused on coordination, integration, and final verification; do not implement inline when delegation is feasible.
