import json
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer"
STANDINGS_URL = "https://site.web.api.espn.com/apis/v2/sports/soccer"

DISK_CACHE_DIR = Path.home() / ".cache" / "tapu"


def _cache_key(url: str) -> str:
    return url.replace("://", "_").replace("/", "_").replace("?", "_").replace("&", "_").replace("=", "_").replace("-", "_")


class ESPNClient:
    def __init__(self, cache_ttl: float = 30.0) -> None:
        self._http = httpx.AsyncClient(
            timeout=10.0,
            headers={"User-Agent": "Tapu/0.1"},
            follow_redirects=True,
        )
        self._cache: dict[str, tuple[float, Any]] = {}
        self._cache_ttl = cache_ttl
        DISK_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _disk_path(self, url: str) -> Path:
        return DISK_CACHE_DIR / f"{_cache_key(url)}.json"

    def _read_disk(self, url: str, max_age: float) -> Any | None:
        path = self._disk_path(url)
        try:
            if path.exists():
                payload = json.loads(path.read_text())
                if datetime.now().timestamp() - payload["ts"] < max_age:
                    return payload["data"]
        except Exception:
            pass
        return None

    def _write_disk(self, url: str, data: Any) -> None:
        try:
            self._disk_path(url).write_text(
                json.dumps({"ts": datetime.now().timestamp(), "data": data})
            )
        except Exception:
            pass

    async def _get(self, url: str, cache_ttl: float | None = None, disk_ttl: float | None = None) -> Any:
        ttl = cache_ttl if cache_ttl is not None else self._cache_ttl
        if url in self._cache:
            cached_time, cached_data = self._cache[url]
            if datetime.now().timestamp() - cached_time < ttl:
                return cached_data

        # Try disk cache for fast startup (longer TTL than in-memory)
        if disk_ttl is not None:
            cached = self._read_disk(url, disk_ttl)
            if cached is not None:
                self._cache[url] = (datetime.now().timestamp(), cached)
                return cached

        response = await self._http.get(url)
        response.raise_for_status()
        data = response.json()
        self._cache[url] = (datetime.now().timestamp(), data)
        if disk_ttl is not None:
            self._write_disk(url, data)
        return data

    async def get_scoreboard(self, slug: str) -> dict[str, Any]:
        return await self._get(
            f"{BASE_URL}/{slug}/scoreboard",
            cache_ttl=3.0,
            disk_ttl=300.0,  # 5 min disk cache for dashboard startup
        )

    async def get_standings(self, slug: str) -> dict[str, Any]:
        return await self._get(
            f"{STANDINGS_URL}/{slug}/standings",
            disk_ttl=3600.0,  # 1 hour — standings rarely change mid-day
        )

    async def get_scoreboard_daterange(self, slug: str, start: str, end: str) -> dict[str, Any]:
        return await self._get(
            f"{BASE_URL}/{slug}/scoreboard?dates={start}-{end}",
            cache_ttl=300.0,
            disk_ttl=3600.0,
        )

    async def get_match_summary(self, slug: str, event_id: str) -> dict[str, Any]:
        return await self._get(
            f"{BASE_URL}/{slug}/summary?event={event_id}",
            cache_ttl=3.0,
        )

    def clear_cache(self) -> None:
        self._cache.clear()
        try:
            for f in DISK_CACHE_DIR.glob("*.json"):
                f.unlink()
        except Exception:
            pass

    async def aclose(self) -> None:
        await self._http.aclose()
