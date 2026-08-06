#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""index_codebase.py - Context 层代码库索引脚本。

子命令:
  build  --project <路径> [--chunk-strategy hybrid] [--embedding local|none|api]
  update --project <路径>
  stats  --project <路径>

设计原则(与 skill-runtime 一致):
- 失败不抛异常,统一通过 error 字段与退出码表达
- 嵌入库可选:无嵌入库时降级为关键词索引(embedding=none),仍可检索
- 索引数据写入 .trae-cn/codebase-index/<项目名>/(不提交 Git)

产出:codebase-index.json(索引清单)
退出码:0=成功;1=有错误;2=参数错误
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 嵌入库可选导入
try:
    import numpy as np  # type: ignore
    HAS_NUMPY = True
except Exception:
    HAS_NUMPY = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
    HAS_SKLEARN = True
except Exception:
    HAS_SKLEARN = False


# ---------- 常量 ----------

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parents[1]
INDEX_ROOT = Path.home() / ".trae-cn" / "codebase-index"

# 代码文件扩展名白名单
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".kt", ".go",
    ".rs", ".c", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php",
    ".swift", ".m", ".vue", ".svelte", ".html", ".css", ".scss",
    ".sql", ".sh", ".ps1", ".bat", ".yaml", ".yml", ".json", ".xml",
    ".md", ".gd", ".tscn",  # Godot
}

# 分块大小阈值(行数)
SMALL_FILE_LINES = 50    # <=50 行:整文件一块
MEDIUM_FILE_LINES = 300  # <=300 行:按函数分块

REPORT_FILENAME = "codebase-index.json"


# ---------- 工具函数 ----------

def _now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _project_name(project_path):
    return Path(project_path).resolve().name


def _index_dir(project_path):
    name = _project_name(project_path)
    return INDEX_ROOT / name


def _file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _detect_language(path):
    ext = Path(path).suffix.lower()
    mapping = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".tsx": "tsx", ".jsx": "jsx", ".java": "java", ".kt": "kotlin",
        ".go": "go", ".rs": "rust", ".c": "c", ".cpp": "cpp",
        ".h": "c", ".hpp": "cpp", ".cs": "csharp", ".rb": "ruby",
        ".php": "php", ".swift": "swift", ".vue": "vue",
        ".html": "html", ".css": "css", ".sql": "sql",
        ".sh": "shell", ".ps1": "powershell", ".gd": "gdscript",
    }
    return mapping.get(ext, "text")


