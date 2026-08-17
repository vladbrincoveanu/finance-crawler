import { useQuery, UseQueryOptions } from 'react-query';
import { holdingsApi } from '../api/apiService';
import { CuratedHolding, ListParams } from '../types/api';

export function useCuratedHoldings(
  params: ListParams = {},
  options?: UseQueryOptions<CuratedHolding[]>,
) {
  return useQuery<CuratedHolding[]>(
    ['curated-holdings', params],
    () => holdingsApi.getHoldings(params),
    options,
  );
}
