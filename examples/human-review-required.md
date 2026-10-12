# 人工决策（完全虚构）

虚构变更有两种有效的数据保留策略，无法从需求与代码确定应选哪种。用户的决定会改变实现；不能替用户选高风险政策。即使 discriminator 提出 retry target=user，宿主也应转人工，而非开启无意义的下一轮。

```json
{
  "iteration": 1,
  "final_status": "human_review_required",
  "writer_output": {
    "changed_files": [],
    "implementation_summary": [
      "已分析两种数据保留方案，未执行未授权迁移。"
    ],
    "behavior_changes": [],
    "risk_notes": [
      "等待用户决策。"
    ],
    "test_recommendations": [
      "确认策略后生成迁移断言。"
    ],
    "needs_review": true
  },
  "reviewer_output": {
    "verdict": "request_changes",
    "risk_assessment": "high",
    "blocking_findings": [
      {
        "file": "docs/data-policy.md",
        "line": null,
        "severity": "blocker",
        "problem": "缺少数据策略授权。",
        "impact": "不能安全执行迁移。",
        "suggestion": "请用户明确策略。"
      }
    ],
    "non_blocking_findings": [],
    "missed_tests": [
      "授权后验证数据保留与迁移。"
    ],
    "review_confidence": 0.86
  },
  "test_generator_output": {
    "test_strategy": [
      "行为断言覆盖空、空白与普通字符串。"
    ],
    "tests_added_or_modified": [],
    "coverage_notes": [
      "三个输入分支均有结果断言。"
    ],
    "not_covered": [
      "策略未定，无法确定预期结果。"
    ],
    "test_commands": [],
    "qa_scenarios": []
  },
  "test_run": {
    "status": "tests_not_run",
    "commands": [],
    "exit_codes": [],
    "summary": "虚构示例：策略未定，尚未运行迁移验证。",
    "reason": "需用户明确验收和授权，不能执行未授权操作。"
  },
  "discriminator_output": {
    "overall_status": "retry",
    "writer_score": 0.75,
    "reviewer_score": 0.85,
    "test_generator_score": 0.78,
    "discriminator_confidence": 0.83,
    "blocking_issues": [
      {
        "owner": "user",
        "issue": "未授权选择数据保留策略。",
        "required_action": "明确保留策略及允许的迁移范围。"
      }
    ],
    "next_action": {
      "target_agent": "user",
      "instruction": "请明确数据保留策略，并确认允许的迁移范围。"
    },
    "evidence_summary": [
      "虚构示例：代码和现有测试都无法回答产品授权问题。"
    ],
    "policy_exceptions": [],
    "memory_proposals": {
      "code-writer": [],
      "code-reviewer": [],
      "code-generate-test": [],
      "discriminator": []
    },
    "memory_not_proposed_reason": "一次性虚构产品选择，不是长期经验。",
    "reasoning_summary": "目标为 user，主会话暂停并以 human_review_required 结束。"
  }
}
```

也可直接返回 overall_status=human_review_required，但 next_action 仍必须为 user 动作。人工升级优先于三轮耗尽。回答后如继续，应开启有明确验收和授权的新工作流，不自动执行迁移或写 Memory。见[状态映射](../docs/architecture.md)。
