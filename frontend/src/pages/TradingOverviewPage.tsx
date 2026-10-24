import React from 'react';
import { EvaluationResponse, HealthResponse } from '../types/dashboard';
import { MetricKpiCard } from '../components/MetricKpiCard';
import { ForecastActualChart } from '../components/ForecastActualChart';
import { AlertBanner } from '../components/AlertBanner';
import { Clock, Zap, Info, Activity } from 'lucide-react';

interface TradingOverviewPageProps {
  evaluation: EvaluationResponse | null;
  health: HealthResponse | null;
  onSelectInterval: (deliveryTime: string) => void;
}

export const TradingOverviewPage: React.FC<TradingOverviewPageProps> = ({
  evaluation,
  health,
  onSelectInterval,
}) => {
  if (!evaluation) return null;

  const { metrics, intervals, quality_flags, date_from, date_to, decision_cutoff } = evaluation;

  const validActuals = intervals.filter((it) => it.actual_mw !== null && it.actual_mw !== undefined);
  const latestActual = validActuals.length > 0 ? validActuals[validActuals.length - 1] : null;

  const validForecasts = intervals.filter((it) => it.forecast_mw !== null && it.forecast_mw !== undefined);
  const latestForecast = validForecasts.length > 0 ? validForecasts[validForecasts.length - 1] : null;

  const isBiasPositive = (metrics.bias_mw ?? 0) > 0;

  return (
    <div>
      <AlertBanner flags={quality_flags} />

      {/* Top Trading Snapshot Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: '1rem',
        marginBottom: '1.25rem',
      }}>
        {/* Latest Eligible Forecast */}
        <div className="terminal-card" style={{ borderLeft: '3px solid var(--wind-cyan)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
            <span style={{ fontSize: '0.74rem', fontWeight: 600, color: 'var(--wind-cyan)', textTransform: 'uppercase' }}>
              Latest Eligible Forecast (WINDFOR)
            </span>
            <Zap size={15} color="var(--wind-cyan)" />
          </div>
          <div className="tabular" style={{ fontSize: '1.75rem', fontWeight: 700, color: '#F8FAFC' }}>
            {latestForecast?.forecast_mw !== null && latestForecast?.forecast_mw !== undefined
              ? `${latestForecast.forecast_mw.toLocaleString()} MW`
              : 'N/A'}
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            Delivery: {latestForecast?.display_time_london || '—'} {latestForecast?.settlement_period ? `(SP ${latestForecast.settlement_period})` : ''}
          </div>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-faint)', marginTop: '0.2rem' }}>
            Pub Time: {latestForecast?.selected_publish_time || 'Latest before cutoff'}
          </div>
        </div>

        {/* Latest Available Actual */}
        <div className="terminal-card" style={{ borderLeft: '3px solid var(--actual-emerald)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
            <span style={{ fontSize: '0.74rem', fontWeight: 600, color: 'var(--actual-emerald)', textTransform: 'uppercase' }}>
              Latest Outturn Actual (FUELHH)
            </span>
            <Activity size={15} color="var(--actual-emerald)" />
          </div>
          <div className="tabular" style={{ fontSize: '1.75rem', fontWeight: 700, color: '#F8FAFC' }}>
            {latestActual?.actual_mw !== null && latestActual?.actual_mw !== undefined
              ? `${latestActual.actual_mw.toLocaleString()} MW`
              : 'N/A'}
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            Delivery: {latestActual?.display_time_london || '—'} {latestActual?.settlement_period ? `(SP ${latestActual.settlement_period})` : ''}
          </div>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-faint)', marginTop: '0.2rem' }}>
            Source: FUELHH Metered Output {health?.elexon_latency_ms ? `(${health.elexon_latency_ms}ms)` : ''}
          </div>
        </div>

        {/* Decision Cutoff Boundary Status */}
        <div className="terminal-card" style={{ borderLeft: '3px solid var(--cutoff-amber)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
            <span style={{ fontSize: '0.74rem', fontWeight: 600, color: 'var(--cutoff-amber)', textTransform: 'uppercase' }}>
              Decision Cutoff Status
            </span>
            <Clock size={15} color="var(--cutoff-amber)" />
          </div>
          <div style={{ fontSize: '1.15rem', fontWeight: 700, color: '#F8FAFC', margin: '0.25rem 0' }}>
            {decision_cutoff ? (
              <span className="tabular">{decision_cutoff}</span>
            ) : (
              'Latest Available (Dynamic)'
            )}
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
            {decision_cutoff ? 'Strict point-in-time gate closure active' : 'No vintage cutoff applied; using latest pre-delivery runs'}
          </div>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-faint)', marginTop: '0.2rem' }}>
            Look-Ahead Protection: Guaranteed Zero Future Leakage
          </div>
        </div>
      </div>

      {/* Accuracy KPI Cards */}
      <MetricKpiCard metrics={metrics} />

      {/* Main Interactive Forecast vs Actual Chart */}
      <ForecastActualChart
        intervals={intervals}
        decisionCutoff={decision_cutoff}
        onSelectInterval={onSelectInterval}
      />

      {/* Executive Analytical Summary */}
      <div className="terminal-card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.65rem' }}>
          <Info size={16} color="var(--wind-cyan)" />
          <h3 style={{ fontSize: '0.88rem', fontWeight: 700, color: '#F8FAFC' }}>
            Period Analytical Evaluation Summary ({date_from} to {date_to})
          </h3>
        </div>
        <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
          During the evaluation period from <strong style={{ color: '#F3F4F6' }}>{date_from}</strong> to <strong style={{ color: '#F3F4F6' }}>{date_to}</strong>,
          wind forecasts achieved a Mean Absolute Error (MAE) of <strong style={{ color: 'var(--wind-cyan)' }}>{metrics.mae_mw?.toLocaleString() ?? 'N/A'} MW</strong> and
          a Root Mean Squared Error (RMSE) of <strong style={{ color: '#818CF8' }}>{metrics.rmse_mw?.toLocaleString() ?? 'N/A'} MW</strong> across {metrics.valid_pairs_count} paired delivery intervals.
          The average bias was <strong style={{ color: isBiasPositive ? 'var(--error-positive)' : 'var(--error-negative)' }}>
            {metrics.bias_mw !== null ? `${metrics.bias_mw > 0 ? '+' : ''}${metrics.bias_mw.toLocaleString()} MW` : 'N/A'}
          </strong> ({metrics.explanation?.bias_interpretation}).
          Data coverage stands at <strong style={{ color: metrics.coverage_pct >= 90 ? 'var(--actual-emerald)' : 'var(--cutoff-amber)' }}>{metrics.coverage_pct}%</strong> of expected settlement periods.
        </p>
      </div>
    </div>
  );
};
