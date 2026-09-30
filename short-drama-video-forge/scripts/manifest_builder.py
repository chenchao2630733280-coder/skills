#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
manifest_builder.py — 从 docs/STORYBOARD.md + docs/ASSET_MANIFEST.json 生成 production/manifest.json 骨架

用法:
    python scripts/manifest_builder.py <project_dir> [--style 都市悬疑] [--t2i 即梦] [--i2v 可灵(Kling)]

输入:
    <project_dir>/docs/STORYBOARD.md        分镜脚本(short-drama-storyboard 产出)
    <project_dir>/docs/ASSET_MANIFEST.json  资产需求清册(阶段4声明 / 阶段4.5锁定) — 资产唯一真源
    <project_dir>/docs/VISUAL_SPEC.md       视觉规范(镜头级补充描述)
输出:
    <project_dir>/production/manifest.json(骨架,status 全部为 pending,
    生成状态由 short-drama-video-forge 执行时回写)

硬前置校验(不通过则退出,不产 manifest):
    被引用资产的 status ∈ {locked, skipped};实体文件存在;文件 sha256 前12位 == 清册 hash

说明:
    本脚本只做"骨架解析",字段与 STORYBOARD 一一对应(见 short-drama-storyboard
    SKILL.md §3.2 格式)。资产部分只写**引用块**(id/variant/assetVersion/hash),
    严禁把 refImage/seed/styleKeywords 复制进 manifest(双真源缺陷,Gate 4.9 阻断)。
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

EP_RE = re.compile(r"^##\s+(EP\d{2})\s*$")
SHOT_RE = re.compile(r"^###\s+(EP\d{2}-S\d{2})\s*$")
FIELD_RE = re.compile(r"^-\s*([^:：]+)[:：]\s*(.+)$")


def parse_storyboard(path: Path):
    """按集按镜头解析,返回 {ep: {shot: {字段名: 值}}}。TODO: 按实际格式微调正则。"""
    data = {}
    cur_ep, cur_shot = None, None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = EP_RE.match(line.strip())
        if m:
            cur_ep, cur_shot = m.group(1), None
            data.setdefault(cur_ep, {})
            continue
        m = SHOT_RE.match(line.strip())
        if m:
            cur_shot = m.group(1)
            data[cur_ep][cur_shot] = {}
            continue
        m = FIELD_RE.match(line.strip())
        if m and cur_ep and cur_shot:
            key, val = m.group(1).strip(), m.group(2).strip()
            data[cur_ep][cur_shot][key] = val
    return data


CHAR_RE = re.compile(r"^([a-zA-Z0-9_]+)(?:\(([a-zA-Z0-9_]+)\))?$")


def parse_visual_spec(path: Path):
    """解析 VISUAL_SPEC 中的角色/场景块。TODO: 按实际 VISUAL_SPEC 格式实现。"""
    return {"characters": [], "scenes": []}


def split_refs(raw: str):
    """拆分 '+'-分隔的引用;角色支持 `id(variant)` 变体语法。"""
    chars, variants, others = [], {}, []
    for item in [x.strip() for x in (raw or "").split("+") if x.strip()]:
        m = CHAR_RE.match(item)
        if not m:
            others.append(item)
            continue
        cid, variant = m.group(1), m.group(2)
        if cid not in chars:
            chars.append(cid)
        if variant:
            variants[cid] = variant
    return chars, variants, others


