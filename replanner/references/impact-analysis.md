# 影响传播分析 (replanner)

本文件定义 replanner 的**影响分析方法**:当一个子任务失败后,如何找出所有受牵连的任务并分级。
脚本 `scripts/replan.py` 的 `impact` 子命令与 `replan` 子命令均基于本方法实现。

## 一、为什么需要影响分析

重规划的核心问题是:"T-003 失败了,还有哪些任务做不下去?"。直接看 `depends_on` 只能找到
直接下游,但下游的下游也会被阻断。影响分析通过遍历依赖图,找出**完整的传播链**,避免遗漏。

- 遗漏受影响任务 → 下游任务带着缺失的依赖执行,必然再次失败,浪费重规划轮次。
- 误判不受影响任务为受影响 → 过度调整,破坏稳定任务。

## 二、依赖图构建

从 task-tree 的 `depends_on` 字段构建**反向依赖图**(reverse graph):

- 定义:若任务 B 的 `depends_on` 含 A,表示 B 依赖 A;A 失败会影响 B。
- 反向图:`reverse[A] = [B, C, ...]`,即 A 的所有直接下游。
- 仅纳入 `depends_on`(数据/控制依赖);`parallel_with` 不构成阻断关系(并行任务失败不阻塞对方)。

```
正向:B.depends_on = [A]   →   A 是 B 的前置
反向:reverse[A].append(B) →   B 是 A 的下游(受 A 影响)
```

构建步骤:
1. 遍历 `tasks`,收集所有 `id` 构成 `id_set`。
2. 对每个任务 B,遍历其 `depends_on`,对每个存在的 A,把 B 加入 `reverse[A]`。
3. 引用不存在的 id 在 schema 校验阶段已报错,此处忽略。

## 三、传播算法(BFS 分层)

从失败任务 `failed_id` 出发,反向 BFS 遍历:

```
visited = {failed_id}
layers = []
current = reverse[failed_id] 中未访问的任务   # 第 1 层:直接影响
记录 current 到 layers[0],加入 visited
frontier = current
while frontier 非空:
    nxt = []
    for t in frontier:
        for child in reverse[t]:
            if child 未访问:
                加入 nxt、visited
    if nxt 非空: 记录到下一层
    frontier = nxt
```

- **第 1 层 = 直接影响**:直接 `depends_on` 失败任务的任务。
- **第 2 层及以后 = 间接影响**:传递依赖链上的任务。
- `affected_ids` = 所有层任务的并集(不含失败任务本身)。
- BFS 与 DFS 等价;BFS 的优势是天然分层,便于按距离排序处理。

> 环检测:依赖图在 schema 校验阶段已保证无环(拓扑排序通过),故 BFS 必然终止。

## 四、影响分级

根据失败任务与受影响任务的优先级,分三级:

| 分级 | 判定条件 | 处置倾向 |
|------|---------|---------|
| 阻断 | 失败任务 priority=P0,**或**受影响任务中含 P0 | 关键路径停滞,必须处理(拆分/降级/人工) |
| 降级 | 受影响任务仅 P1/P2(失败任务非 P0) | 非关键路径,可跳过/降级 |
| 无影响 | `affected_ids` 为空(无人依赖失败任务) | 仅记录失败,后续任务不受影响 |

分级规则(脚本 `analyze_impact` 实现):
1. 若 `failed_task.priority == "P0"` → 阻断。
2. 否则若任一受影响任务 priority == "P0" → 阻断。
3. 否则若 `affected_ids` 非空 → 降级。
4. 否则 → 无影响。

## 五、示例

### 5.1 task-tree 片段

```json
{
  "tasks": [
    { "id": "T-001", "title": "设计文章表", "priority": "P0", "depends_on": [] },
    { "id": "T-003", "title": "实现创建文章接口", "priority": "P0", "depends_on": ["T-001"] },
    { "id": "T-004", "title": "实现文章列表页", "priority": "P1", "depends_on": ["T-003"] },
    { "id": "T-005", "title": "实现评论功能", "priority": "P2", "depends_on": ["T-001"] },
    { "id": "T-006", "title": "部署到测试环境", "priority": "P1", "depends_on": [] }
  ]
}
```

### 5.2 T-001 失败的影响分析

- 反向图:`reverse[T-001] = [T-003, T-005]`,`reverse[T-003] = [T-004]`。
- BFS:
  - 第 1 层(直接):`T-003`、`T-005`
  - 第 2 层(间接):`T-004`(经 T-003)
- `affected_ids = {T-003, T-004, T-005}`
- 分级:T-001 为 P0 → **阻断**。
- 不受影响:`T-006`(无依赖关系)。

### 5.3 T-006 失败的影响分析

- 反向图:`reverse[T-006] = []`(无人依赖它)。
- BFS:无任何层。
- `affected_ids = {}`
- 分级:**无影响**(仅记录失败,其余任务继续)。

## 六、与重规划策略的衔接

影响分级直接驱动策略选择(见 `references/replan-strategies.md`):

- **阻断** → 优先"拆分"(把失败任务拆小重试)或"降级"(换降级方案);不可"跳过"。
- **降级** → 可"跳过"(P1/P2 任务跳过,标注下游影响)或"合并"。
- **无影响** → 通常"重排"或不调整(仅记录失败,后续照常执行)。

脚本 `replan.py` 的 `suggest_strategy` 按此规则给出框架性建议,实际策略由 AI 在 SKILL.md 引导下决策。
