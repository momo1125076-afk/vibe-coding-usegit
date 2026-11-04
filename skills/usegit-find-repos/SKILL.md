---
name: usegit-find-repos
description: "根据客户需求在 GitHub、Gitee 寻找可复用项目，记录许可证、维护状态、平台适配、检索覆盖与证据。用于用户希望找开源替代品、高星项目、微信小程序、Web、App、管理后台或服务端基础项目，以及 UseGit 的 find-repos 阶段。"
---

# UseGit 开源项目搜索

把需求变成可核实的项目候选。阶段名为 `find-repos`。本技能只检索和阅读，不运行搜索结果中的代码。

## 输入

读取当前任务的需求简报、目标平台、必须具备的功能、预算与部署限制。优先使用 `.usegit/artifacts/` 中已有产物；缺失时从用户对话建立最小输入。只有会改变候选范围的问题才需要澄清，其他假设写入报告。

识别用户需要的是可直接改造的业务系统、框架、组件还是技能。将微信小程序与普通移动网页分开；将 App 区分原生与跨平台；管理后台、API 服务、桌面工具、浏览器扩展、自动化与 AI 工作流也应明确运行环境。

## 搜索流程

1. 从业务场景、关键功能、目标平台及技术约束产生中英文检索词。先搜功能和平台，再在结果过多时增加语言、框架、许可证、更新时间或星数条件。星数用于发现线索，不代替质量判断。
2. 使用已提供的连接器、官方 API 或公开网页检索。只有实际使用过的来源才写为已检索。GitHub 与 Gitee 查询语法不同，分别构造查询；不要假设 GitHub 的限定词在 Gitee 同样有效。
3. 为每次查询记录提供方、查询词、观察时间、页数、返回条数、过滤条件和错误。保留部分结果；认证失败、限流、超时与接口错误必须写为覆盖限制，不能写成“没有项目”。不绕过当前环境的网络限制。
4. 对候选读取 README、安装说明、LICENSE、发布记录及与核心需求有关的目录。将“README 声称支持”“查看源码可确认”“已实际运行”分开；本阶段通常不能给出已运行结论。
5. 按规范仓库地址去重。跨站同名仓库、镜像和 fork 先查 upstream、提交历史和项目主页；未确认来源时标记待核实，不把镜像当独立项目，也不合并星数。
6. 有足够结果时选出 3–5 个值得比较的候选，说明命中需求、缺口与下一步核实项。若只有 1 个或没有合适结果，报告实际数量和搜索范围，继续考虑组件组合或自建，不编造候选。

## 内置搜索脚本

运行前定位本技能实际目录。安装后的文件夹可能改名，不依赖其他技能的相邻路径。以下路径中的 `<本技能目录>` 由当前环境解析；脚本要求 Python 3.10 或更高版本，无第三方依赖。

```bash
python3 <本技能目录>/scripts/search_repos.py \
  --provider both --query "appointment booking" \
  --limit 20 --min-stars 10 --out .usegit/artifacts/repos.json
```

针对平台分别搜索时可以重复 `--query`，或分别调用并保留各报告。`--limit` 是每个提供方、每个查询的候选上限。退出码 `1` 仍可能有有用候选，必须读取 `coverage` 和 `errors`。完整参数和 JSON 契约见 [discovery-contract.md](references/discovery-contract.md)。

脚本默认匿名读取公开仓库；可选 `GH_TOKEN` / `GITHUB_TOKEN` 与 `GITEE_TOKEN` 环境变量，不要求用户在对话中粘贴密钥。禁止将密钥写入查询、产物或运行日志。脚本不读取个人凭据文件，不跟随重定向，不执行仓库代码。

许可证未知保留 `null`，公开可见不等于允许开源复用。仓库 API 的许可证标记只是线索，还需读取实际许可文件及相关依赖限制。缺失 star、归档状态、最近推送时间等元数据保留未知，不补成零或最新。

## 产物与交接

保存以下产物，路径可按任务调整：

- `.usegit/artifacts/repos.json`：脚本生成的原始搜索报告，含候选、覆盖和错误。
- `.usegit/artifacts/repository-shortlist.md`：面向客户的候选表、需求匹配、证据链接、镜像关系与待核实项。
- `.usegit/artifacts/find-repos.json`：按主技能当前版本的阶段契约编写的交接记录。

**搜索报告不是阶段完成记录。** `repos.json` 即使带有 `stage`，也不能直接交给主 CLI 的 `record`。单独的阶段记录包含 `schema_version`、`stage`、`status`、`summary`、`outputs`、`evidence`、`checks`、`blockers` 与 `executed_actions`。将原始报告和候选表列入 `outputs[{path,description}]`，按主契约填写证据 ID、类型、主张、核实状态及 URL/路径/命令/观察时间等适用字段。状态值和命令用法以调度技能为准，不自行更新主状态文件。

将真实执行过的查询及来源记入 `evidence` 和原始报告的 `coverage`。普通只读搜索的 `executed_actions` 保持空数组；该字段仅用于主契约列出的发布、付费或破坏性动作。覆盖错误和仍影响选型的未知项进入 `blockers` / `checks`。通过技能名称交给 `usegit-evaluate`，同时传递需求简报、候选报告和搜索限制。不要通过假定的相邻文件夹寻找其他技能。

## 参考

- [discovery-contract.md](references/discovery-contract.md)：脚本参数、输出与边界。
- [sources.md](references/sources.md)：官方 API 来源、核实范围与未实测事项。
