# League Tournament Tabs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add tabbed navigation to `LeagueScreen` so leagues with related domestic tournaments (Copa del Rey, FA Cup, etc.) surface them in separate tabs, each showing matches grouped by round on the left and a compact bracket (QF→SF→Final) on the right.

**Architecture:** `TabbedContent` replaces the current `Horizontal` layout in `LeagueScreen`. Tab 0 is always the main league (unchanged). Tabs 1..N are related tournaments, loaded lazily on first activation. A new `BracketWidget` renders QF→SF→Final as pre-formatted text with box-drawing connectors. Related tournaments are configured in `leagues.toml` as `related = [{name, slug}]` inline tables.

**Tech Stack:** Textual `TabbedContent`/`TabPane`, `ESPNClient`, `tomllib`, box-drawing chars.

---

## File Map

| File | Change |
|------|--------|
| `leagues.toml` | Add `related` lists to La Liga, EPL, Bundesliga, Ligue 1, Liga Prof |
| `src/tapu/config.py` | Add `RelatedTournament` dataclass, update `League`, update `load_leagues()` |
| `src/tapu/api/client.py` | Add `get_tournament_events()` |
| `src/tapu/widgets/bracket.py` | New file — `BracketWidget` + all rendering helpers |
| `src/tapu/screens/league.py` | Replace `Horizontal` with `TabbedContent`, add `_load_tournament()` |
| `tests/test_config.py` | Extend with `RelatedTournament` tests |
| `tests/test_client.py` | Add `get_tournament_events` test |
| `tests/test_bracket.py` | New file — bracket helper + widget tests |

---

## Task 1: Verify ESPN Tournament Slugs

**Files:**
- Modify: `leagues.toml`

- [ ] **Step 1: Curl each candidate slug and check for valid responses**

```bash
for slug in esp.copa_del_rey esp.super_cup eng.fa eng.league_cup ger.dfb_pokal fra.coupe_de_france arg.copa; do
  echo -n "$slug: "
  curl -s "https://site.api.espn.com/apis/site/v2/sports/soccer/$slug/scoreboard" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); evs=d.get('events',[]); print(f'{len(evs)} events, league={d.get(\"leagues\",[{}])[0].get(\"name\",\"?\") if d.get(\"leagues\") else \"?\"}')" 2>/dev/null || echo "FAILED"
done
```

Expected: each slug prints a number of events and a league name. A `FAILED` or `0 events` with no league name means the slug is wrong.

- [ ] **Step 2: For any slug that fails, try common ESPN variant names**

Known ESPN conventions to try if a slug fails:
- `esp.copa_del_rey` → try `esp.copa`
- `eng.league_cup` → try `eng.carabao` or `eng.efl.cup`
- `fra.coupe_de_france` → try `fra.coupe`
- `arg.copa` → try `arg.copa_argentina`

```bash
# Example retry
curl -s "https://site.api.espn.com/apis/site/v2/sports/soccer/esp.copa/scoreboard" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('leagues',[{}])[0].get('name','?'))"
```

- [ ] **Step 3: Update `leagues.toml` with verified slugs**

Replace the La Liga, EPL, Bundesliga, Ligue 1, and Liga Prof entries with `related` fields. Use only slugs confirmed in Step 1. Remove any slug that fails entirely.

