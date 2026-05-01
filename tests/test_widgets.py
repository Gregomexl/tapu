import pytest
from textual.app import App, ComposeResult

from tapu.config import League
from tapu.widgets.bracket import BracketWidget
from tapu.widgets.league_card import LeagueCard
from tapu.widgets.match_card import MatchCard, _period_label, _status_label, format_live_status
from tapu.widgets.match_detail import _extract_meta
from tapu.widgets.standings import StandingsTable


def test_status_label_live():
    event = {
        "status": {
            "type": {"name": "STATUS_SECOND_HALF", "state": "in"},
            "displayClock": "67:00",
            "period": 2,
        }
    }
    label = _status_label(event)
    assert "LIVE" in label
    assert "2nd" in label
    assert "green" in label
    assert "red" not in label


def test_status_label_ht():
    event = {
        "status": {
            "type": {"name": "STATUS_HALFTIME", "state": "in"},
            "displayClock": "45:00",
            "period": 1,
        }
    }
    label = _status_label(event)
    assert "HT" in label
    assert "yellow" in label


def test_status_label_ft():
    event = {
        "status": {
            "type": {"name": "STATUS_FINAL", "state": "post", "detail": "FT"},
            "displayClock": "90:00",
        },
        "date": "",
    }
    label = _status_label(event)
    assert "FT" in label
    assert "dim" in label


def test_period_label_first_half_from_period():
    assert _period_label({"status": {"type": {"name": ""}, "period": 1}}) == "1st"


def test_period_label_second_half_from_name():
    assert _period_label({"status": {"type": {"name": "STATUS_SECOND_HALF"}, "period": 0}}) == "2nd"


def test_period_label_extra_time():
    assert _period_label({"status": {"type": {"name": ""}, "period": 3}}) == "ET"
    assert _period_label({"status": {"type": {"name": "STATUS_OVERTIME"}, "period": 0}}) == "ET"


def test_format_live_status_shows_half_label():
    event = {
        "status": {
            "type": {"name": "STATUS_FIRST_HALF", "state": "in"},
            "period": 1,
        }
    }
    label = format_live_status(event)
    assert "LIVE" in label
    assert "1st" in label
    # No minute granularity — half-only display by design.
    assert "'" not in label


def test_format_live_status_shows_clock_when_requested():
    # Match panel passes show_clock=True to surface the API minute instead of the period.
    event = {
        "status": {
            "type": {"name": "STATUS_SECOND_HALF", "state": "in"},
            "displayClock": "67:23",
            "period": 2,
        }
    }
    label = format_live_status(event, show_clock=True)
    assert "LIVE" in label
    assert "67:23" in label
    assert "1st" not in label and "2nd" not in label


def test_extract_meta_weather_with_temperature():
    summary = {"gameInfo": {"weather": {"displayValue": "Cloudy", "temperature": 12}}}
    parts = _extract_meta({"competitions": [{}]}, summary)
    assert any("Cloudy" in p and "12" in p for p in parts)


def test_extract_meta_referee_prefers_head_official():
    summary = {
        "header": {"competitions": [{"officials": [
            {"displayName": "Asst One", "position": {"displayName": "Assistant Referee"}},
            {"displayName": "Real Ref", "position": {"displayName": "Head Referee"}},
        ]}]}
    }
    parts = _extract_meta({"competitions": [{}]}, summary)
    assert any("Real Ref" in p for p in parts)
    assert not any("Asst One" in p for p in parts)


def test_extract_meta_attendance_formatted():
    event = {"competitions": [{"attendance": 38420}]}
    parts = _extract_meta(event, {})
    assert "38,420" in parts


def test_extract_meta_empty_when_no_data():
    assert _extract_meta({"competitions": [{}]}, {}) == []


def test_format_live_status_ht_overrides_clock_mode():
    # HT trumps show_clock: during the halftime break the panel renders 'HT', not '45:00'.
    event = {
        "status": {
            "type": {"name": "STATUS_HALFTIME", "state": "in"},
            "displayClock": "45:00",
            "period": 1,
        }
    }
    label = format_live_status(event, show_clock=True)
    assert "HT" in label
    assert "45:00" not in label


def test_status_label_upcoming():
    event = {
        "status": {
            "type": {"name": "STATUS_SCHEDULED", "state": "pre", "detail": ""},
        },
        "date": "2026-05-01T19:00:00Z",
    }
    label = _status_label(event)
    assert "cyan" in label
    assert len(label) > 10  # has actual time content


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
