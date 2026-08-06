# validate.ps1 — 产品工作台一致性防回归校验
# 用法：powershell -File _shared/validate.ps1
# 退出码：0 = 全部通过；1 = 存在 FAIL 项

$ErrorActionPreference = 'Continue'
$ws = Split-Path -Parent $PSScriptRoot   # 工作台根目录（_shared 的上一级）
$sharedDir = Join-Path $PSScriptRoot 'references'
$script:fail = 0

function Fail($msg) { Write-Host "FAIL  $msg" -ForegroundColor Red; $script:fail++ }
function Pass($msg) { Write-Host "PASS  $msg" -ForegroundColor Green }

# ---------- 1. 共享文件不得在 skill 内重建拷贝 ----------
# 允许清单：相对工作台根的路径（正斜杠），这些是有意的阶段特有副本
$allowList = @(
    'generate-system-prd/references/schemas/pages.example.json'   # PRD 阶段快照，_stageNote 已说明
)

$sharedNames = Get-ChildItem -Recurse -File $sharedDir |
    Where-Object { $_.Name -ne 'README.md' } |
    Select-Object -ExpandProperty Name -Unique

$skillRefDirs = Get-ChildItem -Directory $ws |
    Where-Object { $_.Name -ne '_shared' -and (Test-Path (Join-Path $_.FullName 'references')) } |
    ForEach-Object { Join-Path $_.FullName 'references' }

