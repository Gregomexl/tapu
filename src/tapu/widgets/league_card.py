import asyncio
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static

from tapu.config import League


def _chafa_available() -> bool:
    return shutil.which("chafa") is not None


def _render_logo_chafa(png_bytes: bytes, width: int = 12, height: int = 4) -> str | None:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(png_bytes)
        tmp_path = f.name
    try:
        result = subprocess.run(
            ["chafa", "--format", "symbols", f"--size={width}x{height}", tmp_path],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.rstrip() if result.returncode == 0 else None
    except Exception:
        return None
    finally:
        Path(tmp_path).unlink(missing_ok=True)


class LeagueCard(Widget, can_focus=True):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("enter", "select", "Open League", show=False),
    ]

    DEFAULT_CSS = """
    LeagueCard {
        height: 9;
        width: 1fr;
        min-width: 24;
        padding: 1 2;
        margin: 0 1 1 0;
        border: solid $surface-lighten-2;
    }
    LeagueCard:focus {
        border: solid $primary;
    }
    LeagueCard.has-live {
        border: solid $success;
    }
    LeagueCard .logo {
        height: auto;
        margin: 0 0 0 0;
    }
    """

    def __init__(self, league: League, scoreboard: dict[str, Any]) -> None:
        super().__init__()
        self.league = league
        self.scoreboard = scoreboard
        events = scoreboard.get("events", [])
        self.live_count = sum(
            1 for e in events
            if e["status"]["type"]["name"] == "STATUS_IN_PROGRESS"
        )
        leagues_data = scoreboard.get("leagues", [])
        logos = leagues_data[0].get("logos", []) if leagues_data else []
        self._logo_url: str | None = logos[0].get("href") if logos else None
        if self.live_count > 0:
            self.add_class("has-live")

    def compose(self) -> ComposeResult:
        events = self.scoreboard.get("events", [])
        live_label = (
            f"[green]{self.live_count} live[/green]"
            if self.live_count > 0
            else f"[dim]{len(events)} matches[/dim]"
        )
        top_match = ""
        if events:
            e = events[0]
            comps = e["competitions"][0]["competitors"]
            home = next(c for c in comps if c["homeAway"] == "home")
            away = next(c for c in comps if c["homeAway"] == "away")
            top_match = (
                f"{home['team']['abbreviation']} "
                f"{home.get('score', '-')}-{away.get('score', '-')} "
                f"{away['team']['abbreviation']}"
            )
        yield Static(f"[bold]{self.league.name}[/bold]  {live_label}", id="logo-line", classes="logo")
        yield Static(f"[dim]{self.league.full_name}[/dim]")
        yield Static(top_match or "[dim]No matches today[/dim]")

    def on_mount(self) -> None:
        if self._logo_url and _chafa_available():
            self.run_worker(self._load_logo(), exclusive=False)

    async def _load_logo(self) -> None:
        try:
            client = getattr(self.app, "client", None)
            if client is None:
                return
            png_bytes = await client.get_logo_bytes(self._logo_url)
            rendered = await asyncio.to_thread(_render_logo_chafa, png_bytes)
            if rendered:
                logo_widget = self.query_one("#logo-line", Static)
                events = self.scoreboard.get("events", [])
                live_label = (
                    f"[green]{self.live_count} live[/green]"
                    if self.live_count > 0
                    else f"[dim]{len(events)} matches[/dim]"
                )
                logo_widget.update(f"{rendered}  {live_label}")
        except Exception:
            pass

    def action_select(self) -> None:
        self.post_message(self.Selected(self.league))

    class Selected(Message):
        def __init__(self, league: League) -> None:
            super().__init__()
            self.league = league
