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
  Code,
  Flex,
  Heading,
  Link,
  Text,
} from '@chakra-ui/react';
import { CrawlRun, CrawlSample, CrawlSourceStatus } from '../types/api';

const formatNumber = (value: number | null | undefined, options?: Intl.NumberFormatOptions) => (
  value == null ? '—' : new Intl.NumberFormat('en-US', options).format(value)
);

const formatTimestamp = (value: string) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toISOString().replace('T', ' ').replace('.000Z', ' UTC');
};

const isEmptyRun = (run: CrawlRun) => run.status === 'complete' && run.rows_seen === 0;

const getStatusLabel = (run: CrawlRun) => {
  if (!run.id) return 'No run recorded';
  if (run.status === 'running') return 'Crawl in progress';
  if (isEmptyRun(run)) return 'Empty run warning';
  if (run.status === 'partial') return 'Partial crawl warning';
  if (run.status === 'failed') return 'Crawl failed';
  if (run.status === 'complete') return 'Healthy crawl';
  return 'Status unavailable';
};

const isRunWarning = (run: CrawlRun) => !run.id || run.status !== 'complete' || isEmptyRun(run);

const getRunWarningMessage = (run: CrawlRun) => {
  if (!run.id) return 'No crawl has been recorded. Treat this source as unverified.';
  if (run.status === 'running') return 'Crawl is still running. Wait for completion before treating this source as healthy.';
  if (run.status === 'failed') return `Crawl failed: ${run.error_message ?? 'Check the crawl counters before retrying.'}`;
  if (isEmptyRun(run)) return 'Run produced no parser output. Check the crawl counters before treating this source as healthy.';
  if (run.status === 'partial') return `Crawl completed with warnings: ${run.error_message ?? 'Check the crawl counters before treating this source as healthy.'}`;
  return `Crawl status is unavailable: ${run.error_message ?? 'Check the crawl counters before treating this source as healthy.'}`;
};

const MetricList = ({ source }: { source: CrawlSourceStatus }) => {
  const metrics = source.target === 'ideas'
    ? [
        ['Parser output', source.counts.parser_output],
        ['Public articles', source.counts.public],
      ]
    : [
        ['Parser output', source.counts.parser_output],
        ['Staged for review', source.counts.staged],
        ['Pending identity', source.counts.pending_identity],
        ['Public curated', source.counts.curated],
      ];

  return (
    <Box as="dl" display="grid" gridTemplateColumns="repeat(2, minmax(0, 1fr))" gap={3}>
      {metrics.map(([label, value]) => (
        <Box key={label} border="1px solid" borderColor="whiteAlpha.200" borderRadius="14px" bg="blackAlpha.200" p={4}>
          <Text as="dt" color="whiteAlpha.600" fontSize="xs" textTransform="uppercase" letterSpacing="0.1em">
            {label}
          </Text>
          <Text as="dd" mt={2} color="white" fontSize="2xl" fontWeight="700">
            {value}
          </Text>
        </Box>
      ))}
    </Box>
  );
};

