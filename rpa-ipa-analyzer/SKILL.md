---
name: rpa-ipa-analyzer
description: Analyze IPA Studio RPA projects to produce structured business/code reports. Use for "analyze this RPA project", IPA Studio flow understanding, Python extraction, business logic mapping. Depths: quick / standard / deep. Token-optimized: extract-first, never read raw multi-MB flow JSON in LLM context.
---

# IPA Studio RPA Analyzer

版本：**3.1.0**。输出：`{project_path}/分析报告_{project_name}.md`（结构见 `references/report_template.md`）。

首次分析可后台跑 `scripts/version_check.py`（缓存 24h）。

## Token 铁律（必须遵守）

1. **Extract-first**：任何深度都先跑脚本抽取；LLM **禁止**把原始 flow JSON（常 >50KB/4MB）整文件读进上下文。
2. **只读产物**：`manifest.json`、`.extracted_nodes/N*.py|js`、`report_skeleton.md`、`globalParams.json`、`project.json`、`processResult.json`。
3. **代码外置**：§2.2 **禁止**粘贴完整源码；写路径 + hash + 业务概述/规则/I-O。
4. **骨架先行**：`extract_nodes.py skeleton` 生成结构章节，LLM 只润色业务语义。
5. **按需加载 references**：默认不读 `ipa_format.md` / `patterns_*`；仅当未知组件或需模式匹配时再读。

`SKILL` 路径：`{SKILL_ROOT}` = 本技能安装目录（含 `scripts/`）。

## 分析深度

| 深度 | 场景 | 产出 |
|------|------|------|
| **quick** | 陌生项目 / ≥500 节点 | 精简报告（§1+§2.1+§3+§5.1+附录B） |
| **standard** | 默认 | 完整报告（代码外置） |
| **deep** | 发布前 | standard + 6 维审计（或 `/rpa-ipa-audit`） |

触发：`--depth` > 自然语言（快速概览/深度分析）> 规模提示（≥500 建议 quick）。

## 流水线（所有深度）

```bash
# 1) 抽取（确定性，零 LLM token）
python {SKILL_ROOT}/scripts/extract_nodes.py extract {project_path} [--force]

# 2) 结构骨架（确定性）
python {SKILL_ROOT}/scripts/extract_nodes.py skeleton {project_path} --depth {quick|standard|deep}

# 3) LLM：读 skeleton + 按需读 N*.py，润色业务语义 → 写 分析报告_*.md
# 4) deep：再跑 /rpa-ipa-audit（默认仅审计 hash 变化节点，见 SKILL_audit.md）
```

### LLM 填写范围

| 深度 | 脚本已生成 | LLM 补齐 |
|------|-----------|----------|
| quick | §1 路径/附录B/参数表/组件统计 | 一句话业务目标、架构说明润色 |
| standard | 同上 + §2.2 节点索引表 | 每节点业务概述/规则/I-O；§4 术语/血缘/公式；§5 建议与风险 |
| deep | 同 standard | + 审计摘要 §6 |

### 大项目降级（standard，代码节点 >200）

按 `code_hash` 去重，同 hash 只深读一份；`<5` 行节点归组一句话。

### 禁止事项

- 用 Explore agent「拆读」原始 flow JSON（抽取已由脚本完成）
- 在报告中嵌入整段 `python_script` / `js_code`
- 未跑 extract/skeleton 就直接写报告

## 项目类型（processResult / manifest）

| 主力 | 类型 |
|------|------|
| `script_python_execute` + `log_task` | Data Processing |
| `mouse_single_click` + `browser_inject_js_code` | Web Automation |
| 两者均显著 | Mixed |

## 层 0 自校准（可选）

- `version_check.py`；quick 可跳过 promotion
- `component_usage_counts.json` 达阈值再跑 `component_promotion.py`（standard/deep）

## 质量自检

- 报告未整段粘贴源码；§2.2 含 `.extracted_nodes/` 引用
- Mermaid / 参数表 / 附录 B 存在
- standard+：§4 血缘+术语+Excel I/O；§5.3/5.4 具体可操作
- deep：§6 或独立 `AUDIT_REPORT.md`

## 增量更新 / 审计

- 代码改后用 **`/rpa-ipa-update`**（`diff` + `patch`，勿全量重写报告）
- 独立审计 **`/rpa-ipa-audit`**（见 `SKILL_audit.md`）

细节字段定义：`references/ipa_format.md`。报告章节：`references/report_template.md`。