def _count_lines(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def _estimate_tokens(text):
    """粗略估算 token 数(约 4 字符 = 1 token)。"""
    return max(1, len(text) // 4)


def _split_into_chunks(path, strategy="hybrid"):
    """把文件分块,返回 [(start_line, end_line, text), ...]。"""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        return []

    total = len(lines)
    if total == 0:
        return []

    text = "".join(lines)

    # file 策略:整文件一块
    if strategy == "file":
        return [(1, total, text)]

    # 小文件:整文件一块
    if total <= SMALL_FILE_LINES:
        return [(1, total, text)]

    # function 策略或 hybrid 的中型文件:按函数/类定义分块
    if strategy in ("function", "hybrid"):
        chunks = _split_by_function(lines, total)
        if chunks:
            return chunks
        # 分块失败则按行数均分
        return _split_by_lines(lines, total, MEDIUM_FILE_LINES)

    # semantic 策略:按类/模块分块(简化:按双换行分段)
    if strategy == "semantic":
        return _split_by_lines(lines, total, MEDIUM_FILE_LINES)

    # 默认
    return [(1, total, text)]


def _split_by_function(lines, total):
    """按函数/类定义分块(简化版:检测 def/class/function 等关键字)。"""
    keywords = ("def ", "class ", "function ", "func ", "func ", "fn ",
                "public ", "private ", "protected ", "static ")
    chunks = []
    start = 0
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if any(stripped.startswith(kw) for kw in keywords) and i > start:
            chunks.append((start + 1, i, "".join(lines[start:i])))
            start = i
    if start < total:
        chunks.append((start + 1, total, "".join(lines[start:total])))
    return chunks if len(chunks) > 1 else [(1, total, "".join(lines))]


def _split_by_lines(lines, total, size):
    """按固定行数分块。"""
    chunks = []
    for i in range(0, total, size):
        end = min(i + size, total)
        chunks.append((i + 1, end, "".join(lines[i:end])))
    return chunks


def _scan_code_files(project_path, ignore_dirs=None):
    """扫描项目下的代码文件。"""
    if ignore_dirs is None:
        ignore_dirs = {".git", "node_modules", "__pycache__", ".trae-cn",
                       "dist", "build", ".next", "vendor", "export", "Build"}
    project = Path(project_path).resolve()
    files = []
    for entry in sorted(project.rglob("*")):
        if not entry.is_file():
            continue
        # 跳过忽略目录
        if any(part in ignore_dirs for part in entry.parts):
            continue
        if entry.suffix.lower() in CODE_EXTENSIONS:
            files.append(entry)
    return files


def _build_tfidf_index(chunks):
    """构建 TF-IDF 关键词索引(降级方案)。"""
    if not HAS_SKLEARN:
        return None
    texts = [c["text"] for c in chunks]
    vectorizer = TfidfVectorizer(max_features=5000)
    try:
        matrix = vectorizer.fit_transform(texts)
        return {"vectorizer": vectorizer, "matrix": matrix}
    except Exception:
        return None


# ---------- 子命令实现 ----------

def cmd_build(args):
    """build:全量索引。"""
    project = Path(args.project).resolve()
    if not project.exists():
        report = {"command": "build", "project": project.name, "stats": {},
                  "results": [], "error": f"项目路径不存在:{project}",
                  "timestamp": _now_iso()}
        print(f"FAIL  项目路径不存在:{project}")
        return 1

    strategy = args.chunk_strategy
    embedding_mode = args.embedding

    files = _scan_code_files(project)
    index_files = []
    all_chunks = []
    total_tokens = 0

    for f in files:
        rel = str(f.relative_to(project)).replace("\\", "/")
        lines = _count_lines(f)
        chunks = _split_into_chunks(f, strategy)
        h = _file_hash(f)
        lang = _detect_language(f)

        chunk_list = []
        for (start, end, text) in chunks:
            tokens = _estimate_tokens(text)
            total_tokens += tokens
            chunk_list.append({"start": start, "end": end, "tokens": tokens})
            all_chunks.append({"file": rel, "start": start, "end": end,
                               "text": text, "language": lang})

        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime).isoformat(timespec="seconds")
        except Exception:
            mtime = ""

        index_files.append({
            "path": rel, "hash": h, "mtime": mtime,
            "chunks": len(chunk_list), "language": lang,
            "lines": lines,
        })

    # 嵌入索引
    embedding_label = "none"
    tfidf_data = None
    if embedding_mode in ("local", "api"):
        if HAS_SKLEARN:
            tfidf_data = _build_tfidf_index(all_chunks)
            embedding_label = "tfidf-keyword" if tfidf_data else "none"
            if tfidf_data is None:
                print("WARN  嵌入库不可用,降级为无嵌入索引(scikit-learn 构建失败)")
        else:
            print("WARN  嵌入库不可用,降级为无嵌入索引(未安装 scikit-learn)")
            embedding_label = "none"
    elif embedding_mode == "none":
        embedding_label = "none"

    # 写索引目录
    idx_dir = _index_dir(project)
    idx_dir.mkdir(parents=True, exist_ok=True)

    index_doc = {
        "project": project.name,
        "project_path": str(project),
        "indexed_at": _now_iso(),
        "embedding_model": embedding_label,
        "chunk_strategy": strategy,
        "stats": {
            "files": len(index_files),
            "chunks": len(all_chunks),
            "tokens": total_tokens,
            "embedding": embedding_label,
        },
        "files": index_files,
    }

    # 保存索引清单
    index_path = idx_dir / REPORT_FILENAME
    index_path.write_text(json.dumps(index_doc, ensure_ascii=False, indent=2),
                          encoding="utf-8")

    # 保存分块数据(供 search.py 检索)
    chunks_path = idx_dir / "chunks.json"
    chunks_doc = [{"file": c["file"], "start": c["start"], "end": c["end"],
                   "text": c["text"][:2000], "language": c["language"]}
                  for c in all_chunks]  # 限制每块 2000 字符防过大
    chunks_path.write_text(json.dumps(chunks_doc, ensure_ascii=False, indent=2),
                           encoding="utf-8")

    print(f"PASS  索引构建完成:{project.name}")
    print(f"  文件数:{len(index_files)}  分块数:{len(all_chunks)}  token:{total_tokens}")
    print(f"  嵌入模式:{embedding_label}  分块策略:{strategy}")
    print(f"  索引位置:{idx_dir}")
    return 0


def cmd_update(args):
    """update:增量更新。"""
    project = Path(args.project).resolve()
    idx_dir = _index_dir(project)
    index_path = idx_dir / REPORT_FILENAME

    if not index_path.exists():
        print("WARN  索引不存在,转为全量 build")
        args.chunk_strategy = "hybrid"
        args.embedding = "local"
        return cmd_build(args)

    # 读旧索引
    try:
        old_index = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"FAIL  读取旧索引失败:{e}")
        return 1

    old_files = {f["path"]: f for f in old_index.get("files", [])}
    strategy = old_index.get("chunk_strategy", "hybrid")

    files = _scan_code_files(project)
    updated = 0
    added = 0
    removed = 0
    index_files = []

    current_paths = set()
    for f in files:
        rel = str(f.relative_to(project)).replace("\\", "/")
        current_paths.add(rel)
        h = _file_hash(f)
        old = old_files.get(rel)

        if old and old["hash"] == h:
            # 未变更,保留
            index_files.append(old)
        else:
            # 变更或新增,重新索引
            chunks = _split_into_chunks(f, strategy)
            lang = _detect_language(f)
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime).isoformat(timespec="seconds")
            except Exception:
                mtime = ""
            index_files.append({
                "path": rel, "hash": h, "mtime": mtime,
                "chunks": len(chunks), "language": lang,
                "lines": _count_lines(f),
            })
            if old:
                updated += 1
            else:
                added += 1

    # 检测删除
    for old_path in old_files:
        if old_path not in current_paths:
            removed += 1

    # 如果有变更,重建 chunks.json(简化:有变更就全量重建分块)
    if added or updated or removed:
        all_chunks = []
        total_tokens = 0
        for f in files:
            rel = str(f.relative_to(project)).replace("\\", "/")
            chunks = _split_into_chunks(f, strategy)
            lang = _detect_language(f)
            for (start, end, text) in chunks:
                tokens = _estimate_tokens(text)
                total_tokens += tokens
                all_chunks.append({"file": rel, "start": start, "end": end,
                                   "text": text[:2000], "language": lang})

        chunks_path = idx_dir / "chunks.json"
        chunks_path.write_text(json.dumps(all_chunks, ensure_ascii=False, indent=2),
                               encoding="utf-8")
    else:
        total_tokens = old_index.get("stats", {}).get("tokens", 0)

    # 更新索引清单
    old_index["indexed_at"] = _now_iso()
    old_index["stats"] = {
        "files": len(index_files),
        "chunks": sum(f["chunks"] for f in index_files),
        "tokens": total_tokens,
        "embedding": old_index.get("embedding_model", "none"),
    }
    old_index["files"] = index_files
    index_path.write_text(json.dumps(old_index, ensure_ascii=False, indent=2),
                          encoding="utf-8")

    print(f"PASS  增量更新完成:{project.name}")
    print(f"  新增:{added}  更新:{updated}  删除:{removed}")
    return 0


