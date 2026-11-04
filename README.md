# Vibe Coding UseGit

把一句产品想法推进到需求、开源选型、运行、改造、部署与验收的九技能工作流。兼容目标：Codex、Claude Code（CC）、DeepSeek Harness、OpenClaw、WorkBuddy。

这是 2026-11-04 在 dot 云工作区**重新构建**的版本。技能正文与参考来自用户已有九个云技能；运行脚本、安装工具和测试重新实现。没有恢复旧工程或旧 Git 历史，也不沿用旧“76 项通过”的结论。实际结果见 [验证报告](docs/validation-report.md)。

**它不是后台自动运行服务。** Skill 提供工作方法，Python CLI 管理状态和证据；搜索、编码与发布依赖当前 Agent 的工具、网络、账号和用户授权。静态包检查不等于五宿主端到端认证。

## 快速开始

要求 Python 3.10+；辅助工具只用标准库。无需预先购买 API 或安装所有第三方平台。

```sh
python3 tools/usegit.py doctor
python3 tools/usegit.py init --project /path/to/customer-project --name booking --idea '微信预约与网页后台，首版不支付' --platform wechat-miniprogram --platform web --platform backend --mode plan
python3 tools/usegit.py next --project /path/to/customer-project
```

安装前查看计划，再在选择的测试项目中应用：

```sh
python3 tools/install_skills.py --host codex --project /path/to/workspace --source skills
python3 tools/install_skills.py --host codex --project /path/to/workspace --source skills --apply
```

五宿主的准确路径、WorkBuddy ZIP、更新和卸载见 [宿主兼容与安装](docs/host-compatibility.md)。

在 Agent 中说：

> 使用 vibe-coding-usegit。我要做一个微信场地预约小程序和网页管理后台，第一版不支付。先理清需求、寻找 GitHub/Gitee 项目、比较方案，只做 plan。已有信息直接用，需要决定的问题集中问我。

## 技能分工

| 技能 | 结果 |
|---|---|
| vibe-coding-usegit | 依赖调度、恢复进度、证据与授权记录 |
| usegit-discover | 需求编号、MVP、验收条件 |
| usegit-find-skills | 已有工具、缺口与最小接入方案 |
| usegit-find-repos | GitHub/Gitee 候选、查询覆盖和错误 |
| usegit-evaluate | 硬条件和六维比较、选型理由 |
| usegit-run | 固定版本首次运行证据 |
| usegit-adapt | 需求映射、修改与回归 |
| usegit-deploy | 构建、部署回执、回滚与发布阶段 |
| usegit-verify | 必需需求逐项真实验证和交付 |

## 交付模式与平台

- plan：到比较与实施方案，不代表软件已运行。
- local（默认）：运行、改造、验收，不强制云部署。
- preview：授权预览并验证。
- release：授权发布并验证，外部审核未完成不得声称上架。

Web/PWA、微信与其他小程序、iOS/Android、桌面、后端、扩展、自动化、AI、游戏、IoT 的路线见 [平台路线](skills/vibe-coding-usegit/references/platforms.md)。有路线不代表对应平台已实测。支付、签名、设备、审核与生产账号需要对应条件。

## 文档

- [完整操作说明](docs/operator-guide.md)
- [五宿主安装、调用与已测边界](docs/host-compatibility.md)
- [状态与证据契约](skills/vibe-coding-usegit/references/orchestration.md)
- [可选工具目录](skills/vibe-coding-usegit/references/tool-adapters.md)
- [验证报告与复现命令](docs/validation-report.md)
- [来源、安全与维护](docs/provenance-and-security.md)

## 开发与验证

```sh
python3 tools/sync_skill_scripts.py
python3 -m unittest discover -s tests -v
python3 tools/check_distribution.py
python3 -m compileall -q tools skills
```

修改 tools 下的公共脚本后必须同步到独立技能包。提交前排除 .env、凭据、客户运行记录和无关文件。本仓库经用户授权公开，但尚未指定软件许可证，公开可读不自动授予修改或再分发许可。可选第三方依赖受各自许可证约束。
