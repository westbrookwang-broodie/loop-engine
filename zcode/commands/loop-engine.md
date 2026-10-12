---
description: 在 ZCode 宿主中以最多三轮独立角色执行 Loop Engine 代码质量工作流。
argument-hint: "<任务与验收标准>"
---

# Loop Engine 命令入口

用户任务：

```text
$ARGUMENTS
```

宿主应加载已安装的 `loop-engine` Skill 并遵循其完整协议。本命令不启动独立后台运行时，不自带调度器、数据库、沙箱或 CI；角色隔离为宿主落实的 policy。

## 前置检查

读取任务、验收标准、项目指令、相关代码、现有测试和已批准 Memory。确认 code-writer/code-reviewer/code-generate-test/discriminator 可用，缺失则停止并解释。可选 companion skills code-review/test-guide/discriminator-rubric 不捆绑，不是硬 import，缺少时不跳过角色。

## 执行阶段

```text
INIT -> WRITE -> REVIEW -> TEST_GENERATE -> TEST_RUN -> DISCRIMINATE
```

1. WRITE 由 code-writer 实现，输出 changed_files/implementation_summary/behavior_changes/risk_notes/test_recommendations/needs_review。
2. REVIEW 由 code-reviewer 审查实际变更，输出 verdict/risk_assessment/blocking_findings/non_blocking_findings/missed_tests/review_confidence。
3. TEST_GENERATE 由 code-generate-test 生成测试或 QA，输出 test_strategy/tests_added_or_modified/coverage_notes/not_covered/test_commands/qa_scenarios。
4. TEST_RUN 由主会话仅运行安全、已知且获授权的命令，记录 status（passed/failed/tests_not_run）、commands、exit_codes、summary、reason。未执行不伪造成功。
5. DISCRIMINATE 独立评估证据，输出 overall_status/writer_score/reviewer_score/test_generator_score/discriminator_confidence/blocking_issues/next_action/evidence_summary/policy_exceptions/memory_proposals/memory_not_proposed_reason/reasoning_summary。

TEST_RUN 的 summary 必须为非空字符串；passed 要求命令非空且退出码全 0；failed 要求命令非空、至少一项非 0 及非空 reason；tests_not_run 要求命令/退出码均空及非空 reason。

blocking_issues 为 owner/issue/required_action 对象数组，owner 为 code-writer/code-reviewer/code-generate-test/user。next_action 为 target_agent/instruction 对象或 null；retry 必须给明确动作，且存在 blocking_issues 时 target_agent 必须匹配至少一个 owner；human_review_required 必须 target=user，pass/fail 为 null。

## Retry 与判停

iteration 从 1 开始，最多三轮。每次 retry 消耗下一轮；定向阶段结束后继续所有后续阶段。

```text
retry target=code-writer -> WRITE -> REVIEW -> TEST_GENERATE -> TEST_RUN -> DISCRIMINATE
retry target=code-reviewer -> REVIEW -> TEST_GENERATE -> TEST_RUN -> DISCRIMINATE
retry target=code-generate-test -> TEST_GENERATE -> TEST_RUN -> DISCRIMINATE
retry target=user -> human_review_required
```

iteration verdict `overall_status` 为 pass/retry/human_review_required/fail；workflow final status `final_status` 为 pass/human_review_required/fail/max_iterations_reached。user 目标优先升级人工；第三轮非 user 的 retry 映射 max_iterations_reached，不开启第四轮。无法完成为 fail，不混同耗尽轮数。

每个主会话报告信封和 examples JSON envelope 必须包含 iteration/final_status/writer_output/reviewer_output/test_generator_output/test_run/discriminator_output。非 user 的 retry 且 iteration < 3 时 final_status 必须显式为 null，表示进行中；其他情况按状态映射填写，不省略字段。

默认门槛 writer_score >= 0.75、reviewer_score >= 0.75、test_generator_score >= 0.70、discriminator_confidence >= 0.75。允许 policy_exceptions 记录有证据的低风险评分例外；不能豁免阻断发现、验收遗漏、代码导致的失败或高风险未决事项。不要因 reviewer approve 或测试文件存在而直接 pass。

## Memory approval

discriminator 仅 proposal；主会话展示 memory_proposals，用户明确确认具体建议与目标后才写入。未确认不写，临时反馈不自动成为长期 Memory。

## 最终输出

报告 final_status、iterations（N/3）、changed_files、实际测试命令与 passed/failed/tests_not_run、实现摘要、审查摘要、测试摘要、最后一次 discriminator 输出、剩余风险及按四个角色分组的 Memory 建议。不宣称未执行的测试通过。
