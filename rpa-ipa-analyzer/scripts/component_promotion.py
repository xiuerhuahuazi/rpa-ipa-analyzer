#!/usr/bin/env python3
"""
Component promotion script — promotes a heuristic component to known status.

Inserts a new elif branch into extract_nodes.py's extract_node_meta dispatch
based on sampled field structure. Creates .bak backup before editing.

Usage:
    python component_promotion.py --component-id web_http_request \
        --fields '["url","method","headers","body","timeout"]' \
        [--code-field script_body]  [--input-field input_vars]  [--output-field output_vars]
"""
import argparse
import json
import shutil
import sys
from datetime import date
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
EXTRACT_NODES_PY = SKILL_DIR / "scripts" / "extract_nodes.py"
COUNTS_FILE = SKILL_DIR / "component_usage_counts.json"


def parse_value_type(field_id: str, sample_value: str) -> str:
    """Guess the param_id to use based on field name heuristics."""
    if field_id in ("python_script", "js_code", "script_body", "code", "exec_script"):
        return "code"
    if field_id in ("python_input_variables", "js_input_variables",
                    "input_variables", "input_vars"):
        return "input_vars"
    if field_id in ("_script_execute_result", "output_variables", "output_vars"):
        return "output_vars"
    return "param"


def generate_elif_branch(component_id: str, fields: list[str],
                         code_field: str | None = None,
                         input_field: str | None = None,
                         output_field: str | None = None) -> str:
    """Generate the elif branch code for a new component type."""
    # Auto-detect if not specified
    if not code_field:
        for f in fields:
            if f in ("python_script", "js_code", "script_body", "code", "exec_script"):
                code_field = f
                break
    if not input_field:
        for f in fields:
            if f in ("python_input_variables", "js_input_variables",
                     "input_variables", "input_vars"):
                input_field = f
                break
    if not output_field:
        for f in fields:
            if f in ("_script_execute_result", "output_variables", "output_vars"):
                output_field = f
                break

    ext = ".js" if ("js" in component_id.lower() or "browser" in component_id.lower()) else ".py"
    code_field_str = code_field or "NONE"

    lines = []
    lines.append(f"    elif component_id == \"{component_id}\":")
    if code_field:
        lines.append(f"        code = find_param(props, \"input_params\", \"{code_field}\")")
    else:
        lines.append("        code = None  # TODO: identify code field")
    if input_field:
        lines.append(f"        input_vars = find_param(props, \"input_params\", \"{input_field}\") or {{}}")
    else:
        lines.append("        input_vars = {}  # TODO: identify input variable field")
    if output_field:
        lines.append(f"        output_vars_raw = find_param(props, \"output_params\", \"{output_field}\") or {{}}")
    else:
        lines.append("        output_vars_raw = {}  # TODO: identify output variable field")
    lines.append("        output_vars = output_vars_raw if isinstance(output_vars_raw, dict) else {}")
    lines.append(f"        ext = \"{ext}\"")
    lines.append(f"        code_field = \"{code_field_str}\"")
    lines.append("        js_category = None")
    lines.append(f"        # TODO: 根据实际语义调整上述字段映射")

    return "\n".join(lines)


def backup():
    """Create .bak copy of extract_nodes.py."""
    bak = EXTRACT_NODES_PY.with_suffix(".py.bak")
    shutil.copy2(EXTRACT_NODES_PY, bak)
    print(f"[备份] {EXTRACT_NODES_PY} → {bak}")


def insert_branch(component_id: str, branch_code: str) -> bool:
    """Insert the elif branch into extract_node_meta's dispatch chain."""
    content = EXTRACT_NODES_PY.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)

    # Find the else: line that dispatches to extract_node_meta_heuristic
    # Pattern: else: / # comment / return extract_node_meta_heuristic(...)
    insert_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "else:" and i > 0:
            # Look forward within 5 lines for extract_node_meta_heuristic
            for ahead in range(1, 6):
                if i + ahead >= len(lines):
                    break
                if "extract_node_meta_heuristic" in lines[i + ahead]:
                    insert_idx = i
                    break
            if insert_idx is not None:
                break

    if insert_idx is None:
        print("[错误] 未找到插入位置 — 无 else: extract_node_meta_heuristic 模式？")
        return False

    # Insert the branch before the else
    branch_lines = branch_code.splitlines(keepends=True)
    for j, bl in enumerate(branch_lines):
        lines.insert(insert_idx + j, bl + "\n")

    EXTRACT_NODES_PY.write_text("".join(lines), encoding="utf-8")
    print(f"[完成] 已插入 {component_id} 分支到 extract_node_meta")
    return True


def update_counts(component_id: str):
    """Mark component as promoted in component_usage_counts.json."""
    if not COUNTS_FILE.exists():
        print("[警告] component_usage_counts.json 不存在，跳过计数更新")
        return
    data = json.loads(COUNTS_FILE.read_text(encoding="utf-8"))
    comp = data.get("components", {}).get(component_id)
    if comp:
        comp["promoted"] = True
        comp["promotion_date"] = str(date.today())
    else:
        data["components"][component_id] = {
            "count": 3,
            "first_seen": str(date.today()),
            "last_seen": str(date.today()),
            "sample_fields": [],
            "sample_flow_path": "",
            "promoted": True,
            "promotion_date": str(date.today()),
        }
    COUNTS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[完成] component_usage_counts.json 已更新: {component_id}.promoted = true")


def main():
    parser = argparse.ArgumentParser(
        description="将启发式组件升级为已知类型，更新 extract_nodes.py"
    )
    parser.add_argument("--component-id", required=True,
                        help="IPA Studio 组件 ID")
    parser.add_argument("--fields", required=True,
                        help="采样字段名的 JSON 数组")
    parser.add_argument("--code-field", default=None,
                        help="包含代码的字段名（自动检测）")
    parser.add_argument("--input-field", default=None,
                        help="输入变量字段名（自动检测）")
    parser.add_argument("--output-field", default=None,
                        help="输出变量字段名（自动检测）")

    args = parser.parse_args()
    fields = json.loads(args.fields)

    print(f"[升级] 组件: {args.component_id}, 字段: {fields}")

    # 1. Backup
    backup()

    # 2. Generate and insert branch
    branch = generate_elif_branch(
        args.component_id, fields,
        args.code_field, args.input_field, args.output_field
    )
    print(f"[生成] 分支代码:\n{branch}")

    if not insert_branch(args.component_id, branch):
        sys.exit(1)

    # 3. Update counts
    update_counts(args.component_id)

    print(f"\n[成功] 组件 {args.component_id} 已升级为已知类型")
    print(f"  请手动更新 SKILL.md 和 ipa_format.md 中的组件列表")


if __name__ == "__main__":
    main()
