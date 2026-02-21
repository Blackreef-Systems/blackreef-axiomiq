from __future__ import annotations

from importlib import resources

import argparse
import json
from pathlib import Path
from typing import Any


def _load_schema(schema_path: Path) -> dict[str, Any]:
    return json.loads(schema_path.read_text(encoding="utf-8"))


def _load_schema_v1() -> dict[str, Any]:
    raw = (
        resources.files("axiomiq.report.schema")
        .joinpath("axiomiq_report.schema.v1.json")
        .read_text(encoding="utf-8")
    )
    return json.loads(raw)


def _validate_schema(payload: dict[str, Any], schema: dict[str, Any]) -> None:
    # jsonschema is a small, stable dependency and the cleanest way to do this.
    try:
        import jsonschema  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "jsonschema is required for schema validation. "
            "Install with: python -m pip install jsonschema"
        ) from e

    jsonschema.validate(instance=payload, schema=schema)


def validate_json(path: str | Path, *, schema_path: str | Path | None = None) -> None:
    """
    Strict JSON validation:
      - No NaN / Infinity (parse_constant trap)
      - Required top-level keys present
      - Shape sanity on the required sections
      - JSON Schema validation (bundled v1 by default)

    Raises ValueError/RuntimeError on failure.
    """
    p = Path(path)
    s = p.read_text(encoding="utf-8")

    obj = json.loads(
        s,
        parse_constant=lambda x: (_ for _ in ()).throw(
            ValueError(f"Non-JSON constant: {x}")
        ),
    )

    if not isinstance(obj, dict):
        raise ValueError("Top-level JSON must be an object")

    required = {"meta", "fleet", "focus", "notes"}
    missing = required.difference(obj.keys())
    if missing:
        raise ValueError(f"Missing required top-level keys: {sorted(missing)}")

    if not isinstance(obj["meta"], dict):
        raise ValueError("meta must be an object")
    if not isinstance(obj["fleet"], dict):
        raise ValueError("fleet must be an object")
    if not isinstance(obj["focus"], dict):
        raise ValueError("focus must be an object")
    if not isinstance(obj["notes"], list):
        raise ValueError("notes must be an array")

    # --- Schema validation (always enforced) ---
    if schema_path is None:
        schema = _load_schema_v1()
    else:
        schema = _load_schema(Path(schema_path))

    _validate_schema(obj, schema)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="axiomiq-validate-json",
        description="Validate AxiomIQ JSON output (strict + schema).",
    )
    ap.add_argument("path", help="Path to JSON report")
    ap.add_argument(
        "--schema",
        default=None,
        help="Optional schema path override. If omitted, uses bundled schema v1.",
    )
    args = ap.parse_args(argv)

    validate_json(args.path, schema_path=args.schema)
    print(f"STRICT JSON OK: {Path(args.path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())