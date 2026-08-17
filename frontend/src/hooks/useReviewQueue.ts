import { useQuery } from 'react-query';
import { reviewApi } from '../api/apiService';

export function useIdentityReviewQueue() {
  return useQuery('identity-review-queue', reviewApi.getIdentityQueue, {
    retry: false,
  });
}

export function useQuarantineReviewQueue() {
  return useQuery('quarantine-review-queue', reviewApi.getQuarantineQueue, {
    retry: false,
  });
}
