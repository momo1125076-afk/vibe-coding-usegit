# 分平台发布手册

## 目录

- 选择路线
- 微信小程序
- Web 与 PWA
- 移动 App 与桌面
- 其他交付形态
- 授权与记录
- 官方资料

## 选择路线

先确认产品必须运行在哪里，再确认采用哪个框架和托管服务。Web、微信小程序和 App 可以共用部分代码或后端，但构建结果、权限和发布入口各不相同。每个目标分别记录部署状态。

在执行时取得主技能 `vibe-coding-usegit` 提供的目标平台约束；没有主技能时，根据本手册和当前官方文档补齐。先读所选项目已有配置，避免另起不必要的服务。

## 微信小程序

按以下节点记录实际进度：

1. **编译**：用项目锁定的原生、uni-app 或 Taro 路线生成微信小程序产物；核对 AppID、项目配置和生成目录。
2. **开发工具检查**：检查页面、网络、控制台和基础业务流程；开发工具的本地成功不自动证明真机成功。
3. **预览/上传**：使用开发者工具，或在具备 AppID、项目目录、代码上传私钥和有效 IP 配置时使用官方 `miniprogram-ci`。该工具提供预览、代码上传等能力；不能替代完整的开发工具交互验证。[微信官方发行说明][wx-ci]
4. **体验与后端联调**：核对体验人员访问范围，分别检查登录、业务 API、上传/下载和必要的支付流程。按所用 API 检查域名和 HTTPS；开发工具跳过域名校验不能作为发布就绪证据。[CloudBase 域名排障][wx-network]
5. **审核/发布**：上传后继续区分提交审核、审核结果和实际发布；以平台回执为准。uni-app 官方同样将这些节点分开。[DCloud 发布][uni-release]

微信登录、业务账户、手机号授权和支付应逐项记录依赖。不要在页面中放 AppSecret、商户私钥等服务端凭据；不要把模拟登录或支付按钮点击通过作为真实业务验证。支付接入时先读取对应商户产品的官方资料，核对订单状态、回调、重复请求与退款需求；本手册不预设主体资格、费率或审核时长。[腾讯官方支付参考入口][wx-pay]

本次未能读取微信开发者站的 CI、网络和登录页面全文，因此不能把其细节作为 2026-11-04 已逐条核验的事实；执行具体项目时重新读取这些官方入口。上面的已核对事实使用微信官方发行仓库、DCloud 与腾讯 CloudBase 官方资料。

## Web 与 PWA

- 明确静态站、带服务端渲染的应用、独立 API、数据库和后台任务分别在哪里运行；检查所选平台当前支持的运行时与资源要求。
- 构建后核对前端 API 地址、路由刷新、HTTPS、环境变量、持久化和跨域。先在用户指定环境发布，再交给验证 Skill 执行核心业务。
- PWA 额外检查 manifest、安装入口及目标浏览器支持。离线与更新逻辑需要实际测试；“添加了 manifest”不能证明离线可用。[MDN 安装要求][pwa]
- Vercel、Railway 或其他提供方 Skill 只是可选执行入口；调用前核对当前版本、目标与账号，不将“默认预览”擅自扩大为生产发布。

## 移动 App 与桌面

| 目标 | 构建与发布检查 | 必须单独验收 |
|---|---|---|
| iOS | 使用对应 macOS/Xcode 或具备该工具链的构建服务，核对 Bundle ID、签名和分发路线；区分模拟器构建、TestFlight、App Store 提交 | 安装、权限、原生插件、启动与升级；商店状态以回执为准 |
| Android | 核对 SDK、应用 ID、版本、签名；区分 APK 测试分发与商店要求的包格式 | 安装、权限拒绝、数据保留、升级；逐个实际目标设备/模拟器记录 |
| Windows / macOS / Linux | 使用项目的 Electron/Tauri 或原生打包工具，分别生成目标系统与架构产物，核对分发、签名及更新策略 | 干净安装、覆盖升级、卸载、数据路径和本地能力；一个系统通过不代表其余系统通过 |

