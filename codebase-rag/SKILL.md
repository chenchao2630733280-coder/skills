---
name: "codebase-rag"
description: "Context 层 skill。对代码库做持久化语义索引,支持跨会话检索与大型项目分块索引。与宿主 SearchCodebase 互补(宿主实时索引,本 skill 持久化+跨会话+支持分块策略)。当大型项目需持久化代码索引或跨会话检索代码时调用。"
---

# codebase-rag

## 一、何时调用

满足以下任一条件即调用本 skill:

- 用户说"建代码库索引 / 持久化索引代码 / codebase-rag"
- 用户说"跨会话检索代码 / 大型项目代码检索"
- 用户说"增量更新代码索引 / 看索引统计"
- 其他 skill(如 `debug-fix` / `refactor`)需要跨会话检索代码时,先调本 skill 建索引或查询
- 项目代码量大(>500 文件),宿主 SearchCodebase 实时索引成本高,需持久化索引

**不要**在以下场景调用:
- 小型项目(<50 文件)的一次性检索(直接用宿主 SearchCodebase 即可)
- 用户只是问"某函数在哪"(用 Grep / SearchCodebase 更快)
- 要修改代码(本 skill 只读不写,检索后交调用方修改)

本 skill **只读不写**:不修改任何代码文件,索引数据写入 `.trae-cn/codebase-index/`(不提交 Git)。

---

## 二、与宿主 SearchCodebase 的分工

| 维度 | 宿主 SearchCodebase | 本 skill (codebase-rag) |
|------|---------------------|------------------------|
| 索引时机 | 实时(随代码变更) | 按需 build / update |
| 持久化 | 会话级(可能丢失) | 持久化到磁盘(跨会话) |
| 检索方式 | 语义嵌入(宿主实现) | 语义嵌入(有库) / 关键词降级(无库) |
| 大型项目 | 可能受限 | 分块策略 + 增量更新优化 |
| 适用场景 | 日常快速检索 | 大型项目 / 跨会话 / 需要分块统计 |

**原则**:互补不替代。日常检索优先宿主 SearchCodebase;大型项目或跨会话场景用本 skill。

---

## 三、索引策略

完整分块策略见 `references/indexing-strategy.md`,本节给出速查:

| 策略 | 适用 | 分块粒度 |
|------|------|---------|
| `file` | 小型文件 / 配置 | 每文件一块 |
| `function` | 中型代码文件 | 每函数/方法一块 |
| `semantic` | 大型代码文件 | 按语义边界(类/模块)分块 |
| `hybrid`(默认) | 混合项目 | 小文件用 file,大文件用 function |

嵌入模型选择见 `references/embedding-models.md`。默认用本地模型(隐私+成本),可选 API 模型。无嵌入库时降级为关键词索引(仍可检索,但非语义)。

---

## 四、scripts 调用方式

通用调用格式:

```
python scripts/index_codebase.py <子命令> [选项]
python scripts/search.py <子命令> [选项]
```

### index_codebase.py

#### build(全量索引)

```
python scripts/index_codebase.py build --project <项目路径> [--chunk-strategy hybrid] [--embedding local]
```

- 扫描项目代码文件(按扩展名过滤)
- 分块 + 计算 hash + 生成嵌入(若嵌入库可用)
- 写入 `.trae-cn/codebase-index/<项目名>/`
- 产出 `codebase-index.json`(索引清单)

#### update(增量更新)

```
python scripts/index_codebase.py update --project <项目路径>
```

- 对比文件 mtime/hash,只重新索引变更文件
- 更新 `codebase-index.json`

#### stats(统计)

```
python scripts/index_codebase.py stats --project <项目路径>
```

- 输出索引统计:文件数 / 分块数 / token 数 / 最后更新时间

### search.py

#### query(语义检索)

```
python scripts/search.py query --project <项目路径> --query "自然语言查询" [--top-k 5]
```

- 有嵌入库:语义检索,返回相关度评分排序的代码块
- 无嵌入库:降级为关键词匹配(TF-IDF)
- 返回:代码块 + 文件位置 + 相关度评分

#### locate(定位符号)

