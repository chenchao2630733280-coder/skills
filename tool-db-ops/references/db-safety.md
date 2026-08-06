# 数据库安全规则

本文件定义 `tool-db-ops` skill 的安全规则、确认规则、连接串管理、迁移文件命名规范与失败码定义。
所有规则在 `scripts/db_ops.py` 中强制执行。

## 一、生产环境只读规则

### 1.1 环境判定

通过连接串(`DB_URL` 或 `DB_HOST`)中是否包含以下关键字判定生产环境(大小写不敏感):

- `production`
- `prod`
- `prd`

只要命中任意一个,即标记为 `production` 环境。

### 1.2 只读约束

| 子命令    | development | production |
| --------- | ----------- | ---------- |
| `migrate` | 允许(需 `--confirm`) | **拒绝** |
| `query`   | 允许        | 允许(仅 SELECT/WITH) |
| `rollback`| 允许(需 `--confirm`) | **拒绝** |

- 生产环境检测到写操作,直接返回失败码 `PROD_WRITE_REJECTED`,不执行任何 SQL。
- `query` 在任何环境下都仅允许 `SELECT` / `WITH` 开头的语句。

## 二、确认规则

- **migrate**:必须传入 `--confirm`,否则拒绝(失败码 `CONFIRM_REQUIRED`)。
- **rollback**:必须传入 `--confirm` 进行二次确认;生产环境即便有 `--confirm` 也拒绝。
- **query**:无需确认(纯只读)。

## 三、连接串管理

### 3.1 来源

连接信息仅从以下环境变量读取,脚本内不硬编码:

- `DB_URL`:完整连接串(优先),如 `sqlite:///./app.db`
- `DB_HOST`:主机地址
- `DB_USER`:用户名
- `DB_PASSWORD`:密码

### 3.2 保密要求

- 连接串**绝不**写入 `db-ops-report.json` 或任何日志输出。
- 脚本错误信息中只包含异常类型与消息,不包含连接串原文。
- 上游 skill 在传递环境时,应通过进程环境变量注入,不写入文件。

### 3.3 默认回退

- 未设置 `DB_URL` 且无 `DB_HOST` 时,默认使用 sqlite3 内存库(`:memory:`),仅用于 `--help` 与本地演示,不应在生产场景使用。

## 四、迁移文件命名规范

### 4.1 命名格式

```
<时间戳>_<序号>_<描述>.sql
```

示例:
```
20240101_0001_init_schema.sql
20240115_0002_add_users_table.sql
```

### 4.2 排序规则

- `migrate up`:按文件名升序执行。
- `migrate down`:按文件名降序执行。
- `rollback --target <版本>`:定位到目标文件,回滚其后的所有文件(逆序)。

### 4.3 文件内容

- 每个文件为合法 SQL,可为多条语句(sqlite3 `executescript` 支持)。
- 文件为空时跳过,不视为错误。
- 文件读取使用 UTF-8 编码。

## 五、失败码定义

| 失败码                    | 触发场景                                         | 是否回滚事务 |
| ------------------------- | ------------------------------------------------ | ------------ |
| `DB_CONNECT_FAILED`       | 数据库连接失败或查询执行异常                     | -            |
| `PROD_WRITE_REJECTED`     | 生产环境检测到写操作(migrate/rollback)          | -            |
| `CONFIRM_REQUIRED`        | migrate/rollback 缺少 `--confirm`                | -            |
| `MIGRATION_FILE_INVALID`  | 迁移目录为空/不存在,或 SQL 执行失败             | 是(回滚事务)|
| `ROLLBACK_TARGET_NOT_FOUND` | rollback 的 `--target` 未匹配到任何迁移文件    | -            |

## 六、事务保护

- `migrate` / `rollback` 在单事务内执行(`BEGIN` ... `COMMIT`)。
- 任意一个文件执行失败,立即 `ROLLBACK`,已执行的文件名仍记录在 `migrationFiles` 中以便排查。
- `query` 不涉及事务(只读)。

## 七、与编排总纲的接入

- 上游(`implement-data-layer`)检测到 `error` 非空时,应中止后续步骤并提示人工介入。
- `rollback` 失败时禁止自动重试,必须人工确认后重新执行。
