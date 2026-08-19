import { validateSchema } from '../types/schema-validator';

describe('schema validation', () => {
  test('validates the API types and crawl status contract', async () => {
    const logSpy = jest.spyOn(console, 'log').mockImplementation();

    try {
      await expect(validateSchema()).resolves.toBe(true);
      expect(logSpy).toHaveBeenCalledWith('Validating CrawlRunResponse...');
      expect(logSpy).toHaveBeenCalledWith('Validating CrawlCountsResponse...');
      expect(logSpy).toHaveBeenCalledWith('Validating CrawlHoldingSampleResponse...');
      expect(logSpy).toHaveBeenCalledWith('Validating CrawlIdeaSampleResponse...');
      expect(logSpy).toHaveBeenCalledWith('Validating CrawlSourceStatusResponse...');
    } finally {
      logSpy.mockRestore();
    }
  });
});
