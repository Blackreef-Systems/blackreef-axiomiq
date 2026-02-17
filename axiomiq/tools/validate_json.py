from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def validate_json(path: str | Path) -> dict[str, Any]:
    """
    Strict JSON validation:
      - Reject NaN / Infinity (JSON non-compliant constants)
      - Require top-level keys: meta, fleet, focus, notes
      - Basic shape sanity checks for those sections
    Returns the parsed JSON object (dict) on success.
    """
    p = Path(path)
    s = p.read_text(encoding="utf-8")

    obj = json.loads(
        s,
        parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f"Non-JSON constant: {x}")),
    )

    if not isinstance(obj, dict):
        raise ValueError("Top-level JSON must be an object (dict)")

    # Required top-level keys
    required = ("meta", "fleet", "focus", "notes")
    for k in required:
        if k not in obj:
            raise ValueError(f"Missing top-level key: {k}")

    # Basic section shape sanity
    if not isinstance(obj["meta"], dict):
        raise ValueError("meta must be an object (dict)")
    if not isinstance(obj["fleet"], dict):
        raise ValueError("fleet must be an object (dict)")
    if not isinstance(obj["focus"], dict):
        raise ValueError("focus must be an object (dict)")
    if not isinstance(obj["notes"], list):
        raise ValueError("notes must be an array (list)")

    # Optional: if fleet.table exists, ensure it's a list (stable expectation for consumers)
    fleet_table = obj["fleet"].get("table", None)
    if fleet_table is not None and not isinstance(fleet_table, list):
        raise ValueError("fleet.table must be an array (list) if present")

    return obj


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="axiomiq-validate-json",
        description="Validate AxiomIQ JSON output (strict: no NaN/Infinity; required keys).",
    )
    ap.add_argument("path", help="Path to JSON report")
    args = ap.parse_args(argv)

    validate_json(args.path)
    print(f"STRICT JSON OK: {Path(args.path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())