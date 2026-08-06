# prompt 版本规则(权威)

本文件定义 prompt 模板的版本号规则与变体标签约定,是 `register_prompt.py` 校验版本号时的唯一事实来源。
`prompt-registry/SKILL.md` §四 引用本文件。

## 一、语义化版本(SemVer)

prompt 版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/) 简化格式:

```
MAJOR.MINOR.PATCH[-PRERELEASE]
```

| 段 | 含义(prompt 语境) | 示例 |
|----|-------------------|------|
| `MAJOR` | prompt 结构性变更(如占位符体系改变、系统提示重组) | `1.0.0` → `2.0.0` |
| `MINOR` | 新增字段/约束(向后兼容,旧调用方仍可工作) | `1.0.0` → `1.1.0` |
| `PATCH` | 文案修正、措辞优化(不影响结构) | `1.0.0` → `1.0.1` |
| `PRERELEASE` | 预发布标签(实验中,未定稿) | `1.1.0-beta` / `2.0.0-rc.1` |

### 1.1 合法格式

- `1.0.0` — 正式版
- `1.1.0-beta` — 预发布版
- `2.0.0-rc.1` — 含序号的预发布版

### 1.2 非法格式(会被 register_prompt.py 拒绝)

- `v1.0.0` — 不允许 `v` 前缀
- `1.0` — 必须三段
- `1.0.0.beta` — 预发布须用 `-` 分隔

## 二、版本排序

`get_prompt.py latest` 按 semver 规则排序:

1. `MAJOR.MINOR.PATCH` 数值比较
2. 同主次修订号下,正式版 > 预发布版
3. 预发布版之间按字符串比较

示例(升序):`1.0.0-alpha` < `1.0.0-beta` < `1.0.0` < `1.1.0`

## 三、变体标签(tag)

同一 skill 可有多个 prompt 变体,用 `tag` 区分:

| tag | 含义 | 适用场景 |
|-----|------|---------|
| `stable` | 稳定版(默认) | 日常使用 |
| `detailed` | 详细版(含更多约束说明) | 需要严格约束输出的场景 |
| `concise` | 简洁版(省略冗余说明) | token 受限场景 |
| `experimental` | 实验版(A/B 测试) | 对比测试新 prompt 效果 |

约束:

- 每个 skill 的每个版本必须有一个 tag(默认 `stable`)
- 同 skill 可有多个 `stable` 版本(不同 semver)
- tag 不参与版本排序,仅用于 `by-tag` 检索

## 四、版本更新流程

1. 修改 prompt 文本
2. 根据变更范围决定新版本号:
   - 措辞微调 → `PATCH+1`
   - 新增字段/约束 → `MINOR+1`
   - 结构重组 → `MAJOR+1`
3. 调用 `register_prompt.py update --skill X --version <新版本> --file prompt.md`
4. 旧版本自动保留(可回退)

## 五、版本回退

回退 = 检索旧版本号,重新注册为新版本(需用户确认):

```
# 1. 查看历史版本
python get_prompt.py by-skill --skill game-blueprint

# 2. 确认要回退到的版本(如 1.0.0)

# 3. 以 1.0.0 的内容注册新版本(如 1.3.0)
python register_prompt.py update --skill game-blueprint --version 1.3.0 \
  --file .trae-cn/prompts/prompts/game-blueprint/1.0.0.md
```

回退需用户确认,脚本不自动执行。

## 六、与 SKILL.md 的关系

- 本文件是版本号规则的权威来源,`register_prompt.py` / `get_prompt.py` 内嵌该规则
- SKILL.md 不重复版本规则细节,仅引用本文件
- `skill-auditor` 审查 prompt 版本合法性时对照本文件
