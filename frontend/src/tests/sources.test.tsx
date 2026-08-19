import React from 'react';
import { render, screen } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import { MemoryRouter } from 'react-router-dom';
import SourcesPage from '../pages/SourcesPage';
import { useCrawlStatus } from '../hooks/useCrawlStatus';
import { CrawlRun, CrawlSourceStatus } from '../types/api';

jest.mock('../hooks/useCrawlStatus', () => ({
  useCrawlStatus: jest.fn(),
}));

const mockUseCrawlStatus = useCrawlStatus as jest.MockedFunction<typeof useCrawlStatus>;

const renderPage = () => render(
  <ChakraProvider>
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <SourcesPage />
    </MemoryRouter>
  </ChakraProvider>,
);

const makeRun = (overrides: Partial<CrawlRun> = {}): CrawlRun => ({
  id: 'run-dataroma',
  source: 'dataroma',
  target: 'holdings',
  status: 'complete',
  parser_version: 'dataroma-v1',
  started_at: '2026-08-17T10:00:00Z',
  finished_at: '2026-08-17T10:01:00Z',
  rows_seen: 4,
  rows_accepted: 3,
  rows_rejected: 1,
  rows_duplicate: 2,
  error_message: null,
  ...overrides,
});

const noRun = (): CrawlRun => ({
  id: null,
  source: null,
  target: null,
  status: null,
  parser_version: null,
  started_at: null,
  finished_at: null,
  rows_seen: 0,
  rows_accepted: 0,
  rows_rejected: 0,
  rows_duplicate: 0,
  error_message: null,
});

const makeSource = (
  overrides: Partial<CrawlSourceStatus> = {},
): CrawlSourceStatus => ({
  source: 'dataroma',
  label: 'Dataroma',
  target: 'holdings',
  public_route: '/holdings/dataroma',
  latest_run: makeRun(),
  counts: {
    parser_output: 4,
    staged: 3,
    pending_identity: 2,
    curated: 1,
    public: 0,
  },
  sample: {
    kind: 'holding',
    investor_name: 'Berkshire Hathaway',
    ticker: 'AAPL',
    company_name: 'Apple Inc.',
    period: '2026-06-30',
    idea_date: null,
    shares: 1234,
    value_usd: 456789,
    pct_portfolio: 5.6,
    activity: 'Added',
    identity_status: 'pending',
    source_url: 'https://dataroma.test/holding/aapl',
    link: null,
  },
  ...overrides,
});

const successfulResult = (data: CrawlSourceStatus[]) => ({
  data,
  isLoading: false,
  isError: false,
  error: null,
} as ReturnType<typeof useCrawlStatus>);

