import pytest
from textual.app import App, ComposeResult
from tapu.config import League
from tapu.widgets.bracket import BracketWidget
from tapu.widgets.league_card import LeagueCard
from tapu.widgets.match_card import MatchCard
from tapu.widgets.standings import StandingsTable


class _LeagueCardTestApp(App):
    def __init__(self, league: League, scoreboard: dict) -> None:
        super().__init__()
        self._league = league
        self._scoreboard = scoreboard

    def compose(self) -> ComposeResult:
        yield LeagueCard(self._league, self._scoreboard)


@pytest.mark.asyncio
async def test_league_card_renders(sample_scoreboard):
    league = League(slug="eng.1", name="EPL", full_name="English Premier League")
    async with _LeagueCardTestApp(league, sample_scoreboard).run_test() as pilot:
        card = pilot.app.query_one(LeagueCard)
        assert card is not None


@pytest.mark.asyncio
async def test_league_card_live_count(sample_scoreboard):
    league = League(slug="eng.1", name="EPL", full_name="English Premier League")
    async with _LeagueCardTestApp(league, sample_scoreboard).run_test() as pilot:
        card = pilot.app.query_one(LeagueCard)
        assert card.live_count == 1


class _StandingsTestApp(App):
    def __init__(self, data: dict) -> None:
        super().__init__()
        self._data = data

    def compose(self) -> ComposeResult:
        yield StandingsTable(self._data)


@pytest.mark.asyncio
async def test_standings_table_renders(sample_standings):
    async with _StandingsTestApp(sample_standings).run_test() as pilot:
        table = pilot.app.query_one(StandingsTable)
        assert table is not None


@pytest.mark.asyncio
async def test_standings_table_row_count(sample_standings):
    async with _StandingsTestApp(sample_standings).run_test() as pilot:
        table = pilot.app.query_one(StandingsTable)
        assert table.row_count == 2


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


def _bracket_events() -> list[dict]:
    def ev(round_name, h_id, a_id, h_score="-", a_score="-", state="pre"):
        return {
            "status": {"type": {"state": state}},
            "competitions": [{
                "notes": [{"headline": round_name}],
                "competitors": [
                    {"homeAway": "home", "score": h_score,
                     "team": {"id": h_id, "shortDisplayName": f"T{h_id}", "abbreviation": f"T{h_id}"}},
                    {"homeAway": "away", "score": a_score,
                     "team": {"id": a_id, "shortDisplayName": f"T{a_id}", "abbreviation": f"T{a_id}"}},
                ],
            }],
        }
    return [
        ev("Quarterfinal", "10", "11", "2", "1", "post"),
        ev("Quarterfinal", "12", "13", "0", "1", "post"),
        ev("Semifinal", "10", "13", "1", "0", "post"),
    ]


class _BracketTestApp(App):
    def __init__(self, events: list) -> None:
        super().__init__()
        self._events = events

    def compose(self) -> ComposeResult:
        yield BracketWidget(self._events)


@pytest.mark.asyncio
async def test_bracket_widget_renders():
    async with _BracketTestApp(_bracket_events()).run_test() as pilot:
        widget = pilot.app.query_one(BracketWidget)
        assert widget is not None


@pytest.mark.asyncio
async def test_bracket_widget_renders_empty():
    async with _BracketTestApp([]).run_test() as pilot:
        widget = pilot.app.query_one(BracketWidget)
        assert widget is not None


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
