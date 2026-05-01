from datetime import datetime
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widget import Widget
from textual.widgets import Static

from tapu.widgets.match_card import format_live_status


def _get_team(competitors: list[dict], home_away: str) -> dict:
    for c in competitors:
        if c["homeAway"] == home_away:
            return c
    return competitors[0]


def _team_abbrs(event: dict) -> dict[str, str]:
    """team_id (str) → club abbreviation (e.g. 'RMA', 'BAR'). Falls back to shortDisplayName.

    Used to tag timeline rows with the club acronym at the end. Replaces the previous
    team-color block — same teams often share visually-similar palette colors (Real
    Madrid / Sevilla / Espanyol are all white-and-red), making the badge ambiguous.
    """
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


def build_timeline(event: dict, summary: dict) -> list[str]:
    """Goals + cards from keyEvents in chronological order.

    Each row is `<icon>  <minute>'  <text>  <ABBR>` — the team acronym at the end
    disambiguates rows when both clubs use similar brand colors.
    Substitutions are intentionally excluded; they get their own section so the
    timeline stays focused on score-relevant events.
    """
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
            continue  # subs handled separately, unknown types dropped

        abbr = abbrs.get(team_id, "")
        abbr_suffix = f"  [dim]{abbr}[/dim]" if abbr else ""
        items.append((secs, f"{icon}  [dim]{clock_val:>5}'[/dim]  {text}{abbr_suffix}"))

    items.sort(key=lambda x: x[0])
    return [s for _, s in items]


def build_substitutions(event: dict, summary: dict) -> list[str]:
    """Substitution rows in chronological order, in the same row format as the timeline.

    `<minute>'  <player ↔ player>  <ABBR>` — single-column scroll, club acronym at the
    end disambiguates which team made the change. Tactical events live in their own
    section so they don't dilute the goals/cards narrative above.
    """
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
        # No right-align padding on the clock — sub rows have no leading icon, so the
        # row starts flush at the section's left edge.
        items.append((secs, f"[dim]{clock_val}'[/dim]  {text}{abbr_suffix}"))

    items.sort(key=lambda x: x[0])
    return [s for _, s in items]


def _format_clock_minute(raw: str) -> str:
    """ESPN returns clock minutes in mixed shapes:
       - '67' (plain), '67:23' (mm:ss for some leagues), '90'+5'' (stoppage with apostrophes).
    Normalize to a single trailing-apostrophe-free token: '67', '90+5'. The caller adds the
    closing apostrophe in the rendered string.
    """
    if not raw:
        return ""
    return raw.replace("'", "").strip()


def _extract_jersey(roster_entry: dict) -> str:
    """ESPN puts the jersey number in different spots — try them all and fall back to '—'.

    Observed paths: roster_entry.jersey, roster_entry.athlete.jersey,
    roster_entry.athlete.uniformNumber. Some payloads return integers; coerce to str.
    """
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
    """ESPN sometimes returns formation as a string ('4-3-3') and sometimes as
    {'name': '4-3-3'}. Normalize."""
    if isinstance(formation, dict):
        return formation.get("name", "") or ""
    return formation or ""


def _format_lineup_section(team_roster: dict) -> list[str]:
    """One team's lineup block: team name + formation header, starting XI rows, and a
    one-line bench summary. Returns markup-ready lines (no enclosing widget).
    """
    team = team_roster.get("team", {}) or {}
    team_name = team.get("displayName", "") or ""
    color = team.get("color", "") or ""
    hex_color = f"#{color}" if len(color) == 6 else None
    badge = (
        f"[on {hex_color}][{hex_color}]  [/{hex_color}][/on {hex_color}] "
        if hex_color
        else ""
    )
    formation = _format_formation(team_roster.get("formation"))
    roster = team_roster.get("roster") or []
    starters = [p for p in roster if p.get("starter")]
    bench = [p for p in roster if not p.get("starter")]

    lines: list[str] = []
    header = f"{badge}[bold]{team_name}[/bold]"
    if formation:
        header += f"  [dim]{formation}[/dim]"
    lines.append(header)

    for p in starters:
        jersey = _extract_jersey(p)
        athlete = p.get("athlete", {}) or {}
        name = athlete.get("displayName") or athlete.get("shortName") or p.get("displayName") or "?"
        pos = (p.get("position", {}) or {}).get("abbreviation", "")
        lines.append(f"  [bold]{jersey:>2}[/bold]  {name}  [dim]{pos}[/dim]")

    if bench:
        # Cap the bench at 7 names so a 23-man squad doesn't bloat the panel.
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
    """Return [home_lines, away_lines] from summary.rosters, ordered home-first.

    Empty list when ESPN hasn't published lineups yet (typical for pre-match >1h out).
    """
    rosters = summary.get("rosters") or []
    if not rosters:
        return []

    competitors = event.get("competitions", [{}])[0].get("competitors", [])
    home_id = next(
        (str(c.get("team", {}).get("id", "")) for c in competitors if c.get("homeAway") == "home"),
        "",
    )
    by_id = {str(r.get("team", {}).get("id", "")): r for r in rosters}
    home = by_id.get(home_id)
    away = next((r for tid, r in by_id.items() if tid != home_id), None)

    if home and away:
        return [_format_lineup_section(home), _format_lineup_section(away)]
    # Fallback: ESPN didn't tag teams clearly — render in the order received.
    return [_format_lineup_section(r) for r in rosters[:2]]


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


