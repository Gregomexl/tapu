# UX Round 1 — Visual Polish & Feedback Design

**Date:** 2026-04-30
**Scope:** Pure display improvements — no new screens, no new API calls

## Summary

Three visual improvements that make the app feel alive and responsive:

1. **Status chips + pulse dot** — color-coded match status badges and an animated dot on live cards
2. **Score change flash** — bright border + green score when a goal is detected on background refresh
3. **Toast + "Updated X ago" counter** — feedback when manual refresh completes and a live timestamp

## Changes by File

| File | Change |
|---|---|
| `src/tapu/widgets/match_card.py` | Status chips, pulse dot, flash state |
| `src/tapu/screens/dashboard.py` | Score change detection, toast, "updated ago" counter |

---

## Feature 1 — Status Chips + Pulse Dot

### Status chips

Replace the plain-text status label in `MatchCard` with a Rich `Text` object using themed colors:

| Status | Label | Color |
|---|---|---|
| Live (`state == "in"`, not HT) | `LIVE` | `$error` (red) |
| Half-time (`displayClock == "HT"`) | `HT` | `$warning` (amber) |
| Final (`state == "post"`) | `FT` | `$text-muted` (grey) |
| Upcoming (`state == "pre"`) | kickoff time | `$accent` (blue) |

Implementation: a `_status_chip()` method on `MatchCard` returns the appropriately colored `Text`. Called from `render()` / `compose()`.

### Pulse dot

A `●` character rendered before the team names on live cards only. It toggles between full opacity and 30% opacity every 700ms via a `set_interval` timer on `MatchCard.on_mount()`. Implemented as a CSS class toggle (`.pulsing`) on a dedicated `Static` child widget. Only started when `state == "in"`. Timer cancelled on unmount.

HT cards get an amber static dot (no animation — half time is not live action).

---

## Feature 2 — Score Change Flash

### Detection (DashboardScreen)

In `DashboardScreen._load_all()`, before overwriting `self._scoreboards`, compare old vs new events for score changes:

```python
for event in new_events:
    event_id = event["id"]
    old_event = _find_event(old_scoreboard, event_id)
    if old_event and _scores_changed(old_event, event):
        # post flash message to the matching LeagueCard / MatchCard if visible
        self._flash_ids.add(event_id)
```

`_scores_changed(a, b)` extracts both competitors' scores and returns `True` if either changed.

### Flash state on MatchCard

`MatchCard` accepts an optional `flash: bool = False` constructor parameter. When `True` on mount, it:
1. Adds CSS class `--flashing` (bright green border, green score color)
2. Starts a `set_timer(3.0, self._clear_flash)` that removes the class after 3 seconds

The flash only applies on the **DashboardScreen** context (where `_scoreboards` are tracked). `LeagueScreen` match cards don't flash — they're re-rendered fresh on each load.

Flash CSS:
```css
MatchCard.--flashing {
    border: tall $success;
    background: $success 10%;
}
MatchCard.--flashing .score {
    color: $success;
    text-style: bold;
}
```

---

## Feature 3 — Toast + "Updated X ago" Counter

### Toast on manual refresh

In `DashboardScreen.action_refresh()`, after `_load_all()` completes, call:

```python
updated = sum(1 for sb in self._scoreboards.values() if sb)
self.app.notify(f"Scores refreshed · {updated} leagues updated", timeout=4)
```

Textual's built-in `notify()` renders a toast in the bottom-right corner automatically. No extra widget needed.

### "Updated X ago" counter

`DashboardScreen` tracks `self._last_refresh: datetime` set at the end of each `_load_all()` call.

A `Static` widget with id `#refresh-ts` is added to the `Footer` area (or as a right-aligned overlay above the footer). A `set_interval(10, self._update_ts)` timer updates its text:

```python
def _update_ts(self) -> None:
    if self._last_refresh is None:
        return
    delta = int((datetime.now() - self._last_refresh).total_seconds())
    if delta < 60:
        label = f"↺ Updated {delta}s ago"
    else:
        label = f"↺ Updated {delta // 60}m ago"
    self.query_one("#refresh-ts", Static).update(label)
```

The label is styled `color: $success dim` so it's visible but doesn't compete with footer keybindings.

---

## Error Handling

- Flash detection is defensive: if old scoreboard is missing or malformed, skip silently — no flash is better than a crash.
- Toast only fires on `action_refresh()` (manual `r` key), not on the 60s background auto-refresh (to avoid noise).
- The pulse timer is cancelled in `MatchCard.on_unmount()` to prevent timer leaks when cards are removed and re-mounted.

---

## Out of Scope

- Rounds 2 and 3 (navigation, search/filter, sparklines) — separate specs
- Form sparkline (W/D/L) — Round 3
- LeagueScreen score flash (only dashboard tracks previous scoreboard state)
