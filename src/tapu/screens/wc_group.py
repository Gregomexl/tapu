from typing import ClassVar

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from tapu.api import ESPNClient
from tapu.config import League
from tapu.widgets.bracket import _event_round
from tapu.widgets.match_card import MatchCard
from tapu.widgets.standings import StandingsTable


class WCGroupScreen(Screen):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("b", "app.pop_screen", "Back", show=False),
        Binding("r", "refresh", "Refresh"),
        Binding("?", "app.open_chat", "Chat"),
        Binding("up", "app.focus_previous", "Prev", show=False),
        Binding("down", "app.focus_next", "Next", show=False),
    ]

    DEFAULT_CSS = """
    WCGroupScreen .main-row {
        height: 1fr;
    }
    WCGroupScreen .matches-col {
        width: 1fr;
        height: 1fr;
        padding: 1;
    }
    WCGroupScreen .standings-col {
        width: 44;
        height: 1fr;
        border-left: solid $surface-lighten-2;
        padding: 1 1 1 1;
    }
    WCGroupScreen .no-matches {
        padding: 2;
        color: $text-muted;
    }
    """

    def __init__(
        self,
        client: ESPNClient,
        league: League,
        group_name: str,
        child_data: dict,
    ) -> None:
        super().__init__()
        self.client = client
        self.league = league
        self._group_name = group_name
        self._child_data = child_data

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(classes="main-row"):
            yield VerticalScroll(
                Static("[dim]Loading...[/dim]", classes="no-matches"),
                id="group-matches",
                classes="matches-col",
            )
            yield VerticalScroll(id="group-standings", classes="standings-col")
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = f"{self.league.full_name} · {self._group_name}"
        self._load_group()

    @work(exit_on_error=False)
    async def _load_group(self) -> None:
        matches_pane = self.query_one("#group-matches", VerticalScroll)
        standings_pane = self.query_one("#group-standings", VerticalScroll)
        try:
            data = await self.client.get_tournament_events(self.league.slug)
            events = data.get("events", [])
            group_events = [ev for ev in events if _event_round(ev) == self._group_name]

            live = [e for e in group_events if e["status"]["type"].get("state") == "in"]
            pre = [e for e in group_events if e["status"]["type"].get("state") not in ("in", "post")]
            done = [e for e in group_events if e["status"]["type"].get("state") == "post"]

            await matches_pane.remove_children()
            if not group_events:
                await matches_pane.mount(Static("[dim]No matches[/dim]", classes="no-matches"))
            else:
                for ev in live + pre + done:
                    await matches_pane.mount(MatchCard(ev))

            await standings_pane.remove_children()
            await standings_pane.mount(StandingsTable({"children": [self._child_data]}, 0, 0))
        except Exception:
            await matches_pane.remove_children()
            await matches_pane.mount(Static("[red]Failed to load[/red]", classes="no-matches"))

    def action_refresh(self) -> None:
        self.client.clear_cache()
        self._load_group()

    def on_match_card_selected(self, message: MatchCard.Selected) -> None:
        from tapu.screens.match import MatchScreen
        self.app.push_screen(
            MatchScreen(self.client, self.league, message.event_id, message.event)
        )
