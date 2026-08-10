# IPA Studio JSON Format Reference

## 文件分类

**Flow 文件**（含 `graphData`）：顶层 key — `graphData`, `global_vars`, `blocks`, `sequences`, `processInfo`

**Config 文件**（无 `graphData`）：`project.json`, `globalParams.json`, `globalParamsAll.json`, `processResult.json`, `globalSelector.json`

## Flow 文件结构

### nodes[] 节点对象
```
{ id, component_id, name, show_name,
  properties[{ type:"base_params"|"input_params"|"output_params",
                params[{ id, name, value_type, value }] }],
  left, top }
```

### 各组件类型字段提取

| 组件 | 路径 |
|------|------|
| `script_python_execute` | input_params: `python_script`(代码), `python_input_variables`(入参dict); output_params: `_script_execute_result`(出参dict) |
| `browser_inject_js_code` | input_params: `js_code`(JS代码); 选择器/等待超时同 UI 节点 |
| `sub_process` | input_params: `process_path`, `input_variables`, `output_variables` |
| `process_if` | input_params: `conditions[{condition, route_endpoint, show}]` |
| `process_exception_catch` | input_params: `try_node`, `catch_node`, `finally_node` |
| `process_assignment` | input_params: `assignment_target_target`, `assignment_target_value` |
| `process_iterator` | input_params: `_loop_datatable`, `_loop_row_data`, `loop_node` |
| `process_while` | input_params: `loop_condition`, `loop_node`, `loop_type` |
| `process_exception_throw` | input_params: `exception_throw_info` |
| `process_delay` | input_params: `delay_time` |
| `log_task` | input_params: `log_level`, `print_text` |
| `datetime_now` | input_params: `datetime_now_type`, `_datetime_define_pattern`; output_params: `datetime_now_result` |
| `application_kill_process` | input_params: `name_or_id`, `process_name` |
| **Excel 组件** | |
| `excel_open_or_create` | input_params: `file_path`, `visible`; output_params: `excel_object` |
| `excel_cell_write` | input_params: `excel_object`, `visible`, `sheet_name`, `cell_location`, `cell_data`, `is_save` |
| `excel_cell_img` | input_params: `excel_object`, `visible`, `sheet_name`, `cell_reference`, `image_path`, `image_width`, `image_height`, `is_save` |
| `excel_save` | input_params: `excel_object`, `visible`, `save_method` |
| `excel_close` | input_params: `excel_object`, `is_close_process`, `is_save`, `visible` |
| **浏览器组件** | |
| `browser_open` | input_params: `browser_type`, `open_url`, `over_time`, `_browser_maximize`, `_browser_load_wait` 等 |
| `browser_attachment` | input_params: `browser_type`, `over_time`, `_browser_maximize`, `_browser_auto_adapt` |
| `browser_load_wait` | input_params: `rpa_browser`, `over_time` |
| `browser_tag_create` | input_params: `open_url`, `rpa_browser`, `_browser_load_wait`, `_browser_load_wait_time` |
| `browser_tag_close` | input_params: `rpa_browser` |
| `browser_tag_switch` | input_params: `match_content`, `match_target`, `rpa_browser` |
| `browser_back` | input_params: `rpa_browser` |
| `browser_refresh` | input_params: `rpa_browser`, `_browser_load_wait`, `_browser_load_wait_time` |
| `browser_download_path_get` | input_params: `browser_type`, `rpa_browser`; output_params: `browser_download_path_name` |
| **UI 交互节点** | |
| `mouse_single_click` | input_params: `ui_element`(CSS/XPath), `text_content`/`input_text`, `key_combination`, `wait_timeout` |
| `keyboard_text_input` | input_params: `element_type`, `interface_selector`, `content`, `content_type`, `rpa_browser`, `waiting_time` |
| `keyboard_hot_send` | input_params: `hot_keys`, `other_key`, `run_count`, `waiting_time`, `window_indicator` |
| `mouse_move` | input_params: `_coordinate_x`, `_coordinate_y`, `cursor_position`, `element_type`, `interface_selector` |
| **UI 检测/截图组件** | |
| `ui_element_exist` | input_params: `window_indicator`, `time_out` |
| `ui_target_exist` | input_params: `time_out`, `uee_select_element`, `window_indicator` |
| `ui_element_wait_show` | input_params: `rpa_browser`, `waiting_time`, `window_indicator` |
| `full_screen_shot` | input_params: `save_file_path` |
| `interface_text_get` | input_params: `element_type`, `interface_selector`, `rpa_browser`, `result_text_name` |
| `table_data_fetch` | input_params: `columns`, `target_selector`, `extract_data`, `page_trun_selector`, `page_trun_num` |
| **文件操作组件** | |
| `file_is_exist` | input_params: `file_path`; output_params: `file_exist_result` |
| `file_delete` | input_params: `file_path` |
| `file_list_get` | input_params: `_dir_source_path`; output_params: `_file_list_object` |
| `list_add_data` | input_params: `src_list`, `value`; output_params: `new_list` |
| `dialog_message_box` | input_params: `button_pressed`, `button_set`, `content`, `title` |

