# 五宿主安装、调用、升级与恢复

核实日期：2026-11-04。这里的兼容适配是**文件分发与安全安装**；自动测试通过不等于五个宿主已真实发现、执行或完成客户项目。项目不自动安装宿主 CLI，不登录账号、不生成凭据、不设置 `allowed-tools`、hooks、MCP 或全局权限。

## 一、安装入口与官方依据

所有源都在 `skills/<name>/SKILL.md`。主技能 `vibe-coding-usegit` 加八个 `usegit-*` 协作技能，共九份独立目录。脚本、引用和模板随所属技能复制，不需要源仓库或兄弟技能目录才能读取自身资源。主技能协调协作技能时仍需要宿主可发现那些技能，缺失时应如实降级，而不是声称调用成功。

| `--host` | 本工具在 `--project` 下的目的地 | 官方规则与调用方式 |
| --- | --- | --- |
| `codex` | `.agents/skills/<name>` | 官方列出项目 `.agents/skills` 和用户 `~/.agents/skills`；由元数据发现，选中后读取正文与资源。在项目新会话中明确要求“使用 vibe-coding-usegit”。[官方定制文档](https://learn.chatgpt.com/docs/customization/overview) |
| `claude-code` | `.claude/skills/<name>` | 本地 Claude Code 支持项目技能，输入 `/vibe-coding-usegit`。本地个人、项目、云会话及 Cowork 的来源不同，不能以本工具安装推断云端可用。[官方技能文档](https://code.claude.com/docs/en/skills) |
| `deepseek-harness` | `.dsh/skills/<name>` | 官方优先扫描项目 `.dsh/skills`，也支持 `.agents/skills`。本工具只写前者，避免两处静默重复。请 Agent 用 `skill({name: "vibe-coding-usegit"})` 加载并检查实际资源来源。[官方子系统说明](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/skills.md) |
| `openclaw` | `skills/<name>` | `--project` 必须指向实际 agent workspace。workspace 技能有较高优先级，发现、依赖就绪和对 agent 可见需分别验证。[官方技能文档](https://docs.openclaw.ai/tools/skills) |
| `workbuddy` | `dist/workbuddy/<name>.zip` | 每个 ZIP 只有一个技能顶层目录；不猜测本地安装路径。技能板块→添加技能→上传技能，选本地包导入。自制包不能用市场对话安装替代。[官方上传说明](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market) |

WorkBuddy 市场规范要求 `name`、`description`、`display_name`、`display_name_en`、`description_zh`、`description_en`、`version`、`author`。适配层补齐中英文展示信息，版本及真实作者必须明确传入，不虚构厂商署名。此要求来自市场分发规范，不声称所有本地加载器也强制这些字段。`examples_zh/en` 是可选项，本包不生成。[WorkBuddy 开放平台规范](https://open.workbuddy.cn/docs/skill)

通用源不注入 `${CLAUDE_SKILL_DIR}`、`{baseDir}` 等专属变量。技能应先确认当前 `SKILL.md` 所在目录，再基于该目录访问资源；需要宿主专属路径变量时由该宿主实际调用层使用。

## 二、先预览，再显式写入

要求 Python 3.10+，只有标准库依赖。在仓库根目录执行。示例中的项目路径由你选择，不要选个人主目录、系统根目录或技能源目录。

```bash
python tools/install_skills.py --host codex --project "/tmp/usegit 客户项目"
python tools/install_skills.py --host codex --project "/tmp/usegit 客户项目" --apply
python tools/install_skills.py --host claude-code --project "/tmp/usegit Claude" --apply
python tools/install_skills.py --host deepseek-harness --project "/tmp/usegit DSH" --apply
python tools/install_skills.py --host openclaw --project "/tmp/usegit Claw workspace" --apply
```

第一条是 dry-run，输出 JSON 计划，不创建项目、目录或备份。其余包含 `--apply` 才实际写入。实际使用时替换为宿主会打开的隔离项目/workspace。若有同名目录，即使文件相同也报冲突，需要显式 `--overwrite`，不静默覆盖。重复执行不会追加嵌套目录。

Windows PowerShell 同样使用双引号路径，例如：

```powershell
python tools/install_skills.py --host codex --project "C:\UseGit 测试\客户项目"
```

Windows 的原生文件系统与宿主没有在 Linux 测试中得到验证。自动测试验证了带空格/中文 POSIX 路径与危险 Windows 风格相对路径的拒绝，不能据此宣称 Windows 实机通过。

其他参数：

- `--source <目录>`：明确替代 `skills` 源；默认相对安装器所在仓库定位，不依赖当前工作目录。
- `--skill <name>`：只处理该技能，可重复传入。默认全部九个；名称只接受本项目固定九个名称。
- `--version X.Y.Z --author "真实作者署名"`：WorkBuddy 打包必需。使用项目发布版本和经确认的作者署名，不要直接把示例文字当实际署名。
- `--uninstall`、`--restore BACKUP_ID`：互斥操作，默认也只预览。
- 正常返回 0；输入、路径、冲突、锁、文件系统错误返回 2，并输出 JSON 错误。命令行语法错误由 argparse 输出错误与退出码 2。

WorkBuddy 生成包：

```bash
python tools/install_skills.py --host workbuddy --project "/tmp/usegit packages" --version 0.2.0 --author "你的真实署名"
# 检查计划后，为同一命令添加 --apply
```

先导入八个协作技能，再导入主技能，全部启用后开新对话明确选择主技能。上述顺序是本项目建议，不是声称平台强制。ZIP 生成不等于 UI 导入，不等于市场投稿成功。本工具不上传、不自动接受协议、不公开发布。

## 三、升级、卸载、备份恢复

升级前保存客户工作，检查新版本差异。更新技能源后用同样命令添加 `--overwrite` 预览，确认后再加 `--apply`。不要把客户 `.usegit` 状态或业务代码放进技能目录。

```bash
python tools/install_skills.py --host codex --project "/tmp/usegit 客户项目" --overwrite
python tools/install_skills.py --host codex --project "/tmp/usegit 客户项目" --overwrite --apply
```

每次成功写操作返回一个 `backup_id`。原内容与清单保存在项目的 `.usegit-installer/backups/<backup_id>/`。将 `.usegit-installer/` 排除版本控制，备份可能包含旧技能的本地编辑。卸载同样先备份，可恢复：

```bash
python tools/install_skills.py --host codex --project "/tmp/usegit 客户项目" --uninstall
python tools/install_skills.py --host codex --project "/tmp/usegit 客户项目" --uninstall --apply
python tools/install_skills.py --host codex --project "/tmp/usegit 客户项目" --restore <实际backup_id>
python tools/install_skills.py --host codex --project "/tmp/usegit 客户项目" --restore <实际backup_id> --apply
```

将尖括号占位符替换为 JSON 中实际的 32 位备份 ID。首次安装的恢复会移除本次新增技能；覆盖安装的恢复还原旧版本；卸载的恢复还原卸载前内容。恢复本身也建立新备份。不会移除其他名称的技能或全局配置。若安装后有内容改动，恢复拒绝覆盖，先另外保存编辑再决定如何处理，不能把拒绝当作已恢复。

对 WorkBuddy，`--uninstall` 只删除本工具输出的 ZIP，**不会卸载已导入应用的技能**。已导入包应在 WorkBuddy 技能管理 UI 移除；升级时保留旧 ZIP，使用 UI 导入新包，核对同名冲突和实际版本；是否替换必须以当前 UI 为准。

### 事务边界

- 使用项目内排他锁，先完成全部预检、暂存与备份，再逐项替换。普通 Python 异常时回滚已经触碰的项；测试通过第三次替换故障注入验证多项回滚。
- 每个替换使用同文件系统的重命名，但九个技能的整体切换不是单次原子事务。不要让正在运行的宿主在升级中读取一半新旧内容；结束会话后升级，再开新会话。
- 突然断电、SIGKILL、磁盘损坏或回滚本身失败不承诺自动恢复。保留锁和备份，核实没有活跃安装进程，检查 `manifest.json` 状态后人工审阅。自动 `--restore` 仅接受 `completed` 的事务，拒绝 `prepared` 等不确定状态，不自动删除疑似旧锁。
- 拒绝 `..` 路径、源/目标重叠、现存 symlink（含祖先及断链）、非普通文件、危险 ZIP 项名、已知凭据文件名和私密目录。忽略 Python 缓存。备份恢复验证目标与旧内容指纹，拒绝被篡改目标路径。
- 这不是通用秘密扫描器，也不是抵御恶意并发文件系统修改的沙箱。打包前仍须审阅源文件内容，不应在其他人可恶意改写的目录运行。锁只协调本安装器，不能阻止外部程序改文件。
- Frontmatter 仅支持受控平面字符串字段：普通单行、JSON 双引号字符串、YAML 单引号字符串；拒绝嵌套、数组、多行、未知键及权限字段。它不是完整 YAML 解析器。若未来要支持更多字段，先扩展明确 schema 和测试，不能静默接受不懂的语义。

## 四、确认宿主真正能用

对每个宿主分别执行，不把某个平台成功推广到其他平台：

1. 开新会话，记录宿主版本、OS、项目/workspace、技能版本和安装路径。
2. 检查九个名字实际出现在技能目录/选择器或加载日志中，再明确加载主技能。
3. 让主技能读取 `usegit-discover`、`usegit-find-repos` 与自身参考资料，记录实际来源，防止用户级旧同名版本抢先。
4. 从实际安装技能中执行 `scripts/usegit.py --help` 等适用命令；从不同工作目录验证资源仍可读。脚本有输出不代表宿主已加载。
5. 用下方 plan 演练创建需求并推进到 evaluate，保存记录后结束会话，再在同一客户项目恢复。移除一个协作技能时应报告缺失而不伪造调用。
6. 单独核实工具能力、网络、登录和目标平台。`doctor` 检出程序或变量仅说明存在，状态 `ready` 需要真实探测，不通过安装器声称已就绪。

建议演练输入：

> 使用 vibe-coding-usegit。做一个微信场地预约小程序与网页管理后台，首版不支付，只完成 plan，不安装第三方软件、不部署、不提交远程仓库。假数据可以但必须说明。请覆盖并发占位、重复提交、取消规则与角色权限。

网络受限或账号缺失时记录 `blocked` / `not-run`，不能编造 GitHub/Gitee 搜索结果、宿主调用或发布成功。

## 五、测试证据分层

运行安装器单元测试：

```bash
python -m unittest discover -s tests -p test_installer.py -v
```

这组测试采用九个临时 fixture，并真实启动独立安装的 fixture Python 脚本；它测试复制与资源相对定位，不替代项目主 CLI 全套验证。五宿主文件布局和 WorkBuddy 字段/ZIP 路径是静态测试。需另用真实技能源生成分发，执行安装后的真实 `usegit.py`，并单独记录各宿主的交互式加载证据。

每条实际宿主检查记录：host、host_version、OS、skill_version、commit、case_id、command_or_prompt、expected、actual、status、evidence_path、timestamp。status 使用 `pass/fail/blocked/not-run`，证据类别使用 `observed/simulated/not-run`。只有运行过的那一层才能标 pass。当前本指南不宣称任何宿主已端到端通过，实际结果以本轮测试报告为准。
