# Ideas Page Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `/ideas` from an always-open filter form into a compact newest-first research list with a filter drawer, working company/author search suggestions, and responsive dense rows.

**Architecture:** Keep `IdeasPage` as the owner of applied URL filters and pagination. Extract pure URL/sort/filter-label logic into `ideasFilters.ts`, isolate draft drawer controls in `IdeasFilterDrawer`, and keep lookup/performance behavior in `IdeaCard` while changing only its presentation to a row. No backend contract changes.

**Tech Stack:** React 18, TypeScript, Chakra UI 2, React Query 3, React Router 6, Jest + Testing Library, Cypress.

---

## File Map

- Create `frontend/src/pages/ideasFilters.ts`: typed filter defaults, URL parsing/serialization, sort mapping, active-filter labels.
- Create `frontend/src/components/IdeasFilterDrawer.tsx`: controlled Chakra drawer; draft state never fetches.
- Modify `frontend/src/pages/IdeasPage.tsx`: compact toolbar, suggestion search, drawer wiring, chips, dense result list.
- Modify `frontend/src/components/IdeaCard.tsx`: dense accessible row, one selected-period metric, existing lookup fallbacks and route props.
- Create `frontend/src/tests/ideasFilters.test.ts`: pure helper tests.
- Create `frontend/src/tests/IdeasPage.test.tsx`: drawer apply/reset, suggestion selection, URL updates, and pagination behavior.
- Modify `frontend/src/tests/components/IdeaCard.test.tsx`: row semantics and selected performance-period assertions.
- Modify `frontend/cypress/e2e/ideas.cy.ts`: replace selectors for the compact toolbar and drawer.

## Task 1: Lock Filter and URL Semantics With Tests

**Files:**
- Create: `frontend/src/pages/ideasFilters.ts`
- Create: `frontend/src/tests/ideasFilters.test.ts`

- [ ] **Step 1: Write failing helper tests**

Create tests for these exported behaviors:

```ts
const DEFAULT_FILTERS = { skip: 0, limit: 20 };

test('hydrates supported filters from URL search params', () => {
  expect(getInitialFilters('?is_short=true&min_performance=4.5&sort_order=asc'))
    .toEqual({
      ...DEFAULT_FILTERS,
      is_short: true,
      min_performance: 4.5,
      sort_order: 'asc',
    });
});

test('ignores invalid numeric values and omits pagination and unsupported search from the URL', () => {
  const filters = { ...DEFAULT_FILTERS, min_performance: Number.NaN };
  expect(toQueryString({ ...filters, search: 'ignored' })).toBe('');
});

test('maps sort selection to API params', () => {
  expect(sortSelectionToFilters('performance-asc')).toEqual({
    sort_by: 'performance',
    sort_order: 'asc',
    performance_period: 'one_year_perf',
  });
});

test('removes a filter without mutating the input', () => {
  const filters = { ...DEFAULT_FILTERS, is_short: true };
  expect(removeFilter(filters, 'is_short')).toEqual(DEFAULT_FILTERS);
  expect(filters.is_short).toBe(true);
});

test('labels only applied non-pagination filters', () => {
  expect(getActiveFilterLabels({
    ...DEFAULT_FILTERS,
    is_short: true,
    is_contest_winner: false,
    has_performance: true,
  })).toEqual([
    { key: 'is_short', label: 'Short ideas' },
    { key: 'is_contest_winner', label: 'Not contest winners' },
    { key: 'has_performance', label: 'Performance tracked' },
  ]);
});
```

Also test every supported `performance_period` label and the `all`/`long`/`short` and `all`/`yes`/`no` UI-to-filter mappings used by the drawer.

- [ ] **Step 2: Run the focused helper test and confirm failure**

Run: `cd frontend && npm test -- --runInBand src/tests/ideasFilters.test.ts`

Expected: FAIL because `frontend/src/pages/ideasFilters.ts` does not exist yet.

- [ ] **Step 3: Implement the pure helper module**

Export these exact types and functions:

```ts
export const PAGE_SIZE = 20;
export const DEFAULT_FILTERS: ListParams = { skip: 0, limit: PAGE_SIZE };
export type SortSelection = 'newest' | 'oldest' | 'performance-desc' | 'performance-asc';
export interface ActiveFilterLabel { key: keyof ListParams; label: string; }

export function getInitialFilters(search: string): ListParams;
export function toQueryString(filters: ListParams): string;
export function removeFilter(filters: ListParams, field: keyof ListParams): ListParams;
export function sortSelectionToFilters(selection: SortSelection): Pick<ListParams, 'sort_by' | 'sort_order' | 'performance_period'>;
export function filtersToSortSelection(filters: ListParams): SortSelection;
export function getActiveFilterLabels(filters: ListParams): ActiveFilterLabel[];
```