```toml
[[leagues]]
slug = "esp.1"
name = "La Liga"
full_name = "La Liga"
color = "#ee8707"
matchday_label = "Matchday"
relegation_spots = 3
flag = "🇪🇸"
related = [
  {name = "Copa del Rey", slug = "esp.copa_del_rey"},
  {name = "Supercopa",    slug = "esp.super_cup"},
]

[[leagues]]
slug = "eng.1"
name = "EPL"
full_name = "English Premier League"
color = "#3d0068"
matchday_label = "Matchweek"
relegation_spots = 3
flag = "🏴󠁧󠁢󠁥󠁮󠁧󠁿"
related = [
  {name = "FA Cup",      slug = "eng.fa"},
  {name = "Carabao Cup", slug = "eng.league_cup"},
]

[[leagues]]
slug = "ger.1"
name = "Bundesliga"
full_name = "Bundesliga"
color = "#d20515"
matchday_label = "Matchday"
relegation_spots = 3
flag = "🇩🇪"
related = [
  {name = "DFB-Pokal", slug = "ger.dfb_pokal"},
]

[[leagues]]
slug = "fra.1"
name = "Ligue 1"
full_name = "Ligue 1"
color = "#0a2d6e"
matchday_label = "Matchday"
relegation_spots = 3
flag = "🇫🇷"
related = [
  {name = "Coupe de France", slug = "fra.coupe_de_france"},
]

[[leagues]]
slug = "arg.1"
name = "Liga Prof"
full_name = "Liga Profesional"
color = "#74acdf"
matchday_label = "Fecha"
relegation_spots = 3
flag = "🇦🇷"
related = [
  {name = "Copa Argentina", slug = "arg.copa"},
]
```

(Leagues with no related entries — UCL, UEL, FIFA WC, Liga MX — keep their current entries unchanged.)

- [ ] **Step 4: Commit**

```bash
git add leagues.toml
git commit -m "config: add related tournament slugs to leagues.toml"
```

---

## Task 2: Config — RelatedTournament + League

**Files:**
- Modify: `src/tapu/config.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_config.py`:

```python
from tapu.config import League, RelatedTournament, load_leagues


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_config.py::test_related_tournament_dataclass tests/test_config.py::test_league_default_related_is_empty tests/test_config.py::test_load_leagues_with_related tests/test_config.py::test_load_leagues_without_related_defaults_to_empty -v
```

Expected: FAIL with `ImportError: cannot import name 'RelatedTournament'`

- [ ] **Step 3: Implement `RelatedTournament`, update `League`, update `load_leagues()`**

Replace the entire contents of `src/tapu/config.py`:

```python
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RelatedTournament:
    name: str
    slug: str


@dataclass(frozen=True)
class League:
    slug: str
    name: str
    full_name: str
    color: str = "#ffffff"
    matchday_label: str = "Week"
    relegation_spots: int = 0
    flag: str = ""
    related: tuple[RelatedTournament, ...] = ()


def load_leagues(path: Path | None = None) -> list[League]:
    if path is None:
        path = Path(__file__).parent.parent.parent / "leagues.toml"
    with path.open("rb") as f:
        data = tomllib.load(f)
    leagues = []
    for entry in data["leagues"]:
        raw_related = entry.pop("related", [])
        related = tuple(RelatedTournament(**r) for r in raw_related)
        leagues.append(League(**entry, related=related))
    return leagues
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_config.py -v
```

Expected: all tests PASS (including the 3 pre-existing tests).

- [ ] **Step 5: Commit**

```bash
git add src/tapu/config.py tests/test_config.py
git commit -m "feat: add RelatedTournament config support"
```

---

## Task 3: API — get_tournament_events()

**Files:**
- Modify: `src/tapu/api/client.py`
- Modify: `tests/test_client.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_client.py`:

```python
@pytest.mark.asyncio
async def test_get_tournament_events_builds_season_date_range(client, sample_scoreboard):
    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(sample_scoreboard)

        result = await client.get_tournament_events("esp.copa_del_rey")

        url = mock_get.call_args[0][0]
        assert "esp.copa_del_rey" in url
        assert "scoreboard" in url
        assert "dates=" in url
        # URL contains a date range of the form YYYYMMDD-YYYYMMDD
        import re
        assert re.search(r"dates=\d{8}-\d{8}", url)
        assert result == sample_scoreboard
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_client.py::test_get_tournament_events_builds_season_date_range -v
```

Expected: FAIL with `AttributeError: 'ESPNClient' object has no attribute 'get_tournament_events'`

- [ ] **Step 3: Implement `get_tournament_events()`**

Add to `src/tapu/api/client.py` after the `get_match_summary` method:

