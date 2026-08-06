---
name: "project-knowledge-base"
description: "项目知识库 skill。结构化存储团队规范/架构决策(ADR)/历史事故/代码规范,供其他 skill 执行前查询。当其他 skill 要获取项目上下文/历史决策/团队规范时调用。"
---

# 项目知识库(project-knowledge-base)

## 一、定位与职责

本 skill 负责项目知识的沉淀与查询,为其他 skill 在执行任务前提供项目上下文、历史决策与团队规范。

知识分类(共四类):

- `team-conventions`:团队规范,如命名约定、分支策略、提交信息格式、Code Review 流程
- `adr`:架构决策记录(Architecture Decision Records),记录技术选型与架构演进的关键决策及其背景、结果
- `postmortems`:事故复盘,记录线上事故/缺陷的时间线、根因、改进措施
- `code-standards`:代码规范,如目录结构、错误处理风格、日志规范、测试约定

## 二、子命令清单

通过 `scripts/kb_ops.py` 提供四个子命令:

| 子命令 | 输入 | 输出 |
|--------|------|------|
| `query` | `--category`(可选)、`--keyword`(可选) | 命中知识条目的完整 JSON,按分类/关键词过滤 |
| `add` | `--category`、`--title`、`--content`、`--tags`(可选,逗号分隔) | 新条目 id 与分类 |
| `update` | `--id`、`--content`(可选)、`--title`(可选) | 更新结果 |
| `list` | `--category`(可选) | 条目概览列表(分类/id/标题/更新时间) |

## 三、存储规则

- 知识统一存储于项目根目录下 `.trae-cn/knowledge/`
- 按分类建立子目录:`.trae-cn/knowledge/{team-conventions,adr,postmortems,code-standards}/`
- 每条知识独立存为 `{id}.json`,id 为 UUID
- 索引文件 `.trae-cn/knowledge/knowledge-base.json` 汇总所有条目元数据
- 知识以追加为主;删除需用户显式确认,脚本默认不提供删除子命令
- 更新时保留 `createdAt`,刷新 `updatedAt`

## 四、scripts 调用方式

工作目录为项目根。调用示例:

```bash
# 按分类 + 关键词查询
python scripts/kb_ops.py query --category adr --keyword "缓存"

# 按分类查询全部
python scripts/kb_ops.py query --category team-conventions

# 全局关键词查询(不指定分类)
python scripts/kb_ops.py query --keyword "日志规范"

# 新增知识条目
python scripts/kb_ops.py add --category adr --title "选用 PostgreSQL 作为主库" --content "决策:采用 PostgreSQL 16..." --tags "数据库,选型"

# 更新条目内容
python scripts/kb_ops.py update --id <UUID> --content "更新后的内容..."

# 更新条目标题
python scripts/kb_ops.py update --id <UUID> --title "新标题"

# 列出全部条目
python scripts/kb_ops.py list

# 按分类列出
python scripts/kb_ops.py list --category postmortems
```

## 五、知识 schema

每条知识为一个 JSON 对象,字段如下:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string(UUID) | 是 | 条目唯一标识,新增时由脚本生成 |
| `category` | string | 是 | 枚举:`team-conventions` / `adr` / `postmortems` / `code-standards` |
| `title` | string | 是 | 条目标题 |
| `content` | string | 是 | 条目正文,支持多行 |
| `tags` | string[] | 否 | 标签数组,可空 |
| `createdAt` | string(ISO8601) | 是 | 创建时间 |
| `updatedAt` | string(ISO8601) | 是 | 最近更新时间 |
| `project` | string | 否 | 所属项目标识(可选) |

完整 schema 详见 `references/kb-schema.md`。

## 六、与编排总纲的接入

其他 skill 在执行主任务前,可调用本 skill 的 `query` 子命令检索相关项目知识,用以约束或上下文化其产出。例如:

- `generate-system-prd` 执行前,查询 `team-conventions` 与 `code-standards`,使 PRD 中的规范段落与团队既有约定一致
- `implement-backend` / `implement-frontend` 执行前,查询 `adr` 获取已确立的技术选型,避免与既有决策冲突
- 事故修复类任务执行前,查询 `postmortems` 中同类事故的根因与改进项

调用方式:在 skill 执行流中插入 `python scripts/kb_ops.py query ...`,将命中结果作为上下文注入。

## 七、失败处理

知识库读写失败**不阻断**主流程:

- 若 `.trae-cn/knowledge/` 不存在或索引缺失,`query` / `list` 返回空结果,主 skill 继续
- 若 `add` / `update` 写入失败,向 stderr 输出 `WARNING: 知识库写入失败,已跳过`,主 skill 继续执行
- 知识查询未命中时,主 skill 不应报错,仅视为"无历史上下文"

## 八、质量检查清单

- [ ] `python scripts/kb_ops.py --help` 可正常运行并列出四个子命令
- [ ] `add` 后对应分类子目录存在 `{id}.json`,索引 `knowledge-base.json` 已更新
- [ ] `query --category <c> --keyword <k>` 能命中新增条目
- [ ] `update --id <id> --content <新内容>` 后 `updatedAt` 变化、`createdAt` 不变
- [ ] `list --category <c>` 仅返回该分类条目
- [ ] 索引与条目文件一致(无孤立文件、无悬挂索引项)
- [ ] 所有文件 UTF-8 编码,中文注释/内容正常
- [ ] 仅依赖 Python 标准库,无外部包
