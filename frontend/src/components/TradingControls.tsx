import React, { useState } from 'react';
import { Calendar, Clock, Info } from 'lucide-react';

interface TradingControlsProps {
  dateFrom: string;
  dateTo: string;
  onDateChange: (from: string, to: string) => void;
  cutoffType: 'rolling_da' | 'snapshot' | 'latest';
  onCutoffTypeChange: (type: 'rolling_da' | 'snapshot' | 'latest') => void;
  daCutoffTime: string;
  onDaCutoffTimeChange: (time: string) => void;
  decisionCutoff: string | null;
  onCutoffChange: (cutoff: string | null) => void;
  granularity: 'half_hourly' | 'hourly';
  onGranularityChange: (g: 'half_hourly' | 'hourly') => void;
  onApply: () => void;
  isLoading: boolean;
}

export const TradingControls: React.FC<TradingControlsProps> = ({
  dateFrom,
  dateTo,
  onDateChange,
  cutoffType,
  onCutoffTypeChange,
  daCutoffTime,
  onDaCutoffTimeChange,
  decisionCutoff,
  onCutoffChange,
  granularity,
  onGranularityChange,
  onApply,
  isLoading,
}) => {
  const [customCutoffInput, setCustomCutoffInput] = useState<string>(decisionCutoff || '2025-12-31T11:30:00Z');

  // Map internal state to preset dropdown key
  let currentPresetKey = 'rolling_da_0920';
  if (cutoffType === 'latest') {
    currentPresetKey = 'latest';
  } else if (cutoffType === 'snapshot') {
    currentPresetKey = 'snapshot';
  } else if (cutoffType === 'rolling_da') {
    if (daCutoffTime === '09:20') currentPresetKey = 'rolling_da_0920';
    else if (daCutoffTime === '09:50') currentPresetKey = 'rolling_da_0950';
    else if (daCutoffTime === '11:00') currentPresetKey = 'rolling_da_1100';
    else if (daCutoffTime === '15:30') currentPresetKey = 'rolling_da_1530';
    else if (daCutoffTime === '17:00') currentPresetKey = 'rolling_da_1700';
    else currentPresetKey = 'custom_da';
  }

  const handlePresetSelect = (presetKey: string) => {
    if (presetKey === 'rolling_da_0920') {
      onCutoffTypeChange('rolling_da');
      onDaCutoffTimeChange('09:20');
      onCutoffChange(null);
    } else if (presetKey === 'rolling_da_0950') {
      onCutoffTypeChange('rolling_da');
      onDaCutoffTimeChange('09:50');
      onCutoffChange(null);
    } else if (presetKey === 'rolling_da_1100') {
      onCutoffTypeChange('rolling_da');
      onDaCutoffTimeChange('11:00');
      onCutoffChange(null);
    } else if (presetKey === 'rolling_da_1530') {
      onCutoffTypeChange('rolling_da');
      onDaCutoffTimeChange('15:30');
      onCutoffChange(null);
    } else if (presetKey === 'rolling_da_1700') {
      onCutoffTypeChange('rolling_da');
      onDaCutoffTimeChange('17:00');
      onCutoffChange(null);
    } else if (presetKey === 'latest') {
      onCutoffTypeChange('latest');
      onCutoffChange(null);
    } else if (presetKey === 'snapshot') {
      onCutoffTypeChange('snapshot');
      onCutoffChange(customCutoffInput);
    }
  };

  const handleCustomCutoffSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (customCutoffInput) {
      onCutoffTypeChange('snapshot');
      onCutoffChange(customCutoffInput);
    }
  };

  return (
    <div className="terminal-card" style={{ marginBottom: '1.25rem', padding: '1rem 1.25rem' }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1rem',
      }}>
        {/* Left: Evaluation Date Bounds */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-muted)' }}>
            <Calendar size={15} color="var(--wind-cyan)" />
            <span style={{ fontSize: '0.78rem', fontWeight: 600, textTransform: 'uppercase' }}>
              Delivery Range:
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input
              type="date"
              className="input-field tabular"
              value={dateFrom}
              onChange={(e) => onDateChange(e.target.value, dateTo)}
              style={{ width: '135px' }}
            />
            <span style={{ color: 'var(--text-faint)' }}>to</span>
            <input
              type="date"
              className="input-field tabular"
              value={dateTo}
              onChange={(e) => onDateChange(dateFrom, e.target.value)}
              style={{ width: '135px' }}
            />
          </div>

          {/* Quick Date Range Buttons */}
          <div style={{ display: 'flex', gap: '0.25rem' }}>
            <button
              className="btn"
              style={{ fontSize: '0.72rem', padding: '0.3rem 0.5rem' }}
              onClick={() => onDateChange('2026-01-01', '2026-01-05')}
            >
              Jan 1–5 (Benchmark)
            </button>
            <button
              className="btn"
              style={{ fontSize: '0.72rem', padding: '0.3rem 0.5rem' }}
              onClick={() => onDateChange('2026-01-01', '2026-01-14')}
            >
              Jan 1–14
            </button>
            <button
              className="btn"
              style={{ fontSize: '0.72rem', padding: '0.3rem 0.5rem' }}
              onClick={() => onDateChange('2026-01-01', '2026-01-31')}
            >
              Full Month (Jan)
            </button>
          </div>
        </div>

        {/* Center: Decision Cutoff Controller */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-muted)' }}>
            <Clock size={15} color="var(--cutoff-amber)" />
            <span style={{ fontSize: '0.78rem', fontWeight: 600, textTransform: 'uppercase' }}>
              Decision Cutoff:
            </span>
          </div>

          <select
            className="select-field"
            value={currentPresetKey}
            onChange={(e) => handlePresetSelect(e.target.value)}
            style={{ fontSize: '0.78rem', maxWidth: '340px' }}
          >
            <option value="rolling_da_0920">EPEX SPOT GB DA 60 (D-1 09:20 London)</option>
            <option value="rolling_da_0950">Nord Pool / N2EX GB DA (D-1 09:50 London)</option>
            <option value="rolling_da_1100">Configurable Reference (D-1 11:00 London)</option>
            <option value="rolling_da_1530">EPEX SPOT Half-Hour (D-1 15:30 London)</option>
            <option value="rolling_da_1700">NESO Day-Ahead Schedule (D-1 17:00 London)</option>
            <option value="latest">Retrospective Benchmark (Latest before Delivery)</option>
            <option value="snapshot">Point-in-Time Snapshot (Single Timestamp)</option>
          </select>

          {cutoffType === 'snapshot' && (
            <form onSubmit={handleCustomCutoffSubmit} style={{ display: 'flex', gap: '0.4rem' }}>
              <input
                type="text"
                placeholder="2025-12-31T11:30:00Z"
                className="input-field tabular"
                value={customCutoffInput}
                onChange={(e) => setCustomCutoffInput(e.target.value)}
                style={{ width: '190px', fontSize: '0.75rem' }}
              />
              <button type="submit" className="btn btn-primary" style={{ padding: '0.3rem 0.6rem' }}>
                Set
              </button>
            </form>
          )}

          {cutoffType === 'rolling_da' && (
            <span className="badge badge-amber" title={`Evaluating forecasts published prior to D-1 ${daCutoffTime} London local time`}>
              Rolling DA ({daCutoffTime} London)
            </span>
          )}
          {cutoffType === 'snapshot' && decisionCutoff && (
            <span className="badge badge-amber" title={`Strict point-in-time barrier: <= ${decisionCutoff}`}>
              Snapshot: {decisionCutoff.slice(0, 16)}Z
            </span>
          )}
          {cutoffType === 'latest' && (
            <span className="badge badge-cyan" title="Latest forecast published at or before delivery start (ex-post excluded)">
              Latest Ex-Ante
            </span>
          )}
        </div>

        {/* Right: Granularity & Refresh */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
            display: 'flex',
            background: 'rgba(255, 255, 255, 0.04)',
            borderRadius: 'var(--radius-sm)',
            padding: '2px',
            border: '1px solid var(--border-subtle)',
          }}>
            <button
              onClick={() => onGranularityChange('hourly')}
              title="Native 1-to-1 comparison: averages FUELHH half-hours to match WINDFOR's native 1-hour resolution"
              style={{
                padding: '0.3rem 0.6rem',
                fontSize: '0.72rem',
                fontWeight: 600,
                background: granularity === 'hourly' ? 'rgba(56, 189, 248, 0.2)' : 'transparent',
                color: granularity === 'hourly' ? 'var(--wind-cyan)' : 'var(--text-muted)',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              Hourly (Native 1-to-1)
            </button>
            <button
              onClick={() => onGranularityChange('half_hourly')}
              title="Broadcast mode: duplicates hourly WINDFOR forecast across SP 2k-1 and SP 2k (evaluates intra-hour ramp)"
              style={{
                padding: '0.3rem 0.6rem',
                fontSize: '0.72rem',
                fontWeight: 600,
                background: granularity === 'half_hourly' ? 'rgba(56, 189, 248, 0.2)' : 'transparent',
                color: granularity === 'half_hourly' ? 'var(--wind-cyan)' : 'var(--text-muted)',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              Half-Hour (Broadcast)
            </button>
          </div>

          <button
            className="btn btn-emerald"
            onClick={onApply}
            disabled={isLoading}
          >
            {isLoading ? 'Calculating...' : 'Recalculate'}
          </button>
        </div>
      </div>

      {/* Sub-header trading clarification banner */}
      <div style={{
        marginTop: '0.75rem',
        paddingTop: '0.6rem',
        borderTop: '1px solid rgba(255, 255, 255, 0.05)',
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        fontSize: '0.72rem',
        color: 'var(--text-muted)',
      }}>
        <Info size={13} color="var(--wind-cyan)" />
        <span>
          <strong style={{ color: 'var(--text-secondary)' }}>GB Power Market Deadlines:</strong> EPEX SPOT GB Day-Ahead 60 closes at <strong>09:20 UK local time</strong> (results ~09:30). Nord Pool / N2EX closes at <strong>09:50 UK local time</strong> (results at 10:00 UK / 11:00 CET). NESO schedule publishes at <strong>17:00 UK local time</strong>. Balancing Mechanism (BM) Gate Closure is <strong>1 hour prior</strong> to each half-hour delivery.
        </span>
      </div>
    </div>
  );
};
