"""FastAPI application: rates dashboard, first-time buyer assistant, and JSON APIs."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, validator

from app.agent_service import run_chat
from app.config import get_settings
from app.rates import refresh_today_snapshot, series_for_chart
from app.scheduler import start_daily_job
from app.store import RateStore

BASE = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE / "templates"))


class ChatLine(BaseModel):
    role: str
    content: str = Field(..., max_length=12000)

    @validator("role")
    def role_ok(cls, v):
        if v not in ("user", "assistant"):
            raise ValueError("role must be user or assistant")
        return v


class ChatRequest(BaseModel):
    messages: List[ChatLine]

    @validator("messages")
    def messages_len(cls, v):
        if not v:
            raise ValueError("messages must not be empty")
        if len(v) > 24:
            raise ValueError("too many messages")
        return v


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    store = RateStore(settings.database_path)
    store.init()
    app.state.settings = settings
    app.state.store = store
    await refresh_today_snapshot(settings, store)
    app.state.scheduler = start_daily_job(settings, store)
    yield
    app.state.scheduler.shutdown(wait=False)


app = FastAPI(
    title="US Homes Mortgage Agent",
    description=(
        "National 30y/15y mortgage benchmarks from FRED, daily snapshots, "
        "and a first-time buyer LLM assistant with tool calling."
    ),
    version="1.0.0",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request},
    )


@app.get("/assistant", response_class=HTMLResponse)
async def assistant_page(request: Request):
    return templates.TemplateResponse(
        "assistant.html",
        {"request": request},
    )


@app.get("/api/rates/today")
async def api_rates_today(request: Request):
    store: RateStore = request.app.state.store
    snap = store.latest_snapshot()
    if not snap:
        raise HTTPException(status_code=503, detail="No rate data yet")
    return {
        "rate_30y": snap.rate_30y,
        "rate_15y": snap.rate_15y,
        "fred_observation_date_30y": snap.source_obs_date_30.isoformat(),
        "fred_observation_date_15y": snap.source_obs_date_15.isoformat(),
        "snapshot_date": snap.snapshot_date.isoformat(),
        "fetched_at": snap.fetched_at.isoformat(timespec="seconds"),
    }


@app.get("/api/rates/chart")
async def api_rates_chart(
    request: Request,
    time_range: str = Query("30d", alias="range"),
):
    settings = request.app.state.settings
    try:
        return await series_for_chart(settings, time_range)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid range. Use 7d, 30d, 90d, 1y.")
    except Exception:
        raise HTTPException(status_code=502, detail="Could not load chart data from FRED.")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/assistant/status")
async def assistant_status(request: Request):
    settings = request.app.state.settings
    return {
        "assistant_enabled": bool(settings.openai_api_key),
        "model": settings.openai_model if settings.openai_api_key else None,
    }


@app.post("/api/chat")
async def api_chat(request: Request, body: ChatRequest):
    settings = request.app.state.settings
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="Assistant is not configured. Set OPENAI_API_KEY (or compatible LLM key) in .env",
        )
    store: RateStore = request.app.state.store
    turns = []
    for m in body.messages:
        c = (m.content or "").strip()
        if not c:
            continue
        turns.append({"role": m.role, "content": c})
    if not turns:
        raise HTTPException(status_code=400, detail="No non-empty messages.")
    try:
        reply = await run_chat(settings, store, turns)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Assistant upstream error. Try again shortly.",
        )
    return {"reply": reply}
