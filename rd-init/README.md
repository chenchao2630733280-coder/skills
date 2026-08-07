# rd-init

产研项目脚手架初始化。根据初步需求创建标准目录结构、project-brief.json 和 project.yaml，为 product-pipeline-master 流水线提供起始输入。

## 使用

```text
请调用 rd-init 初始化项目。
初步需求如下：需求内容
```

或手动执行：

```bash
python .agents/skills/rd-init/scripts/rd-init.py \
  --target-dir . \
  --brief "项目名称：xxx；核心功能：xxx"
```

## 产出

- `docs/project-brief.json` — 结构化需求简报，供 brainstorm-product-feature 消费
- `project.yaml` — 项目配置 + 流水线上下文
- `docs/FEATURE_BRAINSTORM.md` — 需求原文
- 标准目录结构：`output/spec/` `output/prototype/` `output/site/{pc,mobile,assets}/` `output/build/`

## 下一步

初始化完成后，调用 `product-pipeline-master` 启动产研流水线，从 `brainstorm-product-feature`（需求澄清）开始。
