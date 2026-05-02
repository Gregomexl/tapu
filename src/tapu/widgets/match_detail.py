from datetime import datetime
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Static

from tapu.widgets.match_card import format_live_status


def _get_team(competitors: list[dict], home_away: str) -> dict:
    for c in competitors:
        if c.get("homeAway") == home_away:
            return c
    return competitors[0] if competitors else {}


def resolve_team_colors(home: dict, away: dict) -> tuple[str, str]:
    """Return non-colliding colors for home and away teams."""
    def _hex_color(team: dict) -> str:
        color = team.get("color", "")
        return color if len(color) == 6 else ""

    home_hex = _hex_color(home.get("team", {}))
    away_hex = _hex_color(away.get("team", {}))

    # Avoid showing similar colors for both teams
    if home_hex and away_hex:
        try:
            r1, g1, b1 = int(home_hex[0:2], 16), int(home_hex[2:4], 16), int(home_hex[4:6], 16)
            r2, g2, b2 = int(away_hex[0:2], 16), int(away_hex[2:4], 16), int(away_hex[4:6], 16)
            distance = ((r1 - r2)**2 + (g1 - g2)**2 + (b1 - b2)**2) ** 0.5
            if distance < 65:  # threshold for visual similarity
                away_hex = ""
        except ValueError:
            pass

    home_color = f"#{home_hex}" if home_hex else "white"
    away_color = f"#{away_hex}" if away_hex else "cyan"

    return home_color, away_color


