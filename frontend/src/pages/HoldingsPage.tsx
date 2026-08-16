import React from 'react';
import {
  Box,
  Heading,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Spinner,
  Alert,
  AlertIcon,
} from '@chakra-ui/react';
import { useHoldings } from '../hooks/useHoldings';

const HoldingsPage: React.FC = () => {
  const { data: holdings, isLoading, isError, error } = useHoldings({ skip: 0, limit: 100 });

  return (
    <Box p={5}>
      <Heading mb={5}>Holdings</Heading>

      {isLoading && <Spinner data-testid="holdings-loading" />}

      {isError && (
        <Alert status="error" data-testid="holdings-error">
          <AlertIcon />
          {error instanceof Error ? error.message : 'Failed to load holdings'}
        </Alert>
      )}

      {!isLoading && !isError && (
        <Table data-testid="holdings-table">
          <Thead>
            <Tr>
              <Th>Investor</Th>
              <Th>Ticker</Th>
              <Th>Company</Th>
              <Th>Quarter</Th>
              <Th isNumeric>Shares</Th>
              <Th isNumeric>Value (USD)</Th>
              <Th isNumeric>% Portfolio</Th>
              <Th>Activity</Th>
            </Tr>
          </Thead>
          <Tbody>
            {(holdings ?? []).map((h, i) => (
              <Tr key={`${h.investor_name}-${h.ticker}-${h.quarter_date}-${i}`}>
                <Td>{h.investor_name}</Td>
                <Td>{h.ticker}</Td>
                <Td>{h.company_name}</Td>
                <Td>{h.quarter_date}</Td>
                <Td isNumeric>{h.shares.toLocaleString()}</Td>
                <Td isNumeric>{h.value_usd.toLocaleString()}</Td>
                <Td isNumeric>{h.pct_portfolio}</Td>
                <Td>{h.activity}</Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      )}
    </Box>
  );
};

export default HoldingsPage;
