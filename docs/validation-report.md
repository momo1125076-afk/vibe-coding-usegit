# 验证报告

日期：2026-11-04。对象：dot Linux 云工作区重建版，版本 0.2.0-rebuild。Python 3.12.14。源码提交以仓库实际提交为准；本报告不沿用旧工程的 76 项测试记录。

## 本轮真实结果

| 检查 | 结果 | 范围与证据 |
|---|---|---|
| 自动化单测 | 118 / 118 通过 | 工作流58、安装器36、搜索11、评分13；[完整日志](../evidence/unittest.log) |
| 九技能格式 | 9 / 9 通过 | 使用当前 skill-creator quick_validate；[日志](../evidence/skill-format.log)，不是行为证明 |
| 五宿主分发+独立脚本 | 30 / 30 通过 | 每宿主安装/包生成、help、完整init、doctor、status、template；[报告](../evidence/distribution-smoke.json) |
| 独立前向演练复测 | 10 / 10 命令成功 | 微信预约规划生成13份产物，5个需求；[说明](../examples/miniprogram-plan/README.md) |
| 示例快照重放 | 7 / 7 命令成功 | 新临时项目正常登记，blocked状态正确保留；[记录](../evidence/example-replay.json) |
| GitHub连接器查询 | 成功返回3个公开仓库 | [脱敏记录](../evidence/github-connector-search.json)；未核实候选许可/小程序支持/运行情况 |
| 搜索脚本真实API请求 | 未通过 | GitHub和Gitee均 network_error，脚本返回1并保留真实错误；[报告](../evidence/live-search.json) |
| Codex宿主实际启动 | blocked | CLI 0.166.0-alpha.1 初始化app-server遇只读文件系统，退出1；[日志](../evidence/codex-host-startup.log) |
| 其他四宿主实际调用 | not-run | 未发现对应可执行程序，没有UI会话测试；[环境记录](../evidence/host-runtime.json) |

**五宿主目前证明到文件分发和独立Python运行，不是五宿主模型端到端兼容认证。** WorkBuddy ZIP未导入UI或提交市场；Windows/macOS原生文件系统未实测。各产品平台的微信真机、支付、iOS签名、商店审核、正式发布均未执行。

## 独立演练与代码复审发现并修复

- 原技能入口未同步脚本：增加同步工具与逐字节分发检查。
- init缺少文档使用的 name/idea/platform 参数：已实现并用完整命令回归。
- 错把整个 .usegit 目录当禁止路径：允许 artifacts/evidence，继续禁止状态控制文件和越界链接。
- 工程工具与技能副本短暂漂移：独立复测后两者一致，分发检查将继续阻止旧副本发布。
- 复审修正连接器部署证据、多条同需求验收、URL秘密查询参数的校验。
- 独立代码审查另修复评分引用 authorization 泄露风险、无效仓库 URL 丢失部分结果、错误顶层输入退出码和输入有界读取；新增回归。

示例最终 discover/find-skills complete、find-repos/evaluate blocked、complete_for_mode=false。CLI命令成功不能把尚未搜索和比较的plan变成完成，更不是预约软件已经构建成功。

## 复现

在仓库根目录使用Python3.10+：

```sh
python3 -m unittest discover -s tests -v
python3 tools/check_distribution.py
python3 -m compileall -q tools skills
python3 tools/smoke_distributions.py --out /tmp/distribution-smoke.json
python3 tools/replay_example.py
```

搜索真实联调（需要对应网络可达；可选凭据经安全环境注入，不写日志）：

```sh
python3 tools/search_repos.py --provider both --query 'appointment booking' --limit 3 --max-pages 1 --page-size 5 --timeout 5 --out /tmp/live-search.json
```

单元测试对网络传输使用替身；替身通过只证明分支处理，不代表真实API联通。smoke使用临时目录与测试作者标记，WorkBuddy产物不会上传。格式验证器是构建环境的辅助工具，不作为使用本项目的安装依赖。

## 待完成与发布状态

真实五宿主加载、联网搜索、目标平台构建与业务测试需要在具备对应工具/账号/设备的环境补测。GitHub CI配置已经提供，但其远程运行结果只能在实际推送后确认，不能用本地测试代替。仓库创建、远端提交和CI的最终状态由交付消息附上准确链接与结果。
