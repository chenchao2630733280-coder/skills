#!/usr/bin/env python3
"""rd-init：产研项目脚手架初始化。

创建产研流水线标准目录结构，生成 project-brief.json 和 project.yaml，
为 product-pipeline-master 流水线提供起始输入。

用法：
    python rd-init.py --target-dir . --brief "项目名称：xxx；核心功能：xxx"
    python rd-init.py --target-dir . --brief-file docs/FEATURE_BRAINSTORM.md
    python rd-init.py --target-dir . --brief-json '{"project_name":"xxx",...}'
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


# ── 标准目录结构 ──────────────────────────────────────────────

STANDARD_DIRS = [
    "docs",
    "output/spec",
    "output/prototype",
    "output/site/pc",
    "output/site/mobile",
    "output/site/assets",
    "output/build",
]


# ── 工具函数 ──────────────────────────────────────────────────

def require_yaml() -> None:
    if yaml is None:
        raise SystemExit(
            "缺少 PyYAML 依赖，无法生成 project.yaml。\n"
            "请先执行：python -m pip install pyyaml\n"
            "然后重新运行初始化脚本。"
        )


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def write_text(path: Path, content: str, overwrite: bool = False, dry_run: bool = False) -> bool:
    """写入文件，返回是否实际写入。"""
    if path.exists() and not overwrite:
        return False
    if dry_run:
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def save_yaml(path: Path, data: dict[str, Any], overwrite: bool = False, dry_run: bool = False) -> bool:
    require_yaml()
    if path.exists() and not overwrite:
        return False
    if dry_run:
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return True


def save_json(path: Path, data: dict[str, Any], overwrite: bool = False, dry_run: bool = False) -> bool:
    if path.exists() and not overwrite:
        return False
    if dry_run:
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def split_list(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    parts = re.split(r"[、,，;；\n]+", value)
    return [p.strip(" -\t") for p in parts if p.strip(" -\t")]


def extract_field(raw: str, labels: list[str]) -> str:
    for label in labels:
        # 匹配行首、换行后、或分号后的字段标签
        pattern = rf"(?:^|\n|[；;])\s*{re.escape(label)}\s*[:：]\s*(.+)"
        m = re.search(pattern, raw)
        if m:
            value = m.group(1).strip()
            # 截断到下一个分号(单行多字段场景)
            for sep in ["；", ";"]:
                if sep in value:
                    return value.split(sep)[0].strip()
            return value
    return ""


# ── 需求解析 ──────────────────────────────────────────────────

def infer_brief_from_text(raw: str) -> dict[str, Any]:
    project_name = extract_field(raw, ["项目名称", "产品名称", "系统名称", "名称"])
    industry = extract_field(raw, ["行业", "行业领域"])
    product_type = extract_field(raw, ["产品类型", "系统类型"])
    target_users = split_list(extract_field(raw, ["目标用户", "用户", "使用者"]))
    core_value = extract_field(raw, ["核心价值", "产品价值", "价值"])
    business_goal = extract_field(raw, ["业务目标", "目标"])
    features = split_list(extract_field(raw, ["核心功能", "主要功能", "功能", "模块"]))
    tech_req = extract_field(raw, ["技术要求", "技术方向", "技术栈"])

    return {
        "project_name": project_name or "待确认项目名称",
        "industry": industry or "待确认",
        "product_type": product_type or "待确认",
        "target_users": target_users or ["待确认"],
        "core_value": core_value or "待确认",
        "business_goal": business_goal or "待确认",
        "features": features or ["待确认"],
        "tech_requirement": tech_req or "待确认",
        "raw_brief": raw.strip(),
    }


def normalize_brief(data: dict[str, Any]) -> dict[str, Any]:
    raw = data.get("raw_brief") or json.dumps(data, ensure_ascii=False, indent=2)
    tech_stack = data.get("tech_stack") or {}
    if isinstance(tech_stack, str):
        tech_stack = {"notes": tech_stack}

    return {
        "project_name": data.get("project_name") or data.get("name") or "待确认项目名称",
        "industry": data.get("industry") or "待确认",
        "product_type": data.get("product_type") or "待确认",
        "target_users": split_list(data.get("target_users")) or ["待确认"],
        "core_value": data.get("core_value") or "待确认",
        "business_goal": data.get("business_goal") or "待确认",
        "features": split_list(data.get("features")) or ["待确认"],
        "optional_features": split_list(data.get("optional_features")) or [],
        "future_features": split_list(data.get("future_features")) or [],
        "tech_stack": tech_stack,
        "tech_requirement": data.get("tech_requirement") or data.get("technical_requirement") or "待确认",
        "raw_brief": str(raw).strip(),
    }


def load_brief(args: argparse.Namespace) -> dict[str, Any]:
    if args.brief_json:
        data = json.loads(args.brief_json)
        data.setdefault("raw_brief", json.dumps(data, ensure_ascii=False, indent=2))
        return normalize_brief(data)

    if args.brief_file:
        if args.brief_file == "-":
            raw = sys.stdin.read()
        else:
            raw = Path(args.brief_file).read_text(encoding="utf-8")
        return normalize_brief(infer_brief_from_text(raw))

    if args.brief:
        if args.brief == "-":
            raw = sys.stdin.read()
        else:
            raw = args.brief
        return normalize_brief(infer_brief_from_text(raw))

    raise SystemExit("请通过 --brief-json、--brief-file 或 --brief 传入初步需求。")


# ── 目录创建 ──────────────────────────────────────────────────

def create_standard_dirs(target_dir: Path, dry_run: bool = False) -> list[str]:
    """创建标准目录结构，返回已创建的目录列表。"""
    created: list[str] = []
    for rel in STANDARD_DIRS:
        d = target_dir / rel
        if d.exists():
            continue
        if not dry_run:
            d.mkdir(parents=True, exist_ok=True)
        # 创建 .gitkeep 保持空目录
        gitkeep = d / ".gitkeep"
        if not gitkeep.exists():
            if not dry_run:
                gitkeep.write_text("", encoding="utf-8")
        created.append(rel + "/")
    return created


# ── 产出文件生成 ──────────────────────────────────────────────

def gen_project_brief(brief: dict[str, Any]) -> dict[str, Any]:
    """生成 project-brief.json 的内容。"""
    return {
        "schemaVersion": "1.0",
        "project_name": brief["project_name"],
        "industry": brief["industry"],
        "product_type": brief["product_type"],
        "target_users": brief["target_users"],
        "core_value": brief["core_value"],
        "business_goal": brief["business_goal"],
        "features": brief["features"],
        "optional_features": brief.get("optional_features", []),
        "future_features": brief.get("future_features", []),
        "tech_stack": brief.get("tech_stack", {}),
        "tech_requirement": brief["tech_requirement"],
        "raw_brief": brief["raw_brief"],
        "initialized_at": datetime.now().isoformat(timespec="seconds"),
        "next_step": "brainstorm-product-feature",
    }


def gen_project_yaml(brief: dict[str, Any]) -> dict[str, Any]:
    """生成 project.yaml 的内容。"""
    return {
        "project": {
            "name": brief["project_name"],
            "description": brief.get("core_value") or brief.get("raw_brief") or "待确认",
            "status": "初始化完成，待需求澄清",
        },
        "business": {
            "industry": brief["industry"],
            "product_type": brief["product_type"],
            "target_users": brief["target_users"],
            "core_value": brief["core_value"],
            "business_goal": brief["business_goal"],
        },
        "features": {
            "core": brief["features"],
            "optional": brief.get("optional_features", []),
            "future": brief.get("future_features", []),
        },
        "tech_stack": {
            "frontend": (brief.get("tech_stack") or {}).get("frontend") or "待确认",
            "backend": (brief.get("tech_stack") or {}).get("backend") or "待确认",
            "database": (brief.get("tech_stack") or {}).get("database") or "待确认",
            "deployment": (brief.get("tech_stack") or {}).get("deployment") or "待确认",
        },
        "pipeline": {
            "orchestrator": "product-pipeline-master",
            "current_stage": "rd-init",
            "next_stage": "brainstorm-product-feature",
            "stages": [
                "rd-init",
                "brainstorm-product-feature",
                "generate-system-prd",
                "prd-quality-checker",
                "generate-prototype",
                "generate-html-pages",
                "generate-portal",
                "plan-system-implementation",
                "implement-frontend",
                "implement-backend",
                "implement-data-layer",
                "integrate-system",
                "test-and-harden-system",
                "package-and-deploy-system",
            ],
        },
        "output": {
            "spec_dir": "output/spec/",
            "prototype_dir": "output/prototype/",
            "site_dir": "output/site/",
            "build_dir": "output/build/",
            "docs_dir": "docs/",
        },
        "project_initialization": {
            "initialized_by_skill": "rd-init",
            "initialized_at": datetime.now().isoformat(timespec="seconds"),
            "brief_file": "docs/project-brief.json",
        },
    }


def gen_feature_brainstorm_md(brief: dict[str, Any]) -> str:
    """生成 FEATURE_BRAINSTORM.md 的内容。"""
    return f"""# 需求简报

