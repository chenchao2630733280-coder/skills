#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""search.py - Context 层代码库检索脚本。

子命令:
  query  --project <路径> --query "自然语言查询" [--top-k 5]
  locate --project <路径> --symbol "函数名/类名"

设计原则:
- 有嵌入库:语义检索(TF-IDF 相关度排序)
- 无嵌入库:降级为关键词匹配(子串 + 词频)
- 失败不抛异常,统一通过 error 字段与退出码表达

退出码:0=成功;1=有错误;2=参数错误
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
    from sklearn.metrics.pairwise import cosine_similarity  # type: ignore
    HAS_SKLEARN = True
except Exception:
    HAS_SKLEARN = False


# ---------- 常量 ----------

SCRIPT_DIR = Path(__file__).resolve().parent
INDEX_ROOT = Path.home() / ".trae-cn" / "codebase-index"
CHUNKS_FILENAME = "chunks.json"
INDEX_FILENAME = "codebase-index.json"


# ---------- 工具函数 ----------

def _now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _project_name(project_path):
    return Path(project_path).resolve().name


def _index_dir(project_path):
    return INDEX_ROOT / _project_name(project_path)


def _load_chunks(idx_dir):
    """加载分块数据。"""
    chunks_path = idx_dir / CHUNKS_FILENAME
    if not chunks_path.exists():
        return None, "chunks.json 不存在,请先 build 索引"
    try:
        return json.loads(chunks_path.read_text(encoding="utf-8")), None
    except Exception as e:
        return None, f"读取 chunks.json 失败:{e}"


def _keyword_search(chunks, query, top_k):
    """降级:关键词匹配(子串 + 词频评分)。"""
    query_lower = query.lower()
    query_terms = re.findall(r"\w+", query_lower)
    scored = []
    for c in chunks:
        text = c.get("text", "").lower()
        # 子串匹配加分
        score = 0.0
        if query_lower in text:
            score += 10.0
        # 词频加分
        for term in query_terms:
            count = text.count(term)
            score += count
        if score > 0:
            scored.append({
                "file": c["file"], "start": c["start"], "end": c["end"],
                "score": round(score, 2),
                "snippet": c["text"][:200].replace("\n", " "),
            })
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def _tfidf_search(chunks, query, top_k):
    """TF-IDF 语义检索。"""
    if not HAS_SKLEARN:
        return None, "scikit-learn 不可用"
    texts = [c.get("text", "") for c in chunks]
    try:
        vectorizer = TfidfVectorizer(max_features=5000)
        matrix = vectorizer.fit_transform(texts)
        query_vec = vectorizer.transform([query])
        sims = cosine_similarity(query_vec, matrix).flatten()
    except Exception as e:
        return None, f"TF-IDF 检索失败:{e}"

    scored = []
    for i, sim in enumerate(sims):
        if sim > 0.01:  # 过滤极低相关度
            c = chunks[i]
            scored.append({
                "file": c["file"], "start": c["start"], "end": c["end"],
                "score": round(float(sim), 4),
                "snippet": c["text"][:200].replace("\n", " "),
            })
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k], None


# ---------- 子命令实现 ----------

def cmd_query(args):
    """query:语义/关键词检索。"""
    project = Path(args.project).resolve()
    idx_dir = _index_dir(project)
    if not idx_dir.exists():
        print(f"FAIL  索引不存在,请先 build:{project.name}")
        return 1

    chunks, err = _load_chunks(idx_dir)
    if err:
        print(f"FAIL  {err}")
        return 1

    if not chunks:
        print(f"FAIL  无分块数据:{project.name}")
        return 1

    query = args.query
    top_k = args.top_k

    # 优先 TF-IDF,降级关键词
    if HAS_SKLEARN:
        results, err = _tfidf_search(chunks, query, top_k)
        if err:
            print(f"WARN  TF-IDF 检索失败,降级关键词匹配:{err}")
            results = _keyword_search(chunks, query, top_k)
            mode = "keyword"
        else:
            mode = "tfidf"
    else:
        results = _keyword_search(chunks, query, top_k)
        mode = "keyword"

    print(f"检索完成:{project.name}  模式:{mode}  命中:{len(results)}")
    for r in results:
        print(f"  [{r['score']}] {r['file']}:{r['start']}-{r['end']}")
        print(f"    {r['snippet']}")
    return 0


def cmd_locate(args):
    """locate:精确符号定位。"""
    project = Path(args.project).resolve()
    idx_dir = _index_dir(project)
    if not idx_dir.exists():
        print(f"FAIL  索引不存在,请先 build:{project.name}")
        return 1

    chunks, err = _load_chunks(idx_dir)
    if err:
        print(f"FAIL  {err}")
        return 1

    if not chunks:
        print(f"FAIL  无分块数据:{project.name}")
        return 1

    symbol = args.symbol
    # 符号模式:匹配 def/class/function/func 定义行
    patterns = [
        rf"(def|class|function|func|fn|public|private|protected)\s+{re.escape(symbol)}\b",
        rf"\b{re.escape(symbol)}\s*\(",  # 函数调用/定义
    ]

    results = []
    for c in chunks:
        text = c.get("text", "")
        lines = text.split("\n")
        for i, line in enumerate(lines):
            for pat in patterns:
                if re.search(pat, line):
                    abs_line = c["start"] + i
                    results.append({
                        "file": c["file"], "line": abs_line,
                        "snippet": line.strip()[:150],
                    })
                    break

    print(f"符号定位:{symbol}  命中:{len(results)}")
    for r in results[:20]:  # 限制 20 条
        print(f"  {r['file']}:{r['line']}  {r['snippet']}")
    return 0


# ---------- argparse ----------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="search.py",
        description="Context 层代码库检索脚本。语义检索/关键词匹配/符号定位。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python search.py query --project /path/to/project --query \"处理用户登录\"\n"
            "  python search.py locate --project /path/to/project --symbol \"LoginService\"\n"
            "\n退出码:0=成功;1=有错误;2=参数错误"
        ),
    )
    sub = parser.add_subparsers(dest="command", metavar="<子命令>")

    p_query = sub.add_parser("query", help="语义/关键词检索")
    p_query.add_argument("--project", required=True, help="项目路径")
    p_query.add_argument("--query", required=True, help="自然语言查询")
    p_query.add_argument("--top-k", type=int, default=5, help="返回结果数(默认 5)")
    p_query.set_defaults(func=cmd_query)

    p_locate = sub.add_parser("locate", help="精确符号定位")
    p_locate.add_argument("--project", required=True, help="项目路径")
    p_locate.add_argument("--symbol", required=True, help="符号名(函数/类)")
    p_locate.set_defaults(func=cmd_locate)

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
