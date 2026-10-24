import React from 'react';
import { Wind, Download, RefreshCw } from 'lucide-react';
import { HealthResponse } from '../types/dashboard';

interface HeaderProps {
  health: HealthResponse | null;
  mode: 'auto' | 'live' | 'demo';
  onToggleMode: (newMode: 'auto' | 'live' | 'demo') => void;
  onExportCsv: () => void;
  onSync: () => void;
  isSyncing: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  health,
  mode,
  onToggleMode,
  onExportCsv,
  onSync,
  isSyncing,
}) => {
  const isConnected = health?.elexon_api_connected ?? false;
  const isDemo = mode === 'demo';

  return (
    <header style={{
      borderBottom: '1px solid var(--border-subtle)',
      background: 'rgba(8, 12, 20, 0.95)',
      backdropFilter: 'blur(12px)',
      position: 'sticky',
      top: 0,
      zIndex: 100,
      padding: '0.75rem 1.5rem',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      flexWrap: 'wrap',
      gap: '1rem',
    }}>
      {/* Brand & Market Identity */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.875rem' }}>
        <div style={{
          width: '38px',
          height: '38px',
          borderRadius: 'var(--radius-sm)',
          background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.2), rgba(16, 185, 129, 0.2))',
          border: '1px solid rgba(56, 189, 248, 0.3)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--wind-cyan)',
          boxShadow: '0 0 20px rgba(56, 189, 248, 0.2)',
        }}>
          <Wind size={22} />
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <h1 style={{ fontSize: '1.05rem', fontWeight: 700, letterSpacing: '-0.02em', color: '#F8FAFC' }}>
              GB WIND FORECAST TERMINAL
            </h1>
            <span className="badge badge-cyan" style={{ fontSize: '0.65rem' }}>
              ELEXON BMRS
            </span>
          </div>
          <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            Day-Ahead Wind Forecast Accuracy Evaluation &amp; Vintage Audit Platform
          </p>
        </div>
      </div>

      {/* Connectivity & Operational Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        {/* API Health Pill */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.35rem 0.65rem',
          borderRadius: 'var(--radius-sm)',
          background: isConnected ? 'rgba(16, 185, 129, 0.08)' : 'rgba(244, 63, 94, 0.08)',
          border: `1px solid ${isConnected ? 'rgba(16, 185, 129, 0.25)' : 'rgba(244, 63, 94, 0.25)'}`,
          fontSize: '0.74rem',
        }}>
          <span style={{
            width: '7px',
            height: '7px',
            borderRadius: '50%',
            background: isConnected ? '#10B981' : '#F43F5E',
            boxShadow: `0 0 8px ${isConnected ? '#10B981' : '#F43F5E'}`,
          }} />
          <span style={{ color: isConnected ? '#34D399' : '#FB7185', fontWeight: 600 }}>
            {isConnected ? `Elexon BMRS: Online (${health?.elexon_latency_ms ?? 0}ms)` : 'Elexon BMRS: Degraded'}
          </span>
        </div>

        {/* Mode Selector */}
        <div style={{
          display: 'flex',
          background: 'rgba(255, 255, 255, 0.04)',
          borderRadius: 'var(--radius-sm)',
          padding: '2px',
          border: '1px solid var(--border-subtle)',
        }}>
          <button
            onClick={() => onToggleMode('auto')}
            style={{
              padding: '0.3rem 0.65rem',
              fontSize: '0.72rem',
              fontWeight: 600,
              background: !isDemo ? 'rgba(56, 189, 248, 0.2)' : 'transparent',
              color: !isDemo ? 'var(--wind-cyan)' : 'var(--text-muted)',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            Live Market
          </button>
          <button
            onClick={() => onToggleMode('demo')}
            style={{
              padding: '0.3rem 0.65rem',
              fontSize: '0.72rem',
              fontWeight: 600,
              background: isDemo ? 'rgba(245, 158, 11, 0.2)' : 'transparent',
              color: isDemo ? 'var(--cutoff-amber)' : 'var(--text-muted)',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            Demo Fixture
          </button>
        </div>

        {/* Sync Trigger */}
        <button
          className="btn"
          onClick={onSync}
          disabled={isSyncing}
          title="Fetch latest data from Elexon BMRS API into local SQLite cache"
        >
          <RefreshCw size={14} className={isSyncing ? 'spin' : ''} />
          {isSyncing ? 'Syncing...' : 'Sync Elexon'}
        </button>

        {/* CSV Export */}
        <button
          className="btn btn-primary"
          onClick={onExportCsv}
          title="Export evaluated dataset to CSV"
        >
          <Download size={14} />
          Export CSV
        </button>
      </div>
    </header>
  );
};
