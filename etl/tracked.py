from pathlib import Path

import yaml

TRACKED_FILE = Path(__file__).resolve().parent / "tracked_games.yml"


def load_tracked(path: Path | None = None) -> list[dict]:
    data = yaml.safe_load((path or TRACKED_FILE).read_text(encoding="utf-8"))
    return data["games"]
