import React, { useState } from 'react';
import { Calendar, Clock } from 'lucide-react';

interface TradingControlsProps {
  dateFrom: string;
  dateTo: string;
  onDateChange: (from: string, to: string) => void;
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
  decisionCutoff,
  onCutoffChange,
  granularity,
  onGranularityChange,
  onApply,
  isLoading,
}) => {
  const [selectedPreset, setSelectedPreset] = useState<string>('latest');
  const [customCutoffInput, setCustomCutoffInput] = useState<string>(decisionCutoff || '');

  const handlePresetSelect = (presetId: string) => {
    setSelectedPreset(presetId);
    if (presetId === 'latest') {
      onCutoffChange(null);
    } else if (presetId === 'da_1100') {
      const d1 = new Date(dateFrom);
      d1.setUTCDate(d1.getUTCDate() - 1);
      const iso = `${d1.toISOString().split('T')[0]}T11:00:00Z`;
      onCutoffChange(iso);
      setCustomCutoffInput(iso);
    } else if (presetId === 'da_1700') {
      const d1 = new Date(dateFrom);
      d1.setUTCDate(d1.getUTCDate() - 1);
      const iso = `${d1.toISOString().split('T')[0]}T17:00:00Z`;
      onCutoffChange(iso);
      setCustomCutoffInput(iso);
    } else if (presetId === 'custom') {
      if (customCutoffInput) {
        onCutoffChange(customCutoffInput);
      }
    }
  };

  const handleCustomCutoffSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (customCutoffInput) {
      onCutoffChange(customCutoffInput);
      setSelectedPreset('custom');
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
              Evaluation Period:
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
              onClick={() => onDateChange('2026-01-01', '2026-01-07')}
            >
              Jan 1–7
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
              Jan Full Month
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
            value={selectedPreset}
            onChange={(e) => handlePresetSelect(e.target.value)}
            style={{ fontSize: '0.78rem' }}
          >
            <option value="latest">Latest Published (No Cutoff)</option>
            <option value="da_1100">Day-Ahead 11:00 UTC (EPEX Gate)</option>
            <option value="da_1700">Day-Ahead 17:00 UTC (NESO Schedule)</option>
            <option value="custom">Custom Point-in-Time...</option>
          </select>

          {selectedPreset === 'custom' && (
            <form onSubmit={handleCustomCutoffSubmit} style={{ display: 'flex', gap: '0.4rem' }}>
              <input
                type="text"
                placeholder="2025-12-31T12:00:00Z"
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

          {decisionCutoff && (
            <span className="badge badge-amber" title={`Enforcing strict cutoff <= ${decisionCutoff}`}>
              Cutoff Active
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
              onClick={() => onGranularityChange('half_hourly')}
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
              Half-Hour (SP 1–48)
            </button>
            <button
              onClick={() => onGranularityChange('hourly')}
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
              Hourly Avg
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
    </div>
  );
};
