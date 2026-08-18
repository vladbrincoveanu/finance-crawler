# VIC Comments and Source Crawl Views Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose already-crawled ValueInvestorsClub forum comments on idea details, make the three source routes explicit, and add a non-blocking Grafana link to the product dashboard.

**Architecture:** Keep the existing crawler and `comments` table unchanged. Add the comment model to the API model registry, return an ordered `comments` array from the existing idea-detail response, and render it through the shared `IdeaDetailPage` used by both `/ideas/:id` and `/articles/:id`. Keep source verification and curated holding boundaries unchanged; add only literal route labels and an external operations link.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy, PostgreSQL/SQLite tests, React 18, TypeScript, Chakra UI, React Query, Jest + Testing Library, Playwright.

---

## Scope Guard

- Comments are read-only forum posts captured by the existing ValueInvestorsClub crawl.
- Do not add comment creation, editing, deletion, moderation, or identity resolution.
- Do not add a crawl-start control. Manual/operator crawl execution remains outside this UI change.
- Do not add a migration. The `comments` table and `comments.idea_id` foreign key already exist.
- Do not replace `/sources`, merge holding data with ideas, or turn Grafana into an application dependency.

## File Map

- Modify `api/models/__init__.py`: register and export the existing SQLAlchemy `Comment` model so API imports and test metadata include it.
- Modify `api/schemas/schemas.py`: define `CommentResponse` and add the required defaulted `comments` array to `IdeaDetailResponse`.
- Modify `api/routes/ideas.py`: query comments for the requested idea and map them in deterministic order.
- Modify `api/tests/test_ideas_api.py`: seed crawled comments and verify ownership, ordering, text, and empty results.
- Modify `api/validate_schema.py`: require the new OpenAPI schema and detail-response field.
- Modify `api/tests/test_schema_validation.py`: lock the new schema requirements with failing tests first.
- Regenerate `api/schema/openapi.json`: write it through the existing schema validator after API changes; do not hand-edit generated JSON.
- Modify `frontend/src/types/api.ts`: add the frontend comment contract and required `IdeaDetail.comments` array.
- Modify `frontend/src/pages/IdeaDetailPage.tsx`: render the read-only discussion section shared by ideas and articles.
- Create `frontend/src/tests/IdeaDetailPage.test.tsx`: cover populated and empty discussion states.
- Modify `frontend/src/tests/_useIdeas.test.ts`: include `comments` in the hook detail fixture.
- Modify `frontend/src/tests/apiService.test.ts`: include `comments` in the detail API fixture.
- Modify `frontend/src/components/SourceVerificationCard.tsx`: show each literal local route next to its existing matching CTA.
- Modify `frontend/src/pages/HomePage.tsx`: add the external Grafana ingestion-dashboard link.
- Modify `frontend/src/tests/sources.test.tsx`: assert all three route labels and destinations.
- Modify `frontend/src/tests/HomePage.test.tsx`: assert the Grafana link contract.
- Create `frontend/e2e/comments-sources.visual.spec.ts`: screenshot source verification and dashboard surfaces at required widths and assert their route/link labels.

## Task 1: Add Crawled Comments to the Idea Detail API

**Files:**
- Modify: `api/tests/test_ideas_api.py`
- Modify: `api/models/__init__.py`
- Modify: `api/schemas/schemas.py`
- Modify: `api/routes/ideas.py`

- [ ] **Step 1: Extend the API fixture with forum comments and write assertions first**

Import the existing model in `api/tests/test_ideas_api.py`:

```python
from ValueInvestorsClub.ValueInvestorsClub.models.Comment import Comment
```

Add three stored crawl rows to the existing `test_data` fixture. Two belong to `idea1` and share a timestamp so the secondary ID ordering is exercised; the third belongs to `idea2` and must never appear in `idea1`'s response:

```python
comment_later_id = "comment-z"
comment_first_id = "comment-a"
comment_other_id = "comment-other"

comment_later = Comment(
    id=comment_later_id,
    idea_id=idea1_id,
    author="Investor Z",
    posted_at="2026-08-17T10:00:00Z",
    text="Later comment",
)
comment_first = Comment(
    id=comment_first_id,
    idea_id=idea1_id,
    author="Investor A",
    posted_at="2026-08-17T10:00:00Z",
    text="First line\nSecond line",
)
comment_other = Comment(
    id=comment_other_id,
    idea_id=idea2_id,
    author="Other investor",
    posted_at="2026-08-17T09:00:00Z",
    text="Belongs to another idea",
)

db_session.add_all([comment_later, comment_first, comment_other])
db_session.commit()
```

