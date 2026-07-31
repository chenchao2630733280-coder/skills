# rd-init

description: 根据初步需求从 GitLab 拉取最新 AI Product R&D 模板，并初始化一个新的产研项目；仅用于新项目初始化，不用于生成 PRD、页面明细、API、数据库、前端代码或测试。

## 使用

```text
请调用 rd-init Skill 初始化项目。
初步需求如下：需求内容
```

或手动执行：

```bash
python .agents/skills/rd-init/scripts/rd-init.py \
  --target-dir . \
  --brief "项目名称：xxx；核心功能：xxx"
```

默认模板仓库：

```text
https://gitlab.chinacici.com/chenchao/ai-product-rd.git
```
