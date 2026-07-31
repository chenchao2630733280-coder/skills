#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

ENV_TEMPLATE_GIT_URL = "AI_PRODUCT_RD_TEMPLATE_GIT_URL"
ENV_TEMPLATE_GIT_REF = "AI_PRODUCT_RD_TEMPLATE_GIT_REF"
ENV_TEMPLATE_SUBDIR = "AI_PRODUCT_RD_TEMPLATE_SUBDIR"
DEFAULT_TEMPLATE_GIT_URL = "https://gitlab.chinacici.com/chenchao/ai-product-rd.git"

EXCLUDED_COPY_NAMES = {".git", "node_modules", "dist", ".turbo", ".cache", "__pycache__"}

REQUIRED_TEMPLATE_CAPABILITIES = [
    "60_代码/vue-admin-plus/package.json",
    ".agents/skills/backend-api-design/SKILL.md",
    ".agents/skills/mysql-design/SKILL.md",
    "30_原型/页面明细/README.md",
    "99_模板/页面明细字段说明.md",
    "99_模板/页面明细示例-MyChildren.md",
    "scripts/validate_page_detail_specs.py",
]


def require_yaml() -> None:
    if yaml is None:
        raise SystemExit(
            "缺少 PyYAML 依赖，无法安全更新 project.yaml / workflow_state.yaml。\n"
            "请先执行：python -m pip install pyyaml\n"
            "然后重新运行初始化脚本。"
        )


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def write_text(path: Path, content: str, dry_run: bool = False) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_yaml(path: Path) -> dict[str, Any]:
    require_yaml()
    if not path.exists():
        return {}
    return yaml.safe_load(read_text(path)) or {}


def save_yaml(path: Path, data: dict[str, Any], dry_run: bool = False) -> None:
    require_yaml()
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(read_text(path) or "{}")


def save_json(path: Path, data: dict[str, Any], dry_run: bool = False) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def split_list(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    parts = re.split(r"[、,，;；\n]+", value)
    return [p.strip(" -\t") for p in parts if p.strip(" -\t")]


def extract_field(raw: str, labels: list[str]) -> str:
    for label in labels:
        pattern = rf"(?:^|\n)\s*{re.escape(label)}\s*[:：]\s*(.+)"
        m = re.search(pattern, raw)
        if m:
            return m.group(1).strip()
    return ""


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


def run(cmd: list[str], cwd: Path | None = None) -> None:
    printable = " ".join(cmd)
    print(f"执行命令：{printable}")
    try:
        subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)
    except FileNotFoundError as exc:
        if cmd[0] == "git":
            raise SystemExit("未找到 git 命令。请先安装 Git，或使用 --template-dir 指向已克隆的模板目录。") from exc
        raise
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"命令执行失败：{printable}\n退出码：{exc.returncode}") from exc


def clone_template_repo(git_url: str, git_ref: str | None, temp_dir: Path) -> Path:
    repo_dir = temp_dir / "template-repo"
    if not git_url:
        raise SystemExit(
            f"未配置模板 Git 仓库地址。请传入 --template-git-url，或设置环境变量 {ENV_TEMPLATE_GIT_URL}。"
        )

    # 首先尝试浅克隆。ref 可能是分支或 tag。
    cmd = ["git", "clone", "--depth", "1"]
    if git_ref:
        cmd += ["--branch", git_ref]
    cmd += [git_url, str(repo_dir)]

    try:
        run(cmd)
        return repo_dir
    except SystemExit:
        if not git_ref:
            raise
        # 如果 ref 是 commit hash，--branch 可能失败；回退到完整克隆后 checkout。
        if repo_dir.exists():
            shutil.rmtree(repo_dir)
        print("浅克隆指定 ref 失败，尝试完整克隆后 checkout。")
        run(["git", "clone", git_url, str(repo_dir)])
        run(["git", "checkout", git_ref], cwd=repo_dir)
        return repo_dir


