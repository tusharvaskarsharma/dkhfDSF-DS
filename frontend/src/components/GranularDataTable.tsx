import React, { useState, useMemo } from 'react';
import { EvaluationInterval } from '../types/dashboard';
import { Search, Eye, ChevronLeft, ChevronRight } from 'lucide-react';

interface GranularDataTableProps {
  intervals: EvaluationInterval[];
  onSelectInterval?: (deliveryTime: string) => void;
}

export const GranularDataTable: React.FC<GranularDataTableProps> = ({
  intervals,
  onSelectInterval,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 24;

  const filtered = useMemo(() => {
    return intervals.filter((it) => {
      if (statusFilter !== 'ALL' && it.status !== statusFilter) {
        return false;
      }
      if (searchTerm) {
        const term = searchTerm.toLowerCase();
        const matchesDate = it.settlement_date.toLowerCase().includes(term);
        const matchesLondon = it.display_time_london.toLowerCase().includes(term);
        const matchesSp = it.settlement_period?.toString() === term;
        return matchesDate || matchesLondon || matchesSp;
      }
      return true;
    });
  }, [intervals, statusFilter, searchTerm]);

  const totalPages = Math.ceil(filtered.length / pageSize) || 1;
  const paginated = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filtered.slice(start, start + pageSize);
  }, [filtered, currentPage, pageSize]);

  return (
    <div className="terminal-card" style={{ marginBottom: '1.5rem' }}>
      {/* Controls Bar */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '0.75rem',
        marginBottom: '1rem',
      }}>
        <div>
          <h2 style={{ fontSize: '0.92rem', fontWeight: 700, color: '#F8FAFC' }}>
            Settlement Interval Ledger &amp; Granular Verification
          </h2>
          <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            Showing {filtered.length} intervals across selected evaluation window.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          {/* Search Box */}
          <div style={{ position: 'relative' }}>
            <Search size={14} color="var(--text-faint)" style={{ position: 'absolute', left: '0.6rem', top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="text"
              placeholder="Search date or SP..."
              className="input-field"
              value={searchTerm}
              onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
              style={{ paddingLeft: '1.8rem', width: '170px', fontSize: '0.74rem' }}
            />
          </div>

          {/* Status Filter */}
          <select
            className="select-field"
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setCurrentPage(1); }}
            style={{ fontSize: '0.74rem' }}
          >
            <option value="ALL">All Intervals ({intervals.length})</option>
            <option value="VALID">Valid Pairs Only</option>
            <option value="MISSING_FORECAST">Missing Forecast</option>
            <option value="MISSING_ACTUAL">Missing Actual</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div style={{ overflowX: 'auto' }}>
        <table className="terminal-table">
          <thead>
            <tr>
              <th>Delivery (UTC)</th>
              <th>Local Time (London)</th>
              <th>SP</th>
              <th>Actual Gen</th>
              <th>Selected Forecast</th>
              <th>Error (e_t)</th>
              <th>Abs Error</th>
              <th>Forecast Pub (UTC)</th>
              <th>Lead Time</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {paginated.map((row) => {
              const isErrorPos = (row.error_mw ?? 0) > 0;
              return (
                <tr key={row.delivery_time}>
                  <td className="tabular">{row.delivery_time}</td>
                  <td>{row.display_time_london}</td>
                  <td className="tabular">
                    {row.settlement_period ? `SP ${row.settlement_period}` : '—'}
                  </td>
                  <td className="tabular" style={{ fontWeight: 600, color: 'var(--actual-emerald)' }}>
                    {row.actual_mw !== null && row.actual_mw !== undefined ? `${row.actual_mw.toLocaleString()} MW` : '—'}
                  </td>
                  <td className="tabular" style={{ fontWeight: 600, color: 'var(--wind-cyan)' }}>
                    {row.forecast_mw !== null && row.forecast_mw !== undefined ? `${row.forecast_mw.toLocaleString()} MW` : '—'}
                  </td>
                  <td className="tabular">
                    {row.error_mw !== null && row.error_mw !== undefined ? (
                      <span style={{ fontWeight: 600, color: isErrorPos ? 'var(--error-positive)' : 'var(--error-negative)' }}>
                        {row.error_mw > 0 ? `+${row.error_mw.toLocaleString()}` : row.error_mw.toLocaleString()} MW
                      </span>
                    ) : '—'}
                  </td>
                  <td className="tabular">
                    {row.abs_error_mw !== null && row.abs_error_mw !== undefined ? `${row.abs_error_mw.toLocaleString()} MW` : '—'}
                  </td>
                  <td className="tabular" style={{ color: 'var(--text-muted)' }}>
                    {row.selected_publish_time || '—'}
                  </td>
                  <td className="tabular">
                    {row.lead_time_hours !== null && row.lead_time_hours !== undefined ? `${row.lead_time_hours}h` : '—'}
                  </td>
                  <td>
                    {row.status === 'VALID' && <span className="badge badge-emerald">Valid</span>}
                    {row.status === 'MISSING_FORECAST' && <span className="badge badge-rose">No Forecast</span>}
                    {row.status === 'MISSING_ACTUAL' && <span className="badge badge-amber">No Actual</span>}
                    {row.status === 'MISSING_BOTH' && <span className="badge badge-muted">Missing Both</span>}
                  </td>
                  <td>
                    {onSelectInterval && (
                      <button
                        className="btn"
                        style={{ padding: '0.2rem 0.5rem', fontSize: '0.7rem' }}
                        onClick={() => onSelectInterval(row.delivery_time)}
                        title="Inspect forecast revisions for this interval"
                      >
                        <Eye size={12} />
                        Audit
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginTop: '0.85rem',
        paddingTop: '0.75rem',
        borderTop: '1px solid rgba(255, 255, 255, 0.05)',
        fontSize: '0.75rem',
        color: 'var(--text-muted)',
      }}>
        <span>
          Page {currentPage} of {totalPages} ({filtered.length} total intervals)
        </span>
        <div style={{ display: 'flex', gap: '0.35rem' }}>
          <button
            className="btn"
            disabled={currentPage <= 1}
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            style={{ padding: '0.25rem 0.6rem' }}
          >
            <ChevronLeft size={14} /> Prev
          </button>
          <button
            className="btn"
            disabled={currentPage >= totalPages}
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            style={{ padding: '0.25rem 0.6rem' }}
          >
            Next <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
};
