from typing import Any

from rich.text import Text
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import DataTable, Label, Static


def _stat(stats: list[dict], name: str) -> str:
    for s in stats:
        if s["name"] == name:
            return s.get("displayValue") or str(s.get("value", "0"))
    return "-"


def _form_dots(form_str: str) -> str:
    colors = {"W": "green", "D": "yellow", "L": "red"}
    parts = []
    for ch in form_str.upper():
        color = colors.get(ch)
        if color:
            parts.append(f"[{color}]●[/{color}]")
    return " ".join(parts)


def _note_color(desc: str) -> str | None:
    """Map a note description to the same color used by _row_style."""
    d = desc.lower()
    if "relegat" in d or "eliminat" in d:
        return "red"
    if "champion" in d or "advance" in d or "round of" in d:
        return "cyan"
    if "europa" in d or "sudamericana" in d:
        return "green"
    if "conference" in d or "best" in d:
        return "yellow"
    return None


def _legend_items(entries: list[dict]) -> list[tuple[str, str]]:
    """Return (label, color) for each distinct competition zone in this table.

    Labels are taken directly from the ESPN API description so they accurately
    reflect the context — e.g. 'Advance to Knockout Phase' in a tournament
    rather than a hardcoded 'Champions League' label.
    """
    # First description seen per color wins as the legend label
    seen: dict[str, str] = {}
    for entry in entries:
        note = entry.get("note")
        if not note:
            continue
        desc = note.get("description", "").strip()
        if not desc:
            continue
        color = _note_color(desc)
        if color and color not in seen:
            seen[color] = desc
    # Return in a stable order matching visual importance
    result = []
    for color in ("cyan", "green", "yellow", "red"):
        if color in seen:
            result.append((seen[color], color))
    return result


def _row_style(
    rank: int,
    total: int,
    note: dict | None,
    relegation_spots: int,
    promotion_spots: int,
) -> str | None:
    """Return a Rich style string for this row, or None for default."""
    if note:
        desc = note.get("description", "").lower()
        if "relegat" in desc or "eliminat" in desc:
            return "bold red"
        if "champion" in desc or "advance" in desc or "round of" in desc:
            return "bold cyan"
        if "europa" in desc or "sudamericana" in desc:
            return "bold green"
        if "conference" in desc or "best" in desc:
            return "bold yellow"
        # Generic competition zone (liguilla, promotion, etc.)
        return "bold green"
    # Static fallback
    if relegation_spots > 0 and rank > total - relegation_spots:
        return "bold red"
    if promotion_spots > 0 and rank <= promotion_spots:
        return "bold green"
    return None


def _fill_table(
    table: DataTable,
    entries: list[dict],
    relegation_spots: int = 0,
    promotion_spots: int = 0,
) -> None:
    has_form = any(
        _stat(e.get("stats", []), "form") not in ("", "-")
        for e in entries
    )

    if has_form:
        table.add_columns("#", "Team", "P", "W", "D", "L", "GD", "Pts", "Form")
    else:
        table.add_columns("#", "Team", "P", "W", "D", "L", "GD", "Pts")

    def _rank(e: dict) -> int:
        for s in e.get("stats", []):
            if s["name"] == "rank":
                return int(s.get("value", 999))
        return 999

    entries = sorted(entries, key=_rank)
    total = len(entries)
    for i, entry in enumerate(entries, 1):
        stats = {s["name"]: s for s in entry.get("stats", [])}
        rank = int(stats.get("rank", {}).get("value", i))
        team = entry["team"].get("shortDisplayName") or entry["team"]["abbreviation"]
        note = entry.get("note")
        style = _row_style(rank, total, note, relegation_spots, promotion_spots)

        def cell(s: str, st: str | None = style) -> Text:
            t = Text(s, justify="right")
            if st:
                t.stylize(st)
            return t

        row = [
            cell(str(rank)),
            cell(team),
            cell(_stat(entry.get("stats", []), "gamesPlayed")),
            cell(_stat(entry.get("stats", []), "wins")),
            cell(_stat(entry.get("stats", []), "ties")),
            cell(_stat(entry.get("stats", []), "losses")),
            cell(_stat(entry.get("stats", []), "pointDifferential")),
            cell(_stat(entry.get("stats", []), "points")),
        ]
        if has_form:
            form_str = _stat(entry.get("stats", []), "form")
            form_val = Text.from_markup(_form_dots(form_str)) if form_str not in ("", "-") else Text("")
            row.append(form_val)
        table.add_row(*row)


class StandingsTable(Widget):
    DEFAULT_CSS = """
    StandingsTable {
        height: auto;
    }
    StandingsTable .table-header {
        color: $text;
        text-style: bold;
        padding: 0 0 1 0;
    }
    StandingsTable .season-label {
        color: $text-muted;
        text-style: none;
    }
    StandingsTable DataTable {
        height: auto;
        max-height: 28;
        margin: 0 0 1 0;
    }
    StandingsTable Label {
        color: $primary;
        text-style: bold;
        padding: 1 0 0 0;
    }
    StandingsTable .legend {
        padding: 1 0 0 0;
        color: $text-muted;
    }
    """

    def __init__(
        self,
        data: dict[str, Any],
        relegation_spots: int = 0,
        promotion_spots: int = 0,
        league_name: str = "",
        season: str = "",
    ) -> None:
        super().__init__()
        self._data = data
        self._relegation_spots = relegation_spots
        self._promotion_spots = promotion_spots
        self._league_name = league_name
        self._season = season

    @property
    def row_count(self) -> int:
        return sum(t.row_count for t in self.query(DataTable))

    def _all_entries(self) -> list[dict]:
        children = self._data.get("children", [])
        if children:
            entries: list[dict] = []
            for child in children:
                entries.extend(child.get("standings", {}).get("entries", []))
            return entries
        return self._data.get("standings", {}).get("entries", [])

    def compose(self) -> ComposeResult:
        # Header: "LEAGUE TABLE  Season YYYY/YY"
        if self._league_name:
            season_part = f"  [dim]{self._season}[/dim]" if self._season else ""
            yield Static(
                f"[bold]{self._league_name.upper()} TABLE[/bold]{season_part}",
                classes="table-header",
            )

        children = self._data.get("children", [])
        if len(children) > 1:
            for child in children:
                group_name = child.get("name", "Group")
                entries = child.get("standings", {}).get("entries", [])
                if not entries:
                    continue
                yield Label(group_name)
                table = self._make_table()
                _fill_table(table, entries, self._relegation_spots, self._promotion_spots)
                yield table
        else:
            standings = children[0].get("standings", {}) if children else self._data.get("standings", {})
            entries = standings.get("entries", [])
            table = self._make_table()
            _fill_table(table, entries, self._relegation_spots, self._promotion_spots)
            yield table

        # Legend: only show zones present in the data
        legend = _legend_items(self._all_entries())
        if legend:
            parts = [f"[{color}]■[/{color}] {label}" for label, color in legend]
            yield Static("  ".join(parts), classes="legend")

    def _make_table(self) -> DataTable:
        table: DataTable = DataTable()
        table.zebra_stripes = True
        table.cursor_type = "row"
        table.show_cursor = False
        return table
