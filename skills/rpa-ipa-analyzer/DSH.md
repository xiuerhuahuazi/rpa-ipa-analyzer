# DSH 适配说明

本技能在 **DSH**（DeepSeek Harness）下的加载方式、调用约定与环境坑。
机制性适配文件是 `platforms/dsh/dsh.yaml`；本文件面向使用者与维护者。

## 安装

DSH 从以下根目录发现技能，**rank 小者优先**：

| 作用域 | 路径 | rank |
|---|---|---|
| 项目 | `<projectRoot>/.dsh/skills` | 100 |
| 项目 | `<projectRoot>/.agents/skills` | 200 |
| 用户 | `<dshHome>/skills` | 400 |
| 用户 | `<agentsHome>/skills`（默认 `~/.agents`） | 500 |

`projectRoot` = 从 cwd 向上找到的第一个含 `.git` 的目录；**若一路都没有 `.git`，则等于 cwd 本身**。
因此在一个没有 `.git` 的工作区里，`<cwd>/.agents/skills` 会被扫描到。

```bash
# 全用户可用
cp -r skills/rpa-ipa-analyzer/* ~/.agents/skills/rpa-ipa-analyzer/

# 仅某个工作区生效（rank 200，会覆盖同名的用户级副本）
cp -r skills/rpa-ipa-analyzer/* <workspace>/.agents/skills/rpa-ipa-analyzer/
```

安装后 DSH 会在**无需重启**的情况下刷新技能目录（文件监听）。

## DSH 的加载契约（决定了本技能为什么长这样）

DSH 的技能加载器只读取 `SKILL.md` 的 YAML frontmatter，并把正文**原样**嵌入模型上下文：

- 读取字段：`name`（必需，kebab-case）、`description`（必需）、`whenToUse`、
  `user-invocable`、`disable-model-invocation`、`metadata`。
- **正文不做任何占位符替换**；平台只额外注入一段资源提示：
  `Base directory for this skill: <绝对路径>`。

因此上游早期使用的 `{SKILL_ROOT}` 在 DSH 下不会被展开。本技能统一改用 `<SK>`，
并在正文开头声明「以平台注入的基目录提示为准」，这样所有平台都能解析。

## 调用

DSH **没有** `/<skill-name>` 斜杠命令，也不会自动执行技能。触发方式：

- 自然语言：「分析这个 RPA 项目，深度 standard」「更新分析报告」「审计这个项目」；
- 或由模型按 `description` 匹配后调用 `skill` 工具显式加载。

技能内的脚本一律通过启动器调用：

```powershell
& "<SK>\scripts\rpa.cmd" extract  "<project_path>" --force
& "<SK>\scripts\rpa.cmd" skeleton "<project_path>" --depth standard
```

Linux / macOS 用 `<SK>/scripts/rpa.sh`。

## 两个必须知道的环境坑（实测）

### 坑 1 — 可能没有可用的系统 Python

```
python --version   ->  exit 9009（WindowsApps App Execution Alias 桩）
python3 --version  ->  exit 9009（同上）
py -0p             ->  No installed Pythons found!
可用解释器          ->  <项目>/.venv-py38/Scripts/python.exe（Python 3.8.20）
```

上游文档通篇是 `python3 $SK/scripts/extract_nodes.py ...`，在这种机器上**一句都跑不通**。
`scripts/rpa.cmd` / `rpa.sh` 按 `$RPA_IPA_PYTHON` → `$PWD` 及上级的
`.venv-py38` / `.venv` / `venv` → PATH → `py -3` 依次探测，并**逐个用
`sys.version_info >= (3,8)` 校验**后才采用；找不到就 `exit 127` 并打印修法。

### 坑 2 — GBK stdout 把中文节点名变成乱码（最隐蔽）

实测（不加 `-X utf8`）：

```
��Ŀ: Ԥ��������ͬ����v1.0.1_2.1.3
�ڵ�����: 53
```

应为 `项目: 预提新增合同助手v1.0.1_2.1.3` / `节点总数: 53`。

Windows 下 Python 3.8 对非 tty 的 stdout 使用 ANSI 代码页（zh-CN 为 GBK）编码，
而 DSH 按 UTF-8 解码命令输出。**数据没坏、内容全在，但读进模型上下文的全是乱码，
且退出码仍是 0**，最终报告里的节点名、流程名、业务术语会整体错乱。