```python
async def get_tournament_events(self, slug: str) -> dict[str, Any]:
    today = datetime.now()
    if today.month >= 8:
        season_start = today.replace(month=8, day=1).strftime("%Y%m%d")
        season_end = today.replace(year=today.year + 1, month=7, day=31).strftime("%Y%m%d")
    else:
        season_start = today.replace(year=today.year - 1, month=8, day=1).strftime("%Y%m%d")
        season_end = today.replace(month=7, day=31).strftime("%Y%m%d")
    return await self.get_scoreboard_daterange(slug, season_start, season_end)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_client.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/tapu/api/client.py tests/test_client.py
git commit -m "feat: add get_tournament_events to ESPNClient"
```

---

## Task 4: BracketWidget — helpers

**Files:**
- Create: `src/tapu/widgets/bracket.py`
- Create: `tests/test_bracket.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_bracket.py`:

```python
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
    # notes headline is "", should return ""
    assert _event_round(ev) == ""


def test_winner_id_returns_none_for_pre_match():
    ev = _make_event("Final", "1", "2", state="pre")
    assert _winner_id(ev) is None


def test_winner_id_returns_none_for_in_progress():
    ev = _make_event("Final", "1", "2", home_score="1", away_score="0", state="in")
    assert _winner_id(ev) is None


def test_winner_id_returns_home_winner():
    ev = _make_event("Final", "1", "2", home_score="2", away_score="1", state="post")
    assert _winner_id(ev) == "1"


def test_winner_id_returns_away_winner():
    ev = _make_event("Final", "1", "2", home_score="0", away_score="1", state="post")
    assert _winner_id(ev) == "2"


def test_bracket_lines_empty_returns_placeholder():
    result = _bracket_lines([])
    assert result == ["[dim]Bracket not yet available[/dim]"]


def test_bracket_lines_no_round_data_returns_placeholder():
    ev = _make_event("", "1", "2")  # no headline
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
    assert "├─" in combined  # QF connector present
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_bracket.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'tapu.widgets.bracket'`

- [ ] **Step 3: Implement helpers in `src/tapu/widgets/bracket.py`**

Create `src/tapu/widgets/bracket.py`:

