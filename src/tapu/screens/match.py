from typing import Any, ClassVar
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import Footer, Header, Static

from tapu.api import ESPNClient
from tapu.config import League
from tapu.widgets.match_detail import MatchDetail


class MatchScreen(Screen):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("b", "app.pop_screen", "Back", show=False),
        Binding("r", "refresh", "Refresh"),
        Binding("?", "app.open_chat", "Chat"),
    ]

    DEFAULT_CSS = """
    MatchScreen > VerticalScroll {
        background: $surface;
    }
    MatchScreen .loading {
        padding: 2;
        color: $text-muted;
    }
    """

    def __init__(
        self,
        client: ESPNClient,
        league: League,
        event_id: str,
        event: dict[str, Any],
    ) -> None:
        super().__init__()
        self.client = client
        self.league = league
        self.event_id = event_id
        self.event = event
        self._is_live = event["status"]["type"].get("state") == "in"
        self._refresh_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(
            Static("[dim]Loading match details...[/dim]", classes="loading"),
            id="detail-scroll",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = self.event.get("name", "Match")
        self.run_worker(self._load_summary(), exclusive=True)
        if self._is_live:
            self._refresh_timer = self.set_interval(30, self._auto_refresh)

    async def _load_summary(self) -> None:
        scroll = self.query_one("#detail-scroll", VerticalScroll)
        scroll.remove_children()
        try:
            summary = await self.client.get_match_summary(
                self.league.slug, self.event_id
            )
            await scroll.mount(MatchDetail(self.event, summary))
        except Exception:
            await scroll.mount(
                Static("[red]Match details unavailable[/red]", classes="loading")
            )

    async def _auto_refresh(self) -> None:
        try:
            scoreboard = await self.client.get_scoreboard(self.league.slug)
            events = scoreboard.get("events", [])
            updated = next(
                (e for e in events if e["id"] == self.event_id), None
            )
            if updated:
                self.event = updated
                self._is_live = updated["status"]["type"].get("state") == "in"
                if not self._is_live and self._refresh_timer:
                    self._refresh_timer.stop()
            await self._load_summary()
        except Exception:
            pass

    def action_refresh(self) -> None:
        self.client.clear_cache()
        self.run_worker(self._load_summary(), exclusive=True)
