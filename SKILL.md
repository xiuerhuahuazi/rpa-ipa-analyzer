---
name: rpa-ipa-analyzer
description: Analyze IPA Studio RPA projects to produce comprehensive business and code analysis reports with Mermaid flowcharts. Use when the user asks to "analyze this RPA project", "understand this IPA Studio flow", "extract Python code from flow", "map the business logic", "generate a RPA analysis report", or "audit this RPA project". Handles data-processing projects (Python/pandas) AND web automation projects (JavaScript injection, browser operations, UI element interaction), or mixed projects combining both. Supports hierarchical JSON flow files, embedded Python+JavaScript code extraction, global parameter mapping, multi-project batch analysis, and parallel 6-lens code audit swarm (security, performance, error handling, API contracts, testing gaps, documentation drift) with automated report merging.
---

# IPA Studio RPA Project Analyzer

Produce professional, structured business-and-code analysis reports for IPA Studio RPA projects. The output must be a complete Markdown report saved to `{project_path}/分析报告_{project_name}.md`.

## When to Use

- User says "analyze this RPA project" or "analyze this IPA Studio project"
- User asks to "understand the flow", "map the business logic", "extract code from the flows"
- User wants an "analysis report" for an RPA/automation project
- User says "audit this RPA project", "code audit", "security review this flow", or "check code quality"
- User wants a comprehensive audit after analysis (Phase 8 auto-triggers after report generation)

## Project Type Classification

Before analysis, classify from `processResult.json`:

| Component Pattern | Project Type |
|---|---|
| Dominated by `script_python_execute` + `log_task` | **Data Processing** |
| Dominated by `mouse_single_click` + `keyboard_text_input` + `browser_inject_js_code` | **Web Automation** |
| Both in significant numbers | **Mixed** |

Adapt analysis focus accordingly, but the report structure (from `references/report_template.md`) is mandatory for all types.

---

## Phase 0: Common Pattern Recognition — Run Before Phase 1

Before detailed analysis, identify cross-project patterns to avoid redundant work:

### 0.1 Functional Tagging System (Replaces node_id-based COMMON Detection)

Since IPA Studio node IDs are dynamically generated and vary across projects, do NOT rely on hardcoded node_id matching. Instead, the extraction script (`extract_nodes.py`) classifies each code-bearing node by code signature + show_name keywords + structural features.

Nodes are tagged with one of these categories:

| Category | Detection | Meaning | Report Treatment |
|----------|-----------|---------|-----------------|
| **BOILERPLATE** | Pattern match on code signature + show_name keywords | Infrastructure/scaffolding shared across projects (e.g., folder init, random delay, Tkinter dialogs, Chrome config, dependency install) | Single-line mention in flow path; no re-analysis needed |
| **SKELETON** | code_lines ≤ 5 | Minimal node with no substantive logic | Brief mention; skip code block |
| **GLUE** | code_lines < 15, no business keywords in show_name | Parameter conversion / data reshaping between nodes | Short analysis |
| **BUSINESS** | Default | Domain-specific business logic | Full deep analysis in Section 2.2 |
| **SHARED:Nx** | Same code_hash as node Nx within the project | Identical code, same-project duplicate | Note duplication, analyze once |
| **CROSS:proj** | Same code_hash in multiple projects | Cross-project shared code | Reference by name |

The extraction script's `manifest.json` includes `functional_category`, `functional_tag`, and `functional_tags` fields for each node. Use these to determine analysis depth in Section 2.2.

### 0.2 read_excel_advanced Detection

Present in 100% of analyzed IPA Studio financial projects. Recognise by: multi-engine fallback (`openpyxl→xlrd→odf→pyxlsb`), Unnamed column cleanup, string stripping. Note which variant is used, then reference by name — do not re-analyze in each report.

### 0.3 Architecture Depth Detection (Adaptive)

Do NOT assume a fixed architecture. Parse `project.json`'s `process_list` to build the actual file hierarchy tree. Common patterns observed:

