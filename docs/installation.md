# 安装说明

## 前提

需要支持自定义 Agent、命令与 Skill 的 ZCode 宿主。具体资源发现、刷新和角色独立性由宿主版本及配置决定；本仓库不绑定私有模型或固定版本。安装前应检查同名配置是否已有自定义内容。

下载仓库后可从任意工作目录调用脚本，源目录始终按脚本所在仓库定位。Shell 使用 Bash 及 GNU coreutils（包括 realpath、mktemp、mv；Git Bash 和常见 Linux 环境已提供），在 Git Bash 中也接受原生 Windows 目标路径并转换后预检；PowerShell 脚本支持 Windows PowerShell 5.1 及 PowerShell 7。Python 仅用于验证内容，不是运行工作流的必需服务。

## 自动安装

在仓库根目录执行：

```bash
bash scripts/install.sh
bash scripts/install.sh --force
```

```powershell
powershell -NoProfile -File scripts/install.ps1
powershell -NoProfile -File scripts/install.ps1 -Force
```

第二条命令仅用于显式确认覆盖的情况，不是必须执行的步骤。默认目标为 `~/.zcode`。测试或定制可显式指定安装目录：

```bash
bash scripts/install.sh --target ./local-zcode
```

```powershell
powershell -NoProfile -File scripts/install.ps1 -Target ./local-zcode
```

脚本依次预检全部源文件、全部目标冲突和父目录类型，然后才创建目录并复制。现有文件、目录或链接都算冲突；默认退出且不复制。即使 force，目录或符号链接目标及父目录也不允许覆盖，以防越界。脚本只复制下列 6 个固定相对路径，不使用递归扫描：

```text
agents/code-writer.md
agents/code-reviewer.md
agents/code-generate-test.md
agents/discriminator.md
commands/loop-engine.md
skills/loop-engine/SKILL.md
```

预检避免已知冲突造成部分安装。目标与源 `zcode/` 相等、互为祖先或后代时一律拒绝；Windows 路径比较忽略大小写。覆盖先复制到目标同级、独占创建的临时文件，再以 rename/File.Replace 替换目录项，不截断已有目标 inode，因此不会写穿目标硬链接修改另一目录的文件。替换前复查目标与父目录，拒绝 symlink/reparse point；默认非 force 时若目标中途出现则拒绝覆盖。

这不是完整安装事务，也不提供面对磁盘故障、权限变化或恶意并发父目录替换的隔离或回滚。Force 前自行备份；安装期间避免其他进程修改目标。脚本不请求网络、不安装依赖、不删除用户文件；失败时只清理本次安装器创建的同级临时文件。

## 手动安装

可把上述 `zcode/` 下白名单文件逐个复制到 `~/.zcode/` 的同名路径。先检查所有目标冲突。不要把 `AGENTS.example.md` 改名覆盖全局 `AGENTS.md`，仅按需人工合并。Memory 的 `.example.md` 是空模板，不自动安装，不作为真实经验加载。

完成后在 ZCode 中刷新自定义资源或开启新会话，确认四个角色及 `/loop-engine` 可用。缺失角色时命令应停止，不由现有角色兼任。

## 验证与卸载

```bash
PYTHONDONTWRITEBYTECODE=1 python scripts/validate_content.py --root .
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests
```

卸载只需在核对内容与自定义修改后人工处理上述白名单目标。本项目不提供自动删除脚本。可选 companion skills code-review/test-guide/discriminator-rubric 不捆绑，也不是硬 import，未安装不影响基准协议。
