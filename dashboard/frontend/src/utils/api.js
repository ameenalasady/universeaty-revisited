// dashboard/frontend/src/utils/api.js

// During development (npm run dev), redirect requests to the Pi's server.
// In production (served by Flask), use relative URLs.
export const API_BASE = import.meta.env.DEV ? 'http://192.168.0.43:8085' : '';

export async function fetchStatus() {
  const res = await fetch(`${API_BASE}/api/status`);
  if (!res.ok) throw new Error('Failed to fetch hardware status');
  return res.json();
}

export async function fetchDbSummary() {
  const res = await fetch(`${API_BASE}/api/db/summary`);
  if (!res.ok) throw new Error('Failed to fetch DB summary');
  return res.json();
}

export async function fetchWatches(page = 1, limit = 12, search = '', status = '') {
  const url = `${API_BASE}/api/db/watches?page=${page}&limit=${limit}&search=${encodeURIComponent(search)}&status=${status}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch watch requests');
  return res.json();
}

export async function fetchTimelineCourses() {
  const res = await fetch(`${API_BASE}/api/db/snapshots/courses`);
  if (!res.ok) throw new Error('Failed to fetch historical courses list');
  return res.json();
}

export async function fetchTimelineChart(courseCode) {
  const url = `${API_BASE}/api/db/snapshots/timeline?course_code=${encodeURIComponent(courseCode)}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch historical timeline data');
  return res.json();
}

export async function restartScraperService() {
  const res = await fetch(`${API_BASE}/api/service/restart`, { method: 'POST' });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.message || 'Failed to restart scraper service');
  }
  return res.json();
}

export function getLogsStreamUrl() {
  return `${API_BASE}/api/logs/stream`;
}
