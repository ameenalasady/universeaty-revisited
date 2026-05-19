// dashboard/frontend/src/components/ServiceControl.jsx
import React, { useState } from 'react';
import { restartScraperService } from '../utils/api';

export default function ServiceControl({ service, onRestartComplete }) {
  const [loading, setLoading] = useState(false);

  const handleRestart = async () => {
    const confirmRestart = window.confirm("Are you sure you want to restart the main Universeaty scraper service?");
    if (!confirmRestart) return;

    setLoading(true);
    try {
      const data = await restartScraperService();
      if (data.status === 'success') {
        alert("Scraper service restarted successfully!");
      } else {
        alert("Error: " + data.message);
      }
    } catch (err) {
      alert(err.message || "Failed to contact API for service restart.");
      console.error(err);
    } finally {
      setLoading(false);
      if (onRestartComplete) onRestartComplete();
    }
  };

  const isActive = service.active_state === 'active';
  const badgeClass = isActive ? 'status-active' : 'status-inactive';

  return (
    <div className="panel" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '100%' }}>
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
          <div>
            <h3 style={{ fontSize: '0.85rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '0.25rem' }}>Scraper Service</h3>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'white' }}>universeaty.service</h2>
          </div>
          <span className={`service-status-badge ${badgeClass}`} style={{
            padding: '0.35rem 0.75rem',
            borderRadius: '9999px',
            fontSize: '0.75rem',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            background: isActive ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
            color: isActive ? 'var(--accent-success)' : 'var(--accent-error)',
            border: isActive ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(239, 68, 68, 0.3)',
            boxShadow: isActive ? '0 0 12px rgba(16, 185, 129, 0.1)' : 'none'
          }}>
            {service.active_state || 'unknown'}
          </span>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '1rem',
          marginBottom: '1.5rem',
          background: 'rgba(255, 255, 255, 0.02)',
          padding: '0.85rem',
          borderRadius: '12px',
          border: '1px solid rgba(255, 255, 255, 0.02)'
        }}>
          <div>
            <span style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-dimmed)', textTransform: 'uppercase', letterSpacing: '0.25px' }}>PID</span>
            <strong style={{ display: 'block', fontSize: '0.95rem', color: 'var(--text-main)', marginTop: '0.15rem' }}>{service.pid || '--'}</strong>
          </div>
          <div>
            <span style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-dimmed)', textTransform: 'uppercase', letterSpacing: '0.25px' }}>RAM Footprint</span>
            <strong style={{ display: 'block', fontSize: '0.95rem', color: 'var(--text-main)', marginTop: '0.15rem' }}>{service.pid > 0 ? `${service.memory_mb} MB` : '--'}</strong>
          </div>
          <div style={{ gridColumn: 'span 2', marginTop: '0.25rem', borderTop: '1px solid rgba(255, 255, 255, 0.02)', paddingTop: '0.5rem' }}>
            <span style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-dimmed)', textTransform: 'uppercase', letterSpacing: '0.25px' }}>Uptime</span>
            <strong style={{ display: 'block', fontSize: '0.95rem', color: 'var(--text-main)', marginTop: '0.15rem' }}>{service.uptime || '--'}</strong>
          </div>
        </div>
      </div>

      <button 
        onClick={handleRestart} 
        disabled={loading}
        className="restart-button"
        style={{
          background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.2) 0%, rgba(217, 70, 239, 0.2) 100%)',
          border: '1px solid rgba(139, 92, 246, 0.4)',
          color: 'white',
          padding: '0.6rem 1.2rem',
          borderRadius: '8px',
          fontWeight: 600,
          cursor: loading ? 'not-allowed' : 'pointer',
          transition: 'all 0.2s ease',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '0.5rem',
          width: '100%',
          opacity: loading ? 0.6 : 1
        }}
      >
        <svg 
          className={loading ? 'animate-spin' : ''} 
          width="14" 
          height="14" 
          viewBox="0 0 24 24" 
          fill="none" 
          stroke="currentColor" 
          strokeWidth="2.5" 
          strokeLinecap="round" 
          strokeLinejoin="round"
        >
          <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
        </svg>
        {loading ? 'Restarting...' : 'Restart Scraper'}
      </button>
    </div>
  );
}