THREE_COL_THRESHOLD = 120  # min terminal width before switching to three-column layout


class MatchDetail(Widget):
    DEFAULT_CSS = """
    MatchDetail {
        height: auto;
        width: 80;
        max-width: 100%;
        padding: 1 2;
    }
    MatchDetail.wide {
        width: 1fr;
        height: 1fr;
        padding: 1 1;
    }
    MatchDetail .three-col {
        height: 1fr;
        width: 100%;
    }
    MatchDetail .col-side {
        width: 1fr;
        height: 1fr;
        padding: 0 1;
    }
    MatchDetail .col-center {
        width: 2fr;
        height: 1fr;
        padding: 0 1;
        border-left: solid $surface-lighten-2;
        border-right: solid $surface-lighten-2;
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

    def on_mount(self) -> None:
        if self._terminal_width() >= THREE_COL_THRESHOLD:
            self.add_class("wide")

    def _terminal_width(self) -> int:
        try:
            return self.app.size.width
        except Exception:
            return 80

    def compose(self) -> ComposeResult:
        # Build each section as a list of pre-instantiated Static widgets, then arrange
        # them either stacked (narrow) or in three columns (≥ THREE_COL_THRESHOLD).
        # Keeping the section-construction code in one place avoids duplicating it across
        # the two layout branches.
        header_widgets, state, home_id, home_abbr, away_abbr = self._build_header_widgets()
        live_widgets = self._build_live_widgets(state)
        timeline_widgets = self._build_timeline_widgets(state)
        subs_widgets = self._build_subs_widgets(state)
        lineups_widgets = self._build_lineups_widgets()
        stats_widgets = self._build_stats_widgets(home_id, home_abbr, away_abbr)

        if self._terminal_width() >= THREE_COL_THRESHOLD:
            with Horizontal(classes="three-col"):
                with VerticalScroll(classes="col-side"):
                    yield from timeline_widgets
                    yield from subs_widgets
                    yield from live_widgets
                with VerticalScroll(classes="col-center"):
                    yield from header_widgets
                    yield from stats_widgets
                with VerticalScroll(classes="col-side"):
                    yield from lineups_widgets
        else:
            yield from header_widgets
            yield from live_widgets
            yield from timeline_widgets
            yield from subs_widgets
            yield from lineups_widgets
            yield from stats_widgets

    def _build_header_widgets(self) -> tuple[list[Widget], str, str, str, str]:
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
        status = self.event["status"]["type"]
        state = status.get("state", "pre")

        widgets: list[Widget] = []

        notes = competition.get("notes", [])
        group = notes[0].get("headline", "") if notes else ""
        if group:
            widgets.append(Static(f"[dim]{group}[/dim]", classes="status-line"))

        def _badge(team: dict) -> str:
            color = team.get("color", "")
            hex_color = f"#{color}" if color and len(color) == 6 else None
            if hex_color:
                return f"[on {hex_color}][{hex_color}]  [/{hex_color}][/on {hex_color}]"
            return ""

        home_badge = _badge(home["team"])
        away_badge = _badge(away["team"])
        widgets.append(Static(
            f"{home_badge} [bold]{home_name}[/bold]  "
            f"[bold yellow]{home_score}  –  {away_score}[/bold yellow]  "
            f"[bold]{away_name}[/bold] {away_badge}",
            classes="score-block",
        ))

        date_str = self.event.get("date", "")
        if date_str:
            widgets.append(Static(f"[dim]{_format_local_time(date_str)}[/dim]", classes="status-line"))

        status_text = format_live_status(self.event, show_clock=True) or f"[dim]{status.get('detail', 'Upcoming')}[/dim]"
        widgets.append(Static(status_text, id="status-clock", classes="status-line"))

        venue = competition.get("venue", {})
        stadium = venue.get("fullName", "")
        city = venue.get("address", {}).get("city", "")
        if stadium or city:
            location = f"{stadium} · {city}" if stadium and city else stadium or city
            widgets.append(Static(f"[dim]{location}[/dim]", classes="venue-line"))

        meta_parts = _extract_meta(self.event, self.summary)
        if meta_parts:
            widgets.append(Static(f"[dim]{' · '.join(meta_parts)}[/dim]", classes="venue-line"))

        return widgets, state, home_id, home_abbr, away_abbr

    def _build_live_widgets(self, state: str) -> list[Widget]:
        if state != "in":
            return []
        commentary = self.summary.get("commentary", [])
        recent = [c for c in reversed(commentary) if c.get("text")][:5]
        if not recent:
            return []
        lines = []
        for c in recent:
            minute = c.get("time", {}).get("displayValue", "")
            text = c.get("text", "")
            prefix = f"[dim]{minute:>3}'[/dim]  " if minute else "      "
            lines.append(f"{prefix}{text}")
        return [
            Static("── Live Updates", classes="section-label"),
            Static("\n".join(lines), id="commentary", classes="commentary"),
        ]

    def _build_timeline_widgets(self, state: str) -> list[Widget]:
        if state not in ("in", "post"):
            return []
        timeline_lines = build_timeline(self.event, self.summary)
        body = (
            Static("\n".join(timeline_lines), classes="timeline")
            if timeline_lines
            else Static("[dim]  No events yet[/dim]", classes="timeline")
        )
        return [Static("── Timeline", classes="section-label"), body]

    def _build_subs_widgets(self, state: str) -> list[Widget]:
        # Substitutions live in their own section under the timeline so tactical
        # changes don't dilute the goals/cards narrative above. Same single-column
        # vertical-scroll format as the timeline; club acronym at end identifies team.
        if state not in ("in", "post"):
            return []
        sub_lines = build_substitutions(self.event, self.summary)
        if not sub_lines:
            return []
        return [
            Static("── Substitutions", classes="section-label"),
            Static("\n".join(sub_lines), classes="subs-list"),
        ]

    def _build_lineups_widgets(self) -> list[Widget]:
        lineups = build_lineups(self.event, self.summary)
        if not lineups:
            return []
        widgets: list[Widget] = [Static("── Lineups", classes="section-label")]
        for lines in lineups:
            widgets.append(Static("\n".join(lines), classes="lineup"))
        return widgets

    def _build_stats_widgets(self, home_id: str, home_abbr: str, away_abbr: str) -> list[Widget]:
        teams_data = self.summary.get("boxscore", {}).get("teams", [])
        if len(teams_data) < 2:
            return []
        by_id = {str(td["team"]["id"]): td for td in teams_data}
        home_td = by_id.get(home_id, teams_data[0])
        away_td = next((t for t in teams_data if str(t["team"]["id"]) != home_id), teams_data[1])

        h = {s["name"]: s["displayValue"] for s in home_td.get("statistics", [])}
        a = {s["name"]: s["displayValue"] for s in away_td.get("statistics", [])}

        widgets: list[Widget] = [
            Static("── Stats", classes="section-label"),
            Static(
                f"[bold]{home_abbr}[/bold]                                         [bold]{away_abbr}[/bold]",
                classes="stats-header",
            ),
        ]
        for key, label, is_pct in STAT_KEYS:
            hv, av = h.get(key, "-"), a.get(key, "-")
            if hv == "-" and av == "-":
                continue
            home_bar, away_bar = _stat_bar(hv, av)
            hv_display = _fmt_stat(hv, is_pct)
            av_display = _fmt_stat(av, is_pct)
            widgets.append(Static(
                f"[bold]{hv_display:>6}[/bold] {home_bar}  [dim]{label:<12}[/dim]  {away_bar} [bold]{av_display:<6}[/bold]",
                classes="stat-row",
            ))
        return widgets
