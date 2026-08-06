# 常见降级模式清单

本文件列举 runtime.yaml `degrade[].action` 字段的常见取值,供 skill 作者声明降级策略时参考。
`skill-runtime/SKILL.md` §二 引用本文件;`skill-auditor` 第 6 维度审查时校验 `action` 是否在已知模式内(超出标 WARNING,不 FAIL)。

## 一、模式清单

### 1. 占位图(纯色+文字标识)

- **触发条件**:AI 生图失败(API 不可用 / 配额耗尽 / 内容审核拒绝)
- **动作**:生成纯色 PNG,叠加文字标识资源名 + 失败原因
- **适用 skill**:`game-asset-forge`(role/ui/bg 类资源)
- **target 示例**:`assets/role/*/*.png`
- **运行时行为**:`workflow-runtime` 检测到生图失败后,调用本降级动作生成占位图,继续后续流程,不阻塞

### 2. 静音占位

- **触发条件**:音频生成失败(TTS 不可用 / 音频文件损坏)
- **动作**:复制预设的静音 WAV(1 秒,16kHz,单声道)到目标路径
- **适用 skill**:`game-asset-forge`(audio 类资源)
- **target 示例**:`assets/audio/*.wav`
- **运行时行为**:复制静音文件后继续,在产物清单标注 `actualFormat=placeholder`

### 3. 散图降级

- **触发条件**:切图/图集打包失败(TexturePacker CLI 不可用 / 图集格式异常)
- **动作**:放弃图集,改用散图直接引用(每个 sprite 独立 PNG)
- **适用 skill**:`game-asset-forge`(图集打包阶段)、`game-code-forge`(引擎加载层)
- **target 示例**:`assets/atlases/*.png`(降级后不生成,改读 `assets/role/*/*.png`)
- **运行时行为**:回写 ASSET_MANIFEST.json 标注 `atlas=disabled`,引擎加载层切换为散图加载

### 4. strict:false 降级

- **触发条件**:typecheck / lint / 严格校验失败(类型错误 / 未使用变量)
- **动作**:把 tsconfig.json 的 `strict` 临时设为 `false`,允许通过,在产物清单标注 `strict=off`
- **适用 skill**:`game-code-forge`、`implement-frontend`、`test-and-harden-system`
- **target 示例**:`tsconfig.json`
- **运行时行为**:仅作为最后兜底,优先修复类型错误;降级后在 ASSET_ISSUES.md / build-report.json 标 WARNING

### 5. 跳过阶段

- **触发条件**:阶段裁剪(用户明确不需要某阶段 / 上游产物缺失且无法降级)
- **动作**:跳过整个阶段,在执行轨迹标注 `skipped=true` + 跳过原因
- **适用 skill**:编排总纲(`product-pipeline-master` / `game-forge-master`)的阶段裁剪逻辑
- **target 示例**:整个 skill 阶段(无具体路径)
- **运行时行为**:`workflow-runtime` 把对应 step 标 `skipped`,不调用该 skill,继续下一阶段

### 6. 输出部署指令

- **触发条件**:平台 CLI 不可用(gh / glab / jenkins-cli / vercel / cloudbase 未安装)
- **动作**:不执行真实部署,把部署命令打印到 stdout + 写入 `deploy-instructions.md`,提示用户手动执行
- **适用 skill**:`tool-deploy-ops`、`tool-ci-ops`
- **target 示例**:`docs/deploy-instructions.md`
- **运行时行为**:不阻塞流水线,把"手动操作清单"作为产物交回调用方

### 7. 提示手动操作

- **触发条件**:CI/监控平台不可用(网络不通 / 鉴权失败 / 平台下线)
- **动作**:在报告中回填"请手动查询 / 请手动触发"提示,附查询命令模板
- **适用 skill**:`tool-monitor-ops`、`tool-ci-ops`、`tool-db-ops`
- **target 示例**:`monitor-ops-report.json` 的 `manual_hint` 字段
- **运行时行为**:`error` 字段回填提示,exit 0(不阻塞),由人工介入

## 二、声明示例

在 runtime.yaml 中声明降级策略时,`action` 字段建议直接引用上述模式名(可加括号补充细节):

```yaml
degrade:
  - trigger: 生图失败
    action: 占位图(纯色+文字标识)
    target: assets/role/*/*.png
  - trigger: 音频生成失败
    action: 静音占位
    target: assets/audio/*.wav
  - trigger: 图集打包失败
    action: 散图降级
    target: assets/atlases/*.png
```

## 三、未知模式处理

- `action` 取值不在上述 7 类已知模式内时,`skill-auditor` 第 6 维度审查会标 **WARNING**(非 CRITICAL),提示 skill 作者确认是否为新模式
- 新模式可由 skill 作者自定义,但建议在 SKILL.md 中描述清楚触发条件与动作语义
- `validate_runtime.py` 不校验 `action` 取值是否在已知模式内(仅校验非空字符串),由 `skill-auditor` 做语义级 WARNING
