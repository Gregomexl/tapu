import pytest
from tapu.widgets.bracket import _round_key, _event_round, _winner_id, _bracket_lines


def _make_event(round_headline: str, home_id: str, away_id: str,
                home_score: str = "-", away_score: str = "-",
                state: str = "pre", winner_id: str | None = None) -> dict:
    comps = [
        {"homeAway": "home", "score": home_score,
         "team": {"id": home_id, "shortDisplayName": f"T{home_id}", "abbreviation": f"T{home_id}"},
         "winner": winner_id == home_id},
        {"homeAway": "away", "score": away_score,
         "team": {"id": away_id, "shortDisplayName": f"T{away_id}", "abbreviation": f"T{away_id}"},
         "winner": winner_id == away_id},
    ]
    return {
        "status": {"type": {"state": state}},
        "competitions": [{
            "notes": [{"headline": round_headline}] if round_headline else [],
            "competitors": comps,
        }],
    }


# ── _round_key ────────────────────────────────────────────────────────────────

def test_round_key_final_is_zero():
    assert _round_key("Final") == 0


def test_round_key_final_slug_is_zero():
    assert _round_key("final") == 0


def test_round_key_semifinal_is_one():
    assert _round_key("Semifinal") == 1
    assert _round_key("Semi-Final") == 1
    assert _round_key("semifinals") == 1


def test_round_key_quarterfinal_is_two():
    assert _round_key("Quarterfinal") == 2
    assert _round_key("Quarter-Final") == 2
    assert _round_key("quarterfinals") == 2


def test_round_key_round_of_16_is_three():
    assert _round_key("Round of 16") == 3
    assert _round_key("round-of-16") == 3


def test_round_key_round_of_32_is_four():
    assert _round_key("round-of-32") == 4


def test_round_key_numbered_rounds():
    assert _round_key("first-round") == 9
    assert _round_key("second-round") == 8
    assert _round_key("third-round") == 7
    assert _round_key("fourth-round") == 6
    assert _round_key("fifth-round") == 5


def test_round_key_unknown_is_99():
    assert _round_key("Group Stage") == 99


# ── _event_round ──────────────────────────────────────────────────────────────

def test_event_round_extracts_headline():
    ev = _make_event("Semifinal", "1", "2")
    assert _event_round(ev) == "Semifinal"


def test_event_round_falls_back_to_season_slug():
    ev = _make_event("", "1", "2")
    ev["season"] = {"slug": "final"}
    assert _event_round(ev) == "Final"


def test_event_round_returns_empty_for_no_notes_no_slug():
    ev = _make_event("", "1", "2")
    assert _event_round(ev) == ""


# ── _winner_id ────────────────────────────────────────────────────────────────

def test_winner_id_returns_none_for_pre_match():
    ev = _make_event("Final", "1", "2", state="pre")
    assert _winner_id(ev) is None


def test_winner_id_returns_none_for_in_progress():
    ev = _make_event("Final", "1", "2", home_score="1", away_score="0", state="in")
    assert _winner_id(ev) is None


def test_winner_id_returns_home_winner():
    ev = _make_event("Final", "1", "2", home_score="2", away_score="1", state="post", winner_id="1")
    assert _winner_id(ev) == "1"


def test_winner_id_returns_away_winner():
    ev = _make_event("Final", "1", "2", home_score="0", away_score="1", state="post", winner_id="2")
    assert _winner_id(ev) == "2"


# ── _bracket_lines ────────────────────────────────────────────────────────────

def test_bracket_lines_empty_returns_placeholder():
    assert _bracket_lines([]) == ["[dim]Bracket not yet available[/dim]"]


def test_bracket_lines_no_round_data_returns_placeholder():
    ev = _make_event("", "1", "2")
    assert _bracket_lines([ev]) == ["[dim]Bracket not yet available[/dim]"]


def test_bracket_lines_only_group_stage_returns_placeholder():
    ev = _make_event("Group Stage", "1", "2")
    assert _bracket_lines([ev]) == ["[dim]Bracket not yet available[/dim]"]


def test_bracket_lines_sf_only_renders_teams():
    sf = _make_event("Semifinal", "1", "2", home_score="1", away_score="0", state="post", winner_id="1")
    result = _bracket_lines([sf])
    combined = "\n".join(result)
    assert "T1" in combined
    assert "T2" in combined


def test_bracket_lines_shows_round_header():
    sf = _make_event("Semifinal", "1", "2", state="pre")
    combined = "\n".join(_bracket_lines([sf]))
    assert "SEMIFINAL" in combined


def test_bracket_lines_completed_match_shows_winner_arrow():
    sf = _make_event("Semifinal", "10", "13", home_score="1", away_score="0", state="post", winner_id="10")
    combined = "\n".join(_bracket_lines([sf]))
    assert "──►" in combined
    assert "T10" in combined


def test_bracket_lines_multiple_rounds_ordered_earliest_first():
    qf = _make_event("Quarterfinal", "10", "11", home_score="2", away_score="1", state="post", winner_id="10")
    sf = _make_event("Semifinal", "10", "13", home_score="1", away_score="0", state="post", winner_id="10")
    final = _make_event("Final", "10", "3", home_score="2", away_score="1", state="post", winner_id="10")
    combined = "\n".join(_bracket_lines([qf, sf, final]))
    # Use the full header strings to avoid "FINAL" matching inside "SEMIFINAL"
    qf_pos = combined.find("── QUARTERFINAL")
    sf_pos = combined.find("── SEMIFINAL")
    final_pos = combined.find("── FINAL")
    assert qf_pos < sf_pos < final_pos


def test_bracket_lines_pre_match_shows_vs():
    sf = _make_event("Semifinal", "1", "2", state="pre")
    combined = "\n".join(_bracket_lines([sf]))
    assert "vs" in combined


def test_bracket_lines_live_match_shows_green_indicator():
    sf = _make_event("Semifinal", "1", "2", home_score="1", away_score="0", state="in")
    combined = "\n".join(_bracket_lines([sf]))
    assert "green" in combined


def test_bracket_lines_slug_round_renders():
    ev = _make_event("", "1", "2", state="pre")
    ev["season"] = {"slug": "quarterfinals"}
    combined = "\n".join(_bracket_lines([ev]))
    assert "QUARTERFINALS" in combined
