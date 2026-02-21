from __future__ import annotations

import json
from pathlib import Path

import pytest

from axiomiq.tools import validate_json as vj


def _write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, indent=2, allow_nan=False), encoding="utf-8")


def test_validate_json_accepts_matching_schema_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Minimal schema that requires the fields we care about for this test.
    minimal_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["meta", "fleet", "focus", "notes"],
        "properties": {
            "meta": {
                "type": "object",
                "required": ["schema_version"],
                "properties": {"schema_version": {"type": "string"}},
            },
            "fleet": {"type": "object"},
            "focus": {"type": "object"},
            "notes": {"type": "array"},
        },
        "additionalProperties": True,
    }

    monkeypatch.setattr(vj, "_load_schema_text", lambda: json.dumps(minimal_schema))

    report = {
        "meta": {"schema_version": vj.EXPECTED_SCHEMA_VERSION},
        "fleet": {},
        "focus": {},
        "notes": [],
    }

    p = tmp_path / "report.json"
    _write_json(p, report)

    result = vj.validate_json(p)
    assert result.ok is True
    assert result.schema_version == vj.EXPECTED_SCHEMA_VERSION


def test_validate_json_rejects_mismatched_schema_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    minimal_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["meta", "fleet", "focus", "notes"],
        "properties": {
            "meta": {
                "type": "object",
                "required": ["schema_version"],
                "properties": {"schema_version": {"type": "string"}},
            },
            "fleet": {"type": "object"},
            "focus": {"type": "object"},
            "notes": {"type": "array"},
        },
        "additionalProperties": True,
    }

    monkeypatch.setattr(vj, "_load_schema_text", lambda: json.dumps(minimal_schema))

    report = {
        "meta": {"schema_version": "v999"},
        "fleet": {},
        "focus": {},
        "notes": [],
    }

    p = tmp_path / "report.json"
    _write_json(p, report)

    with pytest.raises(vj.SchemaVersionMismatch):
        vj.validate_json(p)