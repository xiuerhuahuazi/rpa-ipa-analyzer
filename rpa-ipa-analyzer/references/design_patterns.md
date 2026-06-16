# Common RPA Design Patterns

Recognize these patterns during analysis and note them in the report. Patterns help explain WHY the code is structured as it is and suggest optimization opportunities.

## Pattern 1: Template-Based Excel Generation

Excel templates in `Resources/` with predefined formatting. Code uses openpyxl to open template → fill data → save as new file with dynamic name.

**Detection**: `openpyxl.load_workbook()` + cell value assignment + `save()` with constructed filename.

## Pattern 2: Multi-Source Merge Pipeline

Load all data from multiple Excel files/sheets upfront → sequential left-join enrichment → final merge. Use `@dataclass` for loaded data container.

**Detection**: Multiple `pd.read_excel()` calls at function start → `pd.merge()` chain → final `to_excel()`.

## Pattern 3: Dual-Mode Operation (Browser vs API)

Global parameter switches between browser automation and HTTP API. Browser mode needs JS token extraction; API mode needs pre-configured tokens.

**Detection**: `if mode == "browser"` branching → `browser_inject_js_code` vs `web_http_request` components.

## Pattern 4: COA-Based Sheet Splitting

Split data into sheets by COA (核算科目) priority rules: A → B → C → D → E. Each rule filters a subset; remainder passes to next rule.

**Detection**: Sequential filter chains with remainder tracking → multiple `to_excel(sheet_name=...)` calls.

## Pattern 5: Web Form Auto-Fill (Data-Driven JS)

Excel row → Python parsing → sequential JS injection per form field → submit. Shared JS nodes across 新增/修改/下架 sub-flows.

**Detection**: `browser_inject_js_code` nodes with `input.value =` patterns + variable input from Excel data.

## Pattern 6: SSCM Token Extraction + API Calling

JS `sessionStorage` extraction (via `StorageUtils` wrapper class) → Python uses bearer_token for authenticated API calls. Browser mode uses JS-extracted tokens; headless mode needs pre-configured tokens. Common in China Mobile SSCM system integrations.

**Detection**: `StorageUtils` in JS code → `web_http_request` with `Authorization: Bearer` header.

## Pattern 7: OCR CAPTCHA Auto-Recognition

Use `ddddocr` library to recognize CAPTCHA images from government/enterprise login pages → Python inputs the recognized text into login forms. Typically paired with proxy configuration for API access. Found in government certificate verification and logistics system login flows.

**Detection**: `import ddddocr` → `classify()` call → `keyboard_text_input` with OCR result.

## Pattern 8: FTP Data Synchronization

Python FTP reads remote CSV/Excel → pandas upsert (insert-or-update by key columns) → FTP uploads updated data back. Uses `ftplib` with standard auth. Common in data sharing between RPA agents and central databases.

**Detection**: `from ftplib import FTP` → `storlines()`/`retrlines()` calls.

## Pattern 9: Dual-Channel Notification (Email + SMS)

Results delivered via SMTP email AND/OR SMS (via `send_message_other_network` HTTP API). Different output channels for single vs batch query modes. SMS uses pre-registered message templates.

**Detection**: `email_smtp_send` + `send_message_other_network` components in same flow.

## Pattern 10: Government API Certificate Verification

Python HTTP requests to government public APIs (应急管理部 cx.mem.gov.cn, 住建部) for personnel certificate verification. Requires session cookie management, CAPTCHA handling, and proxy routing. Supports both single-query and batch-Excel modes.

**Detection**: `requests.Session()` + government `.gov.cn` URLs + CAPTCHA integration.

## Pattern 11: Offline Dependency Installation

`pip install` from local `.whl` files in `Resources/` directory for air-gapped deployment environments. Python `subprocess` or `pip.main()` to install xlrd/xlwt/ddddocr offline. Used when RPA executor machines lack internet access.

**Detection**: `subprocess.run([sys.executable, '-m', 'pip', 'install', ...])` with `.whl` paths.

## Pattern 12: CSS Cascading Form Fill

Sequential UI interaction: keyboard input → mouse click dropdown → keyboard select option. Used for Chinese enterprise OA systems with cascading form controls (一级/二级业务领域 selection). Requires coordinated `keyboard_text_input` → `mouse_single_click` → `keyboard_text_input` chains.

**Detection**: `keyboard_text_input` → `mouse_single_click` → `keyboard_text_input` edge sequence without intermediate code nodes.

## Pattern 13: UI Coordinate-Based Simulated Click

`ui_get_target_location` captures element screen coordinates → Python `pyautogui.click(x, y)` performs the actual click. Used as fallback when direct UI automation selectors fail on complex dialogs or non-standard controls.

**Detection**: `ui_get_target_location` → `script_python_execute` with `pyautogui.click()`.

## Pattern 14: Chrome Preferences Modification

Python reads/writes Chrome's `Preferences` JSON file to disable popup dialogs, set download directories, and configure browser behavior before automation starts. Includes process kill (`taskkill /f /im chrome.exe`) and file permission changes (`os.chmod`). Used to ensure clean browser state for web automation.

**Detection**: `Chrome/Preferences` path + `taskkill` command + `json.load()`/`json.dump()` on Preferences file.

---

## Pattern Detection in Reports

When a pattern is detected during Phase 3-5 analysis:
1. Note the pattern name in the node's analysis
2. Reference this file for the pattern description
3. In Section 5.3 (优化建议), suggest whether the pattern is appropriate or should be replaced
4. Cross-reference: if the same pattern appears across multiple sub-processes, note the consistency
