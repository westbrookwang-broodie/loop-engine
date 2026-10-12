# Memory 政策

## Approval 规则

discriminator 仅 proposal，不直接写长期 Memory。主会话展示按 code-writer/code-reviewer/code-generate-test/discriminator 分组的建议、证据与拟写目标，用户明确确认具体内容后才写入。未确认不写；沉默、默认同意、仅确认代码任务或要求继续循环都不是 Memory approval。

批准只覆盖确认的建议，不允许趁机追加其他经验。实际写入由获授权的主会话完成，目标通常为 `~/.zcode/loop/memory/` 对应角色文件；应保留现有内容并遵循用户的写入方式要求。本仓库安装脚本不安装真实 Memory 或示例模板。

## 可持久化内容

仅保留经验证、跨任务可复用、与项目规则兼容的原则。proposal 对象有 principle/reason/evidence，按角色分组；没有建议时说明 memory_not_proposed_reason。低置信度、未经复现或一次性细节不写成长久原则。

可提议角色边界、审查方法或行为级测试策略，但不得照搬某次失败的私有上下文。即时 finding、测试错误和下一轮动作只属于当前工作流输入。

## 不得持久化

凭据、个人信息、真实路径、内部业务名、运行记录、会话标识、一次性提交或偶发环境细节。不得复制现有私有 Memory 作为公开模板。即使用户批准，也必须先核对数据授权和安全规则。

## 发布模板

发布模板使用固定空结构，校验器精确匹配文本（允许平台换行读取归一化），任何新增原则、证据条目或额外文字都拒绝发布。真实获批经验写入私人实际 Memory，不修改这里的空模板。

[writer](../zcode/loop/memory/code-writer.example.md)、[reviewer](../zcode/loop/memory/code-reviewer.example.md)、[test-generator](../zcode/loop/memory/code-generate-test.example.md)、[discriminator](../zcode/loop/memory/discriminator.example.md) 都为空模板，无真实经验，不自动加载或安装。示例工作流完全虚构，不据此提议未经验证的长期原则。
