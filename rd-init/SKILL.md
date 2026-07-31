# rd-init

description: 根据初步需求从 GitLab 拉取最新 AI Product R&D 模板，并初始化一个新的产研项目；仅用于新项目初始化，不用于生成 PRD、页面明细、API、数据库、前端代码或测试。

## 触发方式

当用户输入类似下面内容时使用：

```text
请调用 rd-init Skill 初始化项目。
初步需求如下：需求内容
```

## 执行方式

1. 提取“初步需求如下：”后面的全部内容。
2. 写入当前目录 `.rd-init-brief.md`。
3. 执行：

```bash
python .agents/skills/rd-init/scripts/rd-init.py \
  --target-dir . \
  --brief-file .rd-init-brief.md
```

如果 Skill 位于全局目录，使用实际路径调用 `scripts/rd-init.py`。

## 边界

初始化阶段只拉取模板、生成或更新 `project.yaml`、`workflow_state.yaml`、`asset_map.json` 和项目说明；不生成 PRD、页面清单、页面明细、API、数据库、前端代码、测试或交付文档。
