# OnlyiFlow 下一阶段优化方向

日期：2026-07-18

状态：已完成；Gate 配置增量作为 0.3.0 正式版本发布

## 决策摘要

0.3.0 产品增量增加**经所有者确认的 Gate 配置与就绪状态展示**。

该方向具备最高的即时用户价值：0.2.0 基线中新初始化的项目只包含 `checks = []`，而原有七个
MCP 工具中没有配置或更新检查项的入口。因此，除非在 OnlyiFlow 工作流之外编辑项目状态，否则首次
明确提出 `check` 时会返回 `gate_checks_missing`。

本阶段增加一个使用封闭 Schema 的 `gate_configure` 工具，并通过 `project_status` 返回精简的
Gate 就绪状态，同时保持现有 quick 流程在稳定使用阶段只需两次调用。该增量不改变宿主安装方式，
也不需要新增依赖。

Gate 配置之后的第二优先级应是所有者控制的流程完成或放弃机制。目前 `waiting_owner` 仍占用
唯一活动流程槽，因此一次落地交接完成后，项目无法启动下一个顺序流程。

## 调研范围

本决策依据当前仓库契约与已接受的实测证据：

- `docs/product-spec.md`；
- `docs/engineering-spec.md`；
- `docs/release-guide.md`；
- `docs/evaluations/2026-07-16-task4-skill-evaluation.md`；
- `docs/evaluations/2026-07-17-task5-efficiency-and-gate-value.md`；
- `docs/evaluations/2026-07-17-task6-three-host-release-smoke.md`；
- `docs/evaluations/2026-07-17-task7-release-readiness.md`；
- `docs/evaluations/2026-07-18-v0.2.0-claude-user-install.md`；
- 当前运行时、存储约束、MCP Schema 与契约测试。

本次决策无需额外开展宿主外部调研。最高优先级缺口位于共享运行时和项目生命周期中，可以脱离
Codex、Claude Code 或 ZCode 独立复现。

## 已验证基线

以下能力已经获得验收证据支持：

- 仅在明确调用时激活 Skill，并隔离普通请求；
- 确定性的项目初始化和单活动流程约束；
- `quick`、`standard` 与 `deep` 三种不同的流程开销；
- 能够通过真实回归验证先失败、修复后通过的精简 Gate 证据；
- 由所有者控制的落地交接；
- 可复现且相互隔离的 Codex、Claude Code 和 ZCode 宿主包；
- Codex 与 Claude 模型验收，以及由所有者协助完成的 ZCode 发布冒烟测试；
- 通过持续保留的本地 Marketplace 实现 Claude Code `user` 范围持久安装。

已接受的测量表明，继续扩展宿主加载能力不是当前首要瓶颈。两个自动化宿主均已通过完整的激活
和 Gate 契约；v0.2.0 候选版本还单独验证了 Claude 的安装、更新、跨项目使用和清理。

## 已确认的产品缺口

### 1. Gate 配置尚未纳入受控工作流

`ProjectStore.initialize()` 当前写入以下默认配置：

```toml
version = 1
checks = []
```

`gate_run` 会正确地以 `gate_checks_missing` 拒绝该状态。Skill 同时要求所有
`.onlyiflow` 状态变更都通过 MCP 完成，但现有 MCP 工具清单中没有配置操作。这造成了从成功
初始化到首次有效 Gate 之间的断点。

### 2. 落地交接会阻塞下一个顺序流程

数据库唯一索引和 `active_flow()` 查询都把 `waiting_owner` 视为活动状态。
`landing_request` 会将流程转换为 `waiting_owner`，当前也没有任何操作可以继续转换为
`landed` 或 `abandoned`。因此，项目可以完成一次落地交接，但无法启动下一个流程。

### 3. 历史证据缺少只读产品入口

SQLite 已记录流程、Gate、规格和领域事件，但 `project_status` 只返回一个活动流程和最近一次
Gate。所有者无法通过可移植 MCP 表面获取精简的历史流程结果。

### 4. 宿主安装仍采用本地、分宿主的生命周期