```python
from typing import Any

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


ROUND_PRIORITY: list[tuple[int, list[str]]] = [
    (0, ["final"]),
    (1, ["semifinal", "semi-final", "semifinales"]),
    (2, ["quarterfinal", "quarter-final", "cuartos"]),
    (3, ["round of 16", "ronda de 16"]),
    (4, ["round of 32"]),
    (5, ["round of 64"]),
]


def _round_key(headline: str) -> int:
    h = headline.lower().strip()
    for key, terms in ROUND_PRIORITY:
        if any(t in h for t in terms):
            return key
    return 99


def _event_round(event: dict) -> str:
    notes = event.get("competitions", [{}])[0].get("notes", [])
    return notes[0].get("headline", "").strip() if notes else ""


def _winner_id(event: dict) -> str | None:
    if event.get("status", {}).get("type", {}).get("state") != "post":
        return None
    competitors = event["competitions"][0]["competitors"]
    try:
        scored = [(c, int(c.get("score") or "0")) for c in competitors]
        winner = max(scored, key=lambda x: x[1])[0]
        return str(winner["team"]["id"])
    except (ValueError, TypeError, IndexError):
        return None


def _fmt_team(comp: dict, width: int = 10) -> str:
    """Return '{name:<width} {score:>2}' — always exactly width+3 chars."""
    name = (comp["team"].get("shortDisplayName") or comp["team"].get("abbreviation", "?"))[:width]
    score = comp.get("score") or "-"
    return f"{name:<{width}} {score:>2}"


def _get_competitors(event: dict) -> tuple[dict, dict]:
    comps = event["competitions"][0]["competitors"]
    home = next((c for c in comps if c["homeAway"] == "home"), comps[0])
    away = next((c for c in comps if c["homeAway"] == "away"), comps[min(1, len(comps) - 1)])
    return home, away


def _bracket_lines(events: list[dict]) -> list[str]:
    """Build text lines for a tournament bracket (QF→SF→Final)."""
    if not events:
        return ["[dim]Bracket not yet available[/dim]"]

    # Group events by round
    by_round: dict[str, list[dict]] = {}
    for ev in events:
        r = _event_round(ev)
        if r:
            by_round.setdefault(r, []).append(ev)
    if not by_round:
        return ["[dim]Bracket not yet available[/dim]"]

    sorted_rounds = sorted(by_round.items(), key=lambda x: _round_key(x[0]))

    # Extract known rounds by priority key
    qf_evs: list[dict] = []
    sf_evs: list[dict] = []
    final_evs: list[dict] = []
    for name, evs in sorted_rounds:
        k = _round_key(name)
        if k == 2:
            qf_evs = evs
        elif k == 1:
            sf_evs = evs
        elif k == 0:
            final_evs = evs

    if not sf_evs and not final_evs:
        return ["[dim]Bracket not yet available[/dim]"]

    N = 10  # team name display width
    gap = " " * (N + 3)  # blank placeholder matching _fmt_team width

    # Map QF winner team ID → QF event
    qf_by_winner: dict[str, dict] = {}
    for ev in qf_evs:
        wid = _winner_id(ev)
        if wid:
            qf_by_winner[wid] = ev

    def null_team(width: int = N) -> str:
        return f"{'?':<{width}}  -"

    lines: list[str] = []

    # Header row
    if qf_evs:
        lines.append(f"  {'QUARTERFINALS':<{N + 3}}  SEMIFINALS")
    else:
        lines.append("  SEMIFINALS")
    lines.append("")

    # Render each SF match with its QF sources
    for sf_ev in sf_evs:
        sf_home, sf_away = _get_competitors(sf_ev)
        home_id = str(sf_home["team"]["id"])
        away_id = str(sf_away["team"]["id"])

        qf_for_home = qf_by_winner.get(home_id)
        qf_for_away = qf_by_winner.get(away_id)

        # Top sub-block: QF that produced sf_home
        if qf_for_home:
            qh, qa = _get_competitors(qf_for_home)
            lines.append(f"  {_fmt_team(qh, N)} ─┐")
            lines.append(f"  {gap}  ├─ {_fmt_team(sf_home, N)}")
            lines.append(f"  {_fmt_team(qa, N)} ─┘")
        else:
            lines.append(f"  {null_team(N)} ─┐")
            lines.append(f"  {gap}  ├─ {_fmt_team(sf_home, N)}")
            lines.append(f"  {null_team(N)} ─┘")

        lines.append("")

        # Bottom sub-block: QF that produced sf_away
        if qf_for_away:
            qh, qa = _get_competitors(qf_for_away)
            lines.append(f"  {_fmt_team(qh, N)} ─┐")
            lines.append(f"  {gap}  ├─ {_fmt_team(sf_away, N)}")
            lines.append(f"  {_fmt_team(qa, N)} ─┘")
        else:
            lines.append(f"  {null_team(N)} ─┐")
            lines.append(f"  {gap}  ├─ {_fmt_team(sf_away, N)}")
            lines.append(f"  {null_team(N)} ─┘")

        lines.append("")

    # Final section
    lines.append("  " + "─" * 30)
    lines.append("  FINAL")
    lines.append("")

    if final_evs:
        fin_home, fin_away = _get_competitors(final_evs[0])
        state = final_evs[0].get("status", {}).get("type", {}).get("state", "pre")
        if state == "post":
            lines.append(f"  {_fmt_team(fin_home, N)}  –  {_fmt_team(fin_away, N)}")
        elif state == "in":
            lines.append(
                f"  {_fmt_team(fin_home, N)}  [green]LIVE[/green]  {_fmt_team(fin_away, N)}"
            )
        else:
            h_name = (fin_home["team"].get("shortDisplayName") or fin_home["team"].get("abbreviation", "?"))[:N]
            a_name = (fin_away["team"].get("shortDisplayName") or fin_away["team"].get("abbreviation", "?"))[:N]
            lines.append(f"  {h_name:<{N}}  vs  {a_name:<{N}}")
    else:
        # SF played, Final match not yet scheduled — derive finalists from SF winners
        finalists: list[str] = []
        for sf_ev in sf_evs:
            wid = _winner_id(sf_ev)
            if wid:
                sf_home, sf_away = _get_competitors(sf_ev)
                comp = sf_home if str(sf_home["team"]["id"]) == wid else sf_away
                finalists.append(
                    (comp["team"].get("shortDisplayName") or comp["team"].get("abbreviation", "?"))[:N]
                )
        if len(finalists) >= 2:
            lines.append(f"  {finalists[0]:<{N}}  vs  {finalists[1]:<{N}}")
        elif len(finalists) == 1:
            lines.append(f"  {finalists[0]:<{N}}  vs  [dim]TBD[/dim]")
        else:
            lines.append("  [dim]TBD[/dim]")

    return lines
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_bracket.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/tapu/widgets/bracket.py tests/test_bracket.py
git commit -m "feat: add BracketWidget helpers and bracket line renderer"
```

