import React from 'react';
import { useParams, Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Heading,
  Text,
  Badge,
  Flex,
  Grid,
  GridItem,
  Button,
  Spinner,
  Alert,
  AlertIcon,
  Link,
  HStack,
  Stack,
} from '@chakra-ui/react';
import { useIdeaDetail } from '../hooks/useIdeas';
import PerformanceChart from '../components/PerformanceChart';

interface IdeaDetailPageProps {
  basePath?: string;
  backLabel?: string;
}

const IdeaDetailPage: React.FC<IdeaDetailPageProps> = ({
  basePath = '/ideas',
  backLabel = 'Back to Ideas',
}) => {
  const { id } = useParams<{ id: string }>();
  const { data: idea, isLoading, isError, error } = useIdeaDetail(id || '');

  if (isLoading) {
    return (
      <Flex justify="center" align="center" minH="300px">
        <Spinner size="xl" />
      </Flex>
    );
  }

  if (isError) {
    return (
      <Alert status="error">
        <AlertIcon />
        <Box>
          <Heading size="md" mb={2}>Error loading idea details</Heading>
          <Text>{error instanceof Error ? error.message : 'Unknown error occurred'}</Text>
          <Button as={RouterLink} to={basePath} mt={4} colorScheme="blue">
            {backLabel}
          </Button>
        </Box>
      </Alert>
    );
  }

  if (!idea) {
    return (
      <Alert status="info">
        <AlertIcon />
        <Box>
          <Heading size="md" mb={2}>Idea not found</Heading>
          <Text>The investment idea you're looking for doesn't exist or has been removed.</Text>
          <Button as={RouterLink} to={basePath} mt={4} colorScheme="blue">
            {backLabel}
          </Button>
        </Box>
      </Alert>
    );
  }

  const {
    company_id,
    user_id,
    date,
    is_short,
    is_contest_winner,
    company,
    user,
    description,
    catalysts,
    performance,
    comments,
  } = idea;

  const formattedDate = new Date(date).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  return (
    <Box>
      <Button as={RouterLink} to={basePath} mb={4} variant="outline">
        {backLabel}
      </Button>

      <Flex 
        justify="space-between" 
        align={{ base: 'flex-start', md: 'center' }}
        direction={{ base: 'column', md: 'row' }}
        mb={6}
      >
        <Box>
          <Heading size="lg">
            {company?.company_name || company_id}
            {company && ` (${company.ticker})`}
          </Heading>
          <HStack mt={2} spacing={2}>
            <Badge colorScheme={is_short ? 'red' : 'green'} fontSize="0.8em">
              {is_short ? 'Short' : 'Long'}
            </Badge>
            {is_contest_winner && (
              <Badge colorScheme="purple" fontSize="0.8em">
                Contest Winner
              </Badge>
            )}
            <Text fontSize="sm" color="gray.600">
              Posted: {formattedDate}
            </Text>
            <Text fontSize="sm" color="gray.600">
              by{' '}
              <Link as={RouterLink} to={`${basePath}?user_id=${user_id}`} color="blue.500">
                {user?.username || user_id}
              </Link>
            </Text>
          </HStack>
        </Box>
      </Flex>

      <Grid templateColumns={{ base: '1fr', lg: '2fr 1fr' }} gap={8}>
        <GridItem>
          {/* Description */}
          <Box mb={8}>
            <Heading size="md" mb={4}>Investment Thesis</Heading>
            <Box p={4} borderWidth="1px" borderRadius="md">
              {description ? (
                <Text whiteSpace="pre-wrap">{description.description}</Text>
              ) : (
                <Text color="gray.500">No description available</Text>
              )}
            </Box>
          </Box>

          {/* Catalysts */}
          {catalysts && (
            <Box mb={8}>
              <Heading size="md" mb={4}>Catalysts</Heading>
              <Box p={4} borderWidth="1px" borderRadius="md">
                <Text whiteSpace="pre-wrap">{catalysts.catalysts}</Text>
              </Box>
            </Box>
          )}
        </GridItem>

        <GridItem>
          {/* Performance Chart */}
          {performance ? (
            <PerformanceChart performance={performance} isShort={is_short} />
          ) : (
            <Box>
              <Heading size="md" mb={4}>Performance</Heading>
              <Box p={4} borderWidth="1px" borderRadius="md">
                <Text>No performance data available</Text>
              </Box>
            </Box>
          )}

          {/* External Link */}
          <Box mt={6}>
            <Heading size="md" mb={4}>Original Link</Heading>
            <Box p={4} borderWidth="1px" borderRadius="md">
              <Link href={idea.link} isExternal color="blue.500">
                View original idea on ValueInvestorsClub
              </Link>
            </Box>
          </Box>
        </GridItem>
      </Grid>

      <Box mt={10} w="100%">
        <Heading size="md" mb={4}>Investor discussion ({comments.length})</Heading>
        {comments.length > 0 ? (
          <Stack spacing={3}>
            {comments.map(comment => (
              <Box
                key={comment.id}
                p={4}
                border="1px solid"
                borderColor="whiteAlpha.200"
                borderRadius="lg"
                bg="whiteAlpha.50"
              >
                <Flex
                  direction={{ base: 'column', md: 'row' }}
                  align={{ base: 'flex-start', md: 'center' }}
                  justify="space-between"
                  gap={2}
                  mb={2}
                >
                  {comment.author && (
                    <Text fontWeight="semibold" color="whiteAlpha.900">
                      {comment.author}
                    </Text>
                  )}
                  {comment.posted_at && (
                    <Text as="time" dateTime={comment.posted_at} color="whiteAlpha.600" fontSize="sm">
                      {comment.posted_at}
                    </Text>
                  )}
                </Flex>
                <Text whiteSpace="pre-wrap" overflowWrap="anywhere">{comment.text}</Text>
              </Box>
            ))}
          </Stack>
        ) : (
          <Box
            p={4}
            border="1px solid"
            borderColor="whiteAlpha.200"
            borderRadius="lg"
            bg="whiteAlpha.50"
          >
            <Text color="whiteAlpha.700">No comments were captured for this crawl</Text>
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default IdeaDetailPage;