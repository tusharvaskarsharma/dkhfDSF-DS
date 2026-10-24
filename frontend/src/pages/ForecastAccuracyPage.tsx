import React from 'react';
import { EvaluationResponse } from '../types/dashboard';
import { MetricKpiCard } from '../components/MetricKpiCard';
import { ForecastActualChart } from '../components/ForecastActualChart';
import { ErrorAnalysisChart } from '../components/ErrorAnalysisChart';
import { GranularDataTable } from '../components/GranularDataTable';
import { AlertBanner } from '../components/AlertBanner';
import { BookOpen, Calendar } from 'lucide-react';

interface ForecastAccuracyPageProps {
  evaluation: EvaluationResponse | null;
  onSelectInterval: (deliveryTime: string) => void;
}

export const ForecastAccuracyPage: React.FC<ForecastAccuracyPageProps> = ({
  evaluation,
  onSelectInterval,
}) => {
  if (!evaluation) return null;

  const { metrics, intervals, daily_breakdown, quality_flags, decision_cutoff } = evaluation;

  return (
    <div>
      <AlertBanner flags={quality_flags} />

      {/* KPI Cards */}
      <MetricKpiCard metrics={metrics} />

      {/* Main Time Series Chart */}
      <ForecastActualChart
        intervals={intervals}
        decisionCutoff={decision_cutoff}
        onSelectInterval={onSelectInterval}
      />

      {/* Error Deviation Chart */}
      <ErrorAnalysisChart intervals={intervals} />

      {/* Daily Accuracy Breakdown Grid */}
      {daily_breakdown && daily_breakdown.length > 0 && (
        <div className="terminal-card" style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <Calendar size={16} color="var(--wind-cyan)" />
            <div>
              <h2 style={{ fontSize: '0.92rem', fontWeight: 700, color: '#F8FAFC' }}>
                Daily Performance &amp; Accuracy Breakdown
              </h2>
              <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                Granular daily aggregation of MAE, RMSE, Directional Bias, and Paired Settlement Coverage.
              </p>
            </div>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table className="terminal-table">
              <thead>
                <tr>
                  <th>Settlement Date</th>
                  <th>Coverage</th>
                  <th>Valid Pairs</th>
                  <th>MAE</th>
                  <th>RMSE</th>
                  <th>Directional Bias</th>
                  <th>WAPE (%)</th>
                  <th>Avg Actual Gen</th>
                  <th>Avg Forecast Gen</th>
                </tr>
              </thead>
              <tbody>
                {daily_breakdown.map((d) => {
                  const isBiasPos = (d.bias_mw ?? 0) > 0;
                  return (
                    <tr key={d.date}>
                      <td className="tabular" style={{ fontWeight: 600 }}>{d.date}</td>
                      <td>
                        <span className={`badge ${d.coverage_pct >= 95 ? 'badge-emerald' : d.coverage_pct >= 80 ? 'badge-amber' : 'badge-rose'}`}>
                          {d.coverage_pct}%
                        </span>
                      </td>
                      <td className="tabular">{d.valid_pairs} / {d.expected_intervals}</td>
                      <td className="tabular" style={{ fontWeight: 600, color: 'var(--wind-cyan)' }}>
                        {d.mae_mw !== null ? `${d.mae_mw.toLocaleString()} MW` : '—'}
                      </td>
                      <td className="tabular" style={{ color: '#818CF8' }}>
                        {d.rmse_mw !== null ? `${d.rmse_mw.toLocaleString()} MW` : '—'}
                      </td>
                      <td className="tabular">
                        {d.bias_mw !== null ? (
                          <span style={{ fontWeight: 600, color: isBiasPos ? 'var(--error-positive)' : 'var(--error-negative)' }}>
                            {d.bias_mw > 0 ? `+${d.bias_mw.toLocaleString()}` : d.bias_mw.toLocaleString()} MW
                          </span>
                        ) : '—'}
                      </td>
                      <td className="tabular" style={{ color: 'var(--cutoff-amber)' }}>
                        {d.wape_pct !== null ? `${d.wape_pct.toFixed(1)}%` : '—'}
                      </td>
                      <td className="tabular">
                        {d.avg_actual_mw !== null ? `${d.avg_actual_mw.toLocaleString()} MW` : '—'}
                      </td>
                      <td className="tabular">
                        {d.avg_forecast_mw !== null ? `${d.avg_forecast_mw.toLocaleString()} MW` : '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Interval Inspection Table */}
      <GranularDataTable intervals={intervals} onSelectInterval={onSelectInterval} />

      {/* Metric Interpretation Educational Guide */}
      <div className="terminal-card" style={{ borderLeft: '3px solid #818CF8' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.65rem' }}>
          <BookOpen size={16} color="#818CF8" />
          <h3 style={{ fontSize: '0.88rem', fontWeight: 700, color: '#F8FAFC' }}>
            Trader Guidance: Interpreting Forecast Accuracy Metrics
          </h3>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          <div>
            <strong style={{ color: '#F3F4F6' }}>Mean Absolute Error (MAE):</strong> Measures the average magnitude of errors without considering their direction. Lower is better. Unlike RMSE, MAE is not excessively influenced by single outlier hours.
          </div>
          <div>
            <strong style={{ color: '#F3F4F6' }}>Root Mean Squared Error (RMSE):</strong> Squares the deviations before averaging, making it disproportionately sensitive to large forecast misses. High RMSE relative to MAE indicates high error volatility and tail risk.
          </div>
          <div>
            <strong style={{ color: '#F3F4F6' }}>Mean Error (Bias):</strong> Indicates systematic imbalance. A positive bias (+ME) means actual wind generation consistently exceeded forecasts (underforecasting). A negative bias (-ME) means forecasts overpromised generation (overforecasting).
          </div>
          <div>
            <strong style={{ color: '#F3F4F6' }}>WAPE vs. MAPE:</strong> In electricity markets with zero or near-zero calm periods, standard MAPE divides by near-zero values resulting in mathematical divergence. WAPE weights errors by the total volume delivered, providing an economically sound percentage metric.
          </div>
        </div>
      </div>
    </div>
  );
};