Extend the fixture return value with:

```python
"comments": [comment_later, comment_first, comment_other],
```

Extend `test_get_idea_detail` after the existing performance assertions:

```python
comments = idea["comments"]
assert [comment["id"] for comment in comments] == ["comment-a", "comment-z"]
assert comments[0]["author"] == "Investor A"
assert comments[0]["posted_at"] == "2026-08-17T10:00:00Z"
assert comments[0]["text"] == "First line\nSecond line"
assert all(comment["id"] != "comment-other" for comment in comments)
```

Add a separate empty-state API test:

```python
def test_get_idea_detail_returns_empty_comments(client, test_data):
    idea_id = test_data["ideas"][2].id

    response = client.get(f"/ideas/{idea_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["comments"] == []
```

- [ ] **Step 2: Run the focused tests and confirm the contract fails**

Run:

```bash
pytest -xvs api/tests/test_ideas_api.py::test_get_idea_detail api/tests/test_ideas_api.py::test_get_idea_detail_returns_empty_comments
```

Expected: FAIL because `IdeaDetailResponse` does not yet expose `comments` and the route does not populate it.

- [ ] **Step 3: Register the existing `Comment` model**

In `api/models/__init__.py`, add the import beside the other idea-related models:

```python
from ValueInvestorsClub.ValueInvestorsClub.models.Comment import Comment
```

Add `"Comment",` to `__all__`. Do not create a second model or change the table definition.

- [ ] **Step 4: Add the Pydantic response contract**

In `api/schemas/schemas.py`, keep the existing `Field` import and add this model after `CatalystsResponse`:

```python
class CommentResponse(BaseModel):
    """A read-only forum comment captured by the VIC crawler."""

    id: str
    author: str
    posted_at: str
    text: str

    model_config = {"from_attributes": True}
```

Add the field to `IdeaDetailResponse`:

```python
comments: List[CommentResponse] = Field(default_factory=list)
```

The field is required in serialized responses but uses a default factory so `model_validate(idea)` starts with an empty list before the route attaches rows.

- [ ] **Step 5: Query and map comments in the existing detail route**

Update the imports in `api/routes/ideas.py`:

```python
from api.models import Comment, Idea, Description, Catalysts, Performance
```

Update the schema imports:

```python
from api.schemas import (
    CommentResponse,
    IdeaResponse,
    IdeaDetailResponse,
    DescriptionResponse,
    CatalystsResponse,
    PerformanceResponse,
)
```

After the description and catalysts queries, query only the requested idea and apply the two-part stable ordering:

```python
comments = (
    db.query(Comment)
    .filter(Comment.idea_id == idea_id)
    .order_by(Comment.posted_at.asc(), Comment.id.asc())
    .all()
)
```

After `result = IdeaDetailResponse.model_validate(idea)`, attach the rows explicitly:

```python
result.comments = [CommentResponse.model_validate(comment) for comment in comments]
```

Keep the existing 404 handling, performance fallback, and response shape unchanged. A missing row set produces `[]`; no second endpoint or crawler call is introduced.

- [ ] **Step 6: Run the API tests and confirm they pass**

Run:

```bash
pytest -xvs api/tests/test_ideas_api.py
```

Expected: all idea, company, user, filtering, pagination, and detail tests pass, including the two comment assertions.

- [ ] **Step 7: Commit the API behavior**

```bash
git add api/models/__init__.py api/schemas/schemas.py api/routes/ideas.py api/tests/test_ideas_api.py
git commit -m "feat(api): expose crawled VIC comments"
```

## Task 2: Lock and Regenerate the OpenAPI Contract

**Files:**
- Modify: `api/tests/test_schema_validation.py`
- Modify: `api/validate_schema.py`
- Modify: `api/schema/openapi.json`

- [ ] **Step 1: Add failing schema requirements**

Add these tests to `api/tests/test_schema_validation.py`:

