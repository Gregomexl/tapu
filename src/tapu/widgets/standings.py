from typing import Any
from textual.widgets import DataTable


def _stat(stats: list[dict], name: str) -> int:
    for s in stats:
        if s["name"] == name:
            return int(s["value"])
    return 0


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
        entries = self._data.get("standings", {}).get("entries", [])
        for i, entry in enumerate(entries, 1):
            team = entry["team"]["abbreviation"]
            stats = entry["stats"]
            self.add_row(
                str(i),
                team,
                str(_stat(stats, "gamesPlayed")),
                str(_stat(stats, "wins")),
                str(_stat(stats, "ties")),
                str(_stat(stats, "losses")),
                str(_stat(stats, "pointDifferential")),
                str(_stat(stats, "points")),
            )