`getInitialFilters` must parse supported boolean, numeric, string, and sorting parameters while intentionally omitting unsupported `search`; invalid numeric values are omitted. `toQueryString` must omit `skip`, `limit`, and `search`, preserve false booleans, and omit `undefined`, `null`, empty strings, and non-finite numbers. `removeFilter` must return a shallow copy with the selected key deleted. `sortSelectionToFilters` must use date descending for newest, date ascending for oldest, and performance with the matching order plus `one_year_perf` for performance selections.

- [ ] **Step 4: Re-run helper tests**

Run: `cd frontend && npm test -- --runInBand src/tests/ideasFilters.test.ts`

Expected: PASS.

- [ ] **Step 5: Commit the pure filter contract**

```bash
git add frontend/src/pages/ideasFilters.ts frontend/src/tests/ideasFilters.test.ts
git commit -m "test: define ideas filter semantics"
```

## Task 2: Add Draft Filter Drawer and Compact Page Controls

**Files:**
- Create: `frontend/src/components/IdeasFilterDrawer.tsx`
- Modify: `frontend/src/pages/IdeasPage.tsx`
- Create: `frontend/src/tests/IdeasPage.test.tsx`

- [ ] **Step 1: Write page interaction tests**

Mock `useIdeas` with a stable result, mock `companiesApi.getCompanies` and `usersApi.getUsers`, render under `QueryClientProvider` and `MemoryRouter`, and cover:

```tsx
test('keeps filter changes in the drawer until Apply filters', async () => {
  render(<IdeasPage />, { wrapper: createWrapper(['/ideas']) });
  await user.click(screen.getByRole('button', { name: /filters/i }));
  await user.selectOptions(screen.getByLabelText(/position/i), 'short');
  expect(screen.getByRole('button', { name: /apply filters/i })).toBeInTheDocument();
  expect(mockGetIdeas).toHaveBeenCalledTimes(1);
  await user.click(screen.getByRole('button', { name: /apply filters/i }));
  await waitFor(() => expect(mockGetIdeas).toHaveBeenLastCalledWith(
    expect.objectContaining({ is_short: true, skip: 0 })
  ));
});

test('closing the drawer discards draft changes', async () => {
  render(<IdeasPage />, { wrapper: createWrapper(['/ideas']) });
  await user.click(screen.getByRole('button', { name: /filters/i }));
  await user.selectOptions(screen.getByLabelText(/position/i), 'short');
  await user.click(screen.getByRole('button', { name: /close/i }));
  expect(mockGetIdeas).toHaveBeenCalledTimes(1);
  expect(window.location.search).toBe('');
});

test('selecting a company suggestion applies the exact ticker filter', async () => {
  mockCompaniesApi.getCompanies.mockResolvedValue([{ ticker: 'AAPL', company_name: 'Apple Inc.' }]);
  render(<IdeasPage />, { wrapper: createWrapper(['/ideas']) });
  await user.type(screen.getByTestId('company-search'), 'Apple');
  await user.click(await screen.findByTestId('company-option'));
  await waitFor(() => expect(mockGetIdeas).toHaveBeenLastCalledWith(
    expect.objectContaining({ company_id: 'AAPL', skip: 0 })
  ));
  expect(window.location.search).toContain('company_id=AAPL');
});

test('reset clears applied drawer filters and active chips', async () => {
  render(<IdeasPage />, { wrapper: createWrapper(['/ideas?is_short=true']) });
  await user.click(screen.getByRole('button', { name: /filters/i }));
  await user.click(screen.getByRole('button', { name: /^reset$/i }));
  expect(screen.queryByText('Short ideas')).not.toBeInTheDocument();
  expect(window.location.search).toBe('');
});
```

Add a test that the sort select translates `performance-desc` to `sort_by=performance`, `sort_order=desc`, and a one-year period. Add a test that `Load more` increments `skip` by `limit` and appends only unseen IDs.

- [ ] **Step 2: Run page tests and confirm failure**

Run: `cd frontend && npm test -- --runInBand src/tests/IdeasPage.test.tsx`

Expected: FAIL because the drawer, toolbar selectors, and page behavior are not implemented.

- [ ] **Step 3: Implement `IdeasFilterDrawer`**

Use a controlled prop contract:

```ts
interface IdeasFilterDrawerProps {
  isOpen: boolean;
  filters: ListParams;
  onClose: () => void;
  onApply: (filters: ListParams) => void;
  onReset: () => void;
}
```

