import React from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { Badge, Box, Flex, Heading, HStack, Link, Skeleton, Text } from '@chakra-ui/react';
import { Idea, Company, User, Performance } from '../types/api';
import { useQuery } from 'react-query';
import { companiesApi, usersApi, ideasApi } from '../api/apiService';

interface IdeaCardProps {
  idea: Idea;
  performance?: Performance; // Making it optional since not all ideas have performance data
  performancePeriod?: string;
  linkBasePath?: string;
}

const PERFORMANCE_PERIODS: Record<string, { key: keyof Performance; label: string }> = {
  one_week_perf: { key: 'oneWeekClosePerf', label: '1W' },
  two_week_perf: { key: 'twoWeekClosePerf', label: '2W' },
  one_month_perf: { key: 'oneMonthPerf', label: '1M' },
  three_month_perf: { key: 'threeMonthPerf', label: '3M' },
  six_month_perf: { key: 'sixMonthPerf', label: '6M' },
  one_year_perf: { key: 'oneYearPerf', label: '1Y' },
  two_year_perf: { key: 'twoYearPerf', label: '2Y' },
  three_year_perf: { key: 'threeYearPerf', label: '3Y' },
  five_year_perf: { key: 'fiveYearPerf', label: '5Y' },
};

const IdeaCard: React.FC<IdeaCardProps> = ({
  idea,
  performance: initialPerformance,
  performancePeriod = 'one_year_perf',
  linkBasePath = '/ideas',
}) => {
  const { id, company_id, user_id, date, is_short, is_contest_winner } = idea;
  
  // Fetch performance data if not provided
  const { data: fetchedPerformance, isLoading: isPerformanceLoading } = useQuery(
    ['idea-performance', id],
    () => ideasApi.getIdeaPerformance(id),
    {
      enabled: !initialPerformance, // Only fetch if not provided
      staleTime: 60000, // Cache results for 1 minute
      cacheTime: 300000 // Keep in cache for 5 minutes
    }
  );
  
  // Use provided performance or fetched data
  const performance = initialPerformance || fetchedPerformance;
  
  // Search by ticker/name instead of company_id
  const { data: companies, isLoading: isCompanyLoading } = useQuery<Company[]>(
    ['company-search', company_id],
    () => companiesApi.getCompanies({ search: company_id }),
    { 
      enabled: !!company_id,
      staleTime: 60000, // Cache results for 1 minute to reduce flickering
      cacheTime: 300000 // Keep in cache for 5 minutes
    }
  );
  
  // Get the first company if multiple are returned
  const company = companies && companies.length > 0 ? companies[0] : null;

  // Search by username instead of user_id
  const { data: users, isLoading: isUserLoading } = useQuery<User[]>(
    ['user-search', user_id],
    () => usersApi.getUsers({ search: user_id }),
    { 
      enabled: !!user_id,
      staleTime: 60000, // Cache results for 1 minute to reduce flickering
      cacheTime: 300000 // Keep in cache for 5 minutes
    }
  );
  
  // Get the first user if multiple are returned
  const user = users && users.length > 0 ? users[0] : null;
  const navigate = useNavigate();
  
  const formattedDate = new Date(date).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
  
  const metric = PERFORMANCE_PERIODS[performancePeriod] || PERFORMANCE_PERIODS.one_year_perf;
  const metricValue = performance
    ? performance[metric.key] as number | null | undefined
    : undefined;
  const adjustedMetricValue = metricValue === null || metricValue === undefined
    ? undefined
    : is_short
      ? -metricValue
      : metricValue;
  const formattedMetricValue = adjustedMetricValue === undefined
    ? '--'
    : `${adjustedMetricValue > 0 ? '+' : ''}${adjustedMetricValue.toFixed(1)}%`;
  const metricColor = adjustedMetricValue === undefined
    ? 'whiteAlpha.500'
    : adjustedMetricValue >= 0
      ? 'green.300'
      : 'red.300';

  const handleRowKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      navigate(`${linkBasePath}/${id}`);
    }
  };

  return (
    <Box
      role="link"
      tabIndex={0}
      aria-label={`Open ${company?.company_name || company_id} idea`}
      onClick={() => navigate(`${linkBasePath}/${id}`)}
      onKeyDown={handleRowKeyDown}
      cursor="pointer"
      px={{ base: 1, md: 3 }}
      py={4}
      borderBottomWidth="1px"
      borderColor="whiteAlpha.200"
      _hover={{ bg: 'whiteAlpha.100' }}
      _focusVisible={{ bg: 'whiteAlpha.100' }}
      transition="background-color 0.2s"
      data-testid="idea-card"
    >
      <Flex align={{ base: 'flex-start', md: 'center' }} gap={4}>
        <Box flex="1" minW={0}>
          <Flex align="center" flexWrap="wrap" gap={2}>
            <Heading size="sm" minW={0}>
              <Link
                as={RouterLink}
                to={`${linkBasePath}/${id}`}
                _hover={{ textDecoration: 'none', color: 'amber.200' }}
              >
                <Skeleton
                  isLoaded={!isCompanyLoading}
                  startColor="ink.800"
                  endColor="whiteAlpha.300"
                  display="inline"
                >
                  {company ? (
                    <>
                      {company.company_name || company_id}
                      {company.ticker && <Text as="span" color="whiteAlpha.600" fontWeight="normal"> ({company.ticker})</Text>}
                    </>
                  ) : (
                    company_id
                  )}
                </Skeleton>
              </Link>
            </Heading>
            <HStack spacing={2}>
              <Badge colorScheme={is_short ? 'red' : 'green'}>
                {is_short ? 'Short' : 'Long'}
              </Badge>
              {is_contest_winner && (
                <Badge colorScheme="orange">Contest Winner</Badge>
              )}
            </HStack>
          </Flex>

          <Flex mt={2} fontSize="sm" color="whiteAlpha.600" flexWrap="wrap" align="center">
            <Text>Posted {formattedDate}</Text>
            <Text mx={2} color="whiteAlpha.400">|</Text>
            <Link
              as={RouterLink}
              to={`${linkBasePath}?user_id=${user_id}`}
              onClick={event => event.stopPropagation()}
              _hover={{ color: 'amber.200' }}
            >
              <Skeleton
                isLoaded={!isUserLoading}
                startColor="ink.800"
                endColor="whiteAlpha.300"
                display="inline"
              >
                {user ? user.username || user_id : user_id}
              </Skeleton>
            </Link>
          </Flex>
        </Box>

        <Box minW={{ base: '70px', md: '100px' }} textAlign="right">
          <Skeleton
            isLoaded={!isPerformanceLoading}
            startColor="ink.800"
            endColor="whiteAlpha.300"
          >
            <Text color={metricColor} fontWeight="bold" fontSize={{ base: 'md', md: 'lg' }}>
              {formattedMetricValue}
            </Text>
          </Skeleton>
          <Text color="whiteAlpha.500" fontSize="xs">{metric.label}</Text>
        </Box>
      </Flex>
    </Box>
  );
};

export default IdeaCard;
