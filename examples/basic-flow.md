# 基本流程（完全虚构）

虚构的字符串清理函数需要正确处理空输入。没有真实项目、运行记录或长期经验。以下为主会话报告信封，内嵌四类角色输出；信封不是第五类角色 Schema。

```text
INIT -> WRITE -> REVIEW -> TEST_GENERATE -> TEST_RUN -> DISCRIMINATE -> pass
```

```json
{
  "iteration": 1,
  "final_status": "pass",
  "writer_output": {
    "changed_files": ["src/clean.py"],
    "implementation_summary": ["增加空输入分支，保持非空行为。"],
    "behavior_changes": ["空字符串得到空字符串。"],
    "risk_notes": ["调用方接口不变。"],
    "test_recommendations": ["覆盖空输入与非空输入。"],
    "needs_review": true
  },
  "reviewer_output": {
    "verdict": "approve",
    "risk_assessment": "low",
    "blocking_findings": [],
    "non_blocking_findings": [],
    "missed_tests": ["验证纯空白输入结果。"],
    "review_confidence": 0.86
  },
  "test_generator_output": {
    "test_strategy": ["行为断言覆盖空、空白与普通字符串。"],
    "tests_added_or_modified": ["tests/test_clean.py"],
    "coverage_notes": ["三个输入分支均有结果断言。"],
    "not_covered": [],
    "test_commands": ["python -m unittest discover -s tests"],
    "qa_scenarios": []
  },
  "test_run": {
    "status": "passed",
    "commands": ["python -m unittest discover -s tests"],
    "exit_codes": [0],
    "summary": "虚构示例：三个行为断言通过。",
    "reason": null
  },
  "discriminator_output": {
    "overall_status": "pass",
    "writer_score": 0.88,
    "reviewer_score": 0.84,
    "test_generator_score": 0.86,
    "discriminator_confidence": 0.86,
    "blocking_issues": [],
    "next_action": null,
    "evidence_summary": ["虚构验收映射：空输入有实现、独立审查和结果断言。"],
    "policy_exceptions": [],
    "memory_proposals": {
      "code-writer": [],
      "code-reviewer": [],
      "code-generate-test": [],
      "discriminator": []
    },
    "memory_not_proposed_reason": "完全虚构示例，不是已验证的真实经验。",
    "reasoning_summary": "示范证据充分、无阻断项时的单轮通过。"
  }
}
```

测试命令仅用于说明虚构报告格式，不声称本仓库包含或实际运行过该函数。完整字段见[架构](../docs/architecture.md)。
