---
name: rpa-ipa-analyzer
description: Analyze IPA Studio RPA projects to produce comprehensive business and code analysis reports with Mermaid flowcharts. Use when the user asks to "analyze this RPA project", "understand this IPA Studio flow", "extract Python code from flow", "map the business logic", or "generate a RPA analysis report". Handles data-processing projects (Python/pandas) AND web automation projects (JavaScript injection, browser operations, UI element interaction), or mixed projects combining both. Supports hierarchical JSON flow files, embedded Python+JavaScript code extraction, global parameter mapping, and multi-project batch analysis.
---

# IPA Studio RPA Project Analyzer

Produce professional, structured business-and-code analysis reports for IPA Studio RPA projects. The output must be a complete Markdown report saved to `{project_path}/分析报告_{project_name}.md`.

## When to Use

- User says "analyze this RPA project" or "analyze this IPA Studio project"
- User asks to "understand the flow", "map the business logic", "extract code from the flows"
- User wants an "analysis report" for an RPA/automation project

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

Recognize these patterns during analysis and note them in the report:

### Pattern 1: Template-Based Excel Generation
Excel templates in `Resources/` with predefined formatting. Code uses openpyxl to open template → fill data → save as new file with dynamic name.

### Pattern 2: Multi-Source Merge Pipeline
Load all data from multiple Excel files/sheets upfront → sequential left-join enrichment → final merge. Use `@dataclass` for loaded data container.

### Pattern 3: Dual-Mode Operation (Browser vs API)
Global parameter switches between browser automation and HTTP API. Browser mode needs JS token extraction; API mode needs pre-configured tokens.

### Pattern 4: COA-Based Sheet Splitting
Split data into sheets by COA (核算科目) priority rules: A → B → C → D → E. Each rule filters a subset; remainder passes to next rule.

### Pattern 5: Web Form Auto-Fill (Data-Driven JS)
Excel row → Python parsing → sequential JS injection per form field → submit. Shared JS nodes across 新增/修改/下架 sub-flows.

### Pattern 6: SSCM Token Extraction + API Calling
JS `sessionStorage` extraction (via `StorageUtils` wrapper class) → Python uses bearer_token for authenticated API calls. Browser mode uses JS-extracted tokens; headless mode needs pre-configured tokens. Common in China Mobile SSCM system integrations.

### Pattern 7: OCR CAPTCHA Auto-Recognition
Use `ddddocr` library to recognize CAPTCHA images from government/enterprise login pages → Python inputs the recognized text into login forms. Typically paired with proxy configuration for API access. Found in government certificate verification and logistics system login flows.

### Pattern 8: FTP Data Synchronization
Python FTP reads remote CSV/Excel → pandas upsert (insert-or-update by key columns) → FTP uploads updated data back. Uses `ftplib` with standard auth. Common in data sharing between RPA agents and central databases.

### Pattern 9: Dual-Channel Notification (Email + SMS)
Results delivered via SMTP email AND/or SMS (via `send_message_other_network` HTTP API). Different output channels for single vs batch query modes. SMS uses pre-registered message templates.

### Pattern 10: Government API Certificate Verification
Python HTTP requests to government public APIs (应急管理部 cx.mem.gov.cn, 住建部) for personnel certificate verification. Requires session cookie management, CAPTCHA handling, and proxy routing. Supports both single-query and batch-Excel modes.

### Pattern 11: Offline Dependency Installation
`pip install` from local `.whl` files in `Resources/` directory for air-gapped deployment environments. Python `subprocess` or `pip.main()` to install xlrd/xlwt/ddddocr offline. Used when RPA executor machines lack internet access.

### Pattern 12: CSS Cascading Form Fill
Sequential UI interaction: keyboard input → mouse click dropdown → keyboard select option. Used for Chinese enterprise OA systems with cascading form controls (一级/二级业务领域 selection). Requires coordinated `keyboard_text_input` → `mouse_single_click` → `keyboard_text_input` chains.

### Pattern 13: UI Coordinate-Based Simulated Click
`ui_get_target_location` captures element screen coordinates → Python `pyautogui.click(x, y)` performs the actual click. Used as fallback when direct UI automation selectors fail on complex dialogs or non-standard controls.

### Pattern 14: Chrome Preferences Modification
Python reads/writes Chrome's `Preferences` JSON file to disable popup dialogs, set download directories, and configure browser behavior before automation starts. Includes process kill (`taskkill /f /im chrome.exe`) and file permission changes (`os.chmod`). Used to ensure clean browser state for web automation.

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

### Scripting (2 types)
| component_id | Code Field | Purpose |
|---|---|---|
| `script_python_execute` | `python_script` | Python data processing |
| `browser_inject_js_code` | `js_code` | JS injected into browser console |

### Browser (7 types)
`browser_attachment`, `browser_navigation`, `browser_load_wait`, `browser_refresh`, `browser_cookie_get`, `window_close`

### UI Automation (12 types)
`mouse_single_click`, `keyboard_text_input`, `keyboard_hot_send`, `ui_element_wait_show`, `ui_element_wait_vanish`, `ui_element_exist`, `interface_text_get`, `dialog_message_box`, `window_minimize`, `ui_get_target_location`, `mouse_wheel_scroll`, `app_user_interaction`

### Flow Control (16 types)
`process_start`, `log_task`, `sub_process`, `process_if`, `process_iterator`, `process_while`, `process_break`, `process_assignment`, `process_delay`, `process_retry`, `process_exception_catch`, `process_exception_throw`, `process_exception_throw_again`, `process_exception_termination`, `process_function_block`, `process_continue`

### File & System (6 types)
`file_list_get`, `file_output_result`, `file_delete`, `file_dir_delete`, `system_project_path_get`, `table_data_fetch`

### Network & Data (4 types)
`web_http_request`, `datatable_iterator`, `email_smtp_send`, `send_message_other_network`

### Newly Added Types (from cross-project analysis)

| component_id | Category | Purpose |
|---|---|---|
| `app_user_interaction` | UI Automation | 通用交互弹框（单选、多选、文本输入、文件上传、提示） |
| `process_function_block` | Flow Control | 逻辑容器（内含完整嵌套子流程） |
| `email_smtp_send` | Network & Data | SMTP 邮件发送（含附件） |
| `send_message_other_network` | Network & Data | 异网短信发送（HTTP API + 消息模板） |
| `table_data_fetch` | File & System | 浏览器表格数据抓取 |
| `ui_get_target_location` | UI Automation | 获取 UI 元素坐标位置（配合 pyautogui） |
| `mouse_wheel_scroll` | UI Automation | 模拟鼠标滚轮 |
| `process_continue` | Flow Control | 循环中跳过当前迭代 |
| `window_close` | Browser | 关闭浏览器窗口 |

See `references/ipa_format.md` for detailed field extraction patterns for each type.
