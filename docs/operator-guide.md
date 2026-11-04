# 操作手册

## 安装和首用

Python 3.10+ 为辅助工具要求；无需第三方 Python 包。先运行 `python3 tools/usegit.py doctor`。它只显示工具路径与环境变量存在性，不打印值；登录、网络、目标环境都要另测。按 [宿主指南](host-compatibility.md) 安装九个技能，启动新会话，显式请求主技能名称。安装失败时检查当前用户写权限、现有同名技能、符号链接和宿主真实发现目录；不要直接覆盖全局安装。

每个客户项目独立建立记录：

```sh
python3 tools/usegit.py init --project /tmp/booking-demo --name booking --idea '微信预约与后台' --platform wechat-miniprogram --platform backend --mode plan
python3 tools/usegit.py status --project /tmp/booking-demo
python3 tools/usegit.py next --project /tmp/booking-demo
python3 tools/usegit.py template discover --project /tmp/booking-demo --out .usegit/artifacts/discover.json
```

模板默认 blocked，必须填入实际需求和结果再登记。`init` 拒绝覆盖已有状态。客户访谈、日志与账号环境数据保存在客户项目 `.usegit/`，不进入技能安装目录，也不默认提交 Git。

## 常用命令

使用 `python3 tools/usegit.py <命令> --help` 查看本构建的完整参数。

| 命令 | 作用 |
|---|---|
| init | 创建项目，默认 local，支持 --name/--idea/重复 --platform |
| doctor | 检查工具存在性，非登录认证 |
| status / next | 核实记录与哈希，列出可执行阶段 |
| template STAGE --out PATH | 输出未执行模板，不覆盖已有文件 |
| record STAGE --artifact PATH | 校验阶段报告、证据、依赖、授权再登记 |
| authorize ACTION --target TARGET --source SOURCE | 记录用户已授予的精确授权 |
| invalidate STAGE --reason TEXT | 标记阶段与依赖过期 |
| set-mode --mode MODE --source SOURCE | 改变交付目标，不自动授权新动作 |
| audit | 文件变化返回 2，并标记过期 |

每个项目命令附 `--project`。正常返回 0；参数、证据、依赖或授权失败返回 2。发生错误时阅读 JSON 错误，不仅检查是否生成了文件。4 MiB 是单个 JSON 上限；大型命令日志单独保留。锁冲突先检查所属进程，不能盲目删除活跃 state.lock。

## 从需求到验收

1. discover：角色、流程、平台、MVP、非目标、假设、待定问题；稳定 REQ ID 和验收条件。不要每一步重复确认已明确的输入。
2. find-skills / find-repos：可并行，但各写自己的产物。前者补能力，后者找软件，不混为一类结果。
3. evaluate：实际读取许可证和核心实现，先硬条件后权重。证据不足保持 needs_review；允许有依据选择自建。
4. run：固定版本，在指定环境启动，保存真实命令、退出码、日志，不把 README 承诺当运行结果。
5. adapt：按需求编号增量修改，复查错误、空数据、权限、重复提交、恢复等关键状态。
6. deploy：仅 preview/release 或明确独立交付要求执行，核对目标授权、构建版本、回执和回滚；区分上传/审核/上架。
7. verify：每个 must 有真实 pass，既测正常流程也测重要失败分支；产物、构建和线上版本一致。

所有阶段 JSON 的精确字段见 [协作契约](../skills/vibe-coding-usegit/references/orchestration.md)。observed 表示记录声称已观察，不是数字签名证明，Agent 仍需读取原始证据。

## GitHub/Gitee 搜索

```sh
python3 tools/search_repos.py --provider both --query 'appointment booking' --limit 20 --max-pages 3 --page-size 50 --timeout 10 --out /tmp/repos.json
```

query 可重复 1–8 次，每次最多256字符；limit 1–100；page-size 1–100；max-pages 1–10；timeout >0且<=30秒；min-stars 非负，include-archived 显式纳入归档。未知 star/license 保留 null。退出0表示有界请求正常结束（不是全站穷尽），1表示部分/错误仍保存报告，2表示输入/文件错误。默认不重试、不跟随重定向、不下载候选代码，2MiB响应上限。

可选 GH_TOKEN/GITHUB_TOKEN 仅发 GitHub 请求头，GITEE_TOKEN 仅发 Gitee 官方端点；不要在聊天中粘贴或把密钥写入仓库。当前环境的网络限制优先。脚本受限时使用宿主已授权连接器或官方网页，并单独记录来源，不能称脚本联调已通过。

## 候选评分

```sh
python3 tools/rank_candidates.py --input /tmp/repos.json --assessments /tmp/assessments.json --out /tmp/comparison.json
```

assessment 格式和分数锚点见 [评分契约](../skills/usegit-evaluate/references/evaluation-contract.md)。fit/runnability/adaptability/maintenance/license/deployment_cost 权重30/20/15/15/10/10，分数0–5。不完整维度不重新归一化；硬条件失败优先排除；空证据不能支持pass/fail或分数。评分只验证引用语法，不读取证据真实性。退出0不代表任何候选已运行或获准复用。

## 变更、更新和故障处理

需求变化先更新 discover，再登记；受影响下游 stale。仅部署目标变化可 invalidate deploy。修改辅助脚本后运行 sync_skill_scripts.py，确保独立安装包不依赖源码目录。

网络失败保留部分覆盖，账号失败使用服务的受支持登录流程；签名、设备或审核缺失明确 blocked。更新技能先 dry-run，使用覆盖备份，失败恢复；客户项目记录不应随技能卸载删除。生产回滚和数据库恢复分别计划，不擅自执行破坏性恢复。

## 一句话示例

- “用 UseGit，只做 plan：我想做离线物品管理 App，优先找可复用项目，比较许可证与同步成本。”
- “继续这个已有项目的 local 模式，先 status 和 next，别重新初始化，修复预约重复提交并验证。”
- “准备微信小程序提交包，但不上传、不送审；列清开发者工具和 AppID 缺项。”

这些示例不授予发布、付款或向第三方发送消息的权限。
