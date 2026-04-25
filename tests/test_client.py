import pytest
from unittest.mock import AsyncMock, MagicMock, patch
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
    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(sample_scoreboard)

        result = await client.get_scoreboard("eng.1")

        mock_get.assert_called_once()
        url = mock_get.call_args[0][0]
        assert "eng.1" in url
        assert "scoreboard" in url
        assert result == sample_scoreboard


@pytest.mark.asyncio
async def test_get_scoreboard_uses_cache(client, sample_scoreboard):
    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(sample_scoreboard)

        await client.get_scoreboard("eng.1")
        await client.get_scoreboard("eng.1")

        assert mock_get.call_count == 1  # second call served from cache


@pytest.mark.asyncio
async def test_get_standings_calls_correct_url(client, sample_standings):
    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get:
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
    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(sample_scoreboard)

        await client.get_scoreboard("eng.1")
        client.clear_cache()
        await client.get_scoreboard("eng.1")

        assert mock_get.call_count == 2  # cache cleared, re-fetched


@pytest.mark.asyncio
async def test_aclose(client):
    with patch.object(client._http, "aclose", new_callable=AsyncMock) as mock_close:
        await client.aclose()
        mock_close.assert_called_once()
