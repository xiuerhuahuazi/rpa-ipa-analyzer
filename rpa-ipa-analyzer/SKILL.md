---
name: rpa-ipa-analyzer
description: Analyze IPA Studio RPA projects to produce comprehensive business and code analysis reports with Mermaid flowcharts. Use when the user asks to "analyze this RPA project", "understand this IPA Studio flow", "extract Python code from flow", "map the business logic", or "generate a RPA analysis report". Supports data-processing (Python/pandas), web automation (JS/browser/UI), and mixed projects. Hierarchical JSON flows, embedded code extraction, global parameter mapping, multi-project batch analysis.
---

# IPA Studio RPA Analyzer

输出：`{project_path}/分析报告_{project_name}.md`，格式严格遵循 `references/report_template.md`。

## 项目类型判定（从 processResult.json）

| 主力组件 | 类型 |
|---------|------|
| `script_python_execute` + `log_task` | **Data Processing** |
| `mouse_single_click` + `browser_inject_js_code` | **Web Automation** |
| 两者均显著 | **Mixed** |

## 分析流程

### Phase 1: 项目发现

并行读取：`project.json`（流程注册）、`globalParams.json`（运行时参数）、`processResult.json`（组件统计）、`globalParamsAll.json`（部署模板）。

输出：流程层级树 + 参数清单 + 组件类型统计。

### Phase 2: 流程结构提取

对每个 JSON 流程文件（主流程 + 全部子流程）：

- **节点**: `graphData.nodes[]` — 提取 `id`, `component_id`, `show_name`; `properties[]` 中 `type:"input_params"` 含代码/配置
- **边**: `graphData.edges[]` — `sourceNode→targetNode`，重建执行 DAG
- **全局变量**: `global_vars[]` — 变量名+描述

各组件类型的字段提取路径见 `references/ipa_format.md`。大文件(>50KB)用 Explore agent 并行提取。

### Phase 3: 代码深度分析

**Python 节点** (`script_python_execute`)：
1. 读取 `python_script` 全文
2. `python_input_variables` → 变量来源映射（上游节点/全局参数/硬编码）
3. `_script_execute_result` → 下游消费者映射
4. 分析：数据结构、处理步骤、业务规则、Excel I/O、异常处理、边界情况

**JavaScript 节点** (`browser_inject_js_code`)：
1. 读取 `js_code` 全文，分类：DOM操作/数据提取/状态检测/值注入
2. 记录 DOM 选择器、`window` 变量、数据交接给 Python 的方式

### Phase 4: 流程序列重建

从边构建邻接表 → 找入口节点 → 正向遍历 → 标注分支/循环/异常/子流程调用 → 按业务逻辑分阶段。

### Phase 5: 业务逻辑解读

| 维度 | 内容 |
|------|------|
| 业务目标 | 解决什么问题？日/月/一次性？输入→输出？ |
| 领域术语表 | 代码中每个专业术语的业务含义 |
| 数据血缘 | Resources/ → 各处理节点 → output/ 端到端 ASCII 流程图，标注每步文件名和列 |
| 业务规则目录 | JOIN键+优先级、筛选条件(含表达式)、计算公式(数学+代码)、决策树 |
| Excel I/O 表 | 每个读写的文件：节点、Sheet、列 |

### Phase 6: 报告生成

严格遵循 `references/report_template.md`。关键质量标准：
- §2.2 每个代码节点独立分析，使用模板的表格+代码块格式
- §4.5 Resources/ 下所有 Excel 文件必须出现
- §5.3 优化建议必须具体可操作（非泛泛的"提升性能"）
- §5.4 风险项含严重程度、触发条件、具体缓解措施
- Appendix B 含完整节点索引

### Phase 7: 质量自检

检查清单：§1-§5 全部存在 | §1 Mermaid 图 | §2 每个 Python 节点已分析 | §3 全部 globalParams 列出 | §4 数据血缘+术语表+Excel I/O | §5 组件统计+优化建议+风险矩阵 | Appendix B 节点索引

---

## 大文件与批量策略

- 大文件(>50KB)：Explore agent 并行提取，每个 agent 负责一个 JSON 文件
- 批量分析：每个项目一个 Explore agent 做 Phase 1-2，串行做 Phase 3-5
- 探索 agent prompt 核心：对每个节点提取 `component_id, show_name, properties(input_params 含代码)`；对每个边提取 `sourceNode→targetNode`