def find_template_root(base_dir: Path, subdir: str | None = None) -> Path:
    if subdir:
        root = (base_dir / subdir).resolve()
        if not root.exists():
            raise SystemExit(f"模板子目录不存在：{root}")
        if (root / "project.yaml").exists() and (root / "workflow_state.yaml").exists() and (root / "asset_map.json").exists():
            return root
        raise SystemExit(f"模板子目录缺少 project.yaml / workflow_state.yaml / asset_map.json：{root}")

    candidates = []
    for p in base_dir.rglob("project.yaml"):
        root = p.parent
        if any(part in EXCLUDED_COPY_NAMES for part in root.parts):
            continue
        if (root / "workflow_state.yaml").exists() and (root / "asset_map.json").exists():
            candidates.append(root)
    if not candidates:
        raise RuntimeError("未找到模板根目录：仓库中应包含 project.yaml、workflow_state.yaml、asset_map.json")
    candidates.sort(key=lambda p: len(p.parts))
    return candidates[0]


def choose_template_root(args: argparse.Namespace, temp_dir: Path) -> tuple[Path, str]:
    if args.template_dir:
        base_dir = Path(args.template_dir).expanduser().resolve()
        if not base_dir.exists():
            raise SystemExit(f"本地模板目录不存在：{base_dir}")
        root = find_template_root(base_dir, args.template_subdir or os.environ.get(ENV_TEMPLATE_SUBDIR))
        return root, f"local-dir:{base_dir}"

    git_url = args.template_git_url or os.environ.get(ENV_TEMPLATE_GIT_URL) or DEFAULT_TEMPLATE_GIT_URL
    git_ref = args.template_ref or os.environ.get(ENV_TEMPLATE_GIT_REF)
    subdir = args.template_subdir or os.environ.get(ENV_TEMPLATE_SUBDIR)
    if not git_url:
        raise SystemExit(
            f"未找到模板来源。请提供 --template-git-url，或设置 {ENV_TEMPLATE_GIT_URL}。\n"
            "模板会经常更新，本 Skill 不再内置模板 zip。默认 Git 地址：https://gitlab.chinacici.com/chenchao/ai-product-rd.git"
        )

    repo_dir = clone_template_repo(git_url, git_ref, temp_dir)
    root = find_template_root(repo_dir, subdir)
    source = f"git:{git_url}"
    if git_ref:
        source += f"#{git_ref}"
    if subdir:
        source += f":{subdir}"
    return root, source


def should_skip_copy(path: Path) -> bool:
    return any(part in EXCLUDED_COPY_NAMES for part in path.parts)


def copy_template(template_root: Path, target_dir: Path, overwrite: bool, dry_run: bool) -> list[str]:
    copied: list[str] = []
    target_dir.mkdir(parents=True, exist_ok=True)
    for item in sorted(template_root.iterdir(), key=lambda p: p.name):
        if item.name in EXCLUDED_COPY_NAMES:
            continue
        target = target_dir / item.name
        rel = item.name
        if target.exists() and not overwrite:
            continue
        if dry_run:
            copied.append(rel + ("/" if item.is_dir() else ""))
            continue
        if target.exists() and overwrite:
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        if item.is_dir():
            shutil.copytree(item, target, ignore=shutil.ignore_patterns(*EXCLUDED_COPY_NAMES))
        else:
            shutil.copy2(item, target)
        copied.append(rel + ("/" if item.is_dir() else ""))
    return copied


