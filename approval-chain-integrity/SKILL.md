---
name: "approval-chain-integrity"
description: "带审核流/审批流的业务系统『审批链断链』排查手册。当审批任务已生成但处理时报 403/无权限、任务派给了错误的人、或出现『审批人不得审批自己提报的单据』类业务校验拦截、审批流『提报后卡住不动』时调用。覆盖流配置 × 角色权限 × 人员归属三要素核查、审批人动态解析（部门负责人/角色/指定人）陷阱、以及把修正固化为回归测试的方法。"
agent_created: true
---

# 审批链完整性排查（流配置 × 角色权限 × 人员归属）

## 零、核心认知：一个等式

> **审批链可用性 = 流配置 × 角色权限 × 人员归属**
> 三者是**乘法**关系，任一为 0，链路即断。

最坑的是：**断点往往不在审核流代码里，而在主数据（种子/迁移）里**。
审核流看着完全正常 —— 流存在、级次对、任务也生成了 —— 但审批人点「通过」就是 403。

**判断口诀**：
- 报错在**提报时** → 大概率是流配置（匹配四档未命中 / 无兜底流 / 锚点不可达）；
- 报错在**处理任务时** → 大概率是角色权限或人员归属（任务已生成，说明流配置是对的）。

---

## 一、三要素逐项核查

### 1.1 流配置（Flow Config）

| 检查项 | 说明 |
|---|---|
| biz_type 有对应流吗 | 缺流 → 提报即失败；多业务共用流时要确认**没有串到兜底流** |
| 匹配四档能否命中 | ① 指定人 → ② 精确部门 → ③ 部门上溯 → ④ 通配；**未命中要显式拒绝，不能静默免审** |
| 级次审批人类型 | `ROLE` / `USER` / `DEPT_LEADER` / `DEPT_ROLE` 四枚举 |
| 锚点可达性 | `deptIds` 指向的部门在树里是否真的存在、是否被停用 |
| 兜底链 | 「上溯 → fallback_role → 阻断」；上溯层数上限（3 级树通常 1 级） |
| 会签/或签 | 或签 ANY 一人过级、同级其余置 `SKIPPED`；会签 ALL 需同级全过，且**末级须显式允许会签** |

### 1.2 角色权限（Role Permission）—— 最高频根因

**症状**：任务生成成功，审批人处理时 `403 / 无权限执行该操作`。

**根因类型**：审批人的**角色**不具备审批权限码（如 `audit:approve`）。

**必查清单**：
```sql
-- 1) 找出该流首级会解析到哪些"角色"
SELECT id, flow_id, level_no, approver_type, approver_value
  FROM wf_audit_flow_level WHERE flow_id = ? ORDER BY level_no;

-- 2) 这些角色持有哪些权限码（关键：逐个人工过一遍，别只看有没有 approve）
SELECT id, role_code, role_name, permission_codes
  FROM sys_role WHERE role_code IN (...);

-- 3) 这些角色有持有人吗（无持有人的角色 = 死链）
SELECT id, username, role_ids FROM sys_user WHERE role_ids LIKE '%<roleId>%';
```

**陷阱 A：`permission_codes` 是整列覆盖写**
迁移脚本里 `UPDATE sys_role SET permission_codes='a,b,c'` 会**静默丢掉**未列出的旧权限码。
→ 必须列出**完整全集**（含此前各轮迁移累积授予的），并在注释里警示。
→ 每次改动后 `SELECT permission_codes` 人工比对，别只看迁移「成功执行」。

**陷阱 B：权限码粒度错配**
业务系统常见拆分为 `booking:approve`（业务审批）/ `audit:approve`（通用审核）。
→ 只发一个会导致「某条流能走、另一条走不通」。必须确认**审批入口实际检查的是哪个码**。

**陷阱 C：角色有权限但没持有人**
角色定义正确、`permission_codes` 也全，但 `sys_user.role_ids` 里没有任何人挂这个角色 → 流能生成任务但任务**无 assignee**。
→ 修法：`UPDATE sys_user SET role_ids='原有,新角色id' WHERE id=<某人>`。

### 1.3 人员归属（Personnel Attribution）—— 第二高频根因

**核心陷阱：`DEPT_LEADER` 是「动态解析」**，它不指向固定人，而是**按申请部门运行时求部门负责人**。

于是产生两个互相纠缠的问题：

| 问题 | 症状 | 修法 |
|---|---|---|
| **负责人是业务提报岗** | 本人提报 → 首级任务派给自己 → 撞「审批人不得审批自己提报的单据」（BR-043 类） | 把该部门负责人改指**审批岗**（且该岗须持审批权限码） |
| **负责人角色缺审批权** | 任务派给负责人，负责人处理时 403 | 给该角色补审批权限码（见 1.2 陷阱 A） |

**自检 SQL**：
```sql
-- 部门负责人 × 其角色 × 其权限，一眼看出谁有隐患
SELECT d.id AS dept_id, d.dept_name, d.leader_id, u.username, u.role_ids, r.permission_codes
  FROM sys_department d
  LEFT JOIN sys_user u ON u.id = d.leader_id
  LEFT JOIN sys_role r ON FIND_IN_SET(r.id, u.role_ids)
 WHERE d.leader_id IS NOT NULL;
```

**判定规则**：
- 负责人**必须**具备该链路的审批权限码；
- 负责人**不应**是纯提报岗（既提报又自审，业务上不成立）；
- 若确实需要同一人兼顾，应在**流程设计层**用「指定人例外」而非「部门负责人」承载。

---

## 二、错误码速查（按症状反推）