三个宿主分别使用不同且已经验证的生命周期入口。继续优化安装体验需要重复进行宿主专项生命周期
验证，并且无法解决上述两个项目级阻塞问题。

## 候选方向比较

| 候选方向 | 用户价值 | 实施成本 | 兼容风险 | 验证负担 | 决策 |
| --- | --- | --- | --- | --- | --- |
| 经所有者确认的 Gate 配置与就绪状态 | 很高：解除首次真实 Gate 的阻塞 | 中 | 低至中：增加 MCP 工具和状态字段 | 中：确定性测试加共享宿主冒烟 | **下一步实施** |
| 所有者专用的完成/放弃机制与顺序复用 | 很高：解除第二个流程的阻塞 | 中至高 | 高：必须维持人工批准边界 | 高：状态迁移、并发和三宿主语义 | 第二阶段设计 |
| 只读流程历史与证据摘要 | 中：改善连续性和可审计性 | 中 | 低：只读增量接口 | 中 | 生命周期闭环后实施 |
| 安装与更新自动化 | 中：减少安装步骤 | 高 | 高：宿主版本和缓存行为不同 | 很高：需要完整生命周期矩阵 | 暂缓 |

## 推荐增量

### 产品结果

项目初始化后，所有者可以通过单独的确认轮次定义精确的确定性 Gate 检查。OnlyiFlow 会在流程
启动前报告项目是否具备 Gate 就绪条件。稳定使用阶段的 quick 路径保持为：

```text
project_status -> flow_start
```

### 建议的可移植接口

增加第八个确定性 MCP 工具：

```text
gate_configure
```

输入：

```json
{
  "project_root": "<explicit project root>",
  "checks": [
    {
      "id": "tests",
      "required": true,
      "command": ["python", "-m", "unittest", "discover", "-s", "tests", "-v"],
      "timeout_seconds": 120
    }
  ]
}
```

契约：

- 复用现有 Gate 校验限制：一至 32 个唯一检查项、一至 32 个命令参数，以及一至 900 秒超时；
- 每次提交完整替换列表，不提供增量变更语义；
- 仅接受已纳管且不存在活动流程的项目，或 Gate 仍为空的旧版活动流程首次配置；
- 全部校验通过后再原子写入 `config.toml`；
- 返回检查 ID、是否必需、超时和数量，不回显命令文本；
- 不启动进程，不调用网络，不安装依赖，也不调用模型；
- 命令文本不进入 SQLite、领域事件、MCP 输出或证据报告。

在已纳管项目的 `project_status` 数据中增加：

```json
{
  "gate_config": {
    "configured": true,
    "check_count": 2,
    "required_count": 1
  }
}
```

当已纳管项目不存在活动流程时：

- Gate 尚未配置：返回 `gate_configure` 作为唯一下一步动作；
- Gate 已配置：返回 `flow_start` 作为唯一下一步动作。

### Skill 行为

Skill 应当：

1. 向所有者展示建议的检查 ID、是否必需、命令和超时；
2. 停止并等待新的所有者确认轮次；
3. 仅在确认后调用 `gate_configure`；
4. 报告 Gate 已就绪，并将 `flow_start` 作为唯一下一步动作；
5. 将配置准备过程排除在稳定阶段 quick 流程测量之外。

### 未采用的替代方案

**只扩展 `project_init`。** 这样可以避免新增工具，但无法清晰支持后续配置更新，也会把项目
状态创建与可执行检查策略耦合在一起。

**由宿主直接编辑 `.onlyiflow/config.toml`。** 这与当前状态所有权规则冲突，也无法生成确定性
的所有者确认记录。

**根据仓库文件自动推断检查项。** 这会让 OnlyiFlow 承担工具链推断职责，并可能静默选择不完整
或不安全的 Gate。

## 推荐增量的验收契约

实施应采用测试优先方式，并满足以下全部条件：

