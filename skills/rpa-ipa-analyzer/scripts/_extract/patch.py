"""Patch IPA flow JSON beyond code bodies.

`apply` deliberately rewrites only ``python_script`` / ``js_code``, leaving
``global_vars``, ``python_input_variables``, ``_script_execute_result`` and
``sub_process.input_variables`` untouched. SKILL.md tells the agent that those
"须另补丁" -- this module is that patch, so the fix no longer has to be
hand-written per project.

Two capabilities:

* :func:`patch_mapping` -- set/remove a node's input & output variable mappings
  and register missing flow ``global_vars`` keys. Enforces the variable rules
  from SKILL.md, most importantly that an output mapping's *flow variable* must
  already be declared in that flow's ``global_vars``.
* :func:`remove_node` -- delete a dead node, refusing unless it is provably
  unreferenced (no edges, and no other node mentions its id).

Both back up the flow file first and re-serialise in the file's original style.
"""
from __future__ import annotations

import json
import random
import string
from pathlib import Path
from typing import Any

from .apply import backup_flow, find_node_by_id
from .core import find_param

_ID_ALPHABET = string.ascii_letters + string.digits + "-_"


def _new_ipa_id() -> str:
    """Generate an id shaped like IPA Studio's own (10 chars, e.g. 'zPZZ0v0q-y')."""
    return "".join(random.choice(_ID_ALPHABET) for _ in range(10))


def dump_flow_text(raw: str, flow: dict) -> str:
    """Re-serialise ``flow`` preserving the original newline and separator style."""
    nl = "\r\n" if "\r\n" in raw else "\n"
    seps = (",", ":")
    if ", " in raw[:2000] and ': "' in raw[:2000]:
        seps = (", ", ": ")
    out = json.dumps(flow, ensure_ascii=False, separators=seps)
    if raw.endswith(nl) and not out.endswith(nl):
        out += nl
    elif raw.endswith("\n") and not out.endswith("\n"):
        out += "\n"
    return out


def load_manifest(project: Path) -> dict:
    mf = project / ".extracted_nodes" / "manifest.json"
    if not mf.exists():
        raise SystemExit("错误: manifest.json 不存在，请先运行 extract")
    return json.loads(mf.read_text(encoding="utf-8"))


def resolve_node(manifest: dict, node_ref: dict) -> dict:
    """Find a manifest node by ``{"seq": n}`` or ``{"node_id": id}``."""
    seq = node_ref.get("seq")
    node_id = node_ref.get("node_id")
    for n in manifest.get("nodes", []):
        if node_id is not None and n.get("node_id") == node_id:
            return n
        if seq is not None and int(n.get("seq", -1)) == int(seq):
            return n
    what = node_id if node_id is not None else f"N{seq}"
    raise SystemExit(f"错误: manifest 中找不到节点 {what}")


def load_flow(project: Path, flow_rel: str) -> tuple:
    """Return (flow_path, raw_text, parsed_dict) for a flow file."""
    flow_path = project / flow_rel
    if not flow_path.exists():
        # manifests may store either separator style
        flow_path = project / flow_rel.replace("\\", "/")
    if not flow_path.exists():
        raise SystemExit(f"错误: 流程文件不存在: {flow_rel}")
    raw = flow_path.read_text(encoding="utf-8")
    return flow_path, raw, json.loads(raw)


def flow_var_keys(flow: dict) -> set:
    return {g.get("key") for g in (flow.get("global_vars") or []) if g.get("key")}


def project_param_keys(project: Path) -> set:
    """Keys declared in globalParams.json (either a top-level array or an object)."""
    p = project / "globalParams.json"
    if not p.exists():
        return set()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return set()
    if isinstance(data, list):
        return {d.get("key") for d in data if isinstance(d, dict) and d.get("key")}
    if isinstance(data, dict):
        inner = data.get("globalParams") or data.get("params")
        if isinstance(inner, list):
            return {d.get("key") for d in inner if isinstance(d, dict) and d.get("key")}
        return {k for k in data if not str(k).startswith("_")}
    return set()


