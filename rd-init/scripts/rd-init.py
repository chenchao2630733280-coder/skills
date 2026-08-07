#!/usr/bin/env python3
"""rd-init：工作台加载器。

扫描 skills 目录全部 skill，生成工作台索引和完整性报告。

用法：
    python rd-init.py --skills-dir .agents/skills
    python rd-init.py --skills-dir . --output .workbench-index.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


# ── skill 分类规则 ────────────────────────────────────────────

PRODUCT_PIPELINE_SKILLS = {
    "brainstorm-product-feature", "generate-system-prd", "prd-quality-checker",
    "plan-system-implementation", "generate-prototype", "generate-html-pages",
    "generate-html-mobile", "generate-html-pc-admin", "generate-portal",
    "implement-frontend", "implement-backend", "implement-data-layer",
    "integrate-system", "test-and-harden-system", "package-and-deploy-system",
    "web-static-deploy", "product-pipeline-master", "build-working-system",
    "frontend-design", "ruanzhu-doc-generator", "bid-functional-solution",
    "screenshot-operation-manual",
}

GAME_PIPELINE_SKILLS = {
    "game-topic-brainstorm", "game-blueprint", "game-spec", "game-art-spec",
    "game-asset-forge", "game-code-forge", "game-integrate", "game-polish",
    "game-quality-gate", "game-forge-master", "short-drama-game-adapt",
}

DRAMA_SKILLS = {
    "ai-short-drama-topic-planner", "ai-short-drama-project-development",
}

# 工作台元 skill：加载/索引/校验工作台自身，不属于任何业务流水线
WORKBENCH_META_SKILLS = {
    "rd-init",
}

# Agent 体系层按维度细分
AGENT_SYSTEM_DIMENSIONS = {
    "Model": ["prompt-registry"],
    "Skill": ["agent-builder"],
    "Tool": ["tool-git-ops", "tool-ci-ops", "tool-deploy-ops", "tool-db-ops", "tool-monitor-ops"],
    "Planning": ["task-planner", "replanner"],
    "Memory": ["project-knowledge-base", "failure-casebook", "session-snapshot"],
    "Context": ["codebase-rag"],
    "Workflow": ["workflow-runtime"],
    "Agent Runtime": ["skill-runtime", "agent-runtime-exec", "agent-orchestrator"],
    "Evaluation": ["skill-auditor"],
    "Data": ["skill-usage-tracker", "adaptive-tuner"],
    "Guardrail": ["guardrail", "diff-reviewer"],
    "Engineering": ["code-review", "debug-fix", "refactor"],
}


def classify_skill(name: str) -> str:
    if name in PRODUCT_PIPELINE_SKILLS:
        return "product"
    if name in GAME_PIPELINE_SKILLS:
        return "game"
    if name in DRAMA_SKILLS:
        return "drama"
    if name in WORKBENCH_META_SKILLS:
        return "workbench"
    for dim, skills in AGENT_SYSTEM_DIMENSIONS.items():
        if name in skills:
            return "agent-system"
    return "unknown"


def get_agent_dimension(name: str) -> str:
    for dim, skills in AGENT_SYSTEM_DIMENSIONS.items():
        if name in skills:
            return dim
    return ""


# ── frontmatter 解析 ─────────────────────────────────────────

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


def parse_frontmatter(content: str) -> dict[str, str]:
    m = FRONTMATTER_RE.match(content)
    if not m:
        return {}
    fm_text = m.group(1)
    result = {}
    for line in fm_text.split("\n"):
        # 支持 name: value / name: "value" / name: 'value'
        m2 = re.match(r'^(\w+)\s*:\s*["\']?(.*?)["\']?\s*$', line)
        if m2:
            result[m2.group(1)] = m2.group(2)
    return result


# ── references 路径提取 ──────────────────────────────────────

REF_RE = re.compile(r"references/[\w/\.\-]+\.md")


def extract_references(content: str) -> list[str]:
    return sorted(set(REF_RE.findall(content)))


# ── skill 扫描 ───────────────────────────────────────────────

def build_refs_index(skills_dir: Path) -> dict[str, list[str]]:
    """构建工作台级 references 索引：{文件名: [所属 skill 目录名]}。

    用于校验跨 skill 目录的 references 引用。
    """
    index: dict[str, list[str]] = {}
    for item in sorted(skills_dir.iterdir(), key=lambda p: p.name):
        if not item.is_dir():
            continue
        if item.name.startswith(".") or item.name.startswith("_"):
            continue
        refs_dir = item / "references"
        if not refs_dir.is_dir():
            continue
        for ref_file in refs_dir.rglob("*.md"):
            index.setdefault(ref_file.name, []).append(item.name)
    return index


def scan_skill(skill_dir: Path, refs_index: dict[str, list[str]] | None = None) -> dict[str, Any]:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return {}

    content = skill_md.read_text(encoding="utf-8", errors="ignore")
    fm = parse_frontmatter(content)
    name = fm.get("name", skill_dir.name)
    description = fm.get("description", "")
    category = classify_skill(name)
    has_runtime = (skill_dir / "runtime.yaml").exists()
    refs = extract_references(content)

    # 校验 references 路径(三种合法位置：skill 目录内 / _shared/references/ / 跨 skill 目录)
    ref_warnings = []
    for ref in refs:
        ref_path = skill_dir / ref
        shared_path = skill_dir.parent / "_shared" / "references" / Path(ref).name
        cross_dir_exists = (
            refs_index is not None
            and Path(ref).name in refs_index
            and skill_dir.name not in refs_index[Path(ref).name]  # 排除自身目录
        )
        if not ref_path.exists() and not shared_path.exists() and not cross_dir_exists:
            ref_warnings.append(ref)

    warnings = []
    if not fm.get("name"):
        warnings.append("frontmatter 缺少 name 字段")
    if not fm.get("description"):
        warnings.append("frontmatter 缺少 description 字段")
    for ref in ref_warnings:
        warnings.append(f"references 路径不存在: {ref}")

    return {
        "name": name,
        "dir": skill_dir.name,
        "description": description,
        "category": category,
        "agent_dimension": get_agent_dimension(name) if category == "agent-system" else "",
        "has_runtime_yaml": has_runtime,
        "references": refs,
        "warnings": warnings,
    }


def scan_workbench(skills_dir: Path) -> dict[str, Any]:
    # 先构建工作台级 references 索引，供跨 skill 目录引用校验
    refs_index = build_refs_index(skills_dir)

    skills = []
    for item in sorted(skills_dir.iterdir(), key=lambda p: p.name):
        if not item.is_dir():
            continue
        if item.name.startswith(".") or item.name.startswith("_") or item.name == "docs":
            continue
        skill_md = item / "SKILL.md"
        if not skill_md.exists():
            continue
        info = scan_skill(item, refs_index)
        if info:
            skills.append(info)

    # 分类统计
    categories = {}
    for s in skills:
        cat = s["category"]
        categories[cat] = categories.get(cat, 0) + 1

    # 收集所有警告
    all_warnings = []
    critical = 0
    warning_count = 0
    for s in skills:
        for w in s["warnings"]:
            all_warnings.append({"skill": s["name"], "warning": w})
            if "缺少" in w and "name" in w:
                critical += 1
            else:
                warning_count += 1

    return {
        "schemaVersion": "1.0",
        "scanned_at": datetime.now().isoformat(timespec="seconds"),
        "skills_dir": str(skills_dir),
        "total_skills": len(skills),
        "categories": categories,
        "runtime_yaml_count": sum(1 for s in skills if s["has_runtime_yaml"]),
        "warning_count": warning_count,
        "critical_count": critical,
        "skills": skills,
        "warnings": all_warnings,
    }


# ── 报告输出 ─────────────────────────────────────────────────

CATEGORY_LABELS = {
    "product": "产研业务层",
    "game": "游戏流水线",
    "drama": "AI 短剧",
    "workbench": "工作台元 skill",
    "agent-system": "Agent 体系层",
    "unknown": "未分类",
}


def print_report(data: dict[str, Any]) -> None:
    print(f"工作台加载完成")
    print(f"扫描目录：{data['skills_dir']}")
    print(f"扫描时间：{data['scanned_at']}")
    print(f"\nSkill 总数：{data['total_skills']}")
    print(f"runtime.yaml 声明：{data['runtime_yaml_count']}")

    print(f"\n分类统计：")
    for cat, count in sorted(data["categories"].items(), key=lambda x: -x[1]):
        label = CATEGORY_LABELS.get(cat, cat)
        print(f"  {label}：{count}")

    # Agent 体系层维度细分
    agent_skills = [s for s in data["skills"] if s["category"] == "agent-system"]
    if agent_skills:
        print(f"\nAgent 体系层维度：")
        dim_counts = {}
        for s in agent_skills:
            dim = s["agent_dimension"] or "未归类"
            dim_counts[dim] = dim_counts.get(dim, 0) + 1
        for dim, count in sorted(dim_counts.items()):
            print(f"  {dim}：{count}")

    # 列出全部 skill
    print(f"\nSkill 清单：")
    for cat in ["workbench", "product", "game", "drama", "agent-system", "unknown"]:
        cat_skills = [s for s in data["skills"] if s["category"] == cat]
        if not cat_skills:
            continue
        label = CATEGORY_LABELS.get(cat, cat)
        print(f"\n  [{label}]")
        for s in cat_skills:
            runtime_tag = " (runtime)" if s["has_runtime_yaml"] else ""
            warning_tag = " ⚠" if s["warnings"] else ""
            desc = s["description"][:60] + "..." if len(s["description"]) > 60 else s["description"]
            print(f"    {s['name']}{runtime_tag}{warning_tag} — {desc}")

    # 警告
    if data["warnings"]:
        print(f"\n完整性警告（{data['warning_count']} WARNING, {data['critical_count']} CRITICAL）：")
        for w in data["warnings"]:
            print(f"  ⚠ {w['skill']}: {w['warning']}")
    else:
        print(f"\n完整性校验：全部通过")

    print(f"\n索引文件：{data.get('index_file', '.workbench-index.json')}")


# ── 主流程 ────────────────────────────────────────────────────

def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="rd-init：工作台加载器，扫描 skill 目录生成索引和完整性报告"
    )
    parser.add_argument("--skills-dir", default=".agents/skills", help="skills 工作台根目录")
    parser.add_argument("--output", default=".workbench-index.json", help="索引文件输出路径")
    parser.add_argument("--quiet", action="store_true", help="只输出索引文件，不打印报告")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    skills_dir = Path(args.skills_dir).expanduser().resolve()

    if not skills_dir.exists():
        raise SystemExit(f"skills 目录不存在：{skills_dir}")

    data = scan_workbench(skills_dir)

    # 写入索引文件
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    data["index_file"] = str(output_path)

    if not args.quiet:
        print_report(data)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