| 症状 / 错误码 | 大概率根因 | 先查什么 |
|---|---|---|
| 403 / 无权限执行该操作 | 审批人角色缺审批权限码 | §1.2，特别是 `permission_codes` 是否被覆盖写截断 |
| **「当前用户不是该任务的审批人」** | **测试/前端用了错误的 token** —— 任务 assignee 是流解析出来的特定人 | 读任务的 `assigneeId`，用**本人**身份操作 |
| 「审批人不得审批自己提报的单据」 | ① 真实主数据缺陷（负责人=提报岗）② **测试用例自己造成了自审**（提报人恰好是末级审批人） | 先看是不是**测试脚本**选错了提报人 |
| 任务生成但没人能处理 | 角色无持有人 / assignee 为空 | §1.2 陷阱 C |
| 提报即失败 / 卡在提报 | 流配置：四档未命中、无兜底、锚点不可达 | §1.1 |
| 一条流能走、另一条不能 | 审批权限码粒度错配（`booking:approve` vs `audit:approve`） | §1.2 陷阱 B |

> ⚠️ **「不是审批人」和「自审拦截」在测试中极易被误读成产品缺陷**。
> 它们在多数情况下恰恰说明**产品按设计正确工作** —— 是测试脚本没按流的解析结果来调用。
> 排查顺序：**先怀疑测试脚本，再怀疑产品**；确认是产品缺陷前，务必回读任务的 assignee 与审核流的级次配置。

---

## 三、迁移修复模板

```sql
-- 修复 1：给角色补审批权（★ 必须列全集，否则静默截断）
-- 原（上一轮迁移后）：'resource:view,booking:view,booking:submit,master:view,master:edit,audit:view'
UPDATE sys_role
   SET permission_codes = 'resource:view,booking:view,booking:submit,master:view,master:edit,audit:view,audit:approve'
 WHERE role_code = 'OPS';

-- 修复 2：部门负责人改指审批岗（解自审冲突）
UPDATE sys_department SET leader_id = <审批岗用户id> WHERE id = <部门id>;
```

**迁移纪律**：
- 版本号递增，**不改已执行文件**（Flyway 校验和会失败）；
- 新增前先 `listdir` 取最大版本号；
- 清理 `target/classes/db/migration` 旧副本，否则可能加载到过期副本；
- 迁移后**必须**重建内存库（H2）并跑真实链路，不能只看迁移日志「Successfully applied」。

---

## 四、把修正固化为回归测试（最重要的一步）

这类缺陷**改完不加固 = 下次调主数据必然复发**。写断言时必须把「三要素」都覆盖到：

```java
@SpringBootTest
@ActiveProfiles("test")
class ApprovalChainIntegrityTest {

    /** 要素②：所有会被 DEPT_LEADER 解析到的用户，其角色必须持审批权 */
    @Test
    void everyDeptLeaderRoleShouldHoldApproveAuthority() {
        for (Long userId : DEPT_LEADER_IDS) {
            List<Role> roles = rolesOf(userMapper.selectById(userId));
            assertTrue(roles.stream().flatMap(r -> permCodes(r).stream())
                    .anyMatch("audit:approve"::equals),
                "BR-108：该用户可被 DEPT_LEADER 解析为审批人，其角色必须持 audit:approve，"
              + "否则任务生成后 403 断链。当前角色：" + roles.stream().map(Role::getRoleCode).toList());
        }
    }

    /** 要素③：部门负责人不应是纯提报岗（解自审冲突） */
    @Test
    void deptLeaderShouldBeAnApproverNotTheSubmitter() { /* 断言该部门下无"派给提报岗"的任务 */ }

    /** 要素②直断言：角色权限码包含审批权 */
    @Test
    void opsRoleShouldHoldApproveAuthority() { /* assertTrue(permCodes(ops).contains("audit:approve")) */ }
}
```

> **注意实体包路径**：用户/角色实体常在 `domain.organization.entity`，
> 而非名字更"直觉"的 `domain.system.entity`（`system` 域往往只有日志/配置/幂等表）。
> 写测试前先确认实际包路径，否则编译失败。

---

## 五、收口清单

1. 逐条走完 §1.1 / §1.2 / §1.3 三张核查表，**不跳项**；
2. 每条修正配一支迁移（版本递增，不改旧文件，`permission_codes` 列全集）；
3. 补回归测试（至少覆盖「角色持权限」+「负责人非提报岗」两类断言）；
4. 跑**全量**单测（不是只跑改动的类）；
5. 重建内存库 + 真实启动 jar，跑 **端到端链路**（提报 → 首级审批 → 二级 → 末级 → 终态），
   且**每一步都用该任务 assignee 本人的身份**调用；
6. 跑旧切片回归；
7. 记录：**症状 → 根因 → 修法 → 防复发**。

---

## 六、反面清单

- ❌ 只看「流配置存在」就认为链路通 —— 权限与归属是独立的两个乘数；
- ❌ 改 `permission_codes` 时只写要加的那一个码（整列覆盖写会截断）；
- ❌ 用同一个管理员账号跑完整条审批链（会掩盖 assignee 解析错误，还会撞自审拦截）；
- ❌ 看到「不是审批人 / 不得审批自己提报的单据」就判为产品缺陷 —— 先怀疑测试脚本；
- ❌ 只给角色补权限、不管**谁持有该角色**（角色空持有 = 死链）；
- ❌ 修完不写回归测试 —— 下一次调组织主数据时必然复发（本文档记录的真实案例：该族缺陷在同一项目内**连续复发 4 次**）。
