import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MetricKpiCard } from '../components/MetricKpiCard';
import { AlertBanner } from '../components/AlertBanner';
import { GranularDataTable } from '../components/GranularDataTable';
import { TradingControls } from '../components/TradingControls';
import { getExportCsvUrl } from '../services/api';
import { AccuracyMetrics, EvaluationInterval } from '../types/dashboard';

describe('MetricKpiCard Component', () => {
  const sampleMetrics: AccuracyMetrics = {
    mae_mw: 245.5,
    rmse_mw: 312.8,
    bias_mw: 85.2,
    wape_pct: 4.85,
    coverage_pct: 98.5,
    valid_pairs_count: 47,
    expected_intervals_count: 48,
    missing_forecast_count: 1,
    missing_actual_count: 0,
    total_actual_mwh: 240000.0,
    total_forecast_mwh: 235000.0,
    explanation: {
      bias_interpretation: 'Underpredicted actuals on average (+)',
      wape_note: 'WAPE calculated as sum(|e|)/sum(|A|)',
    },
  };

  it('renders all metrics with correct values and units', () => {
    render(<MetricKpiCard metrics={sampleMetrics} />);
    expect(screen.getByText('MAE')).toBeInTheDocument();
    expect(screen.getByText('245.5 MW')).toBeInTheDocument();
    expect(screen.getByText('RMSE')).toBeInTheDocument();
    expect(screen.getByText('312.8 MW')).toBeInTheDocument();
    expect(screen.getByText('BIAS (ME)')).toBeInTheDocument();
    expect(screen.getByText('+85.2 MW')).toBeInTheDocument();
    expect(screen.getByText('WAPE')).toBeInTheDocument();
    expect(screen.getByText('4.85%')).toBeInTheDocument();
    expect(screen.getByText('COVERAGE')).toBeInTheDocument();
    expect(screen.getByText('98.5%')).toBeInTheDocument();
  });

  it('handles null and undefined metrics gracefully without crashing', () => {
    const nullMetrics: AccuracyMetrics = {
      mae_mw: null,
      rmse_mw: null,
      bias_mw: null,
      wape_pct: null,
      coverage_pct: 0.0,
      valid_pairs_count: 0,
      expected_intervals_count: 48,
      missing_forecast_count: 48,
      missing_actual_count: 0,
      total_actual_mwh: null,
      total_forecast_mwh: null,
      explanation: {},
    };
    render(<MetricKpiCard metrics={nullMetrics} />);
    const naElements = screen.getAllByText('N/A');
    expect(naElements.length).toBeGreaterThan(0);
    expect(screen.getByText('0.0%')).toBeInTheDocument();
  });
});

describe('AlertBanner Component', () => {
  it('renders quality warning flags', () => {
    const flags = [
      'LOW_COVERAGE_WARNING: Paired coverage is 75%.',
      'MISSING_FORECASTS: 3 intervals have no eligible forecast before cutoff.',
    ];
    render(<AlertBanner flags={flags} />);
    expect(screen.getByText(flags[0])).toBeInTheDocument();
    expect(screen.getByText(flags[1])).toBeInTheDocument();
  });

  it('renders nothing when flags array is empty', () => {
    const { container } = render(<AlertBanner flags={[]} />);
    expect(container.firstChild).toBeNull();
  });
});

describe('GranularDataTable Component', () => {
  const intervals: EvaluationInterval[] = [
    {
      delivery_time: '2026-01-01T00:00:00Z',
      display_time_london: '2026-01-01 00:00 GMT',
      settlement_date: '2026-01-01',
      settlement_period: 1,
      actual_mw: 15000.0,
      forecast_mw: 14500.0,
      error_mw: 500.0,
      abs_error_mw: 500.0,
      selected_publish_time: '2025-12-31T11:30:00Z',
      lead_time_hours: 12.5,
      status: 'VALID',
    },
    {
      delivery_time: '2026-01-01T00:30:00Z',
      display_time_london: '2026-01-01 00:30 GMT',
      settlement_date: '2026-01-01',
      settlement_period: 2,
      actual_mw: 15200.0,
      forecast_mw: null,
      error_mw: null,
      abs_error_mw: null,
      selected_publish_time: null,
      lead_time_hours: null,
      status: 'MISSING_FORECAST',
    },
  ];

  it('renders intervals and displays status badges', () => {
    const auditMock = vi.fn();
    render(<GranularDataTable intervals={intervals} onSelectInterval={auditMock} />);
    expect(screen.getByText('SP 1')).toBeInTheDocument();
    expect(screen.getByText('15,000 MW')).toBeInTheDocument();
    expect(screen.getByText('14,500 MW')).toBeInTheDocument();
    expect(screen.getByText('+500 MW')).toBeInTheDocument();
    expect(screen.getByText('Valid')).toBeInTheDocument();
    expect(screen.getByText('No Forecast')).toBeInTheDocument();

    const auditButtons = screen.getAllByText('Audit');
    fireEvent.click(auditButtons[0]);
    expect(auditMock).toHaveBeenCalledWith('2026-01-01T00:00:00Z');
  });
});

describe('TradingControls Component', () => {
  it('triggers date and cutoff updates', () => {
    const onDateChange = vi.fn();
    const onCutoffTypeChange = vi.fn();
    const onDaCutoffTimeChange = vi.fn();
    const onCutoffChange = vi.fn();
    const onGranularityChange = vi.fn();
    const onApply = vi.fn();

    render(
      <TradingControls
        dateFrom="2026-01-01"
        dateTo="2026-01-31"
        onDateChange={onDateChange}
        cutoffType="rolling_da"
        onCutoffTypeChange={onCutoffTypeChange}
        daCutoffTime="11:00"
        onDaCutoffTimeChange={onDaCutoffTimeChange}
        decisionCutoff={null}
        onCutoffChange={onCutoffChange}
        granularity="hourly"
        onGranularityChange={onGranularityChange}
        onApply={onApply}
        isLoading={false}
      />
    );

    // Click quick preset Jan 1-5 Benchmark
    const jan15Btn = screen.getByText('Jan 1–5 (Benchmark)');
    fireEvent.click(jan15Btn);
    expect(onDateChange).toHaveBeenCalledWith('2026-01-01', '2026-01-05');

    // Click Recalculate
    const recalcBtn = screen.getByText('Recalculate');
    fireEvent.click(recalcBtn);
    expect(onApply).toHaveBeenCalled();
  });
});

describe('API URL Generator', () => {
  it('constructs correct CSV export URL parameters', () => {
    const url = getExportCsvUrl('2026-01-01', '2026-01-15', 'snapshot', '11:00', '2025-12-31T11:00:00Z', 'hourly');
    expect(url).toContain('date_from=2026-01-01');
    expect(url).toContain('date_to=2026-01-15');
    expect(url).toContain('cutoff_type=snapshot');
    expect(url).toContain('decision_cutoff=2025-12-31T11%3A00%3A00Z');
    expect(url).toContain('granularity=hourly');
  });
});