const RunMetadata = ({ run }: { run: CrawlRun }) => {
  if (!run.id) {
    return (
      <Box mt={4} borderTop="1px solid" borderColor="whiteAlpha.100" pt={4}>
        <Text color="white" fontSize="sm" fontWeight="700">No run recorded</Text>
        <Text mt={1} color="whiteAlpha.700" fontSize="sm">Awaiting operator-run crawl</Text>
      </Box>
    );
  }

  return (
    <Box as="dl" mt={4} borderTop="1px solid" borderColor="whiteAlpha.100" pt={4} display="grid" gridTemplateColumns="minmax(0, auto) minmax(0, 1fr)" columnGap={4} rowGap={2} fontSize="sm" sx={{ '& > dd': { minWidth: 0, overflowWrap: 'anywhere' } }}>
      <Text as="dt" color="whiteAlpha.600">Run status</Text>
      <Text as="dd" color="white" fontWeight="700">{getStatusLabel(run)}</Text>
      <Text as="dt" color="whiteAlpha.600">Run ID</Text>
      <Text as="dd" color="whiteAlpha.700" overflowWrap="anywhere">{run.id}</Text>
      <Text as="dt" color="whiteAlpha.600">Parser version</Text>
      <Text as="dd" color="amber.200">{run.parser_version ?? 'Unknown parser'}</Text>
      <Text as="dt" color="whiteAlpha.600">Started</Text>
      <Text as="dd" color="whiteAlpha.700">
        {run.started_at ? <time dateTime={run.started_at}>{formatTimestamp(run.started_at)}</time> : 'Not recorded'}
      </Text>
      <Text as="dt" color="whiteAlpha.600">Finished</Text>
      <Text as="dd" color="whiteAlpha.700">
        {run.finished_at ? <time dateTime={run.finished_at}>{formatTimestamp(run.finished_at)}</time> : 'Still running'}
      </Text>
      <Text as="dt" color="whiteAlpha.600">Rows seen / accepted</Text>
      <Text as="dd" color="whiteAlpha.700">{run.rows_seen} / {run.rows_accepted}</Text>
      <Text as="dt" color="whiteAlpha.600">Rejected / duplicates</Text>
      <Text as="dd" color="whiteAlpha.700">{run.rows_rejected} / {run.rows_duplicate}</Text>
    </Box>
  );
};

const SampleDetails = ({ sample, label }: { sample: CrawlSample; label: string }) => {
  const sourceUrl = sample.source_url ?? sample.link;
  const isIdea = sample.kind === 'idea';

  return (
    <Box border="1px solid" borderColor="whiteAlpha.200" borderRadius="16px" bg="blackAlpha.300" p={4}>
      <Text color="amber.200" fontSize="xs" textTransform="uppercase" letterSpacing="0.14em">
        Latest accepted sample
      </Text>
      <Box as="dl" mt={3} display="grid" gridTemplateColumns="minmax(0, auto) minmax(0, 1fr)" columnGap={4} rowGap={2} fontSize="sm" sx={{ '& > dd': { minWidth: 0, overflowWrap: 'anywhere' } }}>
        {sample.investor_name && (
          <>
            <Text as="dt" color="whiteAlpha.600">Investor</Text>
            <Text as="dd" color="white">{sample.investor_name}</Text>
          </>
        )}
        {sample.ticker && (
          <>
            <Text as="dt" color="whiteAlpha.600">Ticker</Text>
            <Text as="dd" color="amber.200" fontWeight="700">{sample.ticker}</Text>
          </>
        )}
        {sample.company_name && (
          <>
            <Text as="dt" color="whiteAlpha.600">Company</Text>
            <Text as="dd" color="white">{sample.company_name}</Text>
          </>
        )}
        {sample.period && (
          <>
            <Text as="dt" color="whiteAlpha.600">Period</Text>
            <Text as="dd" color="whiteAlpha.700">{sample.period}</Text>
          </>
        )}
        {isIdea && sample.idea_date && (
          <>
            <Text as="dt" color="whiteAlpha.600">Published</Text>
            <Text as="dd" color="whiteAlpha.700">{`Published ${sample.idea_date.slice(0, 10)}`}</Text>
          </>
        )}
        {!isIdea && sample.shares != null && (
          <>
            <Text as="dt" color="whiteAlpha.600">Shares</Text>
            <Text as="dd" color="whiteAlpha.700">{formatNumber(sample.shares)}</Text>
          </>
        )}
        {!isIdea && sample.value_usd != null && (
          <>
            <Text as="dt" color="whiteAlpha.600">Value</Text>
            <Text as="dd" color="whiteAlpha.700">{formatNumber(sample.value_usd, { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })}</Text>
          </>
        )}
        {!isIdea && sample.pct_portfolio != null && (
          <>
            <Text as="dt" color="whiteAlpha.600">Portfolio %</Text>
            <Text as="dd" color="whiteAlpha.700">{formatNumber(sample.pct_portfolio, { maximumFractionDigits: 2 })}%</Text>
          </>
        )}
        {!isIdea && sample.activity && (
          <>
            <Text as="dt" color="whiteAlpha.600">Activity</Text>
            <Text as="dd" color="whiteAlpha.700">{sample.activity}</Text>
          </>
        )}
        {!isIdea && sample.identity_status && (
          <>
            <Text as="dt" color="whiteAlpha.600">Identity</Text>
            <Text as="dd" color="whiteAlpha.700">{sample.identity_status}</Text>
          </>
        )}
      </Box>
      {sourceUrl && (
        <Link
          href={sourceUrl}
          isExternal
          mt={4}
          display="inline-flex"
          alignItems="center"
          gap={1}
          color="amber.200"
          fontSize="sm"
          fontWeight="700"
          aria-label={`Open original source record for ${label}`}
          _hover={{ color: 'white', textDecoration: 'none' }}
        >
          Open original source record <ExternalLinkIcon />
        </Link>
      )}
    </Box>
  );
};

