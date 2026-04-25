import pytest
from textual.app import App, ComposeResult
from tapu.widgets.match_card import MatchCard


class _TestApp(App):
    def __init__(self, event: dict) -> None:
        super().__init__()
        self._event = event

    def compose(self) -> ComposeResult:
        yield MatchCard(self._event)


@pytest.mark.asyncio
async def test_match_card_renders_team_names(sample_scoreboard):
    event = sample_scoreboard["events"][0]
    async with _TestApp(event).run_test() as pilot:
        widget = pilot.app.query_one(MatchCard)
        assert widget is not None


@pytest.mark.asyncio
async def test_match_card_live_status(sample_scoreboard):
    event = sample_scoreboard["events"][0]
    async with _TestApp(event).run_test() as pilot:
        card = pilot.app.query_one(MatchCard)
        assert card.is_live is True


@pytest.mark.asyncio
async def test_match_card_not_live_for_final():
    event = {
        "id": "999",
        "name": "A vs B",
        "shortName": "A vs B",
        "status": {"type": {"name": "STATUS_FINAL"}, "displayClock": "90:00"},
        "competitions": [{"competitors": [
            {"homeAway": "home", "score": "1",
             "team": {"displayName": "Team A", "abbreviation": "AAA", "color": "FF0000",
                      "logos": [{"href": "https://example.com/a.png"}]}},
            {"homeAway": "away", "score": "0",
             "team": {"displayName": "Team B", "abbreviation": "BBB", "color": "0000FF",
                      "logos": [{"href": "https://example.com/b.png"}]}},
        ]}],
    }
    async with _TestApp(event).run_test() as pilot:
        card = pilot.app.query_one(MatchCard)
        assert card.is_live is False
