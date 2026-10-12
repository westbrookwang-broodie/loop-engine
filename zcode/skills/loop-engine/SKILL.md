---
name: loop-engine
description: 由 ZCode 宿主协调独立实现、审查、测试生成、测试运行和判别的最多三轮代码工作流。
---

# Loop Engine

## 定位与能力边界

本 Skill 是宿主解释执行的工作流协议，不是独立后台运行时，不自带调度器、数据库、沙箱或 CI。角色隔离是宿主落实的 policy，不是单个 Skill 的技术保证。主会话负责角色调用、工具授权、证据传递、轮数、状态和人工升级；Schema 不代替业务证据审核。

## 角色

- `code-writer`：实现、修复、重构，不自审或最终判定。
- `code-reviewer`：审查真实 diff，不改实现，不替 discriminator 判定。
- `code-generate-test`：生成或规划有效测试，不修业务实现或最终判定。
- `discriminator`：独立评估三类产出与测试证据，不修改前三类产出。

四个 Agent 缺一则停止，说明缺失角色并以 final_status=fail 报告，不能静默兼任。可选 companion skills `code-review`、`test-guide`、`discriminator-rubric` 不随仓库捆绑，也不是硬 import；不可用时按本协议继续。模型、权限、资源刷新与独立上下文由宿主配置。

## 前置检查 INIT

理解任务、验收标准，读取项目指令、相关实现、调用方、现有测试及测试命令。只读取获授权且已批准的稳定 Memory。建立本轮公开范围内的变更证据；无 Git 时使用前后快照或新文件清单。不能读取或外传无关私有信息。

需求不明确或工具风险需用户决定时，直接升级 human_review_required。首次 iteration=1，最大轮数固定为 3；宿主不应通过增加轮数规避本协议。

## 阶段

```text
INIT -> WRITE -> REVIEW -> TEST_GENERATE -> TEST_RUN -> DISCRIMINATE
```

### WRITE

传入任务、验收标准、项目规范、相关代码、已批准 Memory 与前轮反馈。要求 writer 输出 `changed_files/implementation_summary/behavior_changes/risk_notes/test_recommendations/needs_review`；needs_review 必须为 true。writer 摘要不是独立审查证据。

### REVIEW

传入实际变更、任务、writer 输出与稳定 Memory。要求 `verdict/risk_assessment/blocking_findings/non_blocking_findings/missed_tests/review_confidence`。verdict 为 approve/request_changes；存在阻断 finding 必须 request_changes。每个 finding 为 file/line/severity/problem/impact/suggestion。拒绝浅薄或与真实变更无关的 approve；有阻断项仍继续测试生成和证据汇总，不提前宣布 pass。

### TEST_GENERATE

传入需求、真实变更、writer 输出、reviewer finding 和 missed_tests、现有测试及稳定 Memory。要求 `test_strategy/tests_added_or_modified/coverage_notes/not_covered/test_commands/qa_scenarios`。QA 项为 scenario/steps/expected_result/priority。以可观察断言覆盖原缺陷及风险，不削弱有效测试。测试修改形成新证据；如修改业务实现、验收或高风险测试逻辑超出审查范围，discriminator 必须要求回到 WRITE 或 REVIEW，不能直接通过。

### TEST_RUN

由主会话检查建议命令，选择已知且获授权的验证路径。未知、破坏性、联网、长时间或环境敏感命令须先审批，不能自动执行。记录以下宿主证据（不属于四个角色 Schema）：

- `status`：passed/failed/tests_not_run。
- `commands`：实际运行的命令字符串数组；未执行时为空。
- `exit_codes`：与 commands 一一对应的整数数组；未执行时为空。
- `summary`：真实结果、关键断言与局限的非空字符串简述。
- `reason`：未运行或失败的非空字符串原因；passed 时可为 null。

passed 必须有实际命令且全部退出码为 0；failed 必须有实际命令、至少一项非零退出码及明确 reason；tests_not_run 的 commands/exit_codes 都必须为空且 reason 非空。

无法运行要记录 tests_not_run，不把生成测试等同于通过；环境失败也保留 failed 和退出码，不改写成功。原始输出只在获授权上下文中传递，公开报告使用脱敏摘要。

### DISCRIMINATE

传入真实变更、验收映射、前三类完整输出、测试证据、iteration、max_iterations=3 及稳定 Memory。独立评价实现、审查、测试生成和证据，不被 reviewer verdict 绑架。输出字段：

