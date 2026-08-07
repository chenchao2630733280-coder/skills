# rd-init

---
name: "rd-init"
description: "产研项目脚手架初始化。根据初步需求创建标准目录结构、project-brief.json 和 project.yaml，为 product-pipeline-master 流水线提供起始输入。仅用于新项目初始化，不生成 PRD、原型、代码或测试。"
---

## 一、触发条件

当用户输入类似下面内容时调用：

```text
请调用 rd-init 初始化项目。
初步需求如下：需求内容
```

或用户直接给出需求描述，要求初始化产研项目时。

## 二、前置输入

| 输入 | 来源 | 说明 |
|------|------|------|
| 初步需求文本 | 用户输入 | 包含项目名称、核心功能、目标用户等 |
| --target-dir | 命令行参数 | 目标项目目录，默认当前目录 |

需求文本支持以下字段（均可选，缺失标记"待确认"）：

- 项目名称 / 产品名称 / 系统名称
- 行业 / 行业领域
- 产品类型 / 系统类型
- 目标用户 / 用户 / 使用者
- 核心价值 / 产品价值
- 业务目标 / 目标
- 核心功能 / 主要功能 / 功能 / 模块
- 技术要求 / 技术方向 / 技术栈

## 三、产出契约

| 产物 | 路径 | 说明 |
|------|------|------|
| 项目简报 | `docs/project-brief.json` | 结构化需求简报，供 brainstorm-product-feature 消费 |
| 项目配置 | `project.yaml` | 项目元数据+流水线上下文 |
| 需求原文 | `docs/FEATURE_BRASTORM.md` | 用户输入的原始需求文本 |
| 目录结构 | `output/spec/` `output/prototype/` `output/site/` `output/build/` | 产研流水线标准输出目录（空目录+.gitkeep） |
| 初始化元数据 | `.rd-init.json` | 初始化来源、时间、下一步指引 |

**标准目录结构**：

```
项目根目录/
├── docs/                    ← 文档
│   ├── project-brief.json   ← 结构化需求简报（本 skill 产出）
│   └── FEATURE_BRAINSTORM.md ← 需求原文（本 skill 产出）
├── output/
│   ├── spec/                ← PRD 工件（generate-system-prd 产出）
│   ├── prototype/           ← 原型文档（generate-prototype 产出）
│   ├── site/                ← HTML 原型（generate-html-pages 产出）
│   │   ├── pc/              ← PC 管理后台 HTML
│   │   ├── mobile/          ← 移动端 HTML
│   │   └── assets/          ← 共享资源
│   └── build/               ← 工程实现（implement-* 产出）
├── project.yaml             ← 项目配置（本 skill 产出）
└── .rd-init.json            ← 初始化元数据（本 skill 产出）
```

## 四、执行流程

### 4.1 提取需求

1. 提取"初步需求如下："后面的全部内容（或用户直接给出的需求描述）
2. 调用脚本解析需求文本，提取结构化字段

### 4.2 执行脚本

```bash
python .agents/skills/rd-init/scripts/rd-init.py \
  --target-dir . \
  --brief "项目名称：xxx；核心功能：xxx"
```

或通过文件传入：

```bash
python .agents/skills/rd-init/scripts/rd-init.py \
  --target-dir . \
  --brief-file docs/FEATURE_BRAINSTORM.md
```

### 4.3 脚本动作

1. 创建标准目录结构（`docs/`、`output/spec/`、`output/prototype/`、`output/site/pc/`、`output/site/mobile/`、`output/site/assets/`、`output/build/`）
2. 解析需求文本，提取项目名称、行业、目标用户、核心功能等字段
3. 生成 `docs/project-brief.json`（结构化简报，供 brainstorm-product-feature 消费）
4. 生成 `project.yaml`（项目配置+流水线上下文）
5. 生成 `docs/FEATURE_BRAINSTORM.md`（需求原文）
6. 生成 `.rd-init.json`（初始化元数据）
7. 输出下一步指引：调用 product-pipeline-master 启动产研流水线

### 4.4 脚本参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--target-dir` | 目标项目目录 | `.` |
| `--brief` | 需求文本（直接传入） | — |
| `--brief-file` | 需求文本文件（`-` 为 stdin） | — |
| `--brief-json` | 结构化需求 JSON | — |
| `--overwrite` | 覆盖已存在的文件 | false |
| `--dry-run` | 只预览不写入 | false |

## 五、关键约束

1. **仅初始化**：只创建目录结构和起始文件，不生成 PRD、原型、代码或测试
2. **不拉取模板**：不再从 GitLab 拉取旧模板，目录结构由本 skill 直接创建
3. **下游衔接**：产出 `project-brief.json` 供 `brainstorm-product-feature` 消费，启动 `product-pipeline-master` 流水线
4. **幂等性**：重复执行不覆盖已有文件（除非 `--overwrite`）

## 六、与其他 skill 关系

| 关系 | skill | 说明 |
|------|-------|------|
| 下游 | brainstorm-product-feature | 消费 `docs/project-brief.json`，澄清早期功能想法 |
| 下游 | product-pipeline-master | 产研流水线总纲，编排后续全部阶段 |
| 上游 | 无 | rd-init 是流水线起点 |

**流水线位置**：

```
rd-init → brainstorm-product-feature → generate-system-prd → prd-quality-checker → ...
```

rd-init 是产研流水线的 **stage 0**，在 product-pipeline-master 的阶段 1（需求澄清）之前执行。
