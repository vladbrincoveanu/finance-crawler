import React, { useEffect, useRef, useState } from 'react';
import {
  Alert,
  AlertDescription,
  AlertIcon,
  AlertTitle,
  Badge,
  Box,
  Button,
  Flex,
  Heading,
  Input,
  InputGroup,
  InputLeftElement,
  Select,
  Spinner,
  Tag,
  TagCloseButton,
  TagLabel,
  Text,
  useDisclosure,
} from '@chakra-ui/react';
import { SearchIcon } from '@chakra-ui/icons';
import { useQuery } from 'react-query';
import { useIdeas } from '../hooks/useIdeas';
import IdeaCard from '../components/IdeaCard';
import IdeasFilterDrawer from '../components/IdeasFilterDrawer';
import { companiesApi, usersApi } from '../api/apiService';
import { Idea, ListParams } from '../types/api';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  DEFAULT_FILTERS,
  filtersToSortSelection,
  getActiveFilterLabels,
  getInitialFilters,
  PAGE_SIZE,
  removeFilter,
  SortSelection,
  sortSelectionToFilters,
  toQueryString,
} from './ideasFilters';

interface IdeasPageProps {
  title?: string;
  linkBasePath?: string;
}

interface SearchSuggestion {
  type: 'company' | 'user';
  value: string;
  label: string;
}

