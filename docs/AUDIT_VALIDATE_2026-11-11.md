# 校验脚本审查（2026-11-11 16:10）

> 对象：`_shared/validate.ps1`。它每轮都输出"全部通过"，但从未被审过 ——
> 和生成器模板同一类位置：**被所有人信任、被所有人跳过**。
>
> 方法：不是读代码找 bug，是把它的判定逻辑单独跑一遍（写探针 .ps1，避免命令行转义干扰），
> 再造反例，最后用**独立实现复算同一个数**。

## 1 结论

**8 处问题（2 个 P0）。** 其中 P0-1 意味着：这一项检查对 `game-level-design`（本仓库反引号最多的文件）
**从来没有工作过**，而它每轮都在打印 `PASS ... 共 129 处`。

## 2 P0

### V-01 正则与代码块配对错误，检查对关键文件完全失效

```
[regex]::Matches($content, '`([^`]+)`')
```

`[^`]+` 贪婪且**允许跨行**。SKILL.md 里的 ``` 代码块围栏会被当成"两个相邻的单反引号"，
与正文里的行内反引号混在一起配对，于是匹配出的是**跨段落的大块正文**，不是一个路径 token。

实测 `game-level-design/SKILL.md`：

```
反引号总匹配: 85
references/ 开头 token 数: 0     ← 该文件明明有 8 处 references 引用
```

而脚本打印的是 `PASS ... 共 129 处` —— 那 129 全来自其他 skill 的偶然命中。

修法：`` `[^`\r\n]+` ``（禁止跨行）。修正后该 skill 从 0 → 8，全库从 129 → **297**（去重口径）。

### V-02 FAIL 与 PASS 同时打印

```powershell
foreach ($token in $tokens) { if (...) { Fail "..." } }
Pass "SKILL.md references 引用路径检查完成（共 $refCheck 处）"   # ← 无条件
```

哪怕报了 20 条 FAIL，末尾仍有一行 PASS。汇总会 exit 1，但单项状态是谎报，
而人（和 grep PASS 的脚本）读的是单项行。

修法：记 `$refFailBefore`，只在失败数未增加时打 PASS。其余 14 段本来就有计数判断，只有这一段漏了。

## 3 P1

### V-03 裸文本引用完全在检查视野外

检查只认**反引号包裹**的写法。但仓库里大量引用是裸写（表格单元格、列表项、markdown 链接）：

```
| references/execution-semantics.md |
- references/design-principles-overview.md
[references/product-configuration.md](references/product-configuration.md)
```

独立统计：这类裸引用共 282 处，此前**一处都没查**。

修法：加一条裸引用正则 `(?<![/\w`])references/([A-Za-z0-9_\-]+\.(?:md|json))`，与反引号 token 合并去重。
负向断言排除 `../other-skill/references/xxx` —— 带 skill 前缀的跨 skill 写法是正确的，不能误判。

### V-04 判定过粗：修好漏报后立刻变成误报洪水

只把正则修对、判定仍用 `Test-Path`，立刻报 20 条 FAIL，其中 19 条是**写法正常**：

| 写法 | 实际含义 | 处理 |
|---|---|---|
| `references/{subcommand}.md` | 占位符，按参数存在多份 | skip |
| `references/` | 引用整个目录 | 只查目录存在 |
| `references/14` | 简写，实为 `14_production_routes.md` | 前缀匹配 `14*` |
| `references/01–05` | 区间（en dash） | 展开后逐个前缀匹配 |

修法：`Resolve-RefToken` 分四档 + 三档结果：`local`（本 skill 有）/ `shared`（在 `_shared/references`）/
`cross`（在别的 skill，属路径歧义 → WARN）/ `miss`（才算 FAIL）。

## 4 P2 / P3

| # | 问题 | 处置 |
|---|---|---|
| V-05 | `_shared/references` 不存在或为空时，§1 的 foreach 一个都跑不到 → 直接 PASS。**权威副本丢了反而通过** | 加 `$sharedOk`，缺失即 FAIL |
| V-06 | 章节编号重复：两个 `14.`（session-snapshot 与行数体检） | 后者改 15 |
| V-07 | `banner-design` 引用 `` `ai-artist` references/nano-banana-pro-examples.md ``，而 **`ai-artist` skill 不存在、该文件全仓不存在** | 去掉文件指针，改为"该 skill 需另行安装" |
| V-08 | `game-forge-master` / `short-drama-forge-master` 在 SKILL.md 里写 `references/` 泛指"各下游 skill 的目录"，读者会以为是本 skill 的 | 改为"各自的 references 目录"，去掉路径形态 |

## 5 方法：改完检查器必须用独立实现复算

这轮最该留下的不是那 8 条，而是验证方式。

改正则之后，`129 → 297` 这个数字本身不能证明改对了 —— 它既可能是"修好了漏报"，也可能是"匹配得更野了"。
所以用 Python 按同一口径独立复算了一遍（反引号 token + 裸 token，去重）：

```
独立复算总 token 数: 297
  game-level-design 8
  game-integrate 3
```

两个实现得到同一个数，才算改对。同理，`audit_pipeline.py` 的 `--self-test` 是另一种形式：
**用反例证明检查还活着**。

> 检查器的正确性不能自证。要么用反例（证明它会报），要么用独立实现（证明数字对得上）。
> 只看它输出"全部通过"，等于什么都没验证。

## 6 当前状态

```
PASS  SKILL.md references 引用路径检查完成（共 297 处，跨 skill 歧义 0 处另计）
WARN  SKILL.md 超 500 行（不阻断，待清）：ai-short-drama-project-development(1055),
      ai-short-drama-topic-planner(1246)
校验结果：全部通过
```

超行数的两个短剧 skill 是既有债务（`PIPELINE_AUDIT` §5.3 已裁定转独立任务）。
