import React from 'react';
import { AccuracyMetrics } from '../types/dashboard';
import { HelpCircle, TrendingUp, TrendingDown, CheckCircle2, AlertTriangle } from 'lucide-react';

interface MetricKpiCardProps {
  metrics: AccuracyMetrics;
}

export const MetricKpiCard: React.FC<MetricKpiCardProps> = ({ metrics }) => {
  const isBiasPositive = (metrics.bias_mw ?? 0) > 0;
  const isCoverageGood = metrics.coverage_pct >= 90;

  const cards = [
    {
      title: 'MAE',
      subtitle: 'Mean Absolute Error',
      value: metrics.mae_mw !== null ? `${metrics.mae_mw.toLocaleString()} MW` : 'N/A',
      secondary: 'Average absolute magnitude of forecast error',
      accent: 'var(--wind-cyan)',
      tooltip: 'MAE = (1/N) * sum(|Actual - Forecast|). Robust linear error metric.',
    },
    {
      title: 'RMSE',
      subtitle: 'Root Mean Squared Error',
      value: metrics.rmse_mw !== null ? `${metrics.rmse_mw.toLocaleString()} MW` : 'N/A',
      secondary: 'Penalizes large tail dispatch misses',
      accent: '#818CF8',
      tooltip: 'RMSE = sqrt((1/N) * sum((Actual - Forecast)^2)). Heavily weights extreme forecasting errors.',
    },
    {
      title: 'BIAS (ME)',
      subtitle: 'Mean Directional Error',
      value: metrics.bias_mw !== null ? `${metrics.bias_mw > 0 ? '+' : ''}${metrics.bias_mw.toLocaleString()} MW` : 'N/A',
      secondary: metrics.explanation?.bias_interpretation || (isBiasPositive ? 'Underforecast (+)' : 'Overforecast (-)'),
      accent: isBiasPositive ? 'var(--error-positive)' : 'var(--error-negative)',
      icon: isBiasPositive ? TrendingUp : TrendingDown,
      tooltip: 'ME = (1/N) * sum(Actual - Forecast). Positive means generation exceeded forecast; negative means generation fell short.',
    },
    {
      title: 'WAPE',
      subtitle: 'Weighted Abs % Error',
      value: metrics.wape_pct !== null ? `${metrics.wape_pct.toFixed(2)}%` : 'N/A',
      secondary: metrics.explanation?.wape_note || 'Weighted by total actual volume',
      accent: 'var(--cutoff-amber)',
      tooltip: 'WAPE = sum(|Actual - Forecast|) / sum(|Actual|) * 100%. Avoids zero-division distortion of standard MAPE.',
    },
    {
      title: 'COVERAGE',
      subtitle: 'Data Completeness',
      value: `${metrics.coverage_pct.toFixed(1)}%`,
      secondary: `${metrics.valid_pairs_count} / ${metrics.expected_intervals_count} paired intervals`,
      accent: isCoverageGood ? 'var(--actual-emerald)' : 'var(--cutoff-amber)',
      icon: isCoverageGood ? CheckCircle2 : AlertTriangle,
      tooltip: 'Percentage of expected delivery intervals having both a valid actual and an eligible forecast before the cutoff.',
    },
    {
      title: 'ACTUAL VOLUME',
      subtitle: 'Total Energy Generation',
      value: metrics.total_actual_mwh !== null && metrics.total_actual_mwh !== undefined ? `${(metrics.total_actual_mwh / 1000).toFixed(1)} GWh` : 'N/A',
      secondary: metrics.total_forecast_mwh ? `Forecast: ${(metrics.total_forecast_mwh / 1000).toFixed(1)} GWh` : 'GB Transmission Grid',
      accent: 'var(--actual-emerald)',
      tooltip: 'Total actual wind energy delivered to GB transmission system in the selected period (MWh converted to GWh).',
    },
  ];

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
      gap: '1rem',
      marginBottom: '1.5rem',
    }}>
      {cards.map((card, i) => {
        const Icon = card.icon;
        return (
          <div key={i} className="terminal-card" style={{ position: 'relative', overflow: 'hidden' }}>
            {/* Top accent glow line */}
            <div style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              height: '2px',
              background: card.accent,
              boxShadow: `0 0 10px ${card.accent}`,
            }} />

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <span style={{ fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.06em', color: card.accent }}>
                  {card.title}
                </span>
                <span title={card.tooltip} style={{ cursor: 'help', color: 'var(--text-faint)' }}>
                  <HelpCircle size={12} />
                </span>
              </div>
              {Icon && <Icon size={14} color={card.accent} />}
            </div>

            <div className="tabular" style={{ fontSize: '1.45rem', fontWeight: 700, color: '#F8FAFC', marginBottom: '0.2rem' }}>
              {card.value}
            </div>

            <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
              {card.subtitle}
            </div>

            <div style={{
              fontSize: '0.68rem',
              color: 'var(--text-faint)',
              marginTop: '0.35rem',
              paddingTop: '0.35rem',
              borderTop: '1px solid rgba(255, 255, 255, 0.04)',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}>
              {card.secondary}
            </div>
          </div>
        );
      })}
    </div>
  );
};