启动器因此**固定附加 `-X utf8`**（等价 `PYTHONUTF8=1`，Python 3.7+）。
这也是为什么 DSH 下不要绕过启动器：一个开关覆盖全部子命令与被 import 的模块，
比在每个脚本里包 `TextIOWrapper` 更省事，也不会与上游冲突。

### 坑 3 — 每条命令都是全新 shell 进程

DSH 的命令执行器不保留 cwd 与变量。所以**不要**「先解析 `$PY`、再分两步调用」，
必须每条命令都通过启动器重新解析。

### 坑 4 — frontmatter 里的 ASCII `": "` 会让技能**静默不加载**

DSH 用 `yaml`（eemeli/yaml）解析 frontmatter，比 Claude Code 的解析器严格。
**未加引号的普通标量里出现 ASCII 冒号+空格就是非法 YAML**：

```yaml
# 会报 "Nested mappings are not allowed in compact mappings" → 整个技能被丢弃
description: Analyze, incrementally update, or audit. Modes: analyze (quick/standard/deep), update, audit.
```

实测结论（用 DSH 自带解析器逐例验证）：

| 写法 | 结果 |
|---|---|
| `Modes: analyze (quick/standard/deep)` | ❌ 解析失败 |
| `三种模式：analyze（quick/standard/deep）`（全角冒号/括号） | ✅ |
| 值里含 ASCII 双引号（如 `include "更新分析报告"`） | ✅ |
| 整个值用双引号包起来并转义内部引号 | ✅ |

**上游 3.3.1 的 `description` 就带 `Modes: `，在 DSH 下会直接不加载**（其他平台解析更宽松所以没暴露）。
本仓库已改为全角写法，新增/修改 description 时请保持「普通标量内不出现 ASCII 冒号+空格」。

> 排查提示：技能没出现在目录里时，先核对 frontmatter 能否解析；
> 解析失败时 DSH 只在日志里 `warn`「skill file … ignored: invalid YAML frontmatter」，不会报错给用户。

### 坑 5 — 用命令行复制安装后，DSH 可能不会立刻发现

`skill-filesystem` 只在两种情况失效缓存：

1. 模型侧的文件写入（`write` / `edit` 工具触发 `fs/observed`）；
2. 被监视技能根目录的文件系统事件。

而且第 1 条要求写入路径**长得像技能路径**——`<root>/<名字>/SKILL.md` 或 `<root>/<名字>.md`，
其它文件名（如 `refresh_probe.tmp`）即使写在技能目录里也不会触发刷新。

所以用 `cp -r` / `Copy-Item` 安装后，若目录此前不存在，技能可能直到下次重启才出现。
两种即时生效的办法：

- 用编辑工具改一次 `<技能根>/rpa-ipa-analyzer/SKILL.md`（哪怕只是改注释）；
- 或重启 DSH。

## 子代理差异

| Claude Code 写法 | DSH 做法 |
|---|---|
| `Explore` 子代理拆原始 flow JSON | 不做；原始 JSON 交给脚本。确需并行时用 `subagent`，并在 prompt 中限定「只读 `.extracted_nodes` 产物」 |
| audit 同时启动 6 个 agent | 用 `workflow` fan-out 6 个审计维度，或 6 个后台 `subagent`；合并单独跑 |
| `/rpa-ipa-analyzer --depth standard` | 无斜杠命令，改自然语言触发 |

子代理不共享主会话上下文，派发时必须写明**项目绝对路径、模式、深度、产出路径**。

## 验证记录

在 `收入稽核-数据处理v1.0.4-2.1.3`（23 节点 / 6 代码节点 / 1216 行）完成 analyze 全流程：
`extract` → `skeleton` → `分析报告_收入稽核-数据处理v1.0.4-2.1.3.md`，中文输出无乱码。

同时验证 `diff`（0 变更 → `recommend=incremental`）、`apply --dry-run`（按 hash 正确跳过）、
`patch --meta --dry-run`，以及启动器四条路径：工作区根 / 项目子目录（向上查找）/
`%TEMP%` + `RPA_IPA_PYTHON` 覆盖 / 完全找不到解释器（`exit 127`）。
