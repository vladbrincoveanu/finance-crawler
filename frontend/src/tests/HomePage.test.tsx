import React from 'react';
import { render, screen } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import { MemoryRouter } from 'react-router-dom';
import HomePage from '../pages/HomePage';

describe('HomePage', () => {
  test('links visitors to source verification', () => {
    render(
      <ChakraProvider>
        <MemoryRouter>
          <HomePage />
        </MemoryRouter>
      </ChakraProvider>,
    );

    expect(screen.getByRole('link', { name: /verify sources/i })).toHaveAttribute('href', '/sources');
    expect(screen.getByRole('link', { name: /open ingestion telemetry/i })).toHaveAttribute(
      'href',
      'http://localhost:3001/d/vic-ingestion',
    );
  });
});
