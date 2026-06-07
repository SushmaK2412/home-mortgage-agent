# US Homes Mortgage Agent

Open-source FastAPI application for U.S. homebuyers: a **national rates dashboard** (FRED-backed) and a **first-time buyer assistant** powered by an LLM with **tool calling**. Benchmark data is cached in SQLite; chat history stays in the browser only.

## What this app does

| Surface | Route | Purpose |
|---------|-------|---------|
| **Rates & chart** | `/` | Latest **30-year** and **15-year** national fixed benchmarks, plus an interactive history chart (7d / 30d / 90d / 1y). |
| **First-time buyers** | `/assistant` | Conversational **education** (pre-approval, P&amp;I vs PITI, Loan Estimates, rate context). Uses an LLM with tools grounded in the same FRED snapshots and deterministic payment math. |

This is **not** a lender portal, credit pull, or personalized legal/tax advice. It is a small, forkable reference for **macro transparency** plus **responsible LLM integration**.

## Features

- **FRED API** — series `MORTGAGE30US` and `MORTGAGE15US` (Freddie Mac weekly PMMS averages).
- **Daily scheduler** — refreshes a SQLite snapshot at **09:00** in `SCHEDULE_TZ` (default `America/New_York`).
- **Chart.js** — range selector with loading state for slower FRED windows.
- **LLM assistant** — OpenAI Chat Completions by default; any **OpenAI-compatible** `/v1/chat/completions` endpoint via `OPENAI_BASE_URL`.
- **Agent tools** — `get_benchmark_rates` (SQLite), `estimate_monthly_pi` (Python amortization; P&amp;I only).
- **Privacy** — no user accounts; **no server-side chat logs**; do not commit `.env`.

## Data expectations

FRED PMMS series are **weekly**, not daily. The job runs daily to pick up new observations as soon as they publish; between releases the headline rate may be unchanged. The UI shows **FRED observation dates** so that behavior is clear.

Scraping Yahoo Finance or similar article pages is intentionally **not** used—those pages are unstable HTML and poor programmatic sources.

## Requirements

- Python **3.7+**
- **FRED API key** (free): https://fred.stlouisfed.org/docs/api/api_key.html
- **LLM API key** for `/assistant` — this repo documents **OpenAI** (`OPENAI_API_KEY`); you may point `OPENAI_BASE_URL` at another compatible provider if it supports **tools / function calling**.

## Setup

```bash
git clone https://github.com/SushmaK2412/home-mortgage-agent.git
cd home-mortgage-agent   # or your local folder name
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Set FRED_API_KEY=... and OPENAI_API_KEY=... (assistant)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **Rates:** http://127.0.0.1:8000/
- **Assistant:** http://127.0.0.1:8000/assistant

Rates work with **FRED only**. The assistant returns **503** until `OPENAI_API_KEY` is set.

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `FRED_API_KEY` | Yes | FRED macro data for rates and chart. |
| `SCHEDULE_TZ` | No | IANA timezone for the 09:00 snapshot job (default `America/New_York`). |
| `DATABASE_PATH` | No | SQLite path for benchmark snapshots (default `data/mortgage_rates.db`). |
| `OPENAI_API_KEY` | For assistant | LLM provider API key. |
| `OPENAI_MODEL` | No | Default `gpt-4o-mini`. |
| `OPENAI_BASE_URL` | No | Default `https://api.openai.com/v1`; override for compatible gateways. |

## Project layout

```
app/
  main.py           # FastAPI routes, lifespan, chat API
  agent_service.py  # LLM prompts, tool loop, provider HTTP client
  fred_client.py    # FRED observations client
  rates.py          # Snapshot refresh and chart series
  store.py          # SQLite benchmark snapshots (no chat storage)
  mortgage_math.py  # Deterministic P&I for agent tools
  scheduler.py      # Daily 09:00 job
  config.py         # Settings from .env
templates/          # Rates and assistant pages (sidebar nav)
static/             # CSS, Chart.js client, chat client
docs/               # Tech magazine article draft
```

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Rates dashboard (HTML). |
| GET | `/assistant` | First-time buyer chat UI (HTML). |
| GET | `/api/rates/today` | Latest benchmark snapshot JSON. |
| GET | `/api/rates/chart?range=7d\|30d\|90d\|1y` | Chart series from FRED. |
| GET | `/api/assistant/status` | Whether the assistant is configured. |
| POST | `/api/chat` | `{"messages":[{"role":"user"\|"assistant","content":"..."}]}` → `{"reply":"..."}`. |
| GET | `/api/health` | Liveness check. |

## Open source and secrets

- **Never commit** `.env` — it is in `.gitignore`.
- **Local SQLite** under `data/` and `*.db` files are gitignored; clones start with an empty DB on first run.
- Chat messages are **not** persisted in SQLite; each request sends browser-held history to the LLM provider (see their terms for retention).

## Production notes

- Terminate TLS at a reverse proxy; run `uvicorn app.main:app --host 0.0.0.0 --port 8000` under a process manager.
- In-process APScheduler runs **per process**; multiple replicas need external scheduling or a single worker for the cron job.
- LLM usage may incur **provider billing**; add rate limits and monitoring for public deployments.

## Further reading

Architecture and design rationale: [`docs/TECH_MAGAZINE_ARTICLE.md`](docs/TECH_MAGAZINE_ARTICLE.md).
