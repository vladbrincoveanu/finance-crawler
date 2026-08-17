import React from 'react';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { ChakraProvider } from '@chakra-ui/react';
import { QueryClient, QueryClientProvider } from 'react-query';
import IdeasPage from '../pages/IdeasPage';
import { useIdeas } from '../hooks/useIdeas';
import { companiesApi, usersApi } from '../api/apiService';
import theme from '../theme';

jest.mock('../hooks/useIdeas', () => ({
  useIdeas: jest.fn(),
}));

jest.mock('../api/apiService', () => ({
  companiesApi: {
    getCompanies: jest.fn(),
  },
  usersApi: {
    getUsers: jest.fn(),
  },
}));

jest.mock('../components/IdeaCard', () => ({
  __esModule: true,
  default: ({ idea }: { idea: { company_id: string } }) => (
    <div data-testid="idea-card">{idea.company_id}</div>
  ),
}));

const mockUseIdeas = useIdeas as jest.MockedFunction<typeof useIdeas>;
const mockCompaniesApi = companiesApi as jest.Mocked<typeof companiesApi>;
const mockUsersApi = usersApi as jest.Mocked<typeof usersApi>;

const mockIdeas = [
  {
    id: 'idea-1',
    link: '/ideas/idea-1',
    company_id: 'AAPL',
    user_id: '/users/tester',
    date: '2026-08-17T00:00:00Z',
    is_short: false,
    is_contest_winner: false,
  },
];

const queryResult = {
  data: mockIdeas,
  isLoading: false,
  isError: false,
  error: null,
};

const renderPage = (path = '/ideas') => {
  window.history.pushState({}, '', path);
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        cacheTime: 0,
      },
    },
  });

  return render(
    <ChakraProvider theme={theme}>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <IdeasPage />
        </BrowserRouter>
      </QueryClientProvider>
    </ChakraProvider>,
  );
};

describe('IdeasPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseIdeas.mockReturnValue(queryResult as ReturnType<typeof useIdeas>);
    mockCompaniesApi.getCompanies.mockResolvedValue([]);
    mockUsersApi.getUsers.mockResolvedValue([]);
  });

  afterEach(() => {
    cleanup();
    window.history.pushState({}, '', '/');
  });

  test('keeps filter changes in the drawer until Apply filters', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole('button', { name: /open filters/i }));
    await user.selectOptions(screen.getByLabelText(/position/i), 'short');

    expect(mockUseIdeas.mock.calls.some(([params]) => params?.is_short === true)).toBe(false);

    await user.click(screen.getByRole('button', { name: /apply filters/i }));

    await waitFor(() => expect(mockUseIdeas).toHaveBeenLastCalledWith(
      expect.objectContaining({ is_short: true, skip: 0 }),
    ));
  });

  test('closing the drawer discards draft changes', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole('button', { name: /open filters/i }));
    await user.selectOptions(screen.getByLabelText(/position/i), 'short');
    await user.click(screen.getByRole('button', { name: /close/i }));

    expect(mockUseIdeas.mock.calls.some(([params]) => params?.is_short === true)).toBe(false);
    expect(window.location.search).toBe('');
  });

  test('selecting a company suggestion applies the exact ticker filter', async () => {
    const user = userEvent.setup();
    mockCompaniesApi.getCompanies.mockResolvedValue([
      { ticker: 'AAPL', company_name: 'Apple Inc.' },
    ]);
    renderPage();

    await user.type(screen.getByTestId('company-search'), 'Apple');
    await user.click(await screen.findByTestId('company-option'));

    await waitFor(() => expect(mockUseIdeas).toHaveBeenLastCalledWith(
      expect.objectContaining({ company_id: 'AAPL', skip: 0 }),
    ));
    expect(window.location.search).toContain('company_id=AAPL');
  });

  test('reset clears applied drawer filters and active chips', async () => {
    const user = userEvent.setup();
    renderPage('/ideas?is_short=true');

    expect(screen.getByText('Short ideas')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /open filters/i }));
    await user.click(screen.getByRole('button', { name: /^reset$/i }));

    await waitFor(() => expect(screen.queryByText('Short ideas')).not.toBeInTheDocument());
    expect(window.location.search).toBe('');
  });

  test('sort control maps performance ordering to API filters', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.selectOptions(screen.getByLabelText(/sort ideas/i), 'performance-desc');

    await waitFor(() => expect(mockUseIdeas).toHaveBeenLastCalledWith(
      expect.objectContaining({
        sort_by: 'performance',
        sort_order: 'desc',
        performance_period: 'one_year_perf',
      }),
    ));
  });

  test('load more advances by one page', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByTestId('load-more-button'));

    await waitFor(() => expect(mockUseIdeas).toHaveBeenLastCalledWith(
      expect.objectContaining({ skip: 20, limit: 20 }),
    ));
  });
});
