import React from 'react';
import { render, screen } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import IdeaDetailPage from '../pages/IdeaDetailPage';
import ArticleDetailPage from '../pages/ArticleDetailPage';
import { useIdeaDetail } from '../hooks/useIdeas';
import theme from '../theme';
import { IdeaDetail } from '../types/api';

jest.mock('../hooks/useIdeas', () => ({
  useIdeaDetail: jest.fn(),
}));

const mockUseIdeaDetail = useIdeaDetail as jest.MockedFunction<typeof useIdeaDetail>;

const baseIdeaDetail: IdeaDetail = {
  id: 'idea-1',
  link: 'https://example.com/idea-1',
  company_id: 'company-1',
  user_id: 'user-1',
  date: '2026-08-17T00:00:00Z',
  is_short: false,
  is_contest_winner: false,
  company: {
    ticker: 'VIC',
    company_name: 'Value Investors Club',
  },
  user: {
    username: 'Author',
    user_link: 'https://example.com/users/author',
  },
  comments: [],
};

const renderPage = (
  idea: IdeaDetail,
  {
    entry = '/ideas/idea-1',
    routePath = '/ideas/:id',
    basePath = '/ideas',
    backLabel = 'Back to Ideas',
    page,
  }: {
    entry?: string;
    routePath?: string;
    basePath?: string;
    backLabel?: string;
    page?: React.ReactElement;
  } = {},
) => {
  mockUseIdeaDetail.mockReturnValue({
    data: idea,
    isLoading: false,
    isError: false,
    error: null,
  } as ReturnType<typeof useIdeaDetail>);

  const pageElement = page ?? <IdeaDetailPage basePath={basePath} backLabel={backLabel} />;

  return render(
    <ChakraProvider theme={theme}>
      <MemoryRouter
        initialEntries={[entry]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route
            path={routePath}
            element={pageElement}
          />
        </Routes>
      </MemoryRouter>
    </ChakraProvider>,
  );
};

describe('IdeaDetailPage investor discussion', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders crawled comments with author, stored timestamp, and preserved line breaks', () => {
    renderPage({
      ...baseIdeaDetail,
      comments: [
        {
          id: 'comment-1',
          author: 'Investor A',
          posted_at: '2026-08-17T10:00:00Z',
          text: 'First line\nSecond line',
        },
      ],
    });

    expect(mockUseIdeaDetail).toHaveBeenCalledWith('idea-1');
    expect(screen.getByRole('heading', { name: 'Investor discussion (1)' })).toBeInTheDocument();
    expect(screen.getByText('Investor A')).toBeInTheDocument();
    expect(screen.getByText('2026-08-17T10:00:00Z')).toBeInTheDocument();
    expect(
      screen.getByText(
        (_, element) =>
          element?.tagName.toLowerCase() === 'p' &&
          element.textContent === 'First line\nSecond line',
      ),
    ).toBeInTheDocument();
  });

  test('renders crawled comments through the article alias configuration', () => {
    renderPage(
      {
        ...baseIdeaDetail,
        comments: [
          {
            id: 'comment-1',
            author: 'Investor A',
            posted_at: '2026-08-17T10:00:00Z',
            text: 'First line\nSecond line',
          },
        ],
      },
      {
        entry: '/articles/idea-1',
        routePath: '/articles/:id',
        page: <ArticleDetailPage />,
      },
    );

    expect(mockUseIdeaDetail).toHaveBeenCalledWith('idea-1');
    expect(screen.getByRole('heading', { name: 'Investor discussion (1)' })).toBeInTheDocument();
    expect(screen.getByText('Investor A')).toBeInTheDocument();
    expect(
      screen.getByText(
        (_, element) =>
          element?.tagName.toLowerCase() === 'p' &&
          element.textContent === 'First line\nSecond line',
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Back to Articles' })).toHaveAttribute('href', '/articles');
  });

  test('wraps long mobile comment tokens while preserving newlines', () => {
    const longToken = 'x'.repeat(160);
    const text = `First line\n${longToken}\nSecond line`;
    const originalWidth = window.innerWidth;
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 375 });

    try {
      renderPage({
        ...baseIdeaDetail,
        comments: [
          {
            id: 'comment-1',
            author: 'Investor A',
            posted_at: '2026-08-17T10:00:00Z',
            text,
          },
        ],
      });

      const paragraph = screen.getByText(
        (_, element) =>
          element?.tagName.toLowerCase() === 'p' && element.textContent === text,
      );

      expect(paragraph).toHaveStyle({ overflowWrap: 'anywhere' });
      expect(paragraph.textContent).toBe(text);
    } finally {
      Object.defineProperty(window, 'innerWidth', { configurable: true, value: originalWidth });
    }
  });

  test('renders the empty crawled comments state', () => {
    renderPage(baseIdeaDetail);

    expect(screen.getByRole('heading', { name: 'Investor discussion (0)' })).toBeInTheDocument();
    expect(screen.getByText('No comments were captured for this crawl')).toBeInTheDocument();
  });
});