$dupeCount = 0
foreach ($dir in $skillRefDirs) {
    Get-ChildItem -Recurse -File $dir | Where-Object { $sharedNames -contains $_.Name } | ForEach-Object {
        $rel = $_.FullName.Replace("$ws\", '').Replace('\', '/')
        if ($allowList -notcontains $rel) {
            Fail "共享文件被本地重建：$rel（权威副本在 _shared/references）"
            $dupeCount++
        }
    }
}
if ($dupeCount -eq 0) { Pass "无共享文件的本地重复拷贝（允许清单：$($allowList.Count) 项）" }

# ---------- 2. SKILL.md 中引用的 references 路径必须存在 ----------
$refCheck = 0
Get-ChildItem -Directory $ws | Where-Object { $_.Name -ne '_shared' } | ForEach-Object {
    $skillDir = $_.FullName
    $skillMd = Join-Path $skillDir 'SKILL.md'
    if (-not (Test-Path $skillMd)) { return }
    $content = Get-Content $skillMd -Raw -Encoding UTF8
    $tokens = [regex]::Matches($content, '`([^`]+)`') | ForEach-Object { $_.Groups[1].Value } |
        Where-Object { $_ -match '^(\.\./_shared/)?references/' }
    foreach ($token in $tokens) {
        $refCheck++
        $resolved = [IO.Path]::GetFullPath((Join-Path $skillDir $token))
        if (-not (Test-Path $resolved)) {
            Fail "$(Split-Path $skillDir -Leaf)/SKILL.md 引用了不存在的路径：$token"
        }
    }
}
Pass "SKILL.md references 引用路径检查完成（共 $refCheck 处）"

# ---------- 3. 全部 references JSON 可解析 ----------
$jsonCount = 0; $jsonBad = 0
$jsonDirs = @($sharedDir) + $skillRefDirs
foreach ($dir in $jsonDirs) {
    Get-ChildItem -Recurse -Filter '*.json' -Path $dir | ForEach-Object {
        $jsonCount++
        try { Get-Content $_.FullName -Raw -Encoding UTF8 | ConvertFrom-Json | Out-Null }
        catch { $jsonBad++; Fail "JSON 无法解析：$($_.FullName.Replace("$ws\", '')) -> $($_.Exception.Message)" }
    }
}
if ($jsonBad -eq 0) { Pass "JSON 语法检查通过（共 $jsonCount 个文件）" }

# ---------- 4. design-tokens 单点与版本 ----------
$tokens = Get-ChildItem -Recurse -Filter 'design-tokens.default.json' -Path $ws
if ($tokens.Count -ne 1) {
    Fail "design-tokens.default.json 应仅存于 _shared，实际发现 $($tokens.Count) 处"
} else {
    $tk = Get-Content $tokens[0].FullName -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($tk.version -ne '1.3') { Fail "design-tokens 版本为 $($tk.version)，应为 1.3" }
    elseif ($tokens[0].FullName -notlike "*_shared*") { Fail "design-tokens 不在 _shared 中：$($tokens[0].FullName)" }
    else { Pass "design-tokens 单点存在且版本 1.3" }
}

# ---------- 5. Tool skill 必须有 scripts/ 目录 ----------
$toolSkills = @('tool-git-ops','tool-ci-ops','tool-deploy-ops','tool-db-ops','tool-monitor-ops')
$toolMissing = 0
foreach ($name in $toolSkills) {
    $dir = Join-Path $ws $name
    if (-not (Test-Path (Join-Path $dir 'scripts'))) {
        Fail "Tool skill 缺失 scripts/ 目录:$name"
        $toolMissing++
    }
}
if ($toolMissing -eq 0) { Pass "全部 Tool skill 含 scripts/ 目录(共 $($toolSkills.Count) 个)" }

# ---------- 6. 审查类 skill 必须声明"只读"约束 ----------
$readonlySkills = @('guardrail','diff-reviewer','skill-auditor','code-review')
$roMissing = 0
foreach ($name in $readonlySkills) {
    $md = Join-Path $ws "$name/SKILL.md"
    if (Test-Path $md) {
        $c = Get-Content $md -Raw -Encoding UTF8
        if ($c -notmatch '只读不写|只读') {
            Fail "$name/SKILL.md 未声明'只读'约束"
            $roMissing++
        }
    }
}
if ($roMissing -eq 0) { Pass "全部审查类 skill 声明了'只读'约束(共 $($readonlySkills.Count) 个)" }

# ---------- 7. 新 skill frontmatter 必填 name + description ----------
$newSkills = @('tool-git-ops','tool-ci-ops','tool-deploy-ops','tool-db-ops','tool-monitor-ops','code-review','debug-fix','refactor','guardrail','diff-reviewer','project-knowledge-base','failure-casebook','skill-runtime','task-planner','replanner','workflow-runtime','codebase-rag','skill-usage-tracker','prompt-registry','agent-orchestrator')
$fmMissing = 0
foreach ($name in $newSkills) {
    $md = Join-Path $ws "$name/SKILL.md"
    if (Test-Path $md) {
        $head = Get-Content $md -TotalCount 10 -Encoding UTF8 -ErrorAction SilentlyContinue
        $joined = $head -join "`n"
        if ($joined -notmatch '(?m)^name:\s*"?[^\s"]+' -or $joined -notmatch '(?m)^description:\s*"?[^\s"]+') {
            Fail "$name/SKILL.md frontmatter 缺失 name 或 description"
            $fmMissing++
        }
    } else {
        Fail "$name/SKILL.md 不存在"
        $fmMissing++
    }
}
if ($fmMissing -eq 0) { Pass "全部新 skill frontmatter 含 name + description(共 $($newSkills.Count) 个)" }

# ---------- 8. 声明 runtime.yaml 的 skill 必须符合 skill-runtime schema ----------
# 调用 skill-runtime 的 validate_runtime.py scan 校验
# scan 会扫描所有 skill,对声明了 runtime.yaml 的做 schema 校验
# 当前大部分 skill 未声明 runtime.yaml(UNDECLARED),scan 应返回 exit 0
$runtimeValidator = Join-Path $ws 'skill-runtime\scripts\validate_runtime.py'
$runtimeFail = 0
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Fail "python 不可用,无法校验 runtime.yaml(skill-runtime validate_runtime.py scan)"
    $runtimeFail++
} elseif (-not (Test-Path $runtimeValidator)) {
    Fail "skill-runtime/scripts/validate_runtime.py 不存在,无法校验 runtime.yaml"
    $runtimeFail++
} else {
    $runtimeResult = python $runtimeValidator scan 2>&1
    $runtimeExit = $LASTEXITCODE
    if ($runtimeExit -ne 0) {
        Fail "runtime.yaml schema 校验失败(详见 skill-runtime validate_runtime.py scan 输出)"
        $runtimeFail++
    } else {
        Pass "runtime.yaml schema 校验通过(skill-runtime validate_runtime.py scan)"
    }
}

