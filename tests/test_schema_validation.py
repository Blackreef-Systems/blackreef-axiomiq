from __future__ import annotations

import json
from pathlib import Path

from axiomiq.tools.validate_json import validate_json


def test_bundled_schema_validates_sample_json(tmp_path: Path) -> None:
    # Minimal payload that must satisfy schema v1
    payload = {
        "meta": {
            "generated_at": "2026-01-01 00:00",
            "coverage": "Coverage: N/A",
            "decision_version": "dev",
            "schema_version": "v1",
        },
        "fleet": {"verdict": "OK", "delta": [], "table": []},
        "focus": {"engine_id": "DG1", "health_score": 90.0, "risks": []},
        "notes": [],
    }

    out = tmp_path / "check.json"
    out.write_text(json.dumps(payload, allow_nan=False), encoding="utf-8")

    # If bundled schema exists, this will validate against it automatically.
    validate_json(out)