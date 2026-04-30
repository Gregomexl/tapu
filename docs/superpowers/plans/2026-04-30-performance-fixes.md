# Performance Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate four performance bottlenecks that slow down dashboard load and league screen open time.

**Architecture:** Fix `clear_cache()` to stop nuking disk files, collapse the two mount-time network calls in `LeagueScreen` into a single parallel fetch, and batch widget mounts in both `DashboardScreen` and `LeagueScreen` to reduce layout passes.

**Tech Stack:** Python 3.13, Textual, httpx, pytest, asyncio

---

## Files Changed

| File | Change |
|---|---|
| `src/tapu/api/client.py` | `clear_cache()` clears in-memory dict only |
| `src/tapu/screens/dashboard.py` | Batch-mount `LeagueCard`s in `_load_all()` |
| `src/tapu/screens/league.py` | Replace `_load_matches` + `_load_standings` with single `_load_main`; add `_parse_positions`, `_render_matches`, `_render_standings`; batch-mount in `_render_matches` and `_load_tournament` |
| `tests/test_client.py` | Add test: `clear_cache()` preserves disk files |
| `tests/test_league.py` | New file: unit tests for `_parse_positions` |

---

## Task 1: Fix `clear_cache()` to preserve disk files

**Files:**
- Modify: `src/tapu/api/client.py:122-128`
- Modify: `tests/test_client.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_client.py`:

```python
@pytest.mark.asyncio
async def test_clear_cache_preserves_disk_files(tmp_path, monkeypatch):
    import json, time
    from tapu.api import client as client_module
    monkeypatch.setattr(client_module, "DISK_CACHE_DIR", tmp_path)

    c = ESPNClient()
    cache_file = tmp_path / "some_cached_endpoint.json"
    cache_file.write_text(json.dumps({"ts": time.time(), "data": {"events": []}}))

    c.clear_cache()

    assert cache_file.exists()
    await c.aclose()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_client.py::test_clear_cache_preserves_disk_files -v
```

Expected: FAIL — the current `clear_cache()` deletes all `.json` files in `DISK_CACHE_DIR`.

- [ ] **Step 3: Fix `clear_cache()` in `src/tapu/api/client.py`**

Replace the current `clear_cache` method (lines 122–128):

```python
def clear_cache(self) -> None:
    self._cache.clear()
```

- [ ] **Step 4: Run all client tests**

```bash
uv run pytest tests/test_client.py -v
```

Expected: all PASS, including `test_clear_cache` (which checks in-memory is cleared) and the new disk test.

- [ ] **Step 5: Commit**

```bash
git add src/tapu/api/client.py tests/test_client.py
git commit -m "fix: clear_cache() preserves disk cache files"
```

---

## Task 2: Refactor LeagueScreen to parallel-fetch and share standings

**Files:**
- Modify: `src/tapu/screens/league.py`
- Create: `tests/test_league.py`

This task replaces three methods (`_fetch_positions`, `_load_matches`, `_load_standings`) with four (`_parse_positions`, `_render_matches`, `_render_standings`, `_load_main`) and updates callers. The key change: one `asyncio.gather(get_standings, get_scoreboard_daterange)` at mount instead of two sequential awaits followed by a duplicate standings fetch.

- [ ] **Step 1: Write failing tests for `_parse_positions`**

Create `tests/test_league.py`:

```python
from tapu.screens.league import LeagueScreen


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_league.py -v
```

Expected: FAIL — `_parse_positions` does not exist yet.

- [ ] **Step 3: Replace the three old methods with four new ones in `src/tapu/screens/league.py`**

Remove these methods entirely:
- `_fetch_positions(self)`
- `_load_matches(self)`
- `_load_standings(self)`

Add these four methods:

```python
def _parse_positions(self, standings: dict) -> dict[str, int]:
    positions: dict[str, int] = {}
    for child in standings.get("children", []):
        for i, entry in enumerate(child.get("standings", {}).get("entries", []), 1):
            positions[str(entry["team"]["id"])] = i
    if not positions:
        for i, entry in enumerate(standings.get("standings", {}).get("entries", []), 1):
            positions[str(entry["team"]["id"])] = i
    return positions

async def _render_matches(self, sb: dict) -> None:
    today = date.today()
    pane = self.query_one("#matches-pane", VerticalScroll)
    events = sb.get("events", [])
    await pane.remove_children()
    if not events:
        await pane.mount(Static("[dim]No matches[/dim]", classes="no-matches"))
        return
    widgets: list = []
    for day, day_evs in _group_events_by_day(events):
        widgets.append(Static(_day_label(day, today), classes="section-header"))
        for ev in day_evs:
            widgets.append(MatchCard(ev, positions=self._positions))
    await pane.mount(*widgets)

async def _render_standings(self, standings: dict) -> None:
    pane = self.query_one("#standings-pane", VerticalScroll)
    await pane.remove_children()
    children = standings.get("children", [])
    if self.league.is_tournament and len(children) > 4:
        await pane.mount(WCGroupsWidget(standings))
    else:
        await pane.mount(StandingsTable(standings, self.league.relegation_spots, self.league.promotion_spots))

async def _load_main(self) -> None:
    today = date.today()
    start = today - timedelta(days=self._days_back)

    if self.league.is_tournament:
        try:
            standings = await self.client.get_standings(self.league.slug)
            await self._render_standings(standings)
        except Exception:
            pane = self.query_one("#standings-pane", VerticalScroll)
            await pane.remove_children()
            await pane.mount(Static("[red]Standings unavailable[/red]"))
        return

    results = await asyncio.gather(
        self.client.get_standings(self.league.slug),
        self.client.get_scoreboard_daterange(
            self.league.slug,
            _date_to_api(start),
            _date_to_api(today),
        ),
        return_exceptions=True,
    )
    standings, sb = results[0], results[1]

    if not isinstance(standings, Exception):
        self._positions = self._parse_positions(standings)

    matches_pane = self.query_one("#matches-pane", VerticalScroll)
    standings_pane = self.query_one("#standings-pane", VerticalScroll)

    if isinstance(sb, Exception):
        await matches_pane.remove_children()
        await matches_pane.mount(Static("[red]Failed to load[/red]", classes="no-matches"))
    else:
        await self._render_matches(sb)

    if isinstance(standings, Exception):
        await standings_pane.remove_children()
        await standings_pane.mount(Static("[red]Standings unavailable[/red]"))
    else:
        await self._render_standings(standings)
```

