# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv run tapu              # Run the TUI
uv run pytest            # Run all tests
uv run pytest tests/test_config.py::test_name -v   # Run a single test
uv run ruff check src    # Lint
uv run ruff format src   # Format
```

## Architecture

**Entry point:** `src/tapu/cli.py` → `TapuApp` (in `app.py`) → pushes `DashboardScreen` on mount.

**Screen stack (Textual):** Screens are pushed/popped via `app.push_screen` / `app.pop_screen`:
- `DashboardScreen` — league cards grid, 60s auto-refresh via `set_interval()`
- `LeagueScreen` — tabbed: matches by day, standings, bracket, related tournaments
- `MatchScreen` — detailed match stats, goals, cards, progress bars
- `MatchDayScreen` — all matches for a specific date
- `WCGroupScreen` — World Cup group stage standings

**Config:** `leagues.toml` at repo root defines all leagues. `src/tapu/config.py` loads it into frozen `League` dataclasses. Adding a league is a one-line TOML entry — no code changes needed. Key `League` fields:
- `slug` — ESPN API identifier (e.g. `eng.1`, `fifa.world`)
- `related` — list of `{name, slug}` inline tables, drives tournament tabs in `LeagueScreen`
- `is_tournament`, `has_bracket` — controls which tabs/widgets appear
- `relegation_spots`, `promotion_spots` — drives standings row highlighting

**API client** (`src/tapu/api/client.py`): `ESPNClient` wraps the public ESPN API with a two-layer cache — in-memory (3s TTL for scoreboard, 30s default) and disk (`~/.cache/tapu/`, 1h TTL for standings/brackets). All methods are `async`. Key methods:
- `get_scoreboard(slug)` — today's matches (in-memory cache, 3s TTL)
- `get_scoreboard_daterange(slug, start, end)` — date-range fetch (disk cache, 1h TTL)
- `get_tournament_events(slug)` / `get_knockout_events(slug)` — full season fetches
- `get_standings(slug)`, `get_match_summary(event_id)`
- `clear_cache()` — clears in-memory cache only (disk cache persists)

ESPN occasionally returns a schema template string instead of JSON — `ESPNClient` retries once on `JSONDecodeError` to handle this.

**Widgets** live in `src/tapu/widgets/`. Each widget is self-contained and communicates via custom `Message` subclasses (e.g. `LeagueCard.Selected`, `MatchCard.Selected`, `GroupCard.Selected`) — no direct parent references. Background data fetches use Textual's `@work` decorator to avoid blocking the UI thread.

**CSS** is defined inline as `DEFAULT_CSS` class variables on each widget/screen. No external CSS files. Theme uses Textual's built-in color variables (`$primary`, `$surface`, `$success`, `$warning`).

**Tests** use `pytest-asyncio` with `asyncio_mode = "auto"`. Textual widget tests use `app.run_test()` as an async context manager. The `conftest.py` provides `sample_scoreboard` and `sample_standings` fixtures with realistic ESPN API responses.

**Optional dependency:** `team_logo.py` renders team badges via `PIL` + `rich_pixels`. Falls back silently if either is unavailable.

## ESPN API Slugs

League slugs (e.g. `esp.1`, `eng.1`) and tournament slugs (e.g. `esp.copa_del_rey`, `eng.fa`) map directly to ESPN's public API at `https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard`. Standings use a different base: `https://site.web.api.espn.com/apis/v2/sports/soccer/{slug}/standings`. Verify new slugs with curl before adding them to `leagues.toml`.
