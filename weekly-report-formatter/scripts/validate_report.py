#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
weekly-report-formatter 格式校验器

用法:
    python validate_report.py <周报文件.md>           # 校验，有错 exit 1
    python validate_report.py <周报文件.md> --strict  # 警告也当错误
    python validate_report.py -                       # 从 stdin 读

校验项（错误 E* / 警告 W*）:
    E1 项目块缺少日期行
    E2 阶段名不在白名单
    E3 交付时间非法（空括号 / 待定 / 格式错误）
    E4 进展描述为空或过短（< 6 字）
    E5 项目块没有任何进展条目
    E6 延期行未写明「原定」时间
    W1 描述为套话（正常推进 / 按计划 等）
    W2 报告日期不是今天
    W3 存在空阶段占位行（开发中：无 / 暂无）
"""
import re
import sys
from datetime import date

STAGES = [
    "设计完成待开发",
    "测试完成待上线",
    "方案阶段",
    "代码上线",
    "开发中",
    "设计中",
    "测试中",
    "延期",
]

DATE_LINE = re.compile(r"^\s*(\d{4})年(\d{1,2})月(\d{1,2})日\s*[：:]?\s*(.*)$")

ENTRY = re.compile(
    r"^\s*(?:(?P<func>[^：:（）()]{1,30})[：:])?\s*"
    r"(?P<stage>" + "|".join(STAGES) + r")"
    r"(?:\s*[（(](?P<due>[^）()]*)[）)])?"
    r"\s*[：:]\s*(?P<desc>.+?)\s*$"
)

# 交付时间括号内允许的前缀（用户口径：「（交付时间：2026-10-14）」或「（交付时间2026-10-14）」）
DUE_PREFIX = re.compile(r"^(?:交付时间|上线时间|提测时间)\s*[：:]?\s*")

ISO = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")
CN_DATE = re.compile(r"(\d{1,2})月(\d{1,2})日")
VAGUE_OK = re.compile(r"月(底|初|中旬|下旬)|第\s*\d+\s*周|本周|下周|本月|下月|季度|Q\d")
STAGE_HINT = ["阶段", "设计", "开发", "测试", "上线", "延期", "研发", "提测", "发布", "联调", "排期"]
PLACEHOLDER = re.compile(r"^(无|暂无|待定|无进展|同上|见上|TBD|N/A)[。.、,，]?$")
CLICHE = ["正常推进", "按计划", "无异常", "持续跟进", "顺利进行", "有序推进", "暂无问题", "正常进行"]


def check_due(due, stage, lineno, errors):
    due = (due or "").strip()
    if due == "":
        errors.append((lineno, "E3", "交付时间为空括号「（）」——无排期时应整体省略括号"))
        return
    due = DUE_PREFIX.sub("", due).strip()  # 去掉「交付时间」等前缀后再校验
    if due == "":
        errors.append((lineno, "E3", "括号内只写了「交付时间」没有具体时间，应写「（交付时间：YYYY-MM-DD）」"))
        return
    for bad in ("待定", "TBD", "未定", "暂无"):
        if bad in due and not (stage == "延期" and "原定" in due):
            errors.append((lineno, "E3", f"交付时间含禁用词「{bad}」（仅延期行可写「原定 X，待定」）"))
            return
    if stage == "延期" and "原定" not in due:
        errors.append((lineno, "E6", "延期行未写明「原定」时间，应写（原定 YYYY-MM-DD，现 YYYY-MM-DD）"))
    for m in ISO.finditer(due):
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            date(y, mo, d)
        except ValueError:
            errors.append((lineno, "E3", f"非法日期「{m.group(0)}」"))
    for m in CN_DATE.finditer(due):
        mo, d = int(m.group(1)), int(m.group(2))
        if not (1 <= mo <= 12 and 1 <= d <= 31):
            errors.append((lineno, "E3", f"非法日期「{m.group(0)}」"))
    has_iso = bool(ISO.search(due))
    has_cn = bool(CN_DATE.search(due))
    has_vague = bool(VAGUE_OK.search(due))
    if not (has_iso or has_cn or has_vague):
        errors.append((lineno, "E3", f"交付时间「{due}」无法识别（支持 YYYY-MM-DD / M月D日 / M月底 / M月第N周）"))


def validate(text, strict=False):
    errors, warns = [], []
    lines = text.splitlines()

    current_project = None
    project_has_date = False
    project_has_entry = False
    in_todo = False  # 进入「⚠️ 待补充」区块后，其后所有行不再参与格式校验

    def close_project(lineno):
        nonlocal project_has_date, project_has_entry, current_project
        if current_project is not None:
            if not project_has_date:
                errors.append((lineno, "E1", f"项目「{current_project}」缺少日期行（YYYY年M月D日：）"))
            if not project_has_entry:
                errors.append((lineno, "E5", f"项目「{current_project}」没有任何进展条目"))
        current_project = None  # 清空，避免同一项目被结算两次
        project_has_date = False
        project_has_entry = False

    for i, raw in enumerate(lines, 1):
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.lstrip().startswith(("#", "```", ">", "---", "===")):
            continue
        if in_todo:
            continue
        if line.lstrip().startswith("⚠"):
            close_project(i)
            in_todo = True
            continue

        m_date = DATE_LINE.match(line)
        if m_date:
            y, mo, d = int(m_date.group(1)), int(m_date.group(2)), int(m_date.group(3))
            try:
                rd = date(y, mo, d)
            except ValueError:
                errors.append((i, "E2", f"日期行「{line.strip()}」不是合法日期"))
                continue
            project_has_date = True
            if rd != date.today():
                warns.append((i, "W2", f"报告日期 {rd.isoformat()} 不是今天（{date.today().isoformat()}），请确认是否指定日期"))
            continue

        m_entry = ENTRY.match(line)
        if m_entry:
            project_has_entry = True
            stage = m_entry.group("stage")
            due = m_entry.group("due")
            desc = m_entry.group("desc").strip()
            if stage == "延期" and due is None:
                errors.append((i, "E6", "延期行未写交付时间，应写（原定 YYYY-MM-DD，现 YYYY-MM-DD）"))
            if due is not None:
                check_due(due, stage, i, errors)
            if len(desc) < 6:
                errors.append((i, "E4", f"进展描述过短或为空：「{desc}」"))
            if PLACEHOLDER.match(desc):
                warns.append((i, "W3", f"疑似空阶段占位行：「{line.strip()}」——无进展的整行删除"))
            if len(desc) <= 14 and any(c in desc for c in CLICHE):
                warns.append((i, "W1", f"描述疑似套话：「{desc}」——需补动作+产出物/量化"))
            continue

        # 疑似进展条目但格式不符（如阶段名自造「研发中」）
        if "：" in line and ("（" in line or "(" in line or any(k in line for k in STAGE_HINT)):
            errors.append((i, "E2", f"疑似进展条目但阶段名/格式不合法：「{line.strip()}」——阶段只能取 {STAGES}"))
            continue

        # 其它非空行：视为项目标题
        close_project(i)
        current_project = line.strip()
        if len(current_project) > 40:
            warns.append((i, "W4", f"项目标题过长（{len(current_project)} 字），确认是否为误归类行：{current_project[:30]}…"))

    close_project(len(lines))
    if strict:
        errors.extend(warns)
        warns = []
    return errors, warns


def main():
    try:  # Windows 控制台默认 GBK，强制 UTF-8 输出避免中文乱码
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    strict = "--strict" in sys.argv
    if not args:
        print("用法: python validate_report.py <周报文件.md> [--strict]")
        return 2
    path = args[0]
    if path == "-":
        text = sys.stdin.read()
    else:
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            print(f"[ERROR] 读取失败: {e}")
            return 2

    errors, warns = validate(text, strict)
    if not errors and not warns:
        report = ["✅ 格式校验通过：0 错误 0 警告"]
    else:
        report = [f"❌ L{n} [{c}] {m}" for n, c, m in sorted(errors)]
        report += [f"⚠️  L{n} [{c}] {m}" for n, c, m in sorted(warns)]
        report.append(f"\n合计：{len(errors)} 错误 / {len(warns)} 警告")

    body = "\n".join(report)
    print(body)

    idx = sys.argv.index("--out") if "--out" in sys.argv else -1
    if idx != -1 and idx + 1 < len(sys.argv):  # Windows GBK 控制台乱码时落文件查看
        with open(sys.argv[idx + 1], "w", encoding="utf-8") as f:
            f.write(body + "\n")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