1. `project_status` 能报告 Gate 尚未配置，且不改变项目状态。
2. 无效的 `gate_configure` 输入返回稳定的结构化错误，并保持配置文件字节级不变。
3. 有效且经所有者确认的调用能够原子写入完整配置。
4. 已配置 Gate 的活动流程拒绝重新配置；Gate 仍为空的旧版活动流程可在单独确认后完成首次配置。
5. 响应、SQLite、事件和报告均不包含命令文本或原始进程输出。
6. 现有有效的 version-1 配置保持兼容，并返回正确的就绪状态数量。
7. 已配置项目的 quick 流程仍以恰好两次 MCP 调用进入 `implementing`。
8. 真实回归能够使配置的 Gate 失败，修复后通过，并保持证据精简。
9. 普通请求仍产生零次 OnlyiFlow 调用。
10. Codex、Claude Code 和由所有者协助的 ZCode 均暴露相同的新工具与确认边界。
11. 全新生成的候选包继续保持自包含且可复现。
12. 完整本地测试、Skill 验证器、宿主验证器、生命周期检查和清理全部通过。

## 预计实施范围

后续实施预计只修改与该契约直接相关的区域：

- `src/onlyiflow/gates.py`：共享校验与原子序列化；
- `src/onlyiflow/runtime.py`：就绪状态与配置编排；
- `src/onlyiflow/mcp_server.py`：封闭的输入和输出 Schema；
- `packaging/codex/skills/onlyiflow/SKILL.md`；
- `packaging/shared/skills-claude/onlyiflow/SKILL.md`；
- 聚焦的运行时、MCP、Skill、打包和评估 runner 测试；
- 产品规范、工程规范、发布指南与证据文档。

首个 Gate 配置增量无需变更存储 Schema。如果后续需要配置变更审计记录，应将其与命令存储
问题分开设计。

## 后续实施顺序

### 第二阶段：所有者控制的流程关闭

设计一个所有者专用的流程完成或放弃入口，同时保持人工批准位于模型可调用 MCP 工具之外。
实施前必须定义现有 `waiting_owner` 数据的迁移方式、并发启动行为，以及 `landed` 和
`abandoned` 的准确含义。

### 第三阶段：精简只读历史

终态语义确定后，增加一个有界的只读视图，返回历史流程状态、风险、时间、Gate 结果和规格是否
存在。继续排除对话记录、命令和原始输出。

### 后续阶段：安装体验优化

仅当具体宿主契约提供了稳定且可验证的改进路径时，再重新评估安装自动化；该方向应保持现有
Python 环境与本地 Marketplace 契约。

## 所有者已确认的决策

所有者已确认以下三点：

1. 批准将 Gate 配置作为下一产品增量；
2. 批准增加 `gate_configure`，使可移植 MCP 工具数量从七个增加到八个；
3. 批准仅在不存在活动流程时修改 Gate 配置；完成度检查发现旧版活动流程可能没有 Gate，因此
   首次空配置迁移作为必要兼容例外，配置后仍执行原有锁定规则。

本轮授权覆盖 0.3.0 运行时、宿主清单、规范和验证实现；插件发布与后续产品阶段仍需单独授权。

## 实施状态

0.3.0 Gate 配置增量的运行时、八工具 MCP 契约、三宿主候选包、Skill 确认边界、规范与自动化
验证已经实现。本地测试、静态检查、候选包复现、Claude 用户范围生命周期和六会话模型验收均
通过。完成度审计还修正了旧发布冒烟 runner 绕过 Gate 确认边界的问题；修正后的 Claude
十二项发布冒烟也已通过。完整记录见
`docs/evaluations/2026-07-19-v0.3.0-gate-configuration.md`。

所有者决定暂缓 Codex 0.3.0 在线模型验收；保留的本地 Codex 安装已从生成的 Marketplace
解析为 0.3.0 并保持启用，但宿主清单不作为模型可见性证据。ZCode 0.3.0 的 Desktop 导入、
八工具模型流程、失败/通过 Gate、落地、卸载与清理冒烟已经由所有者协助通过。上述增量已经
纳入 v0.3.0 正式版本。
