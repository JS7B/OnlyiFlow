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
- 以版本化 Wave 和有界工作包引导经明确确认的 deep 目标。
- 执行配置的质量检查并保存结构化 Gate 证据。
- 在全部必需检查通过后生成面向所有者的落地请求。
- 以可选 MCP Resource 提供精简工作流契约，不增加默认上下文。
- 在 Codex、Claude Code 和 ZCode 宿主包中提供一致的工作流语义。

## 发布状态

当前 GitHub 正式版本为 `v0.4.0`。该版本新增一个受限、按需读取的 MCP 工作流契约 Resource，
以及面向明确确认的 deep 目标的可选 Wave 模式。Wave 模式新增三个用于计划修订和工作包证据的
确定性工具，同时保持既有 direct quick/standard 路径不变，且不新增 MCP Prompt 模板。

0.3.0 正式版本建立了 Claude Code `user` 范围持久安装、经所有者确认的 Gate 配置、项目就绪
状态，以及针对 Gate 仍为空的旧版活动流程的受限升级路径。该版本的本地、Claude 与所有者协助
ZCode 验收继续作为 0.4.0 的 direct 流程基线。

既有 Claude 与 Codex 发布基线已通过完整的激活、效率/Gate 与发布冒烟测试契约。由所有者协助
完成的 ZCode 0.3.0 生命周期验证已覆盖普通请求隔离、所有者确认初始化、快速流程执行、Gate
失败与通过、落地和卸载。`v0.4.0` 也已通过 ZCode 3.3.6 的计划展示、确认与认领、恢复、
卸载和清理场景；Claude 与 Codex 的 Wave 在线验收仍待执行。

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

## 更新现有安装

下载或检出目标新版本后，将候选包构建到一个全新的空目录，并在替换任何保留的 Marketplace
目录前完成验证：

```powershell
python -B scripts\build_loader_candidates.py --output-root "<全新输出目录>"
```

关闭准备更新的宿主。只使用 `<全新输出目录>` 中对应宿主的已验证目录替换其保留的 Marketplace，
然后执行该宿主的原生更新流程。

### 更新 Codex

保留现有 `onlyiflow-dev` Marketplace 注册，从新构建的 Marketplace 刷新已安装缓存：

```powershell
<codex> plugin add onlyiflow@onlyiflow-dev --json
```

从 `0.4.0` 更新到后续版本时，版本变化由新构建的清单体现。命令成功后新建 Codex 任务。

### 更新 Claude Code

保留 `onlyiflow-local` 目录及其 user 范围 Marketplace 注册。用新构建替换该目录后执行：

```powershell
claude plugin marketplace update onlyiflow-local
claude plugin update onlyiflow@onlyiflow-local --scope user
```

两条命令均成功后，新建 Claude Code 会话。

### 更新 ZCode

继续以 ZCode Desktop 作为安装入口：

1. 在“已安装”中卸载 OnlyiFlow 插件。
2. 使用新的 `zcode/` 构建替换或刷新保留的本地 Marketplace。
3. 在“发现”中重新安装 OnlyiFlow。
4. 新建任务并确认 Skill 与 MCP 服务器可见。

更新宿主包不会重新创建项目级 `.onlyiflow/` 状态。如果新版 `requirements.txt` 的依赖列表有
变化，请同步所选 Python 环境；其他插件和 Marketplace 保持不变。

以上命令覆盖三个宿主支持的安装、更新与卸载流程。

## 执行工作流

调用 OnlyiFlow 时同时说明预期动作，例如：

```text
$onlyiflow:onlyiflow 为缓存键问题启动 quick 流程
/onlyiflow:onlyiflow 为身份认证变更启动 standard 流程
$onlyiflow:onlyiflow 为这个迁移目标启动 deep Wave 流程
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

对于明确要求 Wave 模式的 deep 目标，宿主先展示一份完整工作包计划并等待单独确认。随后
OnlyiFlow 记录版本化计划，并仅暴露当前 Wave 所需的目标包。是否以及如何使用宿主原生 Agent、
worktree、评审和 Git 由宿主决定；相应宿主动作完成后，OnlyiFlow 只记录精简的工作包交接与集成
证据。依赖包只有在其前置包记录为 `integrated` 后才会解锁；所有工作包完成集成，或有条件的包被
明确记录为 `deferred` 后，才能执行最终项目 Gate。实质性重规划需要再次提交完整计划并由所有者
确认。

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

当前开发版 Skill 协调以下十一个确定性 MCP 工具：

```text
project_status
project_init
gate_configure
flow_start
spec_submit
wave_plan_set
flow_claim
work_package_status
work_package_record
gate_run
landing_request
```

每个工具都会解析明确的项目根目录，并返回稳定的结构化结果以及至多一个下一步动作。

## 仓库结构

- `src/onlyiflow/`：领域、存储、Gate 与工作流运行时
- `server/stdio.py`：插件本地 stdio 服务器引导程序
- `packaging/`：宿主清单与 Skill 资源
- `scripts/build_loader_candidates.py`：宿主包构建器
- `requirements.txt`：运行依赖契约

## 产品核心规则

> 宿主代理负责实现。OnlyiFlow 负责明确的工作流状态和确定性的落地证据。
