# 敏感路径清单

本文件定义 guardrail 默认敏感路径清单。项目可在根目录 `.guardrail.yml` 中覆盖。

## 覆盖方式

在项目根目录创建 `.guardrail.yml`:

```yaml
sensitive_patterns:
  - "secrets/.*"
  - "deploy/.*\.yaml"
  - "internal/kernel/.*"
```

未提供 `.guardrail.yml` 时,使用下方默认清单;解析失败时也回退到默认清单,并在报告中以 WARNING 记录降级。

## 分类与正则模式

### 1. 生产配置

| 正则 | 说明 |
|------|------|
| `config/production/.*\.ya?ml$` | 生产环境 YAML 配置 |
| `.*\.env\.prod$` | 生产环境变量文件 |
| `\.env\.production$` | 生产环境变量文件(Vue/Next 风格) |

### 2. 数据库

| 正则 | 说明 |
|------|------|
| `migrations/.*` | 数据库迁移脚本 |
| `.*schema\.sql$` | 数据库 schema |
| `db/init/.*` | 数据库初始化脚本 |

### 3. 核心代码

| 正则 | 说明 |
|------|------|
| `src/core/.*` | 核心模块目录 |
| `.*/main\.ts$` | TypeScript 主入口 |
| `app/main\.py$` | Python 主入口 |
| `cmd/server/main\.go$` | Go 主入口 |

### 4. 密钥

| 正则 | 说明 |
|------|------|
| `.*\.key$` | 私钥文件 |
| `.*\.pem$` | PEM 证书/密钥 |
| `.*id_rsa$` | SSH 私钥 |
| `.*credentials.*` | 凭证文件 |
| `^\.env$` | 本地环境变量(含 secret) |

## 匹配规则

- 路径统一转为正斜杠后再匹配(跨平台兼容 Windows 反斜杠)。
- 正则使用 `re.search`(部分匹配),非锚定。
- 大小写敏感。
- 命中任一规则即判定为敏感路径,由 `operation-levels.md` 决定后续处置。
