# 评估输入、评分与输出

`rank_candidates.py` 是离线评分器；不联网、不克隆仓库、不读取引用的证据内容、不替代 agent 的核实。Python 3.10+，仅标准库。

## 命令

```text
python3 scripts/rank_candidates.py --input .usegit/artifacts/repos.json
  --assessments .usegit/artifacts/assessments.json
  --out .usegit/artifacts/comparison.json
```

`--input` 和 `--assessments` 必填；`--out` 默认如上，`-` 输出到 stdout。每个输入文件最大 8 MiB。退出码 `0` 为计算完成，即使没有可推荐项目；`2` 为输入、验证或文件读写错误。报告采用原子写入，不会把无效输入算成成功排名。

候选输入可直接使用搜索报告对象，或 `candidates` 数组。最多 2000 个候选；每个必须具有唯一非空 `id`，`stars` 只能为非负整数或 null。搜索报告的 coverage/errors 会保留到评估报告。

## assessments.json

以下 `github:example/demo` 是**演示 ID，必须替换为实际候选 ID**。模板中的 unknown/null 没有已核实结论。

```json
{
  "hard_requirements": ["license-fit", "platform-fit", "origin-verified"],
  "assessments": [
    {
      "candidate_id": "github:example/demo",
      "note": "填写此方案适用范围与关键限制",
      "hard_checks": {
        "license-fit": {"status": "unknown", "evidence": [], "note": "待读取实际许可文件"},
        "platform-fit": {"status": "unknown", "evidence": [], "note": "待核对目标平台"},
        "origin-verified": {"status": "unknown", "evidence": [], "note": "待核对来源与镜像关系"}
      },
      "scores": {
        "fit": {"score": null, "evidence": [], "note": ""},
        "runnability": {"score": null, "evidence": [], "note": ""},
        "adaptability": {"score": null, "evidence": [], "note": ""},
        "maintenance": {"score": null, "evidence": [], "note": ""},
        "license": {"score": null, "evidence": [], "note": ""},
        "deployment_cost": {"score": null, "evidence": [], "note": ""}
      }
    }
  ]
}
```

硬条件 `license-fit`、`platform-fit` 由脚本自动纳入；声明列表可增加约束，不能去掉这两项。`hard_checks` 只允许已声明 ID，状态为 `pass|fail|unknown`。无证据的 pass/fail 降为 unknown。未填写的检查保持 unknown。每个候选最多一条 assessment，引用不存在候选、重复 ID、未知维度或非法分数都报错。

`evidence` 是最多 30 个引用组成的数组，允许公开 HTTP(S) URL 或项目相对路径，例如 `.usegit/artifacts/repo-review.md#license`。不允许 URL 用户名/密码、token 类查询参数、绝对路径、上级路径跳转或其他协议。引用存在不代表内容已经由脚本验证；agent 必须读取并确保足以支撑对应结论。`note` 说明证据为何支持评分和适用范围。

## 固定权重与分数锚点

权重：`fit=30`，`runnability=20`，`adaptability=15`，`maintenance=15`，`license=10`，`deployment_cost=10`。分数 0–5，可为有限小数。布尔值、NaN/Infinity、越界分数无效。

| 分数 | 共通解释 | 评分使用要求 |
| ---: | --- | --- |
| null | 尚未核实 | 保留问题及补证动作，不赋中间分 |
| 0 | 明确不满足该维度 | 必须有失败或缺失能力的证据 |
| 1 | 严重缺口 | 改造/修复成本明显，说明所缺内容 |
| 2 | 部分可用 | 存在影响核心目标的已知缺口 |
| 3 | 基本可用 | 主要目标已有依据，需有限调整 |
| 4 | 很适合 | 核心流程、边界与成本有充分支撑 |
| 5 | 高度吻合且充分验证 | 可运行性 5 分须有当前环境实际运行证据 |

每个维度仍需独立说明：维护看发布、修复和兼容性，不仅看最后 commit；部署成本看所需资源、第三方服务和长期维护；许可证维度看具体复用方式，而非“有 LICENSE 就满分”。尚未实际运行时可按安装文档、依赖锁定、CI 等已读证据评价准备程度，但必须说明推断和未运行范围。

每项贡献 `score / 5 × weight`，加总满分 100。没有分数或没有证据的维度会变成 null、贡献 0 并标记缺失；**不按其余维度重新归一化**。`evidence_coverage_weight` 为有效评分已覆盖的权重，仅描述输入完整度，不是证据真实性保证。

## 分类和输出

有证据的任何硬条件 fail → `excluded`；否则任何硬条件 unknown 或评分缺失 → `needs_review`；否则 → `ranked`。排除条件优先，不允许高总分覆盖硬条件失败。

各分类内按总分降序、证据覆盖权重降序、star 降序、候选 ID 不区分大小写升序稳定排序。star 为 null 排在已知值之后，只用于同分参考。

输出字段：`schema_version`、`report_type: candidate-comparison`、`stage: evaluate`、`evaluated_at`、`weights`、`score_scale`、`hard_requirements`、`ranked`、`needs_review`、`excluded`、`counts`、`search_coverage`、`source_errors`、`notes`。

每行包含原始 `candidate`、`score_total`、`evidence_coverage_weight`、正规化的 `scores` / `hard_checks`、`failed_requirements`、`unresolved_requirements`、`missing_scores`、`classification`、`assessment_note` 与 `position_within_category`。

原始报告不是主技能的阶段完成记录。应另写 `evaluate.json`，引用比较报告作为 output，并按调度技能契约登记已验证证据、仍未解决的问题和实际动作。计算成功并不意味着许可已批准、代码已运行或部署已授权。

## 给客户的决策说明

至少写明：推荐的方案及适用场景，最重要的备选，核心需求匹配与缺口，预计改造范围，运行与部署限制，费用估计依据，来源/版本/许可，未核实项及搜索覆盖。没有符合硬条件的候选时，报告真实原因和组件组合/自建选项，不强行选出最高星项目。
