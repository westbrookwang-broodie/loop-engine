# 定制

## 项目规则

项目 `AGENTS.md` 与安全规范优先。可参考[指令示例](../zcode/AGENTS.example.md)人工合并，不覆盖现有全局指令。将任务验收、相关变更和测试命令作为宿主输入，不在可公开的 Agent 中写入个人配置。

## 模型与权限

四个 Agent frontmatter 只包含 name/description，不绑定模型。使用者在宿主中选择模型、权限与独立上下文。角色隔离为宿主 policy，不能靠提示词保证文件系统或工具隔离。

## 输出契约

修改字段时同步[主 Skill](../zcode/skills/loop-engine/SKILL.md)、命令、Agent、四类 Schema、示例和校验测试。保持 iteration verdict 与 workflow final status 分离。blocking_issues 为 owner/issue/required_action 对象，不退回含糊字符串。

默认阈值 writer/reviewer 为 0.75、test-generator 为 0.70、confidence 为 0.75；评分例外必须记入 policy_exceptions 并有低风险证据，不豁免阻断缺陷。当前协议最多三轮；若维护自己的不同策略，须显式修改协议和验证，不静默延长运行。

## 测试与可选方法论

主会话从项目实际文件识别测试命令，不自动猜测执行危险命令。测试缺少时可规划 QA，但必须记录未执行。

可选 companion skills code-review/test-guide/discriminator-rubric 不捆绑，也不是硬 import。宿主确认可用后可以调用；它们的策略与本仓库状态或 Memory 规则冲突时，以项目规则和本协议为准，不假装已调用。

## Memory

discriminator 仅 proposal；主会话展示，用户明确确认后才写入。请先阅读[Memory 政策](memory-policy.md)，不要将模板作为已批准经验安装。
