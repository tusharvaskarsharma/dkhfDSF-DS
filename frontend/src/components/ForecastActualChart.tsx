import React from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { EvaluationInterval } from '../types/dashboard';

interface ForecastActualChartProps {
  intervals: EvaluationInterval[];
  decisionCutoff?: string | null;
  onSelectInterval?: (deliveryTime: string) => void;
}

export const ForecastActualChart: React.FC<ForecastActualChartProps> = ({
  intervals,
  decisionCutoff: _decisionCutoff,
  onSelectInterval,
}) => {
  // Format data for chart display
  const chartData = intervals.map((it) => {
    const timeParts = it.display_time_london.split(' ');
    const dateParts = timeParts[0]?.split('-') || [];
    const shortLabel = `${dateParts[2]}/${dateParts[1]} ${timeParts[1]}`;

    return {
      delivery_time: it.delivery_time,
      display_time_london: it.display_time_london,
      shortLabel,
      settlement_period: it.settlement_period,
      actual: it.actual_mw,
      forecast: it.forecast_mw,
      error: it.error_mw,
      publish_time: it.selected_publish_time,
      lead_time: it.lead_time_hours,
      status: it.status,
    };
  });

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || !payload.length) return null;
    const data = payload[0].payload;
    const isErrorPos = (data.error ?? 0) > 0;

    return (
      <div style={{
        background: 'rgba(11, 16, 26, 0.95)',
        backdropFilter: 'blur(12px)',
        border: '1px solid rgba(255, 255, 255, 0.12)',
        borderRadius: 'var(--radius-sm)',
        padding: '0.75rem 1rem',
        boxShadow: '0 10px 25px rgba(0,0,0,0.6)',
        fontSize: '0.75rem',
        minWidth: '220px',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '0.3rem' }}>
          <span style={{ fontWeight: 600, color: '#F3F4F6' }}>
            {data.display_time_london}
          </span>
          {data.settlement_period && (
            <span className="badge badge-muted">SP {data.settlement_period}</span>
          )}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#10B981', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#10B981' }} />
              Actual (FUELHH):
            </span>
            <span className="tabular" style={{ fontWeight: 600 }}>
              {data.actual !== null && data.actual !== undefined ? `${data.actual.toLocaleString()} MW` : 'N/A'}
            </span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#38BDF8', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#38BDF8' }} />
              Forecast (WINDFOR):
            </span>
            <span className="tabular" style={{ fontWeight: 600 }}>
              {data.forecast !== null && data.forecast !== undefined ? `${data.forecast.toLocaleString()} MW` : 'N/A'}
            </span>
          </div>

          {data.error !== null && data.error !== undefined && (
            <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px dashed rgba(255,255,255,0.08)', paddingTop: '0.3rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>Error (Act - Fc):</span>
              <span className="tabular" style={{ fontWeight: 600, color: isErrorPos ? 'var(--error-positive)' : 'var(--error-negative)' }}>
                {data.error > 0 ? `+${data.error.toLocaleString()}` : data.error.toLocaleString()} MW
              </span>
            </div>
          )}

          {data.lead_time !== null && data.lead_time !== undefined && (
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-faint)' }}>
              <span>Lead Time:</span>
              <span className="tabular">{data.lead_time} hrs ahead</span>
            </div>
          )}

          {data.status !== 'VALID' && (
            <div style={{ marginTop: '0.2rem' }}>
              <span className="badge badge-amber">{data.status}</span>
            </div>
          )}
        </div>

        {onSelectInterval && (
          <div style={{ marginTop: '0.5rem', fontSize: '0.68rem', color: 'var(--wind-cyan)', textAlign: 'center' }}>
            Click point to audit vintage evolution &rarr;
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="terminal-card" style={{ marginBottom: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '0.92rem', fontWeight: 700, color: '#F8FAFC' }}>
            GB Wind Generation: Actual vs. Forecast Profile
          </h2>
          <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
            FUELHH Actuals (solid emerald) vs. WINDFOR Selected Forecast (dashed cyan). Units in MW.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.75rem', color: '#10B981' }}>
            <span style={{ width: 12, height: 2, background: '#10B981' }} /> Actual (FUELHH)
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.75rem', color: '#38BDF8' }}>
            <span style={{ width: 12, height: 2, borderBottom: '2px dashed #38BDF8' }} /> Forecast (WINDFOR)
          </span>
        </div>
      </div>

      <div style={{ width: '100%', height: 380 }}>
        <ResponsiveContainer>
          <ComposedChart
            data={chartData}
            margin={{ top: 10, right: 20, left: 10, bottom: 20 }}
            onClick={(e: any) => {
              if (e && e.activePayload && e.activePayload.length && onSelectInterval) {
                onSelectInterval(e.activePayload[0].payload.delivery_time);
              }
            }}
          >
            <defs>
              <linearGradient id="actualGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10B981" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#10B981" stopOpacity={0.0} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.05)" />
            
            <XAxis
              dataKey="shortLabel"
              stroke="#6B7280"
              fontSize={11}
              tickLine={false}
              interval="preserveStartEnd"
              minTickGap={40}
            />

            <YAxis
              stroke="#6B7280"
              fontSize={11}
              tickLine={false}
              domain={['auto', 'auto']}
              tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
              label={{ value: 'MW', angle: -90, position: 'insideLeft', fill: '#6B7280', fontSize: 11 }}
            />

            <Tooltip content={<CustomTooltip />} />

            {/* Gradient Area under Actual */}
            <Area
              type="monotone"
              dataKey="actual"
              stroke="none"
              fill="url(#actualGradient)"
              isAnimationActive={false}
            />

            {/* Actual Generation Line */}
            <Line
              type="monotone"
              dataKey="actual"
              name="Actual (FUELHH)"
              stroke="#10B981"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 5, fill: '#10B981', stroke: '#fff', strokeWidth: 2 }}
              isAnimationActive={false}
            />

            {/* Selected Forecast Line */}
            <Line
              type="monotone"
              dataKey="forecast"
              name="Forecast (WINDFOR)"
              stroke="#38BDF8"
              strokeWidth={2}
              strokeDasharray="4 4"
              dot={false}
              activeDot={{ r: 5, fill: '#38BDF8', stroke: '#fff', strokeWidth: 2 }}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