def update_project_yaml(target_dir: Path, brief: dict[str, Any], dry_run: bool) -> None:
    path = target_dir / "project.yaml"
    data = load_yaml(path)

    project = data.setdefault("project", {})
    project["name"] = brief["project_name"]
    project["description"] = brief.get("core_value") or brief.get("raw_brief") or "待确认"
    project["status"] = "初始化完成，待范围确认"

    business = data.setdefault("business", {})
    business["industry"] = brief["industry"]
    business["product_type"] = brief["product_type"]
    business["target_users"] = brief["target_users"]
    business["core_value"] = brief["core_value"]
    business["business_goal"] = brief["business_goal"]

    features = data.setdefault("features", {})
    features["core"] = brief["features"]
    features["optional"] = brief.get("optional_features") or features.get("optional") or []
    features["future"] = brief.get("future_features") or features.get("future") or []

    tech_stack = data.setdefault("tech_stack", {})
    user_tech = brief.get("tech_stack") or {}
    tech_stack["frontend"] = user_tech.get("frontend") or tech_stack.get("frontend") or "Vue 3 + TypeScript + Element Plus + Vue Admin Plus"
    tech_stack["backend"] = user_tech.get("backend") or tech_stack.get("backend") or "待确认"
    tech_stack["database"] = user_tech.get("database") or "MySQL"
    tech_stack["deployment"] = user_tech.get("deployment") or tech_stack.get("deployment") or "待确认"

    init = data.setdefault("project_initialization", {})
    init["initialized_by_skill"] = "rd-init"
    init["initialized_at"] = datetime.now().isoformat(timespec="seconds")
    init["from_brief_enabled"] = True
    init["brief_file"] = "00_工作台/项目需求描述.md"
    init["require_confirmation"] = True
    init["template_source_type"] = "git"

    framework = data.setdefault("frontend_framework", {})
    framework["enabled"] = True
    framework["name"] = "vue-admin-plus"
    framework["source_type"] = "template_git_repo"
    framework["local_dir"] = "60_代码/vue-admin-plus"
    framework["embedded_in_template"] = True
    framework["ready"] = True
    framework["generate_static_html"] = False

    page_detail = data.setdefault("page_detail_specs", {})
    page_detail["enabled"] = True
    page_detail["output_dir"] = "30_原型/页面明细"
    page_detail["field_template"] = "99_模板/页面明细字段说明.md"
    page_detail["example_template"] = "99_模板/页面明细示例-MyChildren.md"
    page_detail["required_before_api"] = True
    page_detail["required_before_database"] = True
    page_detail["required_before_frontend_code"] = True
    page_detail["required_before_test"] = True

    data.setdefault("output", {})["generate_html_static_prototype"] = False
    data.setdefault("output", {})["generate_frontend_code"] = True
    data.setdefault("output", {})["frontend_code_in_framework"] = True
    data.setdefault("output", {})["generate_page_detail_specs"] = True

    save_yaml(path, data, dry_run)


def update_project_description(target_dir: Path, brief: dict[str, Any], dry_run: bool) -> None:
    content = f"""# 项目说明

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

## 模板与内置工程

- 模板来源：Git 仓库实时拉取
- 前端框架：Vue Admin Plus
- 前端工程目录：`60_代码/vue-admin-plus/`
- API Skill：`.agents/skills/backend-api-design/`
- 数据库 Skill：`.agents/skills/mysql-design/`
- 页面明细规格目录：`30_原型/页面明细/`
- 页面明细字段说明：`99_模板/页面明细字段说明.md`
- 页面明细示例：`99_模板/页面明细示例-MyChildren.md`

## 待确认问题

- 产品边界待确认
- 角色权限待确认
- 部署方式待确认
- 第三方系统对接待确认
- 数据字段与业务状态流转待确认
"""
    write_text(target_dir / "10_项目" / "项目说明.md", content, dry_run)


def update_brief_file(target_dir: Path, brief: dict[str, Any], dry_run: bool) -> None:
    content = brief.get("raw_brief") or json.dumps(brief, ensure_ascii=False, indent=2)
    write_text(target_dir / "00_工作台" / "项目需求描述.md", content.rstrip() + "\n", dry_run)


