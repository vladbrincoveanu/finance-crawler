import { useQuery, UseQueryOptions } from 'react-query';
import { crawlApi } from '../api/apiService';
import { CrawlSourceStatus } from '../types/api';

export function useCrawlStatus(options?: UseQueryOptions<CrawlSourceStatus[]>) {
  return useQuery<CrawlSourceStatus[]>(
    ['crawl-status'],
    crawlApi.getStatus,
    { refetchOnWindowFocus: false, staleTime: 30_000, ...options },
  );
}
