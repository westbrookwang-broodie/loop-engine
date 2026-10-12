# 架构

## 组件与宿主职责

仓库包含命令入口、主 Skill、四个 Agent 提示词、输出 Schema、安装脚本和文档。ZCode 宿主负责资源发现、角色调用、模型选择、上下文传递、工具授权、测试执行及终止。它不是独立后台运行时，不自带调度器、数据库、沙箱或业务 CI。

角色隔离是宿主落实的 policy，不是 Skill 的技术保证。宿主应使用独立角色上下文并传递可验证变更，不能让 writer 自审、再自行宣布 pass。TEST_RUN 不是第五个 Agent，而是主会话审批后的执行阶段。

## 阶段与纠正

```text
INIT -> WRITE -> REVIEW -> TEST_GENERATE -> TEST_RUN -> DISCRIMINATE
retry(code-writer) -> WRITE -> REVIEW -> TEST_GENERATE -> TEST_RUN -> DISCRIMINATE
retry(code-reviewer) -> REVIEW -> TEST_GENERATE -> TEST_RUN -> DISCRIMINATE
retry(code-generate-test) -> TEST_GENERATE -> TEST_RUN -> DISCRIMINATE
retry(user) -> human_review_required
```

首次轮数 1，重试加 1，最多三轮。重试 reviewer 后测试生成、运行和判别不能省略。重试 test-generator 时保留未变实现与审查证据，新增测试变更仍须接受风险评估；出现未审查的业务改动时回到对应角色。

## 两类状态

| 单轮 overall_status | 条件 | 工作流 final_status |
| --- | --- | --- |
| pass | 满足证据与政策 | pass |
| human_review_required | 需人工判断 | human_review_required |
| retry | target=user | human_review_required |
| fail | 无法继续 | fail |
| retry | 非 user 且轮数小于 3 | 尚未结束，进入下一轮 |
| retry | 非 user 且轮数为 3 | max_iterations_reached |

第三轮 retry 不伪造 iteration verdict=fail，最终状态也不包含 retry。人工升级优先于轮数耗尽。

## 数据契约

- [writer Schema](../schemas/writer-output.schema.json)
- [reviewer Schema](../schemas/reviewer-output.schema.json)
- [test-generator Schema](../schemas/test-generator-output.schema.json)
- [discriminator Schema](../schemas/discriminator-output.schema.json)

四类 Schema 使用 JSON Schema 2020-12；根对象禁止额外字段。next_action 的 null 与动作条件、阻断项对象、评分范围和 Memory 分组有显式约束。Schema 检查形状，不证明证据真实性；主会话须核查含义。

示例中的每个 JSON envelope 必须完整包含 `iteration/final_status/writer_output/reviewer_output/test_generator_output/test_run/discriminator_output`。仅非 user 的 retry 且 iteration < 3 时，`final_status` 必须显式为 null，表示进行中；null 不是第五种终态。其余情况按上表填写终态，不省略字段。

retry 且 blocking_issues 非空时，next_action.target_agent 必须匹配至少一个 blocking owner；target=user 总是升级 human_review_required。这类跨字段语义由内容校验器与宿主核查，不靠 Schema 形状保证。

完整协议见[主 Skill](../zcode/skills/loop-engine/SKILL.md)，审批规则见[Memory 政策](memory-policy.md)。
