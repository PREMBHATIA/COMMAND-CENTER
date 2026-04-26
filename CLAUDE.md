# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Graas Command Center — a Streamlit multi-page dashboard that aggregates business data from Google Sheets, Slack, RSS feeds, and file uploads into a unified monitoring hub for Graas's product lines (Hoppr, Turbo, All-e, Execute) across India and SE Asia.

## Running the App

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app runs on port 8501 by default. No build step — Streamlit hot-reloads on file save.

## Architecture

**Data flow:** Google Sheets → `services/sheets_client.py` (with parquet cache in `data/cache/`, 4hr TTL) → `services/data_processor.py` → Streamlit pages render with Plotly/pandas.

**Key architectural decisions:**
- `sheets_client.py` tries Streamlit Cloud secrets first (`st.secrets["gcp_service_account"]`), then falls back to local `credentials/service_account.json`. If both fail, it serves stale cache.
- Sheet IDs are in environment variables (`HOPPR_SHEET_ID`, `TURBO_SHEET_ID`, `ALLE_SHEET_ID`, `PI_BOT_SHEET_ID`, `REVENUE_SHEET_ID`, `AR_SHEET_ID`).
- `fetch_sheet_tab()` uses first row as headers (with duplicate-name deduplication). `fetch_sheet_tab_raw()` returns integer-indexed columns — used when header rows are complex (Turbo health scores, AR data).
- Finance page uses **Excel file upload** (not Sheets API) — this was an intentional switch after API integration issues.
- Each page in `pages/` is self-contained: it fetches its own data, processes it inline, and renders. No shared state between pages beyond `st.session_state`.

**Services layer:**
- `sheets_client.py` — Google Sheets API + parquet caching
- `data_processor.py` — Pandas transforms for Hoppr/Turbo (daily metrics, WoW calculations, anomaly detection, health score parsing)
- `competitor_tracker.py` — RSS scraping (Google News, Nitter) with 4hr cache, keyword-based alerts
- `slack_notes.py` — Extracts meeting notes and Granola links from Slack GTM channels
- `alerts.py` — Slack webhook alerts for metric drops (Hoppr >50% WoW drop, Turbo accounts below 30)

**Config:** `config.yaml` holds competitor list, alert keywords, and health/revenue thresholds.

## Conventions

- Pages are numbered with prefix (`1_hoppr.py`, `2_turbo.py`, etc.) per Streamlit multi-page convention. The number determines sidebar order.
- Custom CSS is defined inline via `st.markdown()` with `unsafe_allow_html=True` — the dark theme uses indigo (#4F46E5) as primary.
- Use `pd.DataFrame.map()` not `applymap()` (deprecated in pandas 2.x).
- Environment variables are loaded via `python-dotenv` in services, and synced from `st.secrets` on Streamlit Cloud (see top of `sheets_client.py`).

## Deployment

- **Streamlit Cloud** (primary): pushes to `main` auto-deploy. Secrets configured in Streamlit Cloud UI.
- **Heroku**: `Procfile` and `nixpacks.toml` are configured. Runtime: Python 3.12.13.

## Environment Variables

Required for full functionality:
- `GOOGLE_CREDENTIALS_PATH` — path to service account JSON (default: `credentials/service_account.json`)
- `HOPPR_SHEET_ID`, `TURBO_SHEET_ID`, `ALLE_SHEET_ID`, `PI_BOT_SHEET_ID`, `REVENUE_SHEET_ID`, `AR_SHEET_ID`
- `ANTHROPIC_API_KEY` — for Ask Graas chat page
- `SLACK_BOT_TOKEN`, `SLACK_WEBHOOK_URL` — for meeting notes and alerts
