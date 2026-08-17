import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { ArrowForwardIcon } from '@chakra-ui/icons';
import { Box, Button, Flex, Heading, HStack, SimpleGrid, Text } from '@chakra-ui/react';
import CuratedHoldingsTable from '../components/CuratedHoldingsTable';
import { useCuratedHoldings } from '../hooks/useCuratedHoldings';

const HoldingsPage: React.FC = () => {
  const query = useCuratedHoldings({ skip: 0, limit: 100 });
  const holdings = query.data ?? [];
  const sourceCount = new Set(holdings.map((row) => row.source)).size;

  return (
    <Box>
      <Flex justify="space-between" align={{ base: 'flex-start', md: 'center' }} direction={{ base: 'column', md: 'row' }} gap={5} mb={8}>
        <Box>
          <Text color="amber.200" fontSize="xs" letterSpacing="0.2em" textTransform="uppercase">Ownership intelligence / live ledger</Text>
          <Heading mt={3} fontSize={{ base: '3xl', md: '5xl' }} letterSpacing="-0.05em" color="white">Curated holdings</Heading>
          <Text mt={3} color="whiteAlpha.700" maxW="650px">A source-aware view of reported ownership. Same security, different source facts: never merged, never silently inferred.</Text>
        </Box>
        <HStack spacing={3}>
          <Button as={RouterLink} to="/holdings/dataroma" variant="outline" borderColor="orange.300" color="orange.200" rightIcon={<ArrowForwardIcon />} _hover={{ bg: 'orange.300', color: 'gray.900' }}>Dataroma</Button>
          <Button as={RouterLink} to="/holdings/hedgefollow" variant="outline" borderColor="purple.300" color="purple.200" rightIcon={<ArrowForwardIcon />} _hover={{ bg: 'purple.300', color: 'gray.900' }}>HedgeFollow</Button>
        </HStack>
      </Flex>

      <SimpleGrid columns={{ base: 1, sm: 2 }} spacing={4} mb={8}>
        <Box border="1px solid" borderColor="whiteAlpha.200" borderRadius="18px" bg="whiteAlpha.50" p={5}>
          <Text color="whiteAlpha.500" fontSize="xs" textTransform="uppercase" letterSpacing="0.14em">Curated observations</Text>
          <Text mt={2} color="white" fontSize="3xl" fontWeight="700">{query.isLoading ? '—' : holdings.length}</Text>
        </Box>
        <Box border="1px solid" borderColor="whiteAlpha.200" borderRadius="18px" bg="whiteAlpha.50" p={5}>
          <Text color="whiteAlpha.500" fontSize="xs" textTransform="uppercase" letterSpacing="0.14em">Active sources</Text>
          <Text mt={2} color="white" fontSize="3xl" fontWeight="700">{query.isLoading ? '—' : sourceCount}</Text>
        </Box>
      </SimpleGrid>

      <CuratedHoldingsTable holdings={holdings} isLoading={query.isLoading} isError={query.isError} error={query.error} />
    </Box>
  );
};

export default HoldingsPage;
