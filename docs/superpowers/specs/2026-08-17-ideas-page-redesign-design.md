# Ideas Page Redesign

## Problem

`/ideas` currently presents search, position, contest, performance, and sorting controls as a large always-open form. The control wall pushes the ideas below the fold and makes the page feel like an admin form instead of a research feed.

## Goal

Make newest ideas fast to scan while keeping the existing filters and URL-driven sharing behavior available without occupying the default page.

## Scope

- Replace the always-visible filter form with one compact toolbar and a Chakra drawer.
- Replace the multi-column card grid with dense, clickable idea rows.
- Keep search, pagination, URL query parameters, API contracts, and idea detail links working.
- Preserve the existing dark VIC / FIELD NOTES visual language while adding clearer hierarchy and restrained amber/green/red signal colors.
- Update focused frontend and E2E coverage for the new controls and selectors.

## Non-goals

- No backend or API changes.
- No new filtering capabilities.
- No changes to navigation, detail pages, or the shared application shell.
- No replacement of Chakra UI.

## Design

### Default surface

The page contains:

1. A small investment-research eyebrow, `Investment ideas` heading, and one-line subtitle.
2. A single toolbar with company/ticker/author search, a `Filters` button, and a sort select.
3. Removable active-filter chips only when filters are applied.
4. A `Latest ideas` result label and dense rows.

The default sort is newest first (`sort_by=date`, `sort_order=desc`). The sort select exposes newest first, oldest first, performance high to low, and performance low to high. Performance labels describe raw API ordering; the row display still adjusts the visible result for short ideas using the existing sign convention. Selecting a performance sort ensures a performance period exists, defaulting to one year.

### Filter drawer

The drawer owns secondary controls:

- Position: all, long, or short.
- Contest winner: all, winners, or non-winners.
- Performance status: any, tracked, or untracked. This maps to the API's existing `has_performance` behavior, which checks for a performance row rather than guaranteeing a value for the selected period.
- Minimum and maximum performance.
- Performance period.

Drawer changes are draft-only. `Apply filters` copies the draft into applied filters, resets pagination, updates the URL, and triggers one query. `Reset` clears drawer-specific values, keeps search separate, resets pagination, and updates the URL. Closing the drawer without applying discards drafts.

The drawer is full-width on small screens and right-aligned on larger screens. Every interactive control keeps visible keyboard focus and an accessible label.

### Idea rows

Each row remains linked to the existing idea detail route and keeps `data-testid="idea-card"` for compatibility. The row shows:

- Company name and ticker, with a fallback to `company_id` while lookup is loading or unavailable.
- Author and posted-date metadata using the existing user lookup fallback.
- Long/Short badge and optional contest-winner badge.
- One selected performance value and period, adjusted for short ideas using the existing sign convention.

Rows use hover and focus-visible feedback without layout-shifting transforms. On mobile, metadata wraps below the company while the performance value stays right-aligned.

### URL and data flow

Applied supported `ListParams` remain the single source of truth for `useIdeas`. Supported query parameters continue to hydrate initial state and update through `navigate(..., { replace: true })`; unsupported legacy `search` text is not sent to the ideas endpoint. Draft drawer state never enters the query key until applied. The ideas endpoint does not implement its `search` parameter, so the search field uses existing company/user search endpoints for suggestions; selecting a company applies its exact ticker as `company_id`, and selecting an author applies its exact `user_link` as `user_id`. Clearing the selected suggestion removes that applied filter. Free text without a selected suggestion does not pretend to filter results.

The existing append-on-load-more deduplication stays in place. Results remain an array because the API does not expose a total count; the UI reports loaded results rather than inventing a total.

### Loading and error states

Keep the current API loading/error behavior, but reserve the result area so the toolbar does not jump. Error copy remains visible near the result area. `Load more` remains below the rows and disables when the API returns no additional results.

## Implementation boundaries

- `frontend/src/pages/IdeasPage.tsx`: applied/draft filter flow, URL hydration, toolbar, chips, drawer wiring, result layout.
- `frontend/src/components/IdeasFilterDrawer.tsx`: controlled drawer UI and draft interactions.
- `frontend/src/components/IdeaCard.tsx`: row presentation and selected-period performance display; preserve existing lookup fallbacks and route props.
- `frontend/src/tests/components/IdeaCard.test.tsx`: retain fallback/loading coverage and add row-specific assertions if needed.
- `frontend/src/tests/IdeasPage.test.tsx`: cover apply/reset/search/URL behavior with mocked hooks.
- `frontend/cypress/e2e/ideas.cy.ts`: update selectors and flows for toolbar, drawer, rows, and load more.

## Acceptance criteria

- Default `/ideas` shows no large filter form and no tabs.
- First viewport shows search, filters, sort, and multiple idea rows at desktop width.
- Search suggestions select a company or author and update the corresponding URL parameter and results; unselected free text does not issue a misleading `search` query.
- All existing filter types still update URL parameters and results.
- Closing an unapplied drawer does not trigger a request or change URL filters.
- Applying/resetting filters triggers one applied query and updates active chips.
- Idea rows navigate to the correct detail route and preserve fallback content.
- Layout works at 375px, 768px, 1024px, and 1440px without horizontal scrolling.
- Frontend build, lint, unit tests, and the targeted E2E spec pass, or failures are reported with their cause.
