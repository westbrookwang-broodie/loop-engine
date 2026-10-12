# 测试未运行（完全虚构）

虚构任务仅调整说明文本，已核对实际变更无执行逻辑修改，但已确认当前环境没有项目测试工具。即使低风险也不能把未运行标成 passed。此例展示低于评分阈值时记录的政策例外，不代表通用的跳过测试许可。

```json
{
  "iteration": 1,
  "final_status": "pass",
  "writer_output": {
    "changed_files": [
      "docs/usage.md"
    ],
    "implementation_summary": [
      "澄清使用说明。"
    ],
    "behavior_changes": [],
    "risk_notes": [
      "仅说明文本变更。"
    ],
    "test_recommendations": [
      "人工核对文本与链接。"
    ],
    "needs_review": true
  },
  "reviewer_output": {
    "verdict": "approve",
    "risk_assessment": "low",
    "blocking_findings": [],
    "non_blocking_findings": [],
    "missed_tests": [],
    "review_confidence": 0.85
  },
  "test_generator_output": {
    "test_strategy": [
      "逐项人工核对文本及链接。"
    ],
    "tests_added_or_modified": [],
    "coverage_notes": [
      "人工核对说明文本。"
    ],
    "not_covered": [
      "未运行项目测试工具。"
    ],
    "test_commands": [],
    "qa_scenarios": [
      {
        "scenario": "说明文本与链接",
        "steps": [
          "核对说明与现有接口一致。",
          "逐个确认链接目标。"
        ],
        "expected_result": "说明无矛盾且链接存在。",
        "priority": "P1"
      }
    ]
  },
  "test_run": {
    "status": "tests_not_run",
    "commands": [],
    "exit_codes": [],
    "summary": "虚构示例：仅人工核对文本与链接，没有执行测试。",
    "reason": "已确认环境缺少项目测试工具；变更仅为说明文本。"
  },
  "discriminator_output": {
    "overall_status": "pass",
    "writer_score": 0.85,
    "reviewer_score": 0.85,
    "test_generator_score": 0.68,
    "discriminator_confidence": 0.82,
    "blocking_issues": [],
    "next_action": null,
    "evidence_summary": [
      "虚构验收映射：逐项人工核对说明文本及链接，无执行逻辑变更。"
    ],
    "policy_exceptions": [
      "test_generator_score 低于 0.70；变更纯文本，人工逐项核对提供替代证据，剩余风险低，明确保留 tests_not_run。"
    ],
    "memory_proposals": {
      "code-writer": [],
      "code-reviewer": [],
      "code-generate-test": [],
      "discriminator": []
    },
    "memory_not_proposed_reason": "完全虚构示例，不据此推广跳过验证的经验。",
    "reasoning_summary": "仅示范有充分替代证据与明确低风险时的记录例外。"
  }
}
```

如果缺少替代证据或涉及安全、数据等高风险，应该 human_review_required，而不是以环境不可用掩盖失败。测试确实运行失败时必须记录 failed 与真实退出码。见[人工升级示例](human-review-required.md)。
