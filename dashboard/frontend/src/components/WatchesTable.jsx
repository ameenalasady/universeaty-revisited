// dashboard/frontend/src/components/WatchesTable.jsx
import React, { useState, useEffect } from 'react';
import { fetchDbSummary, fetchWatches } from '../utils/api';

export default function WatchesTable() {
  const [summary, setSummary] = useState({ total_watches: 0, status_counts: { pending: 0, notified: 0, error: 0, cancelled: 0 } });
  const [watches, setWatches] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalRows, setTotalRows] = useState(0);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(false);

  const loadSummary = async () => {
    try {
      const data = await fetchDbSummary();
      setSummary(data);
    } catch (err) {
      console.error(err);
    }
  };

  const loadTable = async (targetPage = 1) => {
    setLoading(true);
    try {
      const data = await fetchWatches(targetPage, 12, search, statusFilter);
      setWatches(data.watches || []);
      setPage(data.page || 1);
      setTotalPages(data.pages || 1);
      setTotalRows(data.total || 0);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSummary();
    loadTable(1);
  }, [statusFilter]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    loadTable(1);
  };

  const handlePageChange = (direction) => {
    const next = page + direction;
    if (next >= 1 && next <= totalPages) {
      loadTable(next);
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 3fr', gap: '1.5rem' }}>
      {/* Quick stats column */}
      <div>
        <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '1.25rem', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.03)', marginBottom: '1rem' }}>
          <h4 style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '0.25rem' }}>Total Watches</h4>
          <p style={{ fontSize: '1.6rem', fontWeight: 700, color: 'white' }}>{Number(summary.total_watches).toLocaleString()}</p>
        </div>
        <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '1.25rem', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.03)', marginBottom: '1rem' }}>
          <h4 style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '0.25rem' }}>Pending</h4>
          <p style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--accent-warning)' }}>{Number(summary.status_counts.pending).toLocaleString()}</p>
        </div>
        <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '1.25rem', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.03)', marginBottom: '1rem' }}>
          <h4 style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '0.25rem' }}>Notified</h4>
          <p style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--accent-success)' }}>{Number(summary.status_counts.notified).toLocaleString()}</p>
        </div>
        <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '1.25rem', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.03)', marginBottom: '1rem' }}>
          <h4 style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '0.25rem' }}>Errored</h4>
          <p style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--accent-error)' }}>{Number(summary.status_counts.error).toLocaleString()}</p>
        </div>
      </div>

      {/* Main Database query panel */}
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.25rem' }}>
          <input 
            type="text" 
            className="db-input" 
            placeholder="Search by course code or recipient email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid var(--glass-border)',
              borderRadius: '8px',
              padding: '0.6rem 1rem',
              color: 'white',
              fontSize: '0.95rem',
              flex: 1,
              outline: 'none',
              transition: 'all 0.2s ease'
            }}
          />
          <select 
            className="db-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{
              background: '#141221',
              border: '1px solid var(--glass-border)',
              borderRadius: '8px',
              padding: '0.6rem 1rem',
              color: 'white',
              fontSize: '0.95rem',
              outline: 'none',
              cursor: 'pointer'
            }}
          >
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="notified">Notified</option>
            <option value="error">Error</option>
            <option value="cancelled">Cancelled</option>
          </select>
          <button 
            type="submit" 
            style={{
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid var(--glass-border)',
              color: 'white',
              padding: '0.6rem 1.2rem',
              borderRadius: '8px',
              fontWeight: 600,
              cursor: 'pointer',
              fontSize: '0.95rem'
            }}
          >
            Query
          </button>
        </form>

        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Term ID</th>
                <th>Course Code</th>
                <th>Section</th>
                <th>Email</th>
                <th>Status</th>
                <th>Created At</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="7" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '2rem' }}>Querying SQLite database...</td>
                </tr>
              ) : watches.length === 0 ? (
                <tr>
                  <td colSpan="7" style={{ textAlign: 'center', color: 'var(--text-dimmed)', padding: '2rem' }}>No watch requests found.</td>
                </tr>
              ) : (
                watches.map(row => {
                  const statusColors = {
                    pending: 'row-status-pending',
                    notified: 'row-status-notified',
                    error: 'row-status-error',
                    cancelled: 'row-status-cancelled'
                  };
                  return (
                    <tr key={row.id}>
                      <td style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.85rem', color: 'var(--text-muted)' }}>{row.id}</td>
                      <td style={{ color: 'var(--text-dimmed)', fontSize: '0.85rem' }}>{row.term_id}</td>
                      <td><strong style={{ color: 'white', fontSize: '0.95rem' }}>{row.course_code}</strong></td>
                      <td>
                        <span style={{
                          fontFamily: "'JetBrains Mono', monospace",
                          background: 'rgba(255,255,255,0.03)',
                          padding: '0.2rem 0.4rem',
                          borderRadius: '4px',
                          fontSize: '0.8rem',
                          border: '1px solid rgba(255,255,255,0.02)'
                        }}>
                          {row.section_display}
                        </span>
                      </td>
                      <td style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{row.email}</td>
                      <td>
                        <span className={`row-status-pill ${statusColors[row.status] || ''}`} style={{
                          display: 'inline-block',
                          padding: '0.15rem 0.5rem',
                          borderRadius: '9999px',
                          fontSize: '0.7rem',
                          fontWeight: 600,
                          textTransform: 'uppercase',
                          letterSpacing: '0.25px',
                          background: row.status === 'pending' ? 'rgba(245, 158, 11, 0.15)' : row.status === 'notified' ? 'rgba(16, 185, 129, 0.15)' : row.status === 'error' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(107, 114, 128, 0.15)',
                          color: row.status === 'pending' ? 'var(--accent-warning)' : row.status === 'notified' ? 'var(--accent-success)' : row.status === 'error' ? 'var(--accent-error)' : 'var(--text-muted)'
                        }}>
                          {row.status}
                        </span>
                      </td>
                      <td style={{ color: 'var(--text-dimmed)', fontSize: '0.85rem', whiteSpace: 'nowrap' }}>
                        {row.created_at ? row.created_at.split('.')[0] : '--'}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          <button 
            disabled={page <= 1 || loading} 
            onClick={() => handlePageChange(-1)}
            style={{
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid var(--glass-border)',
              color: 'white',
              padding: '0.4rem 1rem',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 600,
              opacity: page <= 1 ? 0.4 : 1
            }}
          >
            Previous
          </button>
          <span>Page {page} of {totalPages} ({Number(totalRows).toLocaleString()} total rows)</span>
          <button 
            disabled={page >= totalPages || loading} 
            onClick={() => handlePageChange(1)}
            style={{
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid var(--glass-border)',
              color: 'white',
              padding: '0.4rem 1rem',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 600,
              opacity: page >= totalPages ? 0.4 : 1
            }}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
