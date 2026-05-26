# Changelog

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
