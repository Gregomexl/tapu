import pytest
from textual.app import App, ComposeResult

from tapu.config import League
from tapu.widgets.bracket import BracketWidget
from tapu.widgets.league_card import LeagueCard
from tapu.widgets.match_card import MatchCard, _period_label, _status_label, format_live_status
from tapu.widgets.match_detail import build_lineups, build_substitutions, build_timeline
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





def _timeline_event_with_two_teams():
    return {
        "competitions": [{
            "competitors": [
                {"team": {"id": "1", "abbreviation": "RMA", "color": "FF0000"}, "homeAway": "home"},
                {"team": {"id": "2", "abbreviation": "BAR", "color": "0000FF"}, "homeAway": "away"},
            ]
        }]
    }


def test_build_timeline_orders_goals_and_cards_chronologically():
    # Substitutions are deliberately routed to build_substitutions, not the timeline.
    summary = {"keyEvents": [
        {"team": {"id": "1"}, "clock": {"value": 4500, "displayValue": "75"}, "scoringPlay": True, "shortText": "Pedri Goal", "type": {"type": "play"}},
        {"team": {"id": "2"}, "clock": {"value": 1800, "displayValue": "30"}, "type": {"type": "yellow-card"}, "participants": [{"athlete": {"displayName": "Vinícius"}}]},
        {"team": {"id": "1"}, "clock": {"value": 3840, "displayValue": "64"}, "type": {"type": "substitution"}, "participants": [{"athlete": {"displayName": "García"}}, {"athlete": {"displayName": "López"}}]},
    ]}
    lines = build_timeline(_timeline_event_with_two_teams(), summary)
    assert len(lines) == 2  # sub excluded
    assert "Vinícius" in lines[0] and "🟨" in lines[0]
    assert "Pedri" in lines[1] and "⚽" in lines[1]


def test_build_substitutions_only_returns_subs_in_order():
    summary = {"keyEvents": [
        {"team": {"id": "1"}, "clock": {"value": 4500, "displayValue": "75"}, "scoringPlay": True, "shortText": "Goal", "type": {"type": "play"}},
        {"team": {"id": "2"}, "clock": {"value": 4320, "displayValue": "72"}, "type": {"type": "substitution"}, "participants": [{"athlete": {"displayName": "Pedri"}}, {"athlete": {"displayName": "Gavi"}}]},
        {"team": {"id": "1"}, "clock": {"value": 3840, "displayValue": "64"}, "type": {"type": "substitution"}, "participants": [{"athlete": {"displayName": "García"}}, {"athlete": {"displayName": "López"}}]},
    ]}
    lines = build_substitutions(_timeline_event_with_two_teams(), summary)
    assert len(lines) == 2
    # Ordered by clock seconds: 64 then 72
    assert "García" in lines[0] and "RMA" in lines[0]
    assert "Pedri" in lines[1] and "BAR" in lines[1]
    # No emoji icon on rows — section header carries the label.
    assert "🔄" not in lines[0]


def test_build_substitutions_empty_when_none():
    summary = {"keyEvents": [
        {"team": {"id": "1"}, "clock": {"value": 100, "displayValue": "2"}, "type": {"type": "yellow-card"}, "participants": [{"athlete": {"displayName": "X"}}]},
    ]}
    assert build_substitutions(_timeline_event_with_two_teams(), summary) == []


def test_build_timeline_tags_each_row_with_team_abbr():
    summary = {"keyEvents": [
        {"team": {"id": "1"}, "clock": {"value": 600, "displayValue": "10"}, "scoringPlay": True, "shortText": "Goal", "type": {}},
        {"team": {"id": "2"}, "clock": {"value": 1200, "displayValue": "20"}, "scoringPlay": True, "shortText": "Goal", "type": {}},
    ]}
    lines = build_timeline(_timeline_event_with_two_teams(), summary)
    assert "RMA" in lines[0]
    assert "BAR" in lines[1]
    # No color blocks anymore — the abbreviation is the disambiguator.
    assert "#FF0000" not in lines[0]


def test_build_timeline_strips_stoppage_apostrophes_from_minute():
    summary = {"keyEvents": [
        {"team": {"id": "1"}, "clock": {"value": 5520, "displayValue": "90'+2'"}, "scoringPlay": True, "shortText": "Goal", "type": {}},
    ]}
    line = build_timeline(_timeline_event_with_two_teams(), summary)[0]
    # '90'+2'' would be a double-apostrophe disaster — must render as '90+2''.
    assert "90+2" in line
    assert "''" not in line


def test_build_timeline_drops_unknown_event_types():
    summary = {"keyEvents": [
        {"team": {"id": "1"}, "clock": {"value": 100, "displayValue": "2"}, "type": {"type": "corner-kick"}},
        {"team": {"id": "1"}, "clock": {"value": 200, "displayValue": "4"}, "type": {"type": "yellow-card"}, "participants": [{"athlete": {"displayName": "X"}}]},
    ]}
    lines = build_timeline(_timeline_event_with_two_teams(), summary)
    assert len(lines) == 1
    assert "🟨" in lines[0]


