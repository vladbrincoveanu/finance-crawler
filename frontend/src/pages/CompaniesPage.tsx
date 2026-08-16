import React, { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Heading,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Button,
  Input,
  Flex,
  Spinner,
  Alert,
  AlertIcon,
  Text,
  InputGroup,
  InputRightElement,
} from '@chakra-ui/react';
import { SearchIcon } from '@chakra-ui/icons';
import { useCompanies } from '../hooks/useCompanies';
import { ListParams } from '../types/api';

const CompaniesPage: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState<ListParams>({
    skip: 0,
    limit: 50,
    search: '',
  });

  const { data: companies, isLoading, isError, error } = useCompanies(filters);

  // Keep track of all loaded companies and seen tickers to prevent duplicates
  const [allCompanies, setAllCompanies] = useState<typeof companies>([]);
  const seenTickers = React.useRef(new Set<string>());

  React.useEffect(() => {
    if (companies) {
      if (filters.skip === 0) {
        seenTickers.current = new Set(companies.map(c => c.ticker));
        setAllCompanies(companies);
      } else {
        const newCompanies = companies.filter(c => !seenTickers.current.has(c.ticker));
        newCompanies.forEach(c => seenTickers.current.add(c.ticker));
        if (newCompanies.length > 0) {
          setAllCompanies(prev => [...(prev || []), ...newCompanies]);
        }
      }
    }
  }, [companies, filters.skip]);

  const handleSearch = () => {
    setFilters(prev => ({
      ...prev,
      search: searchQuery,
      skip: 0, // Reset pagination on new search
    }));
  };

  const loadMore = () => {
    setFilters(prev => ({
      ...prev,
      skip: (prev.skip || 0) + (prev.limit || 50),
    }));
  };

  return (
    <Box>
      <Heading mb={6}>Companies</Heading>

      {/* Search */}
      <Box mb={6}>
        <InputGroup size="lg">
          <Input
            placeholder="Search companies by name or ticker..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          />
          <InputRightElement width="4.5rem">
            <Button h="1.75rem" size="sm" onClick={handleSearch}>
              <SearchIcon />
            </Button>
          </InputRightElement>
        </InputGroup>
      </Box>

      {/* Companies Table */}
      {isLoading && !allCompanies?.length ? (
        <Flex justify="center" align="center" minH="300px">
          <Spinner size="xl" />
        </Flex>
      ) : isError ? (
        <Alert status="error">
          <AlertIcon />
          <Box>
            <Heading size="md" mb={2}>Error loading companies</Heading>
            <Text>{error instanceof Error ? error.message : 'Unknown error occurred'}</Text>
          </Box>
        </Alert>
      ) : allCompanies && allCompanies.length > 0 ? (
        <>
          <Box overflowX="auto">
            <Table variant="simple">
              <Thead>
                <Tr>
                  <Th>Ticker</Th>
                  <Th>Company Name</Th>
                  <Th>View Ideas</Th>
                </Tr>
              </Thead>
              <Tbody>
                {allCompanies.map((company) => (
                  <Tr key={company.ticker}>
                    <Td fontWeight="bold">{company.ticker}</Td>
                    <Td>{company.company_name}</Td>
                    <Td>
                      <Button
                        as={RouterLink}
                        to={`/ideas?company_id=${company.ticker}`}
                        size="sm"
                        colorScheme="blue"
                      >
                        View Ideas
                      </Button>
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </Box>

          <Flex justify="center" mt={8}>
            <Button
              onClick={loadMore}
              size="lg"
              colorScheme="blue"
              isLoading={isLoading}
              loadingText="Loading..."
              isDisabled={!!companies && companies.length === 0}
            >
              {companies && companies.length === 0 ? 'No More Companies' : 'Load More'}
            </Button>
          </Flex>
        </>
      ) : (
        <Box textAlign="center" p={8}>
          <Text fontSize="xl">No companies found matching your search criteria.</Text>
        </Box>
      )}
    </Box>
  );
};

export default CompaniesPage;