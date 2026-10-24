import React, { useState, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { Navigation, ScreenTab } from './components/Navigation';
import { TradingControls } from './components/TradingControls';
import { TradingOverviewPage } from './pages/TradingOverviewPage';
import { ForecastAccuracyPage } from './pages/ForecastAccuracyPage';
import { ForecastHistoryPage } from './pages/ForecastHistoryPage';
import { DataStatusPage } from './pages/DataStatusPage';
import { EvaluationResponse, HealthResponse } from './types/dashboard';
import { fetchEvaluation, fetchHealth, getExportCsvUrl, triggerSync } from './services/api';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ScreenTab>('overview');
  const [dateFrom, setDateFrom] = useState<string>('2026-01-01');
  const [dateTo, setDateTo] = useState<string>('2026-01-31');
  const [cutoffType, setCutoffType] = useState<'rolling_da' | 'snapshot' | 'latest'>('rolling_da');
  const [daCutoffTime, setDaCutoffTime] = useState<string>('09:20');
  const [decisionCutoff, setDecisionCutoff] = useState<string | null>(null);
  const [granularity, setGranularity] = useState<'half_hourly' | 'hourly'>('hourly');
  const [mode, setMode] = useState<'auto' | 'live' | 'demo'>('auto');

  const [selectedDeliveryTime, setSelectedDeliveryTime] = useState<string>('');

  const [evaluation, setEvaluation] = useState<EvaluationResponse | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadHealth = useCallback(() => {
    fetchHealth()
      .then(setHealth)
      .catch((err) => console.error('Health check failed:', err));
  }, []);

  const loadData = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchEvaluation(dateFrom, dateTo, cutoffType, daCutoffTime, decisionCutoff, granularity, mode)
      .then((data) => {
        setEvaluation(data);
        if (data.intervals.length > 0 && !selectedDeliveryTime) {
          setSelectedDeliveryTime(data.intervals[0].delivery_time);
        }
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || 'Failed to fetch evaluation');
        setLoading(false);
      });
  }, [dateFrom, dateTo, cutoffType, daCutoffTime, decisionCutoff, granularity, mode, selectedDeliveryTime]);

  useEffect(() => {
    loadHealth();
    const interval = setInterval(loadHealth, 30000);
    return () => clearInterval(interval);
  }, [loadHealth]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleExportCsv = () => {
    const url = getExportCsvUrl(dateFrom, dateTo, cutoffType, daCutoffTime, decisionCutoff, granularity);
    window.open(url, '_blank');
  };

  const handleSync = async () => {
    setIsSyncing(true);
    try {
      await triggerSync(dateFrom, dateTo);
      loadHealth();
      loadData();
    } catch (err: any) {
      alert(`Sync error: ${err.message}`);
    } finally {
      setIsSyncing(false);
    }
  };

  const handleSelectIntervalForAudit = (deliveryTime: string) => {
    setSelectedDeliveryTime(deliveryTime);
    setActiveTab('history');
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Header
        health={health}
        mode={mode}
        onToggleMode={(newMode) => setMode(newMode)}
        onExportCsv={handleExportCsv}
        onSync={handleSync}
        isSyncing={isSyncing}
      />

      <Navigation activeTab={activeTab} onTabChange={setActiveTab} />

      <main style={{ flex: 1, padding: '1.5rem', maxWidth: '1440px', width: '100%', margin: '0 auto' }}>
        {/* Trading Controls are pinned across screens */}
        <TradingControls
          dateFrom={dateFrom}
          dateTo={dateTo}
          onDateChange={(from, to) => {
            setDateFrom(from);
            setDateTo(to);
          }}
          cutoffType={cutoffType}
          onCutoffTypeChange={setCutoffType}
          daCutoffTime={daCutoffTime}
          onDaCutoffTimeChange={setDaCutoffTime}
          decisionCutoff={decisionCutoff}
          onCutoffChange={setDecisionCutoff}
          granularity={granularity}
          onGranularityChange={setGranularity}
          onApply={loadData}
          isLoading={loading}
        />

        {error && (
          <div className="terminal-card" style={{ borderLeft: '3px solid var(--error-negative)', color: '#FB7185', marginBottom: '1.25rem' }}>
            <strong>Evaluation Pipeline Error:</strong> {error}
          </div>
        )}

        {loading && !evaluation && (
          <div className="terminal-card" style={{ textAlign: 'center', padding: '4rem 2rem' }}>
            <div style={{ color: 'var(--wind-cyan)', fontSize: '1.1rem', fontWeight: 600, marginBottom: '0.5rem' }}>
              Calculating UK Wind Forecast Accuracy...
            </div>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>
              Aligning FUELHH actual generation with WINDFOR forecast publications and enforcing decision cutoff logic.
            </div>
          </div>
        )}

        {evaluation && (
          <>
            {activeTab === 'overview' && (
              <TradingOverviewPage
                evaluation={evaluation}
                health={health}
                onSelectInterval={handleSelectIntervalForAudit}
              />
            )}

            {activeTab === 'accuracy' && (
              <ForecastAccuracyPage
                evaluation={evaluation}
                onSelectInterval={handleSelectIntervalForAudit}
              />
            )}

            {activeTab === 'history' && (
              <ForecastHistoryPage
                selectedDeliveryTime={selectedDeliveryTime}
                onSelectDeliveryTime={setSelectedDeliveryTime}
                availableIntervals={evaluation.intervals}
                decisionCutoff={decisionCutoff}
              />
            )}

            {activeTab === 'status' && (
              <DataStatusPage
                health={health}
                evaluation={evaluation}
                onRefreshHealth={loadHealth}
              />
            )}
          </>
        )}
      </main>

      {/* Terminal Footer */}
      <footer style={{
        borderTop: '1px solid var(--border-subtle)',
        padding: '0.85rem 1.5rem',
        background: 'rgba(8, 12, 20, 0.95)',
        fontSize: '0.72rem',
        color: 'var(--text-faint)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '0.5rem',
      }}>
        <div>
          Data Source: Official Elexon BMRS API (FUELHH actuals &amp; WINDFOR forecasts) | Timestamps in UTC internally, rendered in Europe/London (GMT/BST).
        </div>
        <div>
          Analytical Read-Only Terminal &bull; No order execution or financial warranty implied.
        </div>
      </footer>
    </div>
  );
};