---

## Task 5: BracketWidget — compose()

**Files:**
- Modify: `src/tapu/widgets/bracket.py`
- Modify: `tests/test_widgets.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_widgets.py`:

```python
from textual.app import App, ComposeResult
from tapu.widgets.bracket import BracketWidget


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_widgets.py::test_bracket_widget_renders tests/test_widgets.py::test_bracket_widget_renders_empty -v
```

Expected: FAIL with `AttributeError` — `BracketWidget` has no `compose`.

- [ ] **Step 3: Add `BracketWidget` class to `src/tapu/widgets/bracket.py`**

Append to the end of `src/tapu/widgets/bracket.py`:

```python
class BracketWidget(Widget):
    DEFAULT_CSS = """
    BracketWidget {
        height: auto;
        width: 100%;
        padding: 1 0;
    }
    """

    def __init__(self, events: list[dict[str, Any]]) -> None:
        super().__init__()
        self._events = events

    def compose(self) -> ComposeResult:
        for line in _bracket_lines(self._events):
            yield Static(line)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_widgets.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/tapu/widgets/bracket.py tests/test_widgets.py
git commit -m "feat: add BracketWidget compose"
```

---

## Task 6: LeagueScreen — TabbedContent restructure

**Files:**
- Modify: `src/tapu/screens/league.py`

- [ ] **Step 1: Replace imports and add `_group_events_by_round` helper**

At the top of `src/tapu/screens/league.py`, add to the imports:

```python
from textual.widgets import Footer, Header, Static, TabbedContent, TabPane

from tapu.config import League, RelatedTournament
from tapu.widgets.bracket import BracketWidget, _event_round, _round_key
```

Add this function after `_group_events_by_day` (around line 43):

```python
def _group_events_by_round(events: list) -> list[tuple[str, list]]:
    """Return [(round_name, [events]), ...] sorted most-advanced first."""
    by_round: dict[str, list] = {}
    for ev in events:
        r = _event_round(ev)
        if r:
            by_round.setdefault(r, []).append(ev)
    return sorted(by_round.items(), key=lambda x: _round_key(x[0]))
```

- [ ] **Step 2: Rewrite `LeagueScreen.compose()` to use `TabbedContent`**

Replace the `compose` method in `src/tapu/screens/league.py`:

```python
def compose(self) -> ComposeResult:
    yield Header()
    with TabbedContent():
        with TabPane(self.league.full_name, id="tab-main"):
            with Horizontal(classes="main-row"):
                yield VerticalScroll(
                    Static("[dim]Loading...[/dim]", classes="no-matches"),
                    id="matches-pane",
                    classes="matches-col",
                )
                yield VerticalScroll(id="standings-pane", classes="standings-col")
        for related in self.league.related:
            tab_id = f"tab-{related.slug.replace('.', '-')}"
            with TabPane(related.name, id=tab_id):
                with Horizontal(classes="main-row"):
                    yield VerticalScroll(
                        Static("[dim]Loading...[/dim]", classes="no-matches"),
                        id=f"matches-{tab_id}",
                        classes="matches-col",
                    )
                    yield VerticalScroll(id=f"bracket-{tab_id}", classes="standings-col")
    yield Footer()
```

