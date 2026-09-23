---
name: rpa-ipa-analyzer
description: 分析、增量更新或审计 IPA Studio RPA 项目（含 project.json + 流程 JSON 的应用目录）；提取流程内 Python/JS 代码、梳理业务流程、生成 Mermaid 流程与业务规则报告。Analyze, incrementally update, or audit IPA Studio RPA projects. Triggers include "分析这个 RPA 项目", "更新分析报告", "增量更新", "审计", "audit", IPA flow understanding, Python extraction, business logic mapping. Modes: analyze (quick/standard/deep), update, audit. Token-optimized extract-first workflow.
whenToUse: 用户要求理解、分析、增量更新报告或审计一个 IPA Studio RPA 项目时使用。
---

# IPA Studio RPA Analyzer

版本：**3.3.1**。`<SK>` = 本技能安装目录（含 `scripts/`）。
下文所有路径都相对 `<SK>` 解析；平台若注入「技能基目录 / skill base directory」提示，以该提示为准。

支持的平台：Claude Code / Cursor / OpenAI Codex / OpenClaw / **DSH**（适配说明见 `<SK>/DSH.md`）。

单一技能，三种模式（**不要**再安装 `rpa-ipa-update` / `rpa-ipa-audit`）：

| 模式 | 触发 | 产出 |
|------|------|------|
| **analyze** | 分析 / `--depth quick\|standard\|deep` | `分析报告_{name}.md` |
| **update** | 更新分析报告 / 增量更新 | 同报告局部 patch |
| **audit** | 审计 / audit / 代码安全检查 | `AUDIT_REPORT.md`（+ 可选 §6） |

用户未指明时：无报告 → analyze；有报告且刚改代码 → update；明确要审计 → audit。

---

## 第 0 步：解释器与调用

**始终通过技能自带的启动器调用脚本**，不要直接写 `python3 scripts/...`。
启动器会自己解析解释器、校验版本，并固定附加 `-X utf8`：

```bash
# Windows (PowerShell)
& "<SK>\scripts\rpa.cmd" extract  "<project_path>" --force
& "<SK>\scripts\rpa.cmd" skeleton "<project_path>" --depth standard
& "<SK>\scripts\rpa.cmd" stats    "<project_path>"

# Linux / macOS / Git Bash / WSL
"<SK>/scripts/rpa.sh" extract  "<project_path>" --force
"<SK>/scripts/rpa.sh" skeleton "<project_path>" --depth standard
```

启动器解析顺序：`$RPA_IPA_PYTHON` → `$PWD` 及上级目录的 `.venv-py38` / `.venv` / `venv`
→ PATH 上的 `python3` / `python` → `py -3`。**每个候选都会先校验 `sys.version_info >= (3,8)`**
才采用；全部失败则 `exit 127` 并打印修法。

### 为什么必须用启动器（两个实测坑）

1. **机器上可能没有可用的系统 Python。** 在 Windows 上 `python` / `python3` 常指向
   Microsoft Store 的 App Execution Alias 桩（执行即 `exit 9009`），`py` 也可能报
   “No installed Python found!”。此时上游文档里的 `python3 $SK/scripts/extract_nodes.py`
   **一句都跑不通**。启动器会退到项目自带虚拟环境。
2. **不加 `-X utf8` 会静默毁掉分析结果。** Windows 下 Python 用 ANSI 代码页
   （zh-CN 为 GBK）写 stdout，而 Agent 侧按 UTF-8 解码，于是
   `项目: 预提新增合同助手` 变成 `��Ŀ: Ԥ��������ͬ����` —— **数据没坏、内容全在，
   但读进模型上下文的全是乱码，且退出码仍是 0**。启动器已内置该参数，不要绕过。

DSH 额外注意：**每次命令都是全新 shell 进程**，上一条命令里解析出的 `$PY` 在下一条里
不存在，因此务必每条命令都走启动器，而不要「先解析、再分两步调用」。

### 绕过启动器时（仅 `version_check.py` / `component_promotion.py` 等独立脚本）

必须**在同一条命令内**解析并使用：