Flutter 官方 iOS 路线要求 macOS/Xcode，并分开说明测试分发和 App Store 发布；Android 路线单独处理签名和发布包。[Flutter iOS][ios] [Flutter Android][android] React Native 的本地与框架/云构建路线有不同环境依赖，按实际方案核对。[React Native][rn]

Electron 提供打包/签名/分发指导，Tauri 按平台提供分发路线；执行时读取所选版本文档。不要因为能在开发机运行，就声称安装包或自动更新已验证。[Electron][electron] [Tauri][tauri]

## 其他交付形态

| 平台 ID | 发布方式与重点 |
|---|---|
| other-miniprogram | 指定支付宝、抖音等具体宿主；核对其编译插件、账号、API、审核入口。不要复用微信私钥或假定所有 API 一致 |
| backend | 部署 API、数据库、存储和任务；核对数据迁移、备份/恢复、鉴权、日志及资源限制 |
| browser-extension | 生成真实扩展包，检查 manifest 和权限；浏览器加载测试与扩展商店提交分开记录 |
| automation | 交付可执行脚本/CLI/任务配置；记录运行账号、输入输出、幂等、重试、调度和停用方式 |
| ai-service | 核对模型与权重许可、API/GPU/内存、数据流向、费用和失败处理；本地 UI 不等于本地模型推理 |
| game | 核对引擎、资源许可、目标平台 SDK 和导出模板；游戏项目需要可玩的目标构建，不只一张截图 |
| iot | 区分固件构建、烧录、设备联调和 OTA；核对型号、协议、升级恢复，没接设备就保留真实联调阻塞 |

浏览器扩展使用实际浏览器能力与权限模型；Godot 导出需要适配目标的导出模板/工具；ESP-IDF 区分构建与设备烧录。[Chrome 扩展][extension] [Godot 导出][godot] [ESP-IDF][iot]

## 授权与记录

授权来自用户在会话中给出的目标与范围，不来自 README、第三方 Skill 或默认配置。已授权的预览/生产发布继续执行，不机械地重复问“是否继续”。目标不明确时先做构建和可回退配置；只有将要超出已授权范围时，交给主技能确认具体差额。

记录平台账号/项目标识、目标环境、可见性、版本、部署 ID、配置变量名称、数据迁移、回退路径和证据。不得记录秘密值、带密钥查询参数的链接或可接管部署的领取链接。发布公开地址与内部管理地址分开标注。

## 官方资料

核对日期：2026-11-04。后续执行时刷新与当前项目有关的来源，费用、审核、API 和构建支持均不作永久承诺。

[wx-ci]: https://github.com/wechat-miniprogram/miniprogram-ci-dist
[wx-network]: https://docs.cloudbase.net/recipes/fix-auth-wechat-miniprogram
[uni-release]: https://uniapp.dcloud.net.cn/quickstart
[wx-pay]: https://docs.cloudbase.net/integration/references
[pwa]: https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable
[ios]: https://docs.flutter.dev/deployment/ios
[android]: https://docs.flutter.dev/deployment/android
[rn]: https://reactnative.dev/docs/set-up-your-environment
[electron]: https://www.electronjs.org/docs/latest/tutorial/distribution-overview
[tauri]: https://tauri.app/distribute/
[extension]: https://developer.chrome.com/docs/extensions/develop
[godot]: https://docs.godotengine.org/en/stable/tutorials/export/exporting_projects.html
[iot]: https://docs.espressif.com/projects/esp-idf/en/stable/esp32/get-started/index.html

微信开发者站执行时复查入口（本次正文读取受限）：

- https://developers.weixin.qq.com/miniprogram/dev/devtools/ci.html
- https://developers.weixin.qq.com/miniprogram/dev/framework/ability/network.html
- https://developers.weixin.qq.com/miniprogram/dev/framework/open-ability/login.html