- [ ] **Step 3: Add `_loaded_tabs` instance variable and update `__init__`**

In `LeagueScreen.__init__`, add:

```python
def __init__(self, client: ESPNClient, league: League, scoreboard: dict) -> None:
    super().__init__()
    self.client = client
    self.league = league
    self._days_back = 7
    self._refresh_timer: Timer | None = None
    self._positions: dict[str, int] = {}
    self._loaded_tabs: set[str] = set()
```

- [ ] **Step 4: Add lazy tab loading event handler**

Add this method to `LeagueScreen`:

```python
def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
    pane_id = event.pane.id if event.pane else None
    if not pane_id or pane_id == "tab-main" or pane_id in self._loaded_tabs:
        return
    self._loaded_tabs.add(pane_id)
    for related in self.league.related:
        if f"tab-{related.slug.replace('.', '-')}" == pane_id:
            self._load_tournament(related)
            break
```

- [ ] **Step 5: Add `_load_tournament` worker**

Add this method to `LeagueScreen`:

```python
@work(exit_on_error=False)
async def _load_tournament(self, related: RelatedTournament) -> None:
    tab_id = f"tab-{related.slug.replace('.', '-')}"
    matches_pane = self.query_one(f"#matches-{tab_id}", VerticalScroll)
    bracket_pane = self.query_one(f"#bracket-{tab_id}", VerticalScroll)
    try:
        data = await self.client.get_tournament_events(related.slug)
        events = data.get("events", [])
        await matches_pane.remove_children()
        if not events:
            await matches_pane.mount(Static("[dim]No matches[/dim]", classes="no-matches"))
        else:
            for round_name, round_evs in _group_events_by_round(events):
                await matches_pane.mount(Static(round_name, classes="section-header"))
                for ev in round_evs:
                    await matches_pane.mount(MatchCard(ev))
        await bracket_pane.remove_children()
        await bracket_pane.mount(BracketWidget(events))
    except Exception:
        await matches_pane.remove_children()
        await matches_pane.mount(Static("[red]Failed to load[/red]", classes="no-matches"))
```

- [ ] **Step 6: Update `action_refresh` to handle active tournament tab**

Replace the `action_refresh` method:

```python
def action_refresh(self) -> None:
    self.client.clear_cache()
    active = self.query_one(TabbedContent).active
    if active == "tab-main" or not active:
        self._positions.clear()
        self.run_worker(self._load_matches())
        self.run_worker(self._load_standings())
    else:
        self._loaded_tabs.discard(active)
        for related in self.league.related:
            if f"tab-{related.slug.replace('.', '-')}" == active:
                self._load_tournament(related)
                break
```

- [ ] **Step 7: Make `action_more` a no-op on tournament tabs**

Replace the `action_more` method:

```python
def action_more(self) -> None:
    active = self.query_one(TabbedContent).active
    if active != "tab-main":
        return
    self._days_back += 7
    self.run_worker(self._load_matches())
```

- [ ] **Step 8: Run all tests**

```bash
uv run pytest -v
```

Expected: all tests PASS.

- [ ] **Step 9: Smoke-test in the terminal**

```bash
uv run tapu
```

- Open a league that has related tournaments (e.g. La Liga)
- Confirm the tab bar shows `La Liga | Copa del Rey | Supercopa`
- Press `tab` / `shift+tab` to switch between tabs
- Confirm tournament tab loads matches grouped by round on the left and bracket on the right
- Press `r` on the tournament tab — confirm it reloads without error
- Press `r` on the main tab — confirm standings and matches refresh

- [ ] **Step 10: Commit**

```bash
git add src/tapu/screens/league.py
git commit -m "feat: add TabbedContent with tournament tabs to LeagueScreen"
```

---

## Task 7: Push

- [ ] **Step 1: Push all commits**

```bash
git push
```

Expected: all commits pushed to remote.
