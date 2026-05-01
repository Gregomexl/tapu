import pytest
from tapu.screens.league_palette import _filter_leagues
from tapu.config import League


def _league(name: str, slug: str = "x.1") -> League:
    return League(slug=slug, name=name, full_name=name)


def test_filter_empty_query_returns_all():
    leagues = [_league("Premier League"), _league("La Liga"), _league("Bundesliga")]
    assert _filter_leagues(leagues, "") == leagues


def test_filter_case_insensitive():
    leagues = [_league("Premier League"), _league("La Liga")]
    assert _filter_leagues(leagues, "liga") == [_league("La Liga")]


def test_filter_no_match_returns_empty():
    leagues = [_league("Premier League"), _league("La Liga")]
    assert _filter_leagues(leagues, "zzz") == []


def test_filter_partial_match():
    leagues = [_league("Premier League"), _league("Bundesliga"), _league("La Liga")]
    result = _filter_leagues(leagues, "liga")
    assert len(result) == 2
    assert all("liga" in l.full_name.lower() for l in result)
