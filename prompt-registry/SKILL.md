---
name: "prompt-registry"
description: "Model 层 skill(部分)。集中管理各 skill 的 prompt 模板,支持版本化+变体管理+对比。当要统一管理 prompt、做 A/B 测试、或检索某 skill 的 prompt 时调用。不负责模型路由(依赖宿主)。"
---

# prompt-registry

## 一、何时调用

满足以下任一条件即调用本 skill:

- 用户说"注册 prompt / 把某 skill 的 prompt 加进注册表"
- 用户说"检索某 skill 的 prompt / 看某 skill 用了哪个版本的 prompt"
- 用户说"对比两个版本的 prompt / diff 两个 prompt 变体"
- 用户说"做 prompt 的 A/B 测试 / 管理 prompt 变体"
- 用户说"回退某 skill 的 prompt 到上个版本"
- 其他 skill(如 `game-blueprint` / `implement-frontend`)需要查询自身应使用的 prompt 版本时,先调本 skill 检索

**不要**在以下场景调用:

- 用户要选择用哪个模型执行 prompt(model-router / 模型路由依赖宿主能力,本 skill 不做)
- 用户只是问"prompt 怎么写"(纯咨询,直接读 `references/prompt-structure.md` 即可)
- 用户要修改 skill 的执行逻辑(本 skill 只管理 prompt 模板,不改 skill 代码)
- 一次性、不需要版本化的 prompt(直接内联在 SKILL.md 即可,无需注册)

本 skill **写注册表**:会向 `.trae-cn/prompts/` 写入 prompt 模板文件与索引(`prompt-registry.json`),但不修改任何 skill 的 SKILL.md 或脚本逻辑。

---

## 二、核心职责 / 数据模型

### 2.1 核心职责

| 职责 | 说明 | 实现脚本 |
|------|------|---------|
| 注册 | 将某 skill 的 prompt 模板写入注册表,关联 skill 名 + 版本 + 变体标签 | `register_prompt.py add` |
| 检索 | 按 skill 名 / 标签 / 最新版本获取 prompt | `get_prompt.py by-skill / by-tag / latest` |
| 版本化 | 每次修改保留历史版本(可回退) | `register_prompt.py update`(新增版本号,不覆盖旧版) |
| 变体管理 | 同一 skill 可有多个 prompt 变体(如"简洁版"/"详细版"),用 tag 区分 | `register_prompt.py add --tag` |
| 对比 | diff 两个版本/变体的 prompt | `diff_prompts.py` |

### 2.2 数据模型

注册表(`prompt-registry.json`)与 prompt 模板文件的关系:

```
.trae-cn/prompts/
├── prompt-registry.json              # 索引(注册表)
└── prompts/
    ├── game-blueprint/
    │   ├── 1.0.0.md                  # 稳定版 prompt 模板
    │   └── 1.1.0-beta.md             # 详细版变体
    └── implement-frontend/
        ├── 1.0.0.md
        └── 1.2.0.md
```

- **注册表**(`prompt-registry.json`):扁平索引,记录每个 skill 的所有版本及标签,详见 §七
- **prompt 模板文件**(`prompts/{skill}/{version}.md`):实际 prompt 文本,含占位符(运行时由 skill 填充)
- **存储位置**:`.trae-cn/prompts/`(可团队共享,建议加入 Git)

---

## 三、scripts 调用方式

通用约定:

```
python prompt-registry/scripts/<脚本>.py <子命令> [选项]
```

所有脚本均在当前工作目录的 `.trae-cn/prompts/` 下读写数据。

### 3.1 register_prompt.py

#### add(注册新 prompt)

```
python prompt-registry/scripts/register_prompt.py add \
  --skill game-blueprint \
  --version 1.0.0 \
  --tag stable \
  --file path/to/prompt.md
```

- 将 `--file` 指向的 prompt 文本复制到 `.trae-cn/prompts/prompts/{skill}/{version}.md`
- 在 `prompt-registry.json` 中新增一条版本记录(若 skill 不存在则新建 skill 条目)
- 若同 skill + 同 version 已存在:标 error,exit 1(用 `update` 子命令注册新版本)
- `--tag` 用于变体区分(如 `stable` / `detailed` / `concise`),默认 `stable`

#### update(更新 prompt,保留历史)

