# Universeaty Admin Dashboard

Local-network administrative interface for the **Universeaty** scraper system. Served by the
Raspberry Pi on port `8085` (`universeaty-dashboard.service`) and styled to match the main app
(dark, monochrome, glassy — Montserrat + shadcn/ui tokens).

## Features

- **Overview stats** — total watches, pending / notified / errored / cancelled counts, unique
  users, watched courses, seat snapshots, logins (24h/7d), oldest pending watch.
- **Service health** — `universeaty.service` status (PID, RAM, uptime, started), last check-cycle
  duration (avg/last/max from the log), email worker sent/failure counts, queue depth, and a
  one-click **Restart Scraper** action (toast feedback instead of browser alerts).
- **Host status** — CPU temp (with 55°/70° thresholds), load average, RAM/disk bars, host uptime,
  SQLite DB and log sizes.
- **Charts (recharts)** — seat openings (last 14d), watches created vs notified per day, and log
  traffic (lines/hour + status-code mix) parsed from the log.
- **Watch requests explorer** — debounced search (course/email), status + term filters, pagination,
  expandable rows with full timestamps and notify-failure details, CSV export, one-click email copy.
- **Top courses & users** — most-watched courses, seat-opening leaders (7d), top users.
- **Live logs** — SSE stream with parsed lines (timestamp, level badge, logger), level filter chips
  with counts, debounced search, pause/resume, clear, auto-scroll toggle, download buffer, and
  reconnect state.

## Architecture

```
dashboard/
├── backend/            Flask app (Waitress, port 8085)
│   ├── run.py          WSGI entrypoint
│   ├── app/
│   │   ├── config.py   Resolves data sources (DB + log) relative to the repo root
│   │   ├── main.py     App setup, SPA serving, JSON API error handlers
│   │   ├── routes/     status.py · database.py · logs.py
│   │   └── utils/      metrics.py · log_tailer.py · log_stats.py · cache.py (TTL)
│   ├── requirements.txt
│   └── static/         Vite build output (gitignored, produced by `npm run build`)
└── frontend/           React 19 + TypeScript + Vite 8 + Tailwind v4 + shadcn/ui + recharts
```

The dashboard reads the same production SQLite DB and log file as the scraper, strictly
**read-only** (`file:...?mode=ro`), with TTL-cached queries so it stays snappy against the
~250 MB production DB.

### API endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/status` | Host + service metrics (both systemd units, uptime seconds) |
| GET | `/api/db/summary` | Legacy summary (counts) |
| GET | `/api/db/overview` | Rich stats + 14-day daily series (watches/snapshots/notified) |
| GET | `/api/db/top` | Top courses, seat openings (7d), top users, terms |
| GET | `/api/db/watches` | Paginated/searchable watches (`page`, `limit`, `search`, `status`, `term`) |
| GET | `/api/logs/stats` | Parsed log stats (levels, HTTP statuses, cycles, email health) |
| GET | `/api/logs/stream` | SSE live log tail (last 80 lines + rotation handling) |
| POST | `/api/service/restart` | `sudo systemctl restart universeaty.service` |

Path resolution can be overridden for local testing via
`DASHBOARD_DATABASE_PATH` / `DASHBOARD_LOG_FILE_PATH` env vars.

## Local development

```bash
# Backend (from dashboard/backend) — venv with flask, flask-cors, waitress
DASHBOARD_DATABASE_PATH=/path/to/course_watches.db \
DASHBOARD_LOG_FILE_PATH=/path/to/timetable_checker.log \
python run.py

# Frontend (from dashboard/frontend)
npm install
npm run dev          # dev server; API points at http://192.168.0.43:8085
npm run build        # type-check + build into ../backend/static
npm run lint
npm run format:check
```

## Deployment

A GitHub push to `master` triggers a webhook (`webhook.service` on the Pi) that runs
`/home/ameen/universeaty_deploy.sh`, which:

1. `git fetch origin master && git reset --hard origin/master`
2. `npm install && npm run build` in `dashboard/frontend` → outputs to `dashboard/backend/static/`
3. Installs `backend/requirements.txt` **and** `dashboard/backend/requirements.txt` into the venv
4. Restarts `universeaty.service` and `universeaty-dashboard.service`

The dashboard is then served properly by the Flask backend (not prebuilt static hosting) on
`http://<pi-ip>:8085` for local-network access.