def update_workflow_state(target_dir: Path, brief: dict[str, Any], dry_run: bool) -> None:
    path = target_dir / "workflow_state.yaml"
    data = load_yaml(path)
    current = data.setdefault("current", {})
    current["stage"] = "scope_review"
    current["status"] = "not_started"
    current["next_allowed_stage"] = "scope_review"
    current["locked_until_user_confirmation"] = False

    init = data.setdefault("initialization", {})
    init["initialized_by_skill"] = "rd-init"
    init["initialized_at"] = datetime.now().isoformat(timespec="seconds")
    init["project_name"] = brief["project_name"]
    init["project_yaml_generated"] = True
    init["template_source_type"] = "git"
    init["frontend_framework_embedded_in_template"] = True
    init["frontend_framework_path"] = "60_代码/vue-admin-plus"
    init["page_detail_specs_enabled"] = True
    init["page_detail_specs_path"] = "30_原型/页面明细"
    init["page_detail_specs_field_template"] = "99_模板/页面明细字段说明.md"
    init["page_detail_specs_example_template"] = "99_模板/页面明细示例-MyChildren.md"
    init["next_recommended_stage"] = "scope_review"

    # Ensure prototype/page-structure stage, if present, records page detail specs as required output.
    for key in ["prototype_generation", "page_structure_generation", "prototype", "stage_2_prototype"]:
        stage_cfg = data.get("stages", {}).get(key)
        if isinstance(stage_cfg, dict):
            outputs = stage_cfg.setdefault("output_files", [])
            for rel in ["30_原型/页面清单.md", "30_原型/组件树.md", "30_原型/页面明细/*.md"]:
                if rel not in outputs:
                    outputs.append(rel)

    stage = data.setdefault("stages", {}).setdefault("scope_review", {})
    stage["status"] = "not_started"
    stage.setdefault("output_files", ["10_项目/项目说明.md", "00_工作台/阶段确认.md"])
    save_yaml(path, data, dry_run)


def update_asset_map(target_dir: Path, brief: dict[str, Any], dry_run: bool) -> None:
    path = target_dir / "asset_map.json"
    data = load_json(path)
    data.setdefault("project", {})
    data["project"].update({
        "id": data["project"].get("id", "PROJ-001"),
        "name": brief["project_name"],
    })
    data.setdefault("project_initialization", {})
    data["project_initialization"].update({
        "source": "rd-init",
        "template_source_type": "git",
        "status": "initialized",
        "brief_file": "00_工作台/项目需求描述.md",
        "output_file": "project.yaml",
        "project_name": brief["project_name"],
        "confirmation_required": True,
        "initialized_at": datetime.now().isoformat(timespec="seconds"),
    })
    data.setdefault("frontend_framework", {})
    data["frontend_framework"].update({
        "name": "vue-admin-plus",
        "local_dir": "60_代码/vue-admin-plus",
        "status": "ready",
        "source_type": "template_git_repo",
        "embedded_in_template": True,
    })
    existing_page_detail_specs = data.get("page_detail_specs")
    if isinstance(existing_page_detail_specs, dict):
        existing_items = existing_page_detail_specs.get("items", [])
    elif isinstance(existing_page_detail_specs, list):
        existing_items = existing_page_detail_specs
    else:
        existing_items = []
    data["page_detail_specs"] = {
        "enabled": True,
        "output_dir": "30_原型/页面明细",
        "field_template": "99_模板/页面明细字段说明.md",
        "example_template": "99_模板/页面明细示例-MyChildren.md",
        "status": "template_ready",
        "relation_chain": "requirements -> page_list -> component_tree -> page_detail_specs -> api -> database -> frontend_code -> tests",
        "items": existing_items,
    }
    data.setdefault("skills", [])
    existing = {s.get("name") for s in data.get("skills", []) if isinstance(s, dict)}
    if "backend-api-design" not in existing:
        data["skills"].append({
            "id": "SKILL-BACKEND-API-DESIGN",
            "name": "backend-api-design",
            "path": ".agents/skills/backend-api-design/SKILL.md",
            "stage": "api_generation",
            "outputs": ["40_接口/API总览.md", "40_接口/swagger.json", "40_接口/openapi.yaml"],
        })
    if "mysql-design" not in existing:
        data["skills"].append({
            "id": "SKILL-MYSQL-DESIGN",
            "name": "mysql-design",
            "path": ".agents/skills/mysql-design/SKILL.md",
            "stage": "database_generation",
            "outputs": ["50_数据库/数据库设计.md", "50_数据库/schema.sql"],
        })
    save_json(path, data, dry_run)


