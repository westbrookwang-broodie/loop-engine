# 贡献指南

感谢贡献。先阅读[主协议](zcode/skills/loop-engine/SKILL.md)与[架构](docs/architecture.md)，保持此项目作为宿主执行的配置集合，而不是引入后台运行时。

## 变更流程

1. 为问题提供可公开的最小复现或清晰验收标准，不附带真实代码会话或私人配置。
2. 保持修改范围小；同时更新命令、Agent、Schema 和示例的对应契约。
3. 为校验器或安装安全行为的修改增加回归测试。测试仅使用 Python 标准库。
4. 执行以下命令并在提交说明中准确记录结果与局限。

```bash
PYTHONDONTWRITEBYTECODE=1 python scripts/validate_content.py --root .
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests
```

5. 请求独立审查。实现者不能替审查角色或 discriminator 宣布最终通过。

## 发布内容约束

- 不提交模型绑定、本机绝对路径、密钥、内部名称、真实 Memory 或运行记录。
- Memory 只使用固定空模板；通用的虚构经验可在流程文档中说明，不得注入 Memory 模板。
- 不增加自动写 Memory、默认覆盖用户文件、网络安装或删除用户文件行为；安装器只允许清理自己创建的临时文件。
- 不提交字节码缓存，使用 PYTHONDONTWRITEBYTECODE=1 运行测试；PowerShell 等价设置见 README。
- 不以增加评分或跳过有效测试来掩盖阻断问题。
- 文档以中文为主，所有相对链接必须可解析；示例须满足 Schema。

有关私人漏洞报告见 [SECURITY](SECURITY.md)，有关长期知识的审批见 [Memory 政策](docs/memory-policy.md)。提交贡献意味着同意在本仓库 [MIT License](LICENSE) 下发布贡献。
