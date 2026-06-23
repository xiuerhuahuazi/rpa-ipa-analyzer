# Changelog

## 3.0.0 (2026-06-23)

### Breaking Changes
- **SKILL.md 架构重写**：7 个 Phase → 4 个能力层模型（层0自校准→层1项目建模→层2代码与业务分析→层3产物生成）。新旧对照见设计文档
- **extract_nodes.py 模块拆分**：单文件 581 行拆为 10 个模块（`scripts/_extract/`），CLI 入口改为子命令体系（`extract`/`list`/`stats`/`trace`/`compare`）。旧调用语法 `extract_nodes.py <path>` 需改为 `extract_nodes.py extract <path>`
- **manifest.json schema 升级到 2.0**：新增 `edges` 字段和 `_schema_version`，旧 manifest 不兼容新 trace 子命令
- **`references/design_patterns.md` 删除**：被 `patterns_universal.md`（通用 Checklist 模式）+ `patterns_domain.md`（领域参考案例）替代

### Added
- **三级分析深度**：quick（宏观架构，不运行 extract_nodes）/ standard（完整分析，默认）/ deep（含 6 维并行审计）。自然语言识别（"快速概览"/"深度分析"）+ 规模自动判定（>=500 节点推荐 quick）
- **独立审计命令 `/rpa-ipa-audit`**：`SKILL_audit.md`，审计作为 opt-in 重型操作，零默认成本
- **edges 收集与变量血缘追踪**：`extract_nodes.py` 新增 `edges` 收集（`manifest.json` 中 3372 条边）+ `trace` 子命令（BFS 追踪变量从生产者到消费者）
- **`@desc` 自动填充**：`headers.py` 新增 `_auto_desc()`，提取的代码文件不再使用 `[待补充]` 占位符，自动生成含依赖/I/O/模式的有意义描述
- **通用设计模式 Checklist 格式**：`patterns_universal.md`（5 个 UP-0X 模式，Must/Should 条件）+ `patterns_domain.md`（5 个领域参考案例）
- **component_usage_counts.json confidence 系统**：每个组件附带 confidence（low/medium/high）+ 废弃清理提示
- **promotion_config.json**：升级策略可配置（any_domain/global_only/cross_domain）
- **evals 回归测试框架**：golden manifest diff + assertions.py + evals_runner.py（50/50 PASS）

### Changed
- **extract_nodes.py**：新增 `list`/`stats`/`trace`/`compare` CLI 子命令
- **report_template.md**：新增 §6 自动化审计章节、深度标注、章节↔层映射表、设计模式表格
- **ipa_format.md**：组件表从 7 行扩展到 40+ 行，按 Excel/浏览器/UI交互/UI检测/文件操作分类
- **rpa-ipa-update**：同步 v3.0.0 — CLI 子命令语法、快照格式扩展（含 input_vars/output_vars）、变量变化检测（Step 3）、trace 子命令用于连锁影响追踪（Step 5）

### Fixed
- 启发式节点不再落盘独立 `.heuristic.json` 文件（2815→0，数据全量在 manifest.json 中）
- `extract_node_meta` 清理 16 个空 elif 分支（TODO 桩），统一走启发式回落
- `KNOWN_COMMON_NODE_IDS` 死代码删除（node_id 跨项目命中率 0/3123）
- `BOILERPLATE_PATTERNS` / `JS_CATEGORY_PATTERNS` / `STORAGE_UTILS_SIGNATURE` 硬编码删除
- `@desc: [待补充]` 占位符修复为自动生成（308 文件零残留）
- `component_usage_counts.json` 73 组件全部 promote 或标记 confidence

### Removed
- `references/design_patterns.md`（14 个混排模式 → 被通用/领域分离替代）
- `scripts/_cli/`（空目录 — 子命令逻辑内联在 extract_nodes.py dispatch 中）
- `.heuristic.json` 独立文件输出（仅保留 manifest.json 中的全量索引）

---

## 2.0.0 (2026-06-16)

### Breaking Changes
- **目录重组**：`SKILL.md`、`scripts/`、`references/`、`evals/` 从根目录移入 `rpa-ipa-analyzer/` 子目录
- 安装路径变更：`cp SKILL.md` → `cp rpa-ipa-analyzer/SKILL.md`（详见 README.md）

### Added
- **新增 `rpa-ipa-update` 增量更新技能**：代码变更后仅重分析变更节点，局部更新报告而非全量重建
  - 基于 `code_hash` 机制精确定位变更节点
  - `.extracted_nodes/manifest.json` + `hash_snapshot.txt` 快照对比
  - 变更→报告章节映射表（§2.2/§3/§4/Appendix B）
  - 增量 vs 全量自动判断（≤5节点增量，>5节点建议全量）
- 新增顶层 `README.md` 覆盖双技能安装与使用说明

### Changed
- **Token 优化**：4 个核心文件总 Token 消耗从 ~7,700t 降至 ~3,460t（节省 55%）

## 1.1.0 (2026-05-26)

- Excel input file sheet/row detection
- Enhanced report Section 3.1 and Section 4.5
- Added Phase 1.1: Excel Input File Detection

## 1.0.0 (2026-05-12)

- Initial release: IPA Studio RPA project analysis with Mermaid flowcharts
- Python/JS code extraction, functional tagging, JS classification
- Recursive block traversal, UI node extraction, cross-project deduplication
- 14 RPA design patterns documented
