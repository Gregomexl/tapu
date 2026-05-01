from datetime import datetime
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal  # used for goals/cards rows
from textual.widget import Widget
from textual.widgets import Static

from tapu.widgets.match_card import format_live_status


def _get_team(competitors: list[dict], home_away: str) -> dict:
    for c in competitors:
        if c["homeAway"] == home_away:
            return c
    return competitors[0]


def _extract_meta(event: dict, summary: dict) -> list[str]:
    """Inline match meta — weather, referee, attendance — pulled from whichever ESPN endpoint
    has it. Summary takes priority since it carries officials and gameInfo for soccer.
    """
    parts: list[str] = []
    summary_comp = (summary or {}).get("header", {}).get("competitions", [{}])[0]
    event_comp = event.get("competitions", [{}])[0]

    weather = (summary or {}).get("gameInfo", {}).get("weather") or summary_comp.get("weather") or {}
    if isinstance(weather, dict):
        wx = weather.get("displayValue") or weather.get("description") or ""
        temp = weather.get("temperature")
        if wx and temp is not None:
            parts.append(f"☁ {wx} {temp}°")
        elif wx:
            parts.append(f"☁ {wx}")

    officials = summary_comp.get("officials") or event_comp.get("officials") or []
    if officials:
        head = next(
            (o for o in officials if "head" in (o.get("position", {}).get("displayName", "") or "").lower()),
            officials[0],
        )
        ref_name = head.get("displayName") or head.get("fullName")
        if ref_name:
            parts.append(f"Ref: {ref_name}")

    attendance = summary_comp.get("attendance") or event_comp.get("attendance")
    if attendance:
        try:
            n = int(attendance)
            if n > 0:
                parts.append(f"{n:,}")
        except (ValueError, TypeError):
            pass

    return parts


def _format_local_time(date_str: str) -> str:
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%a %d %b · %H:%M %Z")
    except Exception:
        return date_str


def _fmt_stat(raw: str, is_pct: bool = False) -> str:
    if raw == "-":
        return "-"
    try:
        val = float(raw.replace("%", "").strip())
        return f"{round(val)}%" if is_pct else str(round(val)) if "." in raw else raw.strip()
    except (ValueError, AttributeError):
        return raw


