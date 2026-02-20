from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_schema(schema_path: Path) -> dict[str, Any]:
    return json.loads(schema_path.read_text(encoding="utf-8"))


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
      - Optional JSON Schema validation (recommended)

    Raises ValueError/RuntimeError on failure.
    """
    p = Path(path)
    s = p.read_text(encoding="utf-8")

    obj = json.loads(
        s,
        parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f"Non-JSON constant: {x}")),
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

    # Optional schema validation
    if schema_path is not None:
        sp = Path(schema_path)
        schema = _load_schema(sp)
        _validate_schema(obj, schema)
    else:
        # Default: validate against bundled schema v1 if present
        bundled = Path(__file__).resolve().parents[1] / "report" / "schema" / "axiomiq_report.schema.v1.json"
        if bundled.exists():
            schema = _load_schema(bundled)
            _validate_schema(obj, schema)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="axiomiq-validate-json", description="Validate AxiomIQ JSON output (strict + schema).")
    ap.add_argument("path", help="Path to JSON report")
    ap.add_argument(
        "--schema",
        default=None,
        help="Optional schema path override. If omitted, uses bundled schema v1 when available.",
    )
    args = ap.parse_args(argv)

    validate_json(args.path, schema_path=args.schema)
    print(f"STRICT JSON OK: {Path(args.path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())