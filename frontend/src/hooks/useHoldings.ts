import { useQuery, UseQueryOptions } from 'react-query';
import { holdingsApi } from '../api/apiService';
import { Holding, ListParams } from '../types/api';

export function useHoldings(params: ListParams = {}, options?: UseQueryOptions<Holding[]>) {
  return useQuery<Holding[]>(
    ['holdings', params],
    () => holdingsApi.getHoldings(params),
    options
  );
}