def _stat_bar(home_raw: str, away_raw: str, width: int = 12) -> tuple[str, str]:
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
    ("possessionPct", "Possession", True),
    ("totalShots", "Shots", False),
    ("shotsOnTarget", "On Goal", False),
    ("foulsCommitted", "Fouls", False),
    ("yellowCards", "Yellows", False),
    ("redCards", "Reds", False),
    ("wonCorners", "Corners", False),
    ("saves", "Saves", False),
    ("offsides", "Offsides", False),
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
        width: 1fr;
        text-align: center;
        padding: 1 0;
    }
    MatchDetail .status-line {
        text-align: center;
        margin: 0 0 0 0;
    }
    MatchDetail .section-label {
        color: $primary;
        text-style: bold;
        text-align: left;
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
    MatchDetail .stat-row {
        height: 1;
        text-align: center;
    }
    MatchDetail .stats-header {
        text-align: center;
        color: $text-muted;
        text-style: bold;
        margin: 0 0 0 0;
    }
    MatchDetail Horizontal {
        height: auto;
        margin: 0 0 0 0;
    }
    MatchDetail .commentary {
        color: $text-muted;
        padding: 0 0 1 0;
        text-align: left;
    }
    MatchDetail .venue-line {
        text-align: center;
        color: $text-muted;
        margin: 0 0 1 0;
    }
    """

    def __init__(
        self,
        event: dict[str, Any],
        summary: dict[str, Any],
        client=None,
        positions: dict[str, int] | None = None,
    ) -> None:
        super().__init__()
        self.event = event
        self.summary = summary
        self._client = client
        self._positions = positions or {}
        self._is_live = event["status"]["type"].get("state") == "in"

    def compose(self) -> ComposeResult:
        competition = self.event["competitions"][0]
        competitors = competition["competitors"]
        home = _get_team(competitors, "home")
        away = _get_team(competitors, "away")
        home_score = home.get("score", "-")
        away_score = away.get("score", "-")
        home_name = home["team"]["displayName"]
        away_name = away["team"]["displayName"]
        home_abbr = home["team"].get("shortDisplayName") or home["team"]["abbreviation"]
        away_abbr = away["team"].get("shortDisplayName") or away["team"]["abbreviation"]
        home_id = str(home["team"]["id"])


        # Group label (UCL, Europa, World Cup, etc.)
        notes = competition.get("notes", [])
        group = notes[0].get("headline", "") if notes else ""
        if group:
            yield Static(f"[dim]{group}[/dim]", classes="status-line")

        # Team color badges
        def _badge(team: dict) -> str:
            color = team.get("color", "")
            hex_color = f"#{color}" if color and len(color) == 6 else None
            if hex_color:
                return f"[on {hex_color}][{hex_color}]  [/{hex_color}][/on {hex_color}]"
            return ""

        home_badge = _badge(home["team"])
        away_badge = _badge(away["team"])
        yield Static(
            f"{home_badge} [bold]{home_name}[/bold]  "
            f"[bold yellow]{home_score}  –  {away_score}[/bold yellow]  "
            f"[bold]{away_name}[/bold] {away_badge}",
            classes="score-block",
        )

        # Date
        date_str = self.event.get("date", "")
        if date_str:
            yield Static(f"[dim]{_format_local_time(date_str)}[/dim]", classes="status-line")

        # Status / clock
        status = self.event["status"]["type"]
        state = status.get("state", "pre")
        status_text = format_live_status(self.event, show_clock=True) or f"[dim]{status.get('detail', 'Upcoming')}[/dim]"
        yield Static(status_text, id="status-clock", classes="status-line")

        # Venue
        venue = competition.get("venue", {})
        stadium = venue.get("fullName", "")
        city = venue.get("address", {}).get("city", "")
        if stadium or city:
            location = f"{stadium} · {city}" if stadium and city else stadium or city
            yield Static(f"[dim]{location}[/dim]", classes="venue-line")

        # Match meta: weather · referee · attendance
        meta_parts = _extract_meta(self.event, self.summary)
        if meta_parts:
            yield Static(f"[dim]{' · '.join(meta_parts)}[/dim]", classes="venue-line")

        # Live commentary
        if state == "in":
            commentary = self.summary.get("commentary", [])
            recent = [c for c in reversed(commentary) if c.get("text")][:5]
            if recent:
                lines = []
                for c in recent:
                    minute = c.get("time", {}).get("displayValue", "")
                    text = c.get("text", "")
                    prefix = f"[dim]{minute:>3}'[/dim]  " if minute else "      "
                    lines.append(f"{prefix}{text}")
                yield Static("── Live Updates", classes="section-label")
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
                # Mirror layout: home right-aligned (name → clock), away left-aligned (clock → name)
                if team_id == home_id:
                    home_lines.append(f"{name}  [dim]{clock_val}'[/dim]")
                else:
                    away_lines.append(f"[dim]{clock_val}'[/dim]  {name}")

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
                # Mirror layout: home right-aligned (name → clock → icon), away left-aligned (icon → clock → name)
                if team_id == home_id:
                    home_cards.append(f"{name}  [dim]{clock_val}'[/dim]  {icon}")
                else:
                    away_cards.append(f"{icon}  [dim]{clock_val}'[/dim]  {name}")

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
                f"[bold]{home_abbr}[/bold]                                         [bold]{away_abbr}[/bold]",
                classes="stats-header",
            )

            for key, label, is_pct in STAT_KEYS:
                hv, av = h.get(key, "-"), a.get(key, "-")
                if hv == "-" and av == "-":
                    continue
                home_bar, away_bar = _stat_bar(hv, av)
                hv_display = _fmt_stat(hv, is_pct)
                av_display = _fmt_stat(av, is_pct)
                yield Static(
                    f"[bold]{hv_display:>6}[/bold] {home_bar}  [dim]{label:<12}[/dim]  {away_bar} [bold]{av_display:<6}[/bold]",
                    classes="stat-row",
                )
