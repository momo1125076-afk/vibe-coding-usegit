# 协作契约与状态

## 目录

- 项目记录与阶段依赖
- 返回契约
- 证据与授权
- 交接与变更
- CLI 约定

## 项目记录与阶段依赖

每个客户项目单独保存 `.usegit/state.json`，不要在技能安装目录保存客户内容。`.usegit/.gitignore` 默认排除整个运行目录，避免把客户访谈、日志和环境数据误提交。

依赖为 discover → {find-skills, find-repos} → evaluate → run → adapt。local 模式从 adapt 进入 verify；preview/release 从 adapt 进入 deploy 再 verify；plan 到 evaluate 结束。

只有主调度调用 state 写入命令。工作者只写各自的报告与输出；同时发现技能和仓库时使用不同文件名。CLI 用进程锁与原子替换避免同时写入损坏，但这不替代对代码编辑的工作分工。

状态：pending 尚未执行；complete 有可审查产物；blocked 需要外部条件；failed 实际执行失败；skipped 有理由省略（只允许 find-skills/adapt）；not-required 不在当前模式内；stale 上游变更或证据文件变化。

`complete_for_mode=true` 只代表当前模式及已登记需求完成。plan 完成不代表软件已运行；local 完成不代表发布；生产提交完成不代表外部商店已审核。

## 返回契约

每个阶段交回一个独立 JSON 对象，字段如下。额外字段可增加，但不得改变这些字段的含义。

| 字段 | 内容 |
|---|---|
| schema_version | 固定 1 |
| stage | discover/find-skills/find-repos/evaluate/run/adapt/deploy/verify |
| status | complete/blocked/failed/skipped |
| summary | 通俗结果摘要，区分真实执行和计划 |
| outputs | `[{path,description}]`，项目内已存在的文件 |
| evidence | `[{id,kind,claim,verification,...}]` |
| checks | `[{requirement_id,result,evidence_ids,notes?}]` |
| blockers | `[{reason,next_action}]` |
| executed_actions | `[{action,target}]`，实际发生的外部敏感动作 |

discover 完成时还必须有 requirements 数组：`[{id,priority,text,acceptance}]`。priority 为 must/should/could，ID 稳定且唯一；其他文件与验证项都引用同一个 ID。把“快一点”改成可观察结果，再记录假设或待确认阈值，不伪造客户同意。

评分脚本与搜索脚本的 JSON 是原始报告，放入 outputs 引用；它们不是阶段完成报告。例：`repos.raw.json` 是输出，`find-repos.json` 是阶段返回值。

输出与证据路径必须相对项目根目录，不能越界或通过符号链接指向外部。不要使用 state.json 或 state.lock 作为业务产物。

## 证据与授权

evidence.kind：

- `file`：附 path，说明实际读取/生成的文档或源码能支持什么。
- `command`：附 command、整数 exit_code、path（日志）、environment、observed_at；建议再附 commit。
- `url`：附 url、environment、observed_at，说明实际观察到什么。URL 无密码或临时凭据。
- `manual`：附 path（人工验证记录）、environment、observed_at，写出执行人角色与结果，不编造签收。

verification 必须为 observed、simulated 或 not-run。complete/skipped 至少需要 observed 证据，且不能包含失败、阻塞或未测的检查；首次 run 需要退出码为 0 的真实命令。失败命令可以作为排障历史，不能支持一个 pass。验证 must 需求必须 pass，不允许用 not-applicable 静默移除。

返回中的 `executed_actions` 列出发生过的 preview-deploy、production-deploy、store-submit、paid-resource、public-publish、destructive。记录前必须已有用户对同一 action 和 target 的授权。target 用精确可识别的项目/环境/仓库，不能用泛化的“所有环境”。

CLI 的授权记录与证据检查是流程记账，不是权限系统、密码保险箱或真实性证明器。任何人都能编写 JSON；实际真实性由 Agent 阅读原始结果、浏览器/命令证据和用户验收共同核实。禁止用这套记录绕过平台审批或宿主工具限制。

## 交接与变更

工作单最少包括 stage、输入路径、需求 ID、目标环境、允许写入的文件、现有授权范围和交付 JSON 路径。主调度核对报告与原始证据后再调用 record。

代码变更以基线提交、当前提交、修改文件和需求 ID 关联。部署与最终验收应指向同一构建/提交/部署 ID；新代码发生后要重新构建与验证，不能复用旧截图作为新版本证明。

需求变化重跑 discover 后，下游旧结果标 stale；仅部署目标变化可 invalidate deploy。上游产物篡改或丢失时，status/next/audit 会检查哈希并标记相关阶段失效。

最早受影响的阶段和后续失效阶段允许重做；保留原日志和版本以便解释。不要新开第二个无关联工作流或反复重新搜索相同已核实来源。

## CLI 约定

以 `python <技能目录>/scripts/usegit.py <命令>` 调用；每个项目命令附 `--project <项目目录>`。

| 命令 | 用途 |
|---|---|
| init | 建立项目；已有项目拒绝覆盖 |
| doctor | 查看工具路径、Python 与凭据变量是否存在，不输出凭据值 |
| status / next | 查进度与可执行阶段，刷新内容完整性 |
| template STAGE | 生成标 blocked 的未执行模板 |
| record STAGE --artifact PATH | 检查契约、证据路径/哈希、依赖和授权，保存结果 |
| authorize ACTION --target TARGET --source SOURCE | 记录已收到的具体用户授权 |
| invalidate STAGE --reason REASON | 标记该阶段及依赖结果需重做 |
| set-mode --mode MODE --source SOURCE | 变更交付目标；不会自动授权发布 |
| audit | 检查已记录文件是否仍匹配，发现变化退出码 2 |

正常命令返回 0；输入、依赖、证据或权限记录不满足返回 2。客户端应读取 JSON 错误，不把非零退出码当作成功。

单个 JSON 文件最多 4 MiB，写入超过上限时保留原文件并报错。大型日志作为单独证据文件引用；不要把日志正文塞进 summary、授权来源或历史字段。本版本不自动归档长期历史。
