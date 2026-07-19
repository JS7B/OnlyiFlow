# OnlyiFlow

简体中文 | [English](README.md)

OnlyiFlow 是面向 Codex、Claude Code 和 ZCode 的项目级开发工作流插件。它由一个显式调用的
Skill、一个确定性的本地 stdio MCP 服务器，以及基于 SQLite 的工作流状态存储组成。

宿主编码代理负责规划、实现、调试和测试；OnlyiFlow 负责协调流程状态、确定性质量 Gate 和落地
证据。

## 核心能力

- 经所有者确认后初始化项目级工作流状态。
- 经单独的所有者确认后配置确定性项目 Gate。
- 根据变更风险启动 `quick`、`standard` 或 `deep` 流程。
- 记录精简规格和明确的实现认领状态。
- 执行配置的质量检查并保存结构化 Gate 证据。
- 在全部必需检查通过后生成面向所有者的落地请求。
- 在 Codex、Claude Code 和 ZCode 宿主包中提供一致的工作流语义。

## 发布状态

当前 GitHub 正式版本为 `v0.3.0`。该版本包含 Claude Code `user` 范围持久安装、经所有者确认的
Gate 配置、项目就绪状态，以及针对 Gate 仍为空的旧版活动流程的受限升级路径。

0.3.0 正式版本已通过本地验证、Claude 安装与发布冒烟验收，以及由所有者协助完成的 ZCode
生命周期验证。保留的本地 Codex 安装当前解析为 0.3.0 并保持启用；所有者已延期 Codex 0.3.0
在线模型验证。

既有 Claude 与 Codex 发布基线已通过完整的激活、效率/Gate 与发布冒烟测试契约。由所有者协助
完成的 ZCode 0.3.0 生命周期验证已覆盖普通请求隔离、所有者确认初始化、快速流程执行、Gate
失败与通过、落地和卸载。

完整验收记录见
[v0.3.0 Gate 配置证据](docs/evaluations/2026-07-19-v0.3.0-gate-configuration.md)、
[v0.2.0 Claude 安装证据](docs/evaluations/2026-07-18-v0.2.0-claude-user-install.md)
和 [v0.1.0 发布就绪审计](docs/evaluations/2026-07-17-task7-release-readiness.md)。

## 运行要求

- Python 3.11 或更高版本
- `requirements.txt` 中声明的软件包
- Codex、Claude Code 或 ZCode
- 从源码构建宿主包时所需的本地仓库检出

请选择任意 Python 环境，并确保宿主进程能够找到该环境的 `python` 命令。将运行依赖安装到
所选环境：

```powershell
python --version
python -m pip install -r requirements.txt
```

## 构建宿主包

在仓库根目录生成相互隔离的宿主包：

```powershell
python -B scripts\build_loader_candidates.py
```

该命令生成：

```text
build/loader-candidates/codex-marketplace/
build/loader-candidates/claude-marketplace/
build/loader-candidates/zcode/
```

每次全新构建应使用空的输出目录。各宿主的生成目录均为自包含结构。

## 安装与启动

### Codex

将 `<codex>` 替换为可用的 Codex CLI 命令，将 `<仓库根目录>` 替换为本仓库的绝对路径：

```powershell
<codex> plugin marketplace add "<仓库根目录>\build\loader-candidates\codex-marketplace" --json
<codex> plugin add onlyiflow@onlyiflow-dev --json
```

新建 Codex 任务，然后调用：

```text
$onlyiflow:onlyiflow
```

### Claude Code

将 `build/loader-candidates/claude-marketplace/` 复制或解压到稳定的本地目录。将
`<保留的-Claude-Marketplace目录>` 替换为该目录：

```powershell
python -m pip install -r "<保留的-Claude-Marketplace目录>\plugins\onlyiflow\requirements.txt"
claude plugin marketplace add "<保留的-Claude-Marketplace目录>" --scope user
claude plugin install onlyiflow@onlyiflow-local --scope user
```

在目标项目中新建 Claude Code 会话，然后调用：

```text
/onlyiflow:onlyiflow
```

### ZCode

1. 打开“插件管理”，选择“添加插件市场”。
2. 选择 `build/loader-candidates/zcode/`。
3. 从本地 Marketplace 安装 `onlyiflow`。
4. 在目标项目中新建任务，并显式调用 OnlyiFlow Skill。

完整的安装、更新、卸载和验证流程见[发布指南](docs/release-guide.md)。

## 执行工作流

调用 OnlyiFlow 时同时说明预期动作，例如：

```text
$onlyiflow:onlyiflow 为缓存键问题启动 quick 流程
/onlyiflow:onlyiflow 为身份认证变更启动 standard 流程
```

项目首次使用流程：

1. OnlyiFlow 报告项目状态。
2. 宿主展示项目级状态条目并请求所有者确认。
3. 确认后，OnlyiFlow 初始化项目。
4. 宿主提出 Gate 检查方案，并等待单独的所有者确认。
5. OnlyiFlow 保存确认后的 Gate 配置，再启动指定流程。
6. 宿主代理实现并测试变更，OnlyiFlow 同步记录流程状态。
7. 明确提出 `check` 后执行配置的 Gate。
8. Gate 通过后，明确提出 `land` 以记录落地交接。

`quick` 流程直接进入实现阶段；`standard` 流程使用一份精简规格；`deep` 流程在详细规划前增加
一次所有者确认。

如果升级后的项目已经存在活动流程，但 Gate 仍为空，OnlyiFlow 会通过相同的方案展示与单独
所有者确认边界完成首次 Gate 配置，然后恢复该流程。活动流程的已配置 Gate 始终保持锁定。

## 状态与工具模型

已纳管项目的状态保存在：

```text
<project>/.onlyiflow/
  onlyiflow.db
  config.toml
  specs/
```

Skill 协调以下八个确定性 MCP 工具：

```text
project_status
project_init
gate_configure
flow_start
spec_submit
flow_claim
gate_run
landing_request
```

每个工具都会解析明确的项目根目录，并返回稳定的结构化结果以及至多一个下一步动作。

## 仓库分层

产品契约：

- `docs/product-spec.md`：行为、流程语义与产品范围
- `docs/engineering-spec.md`：运行时、持久化、传输、打包与测试契约
- `docs/release-guide.md`：安装、生命周期、验证与发布流程

实现：

- `src/onlyiflow/`：领域、存储、Gate 与工作流运行时
- `server/stdio.py`：插件本地 stdio 服务器引导程序
- `packaging/`：宿主清单与 Skill 资源
- `scripts/build_loader_candidates.py`：宿主包构建器

验证与证据：

- `tests/`：单元、契约、打包和 runner 测试
- `scripts/run_skill_evaluations.py`、`scripts/run_efficiency_measurements.py` 和
  `scripts/run_release_smoke.py`：发布证据 runner
- `docs/research/`、`docs/plans/` 和 `docs/evaluations/`：研究、执行计划与已接受证据

## 产品核心规则

> 宿主代理负责实现。OnlyiFlow 负责明确的工作流状态和确定性的落地证据。
