import React, { useState, useEffect } from 'react';
import { VintageEvolutionResponse, EvaluationInterval } from '../types/dashboard';
import { fetchVintages } from '../services/api';
import { VintageEvolutionChart } from '../components/VintageEvolutionChart';
import { GitCommit } from 'lucide-react';

interface ForecastHistoryPageProps {
  selectedDeliveryTime: string;
  onSelectDeliveryTime: (time: string) => void;
  availableIntervals: EvaluationInterval[];
  decisionCutoff: string | null;
}

export const ForecastHistoryPage: React.FC<ForecastHistoryPageProps> = ({
  selectedDeliveryTime,
  onSelectDeliveryTime,
  availableIntervals,
  decisionCutoff,
}) => {
  const [evolutionData, setEvolutionData] = useState<VintageEvolutionResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedDeliveryTime && availableIntervals.length > 0) {
      onSelectDeliveryTime(availableIntervals[0].delivery_time);
    }
  }, [selectedDeliveryTime, availableIntervals, onSelectDeliveryTime]);

  useEffect(() => {
    if (!selectedDeliveryTime) return;

    let isMounted = true;
    setLoading(true);
    setError(null);

    fetchVintages(selectedDeliveryTime, decisionCutoff)
      .then((data) => {
        if (isMounted) {
          setEvolutionData(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || 'Failed to load vintages');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [selectedDeliveryTime, decisionCutoff]);

  return (
    <div>
      {/* Interval Selector Bar */}
      <div className="terminal-card" style={{ marginBottom: '1.25rem', padding: '1rem 1.25rem' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '1rem',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: 'var(--radius-sm)',
              background: 'rgba(56, 189, 248, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--wind-cyan)',
            }}>
              <GitCommit size={18} />
            </div>
            <div>
              <h2 style={{ fontSize: '0.92rem', fontWeight: 700, color: '#F8FAFC' }}>
                Select Delivery Interval for Vintage Audit
              </h2>
              <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                Inspect all historical National Grid publication runs leading up to this settlement period.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Target Interval:</span>
            <select
              className="select-field tabular"
              value={selectedDeliveryTime}
              onChange={(e) => onSelectDeliveryTime(e.target.value)}
              style={{ minWidth: '240px', fontSize: '0.78rem' }}
            >
              {availableIntervals.map((it) => (
                <option key={it.delivery_time} value={it.delivery_time}>
                  {it.display_time_london} {it.settlement_period ? `(SP ${it.settlement_period})` : ''} - Act: {it.actual_mw ?? '—'} MW
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {loading && (
        <div className="terminal-card" style={{ textAlign: 'center', padding: '3rem' }}>
          <div style={{ color: 'var(--wind-cyan)', marginBottom: '0.5rem' }}>Loading vintage publication runs...</div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Querying historical WINDFOR dataset records</span>
        </div>
      )}

      {error && (
        <div className="terminal-card" style={{ borderLeft: '3px solid var(--error-negative)', color: 'var(--error-negative)' }}>
          Error retrieving vintage data: {error}
        </div>
      )}

      {!loading && !error && evolutionData && (
        <VintageEvolutionChart evolution={evolutionData} />
      )}
    </div>
  );
};
