# 18｜评估夹具工程契约

> 方法论见 `17_deterministic_evaluation.md`；本文只管**怎么把它造成能天天跑的东西**。
> 没有契约的评估体系，两周后就会变成三份互相矛盾的脚本。

---

## 0. 五个工具，一个实现

| 工具 | 职责 | 特性 | 谁读 |
|---|---|---|---|
| `level_score`（库） | 结构压力分：读关卡 JSON → 分 + 诊断列 | **纯静态**，秒级，无对局、无随机 | 下面三个都调它 |
| `level_play`（库） | 三策略对局：`naive / strict / greedy / golden` | 一局一跑，无随机 | `level_audit` |
| `level_audit`（库） | 可解性证明：贪心见证 → 有界穷举 → 三态结论 | 预算与结论分开记 | 两个 CLI |
| `score_table`（CLI） | 只出分与排序，**不建 core** | 改完关卡先看曲线，1 秒 | 策划 / 调参的人 |
| `gate_solver`（CLI） | 表格：证明 + 分数 + 三态闸 + PASS/FAIL | 人读 | 交门禁时看 |
| `level_designer`（CLI） | 同上但出 **JSON + 退出码** | 机读 | CI / 报告生成 |

**唯一实现原则**：`isLegal` / `apply` / 死局判定，全工程只允许一份。
求解器、闸门、提示系统、运行时**必须调同一个**。两份拷贝迟早分叉，
那时"报告说能过、实机过不去"就是必然事件。

> 反例（真实事故）：某项目把 `isLegal` 在搜索里重写了一遍，剪枝时漏了一个字段，
> 于是穷举"证明"了关卡无解；实际 12 步能过。**假无解比找不到解更危险**，因为报告会写"确定"。

---

## 1. 目录与命名

```
tools/
  LevelScore.gd     # 或 level_score.py —— 结构分（唯一实现）
  LevelPlay.gd      # 对局与策略
  LevelAudit.gd     # 证明与编排
  score_table.gd    # CLI：只出分
  gate_solver.gd    # CLI：表格
  level_designer.gd # CLI：JSON + 退出码
  repro_check.py    # 两次运行比对（本 skill 自带，直接可用）
  knob_sweep.*      # 单旋钮单调性扫描
build/
  level_design/
    proposed/       # 草案关卡：先在这里验，不许直接改 data/levels
    rejected/       # 验不过的留档（别删，下次还会踩同一个坑）
```

**草案目录是硬要求**：任何关卡改动先在 `proposed/` 里跑完闸门，验过再写回正式目录。
反过来不可回退——写回之后再发现不可解，已经有人看到过那份数据了。

---

## 2. CLI 契约

```bash
# 只出分（秒级，改完就看）
python tools/score_table.py --dir data/levels

# 全量审计（表格，人读）
python tools/gate_solver.py --dir data/levels

# 机读 + 退出码（CI 用）
python tools/level_designer.py --dir data/levels --out build/eval/gate.json

# 单关加大穷举预算（只在该关可解性未知时用）
python tools/level_designer.py --level 5 --nodes 8000

# 验草案
python tools/gate_solver.py --dir build/level_design/proposed
```

| 退出码 | 含义 | CI 行为 |
|---|---|---|
| `0` | 全部 PASS（或全部豁免且已登记） | 放行 |
| `2` | 存在 FAIL 关 | **阻断**，打印失败清单 |
| `3` | 输入无法解析 | 阻断（是工具或数据坏了，不是关卡坏了） |

**不许用 `1` 表示关卡失败**：`1` 是脚本自身异常，混在一起就没法区分"关卡不好"和"工具崩了"。

---

## 3. 机读输出 schema

写进 `docs/DIFFICULTY_REVIEW.json` 的 `evaluation` 块（Gate 2.5 读它）：