## 项目名称

{brief['project_name']}

## 行业与产品类型

- 行业：{brief['industry']}
- 产品类型：{brief['product_type']}

## 初步需求

{brief['raw_brief'] or '待确认'}

## 目标用户

{chr(10).join('- ' + x for x in brief['target_users'])}

## 核心价值

{brief['core_value']}

## 业务目标

{brief['business_goal']}

## 核心功能

{chr(10).join('- ' + x for x in brief['features'])}

## 技术要求

{brief.get('tech_requirement') or '待确认'}

## 待确认问题

- 产品边界待确认
- 角色权限待确认
- 部署方式待确认
- 第三方系统对接待确认
- 数据字段与业务状态流转待确认
"""


def gen_init_metadata(brief: dict[str, Any]) -> dict[str, Any]:
    """生成 .rd-init.json 的内容。"""
    return {
        "initialized_by": "rd-init",
        "initialized_at": datetime.now().isoformat(timespec="seconds"),
        "project_name": brief["project_name"],
        "next_step": "product-pipeline-master",
        "pipeline_entry": "brainstorm-product-feature",
        "standard_dirs": STANDARD_DIRS,
        "outputs": [
            "docs/project-brief.json",
            "docs/FEATURE_BRAINSTORM.md",
            "project.yaml",
            ".rd-init.json",
        ],
    }


# ── 主流程 ────────────────────────────────────────────────────

def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="rd-init：产研项目脚手架初始化，创建标准目录结构和起始文件"
    )
    parser.add_argument("--target-dir", default=".", help="目标项目目录，默认当前目录")
    parser.add_argument("--brief-json", help="结构化初步需求 JSON 字符串")
    parser.add_argument("--brief-file", help="初步需求文本文件；传 - 时从 stdin 读取")
    parser.add_argument("--brief", help="初步需求文本；传 - 时从 stdin 读取")
    parser.add_argument("--overwrite", action="store_true", help="覆盖已存在的文件")
    parser.add_argument("--dry-run", action="store_true", help="只预览，不写入")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    require_yaml()
    brief = load_brief(args)
    target_dir = Path(args.target_dir).expanduser().resolve()

    if not target_dir.exists():
        target_dir.mkdir(parents=True, exist_ok=True)

    # 1. 创建标准目录结构
    created_dirs = create_standard_dirs(target_dir, args.dry_run)

    # 2. 生成 docs/project-brief.json
    brief_data = gen_project_brief(brief)
    brief_written = save_json(
        target_dir / "docs" / "project-brief.json",
        brief_data,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )

    # 3. 生成 project.yaml
    project_data = gen_project_yaml(brief)
    project_written = save_yaml(
        target_dir / "project.yaml",
        project_data,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )

    # 4. 生成 docs/FEATURE_BRAINSTORM.md
    brainstorm_md = gen_feature_brainstorm_md(brief)
    brainstorm_written = write_text(
        target_dir / "docs" / "FEATURE_BRAINSTORM.md",
        brainstorm_md,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )

    # 5. 生成 .rd-init.json
    metadata = gen_init_metadata(brief)
    metadata_written = save_json(
        target_dir / ".rd-init.json",
        metadata,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )

    # 输出结果
    mode = "Dry run" if args.dry_run else "项目初始化完成"
    print(mode)
    print(f"项目目录：{target_dir}")
    print(f"项目名称：{brief['project_name']}")

    if created_dirs:
        print("\n已创建目录：")
        for d in created_dirs:
            print(f"  {d}")

    print("\n已生成文件：")
    files = [
        ("docs/project-brief.json", brief_written),
        ("project.yaml", project_written),
        ("docs/FEATURE_BRAINSTORM.md", brainstorm_written),
        (".rd-init.json", metadata_written),
    ]
    for rel, written in files:
        status = "已写入" if written else ("已存在(跳过)" if (target_dir / rel).exists() else "已写入")
        print(f"  {rel}：{status}")

    print("\n下一步：")
    print("  调用 product-pipeline-master 启动产研流水线")
    print("  阶段 1：brainstorm-product-feature（读取 docs/project-brief.json 澄清需求）")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