def ensure_global_var(flow: dict, key: str, description: str = "") -> bool:
    """Register ``key`` in this flow's global_vars[] when absent.

    Returns True when a new entry was appended.
    """
    gv = flow.setdefault("global_vars", [])
    for g in gv:
        if g.get("key") == key:
            return False
    gv.append({"id": _new_ipa_id(), "key": key, "description": description, "value": ""})
    return True


def io_param_ids(node: dict) -> tuple:
    """Discover the node's input-variable and output-variable param ids.

    IPA uses ``python_input_variables`` / ``_script_execute_result`` for Python
    nodes, but JS nodes differ, so discover rather than hard-code.
    """
    in_id = out_id = None
    for g in node.get("properties") or []:
        gtype = g.get("type")
        for p in g.get("params") or []:
            pid = p.get("id") or ""
            if gtype == "input_params" and (pid.endswith("input_variables") or pid == "input_variables"):
                in_id = in_id or pid
            if gtype == "output_params" and (pid.endswith("script_execute_result") or pid == "script_execute_result"):
                out_id = out_id or pid
    return in_id, out_id


def _as_dict(value: Any) -> dict:
    return dict(value) if isinstance(value, dict) else {}


def _pair(text: str) -> tuple:
    if "=" not in text:
        raise SystemExit(f"错误: 需要 脚本内名=流程变量名 形式，收到: {text}")
    k, v = text.split("=", 1)
    k, v = k.strip(), v.strip()
    if not k or not v:
        raise SystemExit(f"错误: 映射两侧都不能为空: {text}")
    return k, v


