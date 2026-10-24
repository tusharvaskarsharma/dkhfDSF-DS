import {
  HealthResponse,
  OptionsResponse,
  EvaluationResponse,
  VintageEvolutionResponse,
} from '../types/dashboard';

const API_BASE = '/api/v1';

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) {
    throw new Error(`Health check failed: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchOptions(): Promise<OptionsResponse> {
  const res = await fetch(`${API_BASE}/config/options`);
  if (!res.ok) {
    throw new Error(`Failed to fetch options: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchEvaluation(
  dateFrom: string,
  dateTo: string,
  cutoffType: 'rolling_da' | 'snapshot' | 'latest' = 'rolling_da',
  daCutoffTime: string = '11:00',
  decisionCutoff?: string | null,
  granularity: 'half_hourly' | 'hourly' = 'hourly',
  mode: 'auto' | 'live' | 'demo' = 'auto'
): Promise<EvaluationResponse> {
  const params = new URLSearchParams({
    date_from: dateFrom,
    date_to: dateTo,
    cutoff_type: cutoffType,
    da_cutoff_time: daCutoffTime,
    granularity,
    mode,
  });

  if (decisionCutoff && cutoffType === 'snapshot') {
    params.append('decision_cutoff', decisionCutoff);
  }

  const res = await fetch(`${API_BASE}/evaluation?${params.toString()}`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Evaluation failed: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchVintages(
  deliveryTime: string,
  decisionCutoff?: string | null
): Promise<VintageEvolutionResponse> {
  const params = new URLSearchParams({
    delivery_time: deliveryTime,
  });
  if (decisionCutoff) {
    params.append('decision_cutoff', decisionCutoff);
  }

  const res = await fetch(`${API_BASE}/vintages?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch vintages: HTTP ${res.status}`);
  }
  return res.json();
}

export function getExportCsvUrl(
  dateFrom: string,
  dateTo: string,
  cutoffType: 'rolling_da' | 'snapshot' | 'latest' = 'rolling_da',
  daCutoffTime: string = '11:00',
  decisionCutoff?: string | null,
  granularity: 'half_hourly' | 'hourly' = 'hourly'
): string {
  const params = new URLSearchParams({
    date_from: dateFrom,
    date_to: dateTo,
    cutoff_type: cutoffType,
    da_cutoff_time: daCutoffTime,
    granularity,
  });
  if (decisionCutoff && cutoffType === 'snapshot') {
    params.append('decision_cutoff', decisionCutoff);
  }
  return `${API_BASE}/export?${params.toString()}`;
}

export async function triggerSync(dateFrom: string, dateTo: string): Promise<any> {
  const params = new URLSearchParams({ date_from: dateFrom, date_to: dateTo });
  const res = await fetch(`${API_BASE}/sync?${params.toString()}`, { method: 'POST' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Sync failed: HTTP ${res.status}`);
  }
  return res.json();
}

export async function triggerDemoLoad(): Promise<any> {
  const res = await fetch(`${API_BASE}/demo/load`, { method: 'POST' });
  if (!res.ok) {
    throw new Error(`Failed to load demo fixtures: HTTP ${res.status}`);
  }
  return res.json();
}
