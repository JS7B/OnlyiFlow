# OnlyiFlow

简体中文 | [English](README.md)

OnlyiFlow 是一个小型个人开发流程插件，供一位所有者在 Codex、Claude Code 和 ZCode 中使用。

它有意将可移植的产品边界限定为：

```text
一个仅在明确请求时调用的 Skill
一个确定性的本地 stdio MCP 服务器
本地 SQLite 流程与 Gate 状态
```

宿主编码代理仍然负责理解、规划、编辑、调试和测试代码。OnlyiFlow 只记录明确的工作流状态和
确定性的落地证据。它不会安装 Hooks、拦截代理事件、管理代理配置、运行后台进程，也不会声称
能够控制直接执行的 Git 命令。

## 当前状态

版本 `0.1.0` 仍是经过验证的 GitHub 正式版本。`0.2.0` 候选版本保持相同的工作流运行时，并新增
本地 Claude Marketplace，以便在一个 Windows 用户帐户下跨项目进行持久的 `user` 范围安装。
该候选版本已经提交到 `main`，但在所有者另行授权前不会创建标签或正式发布。

Claude 安装要求 Python 3.11 或更高版本、`requirements.txt` 中声明的依赖，以及一个持续保留的、
已解压本地 Marketplace 目录。它不是免环境方案、跨计算机配置、npm 软件包或公开 Marketplace
发布。多个活动流程仍不在范围内。

Claude 和 Codex 已通过完整的激活、效率/Gate 与发布冒烟测试契约。由所有者协助完成的 ZCode
冒烟测试也通过了相同的普通请求隔离、所有者确认初始化、快速流程、Gate 失败/通过、落地和卸载
语义。

验证结束后，不会遗留 OnlyiFlow 插件、Skill、MCP 暴露、版本化缓存文件、临时工作区或运行时
进程。ZCode 仅按设计保留由所有者添加、但尚未安装的本地 Marketplace 来源；它会显示在“发现”
页面中，并带有“获取”操作。

完整的 15 项审计和已接受报告的哈希记录在发布就绪证据中。所有者已于 2026-07-17 授权该
GitHub 版本；其中不包含任何公开插件 Marketplace 发布。

请勿直接导入仓库源码根目录。不同宿主的发现机制并不相同，因此应通过
`scripts/build_loader_candidates.py` 在 `build/loader-candidates/` 下生成相互隔离的候选包。

此源码树之外的旧仓库只能作为参考资料。本仓库不会继承其中的适配器、Hook、Attention、事件
采集或能力探测架构。

## 运行要求

OnlyiFlow 不要求使用特定的环境管理器或环境名称。请选择任意 Python 3.11+ 环境，并确保宿主
进程能够找到该环境的 `python` 命令。如果使用 Conda，请自行选择并激活环境，再安装依赖并启动
宿主。

所需软件包列在 `requirements.txt` 中。从源码检出目录安装时，请将它们安装到所选环境：

```powershell
python -m pip install -r requirements.txt
```

使用 Claude 发布压缩包时，请使用保留的 Marketplace 目录中随附的副本：

```powershell
python -m pip install -r "<保留的-Claude-Marketplace目录>\plugins\onlyiflow\requirements.txt"
```

## 仓库分层

规范文件：

- `docs/product-spec.md`：产品行为与非目标；
- `docs/engineering-spec.md`：运行时、持久化、传输、打包与测试契约；
- `docs/release-guide.md`：所有者安装、验证、清理和授权流程。

产品与打包实现：

- `src/onlyiflow/` 和 `server/stdio.py`：交付的确定性运行时；
- `packaging/`：宿主清单和仅供手动调用的 Skill 包装模板；
- `scripts/build_loader_candidates.py`：生成宿主包的脚本。

验证工具：

- `tests/`：确定性的单元、契约、打包和 runner 测试；
- `scripts/run_skill_evaluations.py`、`scripts/run_efficiency_measurements.py` 和
  `scripts/run_release_smoke.py`：不会复制到插件中的发布证据 runner。

证据与历史：

- `docs/research/`、`docs/plans/` 和 `docs/evaluations/`：观察记录、执行历史与已接受报告引用；
- `build/task*-*-results/` 下被忽略的 JSON 报告：可在本地复现的证据产物。

证据层中的任务编号、机器观察、探针和历史失败并不是产品要求。如果证据与规范文件不一致，
以产品规范和工程规范为准。

## 文档

- [产品规范](docs/product-spec.md)
- [工程规范](docs/engineering-spec.md)
- [三宿主加载器研究契约](docs/research/2026-07-16-three-host-loader-contract.md)
- [插件优先基础计划](docs/plans/2026-07-16-plugin-first-framework-foundation.md)
- [所有者安装与发布指南](docs/release-guide.md)
- [Claude 用户范围安装计划](docs/plans/2026-07-18-v0.2.0-claude-user-install.md)

生成的插件候选目录：

- `build/loader-candidates/codex-marketplace/`
- `build/loader-candidates/claude-marketplace/`
- `build/loader-candidates/zcode/`（ZCode 本地 Marketplace 根目录；插件位于 `onlyiflow/` 下）

## 产品核心规则

> 宿主代理负责实现。OnlyiFlow 负责明确的工作流状态和确定性的落地证据。

如果没有外部的分支保护、CI 或由所有者安装的 Git hook，OnlyiFlow 无法阻止代理或用户直接运行
`git push`、`git merge` 或其他落地命令。
