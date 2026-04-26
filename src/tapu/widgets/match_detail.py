import time
from datetime import datetime
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Static


def _get_team(competitors: list[dict], home_away: str) -> dict:
    for c in competitors:
        if c["homeAway"] == home_away:
            return c
    return competitors[0]


def _format_local_time(date_str: str) -> str:
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%a %d %b · %H:%M %Z")
    except Exception:
        return date_str


def _format_clock(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}:{s:02d}"


def _stat_bar(home_raw: str, away_raw: str, width: int = 10) -> tuple[str, str]:
    try:
        hv = float(home_raw.replace("%", "").strip())
        av = float(away_raw.replace("%", "").strip())
    except (ValueError, AttributeError):
        return "░" * width, "░" * width
    total = hv + av
    if total == 0:
        return "░" * width, "░" * width
    h_fill = round(hv / total * width)
    a_fill = round(av / total * width)
    home_bar = f"[green]{'█' * h_fill}[/green][dim]{'░' * (width - h_fill)}[/dim]"
    away_bar = f"[dim]{'░' * (width - a_fill)}[/dim][red]{'█' * a_fill}[/red]"
    return home_bar, away_bar


STAT_KEYS = [
    ("possessionPct", "Possession"),
    ("totalShots", "Shots"),
    ("shotsOnTarget", "On Goal"),
    ("foulsCommitted", "Fouls"),
    ("yellowCards", "Yellows"),
    ("redCards", "Reds"),
    ("wonCorners", "Corners"),
    ("saves", "Saves"),
    ("offsides", "Offsides"),
]


