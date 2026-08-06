# CI 平台接入说明

本文档描述 `tool-ci-ops` 支持的三种 CI 平台的接入方式、CLI 命令映射、环境变量配置与降级规则。

## 一、平台总览

| 平台           | CLI 工具       | 触发命令                          | 状态查询                       | 报告读取                          |
| -------------- | -------------- | --------------------------------- | ------------------------------ | --------------------------------- |
| `github-actions` | `gh`           | `gh workflow run <repo> --ref <branch>` | `gh run list --repo <repo>` / `gh run view <id> --repo <repo>` | `gh run view <id> --repo <repo> --log` |
| `gitlab-ci`    | `glab`         | `glab ci trigger --repo <repo> --branch <branch>` | `glab ci list --repo <repo>` / `glab ci view <id> --repo <repo>` | `glab ci trace <id> --repo <repo>` |
| `jenkins`      | `jenkins-cli`  | `jenkins-cli build <job> -p BRANCH=<branch>` | `jenkins-cli last-build-status <job>` | `jenkins-cli console <job>` |

## 二、GitHub Actions

### 接入方式
- 安装 GitHub 官方 CLI:`gh`(https://cli.github.com/)
- 完成认证:`gh auth login`

### 环境变量
| 变量           | 说明                         | 是否必需 |
| -------------- | ---------------------------- | -------- |
| `GITHUB_TOKEN` | GitHub PAT,需 `repo` 与 `workflow` 权限 | 必需     |

### 命令示例
```bash
# 触发
gh workflow run owner/repo --ref main

# 查询最新 run
gh run list --repo owner/repo --limit 1

# 查询指定 run
gh run view 88123 --repo owner/repo

# 读取日志(测试报告)
gh run view 88123 --repo owner/repo --log
```

## 三、GitLab CI

### 接入方式
- 安装 GitLab 官方 CLI:`glab`(https://glab.readthedocs.io/)
- 完成认证:`glab auth login`

### 环境变量
| 变量           | 说明                              | 是否必需 |
| -------------- --------------------------------- | -------- |
| `GITLAB_TOKEN` | GitLab PAT,需 `api` 与 `read_api` 权限 | 必需     |

### 命令示例
```bash
# 触发
glab ci trigger --repo owner/repo --branch dev

# 查询
glab ci list --repo owner/repo
glab ci view 12345 --repo owner/repo

# 读取 trace(测试报告)
glab ci trace 12345 --repo owner/repo
```

## 四、Jenkins

### 接入方式
- 安装 Jenkins CLI:`jenkins-cli`(可从 Jenkins 界面 `/cli` 下载 jar 并封装为命令)
- 或使用 `java -jar jenkins-cli.jar`

### 环境变量
| 变量            | 说明                  | 是否必需 |
| --------------- | --------------------- | -------- |
| `JENKINS_URL`   | Jenkins 服务地址      | 必需     |
| `JENKINS_USER`  | Jenkins 用户名        | 必需     |
| `JENKINS_TOKEN` | Jenkins API Token     | 必需     |

### 命令示例
```bash
# 触发构建(参数化构建)
jenkins-cli build my-job -p BRANCH=main

# 查询最近构建状态
jenkins-cli last-build-status my-job

# 读取控制台日志(测试报告)
jenkins-cli console my-job
```

## 五、降级规则

当出现以下情况时,`ci_ops.py` 不会报错中断,而是降级为"提示用户手动执行":

1. **CLI 未安装**:目标平台 CLI 不在 PATH 中(`where` / `which` 检查失败)。
2. **环境变量缺失**:对应平台所需 token / URL 未设置。
3. **CLI 执行报错**(FileNotFoundError):降级打印待执行命令。

降级时:
- 在控制台打印 `[ci-ops] 平台 CLI 或环境变量不可用` 提示。
- 打印待手动执行的完整命令。
- 打印环境变量配置参考。
- 在 `ci-ops-report.json` 中设置 `status=degraded`、`error` 填写降级原因,退出码为 0(不阻断上层编排)。

## 六、平台选择建议

- 已在 GitHub 托管代码 → 优先 `github-actions`。
- 已在 GitLab 托管代码 → 优先 `gitlab-ci`。
- 自建 Jenkins / 需要复杂流水线编排 → 使用 `jenkins`。
- 不确定时:先 `status` 查询,若 `degraded` 则按提示安装 CLI 或配置环境变量。
