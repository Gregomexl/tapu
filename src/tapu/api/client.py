from datetime import datetime
from typing import Any

import httpx

BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer"
STANDINGS_URL = "https://site.web.api.espn.com/apis/v2/sports/soccer"


class ESPNClient:
    def __init__(self, cache_ttl: float = 30.0) -> None:
        self._http = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "Tapu/0.1"},
            follow_redirects=True,
        )
        self._cache: dict[str, tuple[float, Any]] = {}
        self._cache_ttl = cache_ttl

    async def _get(self, url: str, cache_ttl: float | None = None) -> Any:
        ttl = cache_ttl if cache_ttl is not None else self._cache_ttl
        if url in self._cache:
            cached_time, cached_data = self._cache[url]
            if datetime.now().timestamp() - cached_time < ttl:
                return cached_data
        response = await self._http.get(url)
        response.raise_for_status()
        data = response.json()
        self._cache[url] = (datetime.now().timestamp(), data)
        return data

    async def get_scoreboard(self, slug: str) -> dict[str, Any]:
        return await self._get(f"{BASE_URL}/{slug}/scoreboard", cache_ttl=10.0)

    async def get_standings(self, slug: str) -> dict[str, Any]:
        return await self._get(f"{STANDINGS_URL}/{slug}/standings")

    async def get_match_summary(self, slug: str, event_id: str) -> dict[str, Any]:
        return await self._get(
            f"{BASE_URL}/{slug}/summary?event={event_id}", cache_ttl=10.0
        )

    async def get_logo_bytes(self, url: str) -> bytes:
        response = await self._http.get(url)
        response.raise_for_status()
        return response.content

    def clear_cache(self) -> None:
        self._cache.clear()

    async def aclose(self) -> None:
        await self._http.aclose()
