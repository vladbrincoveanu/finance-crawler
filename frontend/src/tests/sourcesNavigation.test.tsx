import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChakraProvider } from '@chakra-ui/react';
import { MemoryRouter } from 'react-router-dom';
import App from '../App';
import Layout from '../components/Layout';

jest.mock('../api/apiService', () => ({
  healthApi: {
    check: jest.fn().mockResolvedValue({ status: 'ok' }),
  },
}));

jest.mock('../pages/SourcesPage', () => ({
  __esModule: true,
  default: () => <h1>Source verification</h1>,
}));

beforeEach(() => {
  window.scrollTo = jest.fn() as typeof window.scrollTo;
});

describe('source verification route and navigation', () => {
  test('routes /sources to the source verification page', async () => {
    render(
      <ChakraProvider>
        <MemoryRouter initialEntries={['/sources']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <App />
        </MemoryRouter>
      </ChakraProvider>,
    );

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /source verification/i })).toBeInTheDocument();
    });
  });

  test('includes the source verification route in the shared navigation', () => {
    render(
      <ChakraProvider>
        <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Layout />
        </MemoryRouter>
      </ChakraProvider>,
    );

    const sourceLinks = screen.getAllByRole('link', { name: /^sources$/i, hidden: true });
    expect(sourceLinks.length).toBeGreaterThan(0);
    expect(sourceLinks.every((link) => link.getAttribute('href') === '/sources')).toBe(true);
  });

  test('exposes mobile navigation state and closes after selecting Sources', async () => {
    const user = userEvent.setup();

    render(
      <ChakraProvider>
        <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Layout />
        </MemoryRouter>
      </ChakraProvider>,
    );

    const toggle = screen.getByRole('button', { name: /toggle navigation/i });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(toggle).toHaveAttribute('aria-controls', 'mobile-navigation');

    await user.click(toggle);

    const mobileNavigation = document.getElementById('mobile-navigation');
    expect(mobileNavigation).not.toBeNull();
    expect(mobileNavigation).toHaveAttribute('role', 'navigation');
    expect(mobileNavigation).toHaveAttribute('aria-label', 'Mobile navigation');
    expect(mobileNavigation).toHaveAttribute('aria-hidden', 'false');
    expect(toggle).toHaveAttribute('aria-expanded', 'true');

    await user.click(within(mobileNavigation as HTMLElement).getByRole('link', { name: /^sources$/i }));

    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(mobileNavigation).toHaveAttribute('aria-hidden', 'true');
  });
});
