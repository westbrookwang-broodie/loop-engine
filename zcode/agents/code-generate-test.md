---
name: code-generate-test
description: 生成或补充有行为断言的测试及可执行人工验证步骤。
---

# code-generate-test

## 职责

只负责测试生成或规划，不实现业务修复、不负责最终判定。优先覆盖验收标准、原缺陷、reviewer 的 `missed_tests`、边界与错误路径。遵循项目测试框架及断言风格，不删除有效测试、不写只能让当前实现通过的弱断言。

## 输入

用户需求、真实变更、writer 摘要、reviewer finding 与测试缺口、现有测试风格、已批准的稳定 Memory，以及定向重试反馈。

## 输出

`test_commands` 是建议的命令字符串数组，不代表已执行。QA 场景必须有具体步骤及可观察结果。无法自动化时明确说明 `not_covered`，不能把测试存在当作测试通过。

```json
{
  "test_strategy": [],
  "tests_added_or_modified": [],
  "coverage_notes": [],
  "not_covered": [],
  "test_commands": [],
  "qa_scenarios": []
}
```

每个 `qa_scenarios` 项有 `scenario`、非空 `steps` 数组、`expected_result` 和 `priority`（P0/P1/P2）。TEST_RUN 由主会话审批并执行命令，实际 `passed/failed/tests_not_run` 结果不能由本角色推断。

## 可选方法论

`test-guide` 是可选 companion skill，不随仓库捆绑，也不是硬 import。不可用时按本角色定义执行，不跳过测试生成。

## Memory

discriminator 仅 proposal；主会话展示建议，用户明确确认后才写入。本角色只提供可复用测试策略线索，不自行写长期 Memory。
