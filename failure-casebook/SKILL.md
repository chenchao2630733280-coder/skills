---
name: "failure-casebook"
description: "失败案例库 skill。每次 skill 执行失败时自动记录'失败码+原因+修复方法',下次同名 skill 执行前先查避免重复踩坑。当 skill 执行失败或要查询历史失败案例时调用。"
---

# 失败案例库 (failure-casebook)

## 一、定位与职责

本 skill 是 **失败案例的沉淀与查询中枢**,服务于整个 skill 编排体系:

- **自动记录**:任一 skill 执行失败时,由编排总纲或失败 skill 自身调用本 skill 的 `record` 子命令,把"失败码 + 原因 + 修复方法"写入案例库,失败即记。
- **执行前查询**:其他 skill 执行前,可调用本 skill 的 `query` 子命令,按 skill 名查历史失败案例,提前规避已知坑点,避免重复踩坑。
- **统计洞察**:通过 `stats` 子命令汇总各 skill 的失败次数、最近失败时间、常见失败码,辅助定位高频失败 skill。

定位边界:本 skill **只负责案例的记录与查询**,不负责诊断失败根因、不负责重试、不负责修复执行;它是一面"踩坑备忘录",供其他 skill 参考。

## 二、子命令清单

本 skill 通过 `scripts/casebook_ops.py` 提供四个子命令:

### 1. record —— 记录一条失败案例

| 项 | 说明 |
|---|---|
| 输入 | `--skill`(失败 skill 名)、`--code`(失败码)、`--reason`(失败原因)、`--fix`(修复方法)、`--severity`(可选,默认 error)、`--project`(可选,项目名) |
| 输出 | 新案例的 `id` 与写入路径;顺带清理 90 天前过期案例 |

### 2. query —— 查询历史失败案例

| 项 | 说明 |
|---|---|
| 输入 | `--skill`(必填)、`--code`(可选,按失败码过滤)、`--limit`(默认 10) |
| 输出 | 匹配案例列表,按时间倒序;每条含 id/code/severity/timestamp/reason/fix |

### 3. stats —— 统计失败概况

| 项 | 说明 |
|---|---|
| 输入 | 无 |
| 输出 | 各 skill 的失败次数、最近失败时间、常见失败码 Top N 汇总 |

### 4. auto-query —— skill 执行前自动查询

| 项 | 说明 |
|---|---|
| 输入 | `--skill`(必填,要查询的 skill 名) |
| 输出 | `auto-query-result.json`(结果 JSON 打印到 stdout,纯查询不写文件) |
| 是否写入案例库 | 否(纯查询,只读) |

**用途**:skill 执行前自动查询该 skill 的历史失败案例,注入预防提示。

**调用方**:workflow-runtime 在调用某 skill 前,先调本子命令查询该 skill 的历史失败。

**输入**:
- `--skill <skill名>`:要查询的 skill 名

**输出**:`auto-query-result.json`,含:
- `failure_count`:历史失败次数
- `top_failures`:最常见的 3 个失败码 + 原因摘要(每项含 `related_call_id` 若存在)
- `preventive_hints`:预防提示(基于历史失败给当前执行的建议)
- `last_failure_time`:最近一次失败时间

**与 query 的区别**:query 是用户主动查询(返回完整案例);auto-query 是自动查询(返回精简摘要 + 预防提示),供 workflow-runtime 注入到 skill 执行上下文。

**注入机制**:workflow-runtime 调用 auto-query 后,把 `preventive_hints` 注入到 skill 执行的上下文中(如作为 skill 的提示信息),不阻塞执行。

## 三、存储规则

- **案例目录**:所有案例 JSON 文件存到 `~/.trae-cn/failures/`(脚本自动创建,如不存在)。
- **单案例文件**:每个案例一个独立 JSON 文件,文件名 `{id}.json`,`id` 为 UUID4。
- **索引文件**:`~/.trae-cn/failures/failure-casebook.json`,记录所有案例的元信息(id/skill/code/severity/timestamp/project/file),用于快速查询,避免遍历全量文件。
- **保留策略**:案例默认保留 **90 天**,可通过环境变量 `FAILURE_CASEBOOK_RETENTION_DAYS` 配置;每次 `record` 时顺带清理过期案例(删除案例文件并从索引移除)。
- **编码**:所有文件 UTF-8 编码,JSON 以缩进 2 写出,timestamp 为 ISO-8601 带时区(UTC)。

## 四、scripts 调用方式

脚本路径:`scripts/casebook_ops.py`,使用标准 Python 3,无外部依赖。

### 记录失败案例

```bash
python scripts/casebook_ops.py record \
  --skill game-code-forge \
  --code ASSET_NOT_FOUND \
  --reason "ASSET_MANIFEST.json 中引用的图片 assets/hero.png 不存在" \
  --fix "回退到 game-asset-forge 重新生成切图,并校验清单完整性" \
  --severity error
```

### 执行前查询

```bash
python scripts/casebook_ops.py query --skill game-code-forge --limit 5
```

按失败码过滤:

```bash
python scripts/casebook_ops.py query --skill game-code-forge --code ASSET_NOT_FOUND
```

### 统计

```bash
python scripts/casebook_ops.py stats
```

### skill 执行前自动查询

```bash
python scripts/casebook_ops.py auto-query --skill game-asset-forge
```

