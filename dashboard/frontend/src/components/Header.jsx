// dashboard/frontend/src/components/Header.jsx
import React from 'react';

export default function Header({ uptime }) {
  return (
    <header style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '1.5rem 2rem',
      backdropFilter: 'blur(12px)',
      background: 'rgba(11, 9, 20, 0.6)',
      borderBottom: '1px solid var(--glass-border)',
      position: 'sticky',
      top: 0,
      zIndex: 100
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <h1 style={{
          fontSize: '1.5rem',
          fontWeight: 700,
          letterSpacing: '-0.5px',
          background: 'linear-gradient(135deg, #fff 0%, #a78bfa 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent'
        }}>Universeaty</h1>
        <span style={{
          background: 'linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%)',
          color: 'white',
          fontSize: '0.7rem',
          fontWeight: 600,
          textTransform: 'uppercase',
          padding: '0.25rem 0.6rem',
          borderRadius: '9999px',
          letterSpacing: '0.5px',
          boxShadow: '0 0 10px rgba(139, 92, 246, 0.4)'
        }}>Private Admin</span>
      </div>
      <div style={{
        background: 'var(--glass-bg)',
        border: '1px solid var(--glass-border)',
        padding: '0.4rem 0.8rem',
        borderRadius: '9999px',
        fontSize: '0.85rem',
        color: 'var(--text-muted)',
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem'
      }}>
        <span style={{
          display: 'inline-block',
          width: '8px',
          height: '8px',
          backgroundColor: 'var(--accent-success)',
          borderRadius: '50%',
          boxShadow: '0 0 8px var(--accent-success)'
        }}></span>
        Uptime: {uptime}
      </div>
    </header>
  );
}
