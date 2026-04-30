# Performance Fixes Design

**Date:** 2026-04-30
**Scope:** Reduce dashboard load time and league screen open latency

## Problem

Four bottlenecks slow down the two most common user interactions:

1. **Dashboard load** — widgets are mounted one at a time in a loop, each triggering a layout pass.
2. **League screen open** — `_load_matches()` awaits `_fetch_positions()` before starting the daterange fetch (sequential instead of parallel), and both `_load_matches()` and `_load_standings()` independently call `get_standings()` at mount, racing to make the same network request.
3. **Manual refresh** — `clear_cache()` deletes all disk cache files, including standings with a 1h TTL, forcing slow re-fetches that are unnecessary.

## Fixes

### Fix 1 — Parallelize positions + daterange in `_load_matches()`

**File:** `src/tapu/screens/league.py`

Current flow (sequential):
```
await _fetch_positions()       # ~300ms
await get_scoreboard_daterange()  # ~400ms
# total: ~700ms
```

New flow (parallel):
```
asyncio.gather(
    _fetch_positions(),
    get_scoreboard_daterange(),
)
# total: ~400ms (limited by the slower call)
```

Both calls are independent — positions come from the standings endpoint, daterange from the scoreboard endpoint.

### Fix 2 — Share standings result between `_load_matches` and `_load_standings`

**File:** `src/tapu/screens/league.py`

Current `on_mount` launches two workers:
- `_load_matches()` → calls `get_standings()` internally via `_fetch_positions()`
- `_load_standings()` → also calls `get_standings()`

Both fire concurrently at mount, so on first open they race to the same uncached endpoint.

New approach: a single coordinating worker `_load_main()` runs one `asyncio.gather(get_standings(), get_scoreboard_daterange())` and distributes results to both panes. `_load_matches()` and `_load_standings()` become pure render functions that accept pre-fetched data rather than fetching themselves. The 60s background refresh calls `_load_main()` the same way.

### Fix 3 — Batch-mount widgets

**Files:** `src/tapu/screens/dashboard.py`, `src/tapu/screens/league.py`

Replace per-widget `await pane.mount(widget)` loops with:
```python
widgets = []
for ...:
    widgets.append(SectionHeader(...))
    for ev in day_evs:
        widgets.append(MatchCard(ev, ...))
await pane.mount(*widgets)
```

Textual performs one layout pass for the entire batch. Section headers and match cards preserve their interleaved order since list insertion order is maintained.

Same pattern applies to `DashboardScreen._load_all()` for `LeagueCard` mounting.

### Fix 4 — `clear_cache()` preserves disk files

**File:** `src/tapu/api/client.py`

`clear_cache()` currently deletes all `.json` files in `~/.cache/tapu/`. Change it to only clear the in-memory `_cache` dict. Disk entries expire naturally by their TTL (1h for standings/daterange). This means `r` (refresh) still forces a fresh network request for live data (in-memory TTL bypassed) while preserving slow-changing data on disk.

```python
def clear_cache(self) -> None:
    self._cache.clear()
    # disk cache intentionally preserved — entries expire by TTL
```

## Expected Impact

| Interaction | Before | After |
|---|---|---|
| Dashboard first load | N sequential layout passes | 1 layout pass |
| League screen open (cold) | ~700ms (positions → daterange) | ~400ms (parallel) |
| League screen open (standings cached) | 2 network calls | 1 network call |
| Manual refresh | Clears 1h-TTL disk cache | Preserves disk cache |

## Files Changed

- `src/tapu/screens/dashboard.py` — batch-mount in `_load_all()`
- `src/tapu/screens/league.py` — parallelize fetches, share standings, batch-mount
- `src/tapu/api/client.py` — `clear_cache()` in-memory only

## Out of Scope

- Prefetching on LeagueCard focus (good follow-up once these fixes land)
- Startup disk warming for all leagues' standings
