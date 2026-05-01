from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tapu.api.client import ESPNClient


@pytest.fixture
def client():
    return ESPNClient()


def _mock_response(data):
    resp = MagicMock()
    resp.json.return_value = data
    resp.raise_for_status.return_value = None
    return resp


@pytest.mark.asyncio
async def test_get_scoreboard_calls_correct_url(client, sample_scoreboard):
    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get, \
         patch.object(client, "_read_disk", return_value=None):
        mock_get.return_value = _mock_response(sample_scoreboard)

        result = await client.get_scoreboard("eng.1")

        mock_get.assert_called_once()
        url = mock_get.call_args[0][0]
        assert "eng.1" in url
        assert "scoreboard" in url
        assert result == sample_scoreboard


@pytest.mark.asyncio
async def test_get_scoreboard_uses_cache(client, sample_scoreboard):
    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get, \
         patch.object(client, "_read_disk", return_value=None):
        mock_get.return_value = _mock_response(sample_scoreboard)

        await client.get_scoreboard("eng.1")
        await client.get_scoreboard("eng.1")

        assert mock_get.call_count == 1  # second call served from in-memory cache


@pytest.mark.asyncio
async def test_get_standings_calls_correct_url(client, sample_standings):
    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get, \
         patch.object(client, "_read_disk", return_value=None):
        mock_get.return_value = _mock_response(sample_standings)

        result = await client.get_standings("esp.1")

        url = mock_get.call_args[0][0]
        assert "esp.1" in url
        assert "standings" in url
        assert result == sample_standings


@pytest.mark.asyncio
async def test_get_match_summary_calls_correct_url(client):
    summary = {"header": {"id": "456"}}
    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(summary)

        result = await client.get_match_summary("eng.1", "456")

        url = mock_get.call_args[0][0]
        assert "eng.1" in url
        assert "456" in url
        assert result == summary


@pytest.mark.asyncio
async def test_clear_cache(client, sample_scoreboard):
    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get, \
         patch.object(client, "_read_disk", return_value=None):
        mock_get.return_value = _mock_response(sample_scoreboard)

        await client.get_scoreboard("eng.1")
        client.clear_cache()
        await client.get_scoreboard("eng.1")

        assert mock_get.call_count == 2  # cache cleared, re-fetched


@pytest.mark.asyncio
async def test_clear_cache_preserves_disk_files(tmp_path, monkeypatch):
    import json
    import time

    from tapu.api import client as client_module
    monkeypatch.setattr(client_module, "DISK_CACHE_DIR", tmp_path)

    c = ESPNClient()
    cache_file = tmp_path / "some_cached_endpoint.json"
    cache_file.write_text(json.dumps({"ts": time.time(), "data": {"events": []}}))

    c.clear_cache()

    assert cache_file.exists()
    await c.aclose()


@pytest.mark.asyncio
async def test_clear_cache_disk_true_wipes_disk(tmp_path, monkeypatch):
    import json
    import time

    from tapu.api import client as client_module
    monkeypatch.setattr(client_module, "DISK_CACHE_DIR", tmp_path)

    c = ESPNClient()
    cache_file = tmp_path / "some_cached_endpoint.json"
    cache_file.write_text(json.dumps({"ts": time.time(), "data": {"events": []}}))

    c.clear_cache(disk=True)

    assert not cache_file.exists()
    await c.aclose()


@pytest.mark.asyncio
async def test_get_standings_evicts_payload_without_team_ids(tmp_path, monkeypatch):
    """If the cache has fixture-shaped data (entries with no team.id), get_standings
    must drop it and refetch — otherwise the UI sees a 2-team La Liga for an hour."""
    import json
    import time as time_mod

    from tapu.api import client as client_module
    monkeypatch.setattr(client_module, "DISK_CACHE_DIR", tmp_path)

    c = ESPNClient()
    poisoned = {"standings": {"entries": [{"team": {"displayName": "Real Madrid"}}]}}
    real = {"standings": {"entries": [{"team": {"id": "86", "displayName": "Real Madrid"}}]}}

    url = f"{client_module.STANDINGS_URL}/esp.1/standings"
    cache_file = tmp_path / f"{client_module._cache_key(url)}.json"
    cache_file.write_text(json.dumps({"ts": time_mod.time(), "data": poisoned}))

    with patch.object(c._http, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(real)
        result = await c.get_standings("esp.1")

    assert result == real
    assert mock_get.called  # poisoned cache was bypassed and a real fetch happened
    await c.aclose()


@pytest.mark.asyncio
async def test_aclose(client):
    with patch.object(client._http, "aclose", new_callable=AsyncMock) as mock_close:
        await client.aclose()
        mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_daterange_skips_disk_cache_when_range_includes_today(client, sample_scoreboard):
    from datetime import datetime
    today = datetime.now().strftime("%Y%m%d")
    start = (datetime.now().replace(day=1)).strftime("%Y%m%d")
    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get, \
         patch.object(client, "_read_disk", return_value=None) as mock_read, \
         patch.object(client, "_write_disk") as mock_write:
        mock_get.return_value = _mock_response(sample_scoreboard)

        await client.get_scoreboard_daterange("eng.1", start, today)

        # When today is in the range, disk cache is bypassed entirely so a finished
        # match isn't stuck on "LIVE" for up to an hour after the event ends.
        mock_read.assert_not_called()
        mock_write.assert_not_called()


@pytest.mark.asyncio
async def test_daterange_uses_disk_cache_for_past_only_ranges(client, sample_scoreboard):
    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get, \
         patch.object(client, "_read_disk", return_value=None) as mock_read, \
         patch.object(client, "_write_disk") as mock_write:
        mock_get.return_value = _mock_response(sample_scoreboard)

        await client.get_scoreboard_daterange("eng.1", "20200101", "20200131")

        mock_read.assert_called_once()
        mock_write.assert_called_once()


@pytest.mark.asyncio
async def test_get_tournament_events_builds_season_date_range(client, sample_scoreboard):
    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get, \
         patch.object(client, "_read_disk", return_value=None):
        mock_get.return_value = _mock_response(sample_scoreboard)

        result = await client.get_tournament_events("esp.copa_del_rey")

        url = mock_get.call_args[0][0]
        assert "esp.copa_del_rey" in url
        assert "scoreboard" in url
        assert "dates=" in url
        import re
        assert re.search(r"dates=\d{8}-\d{8}", url)
        assert result == sample_scoreboard
