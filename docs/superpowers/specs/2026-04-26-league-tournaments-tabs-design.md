# League Tournament Tabs Implementation Design

**Goal:** Add tabbed navigation to `LeagueScreen` so each league can surface its related domestic tournaments (Copa del Rey, FA Cup, Liguilla, etc.) alongside the main competition, with a compact bracket panel replacing the standings panel for knockout tournaments.

**Architecture:** A `TabbedContent` widget replaces the current `Horizontal` layout in `LeagueScreen`. Tab 0 is always the main league (matches + standings, unchanged). Tabs 1..N are related tournaments (matches by round + bracket). Configuration lives in `leagues.toml`. A new `BracketWidget` renders a compact QF→SF→Final tree in the right panel.

**Tech Stack:** Textual `TabbedContent`/`TabPane`, existing `ESPNClient`, TOML config, box-drawing characters for bracket rendering.

---

## 1. Configuration

### `leagues.toml`

Each league entry gains an optional `related` field — an inline list of `{name, slug}` objects. Leagues with no related tournaments need no changes.

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
slug = "mex.1"
name = "Liga MX"
full_name = "Liga MX"
color = "#006847"
matchday_label = "Week"
flag = "🇲🇽"
# Liguilla is the playoff phase of mex.1, not a separate ESPN slug — no related entries

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
```

Leagues with no related tournaments (UCL, UEL, FIFA WC) keep their existing entries unchanged.

### `src/tapu/config.py`

Add `RelatedTournament` dataclass. Update `League` with a `related` field. Update `load_leagues()` to unpack the raw dicts.

```python
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

---

## 2. API Client

### `src/tapu/api/client.py`

Add one new method that fetches all events for a tournament across the current season (Aug 1 → Jul 31). Reuses the existing cached `get_scoreboard_daterange`.

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

Disk TTL is 1 hour (inherited from `get_scoreboard_daterange`). No extra cache configuration needed.

---

## 3. BracketWidget

### `src/tapu/widgets/bracket.py` (new file)

A static widget that takes a list of ESPN events and renders a compact bracket for the last 3 rounds (QF → SF → Final).

**Round detection:** Each event's round name comes from `competitions[0].notes[0].headline`. We define a priority ordering and pick the 3 most advanced rounds present in the data:

```python
ROUND_PRIORITY = [
    "Final",
    "Semifinal", "Semi-Final",
    "Quarterfinal", "Quarter-Final",
    "Round of 16",
    "Round of 32",
    "Round of 64",
]
```

**Layout:** The right panel is 56 chars wide. The bracket shows three columns (QF, SF, Final) with box-drawing connectors:

```
  QF                  SF               Final

  Barcelona  3 ──┐
                  ├── Barcelona  1 ──┐
  Atlético   1 ──┘                   │
                                      ├── ?
  Real Madrid 2 ──┐                  │
                   ├── Real Madrid 2 ─┘
  Betis      0 ──┘
```

- Team names are truncated to 11 chars (short display name preferred).
- Score shown as single digit or `-` if not yet played.
- `?` shown for matches not yet determined.
- If fewer than 3 rounds exist (early in tournament), show only available rounds.
- If no QF/SF/Final data exists: show `[dim]Bracket not yet available[/dim]`.

**Interface:**

```python
class BracketWidget(Widget):
    def __init__(self, events: list[dict[str, Any]]) -> None: ...
    def compose(self) -> ComposeResult: ...
```

No reactive updates needed — bracket data changes only when `_load_tournament` re-runs.

---

## 4. LeagueScreen Restructuring

### `src/tapu/screens/league.py`

Replace the `Horizontal(matches-col, standings-col)` with `TabbedContent`. Each tab pane contains its own `Horizontal(matches-col, right-col)`.

**Compose structure:**

