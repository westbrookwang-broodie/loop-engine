# 重试 reviewer（完全虚构）

假定实现和测试可用，但审查只复述 writer，没有检查错误分支。纠正的是审查质量，不要求 writer 无关重写。

```text
iteration 1: WRITE -> REVIEW -> TEST_GENERATE -> TEST_RUN -> DISCRIMINATE
iteration 2: REVIEW -> TEST_GENERATE -> TEST_RUN -> DISCRIMINATE
iteration 3: REVIEW -> TEST_GENERATE -> TEST_RUN -> DISCRIMINATE
```

第二、三轮必须继续所有后续阶段。下列为第三轮仍浅薄的虚构报告；单轮 overall_status=retry，最终 final_status=max_iterations_reached，不开启第四轮。

```json
{
  "iteration": 3,
  "final_status": "max_iterations_reached",
  "writer_output": {
    "changed_files": [
      "src/clean.py"
    ],
    "implementation_summary": [
      "增加空输入分支，保持非空行为。"
    ],
    "behavior_changes": [
      "空字符串得到空字符串。"
    ],
    "risk_notes": [
      "调用方接口不变。"
    ],
    "test_recommendations": [
      "覆盖空输入与非空输入。"
    ],
    "needs_review": true
  },
  "reviewer_output": {
    "verdict": "approve",
    "risk_assessment": "low",
    "blocking_findings": [],
    "non_blocking_findings": [],
    "missed_tests": [],
    "review_confidence": 0.58
  },
  "test_generator_output": {
    "test_strategy": [
      "行为断言覆盖空、空白与普通字符串。"
    ],
    "tests_added_or_modified": [
      "tests/test_clean.py"
    ],
    "coverage_notes": [
      "三个输入分支均有结果断言。"
    ],
    "not_covered": [],
    "test_commands": [
      "python -m unittest discover -s tests"
    ],
    "qa_scenarios": []
  },
  "test_run": {
    "status": "passed",
    "commands": [
      "python -m unittest discover -s tests"
    ],
    "exit_codes": [
      0
    ],
    "summary": "虚构示例：行为测试通过，但独立审查证据不足。",
    "reason": null
  },
  "discriminator_output": {
    "overall_status": "retry",
    "writer_score": 0.84,
    "reviewer_score": 0.58,
    "test_generator_score": 0.8,
    "discriminator_confidence": 0.87,
    "blocking_issues": [
      {
        "owner": "code-reviewer",
        "issue": "未核对错误分支的真实变更。",
        "required_action": "读取具体 diff，并说明错误分支风险及对应测试缺口。"
      }
    ],
    "next_action": {
      "target_agent": "code-reviewer",
      "instruction": "审查真实变更中的错误分支，不复述 writer 摘要。"
    },
    "evidence_summary": [
      "虚构示例：现有测试结果不能补偿缺失的独立审查。"
    ],
    "policy_exceptions": [],
    "memory_proposals": {
      "code-writer": [],
      "code-reviewer": [],
      "code-generate-test": [],
      "discriminator": []
    },
    "memory_not_proposed_reason": "完全虚构示例，没有经过验证的长期原则。",
    "reasoning_summary": "审查未达质量要求，但三轮已耗尽；保留 retry verdict 并终止工作流。"
  }
}
```

若同样输出在第一轮出现，宿主只增加一次轮数并从 REVIEW 开始，完整 envelope 的 final_status 必须显式为 null，表示进行中而非终态。若 target=user，则即使第三轮也应优先 human_review_required。见[主协议](../zcode/skills/loop-engine/SKILL.md)。
