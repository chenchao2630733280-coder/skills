# AI短剧项目开发 Skill

这是一个用于“选题确认后”的短剧项目开发 Skill。

## 适用阶段

- 已确认选题
- 已有一句话高概念
- 需要搭建故事发动机
- 需要人物关系、核心规则、整剧结构
- 需要前10集或后续分集大纲
- 需要做制作、商业、合规风险判断

## 目录说明

- `SKILL.md`：完整 Skill 主文件
- `system-prompt.txt`：纯文本系统提示词
- `config/defaults.yaml`：默认参数
- `templates/project-input.md`：项目输入模板
- `templates/development-output.md`：标准输出模板
- `examples/example-request.md`：调用示例
- `references/quality-checklist.md`：质量检查表
- `references/scoring-model.md`：评分模型

## 使用方式

### ChatGPT / 自定义 GPT
将 `SKILL.md` 或 `system-prompt.txt` 内容放入系统指令，然后提交项目输入模板。

### Coze / Dify / 其他智能体
将 `system-prompt.txt` 复制到系统提示词区域，并把 `config/defaults.yaml` 中的参数作为默认变量。

### 直接对话调用
使用 `templates/project-input.md` 填写选题，然后要求系统先做故事发动机、人物关系和阶段大纲。

## 推荐流程

1. 选题复核
2. 故事发动机
3. 核心规则
4. 人物系统
5. 秘密系统
6. 六至八阶段大纲
7. 前10集分集大纲
8. 逻辑与续航检查
9. 继续后续分集
10. 正式剧本创作

## 快捷命令

- 先做故事发动机
- 做核心规则
- 做人物关系
- 做整剧大纲
- 做前10集
- 继续后10集
- 加强悬疑
- 加强爽感
- 降低成本
- 检查逻辑
- 检查续航
- 去掉套路