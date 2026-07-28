---
name: rpa-ipa-analyzer
description: Analyze, incrementally update, or audit IPA Studio RPA projects. Triggers include "分析这个 RPA 项目", "更新分析报告", "增量更新", "审计", "audit", IPA flow understanding, Python extraction, business logic mapping. Modes: analyze (quick/standard/deep), update, audit. Token-optimized extract-first workflow.
---

# IPA Studio RPA Analyzer

版本：**3.2.0**。`{SKILL_ROOT}` = 本技能安装目录（含 `scripts/`）。

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
