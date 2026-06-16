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
| `process_assignment` | input_params: `variable_name`, `variable_value` |
| UI 节点 | input_params: `ui_element`(CSS/XPath), `text_content`/`input_text`, `key_combination`, `wait_timeout` |

### edges[] 边对象
```
{ sourceNode, targetNode, source, target }
```

### global_vars[] 全局变量
```
{ id, key, description, value }
```

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
