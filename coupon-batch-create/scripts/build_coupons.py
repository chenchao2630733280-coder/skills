# -*- coding: utf-8 -*-
"""从 Excel 生成后台卡券创建数据
用法: python build_coupons.py [coupon0.xlsx|coupon1.xlsx] [输出json]
"""
import json
import os
import re
import sys
import datetime
import openpyxl

SRC = sys.argv[1] if len(sys.argv) > 1 else "coupon0.xlsx"
OUT = sys.argv[2] if len(sys.argv) > 2 else "coupons.json"
COVER_ROOT = "cover"
YEAR = 2026
LIMIT_START = f"{YEAR}-09-01 00:00:00"

# 可用商户名 -> 后台商户 id
MERCHANT_IDS = {
    "苏州文化艺术中心": 594,
    "苏州保利大剧院": 589,
    "苏州湾大剧院": 593,
    "苏州狮山大剧院": 592,
    "苏州开明大戏院": 590,
    "中国昆曲剧院": 595,
    "光裕书厅": 588,
    "苏州昆曲传习所": 591,
    "北部市民中心青橙剧场": 587,
}

USAGE_TEXT = """权益名称：“知苏”乐游指南
活动提供单位全称：苏州市文化广电和旅游局
权益说明：
提供一定数量的剧院演出票，新生可在“苏周到”APP免费领取，领取成功后可至相应剧院观看演出。
使用时间：领取后至2026年11月30日。
使用说明：下载并注册登录“苏周到”APP，进入高校新生开学季专题页面，点击相关网页链接进行领取，领取成功后线下至相应剧院前台或票务中心核销使用。演出票数量有限，先到先得，领完即止。
咨询电话：苏州文化艺术中心0512-62899875或4008288299；苏州保利大剧院0512-65027666或0512-65027888；苏州湾大剧院19551012000（9:00-17:00）；苏州狮山大剧院4009282200；开明大戏院 17751132009（周一至周五9:00-17:00）；中国昆曲剧院 0512-69165602；光裕书厅0512-65233735；北部市民中心青橙剧场4008288299；苏州昆曲传习所13915411217。"""

IMG_EXT = (".jpg", ".jpeg", ".png")


def venue_top(venue):
    v = str(venue).replace("—", "-").strip()
    return re.split(r"[-—\s]", v)[0]


# 显式封面映射：剧名片段 -> 封面相对路径（用于文件名与剧目名无法自动匹配的情况）
# 值可不写扩展名（源图可能是 .jpg/.png），运行时自动解析
COVER_OVERRIDE = {
    "HEDWIG": "cover/苏州湾大剧院/1百老汇经典摇滚音乐剧《海德薇》",
    "乐园Project": "cover/狮山大剧院/乐园音乐会",
    "高晓攀": "cover/狮山大剧院/高晓攀专场",
    "生活那些事": "cover/苏州湾大剧院/5脱口秀《生活那些事》",
    "吐槽万岁": "cover/苏州湾大剧院/6脱口秀《吐槽万岁》",
}


def resolve_override(v):
    """把无扩展名/扩展名可能变化的 override 路径解析为真实存在的图片"""
    for cand in (v, v + ".jpg", v + ".png", v + ".jpeg"):
        if os.path.isfile(cand):
            return cand.replace("\\", "/")
    d, b = os.path.dirname(v), os.path.basename(v).lower()
    if os.path.isdir(d):
        for p in all_images(d):
            if os.path.splitext(os.path.basename(p))[0].lower() == b:
                return p
    return v.replace("\\", "/")

_all_cover_dirs = [d for d in os.listdir(COVER_ROOT) if os.path.isdir(os.path.join(COVER_ROOT, d))]


def cover_dir(venue):
    v = str(venue).replace("—", "-").strip()
    # cover 顶层目录名出现在场地名中即可
    for d in _all_cover_dirs:
        if d in v:
            return os.path.join(COVER_ROOT, d)
    top = venue_top(venue)
    for c in (top, top.replace("苏州", ""), v):
        p = os.path.join(COVER_ROOT, c)
        if os.path.isdir(p):
            return p
    return None


def pick_in_dir(d):
    files = [f for f in sorted(os.listdir(d)) if f.lower().endswith(IMG_EXT)]
    if not files:
        return None
    for f in files:
        if re.search(r"横[板版]", f):
            return os.path.join(d, f)
    return os.path.join(d, files[0])


def all_images(base):
    """递归收集 base 下所有图片（含子目录，如「海报/」），返回规范化路径列表"""
    res = []
    for root, dirs, files in os.walk(base):
        dirs.sort()
        for f in sorted(files):
            if f.lower().endswith(IMG_EXT):
                res.append(os.path.join(root, f).replace("\\", "/"))
    return res


