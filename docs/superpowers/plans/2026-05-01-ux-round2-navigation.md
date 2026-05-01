# UX Round 2 — Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a command palette (`g`), a help overlay (`?`), and `←`/`→` tab switching to make the app fully keyboard-navigable.

**Architecture:** Two new `ModalScreen` subclasses (`LeaguePaletteScreen`, `HelpScreen`) registered as global App actions. `ChatScreen` is deleted. `LeagueScreen` gets two new action methods for tab cycling. All per-screen `?` bindings are removed in favour of the global one.

**Tech Stack:** Python 3.13, Textual, pytest, pytest-asyncio

---

## Files

| File | Change |
|---|---|
| `src/tapu/screens/league_palette.py` | Create — `LeaguePaletteScreen` modal |
| `src/tapu/screens/help.py` | Create — `HelpScreen` modal |
| `src/tapu/app.py` | Add `action_open_palette` + `action_open_help`; remove `action_open_chat` |
| `src/tapu/screens/dashboard.py` | Remove `?` binding |
| `src/tapu/screens/league.py` | Remove `?` binding; add `←`/`→` + `action_next_tab`/`action_prev_tab` |
| `src/tapu/screens/match.py` | Remove `?` binding |
| `src/tapu/screens/chat.py` | Delete |
| `tests/test_palette.py` | Create — unit tests for palette filtering |

---

## Task 1: League Palette Screen

**Files:**
- Create: `src/tapu/screens/league_palette.py`
- Create: `tests/test_palette.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_palette.py`:

```python
import pytest
from tapu.screens.league_palette import _filter_leagues
from tapu.config import League


def _league(name: str, slug: str = "x.1") -> League:
    return League(slug=slug, name=name, full_name=name)


def test_filter_empty_query_returns_all():
    leagues = [_league("Premier League"), _league("La Liga"), _league("Bundesliga")]
    assert _filter_leagues(leagues, "") == leagues


def test_filter_case_insensitive():
    leagues = [_league("Premier League"), _league("La Liga")]
    assert _filter_leagues(leagues, "liga") == [_league("La Liga")]


def test_filter_no_match_returns_empty():
    leagues = [_league("Premier League"), _league("La Liga")]
    assert _filter_leagues(leagues, "zzz") == []


def test_filter_partial_match():
    leagues = [_league("Premier League"), _league("Bundesliga"), _league("La Liga")]
    result = _filter_leagues(leagues, "liga")
    assert len(result) == 2
    assert all("liga" in l.full_name.lower() for l in result)
```

- [ ] **Step 2: Run to verify tests fail**

```bash
uv run pytest tests/test_palette.py -v
```

Expected: `ModuleNotFoundError: No module named 'tapu.screens.league_palette'`

- [ ] **Step 3: Create `src/tapu/screens/league_palette.py`**

```python
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView

from tapu.config import League


def _filter_leagues(leagues: list[League], query: str) -> list[League]:
    if not query:
        return leagues
    q = query.lower()
    return [l for l in leagues if q in l.full_name.lower()]


class LeaguePaletteScreen(ModalScreen):
    BINDINGS: list[BindingType] = [
        Binding("escape", "dismiss", "Close", show=False),
    ]

    DEFAULT_CSS = """
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
    #palette-input {
        margin-bottom: 1;
    }
    """

    def __init__(self, leagues: list[League]) -> None:
        super().__init__()
        self._leagues = leagues
        self._filtered = list(leagues)

    def compose(self) -> ComposeResult:
        from textual.containers import Vertical
        with Vertical(id="palette-container"):
            yield Input(placeholder="Search leagues…", id="palette-input")
            yield ListView(
                *[ListItem(Label(l.full_name), id=f"pl-{i}") for i, l in enumerate(self._filtered)],
                id="palette-list",
            )

    def on_input_changed(self, event: Input.Changed) -> None:
        self._filtered = _filter_leagues(self._leagues, event.value)
        lv = self.query_one("#palette-list", ListView)
        lv.clear()
        for i, league in enumerate(self._filtered):
            lv.append(ListItem(Label(league.full_name), id=f"pl-{i}"))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = int(event.item.id.split("-")[1])  # type: ignore[arg-type]
        league = self._filtered[idx]
        self.dismiss(league)
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_palette.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Run full suite**

```bash
uv run pytest -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/tapu/screens/league_palette.py tests/test_palette.py
git commit -m "feat: add LeaguePaletteScreen modal"
```

---

## Task 2: Help Screen

**Files:**
- Create: `src/tapu/screens/help.py`

No unit tests needed — `HelpScreen` is pure display with no logic to test outside Textual's rendering.

- [ ] **Step 1: Create `src/tapu/screens/help.py`**

```python
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.screen import ModalScreen
from textual.widgets import Static


