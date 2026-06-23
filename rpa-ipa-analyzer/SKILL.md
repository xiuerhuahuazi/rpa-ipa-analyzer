---
name: rpa-ipa-analyzer
description: Analyze IPA Studio RPA projects to produce comprehensive business and code analysis reports with Mermaid flowcharts. Use when the user asks to "analyze this RPA project", "understand this IPA Studio flow", "extract Python code from flow", "map the business logic", or "generate a RPA analysis report". Supports quick (overview), standard (full analysis), and deep (with code audit) modes. Automatically detects project scale and recommends depth. Supports data-processing (Python/pandas), web automation (JS/browser/UI), and mixed projects.
---

# IPA Studio RPA Analyzer

当前版本：3.0.0。首次分析前，后台检查 GitHub `xiuerhuahuazi/rpa-ipa-analyzer` 是否有新版本（运行 `scripts/version_check.py`，缓存24h）。如有差异，告诉用户。

输出：`{project_path}/分析报告_{project_name}.md`，格式严格遵循 `references/report_template.md`。

## 分析深度

本分析器支持三个深度级别，可在调用时指定或由系统自动判定：

| 深度 | 适用场景 | 产出 |
|------|---------|------|
| **quick** | 快速了解陌生项目架构，项目 >500 节点时推荐 | ~5-15KB 精简报告（架构图+参数清单+组件统计） |
| **standard** | 正常分析，含完整代码和业务逻辑解读（默认） | ~30-200KB 完整报告 |
| **deep** | 发布前审查，含 6 维并行自动化代码审计 | 完整报告 + `AUDIT_REPORT.md` |

**触发方式（优先级从高到低）：**
1. 参数：`/rpa-ipa-analyzer --depth quick|standard|deep <path>`
2. 自然语言：用户消息含"快速概览"/"quick" → quick；含"深度分析"/"审计"/"deep" → deep
3. 规模自动判定：总节点 >= 500 → 提示"项目较大（N个节点），建议 quick 模式快速获取架构概览。是否继续 quick？也可以选择 standard 或 deep。"

**深度执行矩阵：**

| 层 | quick | standard | deep |
|----|:---:|:---:|:---:|
| 层 0 环境自校准 | ✅ | ✅ | ✅ |
| 层 1 项目建模 | 降级（主流程顶层+processResult） | ✅ 完整 | ✅ 完整 |
| 层 2 代码与业务分析 | ❌ 跳过 | ✅ 完整（>200节点去重+抽样） | ✅ 逐一（为审计准备） |
| 层 3 产物生成 | 精简报告+精简自检 | 完整报告+完整自检 | 完整报告+完整自检+审计 |
| extract_nodes.py | ❌ 不运行 | ✅ 运行 | ✅ 运行 |

---

## 项目类型判定（从 processResult.json）

| 主力组件 | 类型 |
|---------|------|
| `script_python_execute` + `log_task` | **Data Processing** |
| `mouse_single_click` + `browser_inject_js_code` | **Web Automation** |
| 两者均显著 | **Mixed** |

---

## 分析流程（4 个能力层，自底向上）

```
层 0: 环境自校准 ──→ 层 1: 项目建模 ──→ 层 2: 代码与业务分析 ──→ 层 3: 产物生成
```

### 层 0: 环境自校准

**目的**：确保分析器自身状态最优，在所有其他层之前运行。

**0.1 版本检查**（首次分析，缓存 24h）：运行 `scripts/version_check.py`，如有新版本告知用户。

**0.2 自适应组件升级**：检查 `component_usage_counts.json`，如有组件 `count >= 3` 且 `promoted == false`：
1. 运行 `python.exe scripts/component_promotion.py --component-id X --fields '[...]'`
2. 手动 Edit 更新 `ipa_format.md` 中组件列表
3. 标记 `promoted = true`
4. 以 `--force` 重新运行 `extract_nodes.py`

> **重要**：层 0.2 完成后再进入层 1，确保 manifest 使用最新的字段提取逻辑。quick 模式下仅做 0.1 版本检查，跳过 0.2。

### 层 1: 项目建模

**目的**：建立项目完整结构模型——元数据、流程树、节点清单、边拓扑。

**1.1 元数据发现**
- 并行读取：`project.json`、`globalParams.json`、`processResult.json`、`globalParamsAll.json`
- 判定项目类型（Data Processing / Web Automation / Mixed）
- 列出主流程 + 全部子流程注册关系
- 统计节点总数（从 processResult.json 累加 usetotal），供规模判定使用

**1.2 结构提取**（standard / deep）
- 运行 `scripts/extract_nodes.py extract <project_path>` 生成 `.extracted_nodes/`
- 对每个 JSON 流程文件提取：节点(`graphData.nodes[]`)、边(`graphData.edges[]`)、全局变量(`global_vars[]`)
- 已知组件按 `references/ipa_format.md` 提取字段；未知组件走启发式提取。报告中标注 `[启发式提取]`

