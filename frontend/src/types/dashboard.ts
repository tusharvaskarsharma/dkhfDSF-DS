export interface AccuracyMetrics {
  mae_mw: number | null;
  rmse_mw: number | null;
  bias_mw: number | null;
  wape_pct: number | null;
  coverage_pct: number;
  valid_pairs_count: number;
  expected_intervals_count: number;
  missing_forecast_count: number;
  missing_actual_count: number;
  total_actual_mwh?: number | null;
  total_forecast_mwh?: number | null;
  explanation: Record<string, string>;
}

export interface EvaluationInterval {
  delivery_time: string;
  display_time_london: string;
  settlement_date: string;
  settlement_period: number | null;
  actual_mw: number | null;
  forecast_mw: number | null;
  error_mw: number | null;
  abs_error_mw: number | null;
  selected_publish_time: string | null;
  lead_time_hours: number | null;
  status: 'VALID' | 'MISSING_FORECAST' | 'MISSING_ACTUAL' | 'MISSING_BOTH';
}

export interface DailyMetric {
  date: string;
  valid_pairs: number;
  expected_intervals: number;
  coverage_pct: number;
  mae_mw: number | null;
  rmse_mw: number | null;
  bias_mw: number | null;
  wape_pct: number | null;
  avg_actual_mw: number | null;
  avg_forecast_mw: number | null;
}

export interface EvaluationResponse {
  date_from: string;
  date_to: string;
  cutoff_type: 'rolling_da' | 'snapshot' | 'latest';
  da_cutoff_time: string;
  decision_cutoff: string | null;
  granularity: 'half_hourly' | 'hourly';
  alignment_method?: string;
  metrics: AccuracyMetrics;
  intervals: EvaluationInterval[];
  daily_breakdown: DailyMetric[];
  quality_flags: string[];
  last_updated: string;
  data_source_mode: 'LIVE' | 'FIXTURE_DEMO';
}

export interface VintageItem {
  publish_time: string;
  display_publish_london: string;
  generation_mw: number;
  lead_time_hours: number;
  is_eligible_before_cutoff: boolean;
  is_selected: boolean;
  is_ex_post?: boolean;
}

export interface VintageEvolutionResponse {
  delivery_time: string;
  display_time_london: string;
  settlement_date: string | null;
  settlement_period: number | null;
  actual_mw: number | null;
  decision_cutoff: string | null;
  selected_publish_time: string | null;
  selected_forecast_mw: number | null;
  vintages: VintageItem[];
  missing_vintage_warning: string | null;
}

export interface HealthResponse {
  status: string;
  elexon_api_connected: boolean;
  elexon_latency_ms: number | null;
  database_connected: boolean;
  cached_forecast_count: number;
  cached_actual_count: number;
  available_date_range_actuals?: { min: string; max: string } | null;
  available_date_range_forecasts?: { min: string; max: string } | null;
  last_sync_time: string | null;
  server_time_utc: string;
}

export interface CutoffPreset {
  id: string;
  label: string;
  description: string;
}

export interface OptionsResponse {
  default_date_from: string;
  default_date_to: string;
  available_cutoff_presets: CutoffPreset[];
  datasets: Array<Record<string, string>>;
}
