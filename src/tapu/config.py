import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class League:
    slug: str
    name: str
    full_name: str
    color: str = "#ffffff"


def load_leagues(path: Path | None = None) -> list[League]:
    if path is None:
        path = Path(__file__).parent.parent.parent / "leagues.toml"
    with path.open("rb") as f:
        data = tomllib.load(f)
    return [League(**entry) for entry in data["leagues"]]
