# IPA Studio JSON Format Reference

## File Categories

### Flow Files (contain `graphData`)
Top-level keys: `graphData`, `global_vars`, `blocks`, `sequences`, `processInfo`

### Config Files (no `graphData`)
- `project.json` / `project.rpa` — process registry
- `globalParams.json` / `globalParamsAll.json` — runtime parameters
- `processResult.json` — component usage statistics
- `globalSelector.json` — UI element selectors (web automation projects)

## Flow File Structure (`graphData`)

### nodes[] — Each node object:
```
{
  "id": "unique_node_id",
  "component_id": "node_type",       // e.g., "script_python_execute"
  "name": "Chinese type name",
  "show_name": "display label",
  "properties": [                    // array of property groups
    {
      "type": "base_params",         // or "input_params" or "output_params"
      "name": "group name",
      "params": [                    // actual parameters
        {
          "id": "param_id",
          "name": "Chinese param name",
          "value_type": "String|dict|immutable",
          "value": "the actual value or variable reference"
        }
      ]
    }
  ],
  "left": 1234, "top": 567           // visual position
}
```

### Finding Python Scripts
Locate `component_id: "script_python_execute"`, then:
1. In `properties[]`, find entry with `type: "input_params"` and `name: "输入"`
2. In its `params[]`, find `id: "python_script"` → `value` contains the code
3. `id: "python_input_variables"` → `value` is `{var_name: "external_value", ...}`
4. In `properties[]` entry with `type: "output_params"`:
   - `id: "_script_execute_result"` → `value` is `{script_var: "external_var", ...}`

### Finding JavaScript Scripts (`browser_inject_js_code`)
Locate `component_id: "browser_inject_js_code"`, then:
1. In `properties[]`, find entry with `type: "input_params"` and `name: "输入"`
2. In its `params[]`, find `id: "js_code"` → `value` contains the JavaScript code
3. Also check for `id: "js_input_variables"` or similar input variable mappings
4. These scripts execute in the browser console — they have access to `document`, `window`, DOM APIs
5. Common patterns: `document.querySelectorAll()`, `element.click()`, checking page state, extracting data to `window` globals

### Finding UI Automation Nodes
UI automation nodes (`mouse_single_click`, `keyboard_text_input`, etc.) have selectors/targets in their properties. Look for:
- `id: "ui_element"` or `id: "element_selector"` → CSS/XPath selector for the target element
- `id: "text_content"` or `id: "input_text"` → text to type/input
- `id: "key_combination"` → keyboard shortcut for `keyboard_hot_send`
- `id: "wait_timeout"` → timeout in ms for wait nodes

### Finding Process Assignments
`process_assignment` nodes set variables. In `input_params`:
- `id: "variable_name"` → the variable being set
- `id: "variable_value"` → the value expression

### Finding Sub-process Calls
Locate `component_id: "sub_process"`, then:
1. `id: "process_path"` → target flow file path (e.g., `"./业务流程.json"`)
2. `id: "input_variables"` → `{key: value, ...}` mapping to sub-process inputs
3. `id: "output_variables"` → `{sub_out_key: "parent_var", ...}` mapping back

### Finding Conditional Branches
Locate `component_id: "process_if"`, then:
1. `id: "conditions"` → array of `{condition: "expression", route_endpoint: "endpoint_id", show: true/false}`
2. The `route_endpoint` values match edge `target` fields to determine which branch goes where

### Finding Exception Handlers
Locate `component_id: "process_exception_catch"`:
1. `id: "try_node"` → endpoint for normal execution path
2. `id: "catch_node"` → endpoint for exception path
3. `id: "finally_node"` → endpoint for always-execute path

### edges[] — Each edge object:
```
{
  "sourceNode": "source_node_id",
  "targetNode": "target_node_id",
  "source": "endpoint_id_on_source",
  "target": "endpoint_id_on_target",
  "shapeType": "Manhattan"
}
```

### global_vars[] — Variable declarations:
```
{
  "id": "unique_id",
  "key": "variable_name",
  "description": "Chinese description",
  "value": ""                       // typically empty, populated at runtime
}
```

## Config File Structures