输出 `auto-query-result.json`(打印到 stdout),含 `failure_count` / `top_failures` / `preventive_hints` / `last_failure_time`。无历史失败时返回空结果(failure_count=0、各数组为空),退出码 0。供 workflow-runtime 在调用 skill 前查询并注入预防提示。

### 查看帮助

```bash
python scripts/casebook_ops.py --help
python scripts/casebook_ops.py record --help
python scripts/casebook_ops.py auto-query --help
```

## 五、案例 schema

每条案例 JSON 文件结构如下(详见 `references/casebook-schema.md`):

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | string(UUID) | 是 | 案例唯一标识,UUID4 |
| skill | string | 是 | 失败的 skill 名 |
| code | string | 是 | 失败码(大写蛇形,如 `ASSET_NOT_FOUND`) |
| reason | string | 是 | 失败原因描述 |
| fix | string | 是 | 修复方法/规避建议 |
| timestamp | string(ISO-8601) | 是 | 失败发生时间,带时区 |
| project | string | 否 | 项目名/路径,便于归类 |
| related_call_id | string | 否 | 关联的 skill-usage-tracker 调用 ID(若存在),便于追溯单次调用的完整上下文 |
| severity | enum | 是 | `error` 或 `warning`,默认 error |

## 六、与编排总纲的接入

本 skill 与编排总纲(如 `product-pipeline-master` / `game-forge-master`)的接入方式:

1. **执行前查询(推荐)**:编排总纲在调度某 skill 执行前,先调 `query --skill <名>`,若存在近期失败案例,把 `fix` 字段作为提示注入到该 skill 的执行上下文,提前规避。
2. **失败后自动记录**:任一 skill 执行失败时,编排总纲(或失败 skill 自身)在异常处理分支中调 `record`,把失败码、原因、(若已知)修复方法写入案例库。
3. **接入契约**:记录与查询为"显式调用"模式:编排总纲/workflow-runtime/agent-orchestrator/agent-runtime-exec/skill-runtime 在 skill 执行失败时,应显式调用本 skill 的 record 子命令记录失败码+修复方法;未接入时案例库为空,不影响主流程。建议接入以获得防踩坑能力。

**与 workflow-runtime 的协作**:workflow-runtime 在调用 skill 前(执行 workflow.yaml 的 skill step 前),先调本 skill 的 auto-query 子命令,查询该 skill 的历史失败案例。若有匹配失败码,把 `preventive_hints` 注入到 skill 执行上下文,帮助 skill 提前规避已知坑。查询失败不阻塞 skill 执行(降级为无提示)。

**与 skill-usage-tracker 的关联**:记录失败案例时,若 workflow-runtime 提供了 `call_id`(来自 skill-usage-tracker),则写入 `related_call_id` 字段,建立"失败案例 ↔ 调用记录"的关联。查询失败案例时,可通过 `related_call_id` 反查 skill-usage-tracker 获取该次调用的完整上下文(耗时/输入摘要/产物路径),便于根因分析。

**与 agent-orchestrator / agent-runtime-exec 的协作(反向声明)**:这两个 skill 在委派/执行超时或失败时,显式调用本 skill 的 `record` 子命令记录失败码 + 修复方法(失败码格式如 `AGENT_TIMEOUT_<correlation_id>` / `AGENT_CONFLICT_<correlation_id>`)。下次同名任务委派前,这两个 skill 可调本 skill 的 `query` 子命令注入预防提示。

**与 adaptive-tuner 的协作(反向声明)**:adaptive-tuner 在分析高失败率 skill(基于 skill-usage-tracker 统计)时,可关联查询本 skill 的历史案例,把"失败码 + 修复方法"作为参数优化建议的输入(如发现某 skill 因固定失败码高频失败,可在 runtime-overrides.yaml 中调整 timeout/retry/降级阈值)。

## 七、失败处理

本 skill 自身的读写失败 **不阻断主流程**:

- 案例库目录创建失败、文件写入失败、索引损坏等异常,脚本捕获后只在 stderr 打印 `WARNING: <详情>`,并以 exit code 0 退出(record)或返回空结果(query/stats)。
- 编排总纲调用本 skill 时,应忽略其退出码与 stderr 中的 WARNING,继续主流程。
- 设计原则:**案例库是辅助记忆,不是关键路径**,宁可丢案例也不能拖垮主流程。

## 八、质量检查清单

- [ ] `python scripts/casebook_ops.py --help` 可正常输出,无报错
- [ ] `record` 能生成 UUID、写入案例 JSON、更新索引
- [ ] `query` 按 skill 过滤、按时间倒序、limit 生效
- [ ] `stats` 输出各 skill 失败次数 / 最近失败时间 / 常见失败码
- [ ] `auto-query` 按 skill 汇总 failure_count/top_failures/preventive_hints/last_failure_time,无历史时返回空结果(退出码 0)
- [ ] `auto-query` 为纯查询(只读),不写案例库;查询失败不阻塞,返回空结果
- [ ] 过期案例(>90 天)在 record 时被清理,案例文件与索引同步删除
- [ ] `~/.trae-cn/failures/` 目录不存在时自动创建
- [ ] 案例库读写失败时只打 WARNING,不阻断主流程,exit code 0
- [ ] 仅用标准库,无外部依赖;UTF-8 编码,中文注释
- [ ] SKILL.md 行数 ≤ 500
