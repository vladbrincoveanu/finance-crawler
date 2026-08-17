import React from 'react';
import { Alert, AlertIcon, Badge, Box, Button, Heading, SimpleGrid, Text } from '@chakra-ui/react';
import { useIdentityReviewQueue } from '../hooks/useReviewQueue';

const IdentityReviewPage: React.FC = () => {
  const query = useIdentityReviewQueue();
  const candidates = query.data ?? [];

  return (
    <Box>
      <Text color="purple.200" fontSize="xs" letterSpacing="0.2em" textTransform="uppercase">Human gate / identity queue</Text>
      <Heading mt={3} color="white" fontSize={{ base: '3xl', md: '5xl' }} letterSpacing="-0.05em">Identity review</Heading>
      <Text mt={3} color="whiteAlpha.700" maxW="680px">Deterministic candidates and model suggestions are evidence for a reviewer, never automatic merges.</Text>
      {query.isError && <Alert status="warning" mt={8} borderRadius="16px"><AlertIcon />Add a review token to load the protected queue.</Alert>}
      {!query.isLoading && !query.isError && !candidates.length && (
        <Box mt={10} border="1px solid" borderColor="whiteAlpha.200" bg="whiteAlpha.50" borderRadius="20px" p={10} textAlign="center">
          <Text color="green.300" fontWeight="700">Queue is clear</Text>
          <Text mt={2} color="whiteAlpha.600">No unresolved identity candidates are waiting for review.</Text>
        </Box>
      )}
      <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={4} mt={8}>
        {candidates.map((candidate) => (
          <Box key={candidate.id} border="1px solid" borderColor="whiteAlpha.200" bg="whiteAlpha.50" borderRadius="18px" p={6}>
            <Badge colorScheme="purple" borderRadius="full">{candidate.entity_type}</Badge>
            <Text mt={4} color="white" fontWeight="700">Source record {candidate.source_record_id}</Text>
            <Text mt={2} color="whiteAlpha.600" fontSize="sm">Candidate {candidate.candidate_entity_id ?? 'none selected'}</Text>
            <Text mt={4} color="whiteAlpha.500" fontSize="xs">Deterministic score: {candidate.deterministic_score ?? 'pending'}</Text>
            <Button mt={5} size="sm" variant="outline" color="purple.200" borderColor="purple.300" isDisabled>Review in protected console</Button>
          </Box>
        ))}
      </SimpleGrid>
    </Box>
  );
};

export default IdentityReviewPage;
