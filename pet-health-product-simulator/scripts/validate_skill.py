#!/usr/bin/env python3
"""Validate the local Codex skill package structure using the standard library."""

from __future__ import annotations

import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md must start with YAML frontmatter.")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("SKILL.md frontmatter is not closed.")
    block = text[4:end]
    values: dict[str, str] = {}
    for raw in block.splitlines():
        if not raw.strip():
            continue
        if ":" not in raw:
            raise ValueError(f"Unsupported frontmatter line: {raw}")
        key, value = raw.split(":", 1)
        values[key.strip()] = value.strip()
    return values


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    skill_files = [p for p in root.rglob("*") if p.is_file() and p.name.lower() == "skill.md"]
    errors: list[str] = []

    if len(skill_files) != 1:
        errors.append(f"Expected exactly one SKILL.md, found {len(skill_files)}.")
    else:
        skill = skill_files[0]
        try:
            meta = parse_frontmatter(skill.read_text(encoding="utf-8"))
            for required in ("name", "description"):
                if not meta.get(required):
                    errors.append(f"Missing required frontmatter field: {required}.")
            if meta.get("name") and not NAME_RE.fullmatch(meta["name"]):
                errors.append("name must use lowercase letters, digits, and hyphens.")
            if len(meta.get("description", "")) < 40:
                errors.append("description is too vague for reliable skill discovery.")
        except Exception as exc:
            errors.append(str(exc))

    for required in [
        root / "agents" / "openai.yaml",
        root / "references" / "product-contract.md",
        root / "references" / "dialogue-protocol.md",
        root / "references" / "safety-and-triage.md",
        root / "references" / "risk-model.md",
    ]:
        if not required.exists():
            errors.append(f"Missing expected file: {required.relative_to(root)}")

    if errors:
        print("INVALID")
        for item in errors:
            print(f"- {item}")
        return 1

    print("VALID")
    print(f"- skill: {skill_files[0].relative_to(root)}")
    print("- required frontmatter: name, description")
    print("- optional Codex metadata: agents/openai.yaml")
    print("- progressive disclosure references: present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
