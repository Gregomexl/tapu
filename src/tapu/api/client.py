import json
from datetime import datetime
from json import JSONDecodeError
from pathlib import Path
from typing import Any

import httpx

BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer"
STANDINGS_URL = "https://site.web.api.espn.com/apis/v2/sports/soccer"

DISK_CACHE_DIR = Path.home() / ".cache" / "tapu"


def _cache_key(url: str) -> str:
    return url.replace("://", "_").replace("/", "_").replace("?", "_").replace("&", "_").replace("=", "_").replace("-", "_")


def _has_team_ids(data: Any) -> bool:
    """Real ESPN standings always include team.id on every entry. If we get a payload
    with entries but no team.ids, treat it as poisoned (fixture/test data) and force
    a refetch — otherwise it would sit in the disk cache for an hour misleading the UI.
    """
    if not isinstance(data, dict):
        return True
    entries: list = []
    for child in data.get("children", []):
        entries.extend(child.get("standings", {}).get("entries", []))
    entries.extend(data.get("standings", {}).get("entries", []))
    if not entries:
        return True  # not a standings-shaped payload — let the caller decide
    return any(e.get("team", {}).get("id") for e in entries)


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
        try:
            data = response.json()
        except JSONDecodeError:
            # ESPN occasionally returns a schema template instead of data — retry once
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
        )

    async def get_standings(self, slug: str) -> dict[str, Any]:
        url = f"{STANDINGS_URL}/{slug}/standings"
        data = await self._get(url, disk_ttl=3600.0)  # 1 hour — standings rarely change mid-day
        if not _has_team_ids(data):
            # Cache holds bad data (e.g. fixture leak). Evict in-memory + disk and refetch once.
            self._cache.pop(url, None)
            try:
                self._disk_path(url).unlink(missing_ok=True)
            except Exception:
                pass
            data = await self._get(url, disk_ttl=3600.0)
        return data

    async def get_scoreboard_daterange(self, slug: str, start: str, end: str) -> dict[str, Any]:
        # Ranges that include today/future hold volatile data — a long disk cache would
        # leave finished matches stuck on "LIVE" for up to an hour. Short-circuit caching
        # in that case; purely-past ranges keep the long cache since past matches don't change.
        today = datetime.now().strftime("%Y%m%d")
        if end >= today:
            cache_ttl, disk_ttl = 3.0, None
        else:
            cache_ttl, disk_ttl = 300.0, 3600.0
        return await self._get(
            f"{BASE_URL}/{slug}/scoreboard?dates={start}-{end}",
            cache_ttl=cache_ttl,
            disk_ttl=disk_ttl,
        )

    async def get_knockout_events(self, slug: str) -> dict[str, Any]:
        """Fetch current calendar year — captures knockout rounds without being swamped by league/group phase."""
        today = datetime.now()
        start = today.replace(month=1, day=1).strftime("%Y%m%d")
        end = today.replace(month=12, day=31).strftime("%Y%m%d")
        return await self.get_scoreboard_daterange(slug, start, end)

    async def get_tournament_events(self, slug: str) -> dict[str, Any]:
        today = datetime.now()
        if today.month >= 8:
            season_start = today.replace(month=8, day=1).strftime("%Y%m%d")
            season_end = today.replace(year=today.year + 1, month=7, day=31).strftime("%Y%m%d")
        else:
            season_start = today.replace(year=today.year - 1, month=8, day=1).strftime("%Y%m%d")
            season_end = today.replace(month=7, day=31).strftime("%Y%m%d")
        return await self.get_scoreboard_daterange(slug, season_start, season_end)

    async def get_match_summary(self, slug: str, event_id: str) -> dict[str, Any]:
        return await self._get(
            f"{BASE_URL}/{slug}/summary?event={event_id}",
            cache_ttl=3.0,
        )

    def clear_cache(self, disk: bool = False) -> None:
        """Clear the in-memory cache. Pass `disk=True` to also wipe ~/.cache/tapu —
        the in-app escape hatch when stale data has somehow ended up on disk.
        """
        self._cache.clear()
        if disk:
            try:
                for path in DISK_CACHE_DIR.glob("*.json"):
                    path.unlink(missing_ok=True)
            except Exception:
                pass

    async def aclose(self) -> None:
        await self._http.aclose()
