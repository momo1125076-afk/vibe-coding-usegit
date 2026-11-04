# 方法与证据来源

核对日期：2026-11-04。固定六维权重、硬条件和分类规则由 UseGit 设计，属于可调整前先明确记录的产品方法，不是 GitHub、Gitee 或任何许可证机构的官方评分。

## 应优先阅读的证据

1. 用户确认的需求简报、必要功能与部署约束。
2. 候选仓库中的实际 LICENSE、README、安装配置、依赖清单与目标平台代码；记录 URL 和已知提交或版本。
3. 项目官方发布记录、迁移说明与 issue/PR 中与当前需求直接相关的证据。
4. 当前环境实际命令与退出码、日志、页面或 API 验证结果；未运行时保留“未运行”。

## 官方参考

- [GitHub REST 仓库搜索](https://docs.github.com/en/rest/search/search#search-repositories)：候选和搜索覆盖的数据基础，不能证明功能适配。
- [GitHub REST 许可证说明](https://docs.github.com/en/rest/licenses/licenses#about-licenses)：自动识别字段只提供线索，未知字段不能推断为可复用许可。
- [Gitee API v5](https://gitee.com/api/v5/swagger)：官方入口。缺失许可或其他元数据时，回到实际仓库文件核实。

评分器仅校验输入格式、引用形式、权重计算及分类规则。测试使用模拟候选和证据，不构成任何真实项目的质量背书；它不会在线读取或审计 evidence 引用。
