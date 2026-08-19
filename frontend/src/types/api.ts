export interface Idea {
  id: string;
  link: string;
  company_id: string;
  user_id: string;
  date: string; // ISO date string
  is_short: boolean;
  is_contest_winner: boolean;
}

export interface Company {
  ticker: string;
  company_name: string;
}

export interface User {
  username: string;
  user_link: string;
}

export interface Holding {
  investor_name: string;
  ticker: string;
  company_name: string;
  quarter_date: string;
  shares: number;
  value_usd: number;
  pct_portfolio: number;
  activity: string;
}

export interface CuratedHolding {
  source: 'dataroma' | 'hedgefollow' | string;
  investor_id: string;
  investor_name: string;
  portfolio_manager_name: string | null;
  company_id: string;
  company_name: string;
  security_id: string;
  ticker: string;
  period: string;
  shares: number | null;
  value_usd: number | null;
  pct_portfolio: number | null;
  source_activity: string | null;
  completeness: string;
  source_url: string;
}

export type CrawlStatus = 'running' | 'complete' | 'partial' | 'failed';

export interface CrawlRun {
  id: string | null;
  source: string | null;
  target: string | null;
  status: CrawlStatus | null;
  parser_version: string | null;
  started_at: string | null;
  finished_at: string | null;
  rows_seen: number;
  rows_accepted: number;
  rows_rejected: number;
  rows_duplicate: number;
  error_message: string | null;
}

export interface CrawlCounts {
  parser_output: number;
  staged: number;
  pending_identity: number;
  curated: number;
  public: number;
}

export interface CrawlSample {
  kind: 'holding' | 'idea';
  investor_name?: string | null;
  ticker?: string | null;
  company_name?: string | null;
  period?: string | null;
  idea_date?: string | null;
  shares?: number | null;
  value_usd?: number | null;
  pct_portfolio?: number | null;
  activity?: string | null;
  identity_status?: string | null;
  source_url: string | null;
  link?: string | null;
}

export interface CrawlSourceStatus {
  source: string;
  label: string;
  target: string;
  public_route: string;
  latest_run: CrawlRun;
  counts: CrawlCounts;
  sample: CrawlSample | null;
}

export interface IdentityCandidate {
  id: string;
  entity_type: string;
  source_record_id: string;
  candidate_entity_id: string | null;
  deterministic_score: number | null;
  model_score: number | null;
  evidence_json: Record<string, unknown> | null;
  status: string;
}

export interface QuarantineRecord {
  id: string;
  run_id: string;
  source: string;
  record_type: string;
  source_record_id: string;
  reason_code: string;
  reason_detail: string | null;
  raw_payload: Record<string, unknown> | null;
  review_status: string;
  created_at: string;
  reviewed_at: string | null;
}

export interface Description {
  description: string;
}

export interface Catalysts {
  catalysts: string;
}

export interface Performance {
  // Base performance values
  nextDayOpen: number | null;
  nextDayClose: number | null;
  
  // Traditional performance metrics
  oneWeekClosePerf: number | null;
  twoWeekClosePerf: number | null;
  oneMonthPerf: number | null;
  threeMonthPerf: number | null;
  sixMonthPerf: number | null;
  oneYearPerf: number | null;
  twoYearPerf: number | null;
  threeYearPerf: number | null;
  fiveYearPerf: number | null;
  
  // Timeline data for chart visualization
  timeline_labels?: string[];
  timeline_values?: number[];
  
  // Performance periods as a dictionary for easier access
  performance_periods?: Record<string, number>;
}

export interface IdeaComment {
  id: string;
  author: string;
  posted_at: string;
  text: string;
}

export interface IdeaDetail extends Idea {
  company?: Company;
  user?: User;
  description?: Description;
  catalysts?: Catalysts;
  performance?: Performance;
  comments: IdeaComment[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

export interface ListParams {
  skip?: number;
  limit?: number;
  company_id?: string;
  user_id?: string;
  is_short?: boolean;
  is_contest_winner?: boolean;
  start_date?: string;
  end_date?: string;
  search?: string;
  has_performance?: boolean;
  min_performance?: number;
  max_performance?: number;
  performance_period?: string;
  source?: string;
  investor_id?: string;
  security_id?: string;
  period_start?: string;
  period_end?: string;
  sort_by?: string;
  sort_order?: string;
}
