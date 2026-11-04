# 首次运行手册

## 先看什么

| 线索 | 要确认的内容 |
|---|---|
| package.json 与锁文件 | 实际包管理器、引擎版本、安装钩子、开发与构建脚本 |
| pyproject.toml / requirements / lock | Python 版本、依赖来源、是否需要模型或本地编译 |
| compose.yaml / Dockerfile | 服务数量、卷、端口、默认账户、启动时是否执行迁移 |
| manifest.json / pages.json / project.config.json | 是否为 uni-app 或小程序，实际 AppID、编译产物目录 |
| pubspec.yaml / android / ios | Flutter 或移动原生依赖、SDK、模拟器、签名需求 |
| tauri.conf / electron / forge 配置 | 桌面目标、原生依赖、打包工具与更新服务 |
| project.godot / sdkconfig / platformio.ini | 游戏引擎版本、导出模板，或硬件型号、芯片与工具链 |

命令必须来自已读取的项目脚本和当前官方文档。不要把表中的文件名当作所有项目都有的约定。

## 最小运行记录

记录源码来源、选中 ref、完整 commit、工作目录、OS/架构、依赖版本、已执行命令、退出码、就绪条件、日志、测试数据及实际结果。服务命令尚在运行时不要伪造退出码；用日志与健康请求记录就绪结果。

先确认“原项目按原样能运行”，再单独记录为了适配环境做的改动。必要的迁移使用可恢复的测试数据库。若必须调用有费用的模型或第三方 API，检查当前授权的额度与目标，缺失时先完成不产生费用的工作。

## 平台环境边界

- uni-app CLI 的 `build:app-plus` 生成 App 打包资源，不直接证明已经得到可安装的 iOS/Android 包；以具体仓库版本和打包方式为准。[DCloud CLI](https://uniapp.dcloud.net.cn/quickstart-cli)
- Taro 把代码编译为指定端产物，然后交给对应平台工具运行；读取项目实际脚本，不混用 H5 与小程序目标。[Taro 安装及使用](https://docs.taro.zone/docs/GETTING-STARTED)
- Flutter 的 iOS 构建发布路径需要 macOS 与 Xcode；仅有 Linux 环境时，准备源码和可执行验证计划，说明所需 macOS 构建环境。[Flutter iOS](https://docs.flutter.dev/deployment/ios)
- React Native 的本地原生开发依赖 Android Studio/Xcode；框架或云构建可能承担部分环境，必须核对所选路线，不一概要求本机安装所有工具。[React Native 环境](https://reactnative.dev/docs/set-up-your-environment)
- ESP-IDF 的流程区分配置、构建、烧录和监视；没有连接真实开发板时只能报告相应软件验证。[ESP-IDF 入门](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/get-started/index.html)

以上资料核对日期：2026-11-04。实际执行时使用与项目锁定版本匹配的官方文档，不把文档示例的版本号当成项目要求。
