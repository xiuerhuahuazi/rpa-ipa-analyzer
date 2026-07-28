#!/usr/bin/env python3
"""Compare hash_snapshot / previous_manifest vs current manifest.

Usage:
    python diff_nodes.py <project_path> [--json] [--out changed.json]
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path


def _load_snapshot(path: Path) -> dict:
    """Load hash_snapshot.txt → {seq: {name, hash, flow, input_vars, output_vars}}."""
    old = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("|", 5)
        if len(parts) < 4:
            continue
        old[int(parts[0])] = {
            "name": parts[1],
            "hash": parts[2],
            "flow": parts[3],
            "input_vars": parts[4] if len(parts) > 4 else "{}",
            "output_vars": parts[5] if len(parts) > 5 else "{}",
        }
    return old


def _snapshot_from_manifest(nodes: list) -> dict:
    out = {}
    for n in nodes:
        out[int(n["seq"])] = {
            "name": n.get("show_name", ""),
            "hash": n.get("code_hash", ""),
            "flow": n.get("flow_file", ""),
            "input_vars": json.dumps(n.get("input_vars", {}), sort_keys=True, ensure_ascii=False),
            "output_vars": json.dumps(n.get("output_vars", {}), sort_keys=True, ensure_ascii=False),
        }
    return out


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
    new_nodes = {int(n["seq"]): n for n in manifest.get("nodes", [])}

    snap = ed / "hash_snapshot.txt"
    prev = ed / "previous_manifest.json"
    if snap.exists():
        old = _load_snapshot(snap)
    elif prev.exists():
        old = _snapshot_from_manifest(json.loads(prev.read_text(encoding="utf-8")).get("nodes", []))
    else:
        sys.exit("错误: 无 hash_snapshot.txt / previous_manifest.json，建议先全量分析或重新 extract")

    changed, added, removed, var_changed = [], [], [], []

    for s, i in old.items():
        if s not in new_nodes:
            removed.append({"seq": s, "name": i["name"], "flow": i["flow"]})
            continue
        nn = new_nodes[s]
        if nn.get("code_hash", "") != i["hash"]:
            changed.append({"seq": s, "name": i["name"], "flow": i["flow"],
                            "file": nn.get("file", "")})
        new_in = json.dumps(nn.get("input_vars", {}), sort_keys=True, ensure_ascii=False)
        new_out = json.dumps(nn.get("output_vars", {}), sort_keys=True, ensure_ascii=False)
        if new_in != (i.get("input_vars") or "{}") or new_out != (i.get("output_vars") or "{}"):
            var_changed.append({
                "seq": s, "name": i["name"], "flow": i["flow"],
                "input_changed": new_in != (i.get("input_vars") or "{}"),
                "output_changed": new_out != (i.get("output_vars") or "{}"),
            })

    for s, n in new_nodes.items():
        if s not in old:
            added.append({"seq": s, "name": n.get("show_name", ""), "flow": n.get("flow_file", ""),
                          "file": n.get("file", "")})

    return {
        "project": manifest.get("project"),
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
    print(f"建议: {result['recommend']}（delta={result['total_delta']}）")


if __name__ == "__main__":
    main()
