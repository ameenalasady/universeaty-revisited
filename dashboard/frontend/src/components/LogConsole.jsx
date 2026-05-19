// dashboard/frontend/src/components/LogConsole.jsx
import React, { useEffect, useState, useRef } from 'react';
import { getLogsStreamUrl } from '../utils/api';

export default function LogConsole() {
  const [logs, setLogs] = useState([]);
  const [status, setStatus] = useState('connecting'); // connecting, streaming, disconnected
  const consoleBodyRef = useRef(null);

  useEffect(() => {
    // Add initial system startup message
    const initialMsg = {
      id: Date.now() + Math.random(),
      text: `[SYSTEM] ${new Date().toISOString().replace('T', ' ').substring(0, 19)} - Opening connection to Server-Sent Events logs stream on Raspberry Pi...`,
      severity: 'info'
    };
    setLogs([initialMsg]);

    const logsUrl = getLogsStreamUrl();
    const source = new EventSource(logsUrl);

    source.onopen = () => {
      setStatus('streaming');
      const connMsg = {
        id: Date.now() + Math.random(),
        text: `[SYSTEM] ${new Date().toISOString().replace('T', ' ').substring(0, 19)} - Server-Sent Events logs stream initialized successfully.`,
        severity: 'info'
      };
      setLogs(prev => [...prev, connMsg]);
    };

    source.onmessage = (event) => {
      const rawLine = event.data;
      if (!rawLine.trim()) return;

      let severity = 'info';
      if (rawLine.includes(' - CRITICAL - ')) {
        severity = 'critical';
      } else if (rawLine.includes(' - ERROR - ')) {
        severity = 'error';
      } else if (rawLine.includes(' - WARNING - ')) {
        severity = 'warning';
      }

      const newLog = {
        id: Date.now() + Math.random(),
        text: rawLine,
        severity
      };

      setLogs(prev => {
        const updated = [...prev, newLog];
        // Capping logs buffer at 1000 lines for low memory footprint
        if (updated.length > 1000) {
          updated.shift();
        }
        return updated;
      });
    };

    source.onerror = () => {
      setStatus('disconnected');
      const errMsg = {
        id: Date.now() + Math.random(),
        text: `[SYSTEM] ${new Date().toISOString().replace('T', ' ').substring(0, 19)} - Stream disconnected. Attempting automatic reconnection...`,
        severity: 'error'
      };
      setLogs(prev => [...prev, errMsg]);
    };

    return () => {
      source.close();
    };
  }, []);

  // Auto-scroll effect
  useEffect(() => {
    if (consoleBodyRef.current) {
      consoleBodyRef.current.scrollTop = consoleBodyRef.current.scrollHeight;
    }
  }, [logs]);

  const severityStyles = {
    info: { borderLeft: '2px solid #3f3f46', color: '#a1a1aa' },
    warning: { borderLeft: '2px solid #f59e0b', color: '#fcd34d' },
    error: { borderLeft: '2px solid #ef4444', color: '#fca5a5' },
    critical: { borderLeft: '2px solid #ef4444', color: '#f87171', fontWeight: 'bold', background: 'rgba(239, 68, 68, 0.05)' }
  };

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          Connecting directly to logs stream. Logs are filtered and color-coded dynamically.
        </p>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <span style={{
            display: 'inline-block',
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            backgroundColor: status === 'streaming' ? '#10b981' : status === 'connecting' ? '#f59e0b' : '#ef4444'
          }}></span>
          <span style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            {status === 'streaming' ? 'Streaming Live' : status === 'connecting' ? 'Connecting' : 'Disconnected'}
          </span>
        </div>
      </div>

      <div className="console-header" style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '0.6rem 1rem',
        background: '#18181b',
        border: '1px solid #27272a',
        borderBottom: 'none',
        borderRadius: '6px 6px 0 0'
      }}>
        <div style={{ display: 'flex', gap: '6px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#ef4444' }}></div>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#f59e0b' }}></div>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#10b981' }}></div>
        </div>
        <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.7rem', color: 'var(--text-dimmed)', textTransform: 'uppercase' }}>
          timetable_checker.log
        </div>
        <div></div>
      </div>
      <div 
        ref={consoleBodyRef}
        className="console-body" 
        style={{
          background: '#09090b',
          border: '1px solid #27272a',
          borderRadius: '0 0 6px 6px',
          padding: '1rem',
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '0.8rem',
          height: '480px',
          overflowY: 'auto',
          color: '#e4e4e7',
          lineHeight: 1.5
        }}
      >
        {logs.map(log => (
          <div 
            key={log.id} 
            style={{
              marginBottom: '0.35rem',
              whiteSpace: 'pre-wrap',
              paddingLeft: '8px',
              ...severityStyles[log.severity]
            }}
          >
            {log.text}
          </div>
        ))}
      </div>
    </div>
  );
}
