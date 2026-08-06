# diff-reviewer 风险变更识别规则

本文档定义 diff-reviewer 识别的 5 类风险变更的判定条件、严重级别与示例。
脚本 `scripts/diff_review.py` 据此实现。

## 1. 删除文件(deleted_file)- 严重级别:high

### 判定条件
- diff 中出现 `deleted file mode 100644` 标记;或
- `--before`/`--after` 模式下,before 侧存在而 after 侧缺失的文件。

### 示例
```
diff --git a/src/core.py b/src/core.py
deleted file mode 100644
--- a/src/core.py
+++ /dev/null
```

## 2. 大幅删减(large_reduction)- 严重级别:high

### 判定条件
- 按 diff hunk header `@@ -old_start,old_count +new_start,new_count @@` 累计 old_count 与 new_count;
- 删减比例 = (old_count - new_count) / old_count;
- 当删减比例 > 30% 时标记为大幅删减。
- 仅对 `modified` / `renamed` 状态判断(删除文件单独归类)。

### 示例
`@@ -1,100 +1,50 @@` → old_count=100,new_count=50 → 删减 50% > 30% → 标记 high。

## 3. 配置文件变更(config_change)- 严重级别:medium

### 判定条件
路径后缀匹配(大小写不敏感):`*.yml`、`*.yaml`、`*.json`、`*.toml`、`*.ini`、`*.cfg`、`*.conf`。

### 示例
- `config/production.yml`
- `appsettings.json`
- `pyproject.toml`

## 4. 依赖变更(dependency_change)- 严重级别:high

### 判定条件
文件名匹配依赖清单:
`package.json`、`package-lock.json`、`yarn.lock`、`requirements.txt`、`Pipfile`、`Pipfile.lock`、
`go.mod`、`go.sum`、`pom.xml`、`build.gradle`、`build.gradle.kts`、`Cargo.toml`、`Cargo.lock`。

### 示例
- `package.json` 新增依赖
- `requirements.txt` 升级版本
- `go.mod` 移除模块

## 5. 密钥文件变更(secret_change)- 严重级别:critical

### 判定条件
路径匹配(大小写不敏感):
`*.key`、`*.pem`、`*.pfx`、`*.p12`、`.env*`、`id_rsa`、`id_ecdsa`、`credentials.json`。

### 示例
- `secrets/private.key`
- `certs/server.pem`
- `.env.production`
- `~/.ssh/id_rsa`

## 优先级与去重

同一文件可能同时命中多条规则,按以下优先级取最高风险级别(每文件至多命中一类):

1. **secret_change**(critical)
2. **dependency_change**(high)
3. **config_change**(medium)

`deleted_file` 与 `large_reduction` 独立判定:
- 删除文件命中后不再叠加其他规则;
- `large_reduction` 与配置/依赖/密钥规则可并存(分别记录)。

## 严重级别汇总

| 级别 | 含义 | 处置建议 |
| --- | --- | --- |
| critical | 密钥/凭证泄露或变更 | 立即人工介入,检查是否误提交 |
| high | 删除/大幅删减/依赖变更 | 人工确认变更意图,防误删 |
| medium | 配置文件变更 | 复核配置项,防环境差异 |
