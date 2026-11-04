# 外部工具适配

先复用宿主已有工具。这个项目不绑定某一模型、付费平台或 MCP。以下是选配路线，正式使用时重新核对当前官方文档与许可。

| 缺口 | 首选入口 | 接入边界 |
|---|---|---|
| GitHub 项目与源码 | 宿主 GitHub 插件、GitHub CLI 或官方 MCP | 搜索和读仓库需要真实结果；不在日志写 token |
| Gitee 项目 | Gitee 官方 API/官方网页 | API受限时说明覆盖不足，保留检索式；不要声称零结果就是没有项目 |
| Skill 查找 | 已安装技能清单，然后 Skills CLI/官方仓库 | find-skills 找技能，find-repos 找软件项目，不能混为同一结果 |
| 现成方案优先 | ECC search-first | 采用搜索与评估方法；不把上游全文复制进本项目 |
| Web 预览部署 | 当前已连接发布平台；可选 Vercel deploy-to-vercel | 从已有可构建项目开始，返回实际版本与地址 |
| 服务/数据库部署 | 已有服务器/容器环境；可选 Railway use-railway | 根据目标环境选择，先确认当前预算和已有授权 |
| 微信小程序 | 微信开发者工具/miniprogram-ci | 预览、上传、提交审核、发布分别核实，不等同 Web 部署 |

官方入口（2026-11-04 核对）：

- https://github.com/affaan-m/ECC
- https://github.com/vercel-labs/skills
- https://github.com/vercel-labs/agent-skills
- https://github.com/cli/cli
- https://cli.github.com/manual/gh_search_repos
- https://github.com/github/github-mcp-server
- https://gitee.com/api/v5/swagger
- https://github.com/railwayapp/railway-skills
- https://github.com/yunshu0909/yunshu_skillshub

安装第三方技能前读其当前 SKILL.md 与脚本；记录来源、版本/提交、许可证、依赖、可操作范围。优先按单技能和项目范围安装，避免一个任务引入整套不相关全局规则。

网络或账号不足时，继续能完成的方案、代码和本地验证。工具覆盖表需记录 unavailable/untested/ready（有真实探测证据），不要因环境变量存在就认定登录或网络可用。