| Architecture | Files | Typical Scenario |
|---|---|---|
| **Single-file** | 主流程.json only | Simple linear task |
| **Two-layer** | 主流程.json → 主业务.json | Most common pattern (4 of 5 test projects) |
| **Two-layer + business dir** | 主流程.json → 业务流程/*.json + 主业务.json | Complex multi-module projects |
| **Two-layer + tests** | 主流程.json → 主业务.json + 测试流程.json | Projects with test/debug flows |
| **Three-layer + COMMON** | 主流程.json → 业务.json → COMMON/*.json | Template-based projects with shared infrastructure |
| **Multi-nested** | Nested process_function_block chains | Deeply modular projects |

Also detect the interaction mode from `processResult.json` component distribution:
- **API-driven**: `web_http_request` present, no `browser_inject_js_code` or few `mouse_single_click`
- **Browser+JS**: `browser_inject_js_code` + `browser_attachment` dominate
- **UI-automation**: `mouse_single_click` + `keyboard_text_input` with many `app_user_interaction` nodes
- **Mixed**: Multiple interaction modes present

Report the detected architecture and interaction mode in Section 1.1.

### 0.4 Code Duplication Quick Scan

Check for:
- Same `show_name` appearing in multiple sub-flows (e.g., 新增/修改/下架 sharing JS nodes)
- Multi-version nodes (`show_name` containing [1.0]/[2.0])
- Same `node_id` as another project's business node (indicates copy-paste)

### 0.5 JS Injection Classification (Web/Mixed Projects)

For every `browser_inject_js_code` node, classify into one of:

| Category | Detection Pattern | Analysis Focus |
|----------|------------------|----------------|
| **DOM Navigation** | `querySelector().click()`, `location.href` | Which UI element, navigation target |
| **Form Fill** | `input.value =`, `select.value =`, `dispatchEvent` | What data injected, from which Python var |
| **State Detection** | returns boolean, checks element existence | Condition checked, timeout handling |
| **Data Extraction** | `window.xxx =`, `localStorage.getItem` | What extracted, handoff to Python |
| **Page Cleanup** | `window.close()`, `element.remove()` | State being reset |

Report category distribution in Section 2.3. JS nodes in the same category with only parameter differences are candidates for deduplication.

### 0.6 process_function_block Nesting Analysis

IPA Studio's `process_function_block` nodes are logical containers with nested sub-flows. The extraction script now recursively traverses `flow.blocks[]` to extract code nodes from within function blocks. This is critical for complex projects where the main business logic resides in nested blocks.

For each block, the script records:
- Block name (from block metadata or node `show_name`)
- Parent block chain (for nested blocks: `"父块/子块"`)
- All code-bearing nodes within the block

This enables full visibility into deeply modular projects (e.g., 物流核查 project with 16 function blocks → 3 levels deep).

---

## Analysis Workflow

### Phase 1: Project Discovery

Read these files in parallel:

```
Read: {project_path}/project.json      → Process registry, sub-process hierarchy
Read: {project_path}/globalParams.json  → All runtime parameters with types and values
Read: {project_path}/processResult.json → Component usage statistics → classify project type
Read: {project_path}/globalParamsAll.json → Parameter schema (deployment template)
```

**Output of this phase**: Complete process hierarchy tree, parameter inventory, component type list with counts.

### Phase 2: Flow Structure Extraction

For each JSON flow file (main + all sub-processes), extract:

**Nodes** — from `graphData.nodes[]`, capture these fields for EVERY node:
- `id`, `component_id`, `show_name`, `left`/`top` (flow position)
- `properties[]`: find the entry with `type: "input_params"` — it contains code/config
- For `script_python_execute`: extract `python_script`, `python_input_variables`, `_script_execute_result`
- For `browser_inject_js_code`: extract `js_code` field
- For `sub_process`: extract `process_path`, `input_variables`, `output_variables`
- For `process_if`: extract `conditions` array with branch expressions
- For `process_exception_catch`: extract try/catch/finally endpoints
- For UI nodes (`mouse_single_click`, `keyboard_text_input`, etc.): extract element selectors, input text, wait timeouts
- For `process_assignment`: extract variable name and value

**Edges** — from `graphData.edges[]`, capture `sourceNode`, `targetNode`, `source`, `target`. Reconstruct the complete execution DAG.

**Global Vars** — from `global_vars[]`, all variable declarations with descriptions.

**Large files (>50KB)**: Spawn Explore agents in parallel, one per file, reading with offset/limit.

### Phase 2.5: Node Code Persistence (MANDATORY)

**CRITICAL**: After Phase 2 completes, run the extraction script to persist all code-bearing nodes as standalone files. This avoids re-reading large JSON flow files in subsequent analysis, saving significant tokens.

```bash
python3 {skill_path}/scripts/extract_nodes.py "{project_path}" --force
```

This creates `{project_path}/.extracted_nodes/` containing:
- `manifest.json` — complete node index with metadata: seq, node_id, show_name, file, flow_file, component, input_vars, output_vars, **functional_category**, **functional_tag**, **functional_tags**, **code_hash**, **code_lines**, **js_category**, **parent_block**
- `ui_nodes.json` (embedded in manifest) — all UI automation nodes with selectors, input text, wait timeouts
- `N{n}_{flow_shortname}_{sanitized_name}.py` — each `script_python_execute` node as a standalone `.py` file
- `N{n}_{flow_shortname}_{sanitized_name}.js` — each `browser_inject_js_code` node as a standalone `.js` file

The script also:
- Recursively extracts nodes from `process_function_block` nested content (via `flow.blocks[]`)
- Extracts UI automation node metadata (selectors, inputs, timeouts)
- Tags all nodes with functional categories (BOILERPLATE/SKELETON/GLUE/BUSINESS)
- Detects within-project and cross-project code duplicates

Each extracted file has a `@node` docstring header containing: node_id, flow origin, input/output variable mappings, functional category/tag, and a description placeholder.

**File size comparison** (typical):
| Source | Size | Content |
|--------|------|---------|
| JSON flow files (6 files) | ~250 KB | Full DAG (nodes + edges + global_vars + config) |
| Extracted `.py`/`.js` (5-20 files) | ~32-100 KB | Only code + metadata headers |
| `manifest.json` | ~2-10 KB | Node index with I/O mappings, tags, UI nodes |

### Phase 3: Code Deep Analysis

This is the most important phase. For EVERY code-bearing node:

**Read scripts from `.extracted_nodes/` first** — if `manifest.json` exists, read the `.py`/`.js` files directly instead of re-parsing large JSON flow files. Only fall back to JSON parsing when `.extracted_nodes/` doesn't exist or flow files have been updated since `extracted_at` date.

**Skip COMMON nodes**: If `manifest.json` marks a node as `is_common: true`, skip deep analysis. Reference by name in the flow path only.

#### Python nodes (`script_python_execute`)
1. Read the extracted `.py` file (or fallback: parse JSON for `python_script`)
2. Identify: imports, function definitions, main execution logic
3. Map `python_input_variables` to their sources (upstream node output / global parameter / hardcoded), using `manifest.json` for quick lookup
4. Map `_script_execute_result` to downstream consumers
5. Analyze:
   - **Data structures**: all DataFrames, lists, dicts created
   - **Processing steps**: sequential operations with purpose
   - **Business rules**: filter conditions, exclusion lists, calculation formulas, priority logic
   - **Excel I/O**: which Resources file is read/written, which sheet, which columns
   - **Error handling**: try/except blocks, null checks, boundary conditions
   - **Edge cases**: what happens on empty input, missing columns, type mismatches
6. **Financial projects**: Verify money amounts use `Decimal` (not `float`), file paths use `pathlib.Path`

#### JavaScript nodes (`browser_inject_js_code`)
1. Read the extracted `.js` file (or fallback: parse JSON for `js_code`)
2. Classify: DOM Navigation / Form Fill / State Detection / Data Extraction / Page Cleanup (use `js_category` from manifest if available)
3. Note: DOM selectors used, `window` variables set/read, data handoff to Python
4. **Deduplication check**: If same JS node appears in multiple sub-flows (same `code_hash`), note the duplication

### Phase 4: Flow Sequence Reconstruction

1. Build adjacency maps from edges
2. Find all entry points（`process_start` nodes, nodes with no incoming edges）
3. Walk forward following edges
4. Annotate each step:
   - Branch conditions（from `process_if`）
   - Loop boundaries（from `process_iterator`, `process_while`）
   - Exception paths（from `process_exception_catch`）
   - Sub-process call/return points
5. Group nodes into **logical phases**（data loading → cleaning → merging → calculation → export）

### Phase 5: Business Logic Interpretation

This connects code to business meaning. Must cover:

1. **Business objective**: What problem does this RPA solve? Where does it fit（daily/monthly/ad-hoc）? What goes in, what comes out?

2. **Domain concept glossary**: Every specialized term used in the code. For financial projects: 预提/COA/NBHT/费用池 etc. For web projects: platform names, business entity types.

3. **Data lineage**（端到端数据流转）: Trace every input file from `Resources/` through each processing node to `output_file/`. Draw ASCII flow diagram. Map specific columns read/written at each step.

4. **Business rules catalog**: Every rule found in code:
   - JOIN/match keys and priority
   - Filter/exclusion conditions（with actual expressions）
   - Calculation formulas（math notation + code implementation）
   - Decision logic trees（like 推荐操作 conditions）

5. **Excel I/O mapping table**: Every file read or written, by which node, which sheet, which columns.

### Phase 6: Report Generation

Write the final report to `{project_path}/分析报告_{project_name}.md`.

**CRITICAL**: Follow `references/report_template.md` exactly. Every section in that template is mandatory.

Key quality standards:
- Every code node gets individual analysis in Section 2.2
- Section 2.2 uses the exact table + code block format from the template
- Every Mermaid diagram has a text description above it
- All Excel files from Resources/ are accounted for in Section 4.5
- Section 5.3 optimization suggestions are specific and actionable（not generic "improve performance"）
- Risk items in Section 5.4 include severity, trigger conditions, and concrete mitigations
- Appendix B includes a complete node index

### Phase 7: Quality Self-Check

Before declaring done, verify:
- [ ] Phase 2.5 extraction script ran successfully — `.extracted_nodes/manifest.json` exists
- [ ] COMMON nodes identified and marked (not re-analyzed in Section 2.2)
- [ ] read_excel_advanced recognized as universal pattern (not re-analyzed)
- [ ] JS nodes classified by category (web/mixed projects)
- [ ] Money columns using Decimal verified (financial projects)
- [ ] Code duplication rate calculated (multi-variant projects)
- [ ] Multi-version nodes compared (when v1.0 and v2.0 exist)
- [ ] All 5 major sections present
- [ ] Mermaid flowchart in Section 1
- [ ] Every `script_python_execute` node analyzed individually in Section 2
- [ ] Every `browser_inject_js_code` node analyzed (web projects)
- [ ] All globalParams listed with usage locations in Section 3
- [ ] Complete data lineage diagram in Section 4
- [ ] Business concept glossary in Section 4
- [ ] Excel I/O mapping table in Section 4
- [ ] Component stats with interpretation in Section 5
- [ ] Optimization suggestions by category in Section 5
- [ ] Risk matrix in Section 5
- [ ] Complete node index in Appendix B
- [ ] Node index seq numbers match `.extracted_nodes/manifest.json` seq numbers
- [ ] Phase 8 parallel audit launched and completed
- [ ] `audit_findings/` directory contains all 6 agent JSON files
- [ ] `AUDIT_REPORT.md` generated with executive summary, heatmap, and remediation estimates

### Phase 8: Parallel Code Audit (MANDATORY after report generation)

After the main analysis report is generated, launch a 6-agent parallel audit swarm. Each agent targets `.extracted_nodes/` and writes findings to `{project_path}/audit_findings/<agent_name>.json`.

The 6 audit lenses:
1. **Security** — secrets, eval/exec, injection, path traversal, sanitization
2. **Performance** — blocking I/O, memory, unbatched ops, pandas anti-patterns, win32com overhead
3. **API Contracts** — function sig vs docstring, cross-node variable contracts, `_旧` breaking changes
4. **Error Handling** — bare except, swallowed exceptions, missing file checks, COM leaks, div-by-zero
5. **Testing Gaps** — coverage per module, complex untested functions, dead code (`_旧` nodes)
6. **Documentation Drift** — `@desc` [待补充], ghost/phantom params, `@tag` misclassification

**Launch**: All 6 agents simultaneously (one message, 6 Agent tool calls).

**Merge**: When all 6 complete, launch a merge agent that reads all finding files → deduplicates → resolves severity conflicts → generates `{project_path}/AUDIT_REPORT.md` with:
1. Executive Summary (top-5 findings + severity counts)
2. Heatmap of Issues by File
3. Prioritized Finding List
4. Estimated Remediation Effort (hours)
5. Cross-Reference Index

**Full agent prompts and merge template**: See `references/audit_swarm.md`.

**Audit report template**: See `references/report_template.md` Section "AUDIT_REPORT.md 模板".

---

## Financial RPA Code Quality Checklist

For financial/accounting projects, verify these during Phase 3 analysis:

- [ ] All money amounts use `Decimal`, not `float` (critical for accuracy)
- [ ] All file paths use `pathlib.Path`, not string concatenation
- [ ] Excel reading uses the project's `read_excel_advanced` wrapper (multi-engine fallback)
- [ ] Output files are timestamped to prevent accidental overwrite
- [ ] Key columns are validated before processing (missing column detection)
- [ ] Empty/NaN department names are normalized (not left as "nan" in filenames)
- [ ] Sheet names are sanitized for Excel's 31-char limit (`[ ] : \ / ? *`)
- [ ] Print-ready outputs have proper page setup (A4, landscape, margins)
- [ ] File name parts are sanitized for Windows/Linux compatibility

---

## Common RPA Design Patterns

Recognize these 14 patterns during analysis. Full descriptions in `references/design_patterns.md`.

| # | Pattern | Key Signal | Typical Scenario |
|---|---------|------------|------------------|
| 1 | Template-Based Excel | `openpyxl.load_workbook()` + cell fill + `save()` | Pre-formatted Excel output |
| 2 | Multi-Source Merge | Multiple `pd.read_excel()` → `pd.merge()` chain | Data enrichment pipeline |
| 3 | Dual-Mode (Browser vs API) | `if mode` branch → JS vs HTTP components | SSCM/China Mobile systems |
| 4 | COA-Based Sheet Split | Sequential filter chains → multiple `to_excel()` | Financial report splitting |
| 5 | Web Form Auto-Fill | JS `input.value =` + Excel-row-driven data | OA system automation |
| 6 | SSCM Token + API | `StorageUtils` in JS → Bearer token → HTTP API | China Mobile integrations |
| 7 | OCR CAPTCHA | `ddddocr` → `classify()` → form input | Government login bypass |
| 8 | FTP Data Sync | `ftplib` → pandas upsert → FTP upload | Cross-system data sync |
| 9 | Dual Notification | `email_smtp_send` + `send_message_other_network` | Result delivery |
| 10 | Government API Cert | `requests.Session()` + `.gov.cn` + CAPTCHA | Certificate verification |
| 11 | Offline Dep Install | `pip install` from local `.whl` | Air-gapped deployment |
| 12 | CSS Cascading Form | `keyboard_text_input` → `mouse_click` → `keyboard` | OA cascading dropdowns |
| 13 | UI Coordinate Click | `ui_get_target_location` → `pyautogui.click()` | Fallback automation |
| 14 | Chrome Prefs Modify | `Chrome/Preferences` JSON + `taskkill` | Browser state reset |

When a pattern is detected, note it in the node analysis and suggest optimization if applicable.

---

## Handling Large Files

IPA Studio flow files can be 4MB+ (single-line JSON). Strategy:

1. Phase 1 config files are always small — read directly
2. For large flow files, spawn Explore agents in parallel:
   ```
   Agent description: "Extract {flow_name}"
   prompt: "Read {file_path} in sections. For EVERY node extract:
   - component_id, show_name, properties (especially input_params with code)
   For EVERY edge extract: sourceNode→targetNode.
   For browser_inject_js_code: extract FULL js_code.
   For script_python_execute: extract FULL python_script."
   ```
3. Synthesize agent results, then do Phase 3-5 inline（analysis requires full context）

## Batch Analysis

For multiple projects: spawn one Explore agent per project for Phase 1-2 in parallel, then synthesize and do deep analysis on each sequentially.

**Enhanced batch workflow** (when analyzing 3+ projects):

1. Run `extract_nodes.py --force` on all projects first
2. Load all manifests and compare `code_hash` fields across projects
3. Identify cross-project shared code (same hash, different projects)
4. Tag CROSS: references in individual reports
5. Generate a cross-project comparison table in the batch analysis report:
   - Nodes per project, classified by functional category
   - Shared nodes across projects
   - Architecture patterns detected
   - Common design patterns used

---

## Component Type Reference

See `references/ipa_format.md` for the complete component type catalog, including:
- Scripting (2 types): `script_python_execute`, `browser_inject_js_code`
- Browser (7 types), UI Automation (12 types), Flow Control (16 types)
- File & System (6 types), Network & Data (4 types)
- Extraction patterns for each type's code/config fields
