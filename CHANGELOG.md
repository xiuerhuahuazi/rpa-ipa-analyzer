# Changelog

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
  - `SKILL.md`（analyzer）：~2,390t → ~1,007t（-58%）— 删除重复组件列表，Phase 2/3/5 压缩为结构化清单
  - `report_template.md`：~1,892t → ~982t（-48%）— 删除"必须包含"元描述
  - `ipa_format.md`：~1,633t → ~573t（-65%）— JSON 示例压缩为紧凑表格
  - `SKILL.md`（update）：~1,826t → ~898t（-51%）— bash 模板压缩

## 1.1.0 (2026-05-26)

- Excel input file sheet/row detection: when global params contain `paramType: 8` (输入文件) pointing to `.xlsx`/`.xls`, analysis now traces and reports `sheet_name`, `header`/`skiprows`, and `usecols` from `pd.read_excel()` calls
- Enhanced report Section 3.1 with dedicated Excel input parameter sub-table (sheet, start row, column range, reading node)
- Enhanced report Section 4.5 Excel I/O mapping table with "来源" and "数据起始行" columns
- Added Phase 1.1: Excel Input File Detection step to analysis workflow
- Added `ipa_format.md` section documenting the 4-step Excel input file tracing process

## 1.0.0 (2026-05-12)

- IPA Studio RPA project analysis with Mermaid flowchart generation
- Python and JavaScript code extraction from JSON flow files
- Functional tagging system (BOILERPLATE/SKELETON/GLUE/BUSINESS/SHARED/CROSS)
- JS injection classification (DOM Navigation/Form Fill/State Detection/Data Extraction/Page Cleanup)
- Recursive `process_function_block` traversal (3 levels deep)
- UI automation node metadata extraction
- Cross-project code deduplication via MD5 hashing
- 14 common RPA design patterns documented
- Financial RPA code quality checklist
- Adaptive architecture depth detection (single-file to multi-nested)
- Multi-project batch analysis with cross-project comparison
