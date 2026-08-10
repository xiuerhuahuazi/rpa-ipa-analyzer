---
name: rpa-ipa-analyzer
description: Analyze, incrementally update, or audit IPA Studio RPA projects. Triggers include "分析这个 RPA 项目", "更新分析报告", "增量更新", "审计", "audit", IPA flow understanding, Python extraction, business logic mapping. Modes: analyze (quick/standard/deep), update, audit. Token-optimized extract-first workflow.
---

# IPA Studio RPA Analyzer

版本：**3.3.1**。`{SKILL_ROOT}` = 本技能安装目录（含 `scripts/`）。

单一技能，三种模式（**不要**再安装 `rpa-ipa-update` / `rpa-ipa-audit`）：

| 模式 | 触发 | 产出 |
|------|------|------|
| **analyze** | 分析 / `--depth quick\|standard\|deep` | `分析报告_{name}.md` |
| **update** | 更新分析报告 / 增量更新 | 同报告局部 patch |
| **audit** | 审计 / audit / 代码安全检查 | `AUDIT_REPORT.md`（+ 可选 §6） |

用户未指明时：无报告 → analyze；有报告且刚改代码 → update；明确要审计 → audit。

---

## Token 铁律（全模式）

1. **Extract-first**：先跑脚本；LLM **禁止**整读原始 flow JSON。
2. **只读产物**：`manifest.json`、`N*.py|js`、`report_skeleton.md`、`changed.json`、`project.json`、`globalParams.json`、`processResult.json`。
3. **代码外置**：§2.2 只写路径 + hash + 业务概述；禁止贴完整源码。
4. **按需加载**：默认不读 `ipa_format.md` / `patterns_*` / `audit_swarm.md`。
5. **改代码走 apply**：编辑 `.extracted_nodes/N*.py|js` 后用 `apply` 写回 flow，禁止手改巨型 JSON。
6. **变量分域必登记**：新增脚本出参/入参映射前，先在对应流程 `global_vars`（及跨流程时目标流程）登记 `key`；详见下方「变量/参数铁律」。

### 写回流程 JSON（apply）

```bash
python {SKILL_ROOT}/scripts/extract_nodes.py apply {project_path} [--dry-run] [--node N] [--file PATH] [--force]
```

- 默认只写 **hash 有变更** 的 structured 节点；`--node` / `--file` 可精选；`--dry-run` 预览。
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

---

## 模式 A — analyze

```bash
python {SKILL_ROOT}/scripts/extract_nodes.py extract {project_path} [--force]
python {SKILL_ROOT}/scripts/extract_nodes.py skeleton {project_path} --depth {quick|standard|deep}
# LLM：读 skeleton + 按需 N*.py → 写 分析报告_*.md
# deep：完成后自动进入模式 C（audit）
```

| 深度 | 产出 |
|------|------|
| quick | §1 + §2.1 + §3 + §5.1 + 附录 B |
| standard | 完整报告（代码外置） |
| deep | standard + audit |

触发：`--depth` >「快速概览」/「深度分析」> ≥500 节点建议 quick。

standard 且代码节点 >200：按 `code_hash` 去重深读。禁止 Explore 拆原始 JSON。

报告结构：`references/report_template.md`。字段：`references/ipa_format.md`。

可选层 0：`version_check.py`；standard/deep 可跑 `component_promotion.py`。

---

## 模式 B — update

前置：已有 `分析报告_*.md` + `.extracted_nodes/manifest.json`。

```bash
python {SKILL_ROOT}/scripts/extract_nodes.py extract {project_path} --force
python {SKILL_ROOT}/scripts/extract_nodes.py diff {project_path} --json --out {project_path}/.extracted_nodes/changed.json
# 每个变更节点：读 N*.py → 短 Markdown（含 #### 节点 N{n}:）→ patch
python {SKILL_ROOT}/scripts/extract_nodes.py patch {report} --node {n} --from-file node_N{n}.md
python {SKILL_ROOT}/scripts/extract_nodes.py patch {report} --meta "分析日期：{date}（增量更新） | 变更节点：N…"
# 刷新快照为当前 manifest（便于下次 diff）
```

| 规则 | |
|------|--|
| 禁止整份报告进上下文重写 | 只用 diff 列表 + 单节点片段 + patch |
| `recommend=incremental`（delta≤5） | 增量 |
| delta>5 / 子流程大变 / 章节断裂 | 改走 analyze |

I/O 变：`trace --direction up|down`。详情亦见历史增量约定（同 3.1 diff/patch）。

---

## 模式 C — audit

前置：`.extracted_nodes/` 存在（否则先 extract）。`total_nodes==0` → 退出。

| 参数 | 行为 |
|------|------|
| 默认 | **增量**：只审 `diff` 的 changed/added；无快照则全量 |
| `--full` | 全量 6 维 |
| `--scope security[,…]` | 子集 |

Agent prompt：`references/audit_swarm.md`。写入 `audit_findings/*.json` → Merge → `AUDIT_REPORT.md`；可用 `patch` 给分析报告加 §6（勿整文件重写）。

增量且变更很少时串行 1–2 个 agent，勿默认开满 6 路。

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
