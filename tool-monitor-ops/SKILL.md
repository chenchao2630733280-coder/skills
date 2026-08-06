---
name: "tool-monitor-ops"
description: "监控工具层 skill。封装'查日志''查 metric''查 trace'操作。当 debug-fix 或其他 skill 要排查线上问题时调用。只读。"
---

# tool-monitor-ops(监控工具层)

## 一、定位与职责

本 skill 是「监控工具层」的查询封装,职责是把分散在多个监控平台的「查日志、查 metric、查 trace」三类只读操作收敛为统一脚本入口,供上层 skill(典型为 `debug-fix`)在排查线上问题时调用。

- **纯只读**:不写入、不修改、不下发任何配置,绝不触发任何变更动作。
- **只查询不决策**:本 skill 只负责取数与规范化输出,不对「是否回滚」「是否扩容」做任何判断,决策留给编排层。
- **平台无关封装**:通过环境变量切换底层平台(ELK / Grafana / Jaeger / 云厂商),上层调用方式不变。
- **可降级**:平台不可用时,降级为「提示用户手动查询」,不抛错、不阻塞编排流。

## 二、子命令清单

统一入口 `scripts/monitor_ops.py`,三个子命令:

| 子命令 | 作用 | 必填输入 | 可选输入 | 输出 |
|--------|------|----------|----------|------|
| `logs` | 查询服务日志 | `--service` | `--keyword` `--limit`(默认 100) `--time-range`(默认 1h) | 日志条目列表 |
| `metrics` | 查询服务指标 | `--service` `--metric`(cpu/memory/qps/error_rate) | `--time-range`(默认 1h) | 指标数据点列表 |
| `trace` | 查询链路 | `--service` | `--trace-id` `--limit`(默认 10) `--time-range`(默认 1h) | 链路条目列表 |

## 三、安全规则

1. **纯只读**:脚本仅发起 GET 请求,不含任何 POST/PUT/DELETE/PATCH 写操作。
2. **日志默认 100 条**:可通过 `--limit` 调整,不建议单次拉取过大,避免噪声。
3. **trace 默认 10 条**:链路数据量大,默认小批量,`--trace-id` 命中后优先精确查。
4. **指标固定四类**:`metrics` 子命令的 `--metric` 仅允许 `cpu/memory/qps/error_rate`,避免误查。
5. **平台不可用降级**:API 不可达、未配置基地址、返回非 JSON 时,降级为「提示用户手动查询」,写入 report 的 `error` 字段,`entries` 返回空列表,退出码仍为 0。
6. **无数据不报错**:平台返回空集合时,`entries=[]`、`totalCount=0`、`error=null`,视为正常。

## 四、scripts 调用方式

通用调用格式:

```
python scripts/monitor_ops.py <子命令> --service <服务名> [--keyword <关键词>] [--limit <N>] [--time-range <范围>]
```

示例(在 skill 目录下执行):

```bash
# 1. 查询 order-service 最近 1 小时含 "timeout" 的日志(最多 200 条)
python scripts/monitor_ops.py logs --service order-service --keyword timeout --limit 200 --time-range 1h

# 2. 查询 payment-service 最近 30 分钟的 CPU 指标
python scripts/monitor_ops.py metrics --service payment-service --metric cpu --time-range 30m

# 3. 查询 user-service 最近 5 条 trace(不指定 trace-id)
python scripts/monitor_ops.py trace --service user-service --limit 5 --time-range 1h

# 4. 按 trace-id 精确查询链路
python scripts/monitor_ops.py trace --service user-service --trace-id abc123def456
```

> 注意:需先通过环境变量配置平台基地址(见 `references/monitor-platforms.md`)。未配置时脚本会降级为提示,并输出 report。

## 五、产出契约

脚本产出 `monitor-ops-report.json`(写入当前工作目录,同时输出到 stdout)。结构如下:

```json
{
  "command": "logs | metrics | trace",
  "service": "<服务名>",
  "timeRange": "<时间范围,如 1h>",
  "entries": [],
  "totalCount": 0,
  "error": null,
  "timestamp": "2026-08-06T12:00:00"
}
```

字段说明:

- `command`:执行的子命令名。
- `service`:查询的服务名。
- `timeRange`:本次查询的时间范围。
- `entries`:结果条目数组;无数据时为 `[]`。
- `totalCount`:`entries` 的长度。
- `error`:出错或降级时的提示信息;正常为 `null`。
- `timestamp`:本地时间戳(ISO8601 风格)。

## 六、失败处理

| 情况 | 行为 |
|------|------|
| 未配置 `LOG_API_BASE` / `METRIC_API_BASE` / `TRACE_API_BASE` | 降级 report,`error` 给出「手动查询」提示,`entries=[]`,退出码 0 |
| API 不可达 / 超时(默认 5s) | 降级 report,`error` 含错误原因,`entries=[]` |
| 返回非 JSON / 解析失败 | 降级 report,`error` 标注「JSON 解析失败」 |
| 平台返回空集合 | `entries=[]`、`totalCount=0`、`error=null`,视为正常 |
| 写 `monitor-ops-report.json` 失败 | 仅在 stderr 给警告,stdout 仍输出完整 report |

降级提示模板:`监控平台不可用,请手动查询。提示: <具体指引>`。上层 skill 收到非空 `error` 时,应转而提示用户在控制台手动检索,而不是重试脚本。

## 七、与编排总纲的接入

- **被调用方1**:`debug-fix`(线上问题排查):由编排总纲在「线上问题排查」阶段调用。`debug-fix` 拿到故障现象后,依次或并行调用 `logs`(查报错)、`metrics`(查水位)、`trace`(查链路)收集证据。本 skill 产出的 report 作为 `debug-fix` 的输入证据;`debug-fix` 据此判断根因,但根因判断与本 skill 无关。
- **被调用方2**:`package-and-deploy-system`(部署后监控验证):在 **§5 运维能力** 章节调用本 skill 验证监控接入。部署后通过 `logs` 查询服务日志确认启动正常;通过 `metrics` 查询 CPU/内存/QPS/错误率指标验证监控埋点生效;通过 `trace` 查询链路确认分布式追踪接入。产出 `monitor-ops-report.json` 纳入 `output/build/` 运维验证证据。
- **权限边界**:本 skill 不得调用任何「变更类」skill(如 deploy、rollback);若证据指向需变更,由调用方(`debug-fix` 或 `package-and-deploy-system`)上报编排总纲转交对应 skill。

## 八、质量检查清单

发布前逐项确认:

- [ ] `SKILL.md` 行数 ≤ 300,frontmatter 的 `name` 与目录名一致。
- [ ] `python scripts/monitor_ops.py --help` 不报错,三个子命令均可列出。
- [ ] `logs` / `metrics` / `trace` 子命令的必填参数齐全,默认值符合第三节。
- [ ] 脚本仅用 Python 标准库(无第三方依赖),`urllib` 发起 GET 请求。
- [ ] 平台基地址从环境变量读取,未配置时降级为提示而非抛错。
- [ ] 产出 `monitor-ops-report.json` 结构与第五节契约一致,同时输出到 stdout。
- [ ] 无数据时 `entries=[]` 且 `error=null`,退出码 0。
- [ ] 全文 UTF-8 编码,关键注释为中文。
- [ ] `references/monitor-platforms.md` 覆盖 ELK / Grafana / Jaeger / 云厂商接入与降级规则。
- [ ] `agents/openai.yaml` 接口配置字段齐全。
