import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Heading,
  Text,
  Button,
  SimpleGrid,
  Stack,
} from '@chakra-ui/react';
import DashboardSourceEvidence from '../components/DashboardSourceEvidence';

const HomePage: React.FC = () => {
  return (
    <Box>
      {/* Hero Section */}
      <Box 
        bg="linear-gradient(135deg, rgba(24, 42, 65, 0.98), rgba(18, 26, 45, 0.98))"
        border="1px solid"
        borderColor="whiteAlpha.200"
        borderRadius="xl" 
        p={12} 
        mb={12}
        textAlign="center"
        color="white"
      >
        <Heading as="h1" size="2xl" mb={4}>
          VIC Analytics Dashboard
        </Heading>
        <Text fontSize="xl" maxW="3xl" mx="auto" mb={4} color="whiteAlpha.800">
          Explore and analyze investment ideas from ValueInvestorsClub.com, tracking performance metrics
          and uncovering insights from top value investors.
        </Text>
        <Text fontSize="md" fontWeight="bold" color="amber.200" maxW="2xl" mx="auto" mb={8}>
          This is an independent analysis tool not affiliated with ValueInvestorsClub.com
        </Text>
        <Stack direction={{ base: 'column', md: 'row' }} spacing={4} justify="center">
          <Button as={RouterLink} to="/articles" size="lg" colorScheme="blue">
            Browse Articles
          </Button>
          <Button
            as={RouterLink}
            to="/companies"
            size="lg"
            variant="outline"
            color="whiteAlpha.900"
            borderColor="whiteAlpha.400"
            _hover={{ bg: 'whiteAlpha.100', borderColor: 'amber.300' }}
          >
            View Companies
          </Button>
          <Button
            as={RouterLink}
            to="/sources"
            size="lg"
            variant="outline"
            color="whiteAlpha.900"
            borderColor="whiteAlpha.400"
            _hover={{ bg: 'whiteAlpha.100', borderColor: 'amber.300' }}
          >
            Verify Sources
          </Button>
        </Stack>
      </Box>

      <DashboardSourceEvidence />

      {/* Features Section */}
      <SimpleGrid columns={{ base: 1, md: 3 }} spacing={10} mb={12}>
        <Box p={5} shadow="md" borderWidth="1px" borderRadius="md">
          <Heading fontSize="xl" mb={4}>Investment Ideas Database</Heading>
          <Text>
            Access a comprehensive collection of publicly available investment ideas from
            ValueInvestorsClub.com, including both long and short positions.
          </Text>
          <Button as={RouterLink} to="/articles" mt={4} colorScheme="blue" variant="outline">
            Browse Articles
          </Button>
        </Box>
        
        <Box p={5} shadow="md" borderWidth="1px" borderRadius="md">
          <Heading fontSize="xl" mb={4}>Performance Tracking</Heading>
          <Text>
            View detailed performance metrics for each investment idea, including short-term
            and long-term returns.
          </Text>
          <Button as={RouterLink} to="/articles" mt={4} colorScheme="blue" variant="outline">
            Analyze Articles
          </Button>
        </Box>
        
        <Box p={5} shadow="md" borderWidth="1px" borderRadius="md">
          <Heading fontSize="xl" mb={4}>Member Insights</Heading>
          <Text>
            Discover investment ideas from top contributors and track their performance
            over time to identify successful strategies.
          </Text>
          <Button as={RouterLink} to="/users" mt={4} colorScheme="blue" variant="outline">
            View Members
          </Button>
        </Box>
      </SimpleGrid>

      {/* CTA Section */}
      <Box
        bg="linear-gradient(135deg, rgba(17, 27, 45, 0.96), rgba(10, 15, 27, 0.94))"
        border="1px solid"
        borderColor="whiteAlpha.200"
        p={8}
        borderRadius="lg"
        textAlign="center"
        color="white"
      >
        <Heading size="lg" mb={4}>
          Start Exploring Investment Ideas
        </Heading>
        <Text fontSize="lg" mb={6} color="whiteAlpha.700">
          Dive into a wealth of value investing knowledge and performance data
        </Text>
        <Button
          as={RouterLink}
          to="/articles"
          size="lg"
          colorScheme="blue"
          px={8}
        >
          Browse Articles
        </Button>
      </Box>
    </Box>
  );
};

export default HomePage;
