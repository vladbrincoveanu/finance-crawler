# Coverage Results

## Task 9 Baseline

Captured before observability changes on 2026-08-17.

- Backend command: `docker compose run --rm --no-deps api pytest api/tests ValueInvestorsClub/tests --cov=api --cov=ValueInvestorsClub --cov-report=term-missing`
- Backend total: 74%
- Frontend command: `docker compose -f docker-compose.test.yml run --rm frontend-tests npm run test:coverage -- --runInBand --coverageReporters=text-summary`
- Frontend statements: 16.51%
- Frontend lines: 17.32%

## Task 9 Final

Captured after instrumentation on 2026-08-17.

- Backend command: `docker compose run --rm --no-deps api pytest api/tests ValueInvestorsClub/tests --cov=api --cov=ValueInvestorsClub --cov-report=term-missing`
- Backend total: 74% (baseline maintained)
- Frontend command: `docker compose -f docker-compose.test.yml run --rm frontend-tests npm run test:coverage -- --runInBand --coverageReporters=text-summary`
- Frontend statements: 16.51% (baseline maintained)
- Frontend lines: 17.32% (baseline maintained)

Both coverage totals met the no-drop gate.