const IdeasPage: React.FC<IdeasPageProps> = ({
  title = 'Investment Ideas',
  linkBasePath = '/ideas',
}) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [filters, setFilters] = useState<ListParams>(() => getInitialFilters(location.search));
  const [searchQuery, setSearchQuery] = useState('');
  const [searchOpen, setSearchOpen] = useState(false);

  useEffect(() => {
    const nextSearch = toQueryString(filters);
    const currentSearch = location.search.replace(/^\?/, '');

    if (nextSearch !== currentSearch) {
      navigate(nextSearch ? `?${nextSearch}` : '', { replace: true });
    }
  }, [filters, navigate, location.search]);

  const normalizedSearch = searchQuery.trim();
  const { data: companyMatches = [] } = useQuery(
    ['ideas-company-search', normalizedSearch],
    () => companiesApi.getCompanies({ search: normalizedSearch, limit: 5 }),
    {
      enabled: normalizedSearch.length >= 2,
      staleTime: 30000,
    },
  );
  const { data: userMatches = [] } = useQuery(
    ['ideas-user-search', normalizedSearch],
    () => usersApi.getUsers({ search: normalizedSearch, limit: 5 }),
    {
      enabled: normalizedSearch.length >= 2,
      staleTime: 30000,
    },
  );

  const suggestions: SearchSuggestion[] = [
    ...companyMatches.map(company => ({
      type: 'company' as const,
      value: company.ticker,
      label: `${company.company_name} (${company.ticker})`,
    })),
    ...userMatches.map(user => ({
      type: 'user' as const,
      value: user.user_link,
      label: `@${user.username}`,
    })),
  ];

  const [allIdeas, setAllIdeas] = useState<Idea[]>([]);
  const seenIdeaIds = useRef(new Set<string>());
  const isNewFilter = useRef(true);

  const { data: ideas, isLoading, isError, error } = useIdeas(filters);

  useEffect(() => {
    if (ideas) {
      if (filters.skip === 0 || isNewFilter.current) {
        seenIdeaIds.current = new Set<string>();
        ideas.forEach(idea => seenIdeaIds.current.add(idea.id));
        setAllIdeas(ideas);
        isNewFilter.current = false;
      } else {
        const newIdeas = ideas.filter(idea => !seenIdeaIds.current.has(idea.id));
        newIdeas.forEach(idea => seenIdeaIds.current.add(idea.id));
        if (newIdeas.length > 0) {
          setAllIdeas(prev => [...prev, ...newIdeas]);
        }
      }
    }
  }, [ideas, filters.skip]);

  const applyFilters = (nextFilters: ListParams) => {
    isNewFilter.current = true;
    setFilters(previous => ({
      ...nextFilters,
      skip: 0, // Reset pagination when changing filters
      limit: nextFilters.limit || previous.limit || PAGE_SIZE,
    }));
  };

  const applySearchSuggestion = (suggestion: SearchSuggestion) => {
    const nextFilters = { ...filters };
    delete nextFilters.search;

    if (suggestion.type === 'company') {
      nextFilters.company_id = suggestion.value;
    } else {
      nextFilters.user_id = suggestion.value;
    }

    setSearchQuery(suggestion.label);
    setSearchOpen(false);
    applyFilters(nextFilters);
  };

  const handleSortChange = (selection: SortSelection) => {
    applyFilters({ ...filters, ...sortSelectionToFilters(selection) });
  };

  const handleRemoveFilter = (field: keyof ListParams) => {
    applyFilters(removeFilter(filters, field));
  };

  const handleResetFilters = () => {
    setSearchOpen(false);
    applyFilters({ ...DEFAULT_FILTERS });
  };

  const loadMore = () => {
    setFilters(prev => ({
      ...prev,
      skip: (prev.skip || 0) + (prev.limit || 20),
    }));
  };

  const activeFilterLabels = getActiveFilterLabels(filters);

  return (
    <Box>
      <Box mb={{ base: 8, md: 10 }}>
        <Text
          color="amber.300"
          fontSize="xs"
          fontWeight="bold"
          letterSpacing="0.16em"
          textTransform="uppercase"
          mb={2}
        >
          Investment research
        </Text>
        <Heading size="xl" letterSpacing="-0.03em">{title}</Heading>
        <Text color="whiteAlpha.700" mt={2} maxW="560px">
          Newest theses first. Search fast, refine only when needed.
        </Text>
      </Box>

      <Flex
        align={{ base: 'stretch', md: 'center' }}
        direction={{ base: 'column', md: 'row' }}
        gap={3}
        p={{ base: 3, md: 4 }}
        borderWidth="1px"
        borderColor="whiteAlpha.200"
        borderRadius="xl"
        bg="rgba(13, 22, 38, 0.78)"
      >
        <InputGroup position="relative" flex="1" minW={{ base: '100%', md: '240px' }} zIndex={2}>
          <InputLeftElement pointerEvents="none">
            <SearchIcon color="whiteAlpha.500" />
          </InputLeftElement>
          <Input
            data-testid="company-search"
            aria-label="Search company, ticker, or author"
            value={searchQuery}
            placeholder="Search company, ticker, or author"
            pl={10}
            onChange={event => {
              setSearchQuery(event.target.value);
              setSearchOpen(true);
            }}
            onFocus={() => setSearchOpen(normalizedSearch.length >= 2)}
            onKeyDown={event => {
              if (event.key === 'Escape') {
                setSearchOpen(false);
              }
              if (event.key === 'Enter' && suggestions[0]) {
                event.preventDefault();
                applySearchSuggestion(suggestions[0]);
              }
            }}
          />
          {searchOpen && suggestions.length > 0 && (
            <Box
              role="listbox"
              position="absolute"
              top="calc(100% + 8px)"
              left={0}
              right={0}
              p={1}
              bg="ink.900"
              borderWidth="1px"
              borderColor="whiteAlpha.300"
              borderRadius="lg"
              boxShadow="xl"
            >
              {suggestions.map(suggestion => (
                <Button
                  key={`${suggestion.type}-${suggestion.value}`}
                  data-testid={`${suggestion.type}-option`}
                  role="option"
                  variant="ghost"
                  width="100%"
                  justifyContent="flex-start"
                  fontWeight="normal"
                  onClick={() => applySearchSuggestion(suggestion)}
                >
                  {suggestion.label}
                </Button>
              ))}
            </Box>
          )}
        </InputGroup>

        <Button
          aria-label="Open filters"
          onClick={onOpen}
          color="amber.200"
          borderColor="amber.300"
          variant="outline"
          minW={{ base: '100%', md: '120px' }}
        >
          Filters
          {activeFilterLabels.length > 0 && (
            <Badge ml={2} colorScheme="orange" borderRadius="full">
              {activeFilterLabels.length}
            </Badge>
          )}
        </Button>

        <Select
          aria-label="Sort ideas"
          value={filtersToSortSelection(filters)}
          onChange={event => handleSortChange(event.target.value as SortSelection)}
          maxW={{ base: '100%', md: '170px' }}
        >
          <option value="newest">Newest first</option>
          <option value="oldest">Oldest first</option>
          <option value="performance-desc">Performance high to low</option>
          <option value="performance-asc">Performance low to high</option>
        </Select>
      </Flex>

      {activeFilterLabels.length > 0 && (
        <Flex flexWrap="wrap" gap={2} mt={3}>
          {activeFilterLabels.map(filter => (
            <Tag key={filter.key} size="md" borderRadius="full" bg="ink.800" color="whiteAlpha.800">
              <TagLabel>{filter.label}</TagLabel>
              <TagCloseButton
                aria-label={`Remove ${filter.label}`}
                onClick={() => handleRemoveFilter(filter.key)}
              />
            </Tag>
          ))}
        </Flex>
      )}

      <Flex justify="space-between" align="end" mt={{ base: 8, md: 10 }} mb={3}>
        <Box>
          <Heading as="h2" size="md">Latest ideas</Heading>
          <Text color="whiteAlpha.600" fontSize="sm" mt={1}>Newest theses first</Text>
        </Box>
        <Text color="whiteAlpha.600" fontSize="sm">{allIdeas.length} loaded</Text>
      </Flex>

      {isLoading && allIdeas.length === 0 ? (
        <Flex justify="center" align="center" minH="300px" aria-label="Loading ideas">
          <Spinner size="xl" color="amber.300" />
        </Flex>
      ) : isError ? (
        <Alert status="error" borderRadius="lg">
          <AlertIcon />
          <AlertTitle>Error loading ideas!</AlertTitle>
          <AlertDescription>
            {error ? (error as Error).message || 'An error occurred' : 'Unknown error occurred'}
          </AlertDescription>
        </Alert>
      ) : allIdeas.length > 0 ? (
        <>
          <Box borderTopWidth="1px" borderColor="whiteAlpha.200">
            {allIdeas.map(idea => (
              <IdeaCard
                key={idea.id}
                idea={idea}
                linkBasePath={linkBasePath}
              />
            ))}
          </Box>

          <Flex justify="center" mt={8}>
            <Button
              onClick={loadMore}
              size="lg"
              colorScheme="orange"
              variant="outline"
              isLoading={isLoading}
              loadingText="Loading..."
              isDisabled={isLoading || !ideas || ideas.length === 0}
              data-testid="load-more-button"
            >
              {ideas && ideas.length === 0 ? 'No more ideas' : 'Load more'}
            </Button>
          </Flex>
        </>
      ) : (
        <Box textAlign="center" p={8} borderWidth="1px" borderColor="whiteAlpha.200" borderRadius="lg">
          <Text color="whiteAlpha.800">No investment ideas found matching your criteria.</Text>
        </Box>
      )}

      <IdeasFilterDrawer
        isOpen={isOpen}
        filters={filters}
        onClose={onClose}
        onApply={applyFilters}
        onReset={handleResetFilters}
      />
    </Box>
  );
};

export default IdeasPage;
