"""Refresh daily benchmark snapshots and build chart series from FRED."""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, Optional

from app.config import Settings
from app.fred_client import FredClient, SERIES_15Y, SERIES_30Y
from app.store import DailySnapshot, RateStore

logger = logging.getLogger(__name__)


async def refresh_today_snapshot(settings: Settings, store: RateStore) -> Optional[DailySnapshot]:
    try:
        client = FredClient(settings.fred_api_key)
        r30 = await client.latest_rate(SERIES_30Y)
        r15 = await client.latest_rate(SERIES_15Y)
    except Exception as exc:
        logger.warning("FRED fetch failed: %s", exc)
        return None
    if not r30 or not r15:
        return None
    now = datetime.now()
    row = DailySnapshot(
        snapshot_date=now.date(),
        rate_30y=r30[1],
        rate_15y=r15[1],
        source_obs_date_30=r30[0],
        source_obs_date_15=r15[0],
        fetched_at=now,
    )
    store.upsert_snapshot(row)
    return row


def parse_range_days(range_key: str) -> int:
    mapping = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
    if range_key not in mapping:
        raise ValueError("invalid range")
    return mapping[range_key]


async def series_for_chart(settings: Settings, range_key: str) -> Dict:
    days = parse_range_days(range_key)
    end = date.today()
    start = end - timedelta(days=days)
    client = FredClient(settings.fred_api_key)
    o30 = await client.fetch_observations(SERIES_30Y, observation_start=start, observation_end=end)
    o15 = await client.fetch_observations(SERIES_15Y, observation_start=start, observation_end=end)
    return {
        "range": range_key,
        "series_30y": [{"date": x["date"], "value": float(x["value"])} for x in o30],
        "series_15y": [{"date": x["date"], "value": float(x["value"])} for x in o15],
    }
