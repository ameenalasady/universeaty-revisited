# Universeaty Dashboard

A centralized local administrative interface for the **Universeaty** scraper system. This dashboard provides real-time system monitoring, scraper service controls, database exploration, and live log tailing for a host server (e.g., Raspberry Pi).

## Features

- **Host Hardware Status**: Real-time tracking of host CPU load average, RAM footprint, disk usage, active log size, SQLite database size, and CPU temperature.
- **Service Control Panel**: Interactive administrative commands to monitor status (PID, memory, uptime) and gracefully restart the main scraper service.
- **SQLite Watch Explorer**: Fully featured database explorer to search, filter, and page through active course watch requests (Pending, Notified, Errored, Cancelled).
- **Real-Time Timetable Logs**: Live connection to the timetable checker logs stream using Server-Sent Events (SSE) with dynamic color-coding and severities.

## Architecture

The dashboard is split into two components:

1. **Frontend (`/frontend`)**: A React application built with Vite and designed around dark-mode visual hierarchy, featuring soft glassmorphic panels, ambient gradients, and smooth hover translations.
2. **Backend (`/backend`)**: A lightweight Python server built with Flask and served via a high-performance Waitress WSGI runner on port `8085`.

## Local Development

To run the dashboard in development mode locally:

```bash
# 1. Start the React dev server (from dashboard/frontend)
npm run dev

# 2. Run the Flask backend (from dashboard/backend)
python run.py
```
