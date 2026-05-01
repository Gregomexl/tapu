import pytest
from textual.app import App, ComposeResult

from tapu.widgets.standings import StandingsTable, _form_dots, _legend_items


def _entry_with_note(desc: str) -> dict:
    return {"team": {"abbreviation": "TST"}, "stats": [], "note": {"description": desc}}


def test_legend_uses_actual_api_description():
    entries = [_entry_with_note("UEFA Champions League")]
    items = _legend_items(entries)
    assert items == [("UEFA Champions League", "cyan")]


def test_legend_advance_in_tournament_shows_advance_label_not_champions():
    entries = [_entry_with_note("Advance to Knockout Phase")]
    items = _legend_items(entries)
    # In a tournament context, "advance" should show the actual description
    assert items == [("Advance to Knockout Phase", "cyan")]


def test_legend_multiple_zones_ordered_by_color():
    entries = [
        _entry_with_note("UEFA Champions League"),
        _entry_with_note("Relegated"),
        _entry_with_note("UEFA Europa League"),
    ]
    items = _legend_items(entries)
    labels = [label for label, _ in items]
    # cyan before green before red
    assert labels.index("UEFA Champions League") < labels.index("UEFA Europa League")
    assert labels.index("UEFA Europa League") < labels.index("Relegated")


def test_legend_empty_when_no_notes():
    entries = [{"team": {"abbreviation": "TST"}, "stats": []}]
    assert _legend_items(entries) == []


def test_legend_deduplicates_same_color():
    # Multiple "advance" entries should produce only one cyan legend item
    entries = [
        _entry_with_note("Advance to Round of 16"),
        _entry_with_note("Advance to Knockout Phase"),
    ]
    items = _legend_items(entries)
    cyan_items = [item for item in items if item[1] == "cyan"]
    assert len(cyan_items) == 1


def _standings_data(with_form: bool) -> dict:
    def _entry(rank: int, team: str, form: str | None = None) -> dict:
        stats = [
            {"name": "rank", "value": rank, "displayValue": str(rank)},
            {"name": "gamesPlayed", "value": 10, "displayValue": "10"},
            {"name": "wins", "value": 7, "displayValue": "7"},
            {"name": "ties", "value": 2, "displayValue": "2"},
            {"name": "losses", "value": 1, "displayValue": "1"},
            {"name": "pointDifferential", "value": 15, "displayValue": "+15"},
            {"name": "points", "value": 23, "displayValue": "23"},
        ]
        if form is not None:
            stats.append({"name": "form", "value": 0, "displayValue": form})
        return {"team": {"shortDisplayName": team, "abbreviation": team[:3]}, "stats": stats}

    entries = [
        _entry(1, "Real Madrid", "WWDWW" if with_form else None),
        _entry(2, "Barcelona", "LWWDW" if with_form else None),
    ]
    return {"standings": {"entries": entries}}


class _StandingsFormApp(App):
    def __init__(self, data: dict) -> None:
        super().__init__()
        self._data = data

    def compose(self) -> ComposeResult:
        yield StandingsTable(self._data)


@pytest.mark.asyncio
async def test_fill_table_adds_form_column_when_data_present():
    async with _StandingsFormApp(_standings_data(with_form=True)).run_test() as pilot:
        from textual.widgets import DataTable
        table = pilot.app.query_one(DataTable)
        col_labels = [str(col.label) for col in table.columns.values()]
        assert "Form" in col_labels


@pytest.mark.asyncio
async def test_fill_table_omits_form_column_when_no_data():
    async with _StandingsFormApp(_standings_data(with_form=False)).run_test() as pilot:
        from textual.widgets import DataTable
        table = pilot.app.query_one(DataTable)
        col_labels = [str(col.label) for col in table.columns.values()]
        assert "Form" not in col_labels


def test_form_dots_all_results():
    result = _form_dots("WWDLW")
    assert "[green]●[/green]" in result
    assert "[yellow]●[/yellow]" in result
    assert "[red]●[/red]" in result


def test_form_dots_empty_string():
    assert _form_dots("") == ""


def test_form_dots_unknown_chars_skipped():
    result = _form_dots("WXW")
    assert result.count("[green]●[/green]") == 2
    assert "X" not in result


def test_form_dots_lowercase():
    result = _form_dots("wdl")
    assert "[green]●[/green]" in result
    assert "[yellow]●[/yellow]" in result
    assert "[red]●[/red]" in result


def test_form_dots_five_dots_joined_by_spaces():
    result = _form_dots("WWWWW")
    parts = result.split(" ")
    assert len(parts) == 5