When `isOpen` changes to true, copy `filters` into local draft state. Render a right-side Chakra `Drawer` with `DrawerOverlay`, `DrawerContent`, `DrawerHeader`, `DrawerBody`, and `DrawerFooter`. Use labeled selects for position, contest winner, and performance status; number inputs for min/max; and a labeled performance-period select. Use `size="sm"`, `maxW="100vw"`, and `w={{ base: '100vw', md: '420px' }}` for responsive width. `Apply filters` calls `onApply({ ...draft, skip: 0 })` then `onClose`; `Reset` calls `onReset` and `onClose`. Do not call the API from this component.

- [ ] **Step 4: Replace `IdeasPage` form with the toolbar and drawer**

Use `getInitialFilters(location.search)` for applied state and keep the existing append/deduplicate pagination effect. Remove the old always-visible `Select`/`Input` form. Add:

```tsx
<InputGroup position="relative">
  <Input
    data-testid="company-search"
    aria-label="Search company, ticker, or author"
    value={searchQuery}
    placeholder="Search company, ticker, or author"
    onChange={event => { setSearchQuery(event.target.value); setSearchOpen(true); }}
  />
  {searchOpen && suggestions.length > 0 && (
    <Box role="listbox" position="absolute" top="calc(100% + 8px)" left={0} right={0} zIndex={20}>
      {suggestions.map(suggestion => (
        <Button
          key={`${suggestion.type}-${suggestion.value}`}
          data-testid={`${suggestion.type}-option`}
          role="option"
          onClick={() => applySearchSuggestion(suggestion)}
        >
          {suggestion.label}
        </Button>
      ))}
    </Box>
  )}
</InputGroup>
<Button aria-label="Open filters" onClick={onOpen}>Filters</Button>
<Select aria-label="Sort ideas" value={filtersToSortSelection(filters)} onChange={handleSortChange}>
  <option value="newest">Newest first</option>
  <option value="oldest">Oldest first</option>
  <option value="performance-desc">Performance high to low</option>
  <option value="performance-asc">Performance low to high</option>
</Select>
```

Fetch suggestions only when the trimmed query has at least two characters, using `companiesApi.getCompanies({ search: query, limit: 5 })` and `usersApi.getUsers({ search: query, limit: 5 })`. Map company suggestions to `{ type: 'company', value: company.ticker, label: `${company.company_name} (${company.ticker})` }` and user suggestions to `{ type: 'user', value: user.user_link, label: `@${user.username}` }`. Selecting a suggestion sets the matching applied filter, resets `skip`, clears any unsupported `search` value, closes suggestions, and leaves other applied filters intact. The page must never send free text as an ideas `search` filter because that endpoint ignores it.

Render `getActiveFilterLabels(filters)` as Chakra `Tag` chips with `TagCloseButton`; each close button calls `removeFilter` and resets pagination. Pass applied filters into `IdeasFilterDrawer`. Keep URL serialization in one effect and only navigate when the serialized search differs from `location.search.slice(1)`.

- [ ] **Step 5: Run page tests and fix until green**

Run: `cd frontend && npm test -- --runInBand src/tests/IdeasPage.test.tsx src/tests/ideasFilters.test.ts`

Expected: PASS with no open-handle warnings. If React Query retains timers, construct each test `QueryClient` with `retry: false`, `cacheTime: 0`, and clear it in `afterEach`.

- [ ] **Step 6: Commit toolbar and drawer**

```bash
git add frontend/src/components/IdeasFilterDrawer.tsx frontend/src/pages/IdeasPage.tsx frontend/src/pages/ideasFilters.ts frontend/src/tests/IdeasPage.test.tsx frontend/src/tests/ideasFilters.test.ts
git commit -m "feat: simplify ideas filters"
```

## Task 3: Convert Idea Cards Into Dense Rows

**Files:**
- Modify: `frontend/src/components/IdeaCard.tsx`
- Modify: `frontend/src/tests/components/IdeaCard.test.tsx`
- Modify: `frontend/src/pages/IdeasPage.tsx`

- [ ] **Step 1: Add failing row assertions**

Extend the existing component tests to assert `data-testid="idea-card"`, the company link to `/ideas/test-idea-1`, the `Long` and `Contest Winner` badges, author fallback content, and a selected `one_month_perf` value rendered as a signed percentage. Add a short-idea fixture assertion that a positive stored stock move is displayed as a negative investor result.

- [ ] **Step 2: Run the component test and confirm the new metric assertion fails**

Run: `cd frontend && npm test -- --runInBand src/tests/components/IdeaCard.test.tsx`

Expected: existing tests pass; the new selected-period row assertion fails because the component still renders the card grid and all four metrics.

- [ ] **Step 3: Implement the row presentation**

