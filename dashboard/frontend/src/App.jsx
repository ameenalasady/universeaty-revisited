// dashboard/frontend/src/App.jsx
import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import MetricsCard from './components/MetricsCard';
import ServiceControl from './components/ServiceControl';
import WatchesTable from './components/WatchesTable';
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
          <div className="tabs-header" style={{
            display: 'inline-flex',
            background: '#18181b',
            border: '1px solid #27272a',
            padding: '4px',
            borderRadius: '8px',
            gap: '4px',
            marginBottom: '1.5rem'
          }}>
            <button 
              className={`tab-btn ${activeTab === 'db-explorer' ? 'active' : ''}`}
              onClick={() => setActiveTab('db-explorer')}
              style={{
                background: activeTab === 'db-explorer' ? '#27272a' : 'transparent',
                border: 'none',
                color: activeTab === 'db-explorer' ? '#fafafa' : '#a1a1aa',
                padding: '0.45rem 1.25rem',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: 500,
                fontSize: '0.85rem',
                transition: 'all 0.15s ease'
              }}
            >
              SQLite Watch Requests
            </button>
            <button 
              className={`tab-btn ${activeTab === 'live-logs' ? 'active' : ''}`}
              onClick={() => setActiveTab('live-logs')}
              style={{
                background: activeTab === 'live-logs' ? '#27272a' : 'transparent',
                border: 'none',
                color: activeTab === 'live-logs' ? '#fafafa' : '#a1a1aa',
                padding: '0.45rem 1.25rem',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: 500,
                fontSize: '0.85rem',
                transition: 'all 0.15s ease'
              }}
            >
              Real-time Timetable Logs
            </button>
          </div>

          {/* Render active tabs */}
          {activeTab === 'db-explorer' && <WatchesTable />}
          {activeTab === 'live-logs' && <LogConsole />}
        </div>
      </main>

      <footer style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-dimmed)', fontSize: '0.8rem', borderTop: '1px solid var(--glass-border)', backdropFilter: 'blur(12px)', background: 'rgba(11, 9, 20, 0.6)', marginTop: '3rem' }}>
        <p>&copy; 2026 Universeaty Dashboard</p>
      </footer>
    </div>
  );
}
