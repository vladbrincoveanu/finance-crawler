import { ListParams } from '../types/api';

export const PAGE_SIZE = 20;
export const DEFAULT_FILTERS: ListParams = { skip: 0, limit: PAGE_SIZE };

export type SortSelection = 'newest' | 'oldest' | 'performance-desc' | 'performance-asc';
export type PositionSelection = 'all' | 'long' | 'short';
export type BooleanSelection = 'all' | 'yes' | 'no';

export interface ActiveFilterLabel {
  key: keyof ListParams;
  label: string;
}

export const PERFORMANCE_PERIOD_LABELS: Record<string, string> = {
  one_week_perf: '1 week',
  two_week_perf: '2 weeks',
  one_month_perf: '1 month',
  three_month_perf: '3 months',
  six_month_perf: '6 months',
  one_year_perf: '1 year',
  two_year_perf: '2 years',
  three_year_perf: '3 years',
  five_year_perf: '5 years',
};

const STRING_FILTER_KEYS: Array<keyof ListParams> = [
  'company_id',
  'user_id',
  'start_date',
  'end_date',
  'performance_period',
  'source',
  'investor_id',
  'security_id',
  'period_start',
  'period_end',
  'sort_by',
  'sort_order',
];

const parseOptionalBoolean = (value: string | null): boolean | undefined => {
  if (value === 'true') return true;
  if (value === 'false') return false;
  return undefined;
};

const parseOptionalNumber = (value: string | null): number | undefined => {
  if (value === null || value.trim() === '') return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
};

export function getInitialFilters(search: string): ListParams {
  const params = new URLSearchParams(search);
  const filters: ListParams = { ...DEFAULT_FILTERS };

  STRING_FILTER_KEYS.forEach(key => {
    const value = params.get(key);
    if (value) {
      (filters as Record<string, unknown>)[key] = value;
    }
  });

  const isShort = parseOptionalBoolean(params.get('is_short'));
  const isContestWinner = parseOptionalBoolean(params.get('is_contest_winner'));
  const hasPerformance = parseOptionalBoolean(params.get('has_performance'));
  const minPerformance = parseOptionalNumber(params.get('min_performance'));
  const maxPerformance = parseOptionalNumber(params.get('max_performance'));

  if (isShort !== undefined) filters.is_short = isShort;
  if (isContestWinner !== undefined) filters.is_contest_winner = isContestWinner;
  if (hasPerformance !== undefined) filters.has_performance = hasPerformance;
  if (minPerformance !== undefined) filters.min_performance = minPerformance;
  if (maxPerformance !== undefined) filters.max_performance = maxPerformance;

  return filters;
}

export function toQueryString(filters: ListParams): string {
  const params = new URLSearchParams();

  Object.entries(filters).forEach(([key, value]) => {
    if (
      key === 'skip' ||
      key === 'limit' ||
      key === 'search' ||
      value === undefined ||
      value === null ||
      value === '' ||
      (typeof value === 'number' && !Number.isFinite(value))
    ) {
      return;
    }

    params.set(key, String(value));
  });

  return params.toString();
}

export function removeFilter(filters: ListParams, field: keyof ListParams): ListParams {
  const nextFilters = { ...filters };
  delete nextFilters[field];
  return nextFilters;
}

export function sortSelectionToFilters(
  selection: SortSelection,
): Pick<ListParams, 'sort_by' | 'sort_order' | 'performance_period'> {
  switch (selection) {
    case 'oldest':
      return { sort_by: 'date', sort_order: 'asc' };
    case 'performance-desc':
      return {
        sort_by: 'performance',
        sort_order: 'desc',
        performance_period: 'one_year_perf',
      };
    case 'performance-asc':
      return {
        sort_by: 'performance',
        sort_order: 'asc',
        performance_period: 'one_year_perf',
      };
    case 'newest':
    default:
      return { sort_by: 'date', sort_order: 'desc' };
  }
}

export function filtersToSortSelection(filters: ListParams): SortSelection {
  if (filters.sort_by === 'performance') {
    return filters.sort_order === 'asc' ? 'performance-asc' : 'performance-desc';
  }

  return filters.sort_order === 'asc' ? 'oldest' : 'newest';
}

export function positionSelectionToFilter(selection: PositionSelection): boolean | undefined {
  if (selection === 'long') return false;
  if (selection === 'short') return true;
  return undefined;
}

export function booleanSelectionToFilter(selection: BooleanSelection): boolean | undefined {
  if (selection === 'yes') return true;
  if (selection === 'no') return false;
  return undefined;
}

export function getActiveFilterLabels(filters: ListParams): ActiveFilterLabel[] {
  const labels: ActiveFilterLabel[] = [];

  if (filters.company_id) {
    labels.push({ key: 'company_id', label: `Company: ${filters.company_id}` });
  }
  if (filters.user_id) {
    labels.push({ key: 'user_id', label: `Author: ${filters.user_id}` });
  }
  if (filters.is_short !== undefined) {
    labels.push({
      key: 'is_short',
      label: filters.is_short ? 'Short ideas' : 'Long ideas',
    });
  }
  if (filters.is_contest_winner !== undefined) {
    labels.push({
      key: 'is_contest_winner',
      label: filters.is_contest_winner ? 'Contest winners' : 'Not contest winners',
    });
  }
  if (filters.has_performance !== undefined) {
    labels.push({
      key: 'has_performance',
      label: filters.has_performance ? 'Performance tracked' : 'Performance untracked',
    });
  }
  if (filters.min_performance !== undefined) {
    labels.push({ key: 'min_performance', label: `Min performance: ${filters.min_performance}%` });
  }
  if (filters.max_performance !== undefined) {
    labels.push({ key: 'max_performance', label: `Max performance: ${filters.max_performance}%` });
  }
  if (filters.performance_period) {
    labels.push({
      key: 'performance_period',
      label: `Period: ${PERFORMANCE_PERIOD_LABELS[filters.performance_period] || filters.performance_period}`,
    });
  }

  return labels;
}