`overall_status/writer_score/reviewer_score/test_generator_score/discriminator_confidence/blocking_issues/next_action/evidence_summary/policy_exceptions/memory_proposals/memory_not_proposed_reason/reasoning_summary`。

blocking_issues 使用 owner/issue/required_action 对象；owner 为 code-writer/code-reviewer/code-generate-test/user。next_action 为 null 或 target_agent/instruction 对象。retry 必须给明确目标和可执行动作；human_review_required 必须 target=user；pass/fail 必须 null。评分范围 0 至 1。

## 默认评分政策

默认 pass 门槛：writer_score >= 0.75、reviewer_score >= 0.75、test_generator_score >= 0.70、discriminator_confidence >= 0.75。若低于门槛仍通过，必须在 policy_exceptions（字符串数组）记录充分证据、理由与剩余低风险，不可无记录例外。

pass 还须满足验收有具体证据、没有 blocking finding/issue、无代码导致测试失败、角色输出质量足够、剩余风险低且明确。仅环境导致未运行或失败时，可以在已确认环境原因、充分替代证据和低风险下考虑 pass；高风险或证据不足升级人工。例外只能豁免评分门槛，不能豁免这些阻断条件。

## Retry 状态转移

一次 retry 消耗下一轮；iteration 每进入新的纠正流程加 1，而不是每个阶段加 1。可复用未变更的输入，但每轮必须产出新的 discriminator verdict。定向重试后所有后续阶段必须重新执行，不允许 REVIEW 直接跳到判停。

```text
retry target=code-writer -> WRITE -> REVIEW -> TEST_GENERATE -> TEST_RUN -> DISCRIMINATE
retry target=code-reviewer -> REVIEW -> TEST_GENERATE -> TEST_RUN -> DISCRIMINATE
retry target=code-generate-test -> TEST_GENERATE -> TEST_RUN -> DISCRIMINATE
retry target=user -> human_review_required
```

选择问题的真正 owner：实现缺陷/验收遗漏给 writer，浅薄或错误审查给 reviewer，弱断言/覆盖缺口给 test-generator，产品选择/授权/不可判断风险给 user。retry 且 blocking_issues 非空时，next_action.target_agent 必须匹配至少一个 blocking owner。向目标角色传递相关 blocking_issues 和 next_action.instruction，不把所有问题推给 writer。

## 判停与最终状态

`overall_status` 仅表示 **iteration verdict**：pass/retry/human_review_required/fail。`final_status` 仅表示 **workflow final status**：pass/human_review_required/fail/max_iterations_reached。不要使用 retry_stopped 或混淆 verdict 与最终状态。

主会话报告信封及 examples 中的每个 JSON envelope 必须完整包含 iteration/final_status/writer_output/reviewer_output/test_generator_output/test_run/discriminator_output。仅非 user 的 retry 且 iteration < 3 时，final_status 显式为 null，表示尚未结束；null 不是终态。不可用空信封或缺失字段绕过证据检查。

主会话按优先级映射：

1. verdict=human_review_required 或 retry target=user：最终 human_review_required，无论剩余轮数。
2. verdict=pass：满足证据与政策后最终 pass。
3. verdict=fail：无法完成或不可继续，最终 fail，不把轮数耗尽伪装成单轮 fail。
4. verdict=retry 且 iteration < 3：按目标转移，开启下一轮。
5. verdict=retry 且 iteration=3（非 user）：最终 max_iterations_reached，不开启第四轮。

有阻断高风险、角色分歧、审批需求或不可验证的非低风险变更时，升级 human_review_required。用户回答后若继续，应新建有明确授权和上下文的工作流，而非私自绕过三轮上限。

## Memory approval

四个角色只读取获授权、用户已批准的稳定经验；临时反馈不自动持久化。discriminator 仅 proposal，不直接写 Memory。主会话展示按四角色分组的全部建议及目标，用户明确确认具体内容后才写入；未确认、沉默、默认同意或仅要求继续工作流都不算 approval。

每个 proposal 为 principle/reason/evidence 字符串对象，只保留经验证且跨任务可复用的原则，不含真实路径、业务信息、凭据或运行记录。有建议时 memory_not_proposed_reason=null；无建议时给出不宜持久化的理由。仓库只发布空 `.example.md` 模板，不自动安装为实际 Memory。

## 最终报告

主会话输出 final_status、iterations、changed_files、三类产出摘要、TEST_RUN 实际证据、最后一次 discriminator 输出、剩余风险以及按角色分组的 memory_proposals。未执行或失败的验证须明说。最终报告不是新的角色 verdict，不得把测试未运行包装成成功。
