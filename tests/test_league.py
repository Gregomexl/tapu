from tapu.screens.league import LeagueScreen, _get_event_scores


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
