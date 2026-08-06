# 监控平台接入与降级规则

本文档说明 `tool-monitor-ops` 如何对接各监控平台,以及平台不可用时的降级规则。脚本(`scripts/monitor_ops.py`)通过环境变量读取配置,平台无关。

## 一、环境变量清单

| 环境变量 | 作用 | 必填 | 示例 |
|----------|------|------|------|
| `MONITOR_PLATFORM` | 平台标识,仅用于日志与提示 | 否 | `elk` / `grafana` / `jaeger` / `cloud` |
| `LOG_API_BASE` | 日志查询 API 基地址 | logs 命令需要 | `http://elk-gateway.internal:9200` |
| `METRIC_API_BASE` | 指标查询 API 基地址 | metrics 命令需要 | `http://prometheus.internal:9090` |
| `TRACE_API_BASE` | 链路查询 API 基地址 | trace 命令需要 | `http://jaeger-query.internal:16686` |

> 三个 `*_API_BASE` 任一缺失,对应子命令即降级为提示;不影响其他子命令。

## 二、脚本请求约定

脚本对每个基地址拼接固定路径并发起 GET 请求(`Accept: application/json`,默认超时 5s):

- logs:`{LOG_API_BASE}/logs?service=<s>&limit=<n>&time_range=<r>&keyword=<k>`
- metrics:`{METRIC_API_BASE}/metrics?service=<s>&metric=<m>&time_range=<r>`
- trace:`{TRACE_API_BASE}/traces?service=<s>&limit=<n>&time_range=<r>&trace_id=<id>`

响应应为 JSON。数组或 `{"entries": [...]}` 均可被接受并规范化为 `entries`。

## 三、各平台接入方式

### 1. ELK(Elasticsearch + Kibana + Logstash)

- **角色**:日志平台,对接 `logs` 子命令。
- **配置**:`LOG_API_BASE` 指向 Elasticsearch 或封装网关地址;`MONITOR_PLATFORM=elk`。
- **适配说明**:若直接查 ES,需在网关层把上面的 `/logs` 请求翻译为 ES `_search` DSL。脚本不做 DSL 拼装,避免与具体 ES 版本耦合。
- **关键词过滤**:网关应支持 `keyword` 参数做 `match_phrase` 查询;脚本同时在客户端对结果做二次过滤兜底。

### 2. Grafana(背后通常是 Prometheus)

- **角色**:指标平台,对接 `metrics` 子命令。
- **配置**:`METRIC_API_BASE` 指向 Prometheus 或 Grafana 数据代理地址;`MONITOR_PLATFORM=grafana`。
- **适配说明**:网关把 `/metrics?metric=cpu` 翻译为对应 PromQL(如 `rate(container_cpu_usage_seconds_total{service="<s>"}[1m])`);脚本不感知 PromQL。
- **指标口径**:cpu / memory / qps / error_rate 四类由网关映射到具体查询;脚本只传指标名。

### 3. Jaeger

- **角色**:链路平台,对接 `trace` 子命令。
- **配置**:`TRACE_API_BASE` 指向 Jaeger Query 服务地址;`MONITOR_PLATFORM=jaeger`。
- **适配说明**:网关把 `/traces?service=<s>&trace_id=<id>` 翻译为 Jaeger API(`/api/traces?service=...`);`trace_id` 命中时优先按 id 精确查。
- **默认条数**:trace 默认 10 条,链路数据量大,避免拉全量。

### 4. 云厂商(阿里云 SLS / 腾讯云 CLS / AWS CloudWatch 等)

- **角色**:可同时承载日志、指标、链路。
- **配置**:分别配置 `LOG_API_BASE` / `METRIC_API_BASE` / `TRACE_API_BASE` 指向云厂商封装网关(由内部网关屏蔽签名与鉴权);`MONITOR_PLATFORM=cloud`。
- **适配说明**:鉴权(AK/SK、STS)由网关完成,脚本不持有密钥,符合「纯只读、不暴露凭据」原则。
- **安全提示**:切勿把云厂商 AK/SK 写入环境变量交给脚本;密钥只存在于网关侧。

## 四、降级规则

降级触发条件与表现:

| 触发条件 | report 表现 | 上层建议动作 |
|----------|-------------|--------------|
| 对应 `*_API_BASE` 未配置 | `entries=[]`,`error` 提示手动查询 | 在对应平台控制台手动检索 |
| API 不可达 / 超时(>5s) | `entries=[]`,`error` 含错误原因 | 检查网络/网关,稍后重试或手动查 |
| 返回非 JSON / 解析失败 | `entries=[]`,`error` 标注解析失败 | 联系平台方核对接口契约 |
| 平台返回空集合 | `entries=[]`,`error=null` | 视为正常,扩大时间范围或换关键词 |
| 写 report 文件失败 | stdout 仍输出完整 report | 检查当前目录写权限 |

降级原则:**永远不抛未捕获异常、不返回非零退出码**;把「不可用」转化为可读的 `error` 提示,由上层 skill 决定是否转人工。

## 五、配置示例(按平台)

```bash
# ELK + Grafana + Jaeger 组合
export MONITOR_PLATFORM=elk
export LOG_API_BASE=http://elk-gateway.internal:9200
export METRIC_API_BASE=http://prometheus.internal:9090
export TRACE_API_BASE=http://jaeger-query.internal:16686

# 云厂商统一网关
export MONITOR_PLATFORM=cloud
export LOG_API_BASE=http://obs-gateway.internal/log
export METRIC_API_BASE=http://obs-gateway.internal/metric
export TRACE_API_BASE=http://obs-gateway.internal/trace
```
