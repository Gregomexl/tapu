from tapu.screens.league import LeagueScreen, _apply_filters, _get_event_scores


def _make_screen():
    """Instantiate without calling __init__ — we only need instance methods."""
    return LeagueScreen.__new__(LeagueScreen)


def test_parse_positions_children():
    standings = {
        "children": [{
            "standings": {
                "entries": [
                    {"team": {"id": "86"}},
                    {"team": {"id": "83"}},
                ]
            }
        }]
    }
    screen = _make_screen()
    assert screen._parse_positions(standings) == {"86": 1, "83": 2}


def test_parse_positions_flat():
    standings = {
        "standings": {
            "entries": [
                {"team": {"id": "10"}},
                {"team": {"id": "20"}},
                {"team": {"id": "30"}},
            ]
        }
    }
    screen = _make_screen()
    assert screen._parse_positions(standings) == {"10": 1, "20": 2, "30": 3}


def test_parse_positions_empty():
    screen = _make_screen()
    assert screen._parse_positions({}) == {}


def test_parse_positions_skips_entries_without_team_id():
    # Some standings payloads (older endpoints, certain leagues) come back without team.id.
    # Don't blow up — just skip those rows and return whatever we could parse.
    standings = {
        "standings": {
            "entries": [
                {"team": {"displayName": "Real Madrid", "abbreviation": "RMA"}},
                {"team": {"id": "20", "displayName": "Barça", "abbreviation": "BAR"}},
                {"team": {"abbreviation": "ATM"}},
            ]
        }
    }
    screen = _make_screen()
    assert screen._parse_positions(standings) == {"20": 2}


def test_get_event_scores_returns_home_away():
    event = {
        "id": "123",
        "competitions": [{
            "competitors": [
                {"homeAway": "home", "score": "2"},
                {"homeAway": "away", "score": "1"},
            ]
        }]
    }
    assert _get_event_scores(event) == ("2", "1")


def test_tab_cycling_arithmetic():
    ids = ["tab-main", "tab-bracket", "tab-copa"]
    assert ids[(ids.index("tab-main") + 1) % len(ids)] == "tab-bracket"
    assert ids[(ids.index("tab-copa") + 1) % len(ids)] == "tab-main"
    assert ids[(ids.index("tab-main") - 1) % len(ids)] == "tab-copa"


def test_get_event_scores_missing_score():
    event = {
        "id": "456",
        "competitions": [{
            "competitors": [
                {"homeAway": "home"},
                {"homeAway": "away"},
            ]
        }]
    }
    assert _get_event_scores(event) == ("", "")


def _make_event(state: str, home: str, away: str) -> dict:
    return {
        "id": f"{home}-{away}",
        "status": {"type": {"state": state}},
        "competitions": [{
            "competitors": [
                {"team": {"displayName": home, "shortDisplayName": home[:3]}},
                {"team": {"displayName": away, "shortDisplayName": away[:3]}},
            ]
        }]
    }


def test_apply_filters_all_status_returns_all():
    events = [
        _make_event("in", "Real Madrid", "Barcelona"),
        _make_event("post", "Atletico", "Sevilla"),
        _make_event("pre", "Villarreal", "Betis"),
    ]
    assert len(_apply_filters(events, "all", "")) == 3


def test_apply_filters_live_only():
    events = [
        _make_event("in", "Real Madrid", "Barcelona"),
        _make_event("post", "Atletico", "Sevilla"),
    ]
    result = _apply_filters(events, "live", "")
    assert len(result) == 1
    assert result[0]["id"] == "Real Madrid-Barcelona"


def test_apply_filters_done_only():
    events = [
        _make_event("in", "Real Madrid", "Barcelona"),
        _make_event("post", "Atletico", "Sevilla"),
    ]
    result = _apply_filters(events, "done", "")
    assert len(result) == 1
    assert result[0]["id"] == "Atletico-Sevilla"


def test_apply_filters_upcoming_only():
    events = [
        _make_event("post", "Atletico", "Sevilla"),
        _make_event("pre", "Villarreal", "Betis"),
    ]
    result = _apply_filters(events, "upcoming", "")
    assert len(result) == 1
    assert result[0]["id"] == "Villarreal-Betis"


def test_apply_filters_team_query_case_insensitive():
    events = [
        _make_event("post", "Real Madrid", "Barcelona"),
        _make_event("post", "Atletico", "Sevilla"),
    ]
    result = _apply_filters(events, "all", "madrid")
    assert len(result) == 1
    assert result[0]["id"] == "Real Madrid-Barcelona"


def test_apply_filters_combined_status_and_query():
    events = [
        _make_event("in", "Real Madrid", "Barcelona"),
        _make_event("post", "Real Madrid", "Atletico"),
    ]
    result = _apply_filters(events, "live", "madrid")
    assert len(result) == 1
    assert result[0]["status"]["type"]["state"] == "in"


def test_apply_filters_no_results():
    events = [_make_event("post", "Atletico", "Sevilla")]
    assert _apply_filters(events, "live", "") == []


def test_apply_filters_empty_events():
    assert _apply_filters([], "all", "madrid") == []
