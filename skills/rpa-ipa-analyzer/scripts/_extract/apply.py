#!/usr/bin/env python3
"""Apply edited .extracted_nodes code files back into IPA flow JSON nodes.

Usage (via extract_nodes.py):
    python extract_nodes.py apply <project_path> [--dry-run] [--node N] [--file PATH] [--force]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .core import code_hash, find_param


_HEADER_PY_RE = re.compile(
    r'^\s*"""[\s\S]*?^@node:[\s\S]*?"""\s*\n?',
    re.MULTILINE,
)
_HEADER_JS_RE = re.compile(
    r"^\s*/\*\*[\s\S]*?@node:[\s\S]*?\*/\s*\n?",
    re.MULTILINE,
)
_META_ID_RE = re.compile(r"@id:\s*(\S+)")
_META_FLOW_RE = re.compile(r"@flow:\s*(\S+)")
_META_NODE_RE = re.compile(r"@node:\s*N(\d+)\s*—")


def strip_extracted_header(text: str, ext: str) -> str:
    """Remove the extract-generated @node header; return business code only."""
    if ext == ".js":
        m = _HEADER_JS_RE.match(text)
    else:
        m = _HEADER_PY_RE.match(text)
    if m:
        return text[m.end() :]
    # Fallback: if file starts with docstring containing @node
    if text.lstrip().startswith('"""') and "@node:" in text[:800]:
        end = text.find('"""', 3)
        if end != -1:
            rest = text[end + 3 :]
            return rest[1:] if rest.startswith("\n") else rest
    return text


def parse_file_meta(text: str) -> dict:
    head = text[:1200]
    meta = {
        "node_id": None,
        "flow_path": None,
        "seq": None,
    }
    m = _META_ID_RE.search(head)
    if m:
        meta["node_id"] = m.group(1).strip()
    m = _META_FLOW_RE.search(head)
    if m:
        meta["flow_path"] = m.group(1).strip()
    m = _META_NODE_RE.search(head)
    if m:
        meta["seq"] = int(m.group(1))
    return meta


def detect_newline(sample: str) -> str:
    if "\r\n" in sample:
        return "\r\n"
    return "\n"


