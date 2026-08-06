# 维度 5:执行质量审查规则

> 本文件定义"执行后评测"模式的审查规则。仅当审查模式为"执行后评测"时读取本文件。

---

## 一、适用场景

执行后评测模式用于:skill 执行完成、产出实际产物后,对产物质量进行评测。与静态审查(维度 1~4)的区别:

| 对比项 | 静态审查(维度 1~4) | 执行后评测(维度 5) |
|---|---|---|
| 审查对象 | skill 定义文件(SKILL.md/references) | skill 的实际产出物 |
| 审查时机 | skill 设计/修改后 | skill 执行后 |
| 核心问题 | skill 写得对不对 | skill 产出好不好 |
| 阻断权 | 无(建议性) | 无(标 WARNING 进报告) |

---

## 二、四个检查项

### 2.1 产物完整性(E1)

检查产物是否缺失必填字段/章节。

| # | 检查项 | 通过条件 | 失败码 |
|---|---|---|---|
| E1.1 | 必填字段存在 | 产物含 skill 声明的所有必填字段 | `E1-FIELD-MISSING` |
| E1.2 | 必填章节存在 | 文档类产物含声明的所有必填章节 | `E1-SECTION-MISSING` |
| E1.3 | 产物文件存在 | 声明的产物路径都有对应文件 | `E1-FILE-MISSING` |
| E1.4 | 产物非空 | 产物文件非空(>0 字节) | `E1-EMPTY-OUTPUT` |

### 2.2 产物规范符合度(E2)

检查产物是否符合声明的 schema/格式。

| # | 检查项 | 通过条件 | 失败码 |
|---|---|---|---|
| E2.1 | JSON 可解析 | JSON 产物能被 `json.loads` 解析 | `E2-JSON-INVALID` |
| E2.2 | 符合 schema | 产物字段与声明的 schema 一致 | `E2-SCHEMA-MISMATCH` |
| E2.3 | 格式正确 | 文档类产物格式正确(如 Markdown 语法/HTML 结构) | `E2-FORMAT-INVALID` |
| E2.4 | 编码正确 | 产物为 UTF-8 编码 | `E2-ENCODING-INVALID` |

### 2.3 可运行性(E3)

检查代码类产物能否跑起来。

| # | 检查项 | 通过条件 | 失败码 |
|---|---|---|---|
| E3.1 | 依赖可安装 | package.json/requirements.txt 声明的依赖可安装 | `E3-DEP-UNINSTALLABLE` |
| E3.2 | typecheck 通过 | TypeScript 产物 `tsc --noEmit` 退出码 0 | `E3-TYPECHECK-FAILED` |
| E3.3 | 构建通过 | 产物能成功构建(vite build / npm run build) | `E3-BUILD-FAILED` |
| E3.4 | 启动通过 | 产物能启动(如 HTTP 服务返回 200) | `E3-STARTUP-FAILED` |

> E3 仅适用于代码类产物;文档类产物跳过本项。

### 2.4 与声明符合度(E4)

检查 description 声称的能力 vs 实际产出。

| # | 检查项 | 通过条件 | 失败码 |
|---|---|---|---|
| E4.1 | 能力覆盖 | description 声称的能力在产物中有体现 | `E4-CAPABILITY-MISSING` |
| E4.2 | 输入输出对应 | 声明的输入→输出映射在产物中验证 | `E4-IO-MISMATCH` |
| E4.3 | 无过度声明 | 产物未超出 description 声明范围 | `E4-OVER-CLAIMED` |
| E4.4 | 边界遵守 | 产物未违反 skill 声明的边界(如"不产出 X") | `E4-BOUNDARY-VIOLATED` |

---

## 三、严重级别

| 级别 | 含义 | 示例 |
|---|---|---|
| **CRITICAL** | 产物无法使用或产出错误结果 | JSON 不可解析;必填字段全缺;构建失败 |
| **WARNING** | 产物可用但有缺陷 | 部分字段缺失;格式小问题;typecheck 有警告 |
| **INFO** | 优化空间 | 命名不一致;注释缺失;可进一步优化 |

---

## 四、评测流程

```
1. 读取 skill 的 SKILL.md,提取声明的必填字段/章节/schema/能力
2. 读取 skill 的实际产物
3. 按 E1→E2→E3→E4 顺序检查
   - E1 产物完整性:对照声明的必填项
   - E2 规范符合度:对照声明的 schema
   - E3 可运行性:对代码类产物跑 typecheck/build(可选,需标准测试集)
   - E4 声明符合度:对照 description 声称的能力
4. 产出 execution-eval-report.md + execution-eval-report.json
```

---

## 五、产出格式

### 5.1 Markdown 报告(execution-eval-report.md)

```markdown
# 执行后评测报告

- 评测时间:{ISO8601}
- 被评测 skill:{skill 名}
- 产物路径:{产物路径}
- 结论:{PASS | FAIL}
- 问题数:{N}(CRITICAL:{N1} / WARNING:{N2} / INFO:{N3})

## 评测清单
| # | 检查项 | 结果 | 详情 |
|---|---|---|---|

## 问题清单
| # | 检查项 | 失败码 | 严重度 | 详情 | 修复建议 |
|---|---|---|---|---|---|

## 评分
- 完整性:{score}/100
- 规范性:{score}/100
- 可运行性:{score}/100(代码类) / N/A(文档类)
- 符合度:{score}/100
- 综合:{score}/100
```

### 5.2 JSON 工件(execution-eval-report.json)

```json
{
  "evalMode": "execution",
  "skill": "{skill 名}",
  "artifactPath": "{产物路径}",
  "timestamp": "{ISO8601}",
  "conclusion": "PASS|FAIL",
  "checks": [
    {
      "id": "E1.1",
      "name": "必填字段存在",
      "result": "PASS|FAIL",
      "severity": "CRITICAL|WARNING|INFO",
      "detail": "{详情}",
      "code": "{失败码}"
    }
  ],
  "summary": {
    "total": 16,
    "passed": 14,
    "failed": 2,
    "critical": 0,
    "warning": 2,
    "info": 0
  },
  "scores": {
    "completeness": 100,
    "conformity": 85,
    "runnability": 90,
    "alignment": 95,
    "overall": 92
  }
}
```
