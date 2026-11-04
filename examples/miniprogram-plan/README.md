# 微信场地预约：真实前向测试

测试日期：2026-11-04。使用当前工程技能，从用户一句需求新建文档，未读取原有示例答案。

## 实际完成

- 阅读主技能及 discover、find-skills、find-repos、evaluate 协作技能和相关契约。
- 使用现有 Python CLI 初始化 plan、doctor、模板与状态登记；未安装第三方软件。
- 生成 `.usegit/artifacts/` 下 13 份需求、来源、工具与选型准备文件。
- 5 个稳定需求编号，其中 3 个 confirmed，2 个 assumed；业务验收只定义，没有执行。
- discover 与 find-skills 已用源码 CLI 登记 complete。find-repos 与 evaluate 登记 blocked，complete_for_mode 为 false。
- 未联网检索，未运行评分或候选项目，未部署、未提交远程。零候选不意味着没有合适项目。

## 问题与恢复

1. 最初文档的 `skills/vibe-coding-usegit/scripts/usegit.py` 不存在，`--help` 退出 2。后续同步已补文件。
2. 文档 init 的 `--name/--idea/--platform` 参数最初不接受，退出 2，见 logs/documented-init.log。
3. `.usegit/artifacts` 被 template 和 record 当作状态目录整体拒绝。mkdir 后仍复现，根因是校验拒绝整个 `.usegit` 子树而非仅状态文件。
4. 实施过程中 tools/usegit.py 先修复而技能副本仍旧。切回旧副本运行 status，会把新源码已成功登记的 discover 标成 stale。两个文件哈希及实际退出码见 logs/retest.json。

恢复使用当时已修正的 tools/usegit.py，重新登记四阶段后得到 logs/final-status.json。最终打包副本若已再次更新，以后续 retest 为准，不把这些历史错误认定为当前仍存在。

## 仍需完成

本例是需求和选型准备，不是完整 plan 交付。需确认关键预约规则、实际搜索双站、读取候选许可证和核心代码，再形成可追溯比较。本例未把另一个工作者的查询或他人的网络错误冒充自己的执行证据。

## 可复查位置

- `.usegit/artifacts/brief.md`：用户需求与待定事项。
- `.usegit/artifacts/requirements.json`：稳定需求和来源。
- `.usegit/artifacts/*-skills.json` / `find-repos.json` / `evaluate.json`：阶段报告。
- `logs/`：真实 CLI 结果；doctor 的可执行路径仅代表存在，不代表已登录。

复制包中不含凭据和本机原始状态文件，项目记录由 CLI 重新创建后可据报告登记。

## 修正后独立复测

最终技能副本与 tools/usegit.py 字节相同。经实际执行，文档入口 --help、带 --name/--idea/三个 --platform 的全新 init、直接写入 .usegit/artifacts 的 template、四阶段正常 record、status、next、audit 共 10 条命令全部退出 0。详见 logs/fixed-retest.json 及 fixed-00 至 fixed-09.log。原发现的路径、参数和副本漂移问题本次复测未再出现。

状态恢复通过正常 record 完成，没有直接修改 state。最终 discover/find-skills complete，find-repos/evaluate blocked，其余阶段 not-required；complete_for_mode=false 正确反映只做准备、尚未真实搜索与比较。CLI 成功不代表业务或选型完成。

## 从发布快照复现

为避免把真实客户的 .usegit 运行目录提交到版本库，本例的脱敏固定输入放在 `artifacts/`。报告内仍保留运行时 `.usegit/artifacts/` 路径。执行 `python3 tools/replay_example.py` 会在新的临时项目中复制这些输入、正常初始化与登记四阶段并检查状态；不联网、不改原示例。历史日志中的 /tmp 路径仅表示当时的隔离运行位置。