```python
def compose(self) -> ComposeResult:
    yield Header()
    with TabbedContent():
        with TabPane(self.league.full_name, id="tab-main"):
            with Horizontal(classes="main-row"):
                yield VerticalScroll(id="matches-pane", classes="matches-col")
                yield VerticalScroll(id="standings-pane", classes="standings-col")
        for related in self.league.related:
            tab_id = f"tab-{related.slug.replace('.', '-')}"
            with TabPane(related.name, id=tab_id):
                with Horizontal(classes="main-row"):
                    yield VerticalScroll(id=f"matches-{tab_id}", classes="matches-col")
                    yield VerticalScroll(id=f"bracket-{tab_id}", classes="standings-col")
    yield Footer()
```

**Loading:**

- `on_mount` runs `_load_matches()` and `_load_standings()` for the main tab (unchanged).
- Tournament tabs load lazily: `on_tabbed_content_tab_activated(event)` triggers `_load_tournament(related)` the first time each tournament tab is opened. A `_loaded_tabs: set[str]` tracks which have already been fetched.
- `action_refresh` clears cache and reloads the currently active tab only.
- `action_more` (load older matches) applies only to the main league tab — it is a no-op when a tournament tab is active, since tournament data is fetched as a full season upfront.

**`_load_tournament(related: RelatedTournament)` worker:**

```python
@work(exit_on_error=False)
async def _load_tournament(self, related: RelatedTournament) -> None:
    tab_id = f"tab-{related.slug.replace('.', '-')}"
    matches_pane = self.query_one(f"#matches-{tab_id}", VerticalScroll)
    bracket_pane = self.query_one(f"#bracket-{tab_id}", VerticalScroll)
    try:
        data = await self.client.get_tournament_events(related.slug)
        events = data.get("events", [])
        # Mount match cards grouped by round on the left
        await matches_pane.remove_children()
        for round_name, round_evs in _group_events_by_round(events):
            await matches_pane.mount(Static(round_name, classes="section-header"))
            for ev in round_evs:
                await matches_pane.mount(MatchCard(ev))
        # Mount bracket on the right
        await bracket_pane.remove_children()
        await bracket_pane.mount(BracketWidget(events))
    except Exception:
        await matches_pane.remove_children()
        await matches_pane.mount(Static("[red]Failed to load[/red]", classes="no-matches"))
```

**`_group_events_by_round(events)`:** Groups events by round name from `competitions[0].notes[0].headline`, sorted by round priority (Final first, then SF, QF, etc.).

---

## 5. ESPN Slug Verification

The slugs listed in `leagues.toml` (e.g. `esp.copa_del_rey`, `eng.fa`, `ger.dfb_pokal`, `fra.coupe_de_france`, `arg.copa`) are best guesses based on ESPN's naming conventions. The implementation plan must include a **verification step** — curl each slug against `https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard` before committing the config. Any slug that returns a 404 or empty events must be corrected or removed.

## 6. Error Handling

- Tournament fetch fails → left panel shows `[red]Failed to load[/red]`, right panel is empty. Same pattern as standings failure today.
- Tournament has no QF/SF/Final data → `BracketWidget` shows `[dim]Bracket not yet available[/dim]`.
- Tournament has no events at all → left panel shows `[dim]No matches[/dim]`.
- ESPN slug for a `related` entry doesn't exist → fetch fails gracefully (HTTP error caught by `try/except`).

---

## 6. Files Summary

| File | Change |
|------|--------|
| `leagues.toml` | Add `related` lists to La Liga, EPL, Liga MX, Liga Prof, Bundesliga, Ligue 1 |
| `src/tapu/config.py` | Add `RelatedTournament`, update `League`, update `load_leagues()` |
| `src/tapu/api/client.py` | Add `get_tournament_events()` |
| `src/tapu/screens/league.py` | Replace `Horizontal` with `TabbedContent`, add lazy tab loading, `_load_tournament()` |
| `src/tapu/widgets/bracket.py` | New `BracketWidget` |
