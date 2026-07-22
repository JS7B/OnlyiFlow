# OnlyiFlow

简体中文 | [English](README.md)

OnlyiFlow 是面向 Codex、Claude Code 和 ZCode 的项目级开发工作流插件。它由一个显式调用的
Skill、一个确定性的本地 stdio MCP 服务器，以及基于 SQLite 的工作流状态存储组成。

宿主编码代理负责规划、实现、调试和测试；OnlyiFlow 负责协调明确的流程状态、确定性质量 Gate、
有界 Wave 计划和落地证据。

## 核心能力

- 经所有者确认后初始化项目级工作流状态。
- 经单独的所有者确认后配置确定性项目 Gate。
- 根据变更风险启动 `quick`、`standard` 或 `deep` 流程。
- 记录精简规格和明确的实现认领状态。
- 以版本化 Wave 和有界工作包引导经确认的 standard 或 deep 目标。
- 执行配置的质量检查并保存结构化 Gate 证据。
- 在全部必需检查通过后生成面向所有者的落地请求。
- 在不删除保留历史的前提下关闭所有者已处理完成的流程。
- 以可选 MCP Resource 提供精简工作流契约。
- 在 Codex、Claude Code 和 ZCode 宿主包中提供一致的工作流语义。

## 版本沿革

- `v0.1.0` — 建立显式调用的 Skill、项目级 SQLite 状态、确定性 MCP 工作流、
  `quick`/`standard`/`deep` 风险等级、质量 Gate 和落地交接。
- `v0.2.0` — 增加通过保留的本地 Marketplace 和用户自行选择的 Python 环境完成的 Claude Code
  `user` 范围持久安装。
- `v0.3.0` — 增加经所有者确认的 Gate 配置、项目就绪状态，以及对 Gate 仍为空的旧版活动流程的
  受限迁移路径。
- `v0.4.0` — 增加可选的 deep-only Wave 工作流、版本化工作包计划、三个 Wave 工具，以及受限的
  `onlyiflow://contract/concise` MCP Resource。
- `v0.5.0` — 增加适用于 `standard` 工作的可选 Wave 模式，以及经所有者确认的 `flow_close`
  终态转换；关闭流程会释放活动槽位并保留工作流历史。该版本为当前正式版本。

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
4. 在目标项目中新建任务，并在输入区选择 OnlyiFlow Skill。

## 卸载

修改插件状态前应关闭活动宿主会话。卸载宿主插件不会删除项目级 `.onlyiflow/` 工作流状态。

### Codex

```powershell
<codex> plugin remove onlyiflow@onlyiflow-dev --json
<codex> plugin marketplace remove onlyiflow-dev
```

卸载后新建 Codex 任务。

### Claude Code

```powershell
claude plugin uninstall onlyiflow@onlyiflow-local --scope user --yes
claude plugin marketplace remove onlyiflow-local --scope user
```

两条命令均成功后，可以删除保留的本地 Marketplace 目录。新建 Claude Code 会话以刷新可用的
Skill 和 MCP 清单。

### ZCode

1. 打开“插件管理”，切换到“已安装”。
2. 卸载 `onlyiflow`。
3. 确认其 Skill 与 MCP 服务器不再加载。
4. 仅在不再需要时，从“发现”中移除本地 Marketplace 源。

## 执行工作流

只有明确调用 OnlyiFlow 才会激活工作流。将宿主对应的调用方式与一条具体指令组合使用。

| 宿主        | 调用方式                                 |
| ----------- | ---------------------------------------- |
| Codex       | `$onlyiflow:onlyiflow <指令>`          |
| Claude Code | `/onlyiflow:onlyiflow <指令>`          |
| ZCode       | 选择 OnlyiFlow Skill，然后输入`<指令>` |

### 常用指令

| 目的             | 指令示例                                                   |
| ---------------- | ---------------------------------------------------------- |
| 初始化           | `为当前项目初始化 OnlyiFlow，并在每个所有者确认边界停止` |
| 快速变更         | `为缓存键问题启动 quick 流程`                            |
| 标准变更         | `为身份认证变更启动 standard 流程`                       |
| 标准 Wave        | `为身份认证变更启动 standard Wave 流程`                  |
| 深度 direct 变更 | `为存储迁移启动 deep direct 流程`                        |
| 深度 Wave 变更   | `为存储迁移启动 deep Wave 流程`                          |
| 恢复             | `恢复当前活动的 OnlyiFlow 流程，并报告一个下一步动作`    |
| 检查             | `使用已配置的 Gate 检查当前活动流程`                     |
| 落地             | `落地已通过 Gate 的流程，并记录所有者交接`               |
| 关闭             | `关闭已经在外部落地的流程并保留历史`                     |
| 放弃             | `因为目标已被取代而放弃当前活动流程`                     |

例如，一条完整的 Codex Wave 调用指令是：

```text
$onlyiflow:onlyiflow 为这个迁移目标启动 deep Wave 流程
```

### 项目首次使用

首次显式请求会建立两个所有者确认边界：

```text
project_status
  -> 所有者确认初始化项目
project_init
  -> 宿主展示完整 Gate 方案
  -> 所有者确认 Gate 配置
gate_configure
  -> 项目就绪
```

`project_status` 是只读操作。`project_init` 只创建：

```text
<project>/.onlyiflow/
  onlyiflow.db
  config.toml
  specs/
```

