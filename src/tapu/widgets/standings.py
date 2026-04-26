from typing import Any
from textual.widgets import DataTable


def _stat(stats: list[dict], name: str) -> str:
    for s in stats:
        if s["name"] == name:
            return s.get("displayValue") or str(s.get("value", "0"))
    return "-"


class StandingsTable(DataTable):
    DEFAULT_CSS = """
    StandingsTable {
        height: auto;
        max-height: 20;
    }
    """

    def __init__(self, data: dict[str, Any]) -> None:
        super().__init__()
        self._data = data

    def on_mount(self) -> None:
        self.add_columns("#", "Team", "P", "W", "D", "L", "GD", "Pts")
        children = self._data.get("children", [])
        standings = children[0].get("standings", {}) if children else self._data.get("standings", {})
        entries = standings.get("entries", [])
        for i, entry in enumerate(entries, 1):
            team = entry["team"]["abbreviation"]
            stats = entry["stats"]
            self.add_row(
                str(i),
                team,
                _stat(stats, "gamesPlayed"),
                _stat(stats, "wins"),
                _stat(stats, "ties"),
                _stat(stats, "losses"),
                _stat(stats, "pointDifferential"),
                _stat(stats, "points"),
            )