def _team_abbrs(event: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for c in event.get("competitions", [{}])[0].get("competitors", []):
        team_id = str(c.get("team", {}).get("id", ""))
        abbr = c.get("team", {}).get("abbreviation") or c.get("team", {}).get("shortDisplayName") or ""
        if team_id:
            out[team_id] = abbr
    return out


def _participant_name(k: dict, idx: int = 0) -> str:
    parts = k.get("participants") or []
    if 0 <= idx < len(parts):
        return parts[idx].get("athlete", {}).get("displayName", "")
    return ""


def _sub_text(k: dict) -> str:
    parts = k.get("participants") or []
    names = [p.get("athlete", {}).get("displayName", "") for p in parts if p.get("athlete")]
    if len(names) >= 2:
        return f"{names[0]}  ↔  {names[1]}"
    if names:
        return names[0]
    return k.get("shortText", "Substitution")


def build_timeline(event: dict, summary: dict, filter_cards: bool = False, only_cards: bool = False) -> list[str]:
    abbrs = _team_abbrs(event)
    items: list[tuple[float, str]] = []
    for k in summary.get("keyEvents", []) or []:
        team_id = str(k.get("team", {}).get("id", ""))
        clock = k.get("clock", {}) or {}
        clock_val = _format_clock_minute(clock.get("displayValue", ""))
        try:
            secs = float(clock.get("value") or 0)
        except (TypeError, ValueError):
            secs = 0.0
        type_str = (k.get("type", {}) or {}).get("type", "")

        is_card = "card" in type_str
        if only_cards and not is_card:
            continue
        if filter_cards and is_card:
            continue

        if k.get("scoringPlay"):
            icon = "⚽"
            text = (k.get("shortText") or "Goal").replace(" Goal", "")
        elif "yellow-card" in type_str:
            icon = "🟨"
            text = _participant_name(k) or k.get("shortText") or "Booking"
        elif "red-card" in type_str:
            icon = "🟥"
            text = _participant_name(k) or k.get("shortText") or "Sent Off"
        else:
            continue

        abbr = abbrs.get(team_id, "")
        abbr_suffix = f"  [dim]{abbr}[/dim]" if abbr else ""
        items.append((secs, f"{icon}  [dim]{clock_val:>5}'[/dim]  {text}{abbr_suffix}"))

    items.sort(key=lambda x: x[0])
    return [s for _, s in items]


def build_substitutions(event: dict, summary: dict) -> list[str]:
    abbrs = _team_abbrs(event)
    items: list[tuple[float, str]] = []
    for k in summary.get("keyEvents", []) or []:
        type_str = (k.get("type", {}) or {}).get("type", "")
        if not ("substitution" in type_str or type_str == "sub"):
            continue
        team_id = str(k.get("team", {}).get("id", ""))
        clock = k.get("clock", {}) or {}
        clock_val = _format_clock_minute(clock.get("displayValue", ""))
        try:
            secs = float(clock.get("value") or 0)
        except (TypeError, ValueError):
            secs = 0.0
        text = _sub_text(k)
        abbr = abbrs.get(team_id, "")
        abbr_suffix = f"  [dim]{abbr}[/dim]" if abbr else ""
        items.append((secs, f"[dim]{clock_val}'[/dim]  {text}{abbr_suffix}"))

    items.sort(key=lambda x: x[0])
    return [s for _, s in items]


def _format_clock_minute(raw: str) -> str:
    if not raw:
        return ""
    return raw.replace("'", "").strip()


def _extract_jersey(roster_entry: dict) -> str:
    athlete = roster_entry.get("athlete", {}) or {}
    for candidate in (
        roster_entry.get("jersey"),
        athlete.get("jersey"),
        athlete.get("uniformNumber"),
    ):
        if candidate not in (None, ""):
            return str(candidate)
    return "—"


def _format_formation(formation: Any) -> str:
    if isinstance(formation, dict):
        return formation.get("name", "") or ""
    return formation or ""


def _format_lineup_section(team_roster: dict, team_color: str | None = None) -> list[str]:
    team = team_roster.get("team", {}) or {}
    team_name = team.get("displayName", "") or ""
    
    if team_color is None:
        color = team.get("color", "") or ""
        team_color = f"#{color}" if len(color) == 6 else "white"

    formation = _format_formation(team_roster.get("formation"))
    roster = team_roster.get("roster") or []
    starters = [p for p in roster if p.get("starter")]
    bench = [p for p in roster if not p.get("starter")]

    lines: list[str] = []
    header = f"[{team_color}]█[/{team_color}] [bold]{team_name}[/bold]"

    if formation:
        header += f"  [dim]{formation}[/dim]"
    lines.append(header)

    for p in starters:
        jersey = _extract_jersey(p)
        athlete = p.get("athlete", {}) or {}
        name = athlete.get("displayName") or athlete.get("shortName") or p.get("displayName") or "?"
        pos = (p.get("position", {}) or {}).get("abbreviation", "")
        lines.append(f"  [dim]{jersey:>2}[/dim]  {name}  [dim]{pos}[/dim]")

    if bench:
        bench_names = []
        for p in bench[:7]:
            jersey = _extract_jersey(p)
            athlete = p.get("athlete", {}) or {}
            name = athlete.get("displayName") or p.get("displayName") or "?"
            bench_names.append(f"{jersey} {name}")
        more = f" · +{len(bench) - 7}" if len(bench) > 7 else ""
        lines.append(f"  [dim]Bench:[/dim] [dim]{' · '.join(bench_names)}{more}[/dim]")

    return lines


def build_lineups(event: dict, summary: dict) -> list[list[str]]:
    rosters = summary.get("rosters") or []
    if not rosters:
        return []

    competitors = event.get("competitions", [{}])[0].get("competitors", [])
    home_comp = next((c for c in competitors if c.get("homeAway") == "home"), {})
    away_comp = next((c for c in competitors if c.get("homeAway") == "away"), {})
    home_id = str(home_comp.get("team", {}).get("id", ""))
    
    home_color, away_color = resolve_team_colors(home_comp, away_comp)

    by_id = {str(r.get("team", {}).get("id", "")): r for r in rosters}
    home = by_id.get(home_id)
    away = next((r for tid, r in by_id.items() if tid != home_id), None)

    if home and away:
        return [_format_lineup_section(home, home_color), _format_lineup_section(away, away_color)]
    return [_format_lineup_section(r) for r in rosters[:2]]


def _get_weather_emoji(wx: str) -> str:
    wx = wx.lower()
    if any(w in wx for w in ["sun", "clear", "fair"]):
        return "☀️"
    if any(w in wx for w in ["cloud", "overcast"]):
        return "☁️"
    if any(w in wx for w in ["rain", "shower", "drizzle"]):
        return "🌧️"
    if any(w in wx for w in ["snow", "ice", "flurries"]):
        return "❄️"
    if any(w in wx for w in ["storm", "thunder"]):
        return "⛈️"
    return "🌤️"


def _format_local_time(date_str: str) -> str:
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%a %d %b")
    except Exception:
        return date_str


def _format_local_hour(date_str: str) -> str:
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%H:%M %Z")
    except Exception:
        return ""


def _fmt_stat(raw: str, is_pct: bool = False) -> str:
    if raw == "-":
        return "-"
    try:
        val = float(raw.replace("%", "").strip())
        return f"{round(val)}%" if is_pct else str(round(val)) if "." in raw else raw.strip()
    except (ValueError, AttributeError):
        return raw


def _stat_bar(home_raw: str, away_raw: str, home_color: str, away_color: str, width: int = 12) -> tuple[str, str]:
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
    home_bar = f"[{home_color}]{'█' * h_fill}[/{home_color}][dim]{'░' * (width - h_fill)}[/dim]"
    away_bar = f"[dim]{'░' * (width - a_fill)}[/dim][{away_color}]{'█' * a_fill}[/{away_color}]"
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
        width: 100%;
        height: 100%;
        padding: 1 2;
        background: $surface;
    }
    MatchDetail .main-container {
        width: 100%;
        height: 1fr;
    }
    MatchDetail .left-sidebar {
        width: 25%;
        height: 100%;
        padding: 0 1;
        margin-right: 1;
    }
    MatchDetail .main-content {
        width: 75%;
        height: 100%;
    }
    MatchDetail .header-panel {
        width: 100%;
        text-align: center;
        padding: 2 0;
        margin-bottom: 1;
        height: auto;
    }
    MatchDetail .header-score {
        text-align: center;
        padding: 1 0;
        height: 6;
        content-align: center middle;
        border: heavy $surface-lighten-1;
        margin: 0 4;
        background: $surface-lighten-1 10%;
    }
    MatchDetail .header-status {
        text-align: center;
        margin-top: 1;
    }
    MatchDetail .main-columns {
        width: 100%;
        height: 1fr;
    }
    MatchDetail .center-col {
        width: 65%;
        height: 100%;
        padding: 0 1;
        margin-right: 1;
    }
    MatchDetail .right-col {
        width: 35%;
        height: 100%;
        padding: 0 1;
    }
    MatchDetail .panel {
        border: solid $surface-lighten-2;
        padding: 0 1;
        margin-bottom: 1;
        height: auto;
    }
    MatchDetail .panel-header {
        color: $primary;
        text-style: bold;
        text-align: left;
        margin-bottom: 1;
    }
    MatchDetail .kv-row {
        layout: horizontal;
        height: 1;
    }
    MatchDetail .kv-key {
        width: 1fr;
        color: $text-muted;
    }
    MatchDetail .kv-val {
        width: 2fr;
        text-align: right;
        text-style: bold;
    }
    MatchDetail .live-dot {
        color: $success;
        text-style: bold;
    }
    MatchDetail .stat-row {
        height: 1;
        text-align: center;
    }
    MatchDetail .stats-header {
        text-align: center;
        color: $text-muted;
        text-style: bold;
        margin: 0 0 1 0;
    }
    MatchDetail .commentary {
        color: $text-muted;
        padding: 0 0 1 0;
        text-align: left;
    }
    MatchDetail .timeline {
        padding: 0 1 1 1;
        text-align: left;
    }
    MatchDetail .subs-list {
        padding: 0 1 1 0;
        text-align: left;
    }
    MatchDetail .lineup {
        padding: 0 1;
        margin: 0 0 1 0;
        text-align: left;
    }
    MatchDetail .header-subtitle {
        text-align: center;
        color: $text-muted;
        margin-top: 1;
    }
    MatchDetail .league-header {
        padding: 0 1 1 1;
        margin-bottom: 1;
        border-bottom: solid $surface-lighten-2;
        color: $text;
    }
    """

    def __init__(
        self,
        event: dict[str, Any],
        summary: dict[str, Any],
        client=None,
        positions: dict[str, int] | None = None,
        league_name: str = "",
    ) -> None:
        super().__init__()
        self.event = event
        self.summary = summary
        self._client = client
        self._positions = positions or {}
        self._league_name = league_name
        self._is_live = event["status"]["type"].get("state") == "in"

    def compose(self) -> ComposeResult:
        with Horizontal(classes="main-container"):
            with VerticalScroll(classes="left-sidebar"):
                yield from self._build_league_panel()
                yield from self._build_match_overview()
                yield from self._build_lineups()
                yield from self._build_subs()

            with Vertical(classes="main-content"):
                yield from self._build_header()
                with Horizontal(classes="main-columns"):
                    with VerticalScroll(classes="center-col"):
                        yield from self._build_live_feed()
                        yield from self._build_stats()

                    with VerticalScroll(classes="right-col"):
                        yield from self._build_cards()
                        yield from self._build_key_events()
                        yield from self._build_commentary()

    def _build_header(self) -> list[Widget]:
        competition = self.event["competitions"][0]
        competitors = competition["competitors"]
        home = _get_team(competitors, "home")
        away = _get_team(competitors, "away")
        state = self.event["status"]["type"].get("state")
        status = self.event["status"]["type"]

        try:
            home_score_int = int(home.get("score", -1))
            away_score_int = int(away.get("score", -1))
        except (ValueError, TypeError):
            home_score_int = away_score_int = -1

        home_score = home.get("score", "-")
        away_score = away.get("score", "-")
        home_name = home["team"]["displayName"]
        away_name = away["team"]["displayName"]

        home_color, away_color = resolve_team_colors(home, away)

        home_colored = f"[{home_color}]█[/{home_color}] [bold]{home_name.upper()}[/bold]"
        away_colored = f"[bold]{away_name.upper()}[/bold] [{away_color}]█[/{away_color}]"

        # Score: highlight winner/leader; dim loser; both yellow when level
        if state in ("in", "post") and home_score_int >= 0 and away_score_int >= 0:
            if home_score_int > away_score_int:
                h_score = f"[bold bright_white]{home_score}[/bold bright_white]"
                a_score = f"[dim]{away_score}[/dim]"
            elif away_score_int > home_score_int:
                h_score = f"[dim]{home_score}[/dim]"
                a_score = f"[bold bright_white]{away_score}[/bold bright_white]"
            else:
                h_score = f"[bold yellow]{home_score}[/bold yellow]"
                a_score = f"[bold yellow]{away_score}[/bold yellow]"
        else:
            h_score = f"[dim]{home_score}[/dim]"
            a_score = f"[dim]{away_score}[/dim]"

        status_text = (
            format_live_status(self.event, show_clock=True) or f"[dim]{status.get('detail', 'Upcoming')}[/dim]"
        )

        # Subtitle: date · time · venue (· weather if available)
        date_str = self.event.get("date", "")
        venue = competition.get("venue", {})
        stadium = venue.get("fullName", "")
        city = venue.get("address", {}).get("city", "")
        venue_part = f"{stadium}, {city}" if stadium and city else stadium or city

        summary_comp = (self.summary or {}).get("header", {}).get("competitions", [{}])[0]
        weather_data = (self.summary or {}).get("gameInfo", {}).get("weather") or summary_comp.get("weather") or {}
        weather_part = ""
        if isinstance(weather_data, dict):
            wx = weather_data.get("displayValue") or weather_data.get("description") or ""
            temp = weather_data.get("temperature")
            if wx or temp is not None:
                emoji = _get_weather_emoji(wx) if wx else "🌤️"
                weather_part = f"{emoji} {temp}°C" if temp is not None else f"{emoji} {wx}"

        subtitle_parts = []
        if date_str:
            subtitle_parts.append(_format_local_time(date_str))
            subtitle_parts.append(_format_local_hour(date_str))
        if venue_part:
            subtitle_parts.append(venue_part)
        if weather_part:
            subtitle_parts.append(weather_part)
        subtitle = "  ·  ".join(subtitle_parts)

        return [
            Vertical(
                Static(
                    f"{home_colored}    {h_score}  [dim]—[/dim]  {a_score}    {away_colored}",
                    classes="header-score",
                ),
                Static(status_text, classes="header-status"),
                Static(f"[dim]{subtitle}[/dim]", classes="header-subtitle") if subtitle else Static(""),
                classes="header-panel",
            )
        ]

    def _build_league_panel(self) -> list[Widget]:
        """Compact league + round header above match overview."""
        # Use explicitly passed league name first (most reliable)
        comp_name = self._league_name

        if not comp_name:
            # Fall back: parse season slug e.g. "2025-26-laliga" -> "laliga"
            season_raw = self.event.get("season", {}).get("displayName", "")
            if season_raw:
                parts = season_raw.split(" ", 1)
                comp_name = parts[1] if len(parts) > 1 and "-" in parts[0] else season_raw
            else:
                notes = self.event["competitions"][0].get("notes", [])
                comp_name = notes[0].get("headline", "") if notes else ""

        # Round / Matchday from season slug e.g. "2025-26-laliga" or "regular-season-34"
        season = self.event.get("season", {})
        week = season.get("slug", "")
        week_num = ""
        if week:
            parts = week.rsplit("-", 1)
            if len(parts) == 2 and parts[1].isdigit():
                week_num = parts[1]
        if not week_num:
            week_num = str(season.get("week", "") or "")
        round_label = f"Round {week_num}" if week_num else ""

        lines = []
        if comp_name:
            lines.append(f"[bold]{comp_name}[/bold]")
        if round_label:
            lines.append(f"[dim]{round_label}[/dim]")
        if not lines:
            return []
        return [Static("\n".join(lines), classes="league-header")]

    def _build_match_overview(self) -> list[Widget]:
        competition = self.event["competitions"][0]

        status = self.event["status"]["type"]
        is_live = status.get("state") == "in"
        status_val = "[green]● LIVE[/green]" if is_live else status.get("detail", "")

        date_str = self.event.get("date", "")
        date_val = f"{_format_local_time(date_str)}  ·  {_format_local_hour(date_str)}" if date_str else ""

        venue = competition.get("venue", {})
        stadium = venue.get("fullName", "")
        city = venue.get("address", {}).get("city", "")

        summary_comp = (self.summary or {}).get("header", {}).get("competitions", [{}])[0]
        weather = (self.summary or {}).get("gameInfo", {}).get("weather") or summary_comp.get("weather") or {}
        weather_val = ""
        if isinstance(weather, dict):
            wx = weather.get("displayValue") or weather.get("description") or ""
            temp = weather.get("temperature")
            emoji = _get_weather_emoji(wx) if wx else ""
            if emoji and temp is not None:
                weather_val = f"{emoji} {temp}°C"
            elif emoji and wx:
                weather_val = f"{emoji} {wx}"

        # Officials come from summary.gameInfo, not header
        game_info = (self.summary or {}).get("gameInfo", {})
        officials = game_info.get("officials") or competition.get("officials") or []
        ref_val = ""
        if officials:
            head = next(
                (o for o in officials if "head" in (o.get("position", {}).get("displayName", "") or "").lower()),
                officials[0],
            )
            ref_val = head.get("displayName") or head.get("fullName", "")

        def _kv(k: str, v: str) -> Widget:
            return Horizontal(Static(k, classes="kv-key"), Static(v, classes="kv-val"), classes="kv-row")

        items = [Static("MATCH OVERVIEW", classes="panel-header")]
        if status_val:
            items.append(_kv("Status", status_val))
        if date_val:
            items.append(_kv("Date", date_val))
        if stadium:
            items.append(_kv("Stadium", stadium))
        if city:
            items.append(_kv("City", city))
        if weather_val:
            items.append(_kv("Weather", weather_val))
        if ref_val:
            items.append(_kv("Referee", ref_val))

        return [Vertical(*items, classes="panel")]

    def _build_lineups(self) -> list[Widget]:
        lineups = build_lineups(self.event, self.summary)
        if not lineups:
            return []
        items: list[Widget] = [Static("LINEUPS", classes="panel-header")]
        for lines in lineups:
            items.append(Static("\n".join(lines), classes="lineup"))
        return [Vertical(*items, classes="panel")]

    def _build_subs(self) -> list[Widget]:
        state = self.event["status"]["type"].get("state")
        if state not in ("in", "post"):
            return []
        sub_lines = build_substitutions(self.event, self.summary)
        items = [Static("SUBSTITUTIONS", classes="panel-header")]
        if not sub_lines:
            items.append(Static("[dim]  None yet[/dim]", classes="subs-list"))
        else:
            items.append(Static("\n".join(sub_lines), classes="subs-list"))
        return [Vertical(*items, classes="panel")]

    def _build_live_feed(self) -> list[Widget]:
        """Show the most recent 8 commentary entries as a live feed."""
        state = self.event["status"]["type"].get("state")
        if state not in ("in", "post"):
            return []
        commentary = (self.summary or {}).get("commentary", []) or []
        recent = [c for c in commentary if c.get("text")][-8:][::-1]
        if not recent:
            return []
        lines = []
        for c in recent:
            minute = c.get("time", {}).get("displayValue", "")
            text = c.get("text", "")
            prefix = f"[dim]{minute:>3}'[/dim]  " if minute else "      "
            lines.append(f"{prefix}{text}")
        return [
            Vertical(
                Static("LIVE FEED", classes="panel-header"),
                Static("\n".join(lines), classes="commentary"),
                classes="panel",
            )
        ]

    def _build_commentary(self) -> list[Widget]:
        """Full scrollable commentary in the right column."""
        state = self.event["status"]["type"].get("state")
        if state not in ("in", "post"):
            return []
        commentary = (self.summary or {}).get("commentary", []) or []
        if not commentary:
            return []
        lines = []
        for c in reversed(commentary):
            minute = c.get("time", {}).get("displayValue", "")
            text = c.get("text", "")
            prefix = f"[dim]{minute:>3}'[/dim]  " if minute else "      "
            lines.append(f"{prefix}{text}")
        return [
            Vertical(
                Static("COMMENTARY", classes="panel-header"),
                Static("\n\n".join(lines), id="commentary", classes="commentary"),
                classes="panel",
            )
        ]

    def _build_stats(self) -> list[Widget]:
        teams_data = self.summary.get("boxscore", {}).get("teams", [])
        if len(teams_data) < 2:
            return []

        competitors = self.event["competitions"][0]["competitors"]
        home = _get_team(competitors, "home")
        away = _get_team(competitors, "away")
        home_id = str(home["team"]["id"])
        
        home_color, away_color = resolve_team_colors(home, away)

        home_abbr = home["team"].get("shortDisplayName") or home["team"]["abbreviation"]
        away_abbr = away["team"].get("shortDisplayName") or away["team"]["abbreviation"]

        by_id = {str(td["team"]["id"]): td for td in teams_data}
        home_td = by_id.get(home_id, teams_data[0])
        away_td = next((t for t in teams_data if str(t["team"]["id"]) != home_id), teams_data[1])

        h = {s["name"]: s["displayValue"] for s in home_td.get("statistics", [])}
        a = {s["name"]: s["displayValue"] for s in away_td.get("statistics", [])}

        items: list[Widget] = [
            Static("MATCH STATS", classes="panel-header"),
            Static(
                f"[green][bold]{home_abbr}[/bold][/green]                                   [red][bold]{away_abbr}[/bold][/red]",
                classes="stats-header",
            ),
        ]
        for key, label, is_pct in STAT_KEYS:
            hv, av = h.get(key, "-"), a.get(key, "-")
            if hv == "-" and av == "-":
                continue
            home_bar, away_bar = _stat_bar(hv, av, "green", "red", width=10)
            hv_display = _fmt_stat(hv, is_pct)
            av_display = _fmt_stat(av, is_pct)
            items.append(
                Static(
                    f"[white][bold]{hv_display:>5}[/bold][/white] {home_bar} [dim]{label:^10}[/dim] {away_bar} [white][bold]{av_display:<5}[/bold][/white]",
                    classes="stat-row",
                )
            )
        return [Vertical(*items, classes="panel")]

    def _build_cards(self) -> list[Widget]:
        state = self.event["status"]["type"].get("state")
        if state not in ("in", "post"):
            return []
        lines = build_timeline(self.event, self.summary, only_cards=True)
        items = [Static("CARDS", classes="panel-header")]
        if not lines:
            items.append(Static("[dim]  No cards[/dim]", classes="timeline"))
        else:
            items.append(Static("\n".join(lines), classes="timeline"))
        return [Vertical(*items, classes="panel")]

    def _build_key_events(self) -> list[Widget]:
        state = self.event["status"]["type"].get("state")
        if state not in ("in", "post"):
            return []
        # Only scoring plays (cards are in the CARDS panel)
        lines = build_timeline(self.event, self.summary, filter_cards=True)
        items = [Static("GOALS", classes="panel-header")]
        if not lines:
            items.append(Static("[dim]  No goals yet[/dim]", classes="timeline"))
        else:
            items.append(Static("\n".join(lines), classes="timeline"))
        return [Vertical(*items, classes="panel")]
