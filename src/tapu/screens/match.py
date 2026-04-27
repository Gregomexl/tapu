from typing import Any, ClassVar

from textual import work
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
        align: center top;
    }
    MatchScreen .loading {
        width: 80;
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
        self._last_fingerprint: str = ""
        self._positions: dict[str, int] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(
            Static("[dim]Loading match details...[/dim]", classes="loading"),
            id="detail-scroll",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = self.event.get("name", "Match")
        self.run_worker(self._load_fresh(), exclusive=False)
        if self._is_live:
            self._refresh_timer = self.set_interval(5, self._tick_refresh)

    def _tick_refresh(self) -> None:
        self._run_refresh()

    @work(exit_on_error=False)
    async def _run_refresh(self) -> None:
        try:
            scoreboard = await self.client.get_scoreboard(self.league.slug)
            updated = next(
                (e for e in scoreboard.get("events", []) if e["id"] == self.event_id), None
            )
            if updated:
                self.event = updated
                self._is_live = updated["status"]["type"].get("state") == "in"
                if not self._is_live and self._refresh_timer:
                    self._refresh_timer.stop()
            summary = await self.client.get_match_summary(self.league.slug, self.event_id)
            fp = self._fingerprint(self.event, summary)
            if fp != self._last_fingerprint:
                self._last_fingerprint = fp
                await self._load_summary(summary)
            else:
                self._update_clock_label()
        except Exception:
            pass

    async def _load_fresh(self) -> None:
        """Fetch current event state before first render so displayClock is accurate."""
        if self._is_live:
            try:
                scoreboard = await self.client.get_scoreboard(self.league.slug)
                updated = next(
                    (e for e in scoreboard.get("events", []) if e["id"] == self.event_id),
                    None,
                )
                if updated:
                    self.event = updated
            except Exception:
                pass
        await self._load_summary()

    async def _fetch_positions(self) -> dict[str, int]:
        """Build team_id → league position from standings (uses disk cache)."""
        try:
            standings = await self.client.get_standings(self.league.slug)
            positions: dict[str, int] = {}
            children = standings.get("children", [])
            for child in children:
                entries = child.get("standings", {}).get("entries", [])
                for i, entry in enumerate(entries, 1):
                    positions[str(entry["team"]["id"])] = i
            if not positions:
                entries = standings.get("standings", {}).get("entries", [])
                for i, entry in enumerate(entries, 1):
                    positions[str(entry["team"]["id"])] = i
            return positions
        except Exception:
            return {}

    async def _load_summary(self, summary: dict[str, Any] | None = None) -> None:
        scroll = self.query_one("#detail-scroll", VerticalScroll)
        scroll.remove_children()
        try:
            if summary is None:
                summary = await self.client.get_match_summary(
                    self.league.slug, self.event_id
                )
            if not self._positions:
                self._positions = await self._fetch_positions()
            await scroll.mount(MatchDetail(self.event, summary, client=self.client, positions=self._positions))
        except Exception:
            await scroll.mount(
                Static("[red]Match details unavailable[/red]", classes="loading")
            )

    def _fingerprint(self, event: dict[str, Any], summary: dict[str, Any]) -> str:
        competitors = event["competitions"][0]["competitors"]
        scores = tuple(c.get("score", "0") for c in competitors)
        return "|".join([
            event["status"]["type"].get("state", ""),
            str(scores),
            str(len(summary.get("commentary", []))),
            str(len(summary.get("keyEvents", []))),
        ])

    def _update_clock_label(self) -> None:
        try:
            state = self.event["status"]["type"].get("state", "")
            if state != "in":
                return
            display_clock = self.event["status"].get("displayClock", "")
            self.query_one("#status-clock", Static).update(
                f"[green]● LIVE {display_clock}'[/green]"
            )
        except Exception:
            pass

    def action_refresh(self) -> None:
        self.client.clear_cache()
        self._last_fingerprint = ""
        self.run_worker(self._load_fresh(), exclusive=False)
