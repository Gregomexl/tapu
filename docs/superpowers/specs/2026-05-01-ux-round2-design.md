# UX Round 2 — Navigation

**Date:** 2026-05-01
**Scope:** Keyboard navigation improvements — no new data fetching, no new screens beyond two modals

## Summary

Three features that make the app feel keyboard-native:

1. **Command Palette (`g`)** — jump to any league from any screen
2. **Help Overlay (`?`)** — show all bindings for the current screen
3. **Tab & card navigation (`←`/`→`, `↑`/`↓`)** — arrow keys drive tabs and match cards in LeagueScreen

---

## Feature 1 — Command Palette (`g`)

### Behaviour

Press `g` from any screen (Dashboard, LeagueScreen, MatchScreen) to open a `LeaguePaletteScreen` modal. The modal shows all leagues from the app's config as a filterable list.

- Typing narrows the list by league name (case-insensitive substring match)
- `↑`/`↓` move focus through results
- `Enter` dismisses the modal and pushes `LeagueScreen` for the selected league; if the user is already in a `LeagueScreen` it is replaced (popped then pushed) so the stack doesn't grow unboundedly
- `Esc` dismisses without navigating

### Implementation

`g` is an App-level binding on `TapuApp` so it is active on every screen without repeating the binding on each screen class.

`LeaguePaletteScreen` is a `ModalScreen` with:
- An `Input` widget at the top for the filter query
- An `OptionList` (or `ListView`) below showing matching `League` objects
- `on_input_changed` → refilter and repopulate the list
- `on_option_list_option_selected` → pop self, then push `LeagueScreen`

The modal needs access to the full league list and the ESPN client. Both are available on `self.app` (`TapuApp` stores `self.leagues: list[League]` and `self.client: ESPNClient`).

### Palette CSS

```
LeaguePaletteScreen {
    align: center middle;
}
#palette-container {
    width: 60;
    height: auto;
    max-height: 80%;
    border: solid $primary;
    background: $surface;
    padding: 1;
}
```

---

## Feature 2 — Help Overlay (`?`)

### Behaviour

Press `?` from any screen to open a `HelpScreen` modal showing a two-column table of key bindings (Key | Description) for the active screen. `Esc` or `?` closes it.

### Implementation

`?` replaces the existing `app.open_chat` App-level action. `HelpScreen` is a `ModalScreen` that:

1. Receives the active screen's `BINDINGS` list as a constructor argument (passed by the App before pushing)
2. Renders a `Static` with a Rich `Table` — one row per binding where `show=True` (visible bindings only in the rendered table, but all bindings including `show=False` listed under a "hidden shortcuts" section in dimmed text)
3. The table is wrapped in a scrollable container in case the binding list is long

`ChatScreen` (`src/tapu/screens/chat.py`) is deleted — it was a v2 placeholder with no real functionality. All per-screen `Binding("?", "app.open_chat", ...)` entries are removed from `DashboardScreen`, `LeagueScreen`, and `MatchScreen` since the binding is now global on `TapuApp`.

### Help CSS

```
HelpScreen {
    align: center middle;
}
#help-container {
    width: 70;
    height: auto;
    max-height: 80%;
    border: solid $primary;
    background: $surface;
    padding: 1 2;
}
```

---

## Feature 3 — Tab & Card Navigation

### Tab switching (`←` / `→`)

Two bindings added to `LeagueScreen`:

| Key | Action | Description |
|---|---|---|
| `←` | `prev_tab` | Activate previous tab (wraps to last) |
| `→` | `next_tab` | Activate next tab (wraps to first) |

Implementation:
```python
def action_next_tab(self) -> None:
    tc = self.query_one(TabbedContent)
    pane_ids = [p.id for p in tc.query(TabPane)]
    idx = pane_ids.index(tc.active) if tc.active in pane_ids else 0
    tc.active = pane_ids[(idx + 1) % len(pane_ids)]

def action_prev_tab(self) -> None:
    tc = self.query_one(TabbedContent)
    pane_ids = [p.id for p in tc.query(TabPane)]
    idx = pane_ids.index(tc.active) if tc.active in pane_ids else 0
    tc.active = pane_ids[(idx - 1) % len(pane_ids)]
```

These bindings are scoped to `LeagueScreen` and do not conflict with `DashboardScreen` where `←`/`→` already navigate the card grid.

Both bindings are shown in the `LeagueScreen` footer (`show=True`) so users discover them.

### Card navigation (`↑` / `↓`)

`MatchCard` already has `↑`/`↓` bindings that call `screen.focus_previous()` / `screen.focus_next()`. No change needed.

---

## Error Handling

- **Palette with empty query** — shows full league list (no filter applied)
- **Palette navigation from MatchScreen** — the stack becomes `Dashboard → LeagueScreen`; `MatchScreen` is popped before the new `LeagueScreen` is pushed so back navigation remains sensible. Concretely: `self.app.pop_screen()` until no `LeagueScreen` or `MatchScreen` is on the stack, then `push_screen(LeagueScreen(...))`.
- **Help overlay with no bindings** — renders an empty table with a "No bindings defined" message
- **Tab cycling with one tab** — wrapping `% 1` is a no-op; no crash

---

## Files Changed

| File | Change |
|---|---|
| `src/tapu/app.py` | Add global `g` → `action_open_palette`; change `?` → `action_open_help`; remove `ChatScreen` import |
| `src/tapu/screens/league_palette.py` | New — `LeaguePaletteScreen` modal |
| `src/tapu/screens/help.py` | New — `HelpScreen` modal |
| `src/tapu/screens/league.py` | Add `←`/`→` bindings and `action_next_tab` / `action_prev_tab`; remove per-screen `?` binding |
| `src/tapu/screens/dashboard.py` | Remove per-screen `?` binding |
| `src/tapu/screens/match.py` | Remove per-screen `?` binding |
| `src/tapu/screens/chat.py` | Delete file |
| `tests/test_palette.py` | New — unit tests for palette filtering logic |

---

## Out of Scope

- Round 3: search/filter within matches, form sparklines (W/D/L)
- Standings interactivity (sort/filter)
- Scroll position persistence across tab switches
- Mouse click support on palette items (Textual handles this by default via OptionList)