def sha256_12(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def _walk_assets(asset_manifest: dict, project_dir: Path):
    """遍历五类资产,产出 (kind, id, variant, entry, file_path) 用于校验与引用块。"""
    for c in asset_manifest.get("characters", []):
        for v in c.get("variants", []):
            ref = v.get("refImage")
            yield ("characters", c["id"], v.get("variantId"), v,
                   project_dir / ref if ref else None)
    for s in asset_manifest.get("scenes", []):
        ref = s.get("refImage")
        yield ("scenes", s["id"], None, s, project_dir / ref if ref else None)
    for p in asset_manifest.get("props", []):
        ref = p.get("refImage")
        yield ("props", p["id"], None, p, project_dir / ref if ref else None)
    for v in asset_manifest.get("voice", []):
        if v.get("skipped"):
            continue
        sp = v.get("samplePath")
        yield ("voice", v["id"], None, v, project_dir / sp if sp else None)


def verify_locked_assets(asset_manifest: dict, project_dir: Path):
    """硬前置:全部被引用资产必须已锁定、文件存在、hash 相符。不通过抛 SystemExit。"""
    problems = []
    style = asset_manifest.get("styleBaseline") or {}
    if style.get("status") != "locked":
        problems.append("风格基线未锁定(status != locked)")
    for kind, aid, variant, entry, fpath in _walk_assets(asset_manifest, project_dir):
        label = f"{kind}:{aid}" + (f"@{variant}" if variant else "")
        if entry.get("status") not in ("locked", "skipped"):
            problems.append(f"{label} 未锁定(status={entry.get('status')})")
            continue
        if fpath is None or not fpath.exists():
            problems.append(f"{label} 实体文件缺失: {fpath}")
            continue
        if entry.get("hash") and sha256_12(fpath) != entry["hash"]:
            problems.append(f"{label} hash 不符(资产被偷换)")
    if problems:
        print("资产硬前置校验失败,不生成 manifest:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        print("请回 short-drama-asset-forge(阶段 4.5)定妆/走变更流程,过 Gate 3.5 后重跑。",
              file=sys.stderr)
        raise SystemExit(2)


def build_assets_ref(asset_manifest: dict, project_dir: Path,
                     manifest_path: Path) -> dict:
    """只写引用块(id/variant/assetVersion/hash),不复制资产定义。"""
    ref = {
        "source": "docs/ASSET_MANIFEST.json",
        "sourceVersion": asset_manifest.get("version", "1.0"),
        "sourceHash": sha256_12(manifest_path) if manifest_path.exists() else None,
        "characters": [], "scenes": [], "props": [], "voice": [],
    }
    for kind, aid, variant, entry, _ in _walk_assets(asset_manifest, project_dir):
        item = {"id": aid, "assetVersion": entry.get("assetVersion"), "hash": entry.get("hash")}
        if variant:
            item["variant"] = variant
        ref[kind].append(item)
    style = asset_manifest.get("styleBaseline") or {}
    ref["styleBaseline"] = {
        "id": style.get("id"),
        "assetVersion": style.get("assetVersion"),
        "hash": style.get("hash"),
    }
    return ref


def build_manifest(project_dir: Path, style: str, t2i: str, i2v: str) -> dict:
    sb_path = project_dir / "docs" / "STORYBOARD.md"
    vs_path = project_dir / "docs" / "VISUAL_SPEC.md"
    am_path = project_dir / "docs" / "ASSET_MANIFEST.json"
    for p in (sb_path, vs_path, am_path):
        if not p.exists():
            raise FileNotFoundError(f"缺少输入: {p},请先调用 short-drama-storyboard / short-drama-asset-forge")
    asset_manifest = json.loads(am_path.read_text(encoding="utf-8"))
    verify_locked_assets(asset_manifest, project_dir)

    sb = parse_storyboard(sb_path)
    # 变体路由表: (charId, variantId) -> (assetVersion, hash)
    route = {}
    for kind, aid, variant, entry, _ in _walk_assets(asset_manifest, project_dir):
        if kind == "characters":
            route[(aid, variant or "default")] = (entry.get("assetVersion"), entry.get("hash"))

    episodes = []
    for ep, shots in sb.items():
        shot_list = []
        for shot_id, fields in shots.items():
            duration = fields.get("时长", "5s").rstrip("s")
            chars, variants, _ = split_refs(fields.get("角色", ""))
            scenes, _sv, _so = split_refs(fields.get("场景", ""))
            props, _pv, _po = split_refs(fields.get("道具", ""))
            snapshot = {}
            for cid in chars:
                cvar = variants.get(cid, "default")
                av, hv = route.get((cid, cvar), (None, None))
                snapshot[cid] = {"variant": cvar, "assetVersion": av, "hash": hv}
            shot_list.append({
                "id": shot_id,
                "scriptFile": f"docs/scripts/{ep}.md",
                "imagePrompt": fields.get("文生图", ""),
                "videoPrompt": fields.get("图生视频", ""),
                "duration": int(duration) if duration.isdigit() else 5,
                "shotSize": fields.get("景别", ""),
                "camera": fields.get("运镜", ""),
                "characters": chars,
                "charVariants": variants,
                "scenes": scenes,
                "props": props,
                "sound": fields.get("音效", ""),
                "subtitle": fields.get("对白", ""),
                "status": "pending",
                "outputPath": f"shots/{ep}/shot_{shot_id[-2:]}.mp4",
                "assetSnapshot": snapshot,
            })
        episodes.append({"ep": ep, "shots": shot_list})
    return {
        "version": "1.0",
        "project": {
            "title": project_dir.name,
            "totalEpisodes": len(episodes),
            "aspectRatio": "9:16",
            "resolution": [1080, 1920],
            "style": style,
        },
        "toolchain": {"textToImage": t2i, "imageToVideo": i2v},
        "assets": build_assets_ref(asset_manifest, project_dir, am_path),
        "episodes": episodes,
    }


def main():
    ap = argparse.ArgumentParser(description="从 STORYBOARD.md 生成 manifest.json 骨架")
    ap.add_argument("project_dir", type=Path, help="短剧项目根目录")
    ap.add_argument("--style", default="都市悬疑")
    ap.add_argument("--t2i", default="即梦")
    ap.add_argument("--i2v", default="可灵(Kling)")
    args = ap.parse_args()

    manifest = build_manifest(args.project_dir, args.style, args.t2i, args.i2v)
    out_dir = args.project_dir / "production"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "manifest.json"
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest 骨架已写入: {out_path}")


if __name__ == "__main__":
    main()