def update_workbench_files(target_dir: Path, brief: dict[str, Any], dry_run: bool) -> None:
    stage_confirm = f"""# 阶段确认

## 初始化状态

- 项目名称：{brief['project_name']}
- 初始化方式：rd-init Skill
- 模板来源：Git 仓库实时拉取
- 当前阶段：scope_review
- 下一步允许阶段：scope_review

## 待确认

- 请确认 project.yaml 中的项目名称、目标用户、核心功能和技术栈是否正确。
- 确认后执行第 0 阶段：项目理解与范围确认。
"""
    write_text(target_dir / "00_工作台" / "阶段确认.md", stage_confirm, dry_run)

    confirm_record = f"""# 确认记录

## {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 初始化

- 初始化方式：rd-init Skill
- 模板来源：Git 仓库实时拉取
- 项目名称：{brief['project_name']}
- 状态：已完成模板初始化，等待第 0 阶段确认。
"""
    write_text(target_dir / "00_工作台" / "确认记录.md", confirm_record, dry_run)

    health = f"""# 项目健康度

## 初始化检查

- 模板文件：已从 Git 仓库拉取并初始化
- project.yaml：已根据初步需求更新
- workflow_state.yaml：已初始化到 scope_review
- asset_map.json：已记录项目初始化和前端框架
- 前端工程：`60_代码/vue-admin-plus/`
- API Skill：`.agents/skills/backend-api-design/`
- 数据库 Skill：`.agents/skills/mysql-design/`
- 页面明细规格目录：`30_原型/页面明细/`
- 页面明细字段说明模板：`99_模板/页面明细字段说明.md`
- 页面明细示例：`99_模板/页面明细示例-MyChildren.md`

## 当前建议

执行第 0 阶段：项目理解与范围确认。
"""
    write_text(target_dir / "00_工作台" / "项目健康度.md", health, dry_run)


def validate_initialized_project(target_dir: Path) -> list[str]:
    warnings: list[str] = []
    required = [
        "project.yaml",
        "workflow_state.yaml",
        "asset_map.json",
        "AGENTS.md",
        ".ai-workflow/SKILL.md",
        *REQUIRED_TEMPLATE_CAPABILITIES,
    ]
    for rel in required:
        if not (target_dir / rel).exists():
            warnings.append(f"缺少：{rel}")
    return warnings


