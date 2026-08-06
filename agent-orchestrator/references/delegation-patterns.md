# 委派模式 (delegation-patterns)

> agent-orchestrator 的任务委派模式参考。设计多 Agent 协同时查阅。

## 一、四类委派模式

### 1. 扇出(Fan-out)

**结构**:一个主 Agent 把任务拆成多个子任务,并行委派给多个子 Agent。

```
        主 Agent
       /   |   \
  sub-1  sub-2  sub-3   (并行)
       \   |   /
        汇总结果
```

**适用**:子任务相互独立,可并行执行(如"前端 / 后端 / 测试"三 Agent 并行)。

**消息流**:
```
delegate T1->sub-1  (correlation_id=T1)
delegate T1->sub-2  (correlation_id=T1)
delegate T1->sub-3  (correlation_id=T1)
... 并行执行 ...
result sub-1->master (correlation_id=T1)
result sub-2->master (correlation_id=T1)
result sub-3->master (correlation_id=T1)
collect --correlation-id T1
merge  --correlation-id T1 --strategy priority
```

**命令示例**:
```bash
python scripts/orchestrate.py delegate --from master --to sub-1 \
  --task "前端开发" --skill implement-frontend --correlation-id T1 --ack
python scripts/orchestrate.py delegate --from master --to sub-2 \
  --task "后端开发" --skill implement-backend --correlation-id T1 --ack
python scripts/orchestrate.py delegate --from master --to sub-3 \
  --task "测试" --skill test-and-harden-system --correlation-id T1 --ack
python scripts/orchestrate.py collect --correlation-id T1 --timeout 300
python scripts/orchestrate.py merge --correlation-id T1 \
  --strategy priority --priority-order "sub-1,sub-2,sub-3"
```

**冲突解决**:优先级(priority)或投票(voting)。

---

### 2. 扇入(Fan-in)

**结构**:多个子 Agent 的结果汇聚到一个主 Agent 做汇总。

```
  sub-1  sub-2  sub-3   (各自产出)
       \   |   /
        主 Agent(汇总)
```

**适用**:多 Agent 各自产出部分结果,需要聚合(如"三 Agent 各审一部分代码,汇总审查报告")。

**消息流**:
```
各 sub 独立产出 -> result 各自回传 -> master collect + merge
```

**冲突解决**:投票(voting)——多数一致取胜;或人工(human)。

---

### 3. 管道(Pipeline)

**结构**:任务串行流转,前一个 Agent 的输出是后一个的输入。

```
主 Agent -> sub-1 -> sub-2 -> sub-3 -> 主 Agent
```

**适用**:有依赖关系的串行任务(如"PRD -> 原型 -> 代码")。

**消息流**:
```
delegate T1->sub-1 (correlation_id=T1)
result sub-1->master (correlation_id=T1)
delegate T1->sub-2 (correlation_id=T1, payload 含 sub-1 的产物)
result sub-2->master (correlation_id=T1)
delegate T1->sub-3 (correlation_id=T1, payload 含 sub-2 的产物)
result sub-3->master (correlation_id=T1)
```

**命令示例**:
```bash
python scripts/orchestrate.py delegate --from master --to prd-agent \
  --task "生成 PRD" --skill generate-system-prd --correlation-id T1 --ack
# 等待 result
python scripts/orchestrate.py delegate --from master --to proto-agent \
  --task "生成原型" --skill generate-prototype --correlation-id T1 --ack
# 等待 result
python scripts/orchestrate.py delegate --from master --to code-agent \
  --task "生成代码" --skill implement-frontend --correlation-id T1 --ack
python scripts/orchestrate.py collect --correlation-id T1
```

**冲突解决**:通常无冲突(串行,每步单一结果);失败时回退到上一步重跑。

---

### 4. 协商(Negotiation)

**结构**:多 Agent 对等协商,无固定主 Agent,通过投票/讨论达成共识。

```
  sub-1 <-> sub-2
   |         |
  sub-3 <-> sub-4   (对等协商)
       |
    投票/人工裁决
```

**适用**:需要多方观点汇总(如"多 Agent 评审方案,投票决策")。

**消息流**:
```
各 sub 发 notify/query 互相沟通
各 sub 发 result 给协调者(或彼此)
merge --strategy voting 或 human
```

**冲突解决**:投票(voting)——相同结果占比 >50% 取胜;否则转人工(human)。

---

## 二、模式选择速查

| 场景 | 推荐模式 | 冲突策略 |
|------|---------|---------|
| 子任务独立,可并行 | 扇出(Fan-out) | priority |
| 多 Agent 产出需聚合 | 扇入(Fan-in) | voting |
| 任务有依赖,串行流转 | 管道(Pipeline) | 无(串行) |
| 需多方观点,对等协商 | 协商(Negotiation) | voting/human |
| 不确定 | 扇出(最通用) | priority |

---

## 三、与协同模式的关系

| 协同模式 | 常用委派模式 |
|---------|------------|
| 主从模式(一主多从) | 扇出 / 扇入 / 管道 |
| 对等模式(多 Agent 协商) | 协商 |

主从模式下,主 Agent 负责委派 + 收集 + 合并;对等模式下,各 Agent 平等协商,
可指定一个临时协调者负责 merge。

---

## 四、失败处理

| 模式 | 失败处理 |
|------|---------|
| 扇出 | 单个子 Agent 失败不影响其他;merge 时跳过 failed 结果 |
| 扇入 | 同上 |
| 管道 | 某步失败则后续步骤不执行;可回退到上一步重跑(类似 workflow-runtime 的 back_to) |
| 协商 | 某 Agent 掉线不影响其他;voting 时按实际参与数计算 |

所有模式失败均不阻塞:exit 1 但消息日志保留,调用方可重试或转人工。

---

## 五、与 workflow-runtime 的协作

- agent-orchestrator 编排 Agent(粗粒度),workflow-runtime 编排 skill(细粒度)
- 一个 Agent 内部可用 workflow-runtime 调度多个 skill
- 调用链:`agent-orchestrator delegate -> Agent 内部 workflow-runtime 调度 skill -> Agent 回 result`

两层失败处理:
- Agent 层(本 skill):委派超时 / 结果冲突 / 转人工裁决
- skill 层(workflow-runtime):步骤回退 / 跳过 / 终止
- skill 层用尽重试与降级后,才上升到 Agent 层的超时处理