```python
def test_schema_validator_requires_comment_response_schema():
    schema = deepcopy(app.openapi())
    schema["components"]["schemas"].pop("CommentResponse")

    assert validate_schema(schema) is False


def test_schema_validator_requires_idea_detail_comments_field():
    schema = deepcopy(app.openapi())
    schema["components"]["schemas"]["IdeaDetailResponse"]["properties"].pop("comments")

    assert validate_schema(schema) is False
```

- [ ] **Step 2: Run the new schema tests and confirm they fail**

Run:

```bash
pytest -xvs api/tests/test_schema_validation.py
```

Expected: the new tests fail because `validate_schema` does not yet require the comment schema or field.

- [ ] **Step 3: Extend the schema validator**

Add `"CommentResponse"` to `required_schemas` in `api/validate_schema.py`.

After the existing `IdeaResponse` checks, validate the response shape and all comment fields:

```python
idea_detail = schemas.get("IdeaDetailResponse", {})
idea_detail_properties = idea_detail.get("properties", {})
comments_property = idea_detail_properties.get("comments", {})
if comments_property.get("type") != "array" or comments_property.get("items", {}).get(
    "$ref"
) != "#/components/schemas/CommentResponse":
    print("IdeaDetailResponse.comments must be an array of CommentResponse")
    return False

comment_properties = schemas.get("CommentResponse", {}).get("properties", {})
required_comment_fields = ["id", "author", "posted_at", "text"]
missing_comment_fields = [
    field for field in required_comment_fields if field not in comment_properties
]
if missing_comment_fields:
    print(
        "Missing required fields in CommentResponse: "
        + ", ".join(missing_comment_fields)
    )
    return False
```

Leave existing endpoint and crawl-schema checks intact.

- [ ] **Step 4: Run schema tests and regenerate OpenAPI**

Run:

```bash
pytest -xvs api/tests/test_schema_validation.py
python -m api.validate_schema
```

Expected: schema tests pass; the validator prints `Schema validation successful!`; `api/schema/openapi.json` contains `CommentResponse` and the `comments` property on `IdeaDetailResponse`.

- [ ] **Step 5: Commit the schema contract**

```bash
git add api/tests/test_schema_validation.py api/validate_schema.py api/schema/openapi.json
git commit -m "test(api): validate comment contract"
```

## Task 3: Render Crawled Comments on Both Detail Routes

**Files:**
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/pages/IdeaDetailPage.tsx`
- Create: `frontend/src/tests/IdeaDetailPage.test.tsx`
- Modify: `frontend/src/tests/_useIdeas.test.ts`
- Modify: `frontend/src/tests/apiService.test.ts`

- [ ] **Step 1: Add detail-page tests before implementation**

Create `frontend/src/tests/IdeaDetailPage.test.tsx` with a mocked detail hook and both data states:

```tsx
import React from 'react';
import { render, screen } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import IdeaDetailPage from '../pages/IdeaDetailPage';
import { useIdeaDetail } from '../hooks/useIdeas';
import theme from '../theme';

jest.mock('../hooks/useIdeas', () => ({
  useIdeaDetail: jest.fn(),
}));

const mockUseIdeaDetail = useIdeaDetail as jest.MockedFunction<typeof useIdeaDetail>;

const renderPage = () => render(
  <ChakraProvider theme={theme}>
    <MemoryRouter initialEntries={['/articles/idea-1']}>
      <Routes>
        <Route path="/articles/:id" element={<IdeaDetailPage basePath="/articles" backLabel="Back to Articles" />} />
      </Routes>
    </MemoryRouter>
  </ChakraProvider>,
);

const baseIdea = {
  id: 'idea-1',
  link: 'https://valueinvestorsclub.test/ideas/idea-1',
  company_id: 'AAPL',
  user_id: 'https://valueinvestorsclub.test/users/investor-a',
  date: '2026-08-17T00:00:00Z',
  is_short: false,
  is_contest_winner: false,
  company: { ticker: 'AAPL', company_name: 'Apple Inc.' },
  user: { username: 'investor-a', user_link: 'https://valueinvestorsclub.test/users/investor-a' },
  description: { description: 'Thesis' },
  comments: [
    {
      id: 'comment-a',
      author: 'Investor A',
      posted_at: '2026-08-17T10:00:00Z',
      text: 'First line\nSecond line',
    },
  ],
};