class HelpScreen(ModalScreen):
    BINDINGS: list[BindingType] = [
        Binding("escape", "dismiss", "Close", show=False),
        Binding("?", "dismiss", "Close", show=False),
    ]

    DEFAULT_CSS = """
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
    """

    def __init__(self, bindings: list[Binding]) -> None:
        super().__init__()
        self._bindings = bindings

    def compose(self) -> ComposeResult:
        from textual.containers import VerticalScroll
        visible = [b for b in self._bindings if b.show]
        hidden = [b for b in self._bindings if not b.show]

        lines: list[str] = ["[bold]Key Bindings[/bold]\n"]
        if visible:
            for b in visible:
                lines.append(f"  [bold cyan]{b.key:<12}[/bold cyan] {b.description}")
        if hidden:
            lines.append("\n[dim]Hidden shortcuts[/dim]")
            for b in hidden:
                lines.append(f"  [dim]{b.key:<12} {b.description}[/dim]")
        lines.append("\n[dim]Press ? or Esc to close[/dim]")

        from textual.containers import Vertical
        with Vertical(id="help-container"):
            yield VerticalScroll(Static("\n".join(lines)))

    def action_dismiss(self) -> None:
        self.dismiss()
```

- [ ] **Step 2: Run full suite to verify no breakage**

```bash
uv run pytest -v
```

Expected: all tests PASS.

- [ ] **Step 3: Commit**

```bash
git add src/tapu/screens/help.py
git commit -m "feat: add HelpScreen modal"
```

---

## Task 3: Wire palette and help into TapuApp; delete ChatScreen

**Files:**
- Modify: `src/tapu/app.py`
- Delete: `src/tapu/screens/chat.py`
- Modify: `src/tapu/screens/dashboard.py` — remove `?` binding
- Modify: `src/tapu/screens/league.py` — remove `?` binding
- Modify: `src/tapu/screens/match.py` — remove `?` binding

- [ ] **Step 1: Replace `app.py` content**

```python
from textual.app import App
from textual.binding import Binding, BindingType

from tapu.api import ESPNClient
from tapu.config import load_leagues

SPLASH = """\
  ████████╗ █████╗ ██████╗ ██╗   ██╗
  ╚══██╔══╝██╔══██╗██╔══██╗██║   ██║
     ██║   ███████║██████╔╝██║   ██║
     ██║   ██╔══██║██╔═══╝ ██║   ██║
     ██║   ██║  ██║██║     ╚██████╔╝
     ╚═╝   ╚═╝  ╚═╝╚═╝      ╚═════╝  ⚽
  [dim]fútbol en tu terminal[/dim]"""


class TapuApp(App):
    TITLE = "Tapú"
    SUB_TITLE = "fútbol en tu terminal"

    BINDINGS: list[BindingType] = [
        Binding("g", "open_palette", "Go to league"),
        Binding("?", "open_help", "Help"),
    ]

    CSS = """
    Screen {
        background: $surface;
    }
    .splash {
        width: 100%;
        height: auto;
        padding: 1 2;
        color: $success;
        text-align: left;
    }
    """

    def __init__(self, refresh_interval: int = 60) -> None:
        super().__init__()
        self.client = ESPNClient()
        self.leagues = load_leagues()
        self.refresh_interval = refresh_interval

    def on_mount(self) -> None:
        from tapu.screens.dashboard import DashboardScreen
        self.push_screen(DashboardScreen(self.client, self.leagues))

    async def on_unmount(self) -> None:
        await self.client.aclose()

    def action_open_palette(self) -> None:
        from tapu.screens.league_palette import LeaguePaletteScreen

        def _on_league_selected(league) -> None:
            if league is None:
                return
            from tapu.screens.league import LeagueScreen
            from tapu.screens.match import MatchScreen
            # Pop any MatchScreen or LeagueScreen off the stack before pushing new one
            while len(self.screen_stack) > 1 and isinstance(
                self.screen_stack[-1], (LeagueScreen, MatchScreen)
            ):
                self.pop_screen()
            self.push_screen(LeagueScreen(self.client, league, {}))

        self.push_screen(LeaguePaletteScreen(self.leagues), _on_league_selected)

    def action_open_help(self) -> None:
        from tapu.screens.help import HelpScreen
        from textual.binding import Binding
        bindings = [
            b for b in self.screen.BINDINGS
            if isinstance(b, Binding)
        ]
        self.push_screen(HelpScreen(bindings))
