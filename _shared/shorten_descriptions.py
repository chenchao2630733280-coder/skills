"""把超长 description 收进 200 字符内（一次性脚本，改完可留作回归）。

规矩（见 _shared/README.md）:
  * CRLF 安全：按原文件的 EOL 切行、回写，不整篇替换行尾。
  * 只动 description 字段所占的那几行，frontmatter 其余字段原样不动。
  * 不写死行号，靠 YAML 缩进/顶层 key 判定字段边界（description 可能跨行）。

用法:
    python _shared/shorten_descriptions.py --dry     # 只报告，不写盘
    python _shared/shorten_descriptions.py
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESC_LIMIT = 200

# 名字 -> 新描述。要求：<=200 字符、保留「做什么 + 何时用」、保留原触发词。
NEW = {
    "ai-short-drama-topic-planner": "Generate, diversify and evaluate AI short-drama topics with a hard accessibility gate (one-line pitch / visualizable premise / physical payoff). 用于短剧选题、高概念前提、观看动机、趋势雷达、选题对比。",
    "banner-design": "Design banners for social media, ads, website heroes and print. Multiple art directions, platform-correct sizes, styles from minimalist to 3D/neon/duotone, AI visuals.",
    "bid-functional-solution": "Create or revise 标书功能建设方案 from PRDs, requirement specs, screenshot folders, prototypes or DOCX. 用于功能说明/功能描述改写、从 UI 图推功能、裁范围、出 Word 交付件。",
    "brainstorm-product-feature": "Refine an early product feature idea before PRD writing: clarification questions, hidden-assumption checks, feasibility, user flows, risks, edge cases, constraints, alternatives.",
    "build-working-system": "Orchestrate the whole conversion of PRD, page specs and prototypes into a runnable, tested, deployable system. Use when asked to build or finish the entire system, not one layer.",
    "coupon-batch-create": "把「场次明细」Excel 批量建为苏州卡券平台兑换券；也用于封面重裁、批量换封面、核验。当用户说「批量建卡券」「补建演出票卡券」「替换卡券封面」时使用。",
    "delivery-consistency-gate": "多副本交付物一致性门禁。当同一事实散落在 spec JSON、多端 HTML、文档、门户镜像、构建报告时调用：四方一致、单一数据源投影、派生不变量、陈旧术语扫描，产出可复跑门禁脚本。",
    "design-system": "Token architecture and component specs: three-layer tokens (primitive→semantic→component), CSS variables, spacing/typography scales, component specifications, brand-compliant slides.",
    "design": "Design hub: brand identity, design tokens, UI styling, logo/CIP mockups, slides, banners, icons, social photos. 用于设计 logo、生成 CIP、做幻灯片、设计横幅、生成图标、社媒图。",
    "frontend-design": "Guidance for distinctive, intentional visual design when building new UI or reshaping an existing one: aesthetic direction, typography, avoiding templated defaults.",
    "generate-system-prd": "Generate structured PRDs for enterprise systems, native apps, mobile web, mini programs and multi-end products, with terminal-specific rules for domain models, flows, pages, permissions and NFRs.",
    "html-single-file-pack": "把多文件静态站点打包成自包含单文件 HTML（CSS/JS/图片全内联，双击即开）。当「云端上传后图片全裂」「发给别人打开空白」「需要离线单文件交付」时调用。",
    "implement-backend": "Implement production backend APIs, domain services, validation, authorization, auditing, integrations and tests from PRD and architecture contracts. Use for the server side.",
    "implement-data-layer": "Implement production schemas, migrations, constraints, seed data, repositories and transaction rules from the data model and implementation plan. Use for the persistence layer.",
    "integrate-system": "Integrate frontend, backend, database, auth, permissions, files, async jobs and external services into a runnable end-to-end system. Use when replacing mocks with real flows.",
    "modlens": "Read images for text-only models. When an image path/URL, `[Image #1]` or `[Unsupported Image]` appears and you cannot see it, run this before any OCR; returns structured JSON evidence.",
    "opportunity-screening": "个人/小团队商业机会的挖掘、筛选与自身适配评估。当用户问「我该做什么副业」「这个方向能不能做」「是不是红海」「没人脉能做吗」时调用。四层漏斗 + 评分脚本。",
    "package-and-deploy-system": "Prepare a verified app for reproducible local and production deployment: containers, env contracts, CI/CD, migrations, health checks, observability, backup, rollback, release docs.",
    "plan-system-implementation": "Create an executable technical implementation plan from PRD, page specs, prototype and repository: architecture, stack, module boundaries, API contracts, delivery increments.",
    "prd-quality-checker": "审核通用 PRD、需求说明或需求基线，支持一次性 Audit 与逐题 Improve。检查目标、范围、流程、规则、状态、权限、异常、一致性、追踪、验收与交付准备度，输出门禁报告。",
    "research_delivery_workflow": "Convert raw research/interview notes into an as-is business analysis, requirement pool, PRD draft, capability architecture, page structure, handoff input and delivery plan, with source traceability.",
    "ruanzhu-doc-generator": "Generate 软著申请文档 DOCX from product screenshots for PC backends and mobile apps/mini programs. 用于软著文档、产品说明书、操作说明书；PC 与移动端拆成两份 DOCX。",
    "screenshot-operation-manual": "Generate PC admin and mobile operation manuals from screenshots or recordings. 产出手册/用户指南（DOCX/PDF/Markdown/HTML）：模块说明、截图配文、字段、步骤、流程、FAQ。",
    "short-drama-asset-forge": "Short-drama stage 4.5: lock the asset baseline. Reads ASSET_MANIFEST/VISUAL_SPEC/STORYBOARD, builds characters, scenes, props, voice and style baseline, writes back hash/lockedAt. Blocks stage 5.",
    "short-drama-audio-forge": "Short-drama stage 6 (audio, parallel with video-forge). Reads scripts and storyboard, produces voice-over line_{XX}.mp3, BGM and subtitles/{ep}.srt. 用于配音/BGM/音效/字幕。",
    "short-drama-blueprint": "Short-drama stage 1: turn a confirmed topic into a one-page blueprint covering genre, platform, core selling point, production type, scope, monetization, toolchain, complexity and artifact scale.",
    "short-drama-edit": "Short-drama stage 7 (final edit + Gate 5). Reads the production manifest, shots, audio and subtitles, assembles episodes/EP{XX}.mp4, writes BUILD_REPORT.md. 用于剪辑/合成/成片。",
    "short-drama-forge-master": "短剧制作流水线总纲。接收一句话需求，判定短剧类型与路径（全AI/图文/真人辅助/口播），选工具链、裁剪阶段、串联 9 个阶段 skill 与 Gate 0~4/3.5。当用户要「用 AI 制作一部短剧」「从选题到成片」时调用。",
    "short-drama-game-adapt": "把已有短剧/影视/小说/热梗的设定与爽点转化为游戏机制。当用户想「把某个短剧改成游戏」、做 IP 改编游戏化、为小游戏找题材切入点时调用。提取设定做机制，不搬剧情。",
    "short-drama-quality-gate": "Cross-stage quality gate for the short-drama pipeline. Runs contract validation and runtime pre-checks at Gates 0,1,2,3,3.5,4; on FAIL it hard-blocks and returns fixes. Writes gate reports only.",
    "short-drama-script": "Short-drama stage 3: read STORY_SPEC and EPISODE_OUTLINE, write formal vertical-screen scripts one file per episode at docs/scripts/EP{01..NN}.md, 1-3 min each, 5s hook, cliffhanger.",
    "short-drama-spec": "Short-drama stage 2: expand the approved topic into docs/STORY_SPEC.md (story engine, rules, characters, secrets, stages, emotion curve, scoring) plus EPISODE_OUTLINE.md per-episode outline.",
    "short-drama-storyboard": "Short-drama stage 4: turn the script into docs/STORYBOARD.md with per-shot text-to-image and image-to-video prompts, VISUAL_SPEC.md, and ASSET_MANIFEST.json declaring every asset for stage 4.5.",
    "short-drama-topic-brainstorm": "Short-drama stage 0 (optional): generate, diversify and rank topics from a vague one-line idea, outputting docs/TOPIC_PROPOSAL.md for short-drama-blueprint. 用于短剧选题、找方向、选题提案。",
    "short-drama-video-forge": "Short-drama stage 5: build production/manifest.json from STORYBOARD/VISUAL_SPEC and LOCKED ASSET_MANIFEST (assets by id+variant+hash), generate shots/{ep}/shot_{XX}.mp4. Never from unlocked assets.",
    "ai-short-drama-project-development": None,  # 行数问题，不在此脚本处理
    "ui-styling": "Build accessible interfaces with shadcn/ui (Radix + Tailwind) and canvas visuals. Use for components, design systems, responsive layouts, theming, dark mode, posters and visual designs.",
    "ui-ux-pro-max": "UI/UX design intelligence for web and mobile: a searchable local database of styles, palettes, font pairings, product types, UX guidelines, icons, motion presets and chart types across 22 stacks.",
    "web-static-deploy": "Deploy static HTML/JS and Vite/React/Vue builds to GitHub Pages, Vercel, Netlify, CloudBase or COS. Decides PURE STATIC vs NEEDS A DATABASE, then runs the path and covers silent-404 modes.",
}


def read_eol(raw):
    return "\r\n" if "\r\n" in raw else "\n"


def desc_span(lines):
    """返回 description 字段所占的行区间 [start, end)；找不到返回 None。

    注意：必须把 frontmatter 的收尾 --- 当作硬边界。否则会把收尾符当成
    description 的缩进续行吞掉，删掉 --- 之后整个 frontmatter 就废了，
    平台读不到 description（表现为统计里 desc=-1）。
    """
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^description:", line):
            start = i
            break
    if start is None:
        return None
    end = start + 1
    while end < len(lines):
        nxt = lines[end]
        if nxt.strip() == "---":  # frontmatter 收尾，绝不能吞
            break
        if re.match(r"^[A-Za-z_][\w-]*:", nxt):  # 下一个顶层 key
            break
        if nxt.strip() == "":
            break
        end += 1
    return start, end


def sanity(lines, expect):
    """回写前自检：frontmatter 结构完整 + description 值能被重新解析出来。"""
    marks = [i for i, l in enumerate(lines) if l.strip() == "---"]
    if len(marks) < 2:
        return "frontmatter 收尾 --- 丢失"
    if marks[0] != 0:
        return "首行不是 ---"
    fm = lines[marks[0] + 1:marks[1]]
    got = None
    for i, line in enumerate(fm):
        m = re.match(r"^description:\s*(.*)$", line)
        if not m:
            continue
        first = m.group(1).strip()
        if len(first) >= 2 and first[0] == first[-1] == '"':
            got = first[1:-1]
        else:  # 又变成跨行写法了
            got = " ".join([first] + [x.strip() for x in fm[i + 1:]])
        break
    if got is None:
        return "回写后解析不到 description"
    if got != expect:
        return "回写后 description 与预期不一致"
    return None


def main():
    dry = "--dry" in sys.argv
    changed, skipped = [], []
    for name, new in NEW.items():
        if new is None:
            continue
        path = os.path.join(ROOT, name, "SKILL.md")
        if not os.path.exists(path):
            skipped.append((name, "文件不存在"))
            continue
        if len(new) > DESC_LIMIT:
            skipped.append((name, f"新描述仍超限({len(new)})"))
            continue
        raw = open(path, "rb").read().decode("utf-8")
        eol = read_eol(raw)
        lines = raw.split(eol)
        span = desc_span(lines)
        if span is None:
            skipped.append((name, "未找到 description"))
            continue
        old_len = len(" ".join(l.strip() for l in lines[span[0]:span[1]]))
        lines[span[0]:span[1]] = ['description: "%s"' % new]
        why = sanity(lines, new)
        if why:
            skipped.append((name, why))
            continue
        if not dry:
            open(path, "wb").write(eol.join(lines).encode("utf-8"))
        changed.append((name, old_len, len(new)))

    for name, a, b in changed:
        print(f"{a:4d} -> {b:3d}  {name}")
    for name, why in skipped:
        print(f"  跳过 {name}: {why}")
    print(f"{'预演' if dry else '已改写'} {len(changed)} 个，跳过 {len(skipped)} 个")


if __name__ == "__main__":
    main()