describe('IdeaDetailPage comments', () => {
  test('renders captured forum comments and preserves text metadata', () => {
    mockUseIdeaDetail.mockReturnValue({
      data: baseIdea,
      isLoading: false,
      isError: false,
      error: null,
    } as ReturnType<typeof useIdeaDetail>);

    renderPage();

    expect(screen.getByRole('heading', { name: 'Investor discussion (1)' })).toBeInTheDocument();
    expect(screen.getByText('Investor A')).toBeInTheDocument();
    const commentText = screen.getByText(
      (_content, element) => element?.tagName === 'P' && element.textContent === 'First line\nSecond line',
    );
    expect(commentText).toBeInTheDocument();
    expect(screen.getByText('2026-08-17T10:00:00Z')).toBeInTheDocument();
  });

  test('renders an honest empty crawl state', () => {
    mockUseIdeaDetail.mockReturnValue({
      data: { ...baseIdea, comments: [] },
      isLoading: false,
      isError: false,
      error: null,
    } as ReturnType<typeof useIdeaDetail>);

    renderPage();

    expect(screen.getByRole('heading', { name: 'Investor discussion (0)' })).toBeInTheDocument();
    expect(screen.getByText('No comments were captured for this crawl')).toBeInTheDocument();
  });
});
```

The predicate targets the rendered comment paragraph so the test verifies the stored newline without depending on Testing Library's whitespace normalization.

- [ ] **Step 2: Run the detail tests and confirm they fail**

Run:

```bash
cd frontend && npm test -- --runInBand src/tests/IdeaDetailPage.test.tsx
```

Expected: FAIL because `IdeaDetail.comments` and the discussion section do not exist.

- [ ] **Step 3: Add the TypeScript comment contract**

Add this interface before `IdeaDetail` in `frontend/src/types/api.ts`:

```ts
export interface IdeaComment {
  id: string;
  author: string;
  posted_at: string;
  text: string;
}
```

Add the required response field:

```ts
export interface IdeaDetail extends Idea {
  company?: Company;
  user?: User;
  description?: Description;
  catalysts?: Catalysts;
  performance?: Performance;
  comments: IdeaComment[];
}
```

Update every `IdeaDetail` fixture in `frontend/src/tests/_useIdeas.test.ts` and `frontend/src/tests/apiService.test.ts` with `comments: []` unless the test specifically needs a populated comment.

- [ ] **Step 4: Implement the shared read-only discussion section**

In `frontend/src/pages/IdeaDetailPage.tsx`, import `Stack` from Chakra UI and destructure `comments` from `idea`:

```tsx
comments,
```

After the existing closing `</Grid>` and before the page’s final `</Box>`, render:

```tsx
<Box mt={8}>
  <Heading size="md" mb={4}>
    Investor discussion ({comments.length})
  </Heading>

  {comments.length === 0 ? (
    <Box p={4} borderWidth="1px" borderStyle="dashed" borderColor="whiteAlpha.300" borderRadius="md">
      <Text color="whiteAlpha.700">No comments were captured for this crawl</Text>
    </Box>
  ) : (
    <Stack spacing={3}>
      {comments.map((comment) => (
        <Box key={comment.id} p={4} borderWidth="1px" borderColor="whiteAlpha.200" borderRadius="md" bg="whiteAlpha.50">
          <Flex justify="space-between" align={{ base: 'flex-start', md: 'center' }} gap={3} direction={{ base: 'column', md: 'row' }}>
            {comment.author && <Text fontWeight="700" color="white">{comment.author}</Text>}
            {comment.posted_at && (
              <Text color="whiteAlpha.600" fontSize="sm">
                <time dateTime={comment.posted_at}>{comment.posted_at}</time>
              </Text>
            )}
          </Flex>
          <Text mt={3} color="whiteAlpha.800" whiteSpace="pre-wrap">{comment.text}</Text>
        </Box>
      ))}
    </Stack>
  )}