### edges[] 边对象
```
{ sourceNode, targetNode, source, target }
```

### global_vars[] 流程域变量/参数管理
```
{ id, key, description, value }
```

每个 **flow JSON**（主流程、业务流程、生成成本基础表流程、生成预提表流程、数据处理与透视报告、COMMON 子流程等）各自有一份 `global_vars`。  
**同域节点共享**；不同 flow 互不共享，除非经 `sub_process` 的 `input_variables` / `output_variables` 显式传递。

IPA 运行时解析出参/入参映射时，**value 指向的名字必须已在该流程 `global_vars` 中登记**，否则报错类似：

`输出属性【出参定义】解析失败，变量/参数表内不存在【raise_node_error】`

### 变量作用域与脚本映射（必读）

```
globalParams.json          ← 项目级参数（全项目）
       │ 仍须映射进脚本
       ▼
flow.global_vars[]         ← 流程域变量表（每流程一份）
       │
       ├─ script_python_execute.python_input_variables
       │     { 脚本内变量名 : global_vars.key }
       ├─ script_python_execute._script_execute_result
       │     { 脚本内出参名 : global_vars.key }   ← value 侧必须已登记
       └─ sub_process.input_variables / output_variables
             父流程变量 ↔ 子流程变量（两侧 global_vars 均需有 key）
```

| 规则 | 说明 |
|------|------|
| 先登记再映射 | 新增 helper/DF/路径等到出参前，先 `global_vars.append({id, key, description, value:""})` |
| 脚本不能直接看见流程变量 | 必须写进 `python_input_variables`（JS 同理） |
| 项目参数同理 | `globalParams.json` 的 key 进脚本也要节点映射，不是自动注入 |
| 禁止类作出参 | 自定义 Exception/class 不要放进 `_script_execute_result`；函数/数据对象可以 |
| apply 不管变量 | `extract_nodes.py apply` 只写代码字段；`global_vars` 与映射须手改或另做补丁 |

**示例（业务流程产出工具函数 → 成本基础表子流程使用）：**

1. `业务流程.json` `global_vars` 增加 `raise_node_error` 等  
2. `common_function` 节点 `_script_execute_result` 增加 `"raise_node_error": "raise_node_error"`  
3. 子流程节点 `input_variables` 传入同名  
4. `生成成本基础表流程.json` `global_vars` 也增加同名  
5. 各 PY 节点 `python_input_variables` 注入 `"raise_node_error": "raise_node_error"`

## Config 文件结构

### project.json
```
process_list[{ is_main_process, process_path, process_name, process_id, designer_version }]
project_info{ project_name, project_id, main_process_path, version, designer_version, executor_version }
```

### globalParams.json
```
[{ id, key, type:"输入文件"|"下拉单选"|..., description, value, allValues }]
```
项目级参数表（与流程 `global_vars` 不同域）。全项目共享，但 **Python/JS 节点仍须通过入参映射** 才能在脚本内使用。

### globalParamsAll.json
```
[{ paramId, paramName, paramType(6=下拉/8=文件/10=字符串), paramValue, paramDesc }]
```

### processResult.json
```
[{ id, name, version, usetotal }]
```

## 常见架构模式

**三层（纯数据处理）**：主流程(编排+异常) → 业务流程(路由+处理) → COMMON(复用基础设施)

**两层（含 Web 自动化）**：主流程(编排+Web操作) → 子流程(登录/数据/上传) → COMMON

## 未知组件处理

当遇到不在上表中的 `component_id` 时，走启发式提取（`extract_nodes.py` 自动处理）：

1. 从 `processResult.json` 发现所有组件类型
2. 对未知类型：遍历 `properties[]` 中所有 `type:"input_params"` 和 `type:"output_params"` 的 group，提取全部 `(id, value)` 对
3. 值按类型标记不截断：`<code:N lines>` / `<str:N chars>` / `<dict:N keys>` / `<list:N items>`
4. 记录到 `component_usage_counts.json`（计数、采样字段、来源）
5. 报告中在 §5.1.x 汇总，节点在 Appendix B 标注 `[启发式]`
6. 同一组件使用 >= 3 次：自动提示升级为已知类型，更新 `extract_nodes.py`、`ipa_format.md`、`SKILL.md`