```powershell
$PY = "$PWD\.venv-py38\Scripts\python.exe"   # 或 $env:RPA_IPA_PYTHON
& $PY -X utf8 "<SK>\scripts\version_check.py"
```

---

## Token 铁律（全模式）

1. **Extract-first**：先跑脚本；LLM **禁止**整读原始 flow JSON。
2. **只读产物**：`manifest.json`、`N*.py|js`、`report_skeleton.md`、`changed.json`、`project.json`、`globalParams.json`、`processResult.json`。
3. **代码外置**：§2.2 只写路径 + hash + 业务概述；禁止贴完整源码。
4. **按需加载**：默认不读 `references/ipa_format.md` / `patterns_*` / `audit_swarm.md`。
5. **改代码走 apply**：编辑 `.extracted_nodes/N*.py|js` 后用 `apply` 写回 flow，禁止手改巨型 JSON。
6. **变量分域必登记**：新增脚本出参/入参映射前，先在对应流程 `global_vars`（及跨流程时目标流程）登记 `key`；详见下方「变量/参数铁律」。

### 写回流程 JSON（apply）

```bash
"<SK>/scripts/rpa.cmd" apply "<project_path>" --dry-run      # 预览
"<SK>/scripts/rpa.cmd" apply "<project_path>" --node 55      # 指定节点
"<SK>/scripts/rpa.cmd" apply "<project_path>"                # 只写 hash 有变更的
```

- 默认只写 **hash 有变更** 的 structured 节点；`--node` / `--file` / `--force` 可精选。退出码 `2` 表示有节点写入失败。
- 写入前备份 `{flow}.bak_apply_YYYYMMDD_HHMMSS`；剥离 `@node` 头；校验写后 hash。
- **`apply` 只改 `python_script`/`js_code`**，不改 `global_vars`、`python_input_variables`、`_script_execute_result`、子流程 `input_variables` —— 这些须另补丁。
- 规格：`docs/superpowers/specs/2026-08-10-extract-nodes-apply.md`（技能仓库）。

### 变量/参数铁律（IPA 运行时）

Agent 改脚本 I/O 时**必须**遵守，否则运行报「出参定义解析失败，变量/参数表内不存在【xxx】」：

| 层级 | 存放位置 | 作用域 | 脚本如何用到 |
|------|----------|--------|----------------|
| 项目参数 | `globalParams.json` | 全项目共享（文件路径、DATEYM 等） | 仍须经节点 `python_input_variables` / JS 入参映射进脚本 |
| 流程变量 | 各 flow JSON 顶层 **`global_vars[]`** | **仅该流程域**（主流程 / 业务流程 / 生成成本基础表 / 生成预提表 / 数据处理…各自一份） | 域内节点共享；脚本仍须映射 |
| 节点入参映射 | `python_input_variables`（或 JS 等价） | 单节点 | `{脚本内名: 流程变量key}` |
| 节点出参映射 | `_script_execute_result` | 单节点 → 写回流程变量 | `{脚本内名: 流程变量key}`；**value 侧 key 必须已在本流程 `global_vars`** |
| 子流程交换 | `sub_process.input_variables` / `output_variables` | 父→子 / 子→父 | 两侧流程的 `global_vars` 都要有对应 key |

**硬约束：**

1. `_script_execute_result` / 子流程映射里出现的名字，必须先在**该流程** `global_vars` 登记：`{id, key, description, value}`（`value` 可空串）。
2. 跨子流程传递时：源流程出参、父流程桥接、子流程 `global_vars` + `input_variables` **缺一不可**。
3. **禁止**把 Python **类**（如自定义 Exception）写作出参；只映射函数/普通对象。类可留在脚本内，用实例属性识别（如 `is_node_fail`）。
4. 改 I/O 检查清单：`global_vars` → 节点出参/入参映射 →（若跨流程）子流程 `input_variables` → `apply` 脚本。

详情与字段形状：`references/ipa_format.md` §变量作用域与脚本映射。
查血缘用 `trace`：既可用**流程变量名**（如 `OutputPath`、`out_workpath`），也可用**脚本内变量名**（如 `OUTPUT_PATH`）。

---

## 模式 A — analyze