describe('SourcesPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders all source cards with source boundaries, metadata, samples, and public links', () => {
    mockUseCrawlStatus.mockReturnValue(successfulResult([
      makeSource(),
      makeSource({
        source: 'hedgefollow',
        label: 'HedgeFollow',
        public_route: '/holdings/hedgefollow',
        latest_run: {
          ...makeRun(),
          id: 'run-hedgefollow',
          source: 'hedgefollow',
          parser_version: 'hedgefollow-v1',
        },
        sample: {
          ...makeSource().sample!,
          ticker: 'BRK-B',
          company_name: 'Berkshire Hathaway Inc.',
          source_url: 'https://hedgefollow.test/holding/brk-b',
        },
      }),
      makeSource({
        source: 'valueinvestorsclub',
        label: 'ValueInvestorsClub.com',
        target: 'ideas',
        public_route: '/articles',
        counts: {
          parser_output: 4,
          staged: 0,
          pending_identity: 0,
          curated: 0,
          public: 7,
        },
        latest_run: {
          ...makeRun(),
          id: 'run-vic',
          source: 'valueinvestorsclub',
          target: 'ideas',
          parser_version: 'idea-pipeline-v1',
        },
        sample: {
          kind: 'idea',
          investor_name: null,
          ticker: 'ACME',
          company_name: 'Acme Corp',
          period: null,
          idea_date: '2026-08-17T12:30:00Z',
          shares: null,
          value_usd: null,
          pct_portfolio: null,
          activity: null,
          identity_status: null,
          source_url: 'https://valueinvestorsclub.test/idea/acme',
          link: 'https://valueinvestorsclub.test/idea/acme',
        },
      }),
    ]));

    renderPage();

    expect(screen.getByRole('heading', { name: 'Dataroma' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'HedgeFollow' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'ValueInvestorsClub.com' })).toBeInTheDocument();
    expect(screen.getAllByText('Parser output')).toHaveLength(3);
    expect(screen.getAllByText('Staged for review')).toHaveLength(2);
    expect(screen.getAllByText('Pending identity')).toHaveLength(2);
    expect(screen.getAllByText('Public curated')).toHaveLength(2);
    expect(screen.getByText('Public articles')).toBeInTheDocument();
    expect(screen.getAllByText('Berkshire Hathaway')).toHaveLength(2);
    expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
    expect(screen.getByText('ACME')).toBeInTheDocument();
    expect(screen.getAllByText('2026-06-30')).toHaveLength(2);
    expect(screen.getByText('Published 2026-08-17')).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: /open original source record/i })).toHaveLength(3);
    expect(screen.getByText('/holdings/dataroma')).toBeInTheDocument();
    expect(screen.getByText('/holdings/hedgefollow')).toBeInTheDocument();
    expect(screen.getByText('/articles')).toBeInTheDocument();

    const publicLinks = screen.getAllByRole('link', { name: /View public/i });
    expect(publicLinks.map((link) => link.getAttribute('href'))).toEqual([
      '/holdings/dataroma',
      '/holdings/hedgefollow',
      '/articles',
    ]);
  });

  test('renders no-run state without treating zero as success', () => {
    mockUseCrawlStatus.mockReturnValue(successfulResult([
      makeSource({
        latest_run: noRun(),
        counts: {
          parser_output: 0,
          staged: 0,
          pending_identity: 0,
          curated: 0,
          public: 0,
        },
        sample: null,
      }),
      makeSource({ source: 'hedgefollow', label: 'HedgeFollow', sample: null }),
      makeSource({ source: 'valueinvestorsclub', label: 'ValueInvestorsClub.com', target: 'ideas', sample: null }),
    ]));

    renderPage();

    expect(screen.getAllByText('No run recorded')).toHaveLength(2);
    expect(screen.getByText('Awaiting operator-run crawl')).toBeInTheDocument();
    expect(screen.queryByText(/^success$/i)).not.toBeInTheDocument();
  });

  test('marks a zero-row complete response as an empty-run warning', () => {
    mockUseCrawlStatus.mockReturnValue(successfulResult([
      makeSource({
        latest_run: makeRun({ rows_seen: 0, rows_accepted: 0, status: 'complete' }),
        counts: {
          parser_output: 0,
          staged: 0,
          pending_identity: 0,
          curated: 0,
          public: 0,
        },
        sample: null,
      }),
    ]));

    renderPage();

    expect(screen.getAllByText('Empty run warning')).toHaveLength(2);
    expect(screen.getByRole('alert')).toHaveTextContent('Run produced no parser output');
    expect(screen.queryByText(/^complete$/i)).not.toBeInTheDocument();
  });

  test('renders an explicit message when the latest run has no accepted sample', () => {
    mockUseCrawlStatus.mockReturnValue(successfulResult([
      makeSource({ sample: null }),
      makeSource({ source: 'hedgefollow', label: 'HedgeFollow', sample: null }),
      makeSource({ source: 'valueinvestorsclub', label: 'ValueInvestorsClub.com', target: 'ideas', sample: null }),
    ]));

    renderPage();

    expect(screen.getAllByText('No accepted sample in latest run')).toHaveLength(3);
  });

  test('renders partial and failed run errors as warnings', () => {
    mockUseCrawlStatus.mockReturnValue(successfulResult([
      makeSource({
        latest_run: {
          ...makeRun(),
          status: 'partial',
          error_message: 'One record was rejected',
        },
      }),
      makeSource({
        source: 'hedgefollow',
        label: 'HedgeFollow',
        latest_run: {
          ...makeRun(),
          source: 'hedgefollow',
          status: 'failed',
          error_message: 'HTTP 403 from source',
        },
      }),
      makeSource({ source: 'valueinvestorsclub', label: 'ValueInvestorsClub.com', target: 'ideas' }),
    ]));

    renderPage();

    const warnings = screen.getAllByRole('alert');
    expect(warnings).toHaveLength(2);
    expect(warnings[0]).toHaveTextContent('One record was rejected');
    expect(warnings[1]).toHaveTextContent('HTTP 403 from source');
    expect(warnings.every((warning) => warning.getAttribute('data-status') !== 'error')).toBe(true);
  });

  test('renders running and unknown crawl states as human-readable warnings', () => {
    mockUseCrawlStatus.mockReturnValue(successfulResult([
      makeSource({
        latest_run: makeRun({ status: 'running', finished_at: null }),
      }),
      makeSource({
        source: 'hedgefollow',
        label: 'HedgeFollow',
        latest_run: makeRun({
          source: 'hedgefollow',
          status: 'unknown' as unknown as CrawlRun['status'],
        }),
      }),
    ]));

    renderPage();

    expect(screen.getAllByText('Crawl in progress')).toHaveLength(2);
    expect(screen.getAllByText('Status unavailable')).toHaveLength(2);
    const alerts = screen.getAllByRole('alert');
    expect(alerts).toEqual(expect.arrayContaining([
      expect.objectContaining({ textContent: expect.stringMatching(/still running/i) }),
    ]));
    expect(alerts).toHaveLength(2);
    expect(alerts.every((alert) => alert.getAttribute('data-status') === 'warning')).toBe(true);
    expect(screen.queryByText(/healthy crawl/i)).not.toBeInTheDocument();
  });

  test('exposes loading state through busy and live semantics', () => {
    mockUseCrawlStatus.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
    } as ReturnType<typeof useCrawlStatus>);

    renderPage();

    expect(screen.getByTestId('sources-page')).toHaveAttribute('aria-busy', 'true');
    expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'polite');
    expect(screen.getByText('Loading source verification')).toBeInTheDocument();
  });

  test('renders endpoint failures as a page alert', () => {
    mockUseCrawlStatus.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error('status endpoint unavailable'),
    } as ReturnType<typeof useCrawlStatus>);

    renderPage();

    expect(screen.getByRole('alert')).toHaveTextContent('Unable to load source verification');
    expect(screen.getByRole('alert')).toHaveTextContent('status endpoint unavailable');
  });
});
