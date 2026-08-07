# rd-init

工作台加载器。扫描 skills 目录全部 skill，生成工作台索引和完整性报告。

## 使用

```bash
python .agents/skills/rd-init/scripts/rd-init.py --skills-dir .agents/skills
```

## 产出

- `.workbench-index.json` — 全部 skill 的结构化清单（名称/描述/分类/frontmatter/runtime.yaml）
- 对话输出 — 工作台概览：skill 总数、分类统计、完整性警告

## 功能

- 扫描全部 skill 目录，解析 frontmatter 和 runtime.yaml
- 按产研业务层/游戏流水线/AI 短剧/Agent 体系层分类
- 校验完整性：frontmatter 规范、references 路径存在性
- Agent 体系层按 12 维度细分统计