```
python scripts/search.py locate --project <项目路径> --symbol "函数名/类名"
```

- 精确符号定位(基于索引)
- 返回:文件路径 + 行号范围

### 输出报告字段

```json
{
  "command": "build | update | stats | query | locate",
  "project": "项目名",
  "stats": { "files": 120, "chunks": 450, "tokens": 89000, "embedding": "local-xxx" },
  "results": [
    { "file": "src/main.ts", "lines": "10-45", "score": 0.92, "snippet": "..." }
  ],
  "error": null,
  "timestamp": "2026-08-06T10:00:00+08:00"
}
```

退出码:`0`=成功;`1`=有错误(如项目不存在);`2`=参数错误。

---

## 五、references 使用指引

| 文件 | 读取时机 |
|------|---------|
| `references/indexing-strategy.md` | (1) 用户问"分块策略怎么选";(2) build 时指定 `--chunk-strategy` 前查阅 |
| `references/embedding-models.md` | (1) 用户问"嵌入模型怎么选";(2) build 时指定 `--embedding` 前查阅 |

两份 references 均为**懒加载**:仅在需要时读取。

---

## 六、关键约束

1. **只读不写**:不修改任何代码文件,索引数据写入 `.trae-cn/codebase-index/`(加入 .gitignore)。
2. **与宿主互补**:不替代宿主 SearchCodebase,大型项目/跨会话场景用本 skill。
3. **嵌入库可选**:无嵌入库时降级为关键词索引(TF-IDF),仍可检索但非语义;提示用户安装嵌入库以启用语义检索。
4. **增量更新**:基于文件 mtime/hash 对比,不全量重建;文件删除时清理对应索引。
5. **索引大小阈值**:索引超 500MB 时提示用户清理或分项目索引。
6. **失败不阻塞**:索引/检索失败时回填 `error` 字段返回 exit 1,不中断调用方。

---

## 七、与其他 skill 的关系

| skill | 关系 | 说明 |
|-------|------|------|
| `debug-fix` | 消费方 | 定位 Bug 时先查本 skill 索引(跨会话可用) |
| `refactor` | 消费方 | 重构前检索相关代码块 |
| `code-review` | 消费方 | 审查时检索相似代码模式 |
| `failure-casebook` | 协作方 | 索引失败时记录失败码 |
| 宿主 SearchCodebase | 互补 | 宿主实时索引,本 skill 持久化+跨会话 |

---

## 八、codebase-index.json schema

```json
{
  "project": "项目名",
  "indexed_at": "2026-08-06T10:00:00+08:00",
  "embedding_model": "local-xxx | none",
  "chunk_strategy": "hybrid",
  "stats": { "files": 120, "chunks": 450, "tokens": 89000 },
  "files": [
    {
      "path": "src/main.ts",
      "hash": "sha256...",
      "mtime": "2026-08-06T09:00:00",
      "chunks": 5,
      "language": "typescript"
    }
  ]
}
```

---

## 九、质量检查清单

### 9.1 只读不写约束
- [ ] SKILL.md 已声明"只读不写",脚本仅读代码文件、写索引到 `.trae-cn/`,不修改代码。

### 9.2 产物自评项
- [ ] `python scripts/index_codebase.py --help` 不报错,`build` / `update` / `stats` 子命令可见。
- [ ] `python scripts/search.py --help` 不报错,`query` / `locate` 子命令可见。
- [ ] build 能对当前 skills 目录建索引,产出 `codebase-index.json`。
- [ ] update 只重索引 mtime 变更的文件(可用 touch 测试)。
- [ ] query 无嵌入库时降级为关键词匹配,不报错。
- [ ] locate 能精确定位符号(文件路径 + 行号)。
- [ ] `references/indexing-strategy.md` 含 4 类分块策略 + 选择规则。
- [ ] `references/embedding-models.md` 含本地/API 模型对比 + 选择建议。
- [ ] SKILL.md 行数 ≤500,frontmatter 含 name + description。
- [ ] 所有文件 UTF-8 编码,文档与代码注释为中文。
- [ ] 产物自评:本 skill 产出后,按 skill-auditor 执行后评测模式自查(可选)。
