from typing import Any

from rich.text import Text
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import DataTable, Label


def _stat(stats: list[dict], name: str) -> str:
    for s in stats:
        if s["name"] == name:
            return s.get("displayValue") or str(s.get("value", "0"))
    return "-"


def _fill_table(table: DataTable, entries: list[dict], relegation_spots: int = 0) -> None:
    table.add_columns("#", "Team", "P", "W", "D", "L", "GD", "Pts")
    total = len(entries)
    for i, entry in enumerate(entries, 1):
        team = entry["team"].get("shortDisplayName") or entry["team"]["abbreviation"]
        stats = entry.get("stats", [])
        relegated = relegation_spots > 0 and i > total - relegation_spots

        def cell(s: str, r: bool = relegated) -> Text:
            t = Text(s)
            if r:
                t.stylize("bold red")
            return t

        table.add_row(
            cell(str(i)),
            cell(team),
            cell(_stat(stats, "gamesPlayed")),
            cell(_stat(stats, "wins")),
            cell(_stat(stats, "ties")),
            cell(_stat(stats, "losses")),
            cell(_stat(stats, "pointDifferential")),
            cell(_stat(stats, "points")),
        )


class StandingsTable(Widget):
    DEFAULT_CSS = """
    StandingsTable {
        height: auto;
    }
    StandingsTable DataTable {
        height: auto;
        max-height: 24;
        margin: 0 0 1 0;
    }
    StandingsTable Label {
        color: $primary;
        text-style: bold;
        padding: 1 0 0 0;
    }
    """

    def __init__(self, data: dict[str, Any], relegation_spots: int = 0) -> None:
        super().__init__()
        self._data = data
        self._relegation_spots = relegation_spots

    def compose(self) -> ComposeResult:
        children = self._data.get("children", [])
        if len(children) > 1:
            for child in children:
                group_name = child.get("name", "Group")
                entries = child.get("standings", {}).get("entries", [])
                if not entries:
                    continue
                yield Label(group_name)
                table = DataTable()
                _fill_table(table, entries, self._relegation_spots)
                yield table
        else:
            standings = children[0].get("standings", {}) if children else self._data.get("standings", {})
            entries = standings.get("entries", [])
            table = DataTable()
            _fill_table(table, entries, self._relegation_spots)
            yield table
