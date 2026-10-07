from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_config(path: str | Path | None = None) -> dict:
    config_path = Path(path) if path else ROOT / "config" / "study.yaml"
    with config_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)
