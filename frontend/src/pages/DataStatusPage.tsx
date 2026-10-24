import React, { useState } from 'react';
import { HealthResponse, EvaluationResponse } from '../types/dashboard';
import { triggerSync } from '../services/api';
import { Server, Database, RefreshCw, Clock } from 'lucide-react';

interface DataStatusPageProps {
  health: HealthResponse | null;
  evaluation: EvaluationResponse | null;
  onRefreshHealth: () => void;
}

export const DataStatusPage: React.FC<DataStatusPageProps> = ({
  health,
  evaluation,
  onRefreshHealth,
}) => {
  const [syncFrom, setSyncFrom] = useState('2026-01-01');
  const [syncTo, setSyncTo] = useState('2026-01-07');
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<string | null>(null);

  const handleManualSync = async () => {
    setSyncing(true);
    setSyncResult(null);
    try {
      const res = await triggerSync(syncFrom, syncTo);
      setSyncResult(`Successfully ingested ${res.actuals_ingested} FUELHH actuals and ${res.forecasts_ingested} WINDFOR forecasts!`);
      onRefreshHealth();
    } catch (e: any) {
      setSyncResult(`Sync failed: ${e.message}`);
    } finally {
      setSyncing(false);
    }
  };

  const isConnected = health?.elexon_api_connected ?? false;

  return (
    <div>
      {/* Top Infrastructure Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: '1rem',
        marginBottom: '1.5rem',
      }}>
        {/* Elexon API Health */}
        <div className="terminal-card" style={{ borderLeft: `3px solid ${isConnected ? 'var(--actual-emerald)' : 'var(--error-negative)'}` }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
            <span style={{ fontSize: '0.74rem', fontWeight: 600, color: isConnected ? 'var(--actual-emerald)' : 'var(--error-negative)', textTransform: 'uppercase' }}>
              Elexon BMRS API v1
            </span>
            <Server size={16} color={isConnected ? 'var(--actual-emerald)' : 'var(--error-negative)'} />
          </div>
          <div style={{ fontSize: '1.35rem', fontWeight: 700, color: '#F8FAFC', marginBottom: '0.2rem' }}>
            {isConnected ? 'ONLINE & RESPONDING' : 'OFFLINE / UNREACHABLE'}
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
            Endpoint: <span className="tabular">https://data.elexon.co.uk/bmrs/api/v1</span>
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-faint)', marginTop: '0.25rem' }}>
            Ping Latency: <span className="tabular">{health?.elexon_latency_ms ?? '—'} ms</span>
          </div>
        </div>

        {/* SQLite Cache Engine */}
        <div className="terminal-card" style={{ borderLeft: '3px solid var(--wind-cyan)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
            <span style={{ fontSize: '0.74rem', fontWeight: 600, color: 'var(--wind-cyan)', textTransform: 'uppercase' }}>
              SQLite Persistent Storage
            </span>
            <Database size={16} color="var(--wind-cyan)" />
          </div>
          <div className="tabular" style={{ fontSize: '1.35rem', fontWeight: 700, color: '#F8FAFC', marginBottom: '0.2rem' }}>
            {(health?.cached_actual_count ?? 0) + (health?.cached_forecast_count ?? 0)} Total Records
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
            Actuals (FUELHH): <span className="tabular">{health?.cached_actual_count ?? 0}</span> | Forecasts (WINDFOR): <span className="tabular">{health?.cached_forecast_count ?? 0}</span>
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-faint)', marginTop: '0.25rem' }}>
            Engine: WAL mode with deduplicating idempotency
          </div>
        </div>

        {/* Sync Provenance */}
        <div className="terminal-card" style={{ borderLeft: '3px solid var(--cutoff-amber)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
            <span style={{ fontSize: '0.74rem', fontWeight: 600, color: 'var(--cutoff-amber)', textTransform: 'uppercase' }}>
              Data Freshness &amp; Sync
            </span>
            <Clock size={16} color="var(--cutoff-amber)" />
          </div>
          <div className="tabular" style={{ fontSize: '1.15rem', fontWeight: 700, color: '#F8FAFC', marginBottom: '0.2rem' }}>
            {health?.last_sync_time ? health.last_sync_time : 'Awaiting sync trigger'}
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
            Server Time (UTC): <span className="tabular">{health?.server_time_utc}</span>
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-faint)', marginTop: '0.25rem' }}>
            Data Source Mode: <span className="badge badge-cyan">{evaluation?.data_source_mode || 'LIVE'}</span>
          </div>
        </div>
      </div>

      {/* Dataset Specifications */}
      <div className="terminal-card" style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '0.92rem', fontWeight: 700, color: '#F8FAFC', marginBottom: '0.35rem' }}>
          Official Datasets &amp; API Specifications
        </h2>
        <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
          Verified parameters and schemas from Elexon BMRS documentation.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
          <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '1rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
              <span style={{ fontWeight: 700, color: '#10B981' }}>FUELHH (Actual Generation)</span>
              <span className="badge badge-emerald">Half-Hourly</span>
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
              <div><strong>Endpoint:</strong> <code style={{ color: '#BAE6FD' }}>/datasets/FUELHH</code></div>
              <div><strong>Filter:</strong> <code style={{ color: '#BAE6FD' }}>fuelType=WIND</code></div>
              <div><strong>Parameters:</strong> settlementDateFrom, settlementDateTo (max 7-day query window)</div>
              <div><strong>Fields:</strong> startTime (UTC), settlementDate, settlementPeriod (1-48/46/50), generation (MW)</div>
              <div><strong>Cached Range:</strong> {health?.available_date_range_actuals?.min || 'None'} to {health?.available_date_range_actuals?.max || 'None'}</div>
            </div>
          </div>

          <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '1rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
              <span style={{ fontWeight: 700, color: '#38BDF8' }}>WINDFOR (Forecast Generation)</span>
              <span className="badge badge-cyan">Hourly Multi-Vintage</span>
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
              <div><strong>Endpoint:</strong> <code style={{ color: '#BAE6FD' }}>/datasets/WINDFOR</code></div>
              <div><strong>Query Parameters:</strong> publishDateTimeFrom, publishDateTimeTo (max 7-day window)</div>
              <div><strong>Vintages:</strong> Multi-publication runs retained with distinct publishTime</div>
              <div><strong>Fields:</strong> publishTime (UTC), startTime (delivery UTC), generation (hourly avg MW)</div>
              <div><strong>Cached Range:</strong> {health?.available_date_range_forecasts?.min || 'None'} to {health?.available_date_range_forecasts?.max || 'None'}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Manual Sync Trigger */}
      <div className="terminal-card">
        <h2 style={{ fontSize: '0.92rem', fontWeight: 700, color: '#F8FAFC', marginBottom: '0.35rem' }}>
          On-Demand Data Ingestion from Elexon BMRS
        </h2>
        <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
          Query official Elexon endpoints for any date range and persist records into the local SQLite database.
        </p>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>From:</span>
            <input
              type="date"
              className="input-field tabular"
              value={syncFrom}
              onChange={(e) => setSyncFrom(e.target.value)}
              style={{ width: '135px' }}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>To:</span>
            <input
              type="date"
              className="input-field tabular"
              value={syncTo}
              onChange={(e) => setSyncTo(e.target.value)}
              style={{ width: '135px' }}
            />
          </div>

          <button
            className="btn btn-primary"
            onClick={handleManualSync}
            disabled={syncing}
          >
            <RefreshCw size={14} className={syncing ? 'spin' : ''} />
            {syncing ? 'Fetching from Elexon...' : 'Fetch & Cache Range'}
          </button>
        </div>

        {syncResult && (
          <div style={{
            marginTop: '1rem',
            padding: '0.75rem',
            borderRadius: 'var(--radius-sm)',
            background: syncResult.includes('failed') ? 'rgba(244, 63, 94, 0.1)' : 'rgba(16, 185, 129, 0.1)',
            border: `1px solid ${syncResult.includes('failed') ? 'rgba(244, 63, 94, 0.3)' : 'rgba(16, 185, 129, 0.3)'}`,
            color: syncResult.includes('failed') ? '#FB7185' : '#34D399',
            fontSize: '0.78rem',
          }}>
            {syncResult}
          </div>
        )}
      </div>
    </div>
  );
};
