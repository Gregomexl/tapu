from typing import Any

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import DataTable, Label


def _stat(stats: list[dict], name: str) -> str:
    for s in stats:
        if s["name"] == name:
            return s.get("displayValue") or str(s.get("value", "0"))
    return "-"


def _fill_table(table: DataTable, entries: list[dict]) -> None:
    table.add_columns("#", "Team", "P", "W", "D", "L", "GD", "Pts")
    for i, entry in enumerate(entries, 1):
        team = entry["team"]["abbreviation"]
        stats = entry.get("stats", [])
        table.add_row(
            str(i),
            team,
            _stat(stats, "gamesPlayed"),
            _stat(stats, "wins"),
            _stat(stats, "ties"),
            _stat(stats, "losses"),
            _stat(stats, "pointDifferential"),
            _stat(stats, "points"),
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

    def __init__(self, data: dict[str, Any]) -> None:
        super().__init__()
        self._data = data

    def compose(self) -> ComposeResult:
        children = self._data.get("children", [])
        if len(children) > 1:
            # multi-group (e.g. World Cup)
            for child in children:
                group_name = child.get("name", "Group")
                entries = child.get("standings", {}).get("entries", [])
                if not entries:
                    continue
                yield Label(group_name)
                table = DataTable()
                _fill_table(table, entries)
                yield table
        else:
            # single table (regular league)
            standings = children[0].get("standings", {}) if children else self._data.get("standings", {})
            entries = standings.get("entries", [])
            table = DataTable()
            _fill_table(table, entries)
            yield table
