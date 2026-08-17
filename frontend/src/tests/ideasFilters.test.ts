import {
  DEFAULT_FILTERS,
  filtersToSortSelection,
  getActiveFilterLabels,
  getInitialFilters,
  positionSelectionToFilter,
  booleanSelectionToFilter,
  removeFilter,
  sortSelectionToFilters,
  toQueryString,
} from '../pages/ideasFilters';

describe('ideas filter helpers', () => {
  test('hydrates supported filters from URL search params', () => {
    expect(getInitialFilters('?is_short=true&min_performance=4.5&sort_order=asc&search=ignored'))
      .toEqual({
        ...DEFAULT_FILTERS,
        is_short: true,
        min_performance: 4.5,
        sort_order: 'asc',
      });
  });

  test('ignores invalid numeric values and omits pagination and unsupported search from URL', () => {
    const filters = { ...DEFAULT_FILTERS, min_performance: Number.NaN, search: 'ignored' };

    expect(toQueryString(filters)).toBe('');
  });

  test('preserves false booleans when serializing filters', () => {
    expect(toQueryString({ ...DEFAULT_FILTERS, is_short: false })).toBe('is_short=false');
  });

  test('maps performance sort selection to API params', () => {
    expect(sortSelectionToFilters('performance-asc')).toEqual({
      sort_by: 'performance',
      sort_order: 'asc',
      performance_period: 'one_year_perf',
    });
    expect(filtersToSortSelection({ ...DEFAULT_FILTERS, sort_by: 'date', sort_order: 'asc' }))
      .toBe('oldest');
  });

  test('maps drawer selections to optional boolean filters', () => {
    expect(positionSelectionToFilter('all')).toBeUndefined();
    expect(positionSelectionToFilter('long')).toBe(false);
    expect(positionSelectionToFilter('short')).toBe(true);
    expect(booleanSelectionToFilter('all')).toBeUndefined();
    expect(booleanSelectionToFilter('yes')).toBe(true);
    expect(booleanSelectionToFilter('no')).toBe(false);
  });

  test('removes a filter without mutating the input', () => {
    const filters = { ...DEFAULT_FILTERS, is_short: true };

    expect(removeFilter(filters, 'is_short')).toEqual(DEFAULT_FILTERS);
    expect(filters.is_short).toBe(true);
  });

  test('labels only applied non-pagination filters', () => {
    expect(getActiveFilterLabels({
      ...DEFAULT_FILTERS,
      is_short: true,
      is_contest_winner: false,
      has_performance: true,
    })).toEqual([
      { key: 'is_short', label: 'Short ideas' },
      { key: 'is_contest_winner', label: 'Not contest winners' },
      { key: 'has_performance', label: 'Performance tracked' },
    ]);
  });
});