- [ ] **Step 4: Update callers of the removed methods**

Update `on_mount` — replace the two `run_worker` calls with one:

```python
def on_mount(self) -> None:
    self.sub_title = self.league.full_name
    self.run_worker(self._load_main())
    self._refresh_timer = self.set_interval(60, self._tick_refresh)
```

Update `_bg_refresh` — `_load_main` is a plain async method so it can be awaited directly inside this `@work`-decorated method, just like `_load_matches` was:

```python
@work(exit_on_error=False)
async def _bg_refresh(self) -> None:
    await self._load_main()
```

Update `action_more`:

```python
def action_more(self) -> None:
    active = self.query_one(TabbedContent).active
    if active != "tab-main":
        return
    self._days_back += 7
    self.run_worker(self._load_main())
```

Update the `tab-main` branch of `action_refresh`:

```python
def action_refresh(self) -> None:
    self.client.clear_cache()
    active = self.query_one(TabbedContent).active
    if active == "tab-main" or not active:
        self.run_worker(self._load_main())
    elif active == "tab-bracket":
        self._loaded_tabs.discard(active)
        self._load_league_bracket()
    else:
        self._loaded_tabs.discard(active)
        for related in self.league.related:
            if f"tab-{related.slug.replace('.', '-')}" == active:
                self._load_tournament(related)
                break
```

- [ ] **Step 5: Run the new unit tests**

```bash
uv run pytest tests/test_league.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 6: Run the full test suite**

```bash
uv run pytest -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/tapu/screens/league.py tests/test_league.py
git commit -m "perf: parallel standings+daterange fetch in LeagueScreen"
```

---

## Task 3: Batch-mount LeagueCards in DashboardScreen

**Files:**
- Modify: `src/tapu/screens/dashboard.py:106-113`

- [ ] **Step 1: Replace the loop-mount with batch-mount in `_load_all`**

Find the loop in `_load_all` (lines 106–113) and replace it:

```python
await grid.remove_children()
cards: list = []
for league in self.leagues:
    card_id = f"card-{league.slug.replace('.', '-')}"
    sb = self._scoreboards.get(league.slug, {})
    cards.append(LeagueCard(league, sb, self.client, id=card_id))
await grid.mount(*cards)
if cards:
    cards[0].focus()
```

- [ ] **Step 2: Run the full test suite**

```bash
uv run pytest -v
```

Expected: all tests PASS.

- [ ] **Step 3: Commit**

```bash
git add src/tapu/screens/dashboard.py
git commit -m "perf: batch-mount league cards in DashboardScreen"
```

---

## Task 4: Batch-mount match cards in `_load_tournament`

**Files:**
- Modify: `src/tapu/screens/league.py` — `_load_tournament` method

`_render_matches` (added in Task 2) already batch-mounts. This task updates `_load_tournament` to do the same for the related-tournament tabs.

- [ ] **Step 1: Replace the loop-mounts in `_load_tournament`**

Find `_load_tournament` and replace both per-widget `await matches_pane.mount(...)` loops:

```python
@work(exit_on_error=False)
async def _load_tournament(self, related: RelatedTournament) -> None:
    tab_id = f"tab-{related.slug.replace('.', '-')}"
    matches_pane = self.query_one(f"#matches-{tab_id}", VerticalScroll)
    bracket_pane = self.query_one(f"#bracket-{tab_id}", VerticalScroll)
    try:
        data = await self.client.get_knockout_events(related.slug)
        events = data.get("events", [])
        await matches_pane.remove_children()
        if not events:
            await matches_pane.mount(Static("[dim]No matches[/dim]", classes="no-matches"))
        else:
            widgets: list = []
            rounds = _group_events_by_round(events)
            for round_name, round_evs in rounds:
                widgets.append(Static(round_name, classes="section-header"))
                for ev in round_evs:
                    widgets.append(MatchCard(ev))
            await matches_pane.mount(*widgets)
        await bracket_pane.remove_children()
        await bracket_pane.mount(BracketWidget(events))
    except Exception:
        await matches_pane.remove_children()
        await matches_pane.mount(Static("[red]Failed to load[/red]", classes="no-matches"))
```

- [ ] **Step 2: Run the full test suite**

```bash
uv run pytest -v
```

Expected: all tests PASS.

- [ ] **Step 3: Commit**

```bash
git add src/tapu/screens/league.py
git commit -m "perf: batch-mount match cards in _load_tournament"
```