```json
{
  "evaluation": {
    "tier": "deterministic",
    "metric": "pressure = C x (1 + T)",
    "normalization": {"basis": "max", "basis_version": "suzhou-8"},
    "data_source": "static+deterministic",
    "repro": {
      "verdict": "pass",
      "fields_compared": 862,
      "timing_fields_stripped": 40,
      "timing_fields_changed": 24,
      "command": "repro_check.py --a run_a.json --b run_b.json --marker LEVEL_DESIGNER_JSON="
    },
    "gate_selftest": {
      "mutations": ["unsolvable", "no_decision", "score_inversion"],
      "detected": ["unsolvable", "no_decision", "score_inversion"],
      "verdict": "pass"
    },
    "validity": {
      "monotonic": "pass",
      "discriminating": "pass",
      "anchored": "pass",
      "falsifiers": [
        "压力分最高的关若 naive 能过 → 指标失效",
        "T>=1 而 naive 存活 → T 与 naive 走位不同源"
      ]
    },
    "summary": {"levels": 8, "solvable": 8, "gate_pass": 2, "exempt": 1, "fail": 6},
    "status": "FAIL"
  }
}
```

字段纪律：

- `tier ∈ {deterministic, sampled, telemetry}`，**必填**。缺省按 `sampled` 处理（旧产物兼容）。
- `repro.fields_compared` 必须 `≥ 10`，否则视为假 PASS（见 §4）。
- `gate_selftest.detected` 必须是三条全中；少一条 = 闸门当前对该类坏关卡是瞎的。
- `status` 是**汇总判定**，与逐关 `verdict` 一致；不一致以逐关为准并在报告里说明。

---

## 4. 可复现自检：连跑两次，剔计时比全字段

```bash
python tools/level_designer.py --dir data/levels --out build/eval/run_a.json
python tools/level_designer.py --dir data/levels --out build/eval/run_b.json
python tools/repro_check.py --a build/eval/run_a.json --b build/eval/run_b.json \
    --marker LEVEL_DESIGNER_JSON= --json build/eval/repro.json
```

实测输出（本 skill 自带工具，真实工程验证过）：

```
== 可复现性校验 ==
  A: run_a.json  (12930 B)
  B: run_b.json  (12935 B)
  比对字段: 862（已剔除计时字段 40 个）
  计时字段变化: 24 / 40 项（>0 是正常的，说明剔除的是真计时）
  REPRO: PASS — 决策字段逐一相等
```

三条设计要点：

1. **剔计时按字段名，不按字段位置**。`ms` 会出现在多层（`entry.ms`、`policies.*.ms`），
   漏一层就假 FAIL。
2. **比全字段，不只比结论**。`verdict` 相同不代表过程可复现——分数、峰位、
   `blocked_episodes` 都可能漂移，而结论恰好没变。
3. **`fields_compared` 过少判 FAIL**。这是防"比了 0 个字段的 PASS"。
   闸门空转和闸门放行，在日志里长得一样。

**不可复现的常见根因**（按出现频率）：

| 根因 | 症状 | 处置 |
|---|---|---|
| 未播种 RNG | 每次数字都不同 | 固定种子，或彻底去掉随机 |
| 字典/哈希遍历顺序 | 字段顺序变、集合内容不变 | 排序后输出，不依赖插入序 |
| 目录遍历顺序 | 关卡顺序偶尔颠倒 | 按 `level_id` 排序后再处理 |
| 并行跑两个进程 | 数字互相污染（实测过） | **禁止并行**，见 §6 |
| 浮点累加顺序 | 末位抖动 | 输出前按固定精度 round |

---

## 5. 闸门自检：注入坏关卡，闸门必须红

**闸门不会红 = 闸门坏了。** 每次改完闸门（或换关卡集）都要跑一次变异测试。

| 注入 | 怎么造 | 闸门必须报 | 若没报 |
|---|---|---|---|
| **无解关** | 复制一关，把某个必需颜色的卡全删掉 | `solvable=false`（或 `unknown`）→ FAIL | 证明层没接上 |
| **无决策关** | 把某关槽位开到 ≥ 卡数（或入口全开 + 单卡载荷超大） | `naive` 通关 → FAIL（无决策） | 闸门只看可解性 |
| **难度倒挂** | 手工把最难关的压力分改成最低 | 排序/`rank` 与压力分不一致 → FAIL | 排序没读分 |
| **假可复现** | 加一个未播种的随机扰动 | `repro` FAIL | 比对没覆盖该字段 |
| **假陷阱**（最隐蔽） | 用"陷阱段不在最前面"的旧关卡数据 | 不变量（如"从第 0 位起连续动不了 == 最长连续动不了"）不成立 → 校验器非 0 退出 | 只查了"`naive` 会不会死"，没查"为什么死" |