### project.json
```json
{
  "process_list": [
    {
      "is_main_process": true/false,
      "process_path": "主流程.json",
      "process_name": "Chinese name",
      "process_id": "unique_id",
      "parent_name": "COMMON" | null,
      "designer_version": "2.1.3.10",
      "executor_version": "2.1.6"
    }
  ],
  "project_info": {
    "project_name": "项目名v1.0.0_2.1.3",
    "project_id": "应用XXXXXXXX",
    "main_process_path": "主流程.json",
    "version": "1.0.0",
    "designer_version": "2.1.6.9",
    "executor_version": "2.1.6",
    "design_model": "dragModel",
    "process_type": "normal"
  }
}
```

### globalParams.json
Array of parameter objects:
```json
[
  {
    "id": "param_id",
    "key": "TARGETS",            // variable name in flow
    "type": "下拉单选",           // widget type
    "description": "中文说明",
    "value": "\"current_value\"",  // current value (JSON-encoded)
    "allValues": "option1,option2" // for dropdowns
  }
]
```

### globalParamsAll.json
Same data, different schema:
```json
[
  {
    "paramId": "Param_N",
    "paramName": "TARGETS",
    "paramType": 6,              // numeric type code
    "paramValue": "value",
    "paramDesc": "中文说明"
  }
]
```

### processResult.json
Component usage aggregation:
```json
[
  {
    "id": "component_type_id",
    "name": "Chinese name",
    "version": "2.1.0",
    "type": 0,
    "usetotal": 93              // total usage count across all flows
  }
]
```

## Extracted Node Files (`.extracted_nodes/`)

Generated by `scripts/extract_nodes.py` after Phase 2. Contains standalone script files with metadata headers, avoiding repeated JSON parsing.

### Directory structure
```
.extracted_nodes/
├── manifest.json              # Complete node index
├── N{n}_{flow}_{name}.py      # script_python_execute nodes
└── N{n}_{flow}_{name}.js      # browser_inject_js_code nodes
```

### manifest.json schema
```json
{
  "project": "项目名",
  "extracted_at": "YYYY-MM-DD",
  "total_nodes": N,
  "nodes": [
    {
      "seq": 1,
      "node_id": "original_json_node_id",
      "show_name": "节点显示名称",
      "file": "N1_主流程_日志类.py",
      "flow_file": "主流程.json",
      "component": "script_python_execute",
      "input_vars": {"code_var": "rpa_var", ...},
      "output_vars": {"code_var": "rpa_var", ...},
      "description": ""
    }
  ]
}
```

### Python node header format (`.py`)
```python
"""
@node: N{seq} — {show_name}
@id: {node_id}
@flow: {flow_file_path}
@input:  var ← source (, ...)
@output: var → target (, ...)
@desc:   [待补充]
"""

{完整 python_script 代码}
```

### JavaScript node header format (`.js`)
```javascript
/**
 * @node: N{seq} — {show_name}
 * @id: {node_id}
 * @flow: {flow_file_path}
 * @input:  var ← source (, ...)
 * @output: var → target (, ...)
 * @desc:   [待补充]
 */

{完整 js_code 代码}
```

### Usage in Phase 3
Instead of re-reading multi-MB JSON flow files to extract code, Phase 3 reads `.py`/`.js` files directly:
- `manifest.json` provides the full node index and I/O variable mappings for quick lookup
- Each `.py`/`.js` file is self-contained with complete code and metadata
- Only fall back to JSON parsing when `.extracted_nodes/` is missing or stale (flow file `update_at` > `extracted_at`)

## Common Patterns

### Three-Layer Architecture (Pure Data Processing)
```
主流程.json        → Orchestration (Logger, work dir, try/catch/finally)
业务流程.json       → Routing (common functions, TARGETS-based branching)  
生成X流程.json     → Heavy data processing (Excel loads, merges, exports)
COMMON/*.json      → Reusable infrastructure (dir create, upload, delete)
```

### Two-Layer with Web Automation
```
主流程.json        → Orchestration + direct web automation steps
业务流程/*.json    → Specialized sub-flows (login, data processing, upload)
COMMON/*.json       → Infrastructure
```

### Parameter Type Codes (globalParamsAll.json)
| Code | Type |
|------|------|
| 6 | 下拉单选 (dropdown) |
| 8 | 输入文件 (input file) |
| 10 | 字符串 (string) |