class MatchDetail(Widget):
    DEFAULT_CSS = """
    MatchDetail {
        height: auto;
        width: 80;
        max-width: 100%;
        padding: 1 2;
    }
    MatchDetail .score-block {
        text-align: center;
        padding: 1 0;
    }
    MatchDetail .status-line {
        text-align: center;
        margin: 0 0 1 0;
    }
    MatchDetail .section-label {
        color: $primary;
        text-style: bold;
        border-top: solid $surface-lighten-2;
        padding: 1 0 0 0;
        margin: 1 0 0 0;
    }
    MatchDetail .goals-home {
        width: 1fr;
        text-align: right;
        padding: 0 1 0 0;
    }
    MatchDetail .goals-sep {
        width: 1;
        color: $surface-lighten-2;
    }
    MatchDetail .goals-away {
        width: 1fr;
        padding: 0 0 0 1;
    }
    MatchDetail .stats-header {
        text-style: bold;
        margin: 0 0 0 0;
    }
    MatchDetail .stat-row {
        height: 1;
        text-align: center;
    }
    MatchDetail .stats-abbr {
        text-align: center;
        padding: 0 0 0 0;
    }
    MatchDetail Horizontal {
        height: auto;
    }
    MatchDetail .commentary {
        color: $text-muted;
        padding: 0 0 1 0;
    }
    """

    def __init__(self, event: dict[str, Any], summary: dict[str, Any]) -> None:
        super().__init__()
        self.event = event
        self.summary = summary
        self._is_live = event["status"]["type"].get("state") == "in"
        self._base_clock = event["status"].get("clock", 0.0)
        self._fetch_mono = time.monotonic()

    def compose(self) -> ComposeResult:
        competitors = self.event["competitions"][0]["competitors"]
        home = _get_team(competitors, "home")
        away = _get_team(competitors, "away")
        home_score = home.get("score", "-")
        away_score = away.get("score", "-")
        home_name = home["team"]["displayName"]
        away_name = away["team"]["displayName"]
        home_abbr = home["team"]["abbreviation"]
        away_abbr = away["team"]["abbreviation"]
        home_id = str(home["team"]["id"])

        # Score
        yield Static(
            f"[bold]{home_name}[/bold]  "
            f"[bold yellow]{home_score}  —  {away_score}[/bold yellow]  "
            f"[bold]{away_name}[/bold]",
            classes="score-block",
        )

        # Status / clock
        status = self.event["status"]["type"]
        state = status.get("state", "pre")
        if state == "in":
            status_text = f"[green]● LIVE {_format_clock(self._base_clock)}[/green]"
        elif state == "post":
            status_text = f"[dim]{status.get('detail', 'FT')}[/dim]"
        else:
            date_str = self.event.get("date", "")
            local_time = _format_local_time(date_str) if date_str else status.get("detail", "Upcoming")
            status_text = f"[dim]{local_time}[/dim]"
        yield Static(status_text, id="status-clock", classes="status-line")

        # Live commentary
        if state == "in":
            commentary = self.summary.get("commentary", [])
            recent = [c for c in reversed(commentary) if c.get("text")][:5]
            if recent:
                lines = []
                for c in recent:
                    minute = c.get("time", {}).get("displayValue", "")
                    text = c.get("text", "")
                    prefix = f"[dim]{minute:>3}[/dim]  " if minute else "     "
                    lines.append(f"{prefix}{text}")
                yield Static(
                    "[bold dim]── Live Updates " + "─" * 20 + "[/bold dim]",
                    classes="section-label",
                )
                yield Static("\n".join(lines), id="commentary", classes="commentary")

        # Goals
        key_events = self.summary.get("keyEvents", [])
        goals = [k for k in key_events if k.get("scoringPlay")]
        yield Static("⚽  Goals", classes="section-label")

        if not goals:
            yield Static("[dim]  No goals yet[/dim]")
        else:
            home_lines: list[str] = []
            away_lines: list[str] = []
            for g in goals:
                team_id = str(g.get("team", {}).get("id", ""))
                clock_val = g.get("clock", {}).get("displayValue", "")
                name = g.get("shortText", "Goal").replace(" Goal", "")
                if team_id == home_id:
                    home_lines.append(f"[green]●[/green] [bold]{clock_val}[/bold]  {name}")
                else:
                    away_lines.append(f"[bold]{clock_val}[/bold]  {name}  [red]●[/red]")

            rows = max(len(home_lines), len(away_lines), 1)
            home_lines += [""] * (rows - len(home_lines))
            away_lines += [""] * (rows - len(away_lines))

            yield Horizontal(
                Static("\n".join(home_lines), classes="goals-home"),
                Static("│\n" * rows, classes="goals-sep"),
                Static("\n".join(away_lines), classes="goals-away"),
            )

        # Cards
        cards = [k for k in key_events if "card" in k.get("type", {}).get("type", "")]
        if cards:
            home_cards: list[str] = []
            away_cards: list[str] = []
            for c in cards:
                team_id = str(c.get("team", {}).get("id", ""))
                clock_val = c.get("clock", {}).get("displayValue", "")
                name = c.get("participants", [{}])[0].get("athlete", {}).get("displayName", "?")
                card_type = c.get("type", {}).get("type", "")
                if card_type == "yellow-card":
                    icon = "[bold yellow]▪[/bold yellow]"
                elif card_type == "red-card":
                    icon = "[bold red]■[/bold red]"
                else:
                    icon = "[bold yellow]▪[/bold yellow][bold red]■[/bold red]"
                line = f"{icon} [bold]{clock_val}[/bold]  {name}"
                if team_id == home_id:
                    home_cards.append(line)
                else:
                    away_cards.append(f"[bold]{clock_val}[/bold]  {name}  {icon}")

            if home_cards or away_cards:
                yield Static("🟨  Cards", classes="section-label")
                rows = max(len(home_cards), len(away_cards), 1)
                home_cards += [""] * (rows - len(home_cards))
                away_cards += [""] * (rows - len(away_cards))
                yield Horizontal(
                    Static("\n".join(home_cards), classes="goals-home"),
                    Static("│\n" * rows, classes="goals-sep"),
                    Static("\n".join(away_cards), classes="goals-away"),
                )

        # Stats with progress bars
        teams_data = self.summary.get("boxscore", {}).get("teams", [])
        if len(teams_data) >= 2:
            by_id = {str(td["team"]["id"]): td for td in teams_data}
            home_td = by_id.get(home_id, teams_data[0])
            away_td = next((t for t in teams_data if str(t["team"]["id"]) != home_id), teams_data[1])

            h = {s["name"]: s["displayValue"] for s in home_td.get("statistics", [])}
            a = {s["name"]: s["displayValue"] for s in away_td.get("statistics", [])}

            yield Static("📊  Stats", classes="section-label")
            yield Static(
                f"[bold]{home_abbr}[/bold]                                   [bold]{away_abbr}[/bold]",
                classes="stats-abbr",
            )

            for key, label in STAT_KEYS:
                hv, av = h.get(key, "-"), a.get(key, "-")
                if hv == "-" and av == "-":
                    continue
                home_bar, away_bar = _stat_bar(hv, av)
                yield Static(
                    f"{home_bar} [bold]{hv:>5}[/bold]  [dim]{label:<12}[/dim]  [bold]{av:<5}[/bold] {away_bar}",
                    classes="stat-row",
                )

    def on_mount(self) -> None:
        if self._is_live:
            self.set_interval(1, self._tick)

    def _tick(self) -> None:
        elapsed = time.monotonic() - self._fetch_mono
        clock_str = _format_clock(self._base_clock + elapsed)
        try:
            self.query_one("#status-clock", Static).update(
                f"[green]● LIVE {clock_str}[/green]"
            )
        except Exception:
            pass
