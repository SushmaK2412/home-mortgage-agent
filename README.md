# US homes mortgage rates dashboard

Small FastAPI app that shows the latest **30-year** and **15-year** fixed mortgage rates (national averages from the Freddie Mac Primary Mortgage Market Survey, via **FRED**), stores a daily snapshot in SQLite, refreshes on a schedule, and charts history for a selectable window.

## Is this realistic?

Yes. What is **not** realistic is scraping Yahoo Finance article pages: those pages are editorial HTML, not a stable API, and automated scraping can conflict with site terms.

This project uses the **St. Louis Fed FRED API** for series:

- `MORTGAGE30US` — 30-year fixed
- `MORTGAGE15US` — 15-year fixed

Those series are **weekly** (Freddie Mac’s survey), not tick-by-tick daily. A job that runs every morning still makes sense: it picks up the newest FRED observation as soon as it exists. Between weekly releases, the latest value is unchanged; the UI explains this.

## Requirements

- Python 3.7+ (tested with 3.7)
- A **free** FRED API key: https://fred.stlouisfed.org/docs/api/api_key.html

Put the FRED key in `.env` (see `.env.example`). For the **first-time buyer assistant** (`/assistant`), add an **OpenAI API key** (`OPENAI_API_KEY`). The rates page works without OpenAI; the chat does not.

## Setup

```bash
cd MortgageAgent
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set FRED_API_KEY=... and optionally OPENAI_API_KEY=... for /assistant
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://127.0.0.1:8000 — **First-time buyer assistant:** http://127.0.0.1:8000/assistant

## Configuration

| Variable        | Meaning                                      |
|----------------|-----------------------------------------------|
| `FRED_API_KEY` | Required. Free key from FRED.                 |
| `SCHEDULE_TZ`  | IANA timezone for the 9:00 daily job (default `America/New_York`). |
| `DATABASE_PATH`| SQLite file path (default `data/mortgage_rates.db`). |
| `OPENAI_API_KEY` | Optional. Enables `/assistant` LLM chat. |
| `OPENAI_MODEL` | Optional. Default `gpt-4o-mini`. |
| `OPENAI_BASE_URL` | Optional. Default `https://api.openai.com/v1`. |

## API

- `GET /api/rates/today` — Latest stored snapshot (after startup fetch or scheduled job).
- `GET /api/rates/chart?range=7d|30d|90d|1y` — Observation series from FRED for the chart.
- `GET /api/health` — Liveness check.
- `GET /api/assistant/status` — Whether the assistant is configured (`OPENAI_API_KEY` set).
- `POST /api/chat` — Body `{"messages":[{"role":"user"|"assistant","content":"..."}]}`. Returns `{"reply":"..."}`. No messages are stored server-side.

## Open source and GitHub

- **Do not commit** `.env` (contains `FRED_API_KEY`). It is listed in `.gitignore`.
- **Local SQLite** used for cached FRED snapshots lives under `data/` by default (`data/mortgage_rates.db`). The `data/` folder and `*.db` patterns are **gitignored**, so your local test database is **not** pushed when you publish the repo.
- Anyone who clones the repo creates a **fresh empty DB** on first run after configuring `.env`.

## Production notes

- Run behind a reverse proxy with TLS as usual.
- Point a process manager (systemd, Docker, etc.) at `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- The scheduler runs in-process; for multiple replicas, use an external scheduler (e.g. cron + `curl` hitting a refresh endpoint) only if you add such an endpoint later (not included by default).
