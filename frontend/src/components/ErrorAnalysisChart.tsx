import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
  Cell,
} from 'recharts';
import { EvaluationInterval } from '../types/dashboard';

interface ErrorAnalysisChartProps {
  intervals: EvaluationInterval[];
}

export const ErrorAnalysisChart: React.FC<ErrorAnalysisChartProps> = ({ intervals }) => {
  const chartData = intervals
    .filter((it) => it.error_mw !== null && it.error_mw !== undefined)
    .map((it) => {
      const timeParts = it.display_time_london.split(' ');
      const dateParts = timeParts[0]?.split('-') || [];
      const shortLabel = `${dateParts[2]}/${dateParts[1]} ${timeParts[1]}`;

      return {
        delivery_time: it.delivery_time,
        display_time_london: it.display_time_london,
        shortLabel,
        settlement_period: it.settlement_period,
        error_mw: it.error_mw,
        abs_error_mw: it.abs_error_mw,
        actual_mw: it.actual_mw,
        forecast_mw: it.forecast_mw,
      };
    });

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || !payload.length) return null;
    const d = payload[0].payload;
    const isUnderforecast = (d.error_mw ?? 0) > 0;

    return (
      <div style={{
        background: 'rgba(11, 16, 26, 0.95)',
        backdropFilter: 'blur(12px)',
        border: '1px solid rgba(255, 255, 255, 0.12)',
        borderRadius: 'var(--radius-sm)',
        padding: '0.65rem 0.85rem',
        fontSize: '0.74rem',
      }}>
        <div style={{ fontWeight: 600, color: '#F3F4F6', marginBottom: '0.25rem' }}>
          {d.display_time_london} {d.settlement_period ? `(SP ${d.settlement_period})` : ''}
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
          <span style={{ color: 'var(--text-muted)' }}>Forecast Error:</span>
          <span className="tabular" style={{
            fontWeight: 700,
            color: isUnderforecast ? 'var(--error-positive)' : 'var(--error-negative)',
          }}>
            {d.error_mw > 0 ? `+${d.error_mw.toLocaleString()}` : d.error_mw.toLocaleString()} MW
          </span>
        </div>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-faint)', marginTop: '0.2rem' }}>
          {isUnderforecast ? 'Actual exceeded forecast (system was short)' : 'Actual below forecast (system was long)'}
        </div>
      </div>
    );
  };

  return (
    <div className="terminal-card" style={{ marginBottom: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '0.92rem', fontWeight: 700, color: '#F8FAFC' }}>
            Forecast Deviation &amp; Error Over Time (e_t = A_t - F_t)
          </h2>
          <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
            Green bars indicate actual generation exceeded forecast (+ underprediction). Red bars indicate generation fell short (- overprediction).
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.72rem' }}>
          <span style={{ color: 'var(--error-positive)' }}>+ Underforecast (Short)</span>
          <span style={{ color: 'var(--error-negative)' }}>- Overforecast (Long)</span>
        </div>
      </div>

      <div style={{ width: '100%', height: 260 }}>
        <ResponsiveContainer>
          <BarChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.05)" />
            <XAxis
              dataKey="shortLabel"
              stroke="#6B7280"
              fontSize={11}
              tickLine={false}
              interval="preserveStartEnd"
              minTickGap={45}
            />
            <YAxis
              stroke="#6B7280"
              fontSize={11}
              tickLine={false}
              tickFormatter={(v) => `${(v / 1000).toFixed(1)}k`}
              label={{ value: 'Error (MW)', angle: -90, position: 'insideLeft', fill: '#6B7280', fontSize: 11 }}
            />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine y={0} stroke="rgba(255, 255, 255, 0.2)" strokeWidth={1} />
            <Bar dataKey="error_mw" isAnimationActive={false}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={(entry.error_mw ?? 0) >= 0 ? '#34D399' : '#F43F5E'}
                  opacity={0.85}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
