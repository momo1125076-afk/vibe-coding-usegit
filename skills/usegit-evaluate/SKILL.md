---
name: usegit-evaluate
description: "依据客户需求与证据比较 GitHub、Gitee 项目，检查平台和许可证硬条件，并按固定权重输出可选、待核实与排除方案。用于开源选型、项目复用、是否改造或自建的决策，以及 UseGit 的 evaluate 阶段。"
---

# UseGit 选型比较

阶段名为 `evaluate`。先检查硬条件，再比较改造收益与成本。脚本负责一致计算，agent 负责读取证据、判断适用性和解释决策。

## 输入和证据

读取需求简报、候选搜索报告及其 `coverage` / `errors`，以及已找到的相关技能清单。需要比较的是同一需求下可行的整体方案：单项目、多个组件组合、或以框架自建。不同类别不能仅凭 star 排在同一榜上。

逐项建立“需求 → 实现位置或文档 → 缺口 → 工作量”的映射。微信小程序检查小程序目标与工具链；Web 检查浏览器和服务端边界；App 检查目标系统与构建方式；桌面、扩展、API 与自动化各自核实运行环境。API 或 README 的主张不等于已实际运行。

硬条件至少包含 `license-fit` 和 `platform-fit`；脚本会自动保留这两项。按客户约束添加例如 `data-location`、`offline-support`、`origin-verified`。不满足的硬条件必须有证据才标为 `fail`；尚未核实则为 `unknown`。公开仓库但无可核实许可证不能标记许可通过。检查实际 LICENSE、关键依赖和拟采用的部署方式，遇到实质不确定项保留待核实。

## 评分

每项使用 0–5 分，记录证据 URL 或项目内产物路径及说明。分数是本项目的方法，不是平台官方认证。

| 维度 | 字段 | 权重 | 核心判断 |
| --- | --- | ---: | --- |
| 需求匹配 | `fit` | 30 | 核心用户流程和必要功能覆盖 |
| 可运行性 | `runnability` | 20 | 安装说明、依赖、配置与可复现实测 |
| 可改造性 | `adaptability` | 15 | 模块边界、扩展点和改造范围 |
| 维护 | `maintenance` | 15 | 近期发布、兼容性、问题响应与修复证据 |
| 许可证 | `license` | 10 | 许可明确程度及当前复用计划的适配 |
| 部署成本 | `deployment_cost` | 10 | 资源、外部服务、持续维护与发布门槛 |

总分为 `Σ(分数 / 5 × 权重)`。缺失或无证据的评分保留未知且计 0 分，不重新归一化；star 仅在总分和证据覆盖相同后辅助排序。可运行性 5 分需要当前任务环境中的实际运行证据；未运行时说明文档基础和待验证事项，不将安装说明当成运行成功。

0–5 分锚点、完整输入模板及计算限制见 [evaluation-contract.md](references/evaluation-contract.md)。

## 计算和解释

定位本技能实际目录，使用 Python 3.10 或更高版本运行：

```bash
python3 <本技能目录>/scripts/rank_candidates.py \
  --input .usegit/artifacts/repos.json \
  --assessments .usegit/artifacts/assessments.json \
  --out .usegit/artifacts/comparison.json
```

脚本离线计算，不能验证传入的证据是否真实、当前有效或足以支持结论。每条引用必须由 agent 阅读并记录核实结果；不要把引用的存在误说成自动审计通过。

- `ranked`：全部硬条件通过且六项评分有证据，可进入决策。
- `needs_review`：硬条件未知或评分缺失，列出补证所需动作。
- `excluded`：至少一个有证据的硬条件失败，保留原因而不参与推荐。

向客户说明推荐项、最接近的备选项、核心需求覆盖、剩余改造工作及运行/部署成本依据。费用如未询价或未测算则保留估计和假设。搜索覆盖不足也要出现在决策说明中；不能将局部搜索包装成全站最佳项目。

若已有授权且证据支持明确选项，继续选型并交接，不重复请求确认。只有会改变范围、预算或客户偏好的实质取舍仍未解决时才询问。没有可行候选时，清楚说明组件组合、自建或缩小范围的依据。

## 产物与交接

保存 `.usegit/artifacts/assessments.json`、`.usegit/artifacts/comparison.json` 和面向客户的 `.usegit/artifacts/selection.md`。推荐必须可追溯到候选 ID、证据、功能缺口与假设。

**评分报告不是阶段完成记录。** 另写 `.usegit/artifacts/evaluate.json`，采用调度技能的阶段契约：`schema_version`、`stage`、`status`、`summary`、`outputs`、`evidence`、`checks`、`blockers`、`executed_actions`。将上述文件列入 `outputs[{path,description}]`；证据按主契约标明 ID、类型、主张、核实状态及适用的 URL/路径/命令/环境/观察时间。状态枚举和 `record` 命令用法以主技能为准，不能把 `comparison.json` 直接登记为成功阶段，也不要直接修改主状态文件。

通过名称交给 `usegit-run`，传递被选方案、仓库规范地址、已知版本/提交（未知则明示）、许可证结论、安装依据和运行验收目标。硬条件未知时继续补证或向调度技能报告阻塞，不把评分当作部署授权。技能协作使用名称，不依赖安装后的相邻目录。

## 参考

- [evaluation-contract.md](references/evaluation-contract.md)：输入模板、评分锚点、分类与退出码。
- [sources.md](references/sources.md)：方法来源及证据核实边界。
