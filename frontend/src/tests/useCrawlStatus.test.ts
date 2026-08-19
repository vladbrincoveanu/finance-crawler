import { useQuery } from 'react-query';
import { crawlApi } from '../api/apiService';
import { useCrawlStatus } from '../hooks/useCrawlStatus';

jest.mock('react-query', () => ({
  useQuery: jest.fn(),
}));

jest.mock('../api/apiService', () => ({
  crawlApi: {
    getStatus: jest.fn(),
  },
}));

describe('useCrawlStatus', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('overrides the global stale window without enabling polling', () => {
    (useQuery as jest.Mock).mockReturnValue({});

    useCrawlStatus();

    const options = (useQuery as jest.Mock).mock.calls[0][2];
    expect(options).toEqual(expect.objectContaining({
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    }));
    expect(options.refetchInterval).toBeUndefined();
    expect((useQuery as jest.Mock).mock.calls[0][1]).toBe(crawlApi.getStatus);
  });
});