def norm(s):
    return re.sub(r"[《》【】\[\]（）()·\s|：:]", "", str(s))


def parse_date_prefix(fname):
    """从文件名解析日期前缀，返回 '月.日' 集合。
    10.2-3玉蜻蜓.jpg   -> {'10.2', '10.3'}
    11.16-17水上新娘.png -> {'11.16', '11.17'}
    10.4经典越剧折子戏专场.jpg -> {'10.4'}
    """
    m = re.match(r"^(\d{1,2})\.(\d{1,2})(?:-(\d{1,2}))?", fname)
    if not m:
        return None
    month, d1, d2 = int(m.group(1)), int(m.group(2)), m.group(3)
    days = {f"{month}.{d1}"}
    if d2:
        for d in range(d1, int(d2) + 1):
            days.add(f"{month}.{d}")
    return days


def find_cover_by_date(base, md):
    """按 '月.日'（如 10.2）在目录里找日期前缀匹配的文件（递归子目录）"""
    for p in all_images(base):
        days = parse_date_prefix(os.path.basename(p))
        if days and md in days:
            return p
    return None


def find_cover(seq, drama, venue, show_date=None):
    for k, v in COVER_OVERRIDE.items():
        if k in str(drama):
            return resolve_override(v)
    base = cover_dir(venue)
    if not base:
        return None
    # 日期前缀优先（保利等以「月.日」命名的目录）
    if show_date:
        m = re.match(r"(\d+)月(\d+)日", str(show_date))
        if m:
            c = find_cover_by_date(base, f"{int(m.group(1))}.{int(m.group(2))}")
            if c:
                return c
    imgs = all_images(base)
    if seq is not None:
        for p in imgs:
            f = os.path.basename(p)
            if re.match(rf"^{int(seq)}\s*[^0-9]", f) or re.match(rf"^{int(seq)}\.", f):
                return p
    dp = norm(drama)
    # 子目录名（剧目文件夹）匹配
    for p in imgs:
        sub = os.path.dirname(p)
        if sub and os.path.normpath(sub) != os.path.normpath(base):
            fp = norm(os.path.basename(sub))
            if fp and (fp in dp or dp in fp):
                return pick_in_dir(sub)
    for p in imgs:
        fp = re.sub(r"^\d+", "", norm(os.path.splitext(os.path.basename(p))[0]))
        if fp and (fp in dp or dp in fp):
            return p
    return None


def next_day(dstr):
    m = re.match(r"(\d+)月(\d+)日", dstr)
    d = datetime.date(YEAR, int(m.group(1)), int(m.group(2))) + datetime.timedelta(days=1)
    return f"{d.year}-{d.month:02d}-{d.day:02d} 00:00:00"


def show_start(dstr):
    m = re.match(r"(\d+)月(\d+)日", dstr)
    return f"{YEAR}-{int(m.group(1)):02d}-{int(m.group(2)):02d} 00:00:00"


wb = openpyxl.load_workbook(SRC)
ws = wb.active
rows = [r for r in ws.iter_rows(min_row=2, values_only=True) if r[1]]

out, missing_cover, missing_merchant = [], [], []
for r in rows:
    seq, drama, show_date, venue, unit, sessions, per_show = r[0], r[1], r[2], r[3], r[4], r[5], r[6]
    merchant_name = str(r[10]).strip() if len(r) > 10 and r[10] else venue_top(venue)
    cover = find_cover(seq, drama, venue, show_date)
    merchant_id = MERCHANT_IDS.get(merchant_name)
    name = f"{drama}{show_date}"
    if not cover:
        missing_cover.append((seq, drama, str(venue)))
    if not merchant_id:
        missing_merchant.append((seq, merchant_name))
    out.append({
        "序号": seq,
        "卡券名称": name,
        "商品名称": name,
        "剧目名称": drama,
        "演出日期": str(show_date),
        "演出场地": venue,
        "商家名称": str(venue).strip(),
        "可用商户": merchant_name,
        "可用商户id": merchant_id,
        "封面": cover.replace("\\", "/") if cover else None,
        "兑换数量": 1,
        "领取开始": LIMIT_START,
        "领取结束": next_day(str(show_date)),
        "有效开始": show_start(str(show_date)),
        "有效结束": next_day(str(show_date)),
        "单人限领": 1,
        "最大发行数量": int(per_show),
        "使用须知": USAGE_TEXT,
    })

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print(f"源文件: {SRC}  共 {len(out)} 条 -> {OUT}")
print(f"缺封面: {len(missing_cover)} 条")
for m in sorted(set(missing_cover), key=lambda x: (x[0] is None, x[0])):
    print("   -", m)
print(f"缺商户: {len(missing_merchant)} 条")
for m in sorted(set(missing_merchant)):
    print("   -", m)