def cmd_stats(args):
    """stats:输出索引统计。"""
    project = Path(args.project).resolve()
    idx_dir = _index_dir(project)
    index_path = idx_dir / REPORT_FILENAME

    if not index_path.exists():
        print(f"FAIL  索引不存在,请先 build:{project.name}")
        return 1

    try:
        index_doc = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"FAIL  读取索引失败:{e}")
        return 1

    stats = index_doc.get("stats", {})
    print(f"项目:{index_doc.get('project', project.name)}")
    print(f"  最后索引:{index_doc.get('indexed_at', 'unknown')}")
    print(f"  嵌入模式:{stats.get('embedding', 'none')}")
    print(f"  分块策略:{index_doc.get('chunk_strategy', 'hybrid')}")
    print(f"  文件数:{stats.get('files', 0)}")
    print(f"  分块数:{stats.get('chunks', 0)}")
    print(f"  token 数:{stats.get('tokens', 0)}")
    print(f"  索引位置:{idx_dir}")
    return 0


# ---------- argparse ----------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="index_codebase.py",
        description="Context 层代码库索引脚本。构建/更新/统计持久化代码索引。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python index_codebase.py build --project /path/to/project\n"
            "  python index_codebase.py update --project /path/to/project\n"
            "  python index_codebase.py stats --project /path/to/project\n"
            "\n退出码:0=成功;1=有错误;2=参数错误"
        ),
    )
    sub = parser.add_subparsers(dest="command", metavar="<子命令>")

    p_build = sub.add_parser("build", help="全量索引")
    p_build.add_argument("--project", required=True, help="项目路径")
    p_build.add_argument("--chunk-strategy", default="hybrid",
                         choices=["file", "function", "semantic", "hybrid"],
                         help="分块策略(默认 hybrid)")
    p_build.add_argument("--embedding", default="local",
                        choices=["local", "none", "api"],
                        help="嵌入模式(默认 local,无库时降级为 none)")
    p_build.set_defaults(func=cmd_build)

    p_update = sub.add_parser("update", help="增量更新")
    p_update.add_argument("--project", required=True, help="项目路径")
    p_update.set_defaults(func=cmd_update)

    p_stats = sub.add_parser("stats", help="索引统计")
    p_stats.add_argument("--project", required=True, help="项目路径")
    p_stats.set_defaults(func=cmd_stats)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 2
    try:
        return args.func(args)
    except Exception as e:
        print(f"FAIL  未捕获异常:{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
