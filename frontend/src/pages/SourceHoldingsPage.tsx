import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { ArrowBackIcon, ExternalLinkIcon } from '@chakra-ui/icons';
import {
  Badge,
  Box,
  Button,
  Flex,
  Heading,
  HStack,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  Text,
} from '@chakra-ui/react';
import CuratedHoldingsTable from '../components/CuratedHoldingsTable';
import { useCuratedHoldings } from '../hooks/useCuratedHoldings';

export type HoldingSource = 'dataroma' | 'hedgefollow';

interface SourceHoldingsPageProps {
  source: HoldingSource;
}

const SOURCE_COPY: Record<HoldingSource, { label: string; eyebrow: string; description: string; color: string }> = {
  dataroma: {
    label: 'Dataroma holdings',
    eyebrow: 'Source ledger / 01',
    description: 'Quarterly ownership snapshots from Dataroma, kept distinct from other source observations.',
    color: 'amber.200',
  },
  hedgefollow: {
    label: 'HedgeFollow holdings',
    eyebrow: 'Source ledger / 02',
    description: 'Fund-level common-stock observations from HedgeFollow, with options excluded from Phase 1.',
    color: 'purple.200',
  },
};

const SourceHoldingsPage: React.FC<SourceHoldingsPageProps> = ({ source }) => {
  const copy = SOURCE_COPY[source];
  const query = useCuratedHoldings({ source, skip: 0, limit: 100 });
  const holdings = query.data ?? [];
  const totalValue = holdings.reduce((sum, row) => sum + (row.value_usd ?? 0), 0);
  const latestPeriod = holdings[0]?.period ?? '—';

  return (
    <Box>
      <Flex justify="space-between" align={{ base: 'flex-start', md: 'center' }} gap={4} mb={8} direction={{ base: 'column', md: 'row' }}>
        <Box>
          <Text color="whiteAlpha.500" fontSize="xs" letterSpacing="0.2em" textTransform="uppercase">{copy.eyebrow}</Text>
          <Heading mt={3} fontSize={{ base: '3xl', md: '5xl' }} letterSpacing="-0.04em" color="white">{copy.label}</Heading>
          <Text mt={3} color="whiteAlpha.700" maxW="640px">{copy.description}</Text>
        </Box>
        <Button as={RouterLink} to="/holdings" variant="outline" borderColor="whiteAlpha.300" color="whiteAlpha.800" leftIcon={<ArrowBackIcon />} _hover={{ bg: 'whiteAlpha.100', borderColor: copy.color }}>
          All sources
        </Button>
      </Flex>

      <SimpleGrid columns={{ base: 1, sm: 3 }} spacing={4} mb={8}>
        <Stat bg="whiteAlpha.50" border="1px solid" borderColor="whiteAlpha.200" borderRadius="18px" p={5}>
          <StatLabel color="whiteAlpha.500" textTransform="uppercase" letterSpacing="0.14em" fontSize="xs">Curated rows</StatLabel>
          <StatNumber color={copy.color} mt={2}>{holdings.length}</StatNumber>
        </Stat>
        <Stat bg="whiteAlpha.50" border="1px solid" borderColor="whiteAlpha.200" borderRadius="18px" p={5}>
          <StatLabel color="whiteAlpha.500" textTransform="uppercase" letterSpacing="0.14em" fontSize="xs">Observed value</StatLabel>
          <StatNumber color="white" mt={2} fontSize="2xl">{new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: 'compact', maximumFractionDigits: 1 }).format(totalValue)}</StatNumber>
        </Stat>
        <Stat bg="whiteAlpha.50" border="1px solid" borderColor="whiteAlpha.200" borderRadius="18px" p={5}>
          <StatLabel color="whiteAlpha.500" textTransform="uppercase" letterSpacing="0.14em" fontSize="xs">Latest period</StatLabel>
          <StatNumber color="white" mt={2} fontSize="2xl">{latestPeriod}</StatNumber>
        </Stat>
      </SimpleGrid>

      <HStack spacing={3} mb={4}>
        <Badge colorScheme={source === 'dataroma' ? 'orange' : 'purple'} borderRadius="full" px={3} py={1}>{source}</Badge>
        <Text color="whiteAlpha.500" fontSize="sm">Public view · reviewed identities only</Text>
      </HStack>
      <CuratedHoldingsTable holdings={holdings} isLoading={query.isLoading} isError={query.isError} error={query.error} />
      <Text mt={4} color="whiteAlpha.400" fontSize="xs">Source links open the immutable evidence URL <ExternalLinkIcon mx="2px" /></Text>
    </Box>
  );
};

export default SourceHoldingsPage;