```
python prompt-registry/scripts/register_prompt.py update \
  --skill game-blueprint \
  --version 1.1.0 \
  --file path/to/prompt.md \
  [--tag detailed]
```

- **不覆盖旧版本**:以新 `--version` 注册新 prompt,旧版本保留(可回退)
- 若新 version 已存在:标 error,提示换一个版本号,exit 1
- 版本号规则见 `references/prompt-versioning.md`(语义化版本 + 预发布标签)

#### list(列出已注册 prompt)

```
python prompt-registry/scripts/register_prompt.py list [--skill game-blueprint]
```

- 不带 `--skill`:列出全部 skill 的全部版本
- 带 `--skill`:只列出该 skill 的全部版本(含 tag / 更新时间)

### 3.2 get_prompt.py

#### by-skill(按 skill 名检索)

```
python prompt-registry/scripts/get_prompt.py by-skill --skill game-blueprint
```

- 返回该 skill 的全部版本(含路径 / tag / 更新时间)

#### by-tag(按标签检索)

```
python prompt-registry/scripts/get_prompt.py by-tag --tag detailed
```

- 返回所有 skill 中 tag 为 `detailed` 的 prompt 列表

#### latest(获取最新版本)

```
python prompt-registry/scripts/get_prompt.py latest --skill game-blueprint [--tag stable]
```

- 按 semver 排序,返回该 skill 最新版本
- 带 `--tag`:在该 tag 范围内取最新

### 3.3 diff_prompts.py(对比两个版本/变体)

```
# 同 skill 两个版本对比
python prompt-registry/scripts/diff_prompts.py \
  --skill game-blueprint \
  --left-version 1.0.0 \
  --right-version 1.1.0-beta

# 跨 skill 对比
python prompt-registry/scripts/diff_prompts.py \
  --left-skill game-blueprint --left-version 1.0.0 \
  --right-skill implement-frontend --right-version 1.0.0
```

- 逐行 diff,标记增/删/改
- 输出 unified diff 格式 + 统计(增 N 行 / 删 M 行)

### 3.4 输出报告字段

所有脚本统一输出 JSON 报告到 stdout(便于机器解析),同时控制台打印人读摘要:

```json
{
  "command": "add | update | list | by-skill | by-tag | latest | diff",
  "skill": "game-blueprint",
  "results": [
    { "version": "1.0.0", "tag": "stable", "path": "prompts/game-blueprint/1.0.0.md", "updated_at": "..." }
  ],
  "error": null,
  "timestamp": "2026-08-06T10:00:00+08:00"
}
```

退出码:`0`=成功;`1`=有错误(如版本已存在、skill 不存在);`2`=参数错误。

---

## 四、references 使用指引

| 文件 | 读取时机 |
|------|---------|
| `references/prompt-versioning.md` | (1) 用户问"版本号怎么定";(2) `register_prompt.py add/update` 时校验 version 是否合法;(3) `get_prompt.py latest` 时按 semver 排序 |
| `references/prompt-structure.md` | (1) 用户问"prompt 模板怎么写 / 占位符规范";(2) 注册前检查 prompt 文件是否含必要的结构(系统提示/用户提示/占位符声明) |

两份 references 均为**懒加载**:仅在需要时读取,不强制调用方一次性全读。

---

## 五、关键约束

1. **渐进式接入**:不强制所有 skill 立即注册 prompt,先在 `game-*` 和 `implement-*` 试点,再推广。
2. **prompt 是模板**:注册表里的 prompt 文件是模板(含占位符如 `{{skill_name}}` / `{{input}}`),运行时由 skill 填充,不是可直接执行的最终 prompt。
3. **版本回退需确认**:`update` 不覆盖旧版本;若用户要"回退",实际是检索旧版本号重新注册为新版本,需用户确认。
4. **不做模型路由**:模型选择(用 GPT-4 还是 Claude)依赖宿主能力,本 skill 只管 prompt 文本,不管模型。
5. **注册表可团队共享**:存储在 `.trae-cn/prompts/`(建议加入 Git),团队成员可共享同一套 prompt 注册表。
6. **失败不阻塞**:操作失败时回填 `error` 字段返回 exit 1,不中断调用方流程(由调用方决定是否继续)。

---

## 六、与其他 skill 的关系