def write_init_metadata(target_dir: Path, brief: dict[str, Any], template_source: str, dry_run: bool) -> None:
    metadata = {
        "initialized_by": "rd-init",
        "initialized_at": datetime.now().isoformat(timespec="seconds"),
        "template_source": template_source,
        "template_source_type": "git" if template_source.startswith("git:") else "local-dir",
        "project_name": brief["project_name"],
        "template_capabilities": {
            "frontend_framework": "60_代码/vue-admin-plus",
            "api_skill": ".agents/skills/backend-api-design",
            "database_skill": ".agents/skills/mysql-design",
            "page_detail_specs": "30_原型/页面明细",
        },
        "next_step": "scope_review",
    }
    save_json(target_dir / ".rd-init.json", metadata, dry_run)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="rd-init：从 Git 模板仓库初始化 AI Product R&D ReviewGate 项目")
    parser.add_argument("--target-dir", default=".", help="目标项目目录，默认当前目录")
    parser.add_argument("--brief-json", help="结构化初步需求 JSON 字符串")
    parser.add_argument("--brief-file", help="初步需求文本文件；传 - 时从 stdin 读取")
    parser.add_argument("--brief", help="初步需求文本；传 - 时从 stdin 读取")
    parser.add_argument("--template-git-url", help=f"模板 Git 仓库地址，也可用环境变量 {ENV_TEMPLATE_GIT_URL}；默认使用 {DEFAULT_TEMPLATE_GIT_URL}")
    parser.add_argument("--template-ref", help=f"模板 Git 分支、tag 或 commit，也可用环境变量 {ENV_TEMPLATE_GIT_REF}")
    parser.add_argument("--template-subdir", help=f"模板在仓库中的子目录，也可用环境变量 {ENV_TEMPLATE_SUBDIR}")
    parser.add_argument("--template-dir", help="本地已克隆模板目录，仅用于离线测试或内网已同步场景")
    parser.add_argument("--overwrite", action="store_true", help="覆盖目标目录中已存在的同名模板文件")
    parser.add_argument("--dry-run", action="store_true", help="只预览，不写入")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    require_yaml()
    brief = load_brief(args)
    target_dir = Path(args.target_dir).expanduser().resolve()

    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        template_root, template_source = choose_template_root(args, temp_dir)
        copied = copy_template(template_root, target_dir, overwrite=args.overwrite, dry_run=args.dry_run)

    update_brief_file(target_dir, brief, args.dry_run)
    update_project_yaml(target_dir, brief, args.dry_run)
    update_project_description(target_dir, brief, args.dry_run)
    update_workflow_state(target_dir, brief, args.dry_run)
    update_asset_map(target_dir, brief, args.dry_run)
    update_workbench_files(target_dir, brief, args.dry_run)
    write_init_metadata(target_dir, brief, template_source, args.dry_run)

    warnings = [] if args.dry_run else validate_initialized_project(target_dir)

    print("项目初始化完成" if not args.dry_run else "Dry run 完成：未写入文件")
    print(f"项目目录：{target_dir}")
    print(f"模板来源：{template_source}")
    print(f"项目名称：{brief['project_name']}")
    print("已复制顶层文件/目录：")
    for item in copied[:60]:
        print(f"- {item}")
    if len(copied) > 60:
        print(f"- ... 共 {len(copied)} 项")

    print("\n已初始化/更新文件：")
    for rel in [
        "project.yaml",
        "00_工作台/项目需求描述.md",
        "10_项目/项目说明.md",
        "workflow_state.yaml",
        "asset_map.json",
        "00_工作台/阶段确认.md",
        "00_工作台/确认记录.md",
        "00_工作台/项目健康度.md",
        ".rd-init.json",
    ]:
        print(f"- {rel}")

    print("\n模板能力检查：")
    for rel in REQUIRED_TEMPLATE_CAPABILITIES:
        status = "已存在" if (target_dir / rel).exists() else "缺失"
        print(f"- {rel}：{status}")

    if warnings:
        print("\n初始化检查警告：")
        for w in warnings:
            print(f"- {w}")
        print("- 如果页面明细规格相关文件缺失，请更新模板 Git 仓库，确保包含 PageDetailSpecs 相关文件。")

    print("\n待确认问题：")
    print("- 请确认 project.yaml 中的目标用户、核心功能、业务边界和技术栈。")
    print("- 请确认是否需要登录、权限、支付、上传、AI 能力和第三方系统对接。")
    print("- 请确认部署方式和后端技术栈。")

    print("\n推荐下一步指令：")
    print("请读取 project.yaml、AGENTS.md、.ai-workflow/SKILL.md、workflow_state.yaml 和 asset_map.json，只执行第 0 阶段：项目理解与范围确认。要求：输出产品理解、目标用户、核心功能范围、业务边界和待确认问题；写入 10_项目/项目说明.md 和 00_工作台/阶段确认.md；不生成需求、页面清单、组件树、页面明细、接口、数据库、代码结构、测试或交付文档；完成后停止，等待我确认。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
