import React from 'react';
import { Alert, AlertIcon, Badge, Box, Button, Heading, SimpleGrid, Text } from '@chakra-ui/react';
import { useQuarantineReviewQueue } from '../hooks/useReviewQueue';
import { reviewApi } from '../api/apiService';

const QuarantineReviewPage: React.FC = () => {
  const query = useQuarantineReviewQueue();
  const records = query.data ?? [];

  const reprocess = async (id: string) => {
    await reviewApi.reprocessQuarantine(id);
    await query.refetch();
  };

  return (
    <Box>
      <Text color="orange.200" fontSize="xs" letterSpacing="0.2em" textTransform="uppercase">Human gate / data quality</Text>
      <Heading mt={3} color="white" fontSize={{ base: '3xl', md: '5xl' }} letterSpacing="-0.05em">Quarantine review</Heading>
      <Text mt={3} color="whiteAlpha.700" maxW="680px">Malformed or incomplete source material stays visible to operators and invisible to public curated views.</Text>
      {query.isError && <Alert status="warning" mt={8} borderRadius="16px"><AlertIcon />Add a review token to load the protected queue.</Alert>}
      {!query.isLoading && !query.isError && !records.length && (
        <Box mt={10} border="1px solid" borderColor="whiteAlpha.200" bg="whiteAlpha.50" borderRadius="20px" p={10} textAlign="center">
          <Text color="green.300" fontWeight="700">No open quarantine records</Text>
        </Box>
      )}
      <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={4} mt={8}>
        {records.map((record) => (
          <Box key={record.id} border="1px solid" borderColor="whiteAlpha.200" bg="whiteAlpha.50" borderRadius="18px" p={6}>
            <Badge colorScheme="orange" borderRadius="full">{record.reason_code}</Badge>
            <Text mt={4} color="white" fontWeight="700">{record.source} · {record.record_type}</Text>
            <Text mt={2} color="whiteAlpha.600" fontSize="sm">{record.reason_detail ?? 'No detail provided.'}</Text>
            <Button mt={5} size="sm" colorScheme="orange" onClick={() => void reprocess(record.id)}>Mark for reprocess</Button>
          </Box>
        ))}
      </SimpleGrid>
    </Box>
  );
};

export default QuarantineReviewPage;
