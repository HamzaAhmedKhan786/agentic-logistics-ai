from __future__ import annotations

import json
from pathlib import Path

from models.schemas import PlanResponse


OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"


def save_checkpoint(response: PlanResponse) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    target = OUTPUT_DIR / f"{response.run_id}.json"
    target.write_text(response.model_dump_json(indent=2), encoding="utf-8")
    return target


def load_checkpoint(run_id: str) -> dict:
    target = OUTPUT_DIR / f"{run_id}.json"
    return json.loads(target.read_text(encoding="utf-8"))