# ---------- 9. workflow.yaml 可解析性(若存在) ----------
# workflow.yaml 是可选产物,当前可能不存在(编排总纲声明可产出,实际产出需运行编译命令)
# 不存在则跳过(PASS);存在则调用 workflow-runtime 的 compile_workflow.py validate 校验
$workflowValidator = Join-Path $ws 'workflow-runtime\scripts\compile_workflow.py'
$workflowYamls = Get-ChildItem -Recurse -Filter 'workflow.yaml' -Path $ws -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notlike '*node_modules*' }
$workflowFail = 0
if ($workflowYamls.Count -eq 0) {
    Pass "无 workflow.yaml 文件(可选产物,跳过校验)"
} elseif (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Fail "python 不可用,无法校验 workflow.yaml(workflow-runtime compile_workflow.py validate)"
    $workflowFail++
} elseif (-not (Test-Path $workflowValidator)) {
    Fail "workflow-runtime/scripts/compile_workflow.py 不存在,无法校验 workflow.yaml"
    $workflowFail++
} else {
    foreach ($wf in $workflowYamls) {
        $wfResult = python $workflowValidator validate --input $wf.FullName 2>&1
        if ($LASTEXITCODE -ne 0) {
            Fail "workflow.yaml 无法解析:$($wf.FullName.Replace("$ws\", ''))"
            $workflowFail++
        }
    }
    if ($workflowFail -eq 0) {
        Pass "workflow.yaml 可解析性校验通过(共 $($workflowYamls.Count) 个文件)"
    }
}

# ---------- 10. prompt-registry 关键 references 必须存在 ----------
$prDir = Join-Path $ws 'prompt-registry'
$prFail = 0
if (Test-Path $prDir) {
    $prRefs = @('references/prompt-versioning.md','references/prompt-structure.md')
    foreach ($ref in $prRefs) {
        $refPath = Join-Path $prDir $ref
        if (-not (Test-Path $refPath)) {
            Fail "prompt-registry 缺失 references 文件:$ref"
            $prFail++
        }
    }
    if ($prFail -eq 0) { Pass "prompt-registry references 完整(prompt-versioning.md + prompt-structure.md)" }
} else {
    Fail "prompt-registry skill 目录不存在"
    $prFail++
}

# ---------- 11. agent-orchestrator 协议文件必须存在 ----------
$aoDir = Join-Path $ws 'agent-orchestrator'
$aoFail = 0
if (Test-Path $aoDir) {
    $aoRefs = @('references/agent-protocol.md','references/delegation-patterns.md','references/conflict-resolution.md')
    foreach ($ref in $aoRefs) {
        $refPath = Join-Path $aoDir $ref
        if (-not (Test-Path $refPath)) {
            Fail "agent-orchestrator 缺失 references 文件:$ref"
            $aoFail++
        }
    }
    if ($aoFail -eq 0) { Pass "agent-orchestrator references 完整(3 份协议文件)" }
} else {
    Fail "agent-orchestrator skill 目录不存在"
    $aoFail++
}

# ---------- 汇总 ----------
Write-Host ""
if ($script:fail -gt 0) {
    Write-Host "校验结果：$($script:fail) 项 FAIL" -ForegroundColor Red
    exit 1
} else {
    Write-Host "校验结果：全部通过" -ForegroundColor Green
    exit 0
}