const SourceVerificationCard = ({ source }: { source: CrawlSourceStatus }) => {
  const run = source.latest_run;
  const isIdeas = source.target === 'ideas';

  return (
    <Box
      border="1px solid"
      borderColor="whiteAlpha.200"
      borderRadius="22px"
      bg="whiteAlpha.50"
      p={{ base: 5, md: 6 }}
      minW={0}
    >
      <Flex justify="space-between" align={{ base: 'flex-start', sm: isIdeas ? 'flex-start' : 'center' }} direction={{ base: 'column', sm: isIdeas ? 'column' : 'row' }} gap={2}>
        <Box minW={0}>
          <Text color={isIdeas ? 'purple.200' : 'amber.200'} fontSize="xs" textTransform="uppercase" letterSpacing="0.16em">
            {isIdeas ? 'Idea source' : 'Holding source'}
          </Text>
          <Heading
            as="h2"
            mt={2}
            color="white"
            fontSize={isIdeas ? 'lg' : '2xl'}
            overflowWrap="break-word"
            lineHeight="1.1"
          >
            {source.label}
          </Heading>
        </Box>
        <Badge flexShrink={0} colorScheme={isRunWarning(run) ? 'orange' : run.id ? 'green' : 'gray'} px={3} py={1} borderRadius="full">
          {getStatusLabel(run)}
        </Badge>
      </Flex>

      <Text mt={3} color="whiteAlpha.700" fontSize="sm" overflowWrap="anywhere">
        {isIdeas
          ? 'VIC parser output is counted separately from articles already visible in the public route.'
          : source.source === 'hedgefollow'
            ? 'Common-stock parser output only; options are excluded before identity review.'
            : 'Holding observations remain staged until identity review promotes them to curated data.'}
      </Text>

      <RunMetadata run={run} />

      {isRunWarning(run) && (
        <Alert status="warning" mt={4} borderRadius="14px" bg="orange.900" color="orange.100">
          <AlertIcon />
          <AlertDescription fontSize="sm">
            {getRunWarningMessage(run)}
          </AlertDescription>
        </Alert>
      )}

      <Box mt={5}>
        <MetricList source={source} />
      </Box>

      <Box mt={5}>
        {source.sample ? (
          <SampleDetails sample={source.sample} label={source.label} />
        ) : run.id ? (
          <Box border="1px dashed" borderColor="whiteAlpha.300" borderRadius="16px" p={4}>
            <Text color="whiteAlpha.700" fontSize="sm">No accepted sample in latest run</Text>
          </Box>
        ) : null}
      </Box>

      <Text mt={4} color="whiteAlpha.700" fontSize="sm">
        Local route: <Code>{source.public_route}</Code>
      </Text>

      <Button
        as={RouterLink}
        to={source.public_route}
        mt={5}
        size="sm"
        variant="outline"
        borderColor="whiteAlpha.300"
        color="whiteAlpha.800"
        _hover={{ bg: 'whiteAlpha.100', borderColor: 'amber.300' }}
      >
        View public {isIdeas ? 'articles' : 'curated holdings'}
      </Button>
    </Box>
  );
};

export default SourceVerificationCard;
