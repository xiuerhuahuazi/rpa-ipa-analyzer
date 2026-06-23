from __future__ import annotations
from typing import Optional
from .core import find_param, code_hash, count_code_lines, _describe_value
from .result_types import NodeMeta


def extract_python_node(node: dict, flow_path: str) -> Optional[NodeMeta]:
    component_id = node.get("component_id", "")
    node_id = node.get("id", "")
    show_name_raw = node.get("properties", [{}])[0].get("params", [{}])[0].get("value", "")
    show_name = show_name_raw.strip('"') if isinstance(show_name_raw, str) else str(show_name_raw)
    props = node.get("properties", [])
    code = find_param(props, "input_params", "python_script")
    input_vars = find_param(props, "input_params", "python_input_variables") or {}
    output_vars_raw = find_param(props, "output_params", "_script_execute_result") or {}
    output_vars = output_vars_raw if isinstance(output_vars_raw, dict) else {}
    if not code or not isinstance(code, str) or len(code.strip()) < 10:
        return None
    return NodeMeta(
        node_id=node_id, component_id=component_id, show_name=show_name,
        code=code, code_field="python_script", input_vars=input_vars,
        output_vars=output_vars, ext=".py", flow_path=flow_path,
        code_hash=code_hash(code), code_lines=count_code_lines(code),
        extraction_method="structured",
    )


def extract_js_node(node: dict, flow_path: str) -> Optional[NodeMeta]:
    component_id = node.get("component_id", "")
    node_id = node.get("id", "")
    show_name_raw = node.get("properties", [{}])[0].get("params", [{}])[0].get("value", "")
    show_name = show_name_raw.strip('"') if isinstance(show_name_raw, str) else str(show_name_raw)
    props = node.get("properties", [])
    code = find_param(props, "input_params", "js_code")
    input_vars = find_param(props, "input_params", "js_input_variables") or {}
    output_vars_raw = find_param(props, "output_params", "_script_execute_result") or {}
    output_vars = output_vars_raw if isinstance(output_vars_raw, dict) else {}
    if not code or not isinstance(code, str) or len(code.strip()) < 10:
        return None
    return NodeMeta(
        node_id=node_id, component_id=component_id, show_name=show_name,
        code=code, code_field="js_code", input_vars=input_vars,
        output_vars=output_vars, ext=".js", flow_path=flow_path,
        code_hash=code_hash(code), code_lines=count_code_lines(code),
        extraction_method="structured",
    )


def extract_node_meta(node: dict, flow_path: str) -> Optional[NodeMeta]:
    component_id = node.get("component_id", "")
    if component_id == "script_python_execute":
        return extract_python_node(node, flow_path)
    elif component_id == "browser_inject_js_code":
        return extract_js_node(node, flow_path)
    else:
        return extract_node_meta_heuristic(node, flow_path)


def extract_node_meta_heuristic(node: dict, flow_path: str) -> Optional[NodeMeta]:
    component_id = node.get("component_id", "")
    node_id = node.get("id", "")
    props = node.get("properties", [])
    if not props:
        return None
    show_name_raw = props[0].get("params", [{}])[0].get("value", "")
    show_name = show_name_raw.strip('"') if isinstance(show_name_raw, str) else str(show_name_raw)
    all_input_params: dict[str, str] = {}
    all_output_params: dict[str, str] = {}
    for prop in props:
        prop_type = prop.get("type", "")
        params = prop.get("params", [])
        if not isinstance(params, list):
            continue
        for param in params:
            pid = param.get("id", "")
            pval = param.get("value")
            if pid and pval is not None and pval != "":
                if prop_type == "input_params":
                    all_input_params[pid] = _describe_value(pval)
                elif prop_type == "output_params":
                    all_output_params[pid] = _describe_value(pval)
    if not all_input_params and not all_output_params:
        return None
    return NodeMeta(
        node_id=node_id, component_id=component_id, show_name=show_name,
        code="", code_field="", input_vars=all_input_params,
        output_vars=all_output_params, ext="", flow_path=flow_path,
        code_hash="", code_lines=0, extraction_method="heuristic",
    )
