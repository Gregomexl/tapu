import pytest


@pytest.fixture
def sample_scoreboard():
    return {
        "leagues": [
            {
                "logos": [
                    {"href": "https://a.espncdn.com/i/leaguelogos/soccer/500/2.png"}
                ]
            }
        ],
        "events": [
            {
                "id": "123",
                "name": "Real Madrid vs Barcelona",
                "shortName": "RMA vs BAR",
                "status": {
                    "type": {"name": "STATUS_IN_PROGRESS"},
                    "displayClock": "67:00",
                },
                "competitions": [
                    {
                        "competitors": [
                            {
                                "homeAway": "home",
                                "score": "2",
                                "team": {
                                    "displayName": "Real Madrid",
                                    "abbreviation": "RMA",
                                    "color": "FEBE10",
                                    "logos": [{"href": "https://a.espncdn.com/i/teamlogos/soccer/500/86.png"}],
                                },
                            },
                            {
                                "homeAway": "away",
                                "score": "1",
                                "team": {
                                    "displayName": "Barcelona",
                                    "abbreviation": "BAR",
                                    "color": "A50044",
                                    "logos": [{"href": "https://a.espncdn.com/i/teamlogos/soccer/500/83.png"}],
                                },
                            },
                        ]
                    }
                ],
            }
        ],
    }


@pytest.fixture
def sample_standings():
    return {
        "standings": {
            "entries": [
                {
                    "team": {"displayName": "Real Madrid", "abbreviation": "RMA"},
                    "stats": [
                        {"name": "gamesPlayed", "value": 10},
                        {"name": "wins", "value": 8},
                        {"name": "ties", "value": 1},
                        {"name": "losses", "value": 1},
                        {"name": "pointDifferential", "value": 15},
                        {"name": "points", "value": 25},
                    ],
                },
                {
                    "team": {"displayName": "Barcelona", "abbreviation": "BAR"},
                    "stats": [
                        {"name": "gamesPlayed", "value": 10},
                        {"name": "wins", "value": 7},
                        {"name": "ties", "value": 2},
                        {"name": "losses", "value": 1},
                        {"name": "pointDifferential", "value": 12},
                        {"name": "points", "value": 23},
                    ],
                },
            ]
        }
    }