</Box>
```

Do not add an input, submit button, mutation, or separate query. The existing loading/error/not-found states remain unchanged, and `ArticleDetailPage` gains the behavior automatically because it already delegates to `IdeaDetailPage`.

- [ ] **Step 5: Run frontend detail, hook, and API tests**

Run:

```bash
cd frontend && npm test -- --runInBand src/tests/IdeaDetailPage.test.tsx src/tests/_useIdeas.test.ts src/tests/apiService.test.ts
```

Expected: all selected tests pass with no missing `comments` fixture errors.

- [ ] **Step 6: Commit the detail UI**

```bash
git add frontend/src/types/api.ts frontend/src/pages/IdeaDetailPage.tsx frontend/src/tests/IdeaDetailPage.test.tsx frontend/src/tests/_useIdeas.test.ts frontend/src/tests/apiService.test.ts
git commit -m "feat(ui): show crawled VIC comments"
```

## Task 4: Clarify Source Routes and Add Grafana Link

**Files:**
- Modify: `frontend/src/components/SourceVerificationCard.tsx`
- Modify: `frontend/src/pages/HomePage.tsx`
- Modify: `frontend/src/tests/sources.test.tsx`
- Modify: `frontend/src/tests/HomePage.test.tsx`

- [ ] **Step 1: Add failing route/link assertions**

In `frontend/src/tests/sources.test.tsx`, extend the existing successful three-source test:

```tsx
expect(screen.getByText('/holdings/dataroma')).toBeInTheDocument();
expect(screen.getByText('/holdings/hedgefollow')).toBeInTheDocument();
expect(screen.getByText('/articles')).toBeInTheDocument();

const publicLinks = screen.getAllByRole('link', { name: /View public/i });
expect(publicLinks.map((link) => link.getAttribute('href'))).toEqual([
  '/holdings/dataroma',
  '/holdings/hedgefollow',
  '/articles',
]);
```

Replace the existing `HomePage` test with assertions for both product and operations destinations:

```tsx
expect(screen.getByRole('link', { name: /verify sources/i })).toHaveAttribute('href', '/sources');
expect(screen.getByRole('link', { name: /open ingestion telemetry/i })).toHaveAttribute(
  'href',
  'http://localhost:3001/d/vic-ingestion',
);
```

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run:

```bash
cd frontend && npm test -- --runInBand src/tests/sources.test.tsx src/tests/HomePage.test.tsx
```

Expected: source route text and Grafana link assertions fail because the UI does not render them yet.

- [ ] **Step 3: Add literal local paths to source cards**

Import Chakra `Code` in `frontend/src/components/SourceVerificationCard.tsx` and render this immediately before the existing public-route CTA:

```tsx
<Text mt={4} color="whiteAlpha.600" fontSize="sm">
  Local route:{' '}
  <Code bg="blackAlpha.300" color="amber.100">
    {source.public_route}
  </Code>
</Text>
```

Leave the existing CTA as `as={RouterLink} to={source.public_route}` so displayed path and destination use the same response value. Do not hard-code a second route map in the component.

- [ ] **Step 4: Add the external Grafana link without a health dependency**

Import Chakra `Link` and add this link below the hero button stack in `frontend/src/pages/HomePage.tsx`:

```tsx
<Link
  href="http://localhost:3001/d/vic-ingestion"
  isExternal
  mt={5}
  display="inline-flex"
  alignItems="center"
  color="blue.600"
  fontWeight="700"
>
  Open ingestion telemetry
</Link>
```

Do not fetch Grafana, conditionally hide the link, or change `App`’s API health gate. The dashboard remains usable when Grafana is stopped.

- [ ] **Step 5: Run the source and home tests**

Run:

```bash
cd frontend && npm test -- --runInBand src/tests/sources.test.tsx src/tests/HomePage.test.tsx
```

Expected: PASS, including all existing source warning, loading, and navigation coverage.

- [ ] **Step 6: Commit source and operations UI**

```bash
git add frontend/src/components/SourceVerificationCard.tsx frontend/src/pages/HomePage.tsx frontend/src/tests/sources.test.tsx frontend/src/tests/HomePage.test.tsx
git commit -m "feat(ui): clarify source and telemetry links"
```

## Task 5: Add Visual Smoke Coverage and Run the Full Verification Loop

**Files:**
- Create: `frontend/e2e/comments-sources.visual.spec.ts`

- [ ] **Step 1: Add responsive visual checks for the changed public surfaces**

Create `frontend/e2e/comments-sources.visual.spec.ts`:

```ts
import { test, expect } from '@playwright/test';

const viewports = [
  { name: '375', width: 375, height: 812 },
  { name: '768', width: 768, height: 1024 },
  { name: '1280', width: 1280, height: 720 },
];

