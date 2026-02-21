from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import importlib.resources as resources

try:
    import jsonschema
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "jsonschema is required for schema validation. Install with: pip install jsonschema"
    ) from e


from axiomiq.schema_constants import (
    SCHEMA_VERSION,
    SCHEMA_RESOURCE_PACKAGE,
    SCHEMA_RESOURCE_NAME,
)

EXPECTED_SCHEMA_VERSION = SCHEMA_VERSION


class StrictJsonError(ValueError):
    """Raised when JSON is invalid or contains forbidden constants (NaN/Infinity)."""


class SchemaVersionMismatch(ValueError):
    """Raised when meta.schema_version does not match EXPECTED_SCHEMA_VERSION."""


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    schema_version: str


def _reject_nonfinite_constants(value: str) -> Any:
    """
    json.loads hook: reject NaN/Infinity/-Infinity.
    Python's stdlib json will otherwise accept them and produce floats.
    """
    raise StrictJsonError(f"Forbidden JSON constant encountered: {value}")


def _load_schema_text() -> str:
    """
    Load the bundled schema from package resources (no filesystem dependency).
    """
    return resources.files(SCHEMA_RESOURCE_PACKAGE).joinpath(SCHEMA_RESOURCE_NAME).read_text(
        encoding="utf-8"
    )


def _parse_strict_json(text: str) -> dict[str, Any]:
    """
    Strict JSON parsing:
      - reject NaN/Infinity
      - reject invalid JSON
    """
    try:
        data = json.loads(text, parse_constant=_reject_nonfinite_constants)
    except StrictJsonError:
        raise
    except json.JSONDecodeError as e:
        raise StrictJsonError(f"Invalid JSON: {e.msg} (line {e.lineno}, col {e.colno})") from e

    if not isinstance(data, dict):
        raise StrictJsonError("Top-level JSON must be an object.")
    return data


def _extract_schema_version(data: dict[str, Any]) -> str:
    meta = data.get("meta")
    if not isinstance(meta, dict):
        raise SchemaVersionMismatch("Missing or invalid 'meta' object.")
    v = meta.get("schema_version")
    if not isinstance(v, str) or not v.strip():
        raise SchemaVersionMismatch("Missing or invalid 'meta.schema_version' (must be a non-empty string).")
    return v.strip()


def validate_json(path: str | Path, *, expected_schema_version: str = EXPECTED_SCHEMA_VERSION) -> ValidationResult:
    """
    Validate an AxiomIQ report JSON file by:
      1) strict JSON parse (reject NaN/Infinity)
      2) JSON Schema validation (bundled schema)
      3) hard-lock meta.schema_version to expected version
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))

    text = p.read_text(encoding="utf-8")
    data = _parse_strict_json(text)

    # ---- Extract + hard-lock schema version FIRST ----
    actual = _extract_schema_version(data)
    if actual != expected_schema_version:
        raise SchemaVersionMismatch(
            f"Schema version mismatch: expected '{expected_schema_version}', got '{actual}'."
        )

    # ---- Then validate against bundled schema ----
    schema_text = _load_schema_text()
    schema = _parse_strict_json(schema_text)
    jsonschema.validate(instance=data, schema=schema)

    return ValidationResult(ok=True, schema_version=actual)

def main() -> None:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Validate AxiomIQ JSON report.")
    parser.add_argument("path", help="Path to JSON report file")
    args = parser.parse_args()

    try:
        validate_json(args.path)
    except Exception as e:
        print(f"ERROR: {e}")
        raise SystemExit(1) from e

    print("OK: JSON validation passed (strict + schema).")
    raise SystemExit(0)