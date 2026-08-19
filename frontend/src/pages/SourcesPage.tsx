import React from 'react';
import {
  Alert,
  AlertDescription,
  AlertIcon,
  Box,
  Center,
  Heading,
  SimpleGrid,
  Spinner,
  Stack,
  Text,
} from '@chakra-ui/react';
import { useCrawlStatus } from '../hooks/useCrawlStatus';
import SourceVerificationCard from '../components/SourceVerificationCard';

const SourcesPage: React.FC = () => {
  const query = useCrawlStatus();

  return (
    <Box
      data-testid="sources-page"
      aria-busy={query.isLoading}
      aria-live="polite"
      overflowX="hidden"
    >
      <Stack spacing={3} mb={{ base: 8, md: 10 }}>
        <Text color="amber.200" fontSize="xs" textTransform="uppercase" letterSpacing="0.2em">
          Source verification / bounded crawl evidence
        </Text>
        <Heading as="h1" color="white" fontSize={{ base: '3xl', md: '5xl' }} letterSpacing="-0.05em">
          Source verification
        </Heading>
        <Text color="whiteAlpha.700" maxW="760px">
          Inspect parser output separately from staging, identity review, and public data. This page reports the latest operator-run crawl without inferring success from old rows.
        </Text>
      </Stack>

      {query.isLoading && (
        <Center minH="360px" role="status" aria-live="polite" flexDirection="column" gap={4}>
          <Spinner color="amber.300" size="xl" />
          <Text color="whiteAlpha.700">Loading source verification</Text>
        </Center>
      )}

      {query.isError && (
        <Alert status="error" borderRadius="16px" bg="red.900" color="red.100">
          <AlertIcon />
          <AlertDescription>
            Unable to load source verification: {query.error instanceof Error ? query.error.message : 'Unknown endpoint error'}
          </AlertDescription>
        </Alert>
      )}

      {!query.isLoading && !query.isError && (
        <SimpleGrid columns={{ base: 1, xl: 3 }} spacing={{ base: 4, md: 5 }} alignItems="start">
          {(query.data ?? []).map((source) => <SourceVerificationCard key={source.source} source={source} />)}
        </SimpleGrid>
      )}
    </Box>
  );
};

export default SourcesPage;