宿主必须在单独确认 `gate_configure` 前展示每个 Gate 检查、命令、必需标记和超时设置。

### Direct 流程

| 风险         | 适用场景                       | 进入实现阶段的调用路径                                        |
| ------------ | ------------------------------ | ------------------------------------------------------------- |
| `quick`    | 小型且边界明确的变更           | `project_status -> flow_start`                              |
| `standard` | 需要一份精简规格的变更         | `project_status -> flow_start -> spec_submit -> flow_claim` |
| `deep`     | 需要所有者确认规划的高风险工作 | `project_status -> flow_start -> spec_submit -> flow_claim` |

已配置项目中的 `quick` 流程会原子进入 `implementing`。`standard` 和 direct `deep` 流程从
`draft` 开始，保存一份精简规格，再通过 `flow_claim` 进入实现阶段。deep 规划在持久化前增加
所有者确认边界。

### Wave 流程

Wave 模式是适用于 `standard` 或 `deep` 目标的可选能力，`quick` Wave 无效。当任务适合使用
版本化依赖计划和有界工作包时，应在指令中明确要求 Wave。选择 standard Wave 不会增加 deep
风险确认流程。

启动回合与确认回合相互独立：

```text
启动回合：
project_status -> flow_start(mode="wave")
  -> 宿主展示完整 Wave 与工作包计划
  -> 停止并等待所有者确认

确认回合：
project_status -> spec_submit -> wave_plan_set -> flow_claim
  -> 状态：implementing
```

完整计划包括目标、不变量、非目标、工作包依赖、Wave 编号、允许与禁止路径、交付物、验收条件、
授权要求和冲突分析。确认计划不代表授权安装依赖、外部写入、Git 操作或发布；这些操作仍需所有者
另行授权。

执行已确认计划时，是否以及如何使用宿主原生 Agent、worktree、评审和 Git 由宿主决定。

实现阶段按以下方式推进：

1. `project_status` 报告当前 Wave 和一个下一步动作。
2. `work_package_status` 返回一个目标包的有界契约。
3. 宿主按需完成实现、评审、测试、worktree 或 Agent 操作。
4. `work_package_record` 记录已经完成的宿主动作。
5. 前置包记录为 `integrated` 后，后续 Wave 的依赖包才会解锁。
6. 实质性重规划必须再次提交完整 `wave_plan_set` 修订并由所有者确认。
7. 所有包均为 `integrated`，或有条件的包被有效记录为 `deferred` 后，才能执行最终 Gate。

`work_package_record` 支持以下封闭动作：

```text
start
submit
request_changes
accept
integrate
interrupt
block
resume
defer
```

这些动作只记录宿主已经完成的工作，不会执行 Agent、worktree、评审、命令或 Git 操作。

### 检查与落地

明确提出检查指令会调用 `gate_run`。必需检查失败时，流程保持 `implementing`；Gate 通过后，
流程进入 `gate_passed`。

Gate 通过后，明确提出落地指令会调用 `landing_request`，并记录 `waiting_owner`。提交、合并、推送
和发布仍由所有者通过宿主控制。

外部落地完成后，`flow_close(action="landed", reason_code="external_landing_completed")` 会记录
单独确认的终态决定。任意非终态流程也可以使用支持的原因码关闭为 `abandoned`。关闭操作会释放
活动流程槽位，同时保留 Flow、规格、Gate、Wave、工作包和事件历史；它不会执行 Git 或发布操作。

## MCP 表面

OnlyiFlow v0.5.0 暴露十二个确定性 MCP 工具：

| 工具                    | 职责                                                         |
| ----------------------- | ------------------------------------------------------------ |
| `project_status`      | 读取项目就绪状态、活动流程、当前 Gate 状态和一个下一步动作。 |
| `project_init`        | 经所有者确认后创建项目级工作流状态。                         |
| `gate_configure`      | 原子保存完整且经所有者确认的 Gate 配置。                     |
| `flow_start`          | 启动`quick`、`standard` 或 `deep` direct/Wave 流程。   |
| `spec_submit`         | 为 standard 或 deep 流程保存一份精简规格。                   |
| `wave_plan_set`       | 保存完整的初始 Wave 计划或经确认的计划修订。                 |
| `flow_claim`          | 将 ready 状态的 standard 或 deep 流程推进到实现阶段。        |
| `work_package_status` | 读取一个有界工作包契约及其当前状态。                         |
| `work_package_record` | 记录一个已完成的宿主工作包状态转换。                         |
| `gate_run`            | 运行配置的检查并保存精简 Gate 证据。                         |
| `landing_request`     | Gate 通过后记录由所有者控制的落地交接。                      |
| `flow_close`          | 记录经确认的终态决定、释放活动槽位并保留历史。               |

同时暴露一个可选的静态 Resource：

```text
onlyiflow://contract/concise
```

该 Resource 只概述工作流契约，不携带项目状态。动态状态始终来自 `project_status`。OnlyiFlow
不暴露 MCP Prompt 模板。

## 仓库结构

- `src/onlyiflow/`：领域、存储、Gate、Wave 与工作流运行时
- `server/stdio.py`：插件本地 stdio 服务器引导程序
- `packaging/`：宿主清单与 Skill 资源
- `scripts/build_loader_candidates.py`：宿主包构建器
- `requirements.txt`：运行依赖契约

## 产品核心规则

> 宿主代理负责实现。OnlyiFlow 负责明确的工作流状态和确定性的落地证据。
