# 可选适配器入口

核验日期：2026-11-04。这里列的是可选来源；UseGit 没有自动安装或捆绑它们。使用前再次核对当前文件、版本、许可和实际环境。以下能力依据维护者的官方仓库内容核对，未因此认定它们在当前项目已安装或部署成功。

| 候选 | 类型与用途 | UseGit 对接位置 | 已知边界与官方来源 |
|---|---|---|---|
| ECC `search-first` | 开发前研究现成工具和实现 | 搜索、选型 | 提供研究工作流，执行依赖当前 Agent 的工具。[原始技能](https://github.com/affaan-m/ecc/blob/main/skills/search-first/SKILL.md) |
| ECC `deployment-patterns` | 容器、自动构建发布、健康检查和回滚方法 | 构建与部署 | 具体服务器命令和配置仍需落实。[原始技能](https://github.com/affaan-m/ecc/blob/main/skills/deployment-patterns/SKILL.md) |
| Vercel `deploy-to-vercel` | 将已有应用部署到 Vercel | 构建与部署 | 不承担开源项目选型；接入项目后再核对环境和发布目标。[原始技能](https://github.com/vercel-labs/agent-skills/blob/main/skills/deploy-to-vercel/SKILL.md) |
| GitHub `gh` | 指导 Agent 使用 GitHub CLI | 仓库搜索、读取和操作 | Skill 与 `gh` 可执行工具分别检查。[原始技能](https://github.com/cli/cli/blob/trunk/skills/gh/SKILL.md) |
| GitHub MCP Server | 通过工具接口读取和操作 GitHub | 仓库搜索与协作 | MCP 是连接层，实际能力受工具暴露和账号权限限制。[官方仓库](https://github.com/github/github-mcp-server) |
| Railway `use-railway` | 管理服务、数据库、配置、部署与日志 | 构建与部署 | 需相应服务和账号条件；平台模板搜索不能替代全 GitHub/Gitee 检索。[原始技能](https://github.com/railwayapp/railway-skills/blob/main/plugins/railway/skills/use-railway/SKILL.md) |
| Vercel `find-skills` | 发现和安装 Agent 技能 | 技能发现 | 搜索的是技能，应用选型仍交给项目搜索阶段。[原始技能](https://github.com/vercel-labs/skills/blob/main/skills/find-skills/SKILL.md) |
| 云舒 `github-repo-search` | 按中文需求搜索和比较公开 GitHub 项目 | 仓库搜索 | 默认不含安装实施；已有需求与授权沿用主流程，不重复设置确认门槛。[原始技能](https://github.com/yunshu0909/yunshu_skillshub/blob/master/coding/github-repo-search/SKILL.md) |

只选择解决当前缺口的适配器。已有 GitHub 连接器或 UseGit 搜索脚本能覆盖需求时，无须同时安装 GitHub CLI Skill、GitHub MCP 和另一套搜索 Skill。

Gitee 检索优先使用当前已具备且获准使用的 API、官方页面或 UseGit 的 Gitee 搜索实现；不声称上述 GitHub 专属工具自动支持 Gitee。覆盖范围由实际结果报告说明。
