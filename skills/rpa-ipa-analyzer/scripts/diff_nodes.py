#!/usr/bin/env python3
"""Compare the previous extraction against the current manifest.

Usage:
    python diff_nodes.py <project_path> [--json] [--out changed.json]

Matching is done by ``node_id`` whenever the previous state carries ids
(``previous_manifest.json``). Falling back to ``hash_snapshot.txt`` — which only
stores ``seq`` — makes every node after an inserted or deleted node look
"changed", so that file is now only a legacy fallback.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path


def _record(node: dict) -> dict:
    return {
        "seq": int(node.get("seq", -1)),
        "node_id": node.get("node_id", ""),
        "name": node.get("show_name", ""),
        "hash": node.get("code_hash", "") or "",
        "flow": node.get("flow_file", ""),
        "file": node.get("file", ""),
        "input_vars": json.dumps(node.get("input_vars", {}), sort_keys=True, ensure_ascii=False),
        "output_vars": json.dumps(node.get("output_vars", {}), sort_keys=True, ensure_ascii=False),
    }


def _key(record: dict) -> str:
    """Prefer node_id; fall back to seq for legacy snapshots without ids."""
    return record["node_id"] or f"seq:{record['seq']}"


def _load_snapshot(path: Path) -> dict:
    """Load legacy hash_snapshot.txt → {key: record}.

    Format: seq|name|hash|flow|input_vars|output_vars (no node id).
    """
    old = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("|", 5)
        if len(parts) < 4:
            continue
        rec = {
            "seq": int(parts[0]),
            "node_id": "",
            "name": parts[1],
            "hash": parts[2],
            "flow": parts[3],
            "file": "",
            "input_vars": parts[4] if len(parts) > 4 else "{}",
            "output_vars": parts[5] if len(parts) > 5 else "{}",
        }
        old[_key(rec)] = rec
    return old


def _snapshot_from_manifest(nodes: list) -> dict:
    return {_key(r): r for r in (_record(n) for n in nodes)}


def write_hash_snapshot(manifest: dict, dest: Path) -> None:
    from _extract.snapshot import write_hash_snapshot as _w
    _w(manifest, dest)


def diff_project(project_path: str) -> dict:
    root = Path(project_path)
    ed = root / ".extracted_nodes"
    mf_path = ed / "manifest.json"
    if not mf_path.exists():
        sys.exit("错误: manifest.json 不存在，请先 extract")

    manifest = json.loads(mf_path.read_text(encoding="utf-8"))
    new_nodes = {_key(r): r for r in (_record(n) for n in manifest.get("nodes", []))}

    snap = ed / "hash_snapshot.txt"
    prev = ed / "previous_manifest.json"
    if prev.exists():
        basis = "previous_manifest"
        old = _snapshot_from_manifest(json.loads(prev.read_text(encoding="utf-8")).get("nodes", []))
    elif snap.exists():
        # Legacy path: seq-keyed, so insertions/deletions shift every later node.
        basis = "hash_snapshot"
        old = _load_snapshot(snap)
    else:
        sys.exit("错误: 无 hash_snapshot.txt / previous_manifest.json，建议先全量分析或重新 extract")

    changed, added, removed, var_changed = [], [], [], []

    for key, i in old.items():
        nn = new_nodes.get(key)
        if nn is None:
            removed.append({"seq": i["seq"], "node_id": i["node_id"], "name": i["name"], "flow": i["flow"]})
            continue
        if nn["hash"] != i["hash"]:
            changed.append({"seq": nn["seq"], "node_id": nn["node_id"], "name": nn["name"],
                            "flow": nn["flow"], "file": nn["file"]})
        if nn["input_vars"] != i["input_vars"] or nn["output_vars"] != i["output_vars"]:
            var_changed.append({
                "seq": nn["seq"], "node_id": nn["node_id"], "name": nn["name"], "flow": nn["flow"],
                "input_changed": nn["input_vars"] != i["input_vars"],
                "output_changed": nn["output_vars"] != i["output_vars"],
            })

    for key, n in new_nodes.items():
        if key not in old:
            added.append({"seq": n["seq"], "node_id": n["node_id"], "name": n["name"],
                          "flow": n["flow"], "file": n["file"]})

    changed.sort(key=lambda x: x["seq"])
    added.sort(key=lambda x: x["seq"])
    removed.sort(key=lambda x: x["seq"])
    var_changed.sort(key=lambda x: x["seq"])

    return {
        "project": manifest.get("project"),
        "basis": basis,
        "changed": changed,
        "added": added,
        "removed": removed,
        "var_changed": var_changed,
        "total_delta": len(changed) + len(added) + len(removed),
        "recommend": "incremental" if (len(changed) + len(added) + len(removed)) <= 5 else "full",
    }


def main():
    ap = argparse.ArgumentParser(description="Diff extracted nodes vs snapshot")
    ap.add_argument("project_path")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", help="Write JSON result to path")
    args = ap.parse_args()

    result = diff_project(args.project_path)
    if args.out:
        Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    for label, key in [("代码变更", "changed"), ("新增", "added"),
                       ("删除", "removed"), ("变量映射变化", "var_changed")]:
        lst = result[key]
        print(f"{label}: {len(lst)} 个")
        if key == "var_changed":
            for item in lst:
                bits = []
                if item.get("input_changed"):
                    bits.append("输入变量变")
                if item.get("output_changed"):
                    bits.append("输出变量变")
                print(f"  N{item['seq']} [{item['flow']}] {item['name']} — {'/'.join(bits)}")
        else:
            for item in lst[:5]:
                print(f"  N{item['seq']} [{item['flow']}] {item['name']}")
            if len(lst) > 5:
                print(f"  ... 共 {len(lst)} 个")
    if result.get("basis") == "hash_snapshot":
        print("[提示] 依据 hash_snapshot.txt（仅有序号，无节点 ID）比对 —— "
              "若上次以来有节点增删，其后所有节点都会被记为变更。重新 extract 后会改用 previous_manifest.json 按 ID 比对。")
    print(f"建议: {result['recommend']}（delta={result['total_delta']}）")


if __name__ == "__main__":
    main()