quick 模式：不运行 extract_nodes.py，直接读取主流程 JSON + 一级子流程 JSON 的 `graphData.nodes[]` 和 `global_vars[]` 获取顶层结构。

**1.3 大文件策略**（standard / deep 模式下生效）
- 单 JSON >50KB 时，使用 Explore agent 并行提取。每个 agent 读取一个 flow 文件，提取 `component_id`, `show_name`, `properties(input_params)`, `edges[]`
- 批量分析：每个项目一个 Explore agent 做层 1，主 Agent 串行做层 2

### 层 2: 代码与业务分析

**目的**：对每个代码节点做深度分析，重建执行序列，解读业务逻辑，匹配已知设计模式。

**2.1 代码深度分析**

*Python 节点* (`script_python_execute`)：
1. 读取 `.extracted_nodes/N*_*.py` 全文
2. `python_input_variables` → 变量来源映射（上游节点/全局参数/硬编码）
3. `_script_execute_result` → 下游消费者映射
4. 分析：数据结构、处理步骤、业务规则、Excel I/O、异常处理、边界情况

*JavaScript 节点* (`browser_inject_js_code`)：
1. 读取 `.extracted_nodes/N*_*.js` 全文，分类：DOM操作/数据提取/状态检测/值注入
2. 记录 DOM 选择器、`window` 变量、数据交接给 Python 的方式

*standard 模式大项目降级*（节点数 > 200）：代码按 `code_hash` 去重后每组分析一次（manifest 中相同 hash 的节点标注 N{n1}, N{n2}... 共享相同代码），代码行数 < 5 的节点归组分析。

*quick 模式*：跳过本步骤。

**2.2 流程序列重建**
- 从边构建邻接表 → 找入口节点 → 正向遍历 → 标注分支/循环/异常/子流程调用 → 按业务逻辑分阶段
- quick 模式：仅重建主流程顶层序列，子流程标注为黑盒

**2.3 业务逻辑解读 + 设计模式匹配**

业务维度：

| 维度 | 内容 |
|------|------|
| 业务目标 | 解决什么问题？日/月/一次性？输入→输出？ |
| 领域术语表 | 代码中每个专业术语的业务含义 |
| 数据血缘 | Resources/ → 各处理节点 → output/ 端到端 ASCII 流程图，标注每步文件名和列 |
| 业务规则目录 | JOIN键+优先级、筛选条件(含表达式)、计算公式(数学+代码)、决策树 |
| Excel I/O 表 | 每个读写的文件：节点、Sheet、列 |

**设计模式匹配**（新增）：读取 `references/patterns_universal.md`。对每个模式，逐节点检查"必须命中（AND）"的 checklist：
- 全部 must_hit 满足 → `[高置信度匹配: UP-0X 模式名]`
- >=50% must_hit + >=1 optional → `[中置信度匹配: UP-0X 模式名]`

在报告中输出：
- §2.2 节点分析中标注匹配模式及置信度
- §5.1 输出"识别到的设计模式"表格（模式 | 匹配节点 | 置信度 | 说明）
- §5.3 对每个识别到的模式评价其适用性（是否符合当前场景的最佳实践/是否有更优替代）

quick 模式：仅一句话推测业务目标，跳过其余维度和模式匹配。

### 层 3: 产物生成

**目的**：生成分析报告和可选审计报告，执行质量自检。

**3.1 报告生成**

严格遵循 `references/report_template.md`。关键质量标准：
- §2.2 每个代码节点独立分析，使用模板的表格+代码块格式
- §4.5 Resources/ 下所有 Excel 文件必须出现
- §5.1 含组件统计表 + 识别到的设计模式表（若层 2.3 有匹配）
- §5.3 优化建议必须具体可操作（非泛泛的"提升性能"）
- §5.4 风险项含严重程度、触发条件、具体缓解措施
- Appendix B 含完整节点索引

quick 模式精简：只输出 §1（含 Mermaid 图）、§2（仅阶段划分+主流程顶层序列，无代码节点详解）、§3（参数清单）、§5.1（组件统计）、Appendix B（代码节点索引）。

**3.2 质量自检**

检查清单：
- 全部报告：§1 Mermaid 图 | §3 全部 globalParams 列出 | §5.1 组件统计 | §5.1.x 启发式组件 | Appendix B 节点索引
- standard/deep 附加：§2 每个 Python 节点已分析 | §4 数据血缘+术语表+Excel I/O | §5.3 优化建议 | §5.4 风险矩阵
- deep 模式附加：§6 自动化审计摘要存在

**3.3 并行审计**（仅 deep 模式）

启动 6 个 Explore agent 并行审计（详见 `references/audit_swarm.md`）：Security / Performance / API Contracts / Error Handling / Testing Gaps / Documentation Drift。完成后 Merge Agent 合并为 `AUDIT_REPORT.md`，主报告 §6 输出摘要表。

---

## 可选后置步骤

### 代码审计（独立命令）

完成分析后，可运行 `/rpa-ipa-audit {project_path}` 对提取的代码节点进行 6 维并行审计。详见 `SKILL_audit.md` 和 `references/audit_swarm.md`。
