#!/usr/bin/env python3
"""Validate a pet-health simulation session JSON with no external dependencies."""

from __future__ import annotations

import json
import sys
from pathlib import Path

STATES = {
    "WELCOME", "SELECT_PET", "COLLECT_COMPLAINT",
    "CONFIRM_EXTRACTED_ISSUES", "GLOBAL_EMERGENCY_SCREEN",
    "CONTEXTUAL_EMERGENCY_SCREEN", "DYNAMIC_INTERVIEW",
    "CONFIRM_SUMMARY", "RISK_RESULT", "FOLLOW_UP_TRACKING",
    "HANDOFF", "CLOSED",
}
RISKS = {"UNASSESSED", "L1", "L2", "L3", "L4", "L5"}


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/validate_session.py path/to/session.json")
        return 2

    path = Path(sys.argv[1])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"INVALID JSON: {exc}")
        return 1

    errors: list[str] = []
    if data.get("state") not in STATES:
        errors.append(f"Unknown state: {data.get('state')!r}")
    if data.get("risk_level") not in RISKS:
        errors.append(f"Unknown risk_level: {data.get('risk_level')!r}")
    if not isinstance(data.get("complaints", []), list):
        errors.append("complaints must be a list")
    if not isinstance(data.get("emergency_flags", []), list):
        errors.append("emergency_flags must be a list")
    if data.get("emergency_flags") and data.get("risk_level") != "L5":
        errors.append("Sessions with emergency_flags should use L5 in this simulator.")
    if data.get("risk_level") == "L5" and data.get("state") not in {"HANDOFF", "CLOSED"}:
        errors.append("L5 sessions should route to HANDOFF or CLOSED.")

    if errors:
        print("INVALID")
        for item in errors:
            print(f"- {item}")
        return 1

    print("VALID")
    print(f"- state: {data['state']}")
    print(f"- risk_level: {data['risk_level']}")
    print(f"- complaints: {len(data.get('complaints', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