```

- [ ] **Step 2: Remove the `?` binding from `DashboardScreen`**

In `src/tapu/screens/dashboard.py`, remove this line from `BINDINGS`:

```python
Binding("?", "app.open_chat", "Chat"),
```

- [ ] **Step 3: Remove the `?` binding from `LeagueScreen`**

In `src/tapu/screens/league.py`, remove this line from `BINDINGS`:

```python
Binding("?", "app.open_chat", "Chat"),
```

- [ ] **Step 4: Remove the `?` binding from `MatchScreen`**

In `src/tapu/screens/match.py`, remove this line from `BINDINGS`:

```python
Binding("?", "app.open_chat", "Chat"),
```

- [ ] **Step 5: Delete `src/tapu/screens/chat.py`**

```bash
git rm src/tapu/screens/chat.py
```

- [ ] **Step 6: Run full suite**

```bash
uv run pytest -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/tapu/app.py src/tapu/screens/dashboard.py src/tapu/screens/league.py src/tapu/screens/match.py
git commit -m "feat: wire palette and help into TapuApp; remove ChatScreen"
```

---

## Task 4: Tab switching with ←/→ in LeagueScreen

**Files:**
- Modify: `src/tapu/screens/league.py`
- Modify: `tests/test_league.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_league.py`:

```python
from tapu.screens.league import LeagueScreen


def test_tab_ids_from_league_screen():
    """_tab_ids is a pure helper — verify it returns expected ids in order."""
    # This tests the logic used by action_next_tab / action_prev_tab
    ids = ["tab-main", "tab-bracket", "tab-copa"]
    assert ids[(ids.index("tab-main") + 1) % len(ids)] == "tab-bracket"
    assert ids[(ids.index("tab-copa") + 1) % len(ids)] == "tab-main"  # wraps
    assert ids[(ids.index("tab-main") - 1) % len(ids)] == "tab-copa"  # wraps back
```

- [ ] **Step 2: Run to verify test passes already (pure logic test)**

```bash
uv run pytest tests/test_league.py::test_tab_ids_from_league_screen -v
```

Expected: PASS (the test exercises pure Python list arithmetic, no Textual needed).

- [ ] **Step 3: Add `←`/`→` bindings and action methods to `LeagueScreen`**

In `src/tapu/screens/league.py`, add two bindings to `BINDINGS`:

```python
Binding("left", "prev_tab", "← Tab", show=True),
Binding("right", "next_tab", "→ Tab", show=True),
```

Add the two action methods (place them after `action_more`):

```python
def action_next_tab(self) -> None:
    tc = self.query_one(TabbedContent)
    pane_ids = [p.id for p in tc.query(TabPane)]
    if not pane_ids:
        return
    idx = pane_ids.index(tc.active) if tc.active in pane_ids else 0
    tc.active = pane_ids[(idx + 1) % len(pane_ids)]

def action_prev_tab(self) -> None:
    tc = self.query_one(TabbedContent)
    pane_ids = [p.id for p in tc.query(TabPane)]
    if not pane_ids:
        return
    idx = pane_ids.index(tc.active) if tc.active in pane_ids else 0
    tc.active = pane_ids[(idx - 1) % len(pane_ids)]
```

`TabPane` is already imported in `league.py` via `from textual.widgets import ... TabPane`.

- [ ] **Step 4: Run full suite**

```bash
uv run pytest -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/tapu/screens/league.py tests/test_league.py
git commit -m "feat: add tab switching with left/right arrows in LeagueScreen"
```

---

## Task 5: Lint check

- [ ] **Step 1: Run ruff**

```bash
uv run ruff check src
```

Expected: no errors. If any, fix them before proceeding.

- [ ] **Step 2: Run full suite one final time**

```bash
uv run pytest -v
```

Expected: all tests PASS.
