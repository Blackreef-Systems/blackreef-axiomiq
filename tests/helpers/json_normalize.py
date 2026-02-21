from __future__ import annotations

from copy import deepcopy
from typing import Any


def normalize_report_json(data: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize fields that are expected to vary run-to-run so golden comparisons
    are stable and meaningful.
    """
    d = deepcopy(data)

    # meta fields that vary
    meta = d.get("meta", {})
    if isinstance(meta, dict):
        meta["generated_at"] = "<redacted>"
        # keep decision_version/schema_version; those are contract-critical

        # run_config may contain paths; normalize if present
        rc = meta.get("run_config")
        if isinstance(rc, dict):
            if "config" in rc:
                rc["config"] = "<redacted>"
            # Optional: if you ever include absolute paths in run_config
            for k in ("input", "out", "snapshot", "json_out"):
                if k in rc:
                    rc[k] = "<redacted>"

    # Fleet delta ordering can vary if upstream dict/set usage exists.
    fleet = d.get("fleet", {})
    if isinstance(fleet, dict):
        delta = fleet.get("delta")
        if isinstance(delta, list):
            fleet["delta"] = sorted(delta)

    # notes ordering: keep stable
    notes = d.get("notes")
    if isinstance(notes, list):
        d["notes"] = [str(x) for x in notes]

    return d