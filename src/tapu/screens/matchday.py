import re
from datetime import date
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from tapu.api import ESPNClient
from tapu.config import League
from tapu.screens.league import _group_events_by_day
from tapu.widgets.match_card import MatchCard


def _extract_group(event: dict) -> str | None:
    """Extract group label from event notes (e.g., 'Group A')."""
    sources = list(event.get("notes", []))
    comp = event.get("competitions", [{}])[0]
    sources += comp.get("notes", [])
    for note in sources:
        headline = note.get("headline", "")
        m = re.search(r"Group\s+\w+", headline, re.IGNORECASE)
        if m:
            return m.group(0).title()
    return None


class MatchdayScreen(Screen):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("b", "app.pop_screen", "Back", show=False),
        Binding("r", "refresh", "Refresh"),
        Binding("?", "app.open_chat", "Chat"),
        Binding("up", "app.focus_previous", "Prev", show=False),
        Binding("down", "app.focus_next", "Next", show=False),
    ]

    DEFAULT_CSS = """
    MatchdayScreen > VerticalScroll {
        padding: 1;
        height: 1fr;
    }
    MatchdayScreen .loading {
        padding: 2;
        color: $text-muted;
    }
    MatchdayScreen .day-header {
        padding: 1 1 0 1;
        color: $text-muted;
        text-style: bold;
    }
    MatchdayScreen #group-filter {
        height: auto;
        padding: 1 1 0 1;
        background: $surface;
    }
    MatchdayScreen #group-filter Button {
        margin: 0 1 1 0;
        min-width: 10;
    }
    MatchdayScreen #group-filter Button.-active {
        background: $primary;
        color: $text;
    }
    """

    def __init__(
        self,
        client: ESPNClient,
        league: League,
        label: str,
        start_date: str,
        end_date: str,
    ) -> None:
        super().__init__()
        self.client = client
        self.league = league
        self._label = label
        self._start = start_date
        self._end = end_date
        self._active_group: str | None = None
        self._event_groups: dict[str, str | None] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(id="group-filter")
        yield VerticalScroll(
            Static("[dim]Loading...[/dim]", classes="loading"),
            id="scroll",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = f"{self.league.full_name} — {self._label}"
        self.query_one("#group-filter").display = False
        self.run_worker(self._load(), exclusive=True)

    async def _load(self) -> None:
        scroll = self.query_one("#scroll", VerticalScroll)
        await scroll.remove_children()
        self._active_group = None
        self._event_groups = {}
        try:
            sb = await self.client.get_scoreboard_daterange(
                self.league.slug, self._start, self._end
            )
            events = sb.get("events", [])
            if not events:
                await scroll.mount(
                    Static("[dim]No matches for this matchday[/dim]", classes="loading")
                )
                return

            self._event_groups = {e["id"]: _extract_group(e) for e in events}
            groups = sorted(set(g for g in self._event_groups.values() if g))

            if len(groups) > 1:
                await self._build_filter(groups)

            today = date.today()
            for day, day_evs in _group_events_by_day(events):
                if day == today:
                    label = f"[bold]Today · {day.strftime('%a %b %-d')}[/bold]"
                else:
                    label = day.strftime("%a %b %-d")
                await scroll.mount(Static(label, classes="day-header"))
                for ev in day_evs:
                    await scroll.mount(MatchCard(ev, self.client))

        except Exception:
            await scroll.mount(
                Static("[red]Failed to load matchday[/red]", classes="loading")
            )

    async def _build_filter(self, groups: list[str]) -> None:
        bar = self.query_one("#group-filter", Horizontal)
        await bar.remove_children()
        all_btn = Button("All", id="filter-all")
        all_btn.add_class("-active")
        await bar.mount(all_btn)
        for g in groups:
            await bar.mount(Button(g, id=f"filter-{g.replace(' ', '-')}"))
        bar.display = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if not btn_id.startswith("filter-"):
            return

        bar = self.query_one("#group-filter", Horizontal)
        for btn in bar.query(Button):
            btn.remove_class("-active")
        event.button.add_class("-active")

        if btn_id == "filter-all":
            self._active_group = None
        else:
            self._active_group = str(event.button.label)

        self._apply_filter()

    def _apply_filter(self) -> None:
        scroll = self.query_one("#scroll", VerticalScroll)
        for card in scroll.query(MatchCard):
            event_id = card.event.get("id", "")
            group = self._event_groups.get(event_id)
            card.display = self._active_group is None or group == self._active_group

    def action_refresh(self) -> None:
        self.client.clear_cache(disk=True)
        self.run_worker(self._load(), exclusive=True)

    def on_match_card_selected(self, message: MatchCard.Selected) -> None:
        from tapu.screens.match import MatchScreen
        self.app.push_screen(
            MatchScreen(self.client, self.league, message.event_id, message.event)
        )
