# 可人工合并的 Loop Engine 指令示例

本文件不自动安装，不应替换现有用户或项目 `AGENTS.md`。按需人工合并，并优先遵守项目规则。

- 对非简单代码任务，可使用 `/loop-engine` 进行实现、独立审查、测试生成、测试运行及判别。
- 宿主落实角色隔离 policy；不同角色不能静默兼任，缺失角色时停止并说明。
- 最多三轮；实现者不能自行宣称 review 通过或工作流最终 pass。
- 明确记录测试命令与 `passed/failed/tests_not_run`，缺少证据时不得编造成功。
- discriminator 仅 proposal；主会话展示 Memory 建议，用户明确确认后才写入。未确认则不写。
- 临时反馈仅服务当前任务，不自动变成长久 Memory。

完整定义见[主 Skill](skills/loop-engine/SKILL.md)和[Memory 政策](../docs/memory-policy.md)。
