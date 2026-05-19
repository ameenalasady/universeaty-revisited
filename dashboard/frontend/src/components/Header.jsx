// dashboard/frontend/src/components/Header.jsx
import React from 'react';

export default function Header({ uptime }) {
  return (
    <header style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '1.25rem 2rem',
      background: '#18181b',
      borderBottom: '1px solid #27272a',
      position: 'sticky',
      top: 0,
      zIndex: 100
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <h1 style={{
          fontSize: '1.25rem',
          fontWeight: 600,
          letterSpacing: '-0.5px',
          color: '#fafafa'
        }}>Universeaty</h1>
        <span style={{
          background: '#27272a',
          color: '#fafafa',
          fontSize: '0.7rem',
          fontWeight: 600,
          textTransform: 'uppercase',
          padding: '0.2rem 0.6rem',
          borderRadius: '4px',
          letterSpacing: '0.5px',
          border: '1px solid #3f3f46'
        }}>Private Admin</span>
      </div>
      <div style={{
        background: '#18181b',
        border: '1px solid #27272a',
        padding: '0.35rem 0.75rem',
        borderRadius: '6px',
        fontSize: '0.8rem',
        color: '#a1a1aa',
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem'
      }}>
        <span style={{
          display: 'inline-block',
          width: '6px',
          height: '6px',
          backgroundColor: '#10b981',
          borderRadius: '50%'
        }}></span>
        Uptime: {uptime}
      </div>
    </header>
  );
}
