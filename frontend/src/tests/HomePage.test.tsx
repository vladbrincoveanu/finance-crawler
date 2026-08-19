import React from 'react';
import { render, screen } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import { MemoryRouter } from 'react-router-dom';
import HomePage from '../pages/HomePage';
import { useCrawlStatus } from '../hooks/useCrawlStatus';
import { CrawlSourceStatus } from '../types/api';

jest.mock('../hooks/useCrawlStatus', () => ({
  useCrawlStatus: jest.fn(),
}));

const mockedUseCrawlStatus = useCrawlStatus as jest.Mock;

const crawlSources: CrawlSourceStatus[] = [
  {
    source: 'dataroma',
    label: 'Dataroma',
    target: 'holdings',
    public_route: '/holdings/dataroma',
    latest_run: {
      id: 'dataroma-run',
      source: 'dataroma',
      target: 'holdings',
      status: 'partial',
      parser_version: 'dataroma-v1',
      started_at: '2026-08-19T08:00:00Z',
      finished_at: '2026-08-19T08:01:00Z',
      rows_seen: 246,
      rows_accepted: 243,
      rows_rejected: 0,
      rows_duplicate: 3,
      error_message: 'bounded crawl complete',
    },
    counts: {
      parser_output: 246,
      staged: 243,
      pending_identity: 243,
      curated: 0,
      public: 0,
    },
    sample: {
      kind: 'holding',
      investor_name: 'Miller Value Partners',
      ticker: 'BRK.B',
      company_name: 'Berkshire Hathaway CL B',
      period: '2026-Q2',
      shares: 100,
      value_usd: 123456,
      pct_portfolio: 2.5,
      activity: 'Buy',
      identity_status: 'pending',
      source_url: 'https://www.dataroma.com/m/hist/hist.php?f=MUHL&s=BRK.B',
      link: null,
    },
  },
  {
    source: 'hedgefollow',
    label: 'HedgeFollow',
    target: 'holdings',
    public_route: '/holdings/hedgefollow',
    latest_run: {
      id: 'hedgefollow-run',
      source: 'hedgefollow',
      target: 'holdings',
      status: 'partial',
      parser_version: 'hedgefollow-v1',
      started_at: '2026-08-19T08:00:00Z',
      finished_at: '2026-08-19T08:01:00Z',
      rows_seen: 25,
      rows_accepted: 25,
      rows_rejected: 0,
      rows_duplicate: 0,
      error_message: 'bounded crawl complete',
    },
    counts: {
      parser_output: 25,
      staged: 25,
      pending_identity: 25,
      curated: 0,
      public: 0,
    },
    sample: {
      kind: 'holding',
      investor_name: 'Baupost Group Management',
      ticker: 'HLF',
      company_name: 'Herbalife Ltd',
      period: '2026-Q2',
      shares: 200,
      value_usd: 234567,
      pct_portfolio: 1.5,
      activity: 'Hold',
      identity_status: 'pending',
      source_url: 'https://hedgefollow.com/funds/Baupost+Group+Ma',
      link: null,
    },
  },
  {
    source: 'valueinvestorsclub',
    label: 'ValueInvestorsClub.com',
    target: 'ideas',
    public_route: '/articles',
    latest_run: {
      id: 'vic-run',
      source: 'valueinvestorsclub',
      target: 'ideas',
      status: 'complete',
      parser_version: 'vic-v1',
      started_at: '2026-08-19T08:00:00Z',
      finished_at: '2026-08-19T08:01:00Z',
      rows_seen: 1,
      rows_accepted: 1,
      rows_rejected: 0,
      rows_duplicate: 0,
      error_message: null,
    },
    counts: {
      parser_output: 1,
      staged: 0,
      pending_identity: 0,
      curated: 0,
      public: 1,
    },
    sample: {
      kind: 'idea',
      ticker: 'BCC',
      company_name: 'Boise Cascade',
      idea_date: '2026-08-19',
      source_url: 'https://www.valueinvestorsclub.com/idea/Boise_Cascade/6809811440',
      link: 'https://www.valueinvestorsclub.com/idea/Boise_Cascade/6809811440',
    },
  },
];

describe('HomePage', () => {
  beforeEach(() => {
    mockedUseCrawlStatus.mockReset();
  });

  test('links visitors to source verification', () => {
    mockedUseCrawlStatus.mockReturnValue({ isLoading: false, isError: false, data: [] });

    render(
      <ChakraProvider>
        <MemoryRouter>
          <HomePage />
        </MemoryRouter>
      </ChakraProvider>,
    );

    expect(screen.getByRole('link', { name: /verify sources/i })).toHaveAttribute('href', '/sources');
  });

  test('shows the latest sample from all three crawled sources', () => {
    mockedUseCrawlStatus.mockReturnValue({ isLoading: false, isError: false, data: crawlSources });

    render(
      <ChakraProvider>
        <MemoryRouter>
          <HomePage />
        </MemoryRouter>
      </ChakraProvider>,
    );

    expect(screen.getByRole('heading', { name: /live crawl evidence/i })).toBeInTheDocument();
    expect(screen.getByText('BRK.B')).toBeInTheDocument();
    expect(screen.getByText('HLF')).toBeInTheDocument();
    expect(screen.getByText('BCC')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /view full source verification/i })).toHaveAttribute('href', '/sources');
  });

  test('keeps the dashboard usable while source status is loading', () => {
    mockedUseCrawlStatus.mockReturnValue({ isLoading: true, isError: false, data: undefined });

    render(
      <ChakraProvider>
        <MemoryRouter>
          <HomePage />
        </MemoryRouter>
      </ChakraProvider>,
    );

    expect(screen.getByText(/loading live crawl evidence/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /vic analytics dashboard/i })).toBeInTheDocument();
  });

  test('reports source status errors without hiding the dashboard', () => {
    mockedUseCrawlStatus.mockReturnValue({
      isLoading: false,
      isError: true,
      error: new Error('status endpoint unavailable'),
      data: undefined,
    });

    render(
      <ChakraProvider>
        <MemoryRouter>
          <HomePage />
        </MemoryRouter>
      </ChakraProvider>,
    );

    expect(screen.getByText(/unable to load live crawl evidence/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /vic analytics dashboard/i })).toBeInTheDocument();
  });
});