def test_build_timeline_empty_summary():
    assert build_timeline(_timeline_event_with_two_teams(), {}) == []
    assert build_timeline(_timeline_event_with_two_teams(), {"keyEvents": []}) == []


def _lineup_summary():
    def player(jersey, name, pos, starter):
        return {
            "athlete": {"jersey": jersey, "displayName": name},
            "position": {"abbreviation": pos},
            "starter": starter,
        }
    return {
        "rosters": [
            {
                "team": {"id": "1", "displayName": "Real Madrid"},
                "formation": "4-3-3",
                "roster": [
                    player("1", "Courtois", "GK", True),
                    player("2", "Carvajal", "RB", True),
                    player("4", "Alaba", "CB", True),
                    player("13", "Lunin", "GK", False),
                    player("18", "Vázquez", "RB", False),
                ],
            },
            {
                "team": {"id": "2", "displayName": "Barcelona"},
                "formation": {"name": "4-3-2-1"},  # dict variant
                "roster": [
                    player("1", "ter Stegen", "GK", True),
                ],
            },
        ]
    }


def test_build_lineups_orders_home_first():
    event = _timeline_event_with_two_teams()
    home_lines, away_lines = build_lineups(event, _lineup_summary())
    assert "Real Madrid" in home_lines[0]
    assert "Barcelona" in away_lines[0]


def test_build_lineups_renders_formation_in_header():
    event = _timeline_event_with_two_teams()
    home_lines, away_lines = build_lineups(event, _lineup_summary())
    assert "4-3-3" in home_lines[0]
    # Dict-form formation also normalized to '4-3-2-1'.
    assert "4-3-2-1" in away_lines[0]


def test_build_lineups_prepends_color_badge_to_team_header():
    event = _timeline_event_with_two_teams()
    summary = _lineup_summary()
    # _lineup_summary() doesn't carry team.color; inject one for this test.
    summary["rosters"][0]["team"]["color"] = "FFFFFF"
    summary["rosters"][1]["team"]["color"] = "A50044"
    home_lines, away_lines = build_lineups(event, summary)
    assert "#FFFFFF" in home_lines[0]
    assert "#A50044" in away_lines[0]


def test_build_lineups_separates_starters_from_bench():
    event = _timeline_event_with_two_teams()
    home_lines, _ = build_lineups(event, _lineup_summary())
    starter_rows = [line for line in home_lines if "Courtois" in line or "Carvajal" in line or "Alaba" in line]
    assert len(starter_rows) == 3
    bench_line = next(line for line in home_lines if "Bench" in line)
    assert "Lunin" in bench_line
    assert "Vázquez" in bench_line


def test_build_lineups_empty_when_no_rosters():
    assert build_lineups(_timeline_event_with_two_teams(), {}) == []
    assert build_lineups(_timeline_event_with_two_teams(), {"rosters": []}) == []


def test_build_lineups_extracts_jersey_from_entry_level():
    # ESPN sometimes puts jersey on the roster entry instead of inside athlete.
    summary = {"rosters": [
        {
            "team": {"id": "1", "displayName": "Real Madrid"},
            "formation": "4-3-3",
            "roster": [
                {"jersey": "9", "athlete": {"displayName": "Joselu"}, "position": {"abbreviation": "ST"}, "starter": True},
            ],
        },
        {
            "team": {"id": "2", "displayName": "Barcelona"},
            "formation": "4-3-3",
            "roster": [
                {"athlete": {"displayName": "Lewandowski", "uniformNumber": 9}, "position": {"abbreviation": "ST"}, "starter": True},
            ],
        },
    ]}
    home_lines, away_lines = build_lineups(_timeline_event_with_two_teams(), summary)
    starter_home = next(line for line in home_lines if "Joselu" in line)
    starter_away = next(line for line in away_lines if "Lewandowski" in line)
    # No '—' placeholder when the data is just on a different field.
    assert "—" not in starter_home
    assert "—" not in starter_away
    assert " 9" in starter_home  # entry-level jersey picked up
    assert " 9" in starter_away  # athlete.uniformNumber (integer) coerced to string


def test_format_live_status_normalizes_stoppage_clock():
    # ESPN returns "90'+5'" with embedded apostrophes — render it as "90+5'" not "90'+5''".
    event = {
        "status": {
            "type": {"name": "STATUS_SECOND_HALF", "state": "in"},
            "displayClock": "90'+5'",
            "period": 2,
        }
    }
    label = format_live_status(event, show_clock=True)
    assert "90+5'" in label
    assert "90'+5''" not in label


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
