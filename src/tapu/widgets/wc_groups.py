from typing import Any

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import ItemGrid
from textual.message import Message
from textual.widget import Widget
from textual.widgets import DataTable, Label


def _stat(stats: list[dict], name: str) -> str:
    for s in stats:
        if s["name"] == name:
            return s.get("displayValue") or str(s.get("value", "0"))
    return "-"


def _note_style(note: dict | None) -> str:
    if not note:
        return ""
    desc = note.get("description", "").lower()
    if "eliminat" in desc:
        return "dim"
    if "advance" in desc or "champion" in desc:
        return "bold cyan"
    if "best" in desc:
        return "bold yellow"
    return "bold green"


def _rank_val(entry: dict) -> int:
    for s in entry.get("stats", []):
        if s["name"] == "rank":
            return int(s.get("value", 999))
    return 999


class GroupCard(Widget):
    """Selectable group card showing a mini standings table."""

    can_focus = True
    BINDINGS = [
        Binding("enter", "select", "Open Group", show=False),
        Binding("up", "focus_previous", "", show=False),
        Binding("left", "focus_previous", "", show=False),
        Binding("down", "focus_next", "", show=False),
        Binding("right", "focus_next", "", show=False),
    ]

    DEFAULT_CSS = """
    GroupCard {
        height: auto;
        padding: 0 0 1 0;
    }
    GroupCard:focus {
        border-left: thick $accent;
        background: $surface-lighten-1;
    }
    GroupCard:hover {
        background: $surface-lighten-1;
    }
    GroupCard Label {
        color: $primary;
        text-style: bold;
        padding: 0 0 0 1;
    }
    GroupCard DataTable {
        height: auto;
    }
    """

    class Selected(Message):
        def __init__(self, group_name: str, child_data: dict) -> None:
            super().__init__()
            self.group_name = group_name
            self.child_data = child_data

    def __init__(self, child: dict) -> None:
        super().__init__()
        self._child = child
        self._group_name = child.get("name", "Group")

    def compose(self) -> ComposeResult:
        yield Label(self._group_name)
        table: DataTable = DataTable()
        table.zebra_stripes = True
        table.cursor_type = "row"
        table.show_cursor = False
        table.add_columns("#", "Team", "P", "W", "D", "L", "GD", "Pts")

        entries = sorted(
            self._child.get("standings", {}).get("entries", []),
            key=_rank_val,
        )
        for entry in entries:
            team = entry["team"].get("shortDisplayName") or entry["team"]["abbreviation"]
            stats = entry.get("stats", [])
            note = entry.get("note")
            style = _note_style(note)
            rank = _rank_val(entry)
            rank_str = str(rank) if rank < 999 else "-"

            gd_raw = _stat(stats, "pointDifferential")
            try:
                gd = f"{int(float(gd_raw)):+d}"
            except (ValueError, TypeError):
                gd = gd_raw

            def cell(s: str, st: str | None = style) -> Text:
                t = Text(s, justify="right")
                if st:
                    t.stylize(st)
                return t

            table.add_row(
                cell(rank_str),
                cell(team),
                cell(_stat(stats, "gamesPlayed")),
                cell(_stat(stats, "wins")),
                cell(_stat(stats, "ties")),
                cell(_stat(stats, "losses")),
                cell(gd),
                cell(_stat(stats, "points")),
            )
        yield table

    def on_click(self) -> None:
        self.post_message(self.Selected(self._group_name, self._child))

    def on_key(self, event) -> None:
        if event.key == "enter":
            self.post_message(self.Selected(self._group_name, self._child))
            event.prevent_default()


class WCGroupsWidget(Widget):
    DEFAULT_CSS = """
    WCGroupsWidget {
        height: auto;
        width: 100%;
    }
    WCGroupsWidget ItemGrid {
        height: auto;
        padding: 1 0;
    }
    """

    def __init__(self, data: dict[str, Any]) -> None:
        super().__init__()
        self._data = data

    def compose(self) -> ComposeResult:
        with ItemGrid(min_column_width=52, stretch_height=False):
            for child in self._data.get("children", []):
                yield GroupCard(child)
