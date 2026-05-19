// dashboard/frontend/src/components/MetricsCard.jsx
import React from 'react';

export default function MetricsCard({ metrics }) {
  const ram = metrics.ram || { total_mb: 0, used_mb: 0, free_mb: 0, percent: 0.0 };
  const disk = metrics.disk || { total_mb: 0, used_mb: 0, free_mb: 0, percent: 0.0 };
  const cpuTemp = metrics.cpu_temp || 0.0;
  const cpuLoad = metrics.cpu_load || "0.00 0.00 0.00";
  const dbSize = metrics.db_size_mb || 0.0;
  const logSize = metrics.log_size_mb || 0.0;

  const tempColor = cpuTemp > 70 ? 'var(--accent-error)' : cpuTemp > 55 ? 'var(--accent-warning)' : 'var(--accent-success)';

  return (
    <>
      {/* Card 1: RAM & Disk Usage progress */}
      <div className="panel">
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #27272a', paddingBottom: '0.75rem' }}>
            <h3 style={{ fontSize: '0.85rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Host Status (Raspberry Pi)</h3>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: tempColor }}>{cpuTemp} °C</span>
          </div>
          
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>RAM Usage</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'white' }}>{ram.percent}%</div>
            </div>
            <div style={{ fontSize: '1.8rem', fontWeight: 700, color: 'white', display: 'flex', alignItems: 'baseline', gap: '0.25rem', marginTop: '0.25rem' }}>
              {ram.used_mb} <span style={{ fontSize: '1rem', fontWeight: 500, color: 'var(--text-muted)' }}>/ {ram.total_mb} MB</span>
            </div>
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${ram.percent}%`, background: '#fafafa' }}></div>
            </div>
          </div>

          <div style={{ marginTop: '0.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Disk Space (/)</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'white' }}>{disk.percent}%</div>
            </div>
            <div style={{ fontSize: '1.8rem', fontWeight: 700, color: 'white', display: 'flex', alignItems: 'baseline', gap: '0.25rem', marginTop: '0.25rem' }}>
              {Math.round(disk.used_mb / 1024)} <span style={{ fontSize: '1rem', fontWeight: 500, color: 'var(--text-muted)' }}>/ {Math.round(disk.total_mb / 1024)} GB</span>
            </div>
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${disk.percent}%`, background: '#a1a1aa' }}></div>
            </div>
          </div>
        </div>
      </div>

      {/* Card 2: Files Storage & CPU stats */}
      <div className="panel" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', width: '100%' }}>
          <h3 style={{ fontSize: '0.85rem', color: 'var(--text-muted)', textTransform: 'uppercase', borderBottom: '1px solid #27272a', paddingBottom: '0.75rem' }}>Files Storage</h3>
          
          <div style={{ display: 'flex', justifycontent: 'space-between', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-dimmed)', textTransform: 'uppercase' }}>SQLite Database</span>
              <strong style={{ display: 'block', fontSize: '1.3rem', fontWeight: 700, color: 'white', marginTop: '0.15rem' }}>{dbSize} MB</strong>
            </div>
            <div style={{ textAlign: 'right' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-dimmed)', textTransform: 'uppercase' }}>Active Logs Size</span>
              <strong style={{ display: 'block', fontSize: '1.3rem', fontWeight: 700, color: 'white', marginTop: '0.15rem' }}>{logSize} MB</strong>
            </div>
          </div>

          <div style={{ background: '#18181b', border: '1px solid #27272a', padding: '0.85rem', borderRadius: '6px', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
              <span>CPU Load Average:</span>
              <strong style={{ color: 'white', fontFamily: "'JetBrains Mono', monospace" }}>{cpuLoad}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Local Pi IP:</span>
              <strong style={{ color: 'white', fontFamily: "'JetBrains Mono', monospace" }}>192.168.0.43</strong>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