def normalize_newlines(text: str, nl: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if nl == "\r\n":
        return text.replace("\n", "\r\n")
    return text


def set_param(properties: list[dict], prop_type: str, param_id: str, value: Any) -> bool:
    """Set param value in-place. Returns True if found and updated."""
    for prop in properties:
        if prop.get("type") != prop_type:
            continue
        for param in prop.get("params", []):
            if param.get("id") == param_id:
                param["value"] = value
                return True
    return False


def find_node_by_id(flow: dict, node_id: str) -> Optional[dict]:
    for node in flow.get("graphData", {}).get("nodes", []):
        if node.get("id") == node_id:
            return node
    return None


def code_field_for_node(node: dict) -> Optional[str]:
    cid = node.get("component_id", "")
    if cid == "script_python_execute":
        return "python_script"
    if cid == "browser_inject_js_code":
        return "js_code"
    # Heuristic fallback: longest code-like string param
    return None


def load_manifest(project: Path) -> dict:
    mf = project / ".extracted_nodes" / "manifest.json"
    if not mf.exists():
        sys.exit(f"错误: 找不到 {mf}，请先 extract")
    return json.loads(mf.read_text(encoding="utf-8"))


def resolve_candidates(
    project: Path,
    manifest: dict,
    node_seqs: list[int],
    file_globs: list[str],
) -> list[dict]:
    """Build candidate list from explicit filters or all structured code nodes."""
    nodes = manifest.get("nodes", [])
    by_seq = {int(n["seq"]): n for n in nodes}
    ed = project / ".extracted_nodes"

    selected: dict[int, dict] = {}

    if node_seqs or file_globs:
        for s in node_seqs:
            if s not in by_seq:
                print(f"[警告] manifest 无序号 N{s}，跳过")
                continue
            selected[s] = by_seq[s]
        for pattern in file_globs:
            matches = list(ed.glob(pattern))
            if not matches:
                # also allow bare filename
                matches = list(ed.glob(Path(pattern).name))
            if not matches:
                print(f"[警告] 无匹配文件: {pattern}")
                continue
            for path in matches:
                if path.suffix not in (".py", ".js"):
                    continue
                # match by filename to manifest
                hit = next((n for n in nodes if n.get("file") == path.name), None)
                if hit:
                    selected[int(hit["seq"])] = hit
                else:
                    # allow orphan file with header meta
                    text = path.read_text(encoding="utf-8")
                    meta = parse_file_meta(text)
                    if not meta["node_id"]:
                        print(f"[警告] {path.name} 无 @id 且不在 manifest，跳过")
                        continue
                    selected[meta.get("seq") or -abs(hash(path.name)) % 10_000_000] = {
                        "seq": meta.get("seq"),
                        "node_id": meta["node_id"],
                        "file": path.name,
                        "flow_file": meta.get("flow_path") or "",
                        "extraction_method": "structured",
                        "show_name": path.stem,
                    }
    else:
        for n in nodes:
            if n.get("extraction_method") != "structured":
                continue
            if not str(n.get("file", "")).endswith((".py", ".js")):
                continue
            selected[int(n["seq"])] = n

    out = []
    for n in selected.values():
        f = n.get("file")
        if not f:
            continue
        p = ed / f
        if not p.exists():
            print(f"[警告] 文件不存在: {p.name}")
            continue
        out.append({**n, "_path": str(p)})
    return sorted(out, key=lambda x: int(x.get("seq") or 0))


def plan_apply(
    project: Path,
    candidates: list[dict],
    force: bool,
) -> list[dict]:
    """Compare file body vs live flow code; return plans with action."""
    flow_cache: dict[str, dict] = {}
    plans = []

    for item in candidates:
        path = Path(item["_path"])
        raw = path.read_text(encoding="utf-8")
        meta = parse_file_meta(raw)
        node_id = meta.get("node_id") or item.get("node_id")
        flow_rel = meta.get("flow_path") or item.get("flow_file")
        if not node_id or not flow_rel:
            plans.append({
                **item,
                "action": "error",
                "reason": "缺少 @id 或 @flow",
            })
            continue

        flow_path = project / flow_rel
        if not flow_path.exists():
            plans.append({
                **item, "action": "error",
                "reason": f"流程文件不存在: {flow_rel}",
                "node_id": node_id, "flow_file": flow_rel,
            })
            continue

        if flow_rel not in flow_cache:
            flow_cache[flow_rel] = json.loads(flow_path.read_text(encoding="utf-8"))
        flow = flow_cache[flow_rel]
        node = find_node_by_id(flow, node_id)
        if not node:
            plans.append({
                **item, "action": "error",
                "reason": f"流程中找不到节点 id={node_id}",
                "node_id": node_id, "flow_file": flow_rel,
            })
            continue

        field = code_field_for_node(node)
        if not field:
            plans.append({
                **item, "action": "error",
                "reason": f"不支持的组件: {node.get('component_id')}",
                "node_id": node_id, "flow_file": flow_rel,
            })
            continue

        old_code = find_param(node.get("properties", []), "input_params", field)
        if not isinstance(old_code, str):
            plans.append({
                **item, "action": "error",
                "reason": f"节点无代码字段 {field}",
                "node_id": node_id, "flow_file": flow_rel,
            })
            continue

        ext = path.suffix
        body = strip_extracted_header(raw, ext)
        nl = detect_newline(old_code)
        new_code = normalize_newlines(body, nl)
        # Avoid trailing-newline-only diffs flipping apply
        old_hash = code_hash(old_code)
        new_hash = code_hash(new_code)

        action = "apply"
        reason = "代码有变更"
        if old_hash == new_hash and not force:
            action = "skip"
            reason = "与流程内代码 hash 一致"
        elif old_hash == new_hash and force:
            reason = "hash 一致但 --force 仍写入"

        plans.append({
            **item,
            "action": action,
            "reason": reason,
            "node_id": node_id,
            "flow_file": flow_rel,
            "code_field": field,
            "old_hash": old_hash,
            "new_hash": new_hash,
            "old_lines": len(old_code.splitlines()),
            "new_lines": len(new_code.splitlines()),
            "_new_code": new_code,
            "_flow_path": str(flow_path),
        })
    return plans


def backup_flow(flow_path: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = flow_path.with_name(f"{flow_path.name}.bak_apply_{ts}")
    shutil.copy2(flow_path, bak)
    return bak


def execute_plans(project: Path, plans: list[dict], dry_run: bool) -> dict:
    stats = {"apply": 0, "skip": 0, "error": 0, "backed_up": []}
    # group writes by flow file
    to_write: dict[str, list[dict]] = {}
    for p in plans:
        act = p["action"]
        if act == "skip":
            stats["skip"] += 1
            print(f"[跳过] N{p.get('seq')} {p.get('file')} — {p['reason']}")
            continue
        if act == "error":
            stats["error"] += 1
            print(f"[错误] N{p.get('seq')} {p.get('file')} — {p['reason']}")
            continue
        to_write.setdefault(p["_flow_path"], []).append(p)
        print(
            f"[待写] N{p.get('seq')} {p.get('file')} → {p['flow_file']} "
            f"id={p['node_id']} {p['old_hash'][:12]}→{p['new_hash'][:12]} "
            f"lines {p['old_lines']}→{p['new_lines']}"
        )

    planned = sum(len(v) for v in to_write.values())
    if dry_run:
        stats["apply"] = planned
        print(f"[dry-run] 将写入 {planned} 个节点，涉及 {len(to_write)} 个流程文件")
        return stats

    for flow_path_str, items in to_write.items():
        flow_path = Path(flow_path_str)
        bak = backup_flow(flow_path)
        stats["backed_up"].append(str(bak))
        print(f"[备份] {bak.name}")

        raw = flow_path.read_text(encoding="utf-8")
        nl = "\r\n" if "\r\n" in raw else "\n"
        # Prefer compact separators matching IPA Studio exports
        seps = (",", ":")
        if ", " in raw[:2000] and ': "' in raw[:2000]:
            seps = (", ", ": ")

        flow = json.loads(raw)
        for item in items:
            node = find_node_by_id(flow, item["node_id"])
            if not node:
                stats["error"] += 1
                print(f"[错误] 写入前节点消失: {item['node_id']}")
                continue
            ok = set_param(
                node.get("properties", []),
                "input_params",
                item["code_field"],
                item["_new_code"],
            )
            if not ok:
                stats["error"] += 1
                print(f"[错误] 无法设置字段 {item['code_field']}: {item['node_id']}")
                continue
            # verify in-memory
            got = find_param(node.get("properties", []), "input_params", item["code_field"])
            if code_hash(got) != item["new_hash"]:
                stats["error"] += 1
                print(f"[错误] 写后 hash 校验失败: {item['file']}")
                continue
            stats["apply"] += 1
            print(f"[完成] N{item.get('seq')} {item['file']}")

        out = json.dumps(flow, ensure_ascii=False, separators=seps)
        if raw.endswith(nl) and not out.endswith(nl):
            out += nl
        elif raw.endswith("\n") and not out.endswith("\n"):
            out += "\n"
        flow_path.write_text(out, encoding="utf-8")
        print(f"[保存] {flow_path.name}")

    return stats


def apply_project(
    project_path: str,
    dry_run: bool = False,
    node_seqs: Optional[list[int]] = None,
    files: Optional[list[str]] = None,
    force: bool = False,
) -> dict:
    project = Path(project_path).resolve()
    manifest = load_manifest(project)
    candidates = resolve_candidates(
        project, manifest, node_seqs or [], files or []
    )
    if not candidates:
        print("[结束] 无候选节点")
        return {"apply": 0, "skip": 0, "error": 0, "backed_up": []}

    # Default mode (no explicit filters): only apply when hash differs.
    # Explicit --node/--file: still skip identical unless --force.
    plans = plan_apply(project, candidates, force=force)

    # If no explicit selection, drop skips from noise? Keep them visible.
    # When neither node nor file specified, only consider structured changed —
    # plan_apply already marks skip for identical.

    return execute_plans(project, plans, dry_run=dry_run)


def main(argv: Optional[list[str]] = None) -> None:
    ap = argparse.ArgumentParser(description="Apply .extracted_nodes code back to flow JSON")
    ap.add_argument("project_path")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--node", type=int, action="append", dest="nodes",
                    help="节点序号，可重复，如 --node 55")
    ap.add_argument("--file", action="append", dest="files",
                    help="文件名或 glob，相对 .extracted_nodes")
    ap.add_argument("--force", action="store_true",
                    help="即使 hash 一致也写入")
    args = ap.parse_args(argv)

    stats = apply_project(
        args.project_path,
        dry_run=args.dry_run,
        node_seqs=args.nodes,
        files=args.files,
        force=args.force,
    )
    print(
        f"[汇总] apply={stats['apply']} skip={stats['skip']} "
        f"error={stats['error']} backups={len(stats.get('backed_up') or [])}"
    )
    if stats["error"]:
        sys.exit(2)
    if stats["apply"] == 0 and not args.dry_run and not stats["skip"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
