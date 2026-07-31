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

# ---------- 汇总 ----------
Write-Host ""
if ($script:fail -gt 0) {
    Write-Host "校验结果：$($script:fail) 项 FAIL" -ForegroundColor Red
    exit 1
} else {
    Write-Host "校验结果：全部通过" -ForegroundColor Green
    exit 0
}
