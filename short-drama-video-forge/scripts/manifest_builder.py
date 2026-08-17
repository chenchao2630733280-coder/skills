#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
manifest_builder.py — 从 docs/STORYBOARD.md 生成 production/manifest.json 骨架

用法:
    python scripts/manifest_builder.py <project_dir> [--style 都市悬疑] [--t2i 即梦] [--i2v 可灵(Kling)]

输入:
    <project_dir>/docs/STORYBOARD.md   分镜脚本(short-drama-storyboard 产出)
    <project_dir>/docs/VISUAL_SPEC.md  视觉规范(角色/场景/seed)
输出:
    <project_dir>/production/manifest.json(骨架,status 全部为 pending,
    生成状态由 short-drama-video-forge 执行时回写)

说明:
    本脚本只做"骨架解析",字段与 STORYBOARD 一一对应(见 short-drama-storyboard
    SKILL.md §3.2 格式)。完整实现需按实际 STORYBOARD 格式调整解析正则(见 TODO),
    并补充 VISUAL_SPEC 的角色/场景解析。
"""
import argparse
import json
import re
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


def parse_visual_spec(path: Path):
    """解析 VISUAL_SPEC 中的角色/场景块。TODO: 按实际 VISUAL_SPEC 格式实现。"""
    return {"characters": [], "scenes": []}


def build_manifest(project_dir: Path, style: str, t2i: str, i2v: str) -> dict:
    sb_path = project_dir / "docs" / "STORYBOARD.md"
    vs_path = project_dir / "docs" / "VISUAL_SPEC.md"
    if not sb_path.exists() or not vs_path.exists():
        raise FileNotFoundError(
            f"缺少输入: {sb_path} 或 {vs_path},请先调用 short-drama-storyboard"
        )
    sb = parse_storyboard(sb_path)
    vs = parse_visual_spec(vs_path)
    episodes = []
    for ep, shots in sb.items():
        shot_list = []
        for shot_id, fields in shots.items():
            duration = fields.get("时长", "5s").rstrip("s")
            shot_list.append({
                "id": shot_id,
                "scriptFile": f"docs/scripts/{ep}.md",
                "imagePrompt": fields.get("文生图", ""),
                "videoPrompt": fields.get("图生视频", ""),
                "duration": int(duration) if duration.isdigit() else 5,
                "shotSize": fields.get("景别", ""),
                "camera": fields.get("运镜", ""),
                "characters": [c.strip() for c in fields.get("角色", "").split("+") if c.strip()],
                "scenes": [s.strip() for s in fields.get("场景", "").split("+") if s.strip()],
                "sound": fields.get("音效", ""),
                "subtitle": fields.get("对白", ""),
                "status": "pending",
                "outputPath": f"shots/{ep}/shot_{shot_id[-2:]}.mp4",
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
        "characters": vs["characters"],
        "scenes": vs["scenes"],
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
