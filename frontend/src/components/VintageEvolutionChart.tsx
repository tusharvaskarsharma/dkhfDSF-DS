import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';
import { VintageEvolutionResponse } from '../types/dashboard';
import { CheckCircle2, AlertCircle } from 'lucide-react';

interface VintageEvolutionChartProps {
  evolution: VintageEvolutionResponse;
}

export const VintageEvolutionChart: React.FC<VintageEvolutionChartProps> = ({ evolution }) => {
  const chartData = evolution.vintages.map((v) => ({
    publish_time: v.publish_time,
    display_publish: v.display_publish_london,
    lead_time_hours: v.lead_time_hours,
    generation_mw: v.generation_mw,
    is_selected: v.is_selected,
    is_eligible: v.is_eligible_before_cutoff,
  }));

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || !payload.length) return null;
    const item = payload[0].payload;

    return (
      <div style={{
        background: 'rgba(11, 16, 26, 0.95)',
        backdropFilter: 'blur(12px)',
        border: '1px solid rgba(255, 255, 255, 0.12)',
        borderRadius: 'var(--radius-sm)',
        padding: '0.65rem 0.85rem',
        fontSize: '0.74rem',
      }}>
        <div style={{ color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
          Publication Timestamp:
        </div>
        <div style={{ fontWeight: 600, color: '#F3F4F6' }}>
          {item.display_publish}
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', marginTop: '0.35rem' }}>
          <span>Forecast Output:</span>
          <span className="tabular" style={{ fontWeight: 700, color: 'var(--wind-cyan)' }}>
            {item.generation_mw.toLocaleString()} MW
          </span>
        </div>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-faint)', marginTop: '0.2rem' }}>
          Lead time: {item.lead_time_hours} hrs prior to delivery
        </div>
        {item.is_selected && (
          <div style={{ marginTop: '0.3rem' }}>
            <span className="badge badge-amber">Selected at Cutoff</span>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="terminal-card" style={{ marginBottom: '1.5rem' }}>
      {/* Header Info */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '0.75rem',
        marginBottom: '1rem',
        paddingBottom: '0.75rem',
        borderBottom: '1px solid var(--border-subtle)',
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <h2 style={{ fontSize: '0.96rem', fontWeight: 700, color: '#F8FAFC' }}>
              Forecast Revision Vintage Evolution
            </h2>
            <span className="badge badge-cyan">
              Delivery: {evolution.display_time_london}
            </span>
            {evolution.settlement_period && (
              <span className="badge badge-muted">
                SP {evolution.settlement_period}
              </span>
            )}
          </div>
          <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
            Tracking how National Grid / NESO wind forecast revisions converged as publication approached delivery time.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {evolution.actual_mw !== null && evolution.actual_mw !== undefined && (
            <div style={{ textAlign: 'right' }}>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Actual Outturn:</span>
              <div className="tabular" style={{ fontWeight: 700, color: 'var(--actual-emerald)', fontSize: '1rem' }}>
                {evolution.actual_mw.toLocaleString()} MW
              </div>
            </div>
          )}

          {evolution.selected_forecast_mw !== null && evolution.selected_forecast_mw !== undefined && (
            <div style={{ textAlign: 'right' }}>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Selected at Cutoff:</span>
              <div className="tabular" style={{ fontWeight: 700, color: 'var(--cutoff-amber)', fontSize: '1rem' }}>
                {evolution.selected_forecast_mw.toLocaleString()} MW
              </div>
            </div>
          )}
        </div>
      </div>

      {evolution.missing_vintage_warning && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.6rem 0.85rem',
          borderRadius: 'var(--radius-sm)',
          background: 'rgba(245, 158, 11, 0.1)',
          border: '1px solid rgba(245, 158, 11, 0.25)',
          color: '#FBBF24',
          fontSize: '0.76rem',
          marginBottom: '1rem',
        }}>
          <AlertCircle size={15} />
          <span>{evolution.missing_vintage_warning}</span>
        </div>
      )}

      {/* Revision Chart */}
      <div style={{ width: '100%', height: 280, marginBottom: '1.25rem' }}>
        <ResponsiveContainer>
          <LineChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.05)" />
            <XAxis
              dataKey="display_publish"
              stroke="#6B7280"
              fontSize={11}
              tickLine={false}
              label={{ value: 'Publication Run Time (Europe/London)', position: 'insideBottom', offset: -10, fill: '#6B7280', fontSize: 11 }}
            />
            <YAxis
              stroke="#6B7280"
              fontSize={11}
              tickLine={false}
              domain={['auto', 'auto']}
              label={{ value: 'Forecast Generation (MW)', angle: -90, position: 'insideLeft', fill: '#6B7280', fontSize: 11 }}
            />
            <Tooltip content={<CustomTooltip />} />
            
            {/* Actual Outturn Baseline */}
            {evolution.actual_mw !== null && (
              <ReferenceLine
                y={evolution.actual_mw}
                stroke="#10B981"
                strokeDasharray="5 5"
                label={{ value: `Actual: ${evolution.actual_mw} MW`, fill: '#10B981', fontSize: 11 }}
              />
            )}

            <Line
              type="monotone"
              dataKey="generation_mw"
              stroke="#38BDF8"
              strokeWidth={2}
              dot={(props: any) => {
                const isSelected = props.payload.is_selected;
                return (
                  <circle
                    cx={props.cx}
                    cy={props.cy}
                    r={isSelected ? 6 : 4}
                    fill={isSelected ? '#F59E0B' : '#38BDF8'}
                    stroke={isSelected ? '#FFF' : '#080C14'}
                    strokeWidth={isSelected ? 2 : 1}
                  />
                );
              }}
              activeDot={{ r: 7, fill: '#38BDF8' }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Vintages Detail Table */}
      <div style={{ overflowX: 'auto' }}>
        <table className="terminal-table">
          <thead>
            <tr>
              <th>Publication Time (UTC)</th>
              <th>Local Time (London)</th>
              <th>Lead Time</th>
              <th>Forecast Value</th>
              <th>Revision from Prior</th>
              <th>Cutoff Eligibility</th>
              <th>Selected Status</th>
            </tr>
          </thead>
          <tbody>
            {evolution.vintages.map((v, idx) => {
              const prev = idx > 0 ? evolution.vintages[idx - 1] : null;
              const delta = prev ? v.generation_mw - prev.generation_mw : null;

              return (
                <tr key={v.publish_time} style={{ background: v.is_selected ? 'rgba(245, 158, 11, 0.08)' : 'transparent' }}>
                  <td className="tabular">{v.publish_time}</td>
                  <td>{v.display_publish_london}</td>
                  <td className="tabular">{v.lead_time_hours} hrs prior</td>
                  <td className="tabular" style={{ fontWeight: 600, color: 'var(--wind-cyan)' }}>
                    {v.generation_mw.toLocaleString()} MW
                  </td>
                  <td className="tabular">
                    {delta !== null ? (
                      <span style={{ color: delta > 0 ? 'var(--error-positive)' : delta < 0 ? 'var(--error-negative)' : 'var(--text-muted)' }}>
                        {delta > 0 ? `+${delta.toLocaleString()}` : delta.toLocaleString()} MW
                      </span>
                    ) : (
                      <span style={{ color: 'var(--text-faint)' }}>Initial Run</span>
                    )}
                  </td>
                  <td>
                    {v.is_eligible_before_cutoff ? (
                      <span className="badge badge-emerald">Eligible (&le; Cutoff)</span>
                    ) : (
                      <span className="badge badge-rose">Post-Cutoff (Future Info)</span>
                    )}
                  </td>
                  <td>
                    {v.is_selected ? (
                      <span className="badge badge-amber" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                        <CheckCircle2 size={12} /> Active Decision Vintage
                      </span>
                    ) : (
                      <span style={{ color: 'var(--text-faint)' }}>—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
