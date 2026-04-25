import pytest
from pathlib import Path
from tapu.config import League, load_leagues


def test_league_dataclass():
    league = League(slug="eng.1", name="EPL", full_name="English Premier League")
    assert league.slug == "eng.1"
    assert league.name == "EPL"
    assert league.full_name == "English Premier League"


def test_load_leagues_returns_list(tmp_path):
    toml = tmp_path / "leagues.toml"
    toml.write_text(
        '[[leagues]]\nslug = "eng.1"\nname = "EPL"\nfull_name = "English Premier League"\n'
    )
    leagues = load_leagues(toml)
    assert len(leagues) == 1
    assert leagues[0].slug == "eng.1"
    assert leagues[0].name == "EPL"


def test_load_leagues_multiple(tmp_path):
    toml = tmp_path / "leagues.toml"
    toml.write_text(
        '[[leagues]]\nslug = "eng.1"\nname = "EPL"\nfull_name = "Premier League"\n\n'
        '[[leagues]]\nslug = "esp.1"\nname = "La Liga"\nfull_name = "La Liga"\n'
    )
    leagues = load_leagues(toml)
    assert len(leagues) == 2
    assert leagues[1].slug == "esp.1"