for (const viewport of viewports) {
  test(`source verification is legible at ${viewport.name}px`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto('/sources');
    await expect(page.getByRole('heading', { name: /Source verification/i })).toBeVisible();
    await expect(page.getByText('/articles')).toBeVisible();
    await expect(page.getByText('/holdings/dataroma')).toBeVisible();
    await expect(page.getByText('/holdings/hedgefollow')).toBeVisible();
    await expect(page).toHaveScreenshot(`sources-routes-${viewport.name}.png`, { fullPage: true });
  });

  test(`product dashboard exposes telemetry at ${viewport.name}px`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto('/');
    await expect(page.getByRole('heading', { name: /VIC Analytics Dashboard/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /open ingestion telemetry/i })).toHaveAttribute(
      'href',
      'http://localhost:3001/d/vic-ingestion',
    );
    await expect(page).toHaveScreenshot(`home-telemetry-${viewport.name}.png`, { fullPage: true });
  });
}
```

The detail-page unit tests cover populated and empty comments without requiring a live idea ID. The visual spec covers the source route and dashboard surfaces that are stable public routes.

- [ ] **Step 2: Run targeted frontend verification**

Run:

```bash
cd frontend && npm test -- --runInBand src/tests/IdeaDetailPage.test.tsx src/tests/sources.test.tsx src/tests/HomePage.test.tsx src/tests/apiService.test.ts src/tests/_useIdeas.test.ts
cd frontend && npm run validate-schema
cd frontend && npm run lint
cd frontend && npm run build
```

Expected: all targeted tests pass, TypeScript schema validation reports `All frontend types valid against the API schema`, lint exits cleanly, and the production build completes.

- [ ] **Step 3: Run backend, schema, and project verification**

Run:

```bash
pytest -xvs api/tests/test_ideas_api.py api/tests/test_schema_validation.py
python -m api.validate_schema
./run_tests.sh
```

Expected: focused backend tests and schema validation pass. If `./run_tests.sh` encounters a pre-existing Docker, database, or crawler-environment failure, record the exact failing command and error rather than weakening the new tests.

- [ ] **Step 4: Run responsive visual smoke checks**

With the API and frontend running at the configured local URLs, run:

```bash
cd frontend && npm run test:visual -- e2e/comments-sources.visual.spec.ts
```

Expected: screenshots pass at 375px, 768px, and 1280px, with no horizontal overflow and visible route/Grafana labels. Inspect the generated screenshots for the detail-page unit-tested states through the existing app if a crawled idea is available; do not trigger a crawl from the UI.

- [ ] **Step 5: Inspect the final scoped diff**

Run:

```bash
git diff --check
git diff -- api/models/__init__.py api/schemas/schemas.py api/routes/ideas.py api/tests/test_ideas_api.py api/validate_schema.py api/tests/test_schema_validation.py api/schema/openapi.json frontend/src/types/api.ts frontend/src/pages/IdeaDetailPage.tsx frontend/src/components/SourceVerificationCard.tsx frontend/src/pages/HomePage.tsx frontend/src/tests frontend/e2e/comments-sources.visual.spec.ts
```

Confirm the diff contains only read-only crawled-comment exposure, source-route labels, the external telemetry link, tests, generated OpenAPI output, and no comment mutation or crawl-start UI.

- [ ] **Step 6: Commit visual coverage and verified cleanup**

```bash
git add frontend/e2e/comments-sources.visual.spec.ts
git commit -m "test(ui): verify source and comment views"
```

## Plan Self-Review

- Spec coverage: comment provenance, additive API response, deterministic ownership/order, truthful empty state, both detail routes, three source routes, Grafana link, no crawl trigger, schema validation, responsive verification, and rollback boundaries each map to a task above.
- Placeholder scan: no unresolved design choice, placeholder, or deferred implementation step remains.
- Type consistency: `IdeaComment` is the frontend representation of API `CommentResponse`; `IdeaDetail.comments` is required and all listed fixtures receive the field; OpenAPI generation and both validators check the same response shape.
- Error behavior: missing rows serialize as `[]`; detail API errors retain existing behavior; Grafana is an inert external link; source warning states remain unchanged.
- Scope: no migration, crawler edit, mutation route, moderation surface, cross-source merge, or unrelated navigation redesign is included.
