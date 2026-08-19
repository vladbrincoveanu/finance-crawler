import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { ExternalLinkIcon } from '@chakra-ui/icons';
import {
  Alert,
  AlertDescription,
  AlertIcon,
  Badge,
  Box,
  Button,
  Flex,
  Heading,
  Link,
  SimpleGrid,
  Spinner,
  Stack,
  Text,
} from '@chakra-ui/react';
import { CrawlRun, CrawlSourceStatus } from '../types/api';
import { useCrawlStatus } from '../hooks/useCrawlStatus';

const getStatusColor = (run: CrawlRun | null) => {
  if (!run?.id) return 'gray';
  if (run.status === 'complete') return 'green';
  if (run.status === 'running') return 'blue';
  if (run.status === 'failed') return 'red';
  return 'orange';
};

const getStatusLabel = (run: CrawlRun | null) => {
  if (!run?.id) return 'Not run';
  if (run.status === 'complete') return 'Healthy';
  if (run.status === 'running') return 'Running';
  if (run.status === 'failed') return 'Failed';
  return 'Partial';
};

const SourceEvidenceCard = ({ source }: { source: CrawlSourceStatus }) => {
  const run = source.latest_run;
  const sample = source.sample;
  const isIdea = source.target === 'ideas';
  const sampleTitle = sample?.ticker || sample?.company_name || 'No accepted sample';
  const sampleUrl = sample?.source_url || sample?.link;

  return (
    <Box
      border="1px solid"
      borderColor="whiteAlpha.200"
      borderTopColor={isIdea ? 'purple.300' : 'amber.300'}
      borderRadius="20px"
      bg="rgba(7, 11, 20, 0.64)"
      p={{ base: 4, md: 5 }}
      minW={0}
      transition="transform 180ms ease, border-color 180ms ease"
      _hover={{ transform: 'translateY(-2px)', borderColor: 'amber.300' }}
    >
      <Flex align="flex-start" justify="space-between" gap={3}>
        <Box minW={0}>
          <Text
            color={isIdea ? 'purple.200' : 'amber.200'}
            fontSize="xs"
            fontWeight="700"
            letterSpacing="0.14em"
            textTransform="uppercase"
          >
            {isIdea ? 'Idea source' : 'Holding source'}
          </Text>
          <Heading as="h3" mt={2} color="white" fontSize="lg" lineHeight="1.15" overflowWrap="anywhere">
            {source.label}
          </Heading>
        </Box>
        <Badge flexShrink={0} colorScheme={getStatusColor(run)} borderRadius="full" px={2.5} py={1}>
          {getStatusLabel(run)}
        </Badge>
      </Flex>

      <Flex mt={4} gap={2} wrap="wrap" color="whiteAlpha.700" fontSize="sm">
        <Text>{run ? `${run.rows_accepted} accepted` : 'No run recorded'}</Text>
        <Text color="whiteAlpha.400">/</Text>
        <Text>{isIdea ? `${source.counts.public} public` : `${source.counts.staged} staged`}</Text>
      </Flex>

      <Box mt={4} border="1px solid" borderColor="whiteAlpha.100" borderRadius="14px" bg="whiteAlpha.50" p={3.5}>
        <Text color="whiteAlpha.500" fontSize="xs" letterSpacing="0.1em" textTransform="uppercase">
          Latest accepted sample
        </Text>
        <Text mt={2} color="white" fontSize="lg" fontWeight="700" overflowWrap="anywhere">
          {sampleTitle}
        </Text>
        {sample?.company_name && sample.ticker && (
          <Text mt={1} color="whiteAlpha.700" fontSize="sm" overflowWrap="anywhere">
            {sample.company_name}
          </Text>
        )}
        {sample?.investor_name && (
          <Text mt={2} color="whiteAlpha.600" fontSize="xs" overflowWrap="anywhere">
            Investor: {sample.investor_name}
          </Text>
        )}
        <Text mt={2} color={isIdea ? 'purple.200' : 'amber.200'} fontSize="xs" fontWeight="700">
          {isIdea ? 'Public idea record' : `Staged / ${sample?.identity_status || 'pending identity'}`}
        </Text>
        {sampleUrl && (
          <Link
            href={sampleUrl}
            isExternal
            mt={3}
            display="inline-flex"
            alignItems="center"
            gap={1}
            color="whiteAlpha.800"
            fontSize="xs"
            fontWeight="700"
            aria-label={`Open original source record for ${source.label}`}
            _hover={{ color: 'amber.200', textDecoration: 'none' }}
          >
            Open source record <ExternalLinkIcon />
          </Link>
        )}
      </Box>
    </Box>
  );
};

const DashboardSourceEvidence: React.FC = () => {
  const query = useCrawlStatus();

  return (
    <Box
      as="section"
      aria-busy={query.isLoading}
      aria-live="polite"
      border="1px solid"
      borderColor="whiteAlpha.200"
      borderRadius="28px"
      bg="linear-gradient(135deg, rgba(17, 27, 45, 0.96), rgba(10, 15, 27, 0.94))"
      boxShadow="0 24px 80px rgba(0, 0, 0, 0.2)"
      p={{ base: 5, md: 8 }}
      mb={12}
    >
      <Flex align={{ base: 'flex-start', md: 'flex-end' }} justify="space-between" direction={{ base: 'column', md: 'row' }} gap={5}>
        <Stack spacing={2}>
          <Text color="amber.200" fontSize="xs" fontWeight="700" letterSpacing="0.18em" textTransform="uppercase">
            Data provenance / live checks
          </Text>
          <Heading as="h2" color="white" fontSize={{ base: '2xl', md: '3xl' }} letterSpacing="-0.04em">
            Live crawl evidence
          </Heading>
          <Text color="whiteAlpha.700" maxW="680px" fontSize={{ base: 'sm', md: 'md' }}>
            The latest bounded crawl, its accepted output, and one real record from every source. Staged holdings are not presented as curated data.
          </Text>
        </Stack>
        <Button
          as={RouterLink}
          to="/sources"
          variant="outline"
          size="sm"
          borderColor="whiteAlpha.300"
          color="whiteAlpha.900"
          flexShrink={0}
          aria-label="View full source verification"
          _hover={{ bg: 'whiteAlpha.100', borderColor: 'amber.300' }}
        >
          View full source verification
        </Button>
      </Flex>

      {query.isLoading && (
        <Flex mt={7} align="center" gap={3} color="whiteAlpha.700" role="status">
          <Spinner size="sm" color="amber.300" />
          <Text>Loading live crawl evidence</Text>
        </Flex>
      )}

      {query.isError && (
        <Alert mt={7} status="error" borderRadius="14px" bg="red.900" color="red.100">
          <AlertIcon />
          <AlertDescription>
            Unable to load live crawl evidence: {query.error instanceof Error ? query.error.message : 'Unknown endpoint error'}
          </AlertDescription>
        </Alert>
      )}

      {!query.isLoading && !query.isError && (
        query.data?.length ? (
          <SimpleGrid mt={7} columns={{ base: 1, lg: 3 }} spacing={4} alignItems="stretch">
            {query.data.map((source) => <SourceEvidenceCard key={source.source} source={source} />)}
          </SimpleGrid>
        ) : (
          <Alert mt={7} status="warning" borderRadius="14px" bg="orange.900" color="orange.100">
            <AlertIcon />
            <AlertDescription>No crawl evidence is available yet.</AlertDescription>
          </Alert>
        )
      )}
    </Box>
  );
};

export default DashboardSourceEvidence;