```bash
"<SK>/scripts/rpa.cmd" extract  "<project_path>" --force
"<SK>/scripts/rpa.cmd" skeleton "<project_path>" --depth standard
# LLM：读 .extracted_nodes/report_skeleton.md + 按需 N*.py → 写 分析报告_*.md
# deep：完成后自动进入模式 C（audit）
```

| 深度 | 产出 |
|------|------|
| quick | §1 + §2.1 + §3 + §5.1 + 附录 B |
| standard | 完整报告（代码外置） |
| deep | standard + audit |

触发：`--depth` >「快速概览」/「深度分析」> ≥500 节点建议 quick。

standard 且代码节点 >200：按 `code_hash` 去重深读。

报告写到项目根目录 `分析报告_{项目名}.md`，结构照 `references/report_template.md`；字段含义照 `references/ipa_format.md`。

可选层 0：`version_check.py`；standard/deep 可跑 `component_promotion.py`。

---

## 模式 B — update

前置：已有 `分析报告_*.md` + `.extracted_nodes/manifest.json`。

```bash
"<SK>/scripts/rpa.cmd" extract "<project_path>" --force
"<SK>/scripts/rpa.cmd" diff    "<project_path>" --json --out "<project_path>/.extracted_nodes/changed.json"
# 每个变更节点：读 N*.py → 短 Markdown（含 #### 节点 N{n}:）→ patch
"<SK>/scripts/rpa.cmd" patch "<report>" --node <n> --from-file node_N<n>.md
"<SK>/scripts/rpa.cmd" patch "<report>" --meta "分析日期：<date>（增量更新） | 变更节点：N…"
```

| 规则 | |
|------|--|
| 禁止整份报告进上下文重写 | 只用 diff 列表 + 单节点片段 + patch |
| `recommend=incremental`（delta≤5） | 增量 |
| delta>5 / 子流程大变 / 章节断裂 | 改走 analyze |

I/O 变：`trace --direction up|down`。

---

## 模式 C — audit

前置：`.extracted_nodes/` 存在（否则先 extract）。`total_nodes==0` → 退出。

| 参数 | 行为 |
|------|------|
| 默认 | **增量**：只审 `diff` 的 changed/added；无快照则全量 |
| `--full` | 全量 6 维 |
| `--scope security[,…]` | 子集 |

6 个审计维度的 agent prompt 见 `references/audit_swarm.md`。每个维度把结果写入
`<project_path>/audit_findings/*.json` → Merge → `AUDIT_REPORT.md`；
可用 `patch` 给分析报告加 §6（勿整文件重写）。

增量且变更很少时串行 1–2 个维度，勿默认开满 6 路。

### 子代理差异（Claude Code ↔ DSH）

| 上游（Claude Code）写法 | DSH 做法 |
|---|---|
| 用 **Explore** 子代理拆原始 flow JSON | **不做**。原始 JSON 一律交给脚本；确需并行阅读时用 `subagent`，并在 prompt 里明确「只读 `.extracted_nodes` 产物，禁止读原始流程 JSON」 |
| audit「同时启动 6 个 agent」 | 用 `workflow`（一个脚本 fan-out 6 个维度，写回 `audit_findings/*.json`）或 6 个后台 `subagent`；合并步骤单独跑一次 |
| `/rpa-ipa-analyzer --depth standard` 斜杠命令 | DSH **无**该斜杠命令。用自然语言触发，例如「分析这个 RPA 项目，深度 standard」 |

子代理不共享主会话上下文，派发时把**项目绝对路径、模式、深度、产出路径**写进 prompt。

---

## 项目类型（processResult / manifest）

| 主力 | 类型 |
|------|------|
| `script_python_execute` + `log_task` | Data Processing |
| `mouse_single_click` + `browser_inject_js_code` | Web Automation |
| 两者均显著 | Mixed |

## 质量自检

- 未整段贴源码；§2.2 含 `.extracted_nodes/` 引用
- analyze：Mermaid / 参数表 / 附录 B；standard+ 含 §4/§5.3/§5.4
- audit：`AUDIT_REPORT.md` 或标 INCOMPLETE
- 脚本输出未见乱码（`��`），命令均通过 `rpa.cmd` / `rpa.sh` 调用
