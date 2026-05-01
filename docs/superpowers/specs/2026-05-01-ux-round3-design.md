# UX Round 3 — Form Sparklines & Match Filter

**Date:** 2026-05-01
**Scope:** Pure display and client-side filtering improvements — no new screens, no new API endpoints

## Summary

Two features that add depth to the league view without adding complexity:

1. **Form sparklines** — colored W/D/L dots on each standings row showing last 5 results
2. **Match filter bar** — status chips + team search above the match list in LeagueScreen

---

## Feature 1 — Form Sparklines

### Display

A `Form` column is appended to the right of the `StandingsTable`. Each row shows 5 colored dots representing the last 5 matches (oldest → newest):

| Result | Dot | Color |
|---|---|---|
| Win | ● | `$success` (green) |
| Draw | ● | `$warning` (amber) |
| Loss | ● | `$error` (red) |

Example row: `● ● ● ● ●` = W W D W W

### Data

ESPN's standings API returns a `form` stat on each entry — a string like `"WWDLW"` (each character is one result). This stat is not present on every league. The column is omitted entirely when no entry in the standings has form data — no empty column, no placeholder dots.

### Implementation

**File:** `src/tapu/widgets/standings.py`

A pure helper `_form_dots(form_str: str) -> str` is added:

```python
def _form_dots(form_str: str) -> str:
    colors = {"W": "$success", "D": "$warning", "L": "$error"}
    parts = []
    for ch in form_str.upper():
        color = colors.get(ch)
        if color:
            parts.append(f"[{color}]●[/{color}]")
    return " ".join(parts)
```

In `_fill_table()`:
1. After building existing columns, check if any entry has a non-empty `form` stat.
2. If yes, add a `Form` column header and populate each row with `_form_dots(form_str)`.
3. If no entry has form data, skip the column.

The `_stat()` helper already handles missing stats gracefully (returns `""`) — form extraction uses the same pattern.

---

## Feature 2 — Match Filter Bar

### Display

A compact horizontal bar sits above the matches pane in `LeagueScreen` (non-tournament leagues only, same condition as the matches pane itself). It contains:

- **Status chips** (left): `All · Live · Done · Upcoming` — pill-style buttons, one active at a time, highlighted with `$primary` background when selected
- **Team search input** (right): text field with placeholder "team…", filters live as you type

Both filters apply simultaneously: status chip AND team query are ANDed together.

### Filtering Logic

A pure helper `_apply_filters(events, status, query)` in `league.py`:

```python
def _apply_filters(
    events: list[dict], status: str, query: str
) -> list[dict]:
    if status != "all":
        state_map = {"live": "in", "done": "post", "upcoming": "pre"}
        target = state_map.get(status, "")
        events = [e for e in events if e["status"]["type"].get("state") == target]
    if query:
        q = query.lower()
        events = [
            e for e in events
            if any(
                q in c["team"].get("displayName", "").lower() or
                q in c["team"].get("shortDisplayName", "").lower()
                for c in e["competitions"][0]["competitors"]
            )
        ]
    return events
```

`_render_matches` calls `_apply_filters(events, self._status_filter, self._team_query)` before grouping by day.

### State

Two instance vars added to `LeagueScreen`:

```python
self._status_filter: str = "all"   # "all" | "live" | "done" | "upcoming"
self._team_query: str = ""
self._current_sb: dict = {}        # last fetched scoreboard, for re-rendering on filter change
```

`_current_sb` is set at the end of `_render_matches`. When a filter changes, `_render_matches(self._current_sb)` is called via `self.run_worker(...)`.

### Key Bindings

Added to `LeagueScreen.BINDINGS`:

| Key | Action | Description |
|---|---|---|
| `f` | `cycle_filter` | Cycle status chip: All → Live → Done → Upcoming → All |
| `/` | `focus_search` | Focus the team search input |

`Esc` inside the input clears the query and returns focus to the match list (handled via `on_input_submitted` / `on_key` on the Input widget).

### Layout Change

Current `LeagueScreen` compose for the main tab:
```python
with Horizontal(classes="main-row"):
    yield VerticalScroll(..., id="matches-pane", classes="matches-col")
    yield VerticalScroll(id="standings-pane", classes="standings-col")
```

New layout:
```python
with Horizontal(classes="main-row"):
    with Vertical(classes="matches-col"):
        yield Horizontal(id="filter-bar", classes="filter-bar")  # chips + input
        yield VerticalScroll(..., id="matches-pane")
    yield VerticalScroll(id="standings-pane", classes="standings-col")
```

Filter bar CSS:
```css
LeagueScreen .filter-bar {
    height: 3;
    padding: 0 1;
    border-bottom: solid $surface-lighten-2;
    align: left middle;
}
LeagueScreen .filter-chip {
    padding: 0 2;
    margin-right: 1;
    border: none;
    background: $surface-lighten-1;
    color: $text-muted;
}
LeagueScreen .filter-chip.active {
    background: $primary;
    color: $text;
}
LeagueScreen #filter-input {
    width: 1fr;
    border: none;
    background: $surface-lighten-1;
    margin-left: 1;
}
```

---

## Error Handling

- **No form data**: `_form_dots("")` returns `""`. Column is suppressed when all entries return empty form.
- **Partial form data** (some entries have form, some don't): entries with no form show an empty cell; column is still shown if any entry has form.
- **Filter with no results**: `_render_matches` shows `[dim]No matches[/dim]` (same as empty event list).
- **Filter on background refresh**: `_current_sb` is updated every refresh — active filter is re-applied automatically, so live counts stay accurate.

---

## Files Changed

| File | Change |
|---|---|
| `src/tapu/widgets/standings.py` | Add `_form_dots()` helper; add Form column when data is present |
| `src/tapu/screens/league.py` | Add `_apply_filters()`; add filter bar to compose; add `_current_sb`, `_status_filter`, `_team_query`; add `f`/`/` bindings |
| `tests/test_standings.py` | New — unit tests for `_form_dots` |
| `tests/test_league.py` | Add tests for `_apply_filters` |

---

## Out of Scope

- Standings sorting (click column header to sort by GD, wins, etc.)
- Saving filter state across screen pushes/pops
- Filter on tournament/bracket tabs
- Round 4 (if any): match timeline, player stats
