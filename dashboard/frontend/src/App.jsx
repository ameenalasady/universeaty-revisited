// dashboard/frontend/src/App.jsx
import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import MetricsCard from './components/MetricsCard';
import ServiceControl from './components/ServiceControl';
import WatchesTable from './components/WatchesTable';
import HistoryChart from './components/HistoryChart';
import LogConsole from './components/LogConsole';
import { fetchStatus } from './utils/api';

export default function App() {
  const [metrics, setMetrics] = useState({
    pi_uptime: 'Checking...',
    cpu_temp: 0.0,
    cpu_load: '0.00 0.00 0.00',
    ram: { total_mb: 0, used_mb: 0, free_mb: 0, percent: 0.0 },
    disk: { total_mb: 0, used_mb: 0, free_mb: 0, percent: 0.0 },
    service: { active_state: 'inactive', sub_state: 'unknown', pid: 0, memory_mb: 0.0, uptime: 'N/A' },
    db_size_mb: 0.0,
    log_size_mb: 0.0
  });

  const [activeTab, setActiveTab] = useState('db-explorer');

  const loadStatusMetrics = async () => {
    try {
      const data = await fetchStatus();
      setMetrics(data);
    } catch (err) {
      console.error("Error fetching metrics:", err);
    }
  };

  useEffect(() => {
    // Initial fetch
    loadStatusMetrics();

    // Pull status metrics every 5 seconds
    const interval = setInterval(loadStatusMetrics, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Header uptime={metrics.pi_uptime} />

      <main style={{ flex: 1, padding: '2rem', maxWidth: '1600px', margin: '0 auto', width: '100%', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
        
        {/* System Health metrics panel row */}
        <div className="grid-3">
          <MetricsCard metrics={metrics} />
          <ServiceControl service={metrics.service} onRestartComplete={loadStatusMetrics} />
        </div>

        {/* Tab content navigation control panels */}
        <div className="panel">
          <div className="tabs-header" style={{ display: 'flex', gap: '0.75rem', borderBottom: '1px solid var(--glass-border)', paddingBottom: '1rem', marginBottom: '1.5rem' }}>
            <button 
              className={`tab-btn ${activeTab === 'db-explorer' ? 'active' : ''}`}
              onClick={() => setActiveTab('db-explorer')}
              style={{
                background: 'transparent',
                border: activeTab === 'db-explorer' ? '1px solid rgba(139, 92, 246, 0.3)' : '1px solid transparent',
                color: activeTab === 'db-explorer' ? 'white' : 'var(--text-muted)',
                backgroundColor: activeTab === 'db-explorer' ? 'var(--accent-primary-glow)' : 'transparent',
                padding: '0.5rem 1.25rem',
                borderRadius: '8px',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.95rem',
                transition: 'all 0.2s ease'
              }}
            >
              SQLite Watch Requests
            </button>
            <button 
              className={`tab-btn ${activeTab === 'seat-history' ? 'active' : ''}`}
              onClick={() => setActiveTab('seat-history')}
              style={{
                background: 'transparent',
                border: activeTab === 'seat-history' ? '1px solid rgba(139, 92, 246, 0.3)' : '1px solid transparent',
                color: activeTab === 'seat-history' ? 'white' : 'var(--text-muted)',
                backgroundColor: activeTab === 'seat-history' ? 'var(--accent-primary-glow)' : 'transparent',
                padding: '0.5rem 1.25rem',
                borderRadius: '8px',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.95rem',
                transition: 'all 0.2s ease'
              }}
            >
              Seats Historical Charts
            </button>
            <button 
              className={`tab-btn ${activeTab === 'live-logs' ? 'active' : ''}`}
              onClick={() => setActiveTab('live-logs')}
              style={{
                background: 'transparent',
                border: activeTab === 'live-logs' ? '1px solid rgba(139, 92, 246, 0.3)' : '1px solid transparent',
                color: activeTab === 'live-logs' ? 'white' : 'var(--text-muted)',
                backgroundColor: activeTab === 'live-logs' ? 'var(--accent-primary-glow)' : 'transparent',
                padding: '0.5rem 1.25rem',
                borderRadius: '8px',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.95rem',
                transition: 'all 0.2s ease'
              }}
            >
              Real-time Timetable Logs
            </button>
          </div>

          {/* Render active tabs */}
          {activeTab === 'db-explorer' && <WatchesTable />}
          {activeTab === 'seat-history' && <HistoryChart />}
          {activeTab === 'live-logs' && <LogConsole />}
        </div>
      </main>

      <footer style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-dimmed)', fontSize: '0.8rem', borderTop: '1px solid var(--glass-border)', backdropFilter: 'blur(12px)', background: 'rgba(11, 9, 20, 0.6)', marginTop: '3rem' }}>
        <p>&copy; 2026 Universeaty Dashboard &bull; strictly private local administrative interface</p>
      </footer>
    </div>
  );
}
