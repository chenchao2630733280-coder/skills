#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_episodes.py — 短剧成片自动合成脚本(short-drama-edit 辅助工具,可选)

用法:
    python scripts/build_episodes.py --dry-run          # 只打印每集 ffmpeg 命令清单,不执行
    python scripts/build_episodes.py                    # 解析 manifest 并逐集执行合成
    python scripts/build_episodes.py --ep EP01          # 只合成指定集
    python scripts/build_episodes.py --out-dir episodes # 指定输出目录(默认 episodes/)

说明:
    本脚本是 SKILL.md §三/§四 的自动化形态:读取 production/manifest.json,
    按集生成"拼接→转场→运镜→混音→烧字幕→导出"的 ffmpeg 命令并执行。
    manifest 结构(最小读取契约,以 short-drama-video-forge 实际产出为准):
        {
          "episode": "EP01",
          "shots": [
            {"shot_id": 1, "file": "shots/EP01/shot_01.mp4",
             "type": "video", "duration": 5.0, "line": "line_01"},
            {"shot_id": 5, "file": "shots/EP01/shot_05.png",
             "type": "image", "duration": 5.0, "line": null}
          ],
          "bgm": "audio/bgm_tension.mp3",
          "sfx": ["audio/sfx_door.mp3"]
        }
    本文件为骨架实现:命令生成逻辑(gen_ffmpeg_cmd)是主流程,执行/重试/占位降级
    按 SKILL.md §六 处理。可直接运行,也允许流水线内按需改写(非强制完整实现)。
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # {project}/ (skill 目录上一级)
MANIFEST = PROJECT_ROOT / "production" / "manifest.json"
EPISODES_DIR = PROJECT_ROOT / "episodes"

VIDEO_ARGS = ["-c:v", "libx264", "-b:v", "6M", "-maxrate", "8M", "-bufsize", "12M",
              "-r", "30", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
              "-movflags", "+faststart"]


def check_ffmpeg() -> None:
    """ffmpeg/ffprobe 可用性检查;缺失则报错退出。"""
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        sys.exit("[错误] 未找到 ffmpeg/ffprobe,请先安装 FFmpeg ≥ 4.4 并加入 PATH。")


def load_manifest() -> dict:
    """加载并校验 manifest;缺失/非法 JSON 时报错退出(见 SKILL.md §二.1)。"""
    if not MANIFEST.exists():
        sys.exit(f"[错误] manifest 缺失: {MANIFEST}\n请先调用 short-drama-video-forge 生成。")
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"[错误] manifest JSON 解析失败(行 {e.lineno}): {e}\n原文片段: {MANIFEST.read_text(encoding='utf-8')[:200]}")


def gen_ffmpeg_cmd(episode: dict, out_dir: Path) -> list[str]:
    """按集生成 ffmpeg 命令(骨架:拼接+统一参数;完整混音/字幕见 references/ffmpeg-recipes.md)。

    返回 ffmpeg 命令参数列表。缺镜头文件时命令引用占位黑场(占位生成见 gen_placeholder)。
    """
    ep = episode["episode"]
    # 1. 拼接清单
    list_file = PROJECT_ROOT / f"list_{ep}.txt"
    lines = []
    for shot in episode["shots"]:
        src = PROJECT_ROOT / shot["file"]
        if not src.exists():
            # 缺镜头:降级为占位黑场 + 字幕"待补拍"标记(见 SKILL.md §六)
            placeholder = gen_placeholder(ep, shot["shot_id"])
            lines.append(f"file '{placeholder.as_posix()}'")
        else:
            lines.append(f"file '{src.as_posix()}'")
    list_file.write_text("\n".join(lines), encoding="utf-8")

    out = out_dir / f"{ep}.mp4"
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file)]
    # 2. 统一竖屏参数(scale+pad 强制 1080x1920,30fps)
    cmd += ["-vf", ("scale=1080:1920:force_original_aspect_ratio=decrease,"
                    "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p")]
    cmd += VIDEO_ARGS + [str(out)]
    return cmd


def gen_placeholder(ep: str, shot_id: int) -> Path:
    """生成占位黑场视频(1080x1920,黑屏 + "待补拍"文字字幕),返回路径。"""
    placeholder = PROJECT_ROOT / f"_placeholder_{ep}_shot{shot_id:02d}.mp4"
    if not placeholder.exists():
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=1080x1920:r=30",
             "-vf", ("drawtext=text='待补拍':fontsize=72:fontcolor=white:"
                     "x=(w-text_w)/2:y=(h-text_h)/2"),
             "-t", "5", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(placeholder)],
            check=True, capture_output=True)
    return placeholder


def run_episode(episode: dict, out_dir: Path, dry_run: bool, max_retry: int = 2) -> bool:
    """合成单集;失败重试 ≤2 次,仍失败返回 False(不阻塞其他集,见 SKILL.md §六)。"""
    cmd = gen_ffmpeg_cmd(episode, out_dir)
    ep = episode["episode"]
    if dry_run:
        print(f"# {ep} 命令清单:\n  " + " ".join(cmd) + "\n")
        return True
    out_dir.mkdir(parents=True, exist_ok=True)
    for attempt in range(max_retry + 1):
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"[OK] {ep} 合成完成 -> {out_dir / (ep + '.mp4')}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[重试 {attempt + 1}/{max_retry + 1}] {ep} 合成失败: {e.stderr.decode('utf-8', 'ignore')[-300:]}")
    print(f"[FAIL] {ep} 合成失败(重试 {max_retry} 次后),已记入失败清单,不阻塞其他集。")
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="短剧成片自动合成(short-drama-edit)")
    parser.add_argument("--dry-run", action="store_true", help="只打印命令清单,不执行")
    parser.add_argument("--ep", default=None, help="只合成指定集,如 EP01")
    parser.add_argument("--out-dir", default=str(EPISODES_DIR), help="输出目录(默认 episodes/)")
    args = parser.parse_args()

    check_ffmpeg()
    manifest = load_manifest()
    episodes = manifest["episodes"] if isinstance(manifest, dict) and "episodes" in manifest else [manifest]

    out_dir = Path(args.out_dir)
    results = {}
    for episode in episodes:
        if args.ep and episode["episode"] != args.ep:
            continue
        results[episode["episode"]] = run_episode(episode, out_dir, args.dry_run)

    if not args.dry_run:
        failed = [ep for ep, ok in results.items() if not ok]
        print("\n汇总: 成功", len(results) - len(failed), "/ 失败", len(failed),
              "(失败清单请同步写入 docs/BUILD_REPORT.md 的 Gate 5 部分)")


if __name__ == "__main__":
    main()
