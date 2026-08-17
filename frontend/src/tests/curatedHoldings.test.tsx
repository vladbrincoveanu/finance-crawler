import { render, screen } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import { MemoryRouter } from 'react-router-dom';
import CuratedHoldingsTable from '../components/CuratedHoldingsTable';
import SourceHoldingsPage from '../pages/SourceHoldingsPage';
import { CuratedHolding } from '../types/api';

jest.mock('../hooks/useCuratedHoldings', () => ({
  useCuratedHoldings: () => ({
    data: [],
    isLoading: false,
    isError: false,
    error: null,
  }),
}));

const holding: CuratedHolding = {
  source: 'dataroma',
  investor_id: 'investor-1',
  investor_name: 'Berkshire Hathaway',
  portfolio_manager_name: 'Warren Buffett',
  company_id: 'company-1',
  company_name: 'Berkshire Hathaway',
  security_id: 'security-1',
  ticker: 'BRK.B',
  period: '2026-06-30',
  shares: 120,
  value_usd: 1000,
  pct_portfolio: 2.5,
  source_activity: 'hold',
  completeness: 'complete',
  source_url: 'https://dataroma.test/brk',
};

function renderWithChakra(ui: React.ReactElement) {
  return render(
    <ChakraProvider>
      <MemoryRouter>{ui}</MemoryRouter>
    </ChakraProvider>,
  );
}

describe('CuratedHoldingsTable', () => {
  test('renders provenance, partial coverage, and source link', () => {
    renderWithChakra(
      <CuratedHoldingsTable
        holdings={[holding, { ...holding, source: 'hedgefollow', completeness: 'partial', shares: null }]}
      />,
    );

    expect(screen.getByText('dataroma')).toBeInTheDocument();
    expect(screen.getByText('hedgefollow')).toBeInTheDocument();
    expect(screen.getByText('Unknown coverage')).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: /View source/i })).toHaveLength(2);
  });

  test('renders a useful empty state', () => {
    renderWithChakra(<CuratedHoldingsTable holdings={[]} />);

    expect(screen.getByText('No curated holdings yet')).toBeInTheDocument();
    expect(screen.getByText(/unresolved or quarantined/i)).toBeInTheDocument();
  });
});

describe('SourceHoldingsPage', () => {
  test('shows the source-specific heading', () => {
    renderWithChakra(<SourceHoldingsPage source="dataroma" />);

    expect(screen.getByRole('heading', { name: /Dataroma holdings/i })).toBeInTheDocument();
  });
});
