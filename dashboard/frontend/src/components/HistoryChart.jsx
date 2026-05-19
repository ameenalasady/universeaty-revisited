// dashboard/frontend/src/components/HistoryChart.jsx
import React, { useState, useEffect, useRef } from 'react';
import { Chart, registerables } from 'chart.js';
import 'chartjs-adapter-date-fns';
import { fetchTimelineCourses, fetchTimelineChart } from '../utils/api';

// Register all Chart.js modules
Chart.register(...registerables);

export default function HistoryChart() {
  const [courses, setCourses] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState('');
  const [infoText, setInfoText] = useState('Select a course to view historical seat timelines parsed from logs.');
  const chartRef = useRef(null);
  const chartInstance = useRef(null);

  const loadCourses = async () => {
    try {
      const data = await fetchTimelineCourses();
      setCourses(data.courses || []);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadCourses();
  }, []);

  useEffect(() => {
    if (!selectedCourse) {
      setInfoText('Select a course to view historical seat timelines parsed from logs.');
      if (chartInstance.current) {
        chartInstance.current.destroy();
        chartInstance.current = null;
      }
      return;
    }

    const renderChart = async () => {
      try {
        const data = await fetchTimelineChart(selectedCourse);
        const sectionsList = Object.keys(data.sections || {});
        let totalPoints = 0;
        sectionsList.forEach(s => totalPoints += data.sections[s].length);

        setInfoText(`Found ${sectionsList.length} sections with ${totalPoints} historical seat data points.`);

        const colors = [
          '#fafafa', '#a1a1aa', '#71717a', '#10b981', '#f59e0b', '#ef4444', 
          '#3b82f6', '#ec4899', '#14b8a6', '#84cc16'
        ];

        const datasets = [];
        let colorIdx = 0;

        sectionsList.forEach(secName => {
          const points = data.sections[secName];
          const dataPoints = points.map(pt => ({
            x: new Date(pt.captured_at.replace(" ", "T")),
            y: pt.open_seats
          }));

          datasets.push({
            label: `${secName} (Open Seats)`,
            data: dataPoints,
            borderColor: colors[colorIdx % colors.length],
            backgroundColor: colors[colorIdx % colors.length] + '15',
            borderWidth: 2,
            tension: 0.15,
            pointRadius: 3,
            pointHoverRadius: 6,
            fill: false
          });
          colorIdx++;
        });

        if (chartInstance.current) {
          chartInstance.current.destroy();
        }

        const ctx = chartRef.current.getContext('2d');
        chartInstance.current = new Chart(ctx, {
          type: 'line',
          data: { datasets },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
              intersect: false,
              mode: 'index'
            },
            scales: {
              x: {
                type: 'time',
                time: {
                  parser: 'yyyy-MM-dd HH:mm:ss',
                  tooltipFormat: 'MMM d, yyyy h:mm a',
                  displayFormats: {
                    hour: 'MMM d, h a',
                    day: 'MMM d'
                  }
                },
                grid: { color: '#27272a' },
                ticks: { color: '#a1a1aa' }
              },
              y: {
                beginAtZero: true,
                grid: { color: '#27272a' },
                ticks: { color: '#a1a1aa', stepSize: 1 }
              }
            },
            plugins: {
              legend: {
                labels: { color: '#fafafa', font: { family: "'Inter', sans-serif" } }
              },
              tooltip: {
                backgroundColor: '#18181b',
                titleColor: '#fafafa',
                bodyColor: '#fafafa',
                borderColor: '#27272a',
                borderWidth: 1
              }
            }
          }
        });

      } catch (err) {
        console.error(err);
      }
    };

    renderChart();

    return () => {
      if (chartInstance.current) {
        chartInstance.current.destroy();
        chartInstance.current = null;
      }
    };
  }, [selectedCourse]);

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1.5rem' }}>
        <label style={{ fontWeight: 500, color: 'var(--text-muted)', fontSize: '0.85rem' }}>SELECT WATCHED COURSE HISTORY:</label>
        <select 
          value={selectedCourse}
          onChange={(e) => setSelectedCourse(e.target.value)}
          style={{
            minWidth: '250px'
          }}
        >
          <option value="">Select a course...</option>
          {courses.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <span style={{ fontSize: '0.8rem', color: 'var(--text-dimmed)' }}>{infoText}</span>
      </div>

      <div style={{ position: 'relative', height: '400px', width: '100%' }}>
        <canvas ref={chartRef}></canvas>
      </div>
    </div>
  );
}