Add `performancePeriod?: string` to `IdeaCardProps`, with `one_year_perf` as the fallback. Map API period names to `Performance` keys and compact labels (`1W`, `2W`, `1M`, `3M`, `6M`, `1Y`, `2Y`, `3Y`, `5Y`). Keep the existing `useQuery` calls and fallback IDs. Replace the outer card styling with a bordered-bottom row using `display="flex"`, `justify="space-between"`, `gap`, `py`, and responsive wrapping. Keep `data-testid="idea-card"`.

Render company as the primary detail link and add an outer row click/keyboard handler that navigates to `${linkBasePath}/${id}` while stopping propagation from the author filter link. Use `role="link"`, `tabIndex={0}`, and Enter/Space handling for keyboard users. Add `_hover` background/border feedback, `cursor="pointer"`, and no transform. Render one selected performance value in the right column; use the existing short adjustment and green/red color logic. Render the period label under the value and a neutral `--` when no metric exists.

Pass `performancePeriod={filters.performance_period}` from `IdeasPage` so rows reflect the drawer/sort period.

- [ ] **Step 4: Run component tests**

Run: `cd frontend && npm test -- --runInBand src/tests/components/IdeaCard.test.tsx`

Expected: PASS, including loading and fallback assertions.

- [ ] **Step 5: Commit dense rows**

```bash
git add frontend/src/components/IdeaCard.tsx frontend/src/pages/IdeasPage.tsx frontend/src/tests/components/IdeaCard.test.tsx
git commit -m "feat: show ideas as dense rows"
```

## Task 4: Update End-to-End Coverage

**Files:**
- Modify: `frontend/cypress/e2e/ideas.cy.ts`

- [ ] **Step 1: Replace stale form selectors**

Update the setup assertion to `cy.contains('Investment ideas')`. Replace the old company/user toggle tests with:

```ts
cy.get('[data-testid="company-search"]').type('Apple');
cy.get('[data-testid="company-option"]').first().click();
cy.url().should('include', 'company_id=');

cy.get('[aria-label="Open filters"]').click();
cy.get('[aria-label="Position"]').select('short');
cy.contains('button', /apply filters/i).click();
cy.url().should('include', 'is_short=true');
cy.contains('Short ideas').should('be.visible');
```

Add a close-without-apply test that records the current URL, opens the drawer, changes position, closes it, and asserts the URL is unchanged. Keep the load-more assertion but continue using `[data-testid="load-more-button"]` and `[data-testid="idea-card"]`. Keep the detail navigation assertion, clicking the company link inside the first row if the outer row role link is not the stable target.

- [ ] **Step 2: Run the targeted Cypress spec**

Run: `cd frontend && npm run test:e2e -- --spec cypress/e2e/ideas.cy.ts`

Expected: PASS against the running frontend/API. If the local API fixture has no matching company suggestion, use an existing fixture company string from the API response rather than weakening the selector assertion.

- [ ] **Step 3: Commit E2E updates**

```bash
git add frontend/cypress/e2e/ideas.cy.ts
git commit -m "test: cover ideas drawer flow"
```

## Task 5: Responsive Verification and Final Simplification

**Files:**
- Modify only the files needed to correct verified failures from Tasks 2-4.

- [ ] **Step 1: Run the frontend quality checks**

Run:

```bash
cd frontend && npm run lint
cd frontend && npm run build
cd frontend && npm test -- --runInBand
```

Expected: lint, TypeScript build, and all unit tests pass.

- [ ] **Step 2: Smoke-test desktop and mobile routes**

With the app running at `http://localhost:3010`, verify `/ideas` at viewport widths 1440, 1024, 768, and 375. Confirm the first viewport shows the toolbar and multiple rows; confirm no horizontal scrollbar; open and close the drawer; apply a filter; remove an active chip; select a search suggestion; click a row/company link; and load another page.

- [ ] **Step 3: Inspect the final diff for scope and accessibility**

Run:

```bash
git diff -- frontend/src/pages/IdeasPage.tsx frontend/src/components/IdeasFilterDrawer.tsx frontend/src/components/IdeaCard.tsx frontend/src/pages/ideasFilters.ts frontend/src/tests frontend/cypress/e2e/ideas.cy.ts
```

Confirm no old filter headings, tabs, unsupported `search` query, emoji icons, missing labels, or unrelated files entered the implementation commits. Confirm focus rings, 44px-ish touch targets, `aria-label`s, and reduced motion are inherited or explicitly preserved.

- [ ] **Step 4: Commit verified cleanup**

```bash
git add frontend/src frontend/cypress/e2e/ideas.cy.ts
git commit -m "fix: polish ideas page responsive flow"
```
