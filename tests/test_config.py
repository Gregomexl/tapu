from tapu.config import League, RelatedTournament, load_leagues


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


def test_related_tournament_dataclass():
    rt = RelatedTournament(name="Copa del Rey", slug="esp.copa_del_rey")
    assert rt.name == "Copa del Rey"
    assert rt.slug == "esp.copa_del_rey"


def test_league_default_related_is_empty():
    league = League(slug="eng.1", name="EPL", full_name="English Premier League")
    assert league.related == ()


def test_load_leagues_with_related(tmp_path):
    toml = tmp_path / "leagues.toml"
    toml.write_text(
        '[[leagues]]\n'
        'slug = "esp.1"\n'
        'name = "La Liga"\n'
        'full_name = "La Liga"\n'
        'related = [{name = "Copa del Rey", slug = "esp.copa_del_rey"}]\n'
    )
    leagues = load_leagues(toml)
    assert len(leagues) == 1
    assert len(leagues[0].related) == 1
    assert leagues[0].related[0].name == "Copa del Rey"
    assert leagues[0].related[0].slug == "esp.copa_del_rey"


def test_load_leagues_without_related_defaults_to_empty(tmp_path):
    toml = tmp_path / "leagues.toml"
    toml.write_text(
        '[[leagues]]\nslug = "eng.1"\nname = "EPL"\nfull_name = "Premier League"\n'
    )
    leagues = load_leagues(toml)
    assert leagues[0].related == ()
