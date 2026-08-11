from pathlib import Path
import sys, re, json, yaml

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "SKILL.md",
    "workflow.yaml",
    "stages/01_evidence_normalization.md",
    "stages/02_business_analysis.md",
    "stages/03_product_requirements_prd.md",
    "stages/04_technical_handoff.md",
    "stages/05_delivery_planning.md",
    "gates/quality_gate.md",
    "templates/01_current_business_research_analysis.md",
    "templates/02_requirement_pool.csv",
    "templates/03_prd_draft.md",
    "templates/04_technical_handoff.md",
    "templates/05_delivery_plan.md",
    "templates/06_open_questions.csv",
    "templates/07_risk_register.csv",
    "references/information_classification.md",
    "references/traceability.md",
    "references/routing.md",
    "schemas/workflow_state.schema.json",
]

errors = []

for rel in REQUIRED:
    if not (ROOT / rel).exists():
        errors.append(f"missing: {rel}")

# Validate JSON
try:
    json.loads((ROOT / "schemas/workflow_state.schema.json").read_text(encoding="utf-8"))
except Exception as e:
    errors.append(f"invalid json schema: {e}")

# YAML optional if PyYAML exists
try:
    import yaml
    yaml.safe_load((ROOT / "workflow.yaml").read_text(encoding="utf-8"))
except ImportError:
    pass
except Exception as e:
    errors.append(f"invalid workflow yaml: {e}")

# Ensure business analysis has all ten chapters
ba = (ROOT / "stages/02_business_analysis.md").read_text(encoding="utf-8")
chapters = [
    "一、调研基本信息",
    "二、业务整体概况",
    "三、业务现状分析",
    "四、用户角色分析",
    "五、系统现状分析",
    "六、数据与接口分析",
    "七、业务问题总结",
    "八、建设机会分析",
    "九、待确认事项清单",
    "十、调研结论",
]
for c in chapters:
    if c not in ba:
        errors.append(f"business analysis missing chapter: {c}")

# Ensure Stage 3 and its template require a traceable product architecture.
stage3 = (ROOT / "stages/03_product_requirements_prd.md").read_text(encoding="utf-8")
prd_template = (ROOT / "templates/03_prd_draft.md").read_text(encoding="utf-8")
quality_gate = (ROOT / "gates/quality_gate.md").read_text(encoding="utf-8")
workflow = yaml.safe_load((ROOT / "workflow.yaml").read_text(encoding="utf-8"))

for required_phrase in [
    "## Product Architecture",
    "产品能力架构图",
    "待确认、候选接入和产品建议不得与已确认主线使用相同状态表达",
    "产品架构只表达产品能力、业务场景和协同边界",
]:
    if required_phrase not in stage3:
        errors.append(f"product architecture rule missing in Stage 3: {required_phrase}")

for required_phrase in [
    "## 三、产品架构",
    "```mermaid",
    "### 3.2 架构分层说明",
    "对应REQ",
    "### 3.3 产品架构原则与边界",
]:
    if required_phrase not in prd_template:
        errors.append(f"product architecture section missing in PRD template: {required_phrase}")

for required_phrase in [
    "是否包含产品能力架构图",
    "是否明确区分已确认主线、产品建议和待确认/候选接入",
    "是否错误输出了技术组件、部署拓扑或未经确认的接口能力",
]:
    if required_phrase not in quality_gate:
        errors.append(f"product architecture check missing in quality gate: {required_phrase}")

stage3_config = next((s for s in workflow.get("stages", []) if s.get("id") == "stage_3"), {})
required_architecture_gates = {
    "product_capability_architecture_complete",
    "architecture_nodes_traceable",
    "candidate_scope_visually_distinct",
    "product_architecture_not_technical_architecture",
}
missing_architecture_gates = required_architecture_gates - set(stage3_config.get("gate", []))
for gate in sorted(missing_architecture_gates):
    errors.append(f"Stage 3 workflow gate missing: {gate}")

# Ensure Stage 3 and its template require terminal-aware navigation and pages.
for required_phrase in [
    "## Product Navigation and Page Structure",
    "输入明确“一个端”时不得拆分多个客户端",
    "产品导航树",
    "页面层级与页面清单",
    "角色/身份可见性矩阵",
    "核心页面流",
    "终端或载体口径冲突时不得自行覆盖旧证据",
]:
    if required_phrase not in stage3:
        errors.append(f"navigation/page rule missing in Stage 3: {required_phrase}")

for required_phrase in [
    "### 3.4 产品导航与页面结构",
    "#### 3.4.1 终端策略基线",
    "#### 3.4.2 产品导航树",
    "#### 3.4.3 页面层级与页面清单",
    "#### 3.4.4 角色/身份可见性矩阵",
    "#### 3.4.5 核心页面流",
    "#### 3.4.6 导航与页面规则",
]:
    if required_phrase not in prd_template:
        errors.append(f"navigation/page section missing in PRD template: {required_phrase}")

for required_phrase in [
    "是否包含终端策略基线、产品导航树和页面层级/清单",
    "是否错误拆分或合并客户端",
    "是否被错误作为默认可见导航",
    "是否在无输入依据时把运营后台、供应商端或内部办公端放入用户端",
    "是否保留双方证据并进入 `Q/RISK`",
]:
    if required_phrase not in quality_gate:
        errors.append(f"navigation/page check missing in quality gate: {required_phrase}")

required_navigation_gates = {
    "terminal_strategy_source_backed",
    "product_navigation_and_page_structure_complete",
    "page_groups_traceable_to_requirements",
    "role_visibility_and_core_flows_complete",
    "single_multi_terminal_constraint_respected",
    "candidate_pages_not_default_visible",
    "user_and_management_terminal_boundaries_preserved",
    "terminal_conflicts_visible",
}
missing_navigation_gates = required_navigation_gates - set(stage3_config.get("gate", []))
for gate in sorted(missing_navigation_gates):
    errors.append(f"Stage 3 navigation workflow gate missing: {gate}")

# Genericity checks.
# The package must not ship project/example folders or pre-seeded domain modules.
if (ROOT / "examples").exists():
    errors.append("examples directory is not allowed in the generic package")

skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
for required_phrase in [
    "不预设任何行业",
    "所有业务名、系统名、角色名、渠道名、数字、约束，均从用户输入中提取",
]:
    if required_phrase not in skill_text:
        errors.append(f"genericity rule missing in SKILL.md: {required_phrase}")

if errors:
    print("FAIL")
    for e in errors:
        print("-", e)
    sys.exit(1)

print("PASS")
print(f"validated {len(REQUIRED)} required files")
