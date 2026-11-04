# 搜索报告契约

这是 `search_repos.py` 的原始数据协议，不是 UseGit 的阶段完成协议。输出中的 `stage: find-repos` 仅标注所属阶段。

## 命令

```text
python3 scripts/search_repos.py --provider both --query TEXT [--query TEXT ...]
  [--limit 20] [--min-stars 0] [--max-pages 3] [--page-size 50]
  [--timeout 10] [--include-archived] [--out .usegit/artifacts/repos.json]
```

| 参数 | 含义与范围 |
| --- | --- |
| `--provider` | `github`、`gitee`、`both`，默认 `both` |
| `--query` | 可重复 1–8 次，每个 1–256 个字符；去除完全相同的查询 |
| `--limit` | 每个提供方、每个查询最多接收的不同候选数，1–100 |
| `--min-stars` | 非负整数；大于 0 时过滤未知或不足的 star 数 |
| `--max-pages` | 每个提供方、每个查询最多页数，1–10 |
| `--page-size` | 每页请求数量，1–100 |
| `--timeout` | 单次请求网络超时秒数，大于 0 且不超过 30 |
| `--include-archived` | 纳入明确归档的仓库；缺失归档状态始终保留未知 |
| `--out` | JSON 文件路径；`-` 表示 stdout，默认位于 `.usegit/artifacts/` |

Python 3.10+，仅标准库。保存采用同目录临时文件与原子替换。退出码 `0` 为请求按边界正常结束（可能没有候选）；`1` 为部分覆盖、跳过或错误，JSON 仍保存；`2` 为参数或读写错误。

## 顶层输出

```json
{
  "schema_version": 1,
  "report_type": "repository-discovery",
  "stage": "find-repos",
  "retrieved_at": "RFC3339 UTC",
  "queries": ["原始检索词"],
  "parameters": {},
  "coverage": [],
  "errors": [],
  "candidates": [],
  "notes": [],
  "coverage_complete": false
}
```

`coverage_complete` 表示此次有界请求没有被标记为 partial/error/skipped，**不代表全站穷尽**。达到候选 `limit` 可正常结束；达到页数预算而还可能有结果则标为 `partial`。要看全量条件还需检查每个 coverage 的 `exhaustive` 和 `stop_reason`。

## 候选字段

每个候选都含以下固定字段。未知字段保留 `null`，不补造零、false 或当前时间。

| 字段 | 类型与含义 |
| --- | --- |
| `id` | `github:owner/repo` 或 `gitee:owner/repo`，从规范仓库 URL 得到 |
| `provider` | `github` 或 `gitee` |
| `full_name` | 规范路径的 `owner/repo`，不是 Gitee 显示名 |
| `url` | 对应平台 HTTPS 仓库地址，不含认证、查询参数或 fragment |
| `description` | 字符串或 null |
| `stars`、`forks` | 非负整数或 null |
| `archived` | 布尔值或 null |
| `license` | `{spdx_id,name,key,url}` 或 null；API 标签不是许可审核 |
| `language` | 字符串或 null |
| `pushed_at` | 提供方给出的最近推送时间或 null，不用更新时间冒充 |
| `source_api` | 首次观察到此候选的 API 页地址，已移除凭据 |
| `retrieved_at` | 本次检索 UTC 时间 |

另有 `provider_repository_id`、`is_fork`、`mirror_url`、`upstream_url`、`origin_status`、`metadata_warnings` 和 `matched_queries`。`origin_status` 为 `fork`、`mirror` 或 `unverified`，不根据缺少镜像字段推断原创。跨平台镜像暂时分别保留并待核实；不得当作独立方案累计星数。同提供方同规范 ID 跨查询合并，`matched_queries` 保留命中的查询。

许可 `NOASSERTION` / unknown 不当作开源许可；纯文本许可标签只记名称，不自行伪造 SPDX 标识。必须阅读实际 LICENSE 才能得出复用结论。公开、但许可未知的仓库仍可成为待核实线索。

## 覆盖与错误

`coverage[]` 每个提供方/查询一项，包含：

- `provider`、`query`、`status`（`ok|empty|partial|error|skipped`）。
- `pages_requested`、`raw_items`、`accepted_items`、`filtered_items`、`invalid_items`。
- `total_count`、`exhaustive`、`incomplete_results`、`stop_reason`。
- `source_urls`（不含 token）、`authenticated`（仅布尔值）、可用时的 `rate_limit`。

GitHub 明确的 `total_count` 优先于短页启发式。`incomplete_results=true` 即使有候选也必须为 partial。Gitee 数组响应没有本适配器可核实的总数，因此 `exhaustive` 始终为 false；空数组只证明接口此次返回空，不证明网站没有适合项目。

`errors[]` 包含 `provider/query/page/code/message/http_status/retry_after_seconds`。认证、403、429、网络与服务错误不会被吞成空数组。部分成功的候选保留；同提供方遇到广泛认证/限流/网络问题后跳过剩余查询，另一个提供方可继续。未自动重试，避免扩大限流。

## 网络和凭据边界

固定端点：`https://api.github.com/search/repositories` 与 `https://gitee.com/api/v5/search/repositories`。默认匿名；`GH_TOKEN` 优先于 `GITHUB_TOKEN`，只发往 GitHub Authorization header；`GITEE_TOKEN` 只用于 Gitee 官方端点实际请求的 `access_token` 参数。输出来源 URL 单独构造，不包含认证值。

不读取本机个人凭据文件，不将请求对象、响应正文、原始网络异常或 token 打印到报告。不跟随任何 HTTP 重定向；该限制宁可返回可见的 `redirect_blocked`，也不把凭据转发给新主机。单响应最多 2 MiB，限制页数和请求时间；保持环境的代理与 TLS 校验，不绕过网络访问规则。不下载、安装、运行或部署候选项目。
