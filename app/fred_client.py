from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

import httpx

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"
SERIES_30Y = "MORTGAGE30US"
SERIES_15Y = "MORTGAGE15US"


class FredClient:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def fetch_observations(
        self,
        series_id: str,
        observation_start: Optional[date] = None,
        observation_end: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        params = {
            "series_id": series_id,
            "api_key": self._api_key,
            "file_type": "json",
        }
        if observation_start is not None:
            params["observation_start"] = observation_start.isoformat()
        if observation_end is not None:
            params["observation_end"] = observation_end.isoformat()

        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(FRED_BASE, params=params)
            r.raise_for_status()
        data = r.json()
        obs = data.get("observations") or []
        return [o for o in obs if o.get("value") not in (".", None)]

    async def latest_rate(self, series_id: str) -> Optional[Tuple[date, float]]:
        end = date.today()
        start = end - timedelta(days=120)
        rows = await self.fetch_observations(series_id, observation_start=start, observation_end=end)
        if not rows:
            return None
        last = rows[-1]
        d = date.fromisoformat(last["date"])
        return d, float(last["value"])