注入跑完必须**全部报红**。只要有一条是绿的，就说明闸门对该类问题失明，
此时"全绿通过"比"红"更危险。

**"假陷阱"为什么单列一行**：它不属于"关卡坏了"，而属于"归因错了"。此时每一关
都还可解、`naive` 也还会死，逐关判定**全绿** —— 坏掉的是压力分里那个 `T`。
所以它的判据不能挂在逐关判定上，必须是一条**独立的结构不变量**（两个同源指标必须相等）。
用一张"旧数据"当夹具就够了：旧项目里那种"陷阱段偏了 1~3 位"的存档，正是现成的反例。

> 这条纪律的等价说法：**闸门要能说出"如果我错了，会怎么被发现"**。
> 说不出来的闸门，等于没装。

---

## 6. 性能预算与禁忌

| 项 | 实测值（8 关 / 24×24 / Godot headless） | 结论 |
|---|---|---|
| 纯静态出分 | < 1 秒 | 改完关卡立刻看，不用等 |
| 全量审计（证明 + 三态闸） | ≈ 8–10 秒 | 可以进每次提交 |
| 单关穷举 | 视预算，默认 400 节点 | 只在"未知"时加大 |

**禁忌：**

- **禁止并行跑两个审计进程。** 实测并行会互相干扰，产出互相矛盾的读数
  （这也是抽样口径"不可复现"的成因之一）。
- **禁止在审计里读线上数据或网络。** 审计必须是纯函数：输入关卡文件，输出结论。
- **禁止把计时字段写进报告结论。** 它不是难度，也不是稳定性指标。

---

## 7. Gate 2.5 字段对接

| Gate 2.5 检查项 | 读 `evaluation` 的哪个字段 | 判据 |
|---|---|---|
| 2.5.13 可复现性证据 | `repro.verdict` / `fields_compared` | `pass` 且 `fields_compared ≥ 10` |
| 2.5.14 闸门有牙齿 | `gate_selftest.detected` / `summary` | 三变异全中；且 `naive` 全过的关有豁免登记或判 FAIL |
| 2.5.15 指标有效性 | `validity.*` / `normalization` / `falsifiers` | 单调/可分/锚点均 `pass`；`falsifiers` 非空；`basis_version` 非空 |
| 2.5.7 门禁结论可解释 | `status` / 逐关 `verdict` | `PASS`，或 FAIL 项在 `LEVEL_PLAN.md §5` 逐条处置 |

> 老项目兼容：`evaluation` 块缺失时，2.5.13~2.5.15 记 **WARNING**（`EVAL_BLOCK_MISSING`），
> 不判 FAIL。但**不得**因此认为"已通过"——报告结论仍取决于 2.5.7。

---

## 8. 迁移路径（已有抽样口径的老项目）

按顺序做，**不要并行改**：

1. **先立双轨，但只让新口径说话**：旧脚本保留（老命令不崩），输出打 `DEPRECATED` 标记，
   不再进报告。文档顶部给旧口径写墓志铭（作废日期 + 原因 + 现指向）。
2. **补 L0 证明**：先只有"贪心见证"，能跑通即可；穷举后加。此阶段 `tier` 写
   `deterministic` 但 `validity.anchored` 留 `pending`。
3. **补 L1 三态闸**：`naive` 先跑起来，把"全关 naive 都过"这个事实**写在报告第一行**——
   这是最有价值的一条诊断，不是失败。
4. **补 L2 结构与单调扫描**：`knob_sweep` 跑一遍，确认放宽 → 分数单调不增。
5. **补锚点与变异测试**：两端关卡对齐，三种坏关全红。
6. **收口**：`evaluation` 块填满，Gate 2.5 的 2.5.13~2.5.15 从 WARNING 转正式判据。

每步都要能独立交付一份"比上一步更可信"的报告。**不要等到全绿才出报告**——
一份写着"8 关全部可解、7 关 naive 也能过"的 FAIL 报告，比一份漂亮的 PASS 报告有用得多。
