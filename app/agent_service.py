"""First-time buyer LLM assistant: system prompt, tool loop, OpenAI-compatible API."""

import json
import logging
from typing import Any, Dict, List

import httpx

from app.config import Settings
from app.mortgage_math import monthly_principal_interest
from app.store import RateStore

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a mortgage education assistant for first-time U.S. homebuyers.

Rules:
- Be clear, practical, and supportive. Use short sections or bullets when helpful.
- You are not a lawyer, tax advisor, or loan officer. Do not give personalized legal/tax advice. Say when they should talk to a HUD counselor, lender, or CPA.
- Do not ask for or rely on sensitive identifiers (SSN, full address, account numbers). If the user shares them, refuse to store or repeat them and steer back to general education.
- National benchmark rates are provided in context or via get_benchmark_rates; actual offers vary by lender, credit, and property.
- When discussing payments, clarify P&I vs PITI (taxes/insurance). Use estimate_monthly_pi for principal+interest math when numbers are given as ranges or examples.
- Encourage comparing Loan Estimates and understanding APR vs note rate.

Tone: calm, neutral, educational."""

TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_benchmark_rates",
            "description": "Current national benchmark 30-year and 15-year fixed mortgage rates (FRED/Freddie Mac weekly survey) from this app.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_monthly_pi",
            "description": "Compute fixed-rate monthly principal and interest (excludes taxes, insurance, HOA).",
            "parameters": {
                "type": "object",
                "properties": {
                    "loan_amount": {
                        "type": "number",
                        "description": "Loan amount in dollars (example or rounded range is fine)",
                    },
                    "annual_rate_percent": {
                        "type": "number",
                        "description": "Annual interest rate in percent, e.g. 6.37",
                    },
                    "years": {
                        "type": "integer",
                        "description": "Loan term in years",
                        "enum": [15, 20, 30],
                    },
                },
                "required": ["loan_amount", "annual_rate_percent", "years"],
            },
        },
    },
]


def _execute_tool(name: str, arguments: Dict[str, Any], store: RateStore) -> str:
    if name == "get_benchmark_rates":
        snap = store.latest_snapshot()
        if not snap:
            return json.dumps({"ok": False, "error": "Benchmark rates unavailable. Try again later."})
        return json.dumps(
            {
                "ok": True,
                "rate_30y_percent": snap.rate_30y,
                "rate_15y_percent": snap.rate_15y,
                "fred_observation_date_30y": snap.source_obs_date_30.isoformat(),
                "fred_observation_date_15y": snap.source_obs_date_15.isoformat(),
                "note": "Weekly Freddie Mac PMMS averages via FRED; not a lender quote.",
            }
        )
    if name == "estimate_monthly_pi":
        try:
            amt = float(arguments["loan_amount"])
            rate = float(arguments["annual_rate_percent"])
            years = int(arguments["years"])
            if years not in (15, 20, 30):
                years = 30
            pi = monthly_principal_interest(amt, rate, years)
            return json.dumps(
                {
                    "ok": True,
                    "monthly_principal_interest_usd": pi,
                    "loan_amount_usd": amt,
                    "annual_rate_percent": rate,
                    "years": years,
                    "disclaimer": "Principal and interest only; add taxes, insurance, PMI if applicable.",
                }
            )
        except (KeyError, TypeError, ValueError) as e:
            return json.dumps({"ok": False, "error": str(e)})
    return json.dumps({"ok": False, "error": "unknown_tool"})


def _rate_context_block(store: RateStore) -> str:
    snap = store.latest_snapshot()
    if not snap:
        return "Benchmark rates: not loaded yet (FRED unavailable)."
    return (
        f"Benchmark rates (national, weekly Freddie Mac via FRED): "
        f"30-year fixed ≈ {snap.rate_30y}%, 15-year fixed ≈ {snap.rate_15y}%. "
        f"FRED observation dates: 30y {snap.source_obs_date_30}, 15y {snap.source_obs_date_15}."
    )


async def run_chat(
    settings: Settings,
    store: RateStore,
    user_turns: List[Dict[str, str]],
) -> str:
    if not settings.openai_api_key:
        raise RuntimeError("LLM API key not configured (set OPENAI_API_KEY in .env)")

    system_content = SYSTEM_PROMPT + "\n\n" + _rate_context_block(store)
    api_messages: List[Dict[str, Any]] = [{"role": "system", "content": system_content}]
    for m in user_turns:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if role not in ("user", "assistant") or not content:
            continue
        if len(content) > 12000:
            content = content[:12000] + "…"
        api_messages.append({"role": role, "content": content})

    if len(api_messages) < 2:
        raise ValueError("Send at least one user message.")

    model = settings.openai_model
    url = settings.openai_base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }

    max_loops = 6
    for _ in range(max_loops):
        payload = {
            "model": model,
            "messages": api_messages,
            "tools": TOOLS,
            "tool_choice": "auto",
            "temperature": 0.6,
            "max_tokens": 2000,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(url, headers=headers, json=payload)
            if r.status_code >= 400:
                logger.warning("LLM API error %s: %s", r.status_code, r.text[:500])
                r.raise_for_status()
            data = r.json()

        choice = data["choices"][0]["message"]
        tool_calls = choice.get("tool_calls")

        if tool_calls:
            api_messages.append(choice)
            for tc in tool_calls:
                fn = tc.get("function") or {}
                name = fn.get("name", "")
                raw_args = fn.get("arguments") or "{}"
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except json.JSONDecodeError:
                    args = {}
                if not isinstance(args, dict):
                    args = {}
                out = _execute_tool(name, args, store)
                api_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.get("id", ""),
                        "content": out,
                    }
                )
            continue

        content = choice.get("content") or ""
        if isinstance(content, str) and content.strip():
            return content.strip()
        return "I did not get a usable reply. Please try again with a shorter question."

    return "Stopped after too many tool steps. Please simplify your question."
