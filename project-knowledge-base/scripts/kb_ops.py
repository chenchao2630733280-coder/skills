#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""项目知识库操作脚本。

支持 query / add / update / list 四个子命令,使用 Python 标准库实现,无外部依赖。
知识存储于当前工作目录下的 .trae-cn/knowledge/ 目录,按分类分子目录,
索引文件为 .trae-cn/knowledge/knowledge-base.json。

用法示例:
    python scripts/kb_ops.py query --category adr --keyword "缓存"
    python scripts/kb_ops.py add --category adr --title "标题" --content "内容"
    python scripts/kb_ops.py update --id <UUID> --content "新内容"
    python scripts/kb_ops.py list --category team-conventions
"""

import argparse
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

# 知识库根目录:以当前工作目录为项目根
KNOWLEDGE_BASE_DIR = Path.cwd() / ".trae-cn" / "knowledge"
# 索引文件路径
INDEX_FILE = KNOWLEDGE_BASE_DIR / "knowledge-base.json"

# 支持的知识分类(与子目录一一对应)
CATEGORIES = ("team-conventions", "adr", "postmortems", "code-standards")


def ensure_dirs():
    """确保知识库根目录及各分类子目录存在。"""
    KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
    for category in CATEGORIES:
        (KNOWLEDGE_BASE_DIR / category).mkdir(parents=True, exist_ok=True)


def rel_path(path):
    """返回相对当前工作目录的路径字符串,失败则回退为绝对路径。"""
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def load_index():
    """读取索引文件;不存在或损坏时返回空索引。"""
    if not INDEX_FILE.exists():
        return {"entries": []}
    try:
        with INDEX_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("entries"), list):
            return data
        return {"entries": []}
    except (json.JSONDecodeError, OSError):
        return {"entries": []}


def save_index(index):
    """写入索引文件。"""
    ensure_dirs()
    with INDEX_FILE.open("w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def now_iso():
    """返回当前本地时间的 ISO8601 字符串(精度到秒)。"""
    return datetime.now().isoformat(timespec="seconds")


def cmd_query(args):
    """按分类和关键词搜索知识条目并打印完整 JSON。"""
    index = load_index()
    keyword = (args.keyword or "").strip().lower()
    results = []
    for entry in index.get("entries", []):
        # 分类过滤(未指定分类则全部)
        if args.category and entry.get("category") != args.category:
            continue
        # 关键词过滤:命中标题/正文/标签任一即可
        if keyword:
            hay = " ".join([
                entry.get("title", ""),
                entry.get("content", ""),
                " ".join(entry.get("tags", [])),
            ]).lower()
            if keyword not in hay:
                continue
        results.append(entry)

    if not results:
        print("未找到匹配的知识条目。")
        return
    for entry in results:
        print(json.dumps(entry, ensure_ascii=False, indent=2))
        print("-" * 40)


def cmd_add(args):
    """新增知识条目:生成 UUID,写入分类子目录,并更新索引。"""
    ensure_dirs()
    if args.category not in CATEGORIES:
        print(f"错误:不支持的分类 '{args.category}'。支持的分类:{', '.join(CATEGORIES)}",
              file=sys.stderr)
        sys.exit(1)

    entry_id = str(uuid.uuid4())
    timestamp = now_iso()
    tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []

    entry = {
        "id": entry_id,
        "category": args.category,
        "title": args.title,
        "content": args.content,
        "tags": tags,
        "createdAt": timestamp,
        "updatedAt": timestamp,
    }

    entry_file = KNOWLEDGE_BASE_DIR / args.category / f"{entry_id}.json"
    try:
        with entry_file.open("w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f"WARNING: 知识库写入失败,已跳过({exc})", file=sys.stderr)
        return

    index = load_index()
    index.setdefault("entries", []).append({
        "id": entry_id,
        "category": args.category,
        "title": args.title,
        "tags": tags,
        "createdAt": timestamp,
        "updatedAt": timestamp,
        "path": rel_path(entry_file),
    })
    save_index(index)
    print(f"已新增知识条目:id={entry_id},分类={args.category}")


def cmd_update(args):
    """按 id 更新指定条目的 content 和/或 title,同步刷新索引。"""
    index = load_index()
    meta = None
    for entry in index.get("entries", []):
        if entry.get("id") == args.id:
            meta = entry
            break
    if meta is None:
        print(f"错误:未找到 id={args.id} 的条目。", file=sys.stderr)
        sys.exit(1)

    # content 与 title 至少要提供一个
    if not args.content and not args.title:
        print("错误:update 至少需要提供 --content 或 --title 之一。", file=sys.stderr)
        sys.exit(1)

    category = meta["category"]
    entry_file = KNOWLEDGE_BASE_DIR / category / f"{args.id}.json"
    if not entry_file.exists():
        print(f"错误:知识文件不存在 {entry_file}", file=sys.stderr)
        sys.exit(1)

    try:
        with entry_file.open("r", encoding="utf-8") as f:
            entry = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"错误:读取条目文件失败({exc})", file=sys.stderr)
        sys.exit(1)

    if args.title:
        entry["title"] = args.title
        meta["title"] = args.title
    if args.content:
        entry["content"] = args.content
    entry["updatedAt"] = now_iso()
    meta["updatedAt"] = entry["updatedAt"]

    try:
        with entry_file.open("w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False, indent=2)
        save_index(index)
        print(f"已更新知识条目:id={args.id}")
    except OSError as exc:
        print(f"WARNING: 知识库写入失败,已跳过({exc})", file=sys.stderr)


def cmd_list(args):
    """列出全部或按分类列出知识条目概览。"""
    index = load_index()
    entries = index.get("entries", [])
    if args.category:
        entries = [e for e in entries if e.get("category") == args.category]
    if not entries:
        print("知识库为空。")
        return
    for entry in entries:
        print(f"[{entry.get('category')}] {entry.get('id')} | "
              f"{entry.get('title')} (更新于 {entry.get('updatedAt')})")


def build_parser():
    """构建并返回 argparse 解析器。"""
    parser = argparse.ArgumentParser(
        description="项目知识库操作工具(query/add/update/list)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # query 子命令
    p_query = sub.add_parser("query", help="按分类和关键词查询知识")
    p_query.add_argument("--category", choices=CATEGORIES, help="知识分类(可选)")
    p_query.add_argument("--keyword", help="搜索关键词(可选)")
    p_query.set_defaults(func=cmd_query)

    # add 子命令
    p_add = sub.add_parser("add", help="新增知识条目")
    p_add.add_argument("--category", choices=CATEGORIES, required=True, help="知识分类")
    p_add.add_argument("--title", required=True, help="条目标题")
    p_add.add_argument("--content", required=True, help="条目内容")
    p_add.add_argument("--tags", help="标签,逗号分隔(可选)")
    p_add.set_defaults(func=cmd_add)

    # update 子命令
    p_update = sub.add_parser("update", help="更新知识条目")
    p_update.add_argument("--id", required=True, help="条目 ID(UUID)")
    p_update.add_argument("--content", help="新内容(可选)")
    p_update.add_argument("--title", help="新标题(可选)")
    p_update.set_defaults(func=cmd_update)

    # list 子命令
    p_list = sub.add_parser("list", help="列出知识条目")
    p_list.add_argument("--category", choices=CATEGORIES, help="知识分类(可选)")
    p_list.set_defaults(func=cmd_list)

    return parser


def main():
    """脚本主入口:解析参数并派发到对应子命令处理函数。"""
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
