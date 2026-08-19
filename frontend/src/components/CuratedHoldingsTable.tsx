import React from 'react';
import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Link,
  Spinner,
  Table,
  TableContainer,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tr,
} from '@chakra-ui/react';
import { ExternalLinkIcon } from '@chakra-ui/icons';
import { CuratedHolding } from '../types/api';

interface CuratedHoldingsTableProps {
  holdings: CuratedHolding[];
  isLoading?: boolean;
  isError?: boolean;
  error?: unknown;
}

const sourceColor: Record<string, string> = {
  dataroma: 'amber',
  hedgefollow: 'purple',
};

const formatNumber = (value: number | null, options?: Intl.NumberFormatOptions) =>
  value === null ? '—' : new Intl.NumberFormat('en-US', options).format(value);

const CuratedHoldingsTable: React.FC<CuratedHoldingsTableProps> = ({
  holdings,
  isLoading = false,
  isError = false,
  error,
}) => {
  if (isLoading) {
    return (
      <Box minH="260px" display="grid" placeItems="center" aria-label="Loading curated holdings">
        <Spinner color="amber.300" size="lg" />
      </Box>
    );
  }

  if (isError) {
    return (
      <Alert status="error" borderRadius="16px" bg="red.900" color="red.100">
        <AlertIcon />
        {error instanceof Error ? error.message : 'Unable to load curated holdings.'}
      </Alert>
    );
  }

  if (!holdings.length) {
    return (
      <Box
        border="1px solid"
        borderColor="whiteAlpha.200"
        bg="whiteAlpha.50"
        borderRadius="20px"
        px={{ base: 6, md: 10 }}
        py={{ base: 12, md: 16 }}
        textAlign="center"
      >
        <Text color="amber.200" fontSize="lg" fontWeight="700">
          No curated holdings yet
        </Text>
        <Text mt={2} color="whiteAlpha.700" maxW="480px" mx="auto">
          Source observations appear here only after identity review. Unresolved or quarantined
          rows stay out of the public table.
        </Text>
      </Box>
    );
  }

  return (
    <TableContainer
      border="1px solid"
      borderColor="whiteAlpha.200"
      borderRadius="20px"
      bg="whiteAlpha.50"
      overflowX="auto"
      sx={{ '&::-webkit-scrollbar': { height: '8px' }, '&::-webkit-scrollbar-thumb': { background: 'rgba(245,158,11,.45)', borderRadius: '8px' } }}
    >
      <Table variant="unstyled" size="sm" minW="1120px">
        <Thead>
          <Tr borderBottom="1px solid" borderColor="whiteAlpha.200">
            {['Source', 'Investor', 'Manager', 'Company', 'Security', 'Period', 'Activity', 'Shares', 'Value', 'Portfolio %', 'Coverage', ''].map((label) => (
              <Th key={label} color="whiteAlpha.600" fontSize="10px" letterSpacing="0.14em" textTransform="uppercase" py={4} px={4}>
                {label}
              </Th>
            ))}
          </Tr>
        </Thead>
        <Tbody>
          {holdings.map((holding) => {
            const coverage = holding.completeness === 'complete' ? 'Complete' : 'Unknown coverage';
            return (
              <Tr key={`${holding.source}-${holding.security_id}-${holding.period}`} _hover={{ bg: 'whiteAlpha.100' }} transition="background 180ms ease">
                <Td px={4} py={4}>
                  <Badge colorScheme={sourceColor[holding.source] ?? 'gray'} variant="subtle" textTransform="lowercase" borderRadius="full" px={2.5}>
                    {holding.source}
                  </Badge>
                </Td>
                <Td px={4} py={4} color="white" fontWeight="600">{holding.investor_name}</Td>
                <Td px={4} py={4} color="whiteAlpha.700">{holding.portfolio_manager_name ?? '—'}</Td>
                <Td px={4} py={4} color="whiteAlpha.800">{holding.company_name}</Td>
                <Td px={4} py={4}>
                  <Text color="amber.200" fontWeight="700">{holding.ticker}</Text>
                </Td>
                <Td px={4} py={4} color="whiteAlpha.700" whiteSpace="nowrap">{holding.period}</Td>
                <Td px={4} py={4} color={holding.source_activity ? 'whiteAlpha.800' : 'whiteAlpha.600'}>{holding.source_activity ?? 'Unknown'}</Td>
                <Td px={4} py={4} isNumeric color="whiteAlpha.800">{formatNumber(holding.shares)}</Td>
                <Td px={4} py={4} isNumeric color="whiteAlpha.800" whiteSpace="nowrap">{formatNumber(holding.value_usd, { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })}</Td>
                <Td px={4} py={4} isNumeric color="whiteAlpha.800">{formatNumber(holding.pct_portfolio, { maximumFractionDigits: 2 })}{holding.pct_portfolio === null ? '' : '%'}</Td>
                <Td px={4} py={4}>
                  <Text fontSize="xs" color={holding.completeness === 'complete' ? 'green.300' : 'orange.300'} whiteSpace="nowrap">{coverage}</Text>
                </Td>
                <Td px={4} py={4} textAlign="right">
                  <Link href={holding.source_url} isExternal color="amber.200" fontSize="xs" fontWeight="700" whiteSpace="nowrap" aria-label={`View source for ${holding.ticker}`} _hover={{ color: 'white', textDecoration: 'none' }}>
                    View source <ExternalLinkIcon mx="2px" />
                  </Link>
                </Td>
              </Tr>
            );
          })}
        </Tbody>
      </Table>
    </TableContainer>
  );
};

export default CuratedHoldingsTable;
