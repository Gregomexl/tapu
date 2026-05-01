from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView

from tapu.config import League


def _filter_leagues(leagues: list[League], query: str) -> list[League]:
    if not query:
        return leagues
    q = query.lower()
    return [league for league in leagues if q in league.full_name.lower()]


class LeaguePaletteScreen(ModalScreen):
    BINDINGS: ClassVar[list[BindingType]] = [
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
        with Vertical(id="palette-container"):
            yield Input(placeholder="Search leagues…", id="palette-input")
            yield ListView(
                *[ListItem(Label(league.full_name), id=f"pl-{i}") for i, league in enumerate(self._filtered)],
                id="palette-list",
            )

    def on_input_changed(self, event: Input.Changed) -> None:
        self._filtered = _filter_leagues(self._leagues, event.value)
        lv = self.query_one("#palette-list", ListView)
        lv.clear()
        for i, league in enumerate(self._filtered):
            lv.append(ListItem(Label(league.full_name), id=f"pl-{i}"))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = int(event.item.id.split("-")[1])  # type: ignore[union-attr]
        league = self._filtered[idx]
        self.dismiss(league)

    def action_dismiss(self) -> None:
        self.dismiss(None)
