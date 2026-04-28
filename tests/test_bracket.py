import pytest
from tapu.widgets.bracket import _round_key, _event_round, _winner_id, _bracket_lines


def _make_event(round_headline: str, home_id: str, away_id: str,
                home_score: str = "-", away_score: str = "-",
                state: str = "pre") -> dict:
    return {
        "status": {"type": {"state": state}},
        "competitions": [{
            "notes": [{"headline": round_headline}],
            "competitors": [
                {"homeAway": "home", "score": home_score,
                 "team": {"id": home_id, "shortDisplayName": f"T{home_id}", "abbreviation": f"T{home_id}"}},
                {"homeAway": "away", "score": away_score,
                 "team": {"id": away_id, "shortDisplayName": f"T{away_id}", "abbreviation": f"T{away_id}"}},
            ],
        }],
    }


def test_round_key_final_is_zero():
    assert _round_key("Final") == 0


def test_round_key_semifinal_is_one():
    assert _round_key("Semifinal") == 1
    assert _round_key("Semi-Final") == 1


def test_round_key_quarterfinal_is_two():
    assert _round_key("Quarterfinal") == 2
    assert _round_key("Quarter-Final") == 2


def test_round_key_round_of_16_is_three():
    assert _round_key("Round of 16") == 3


def test_round_key_unknown_is_99():
    assert _round_key("Group Stage") == 99


def test_event_round_extracts_headline():
    ev = _make_event("Semifinal", "1", "2")
    assert _event_round(ev) == "Semifinal"


def test_event_round_returns_empty_for_no_notes():
    ev = _make_event("", "1", "2")
    assert _event_round(ev) == ""


def test_winner_id_returns_none_for_pre_match():
    ev = _make_event("Final", "1", "2", state="pre")
    assert _winner_id(ev) is None


def test_winner_id_returns_none_for_in_progress():
    ev = _make_event("Final", "1", "2", home_score="1", away_score="0", state="in")
    assert _winner_id(ev) is None


def test_winner_id_returns_home_winner():
    ev = _make_event("Final", "1", "2", home_score="2", away_score="1", state="post")
    ev["competitions"][0]["competitors"][0]["winner"] = True
    ev["competitions"][0]["competitors"][1]["winner"] = False
    assert _winner_id(ev) == "1"


def test_winner_id_returns_away_winner():
    ev = _make_event("Final", "1", "2", home_score="0", away_score="1", state="post")
    ev["competitions"][0]["competitors"][0]["winner"] = False
    ev["competitions"][0]["competitors"][1]["winner"] = True
    assert _winner_id(ev) == "2"


def test_bracket_lines_empty_returns_placeholder():
    result = _bracket_lines([])
    assert result == ["[dim]Bracket not yet available[/dim]"]


def test_bracket_lines_no_round_data_returns_placeholder():
    ev = _make_event("", "1", "2")
    result = _bracket_lines([ev])
    assert result == ["[dim]Bracket not yet available[/dim]"]


def test_bracket_lines_only_group_stage_returns_placeholder():
    ev = _make_event("Group Stage", "1", "2")
    result = _bracket_lines([ev])
    assert result == ["[dim]Bracket not yet available[/dim]"]


def test_bracket_lines_sf_only_renders_teams():
    sf = _make_event("Semifinal", "1", "2", home_score="1", away_score="0", state="post")
    result = _bracket_lines([sf])
    combined = "\n".join(result)
    assert "T1" in combined
    assert "T2" in combined


def test_bracket_lines_qf_and_sf_renders_qf_connector():
    qf1 = _make_event("Quarterfinal", "10", "11", home_score="2", away_score="1", state="post")
    qf2 = _make_event("Quarterfinal", "12", "13", home_score="0", away_score="1", state="post")
    sf = _make_event("Semifinal", "10", "13", home_score="1", away_score="0", state="post")
    result = _bracket_lines([qf1, qf2, sf])
    combined = "\n".join(result)
    assert "├─" in combined
    assert "T10" in combined
    assert "T13" in combined


def test_bracket_lines_final_shown_at_bottom():
    sf1 = _make_event("Semifinal", "1", "2", home_score="1", away_score="0", state="post")
    sf2 = _make_event("Semifinal", "3", "4", home_score="2", away_score="1", state="post")
    final = _make_event("Final", "1", "3", home_score="1", away_score="0", state="post")
    result = _bracket_lines([sf1, sf2, final])
    combined = "\n".join(result)
    assert "FINAL" in combined
    assert "T1" in combined
    assert "T3" in combined