def patch_mapping(
    project: Path,
    node_ref: dict,
    set_inputs: list,
    set_outputs: list,
    del_inputs: list,
    del_outputs: list,
    global_var_needs: list,
    description: str = "",
    dry_run: bool = False,
) -> dict:
    """Apply I/O mapping and global_vars changes to one node. Returns stats."""
    manifest = load_manifest(project)
    mnode = resolve_node(manifest, node_ref)
    flow_rel = mnode.get("flow_file")
    node_id = mnode.get("node_id")
    flow_path, raw, flow = load_flow(project, flow_rel)
    node = find_node_by_id(flow, node_id)
    if node is None:
        raise SystemExit(f"错误: 流程 {flow_rel} 中找不到节点 {node_id}")

    in_id, out_id = io_param_ids(node)
    if not in_id:
        raise SystemExit(f"错误: 节点 {node_id} 没有可识别的输入变量定义字段")

    stats = {"flow": flow_rel, "node_id": node_id, "seq": mnode.get("seq"),
             "input_added": [], "output_added": [], "removed": [],
             "global_vars_added": [], "warnings": []}

    # --- 1. register any requested global_vars first, so output validation passes
    for key in global_var_needs:
        if ensure_global_var(flow, key, description):
            stats["global_vars_added"].append(key)

    declared = flow_var_keys(flow)
    params = project_param_keys(project)

    # --- 2. inputs
    if set_inputs or del_inputs:
        before = _as_dict(find_param(node.get("properties", []), "input_params", in_id))
        after = dict(before)
        for item in set_inputs:
            k, v = _pair(item)
            after[k] = v
            stats["input_added"].append(f"{k}={v}")
            if v not in declared and v not in params:
                stats["warnings"].append(
                    f"入参 {k} 映射到 '{v}'，它既不在本流程 global_vars 也不是 globalParams 参数"
                )
        for k in del_inputs:
            if after.pop(k, None) is not None:
                stats["removed"].append(f"input:{k}")
        _write_param(node, "input_params", in_id, after)

    # --- 3. outputs (hard constraint: value must be declared in THIS flow's global_vars)
    if set_outputs or del_outputs:
        if not out_id:
            raise SystemExit(f"错误: 节点 {node_id} 没有可识别的出参定义字段")
        before = _as_dict(find_param(node.get("properties", []), "output_params", out_id))
        after = dict(before)
        for item in set_outputs:
            k, v = _pair(item)
            if v not in declared:
                raise SystemExit(
                    f"错误: 出参 value '{v}' 未在流程 {flow_rel} 的 global_vars 中登记。\n"
                    f"      IPA 运行时会报「出参定义解析失败，变量/参数表内不存在【{v}】」。\n"
                    f"      请先补登记（本命令加 --ensure-global-var {v}）或改用已登记的 key。"
                )
            after[k] = v
            stats["output_added"].append(f"{k}={v}")
        for k in del_outputs:
            if after.pop(k, None) is not None:
                stats["removed"].append(f"output:{k}")
        _write_param(node, "output_params", out_id, after)

    out_text = dump_flow_text(raw, flow)
    if dry_run:
        stats["dry_run"] = True
        return stats

    bak = backup_flow(flow_path, "mapping")
    stats["backup"] = str(bak)
    # open() rather than Path.write_text: `newline=` on write_text needs 3.10.
    with open(flow_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(out_text)
    return stats


def _write_param(node: dict, group_type: str, param_id: str, value: dict) -> None:
    for g in node.get("properties") or []:
        if g.get("type") != group_type:
            continue
        for p in g.get("params") or []:
            if p.get("id") == param_id:
                p["value"] = value
                return
    raise SystemExit(f"错误: 无法写入 {group_type}/{param_id}")


def remove_node(
    project: Path,
    node_ref: dict,
    force: bool = False,
    dry_run: bool = False,
) -> dict:
    """Delete a dead node after proving nothing references it."""
    manifest = load_manifest(project)
    mnode = resolve_node(manifest, node_ref)
    flow_rel = mnode.get("flow_file")
    node_id = mnode.get("node_id")
    flow_path, raw, flow = load_flow(project, flow_rel)

    nodes = flow.get("graphData", {}).get("nodes") or []
    node = find_node_by_id(flow, node_id)
    if node is None:
        raise SystemExit(f"错误: 流程 {flow_rel} 中找不到节点 {node_id}")

    stats = {"flow": flow_rel, "node_id": node_id, "seq": mnode.get("seq"),
             "show_name": _show_name(node), "refs": [], "removed": False}

    # --- prove it is unreferenced
    edges = flow.get("graphData", {}).get("edges") or []
    edge_refs = [e for e in edges if node_id in (e.get("sourceNode"), e.get("targetNode"))]
    for e in edge_refs:
        stats["refs"].append(f"edge {e.get('sourceNode')} -> {e.get('targetNode')}")

    for other in nodes:
        if other.get("id") == node_id:
            continue
        blob = json.dumps(other, ensure_ascii=False)
        if node_id in blob:
            stats["refs"].append(f"被节点 {other.get('id')} 的字段引用")

    if stats["refs"] and not force:
        raise SystemExit(
            f"错误: 节点 {node_id} 仍被引用，拒绝删除（--force 可强制）：\n  "
            + "\n  ".join(stats["refs"])
        )

    nodes_before = len(nodes)
    nodes.remove(node)
    out_text = dump_flow_text(raw, flow)
    stats["nodes_before"] = nodes_before
    stats["nodes_after"] = len(nodes)

    if dry_run:
        stats["dry_run"] = True
        return stats

    bak = backup_flow(flow_path, "remove-node")
    stats["backup"] = str(bak)
    with open(flow_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(out_text)
    stats["removed"] = True
    return stats


def _show_name(node: dict) -> str:
    for g in node.get("properties") or []:
        if g.get("type") != "base_params":
            continue
        for p in g.get("params") or []:
            if p.get("id") == "show_name":
                return str(p.get("value") or "")
    return str(node.get("description") or "")