| skill | 关系 | 说明 |
|-------|------|------|
| `game-blueprint` / `game-spec` 等 game-* | 消费方(试点) | 渐进式接入首批:从注册表检索应使用的 prompt 版本 |
| `implement-frontend` / `implement-backend` | 消费方(试点) | 渐进式接入首批:从注册表检索应使用的 prompt 版本 |
| `skill-auditor` | 校验方 | 审查 skill 的 prompt 是否已注册、版本是否合法 |
| `skill-creator` | 上游 | 新建 skill 时可参考本 skill 注册 prompt 模板 |
| 宿主(模型路由) | 互补 | 宿主决定用哪个模型执行,本 skill 提供该模型应使用的 prompt 模板 |

---

## 七、prompt-registry.json schema

```json
{
  "registry_version": "1.0",
  "updated_at": "2026-08-06T10:00:00+08:00",
  "skills": [
    {
      "skill": "game-blueprint",
      "versions": [
        {
          "version": "1.0.0",
          "tag": "stable",
          "path": "prompts/game-blueprint/1.0.0.md",
          "updated_at": "2026-08-06T10:00:00+08:00",
          "notes": "初始稳定版"
        },
        {
          "version": "1.1.0-beta",
          "tag": "detailed",
          "path": "prompts/game-blueprint/1.1.0-beta.md",
          "updated_at": "2026-08-06T11:00:00+08:00",
          "notes": "详细版变体,含更多约束说明"
        }
      ]
    }
  ]
}
```

字段说明:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `registry_version` | string | 是 | 注册表 schema 版本(当前 `1.0`) |
| `updated_at` | string | 是 | 注册表最后更新时间(ISO8601) |
| `skills[].skill` | string | 是 | skill 名称(对应工作台目录名) |
| `skills[].versions[].version` | string | 是 | 语义化版本号(如 `1.0.0` / `1.1.0-beta`),同 skill 内唯一 |
| `skills[].versions[].tag` | string | 是 | 变体标签(如 `stable` / `detailed` / `concise`) |
| `skills[].versions[].path` | string | 是 | prompt 模板文件相对路径(相对 `.trae-cn/prompts/`) |
| `skills[].versions[].updated_at` | string | 是 | 该版本注册/更新时间(ISO8601) |
| `skills[].versions[].notes` | string | 否 | 版本说明 |

---

## 八、质量检查清单

### 8.1 核心职责约束

- [ ] SKILL.md 已声明职责边界:注册/检索/版本化/变体管理/对比,不做模型路由。
- [ ] `register_prompt.py` 的 `update` 不覆盖旧版本(新增版本号,保留历史)。
- [ ] 所有脚本失败时回填 `error` 字段,不抛异常阻断调用方。

### 8.2 产物自评项

- [ ] `python prompt-registry/scripts/register_prompt.py --help` 不报错,`add` / `update` / `list` 子命令可见。
- [ ] `python prompt-registry/scripts/get_prompt.py --help` 不报错,`by-skill` / `by-tag` / `latest` 子命令可见。
- [ ] `python prompt-registry/scripts/diff_prompts.py --help` 不报错,对比参数可见。
- [ ] `register_prompt.py add` 能注册 prompt,写入 `.trae-cn/prompts/prompts/{skill}/{version}.md` + 更新 `prompt-registry.json`。
- [ ] `register_prompt.py add` 同 skill+version 重复注册时标 error,exit 1。
- [ ] `register_prompt.py list` 能列出全部 / 按 skill 过滤。
- [ ] `get_prompt.py latest` 按 semver 排序返回最新版本。
- [ ] `get_prompt.py by-tag` 能跨 skill 按标签检索。
- [ ] `diff_prompts.py` 能输出 unified diff + 增删统计。
- [ ] `references/prompt-versioning.md` 含语义化版本规则 + 预发布标签 + 变体标签约定。
- [ ] `references/prompt-structure.md` 含系统提示/用户提示/占位符规范 + 示例。
- [ ] `agents/openai.yaml` 含 display_name / short_description / default_prompt。
- [ ] SKILL.md 行数 ≤500,frontmatter 含 name + description。
- [ ] 所有文件 UTF-8 编码,文档与代码注释为中文。
- [ ] 产物自评:本 skill 产出后,按 skill-auditor 执行后评测模式自查(可选)。
