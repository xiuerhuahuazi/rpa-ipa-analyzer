#!/usr/bin/env python3
"""IPA Studio RPA Node Extractor — CLI entry point.

Usage:
    python extract_nodes.py extract <project_path> [--force] [--no-edges]
    python extract_nodes.py list <project_path> [--type py|js|heuristic] [--flow <name>] [--format table|json]
    python extract_nodes.py stats <project_path> [--json]
    python extract_nodes.py trace <project_path> <variable_name> [--direction up|down|both] [--depth N]
    python extract_nodes.py compare <proj1> <proj2> [--mode shared-code|component-diff|all]
    python extract_nodes.py diff <project_path> [--json] [--out changed.json]
    python extract_nodes.py skeleton <project_path> [--depth quick|standard|deep]
    python extract_nodes.py patch <report.md> [--node N] [--from-file f] [--delete] [--meta ...]
    python extract_nodes.py apply <project_path> [--dry-run] [--node N] [--file PATH] [--force]
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from collections import deque

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))


def cmd_extract(args):
    from _extract import extract_project
    extract_project(args.project_path, force=args.force, collect_edges=not args.no_edges)


def cmd_list(args):
    mf = Path(args.project_path) / ".extracted_nodes" / "manifest.json"
    if not mf.exists():
        sys.exit("错误: manifest.json 不存在，请先运行 extract")
    m = json.loads(mf.read_text(encoding="utf-8"))
    nodes = m["nodes"]
    if args.type and args.type != "all":
        if args.type == "heuristic":
            nodes = [n for n in nodes if n.get("extraction_method") == "heuristic"]
        else:
            nodes = [n for n in nodes if n.get("file", "").endswith(f".{args.type}")]
    if args.flow:
        nodes = [n for n in nodes if args.flow in n.get("flow_file", "")]
    if args.format == "json":
        print(json.dumps(nodes, ensure_ascii=False, indent=2))
    else:
        print(f"{'N#':>4} | {'类型':12} | {'名称':25} | {'流程':30} | 行数")
        print("-" * 84)
        for n in nodes:
            ext = n.get("file", "").split(".")[-1] if "." in n.get("file", "") else "heuristic"
            print(f"N{n['seq']:<4} | {ext:12} | {n['show_name'][:25]:25} | {n.get('flow_file','')[:30]:30} | {n.get('code_lines',0)}")


def cmd_stats(args):
    mf = Path(args.project_path) / ".extracted_nodes" / "manifest.json"
    if not mf.exists():
        sys.exit("错误: manifest.json 不存在，请先运行 extract")
    m = json.loads(mf.read_text(encoding="utf-8"))
    if args.json:
        print(json.dumps(m.get("stats", {}), ensure_ascii=False, indent=2))
    else:
        s = m.get("stats", {})
        print(f"项目: {m.get('project', '?')}")
        print(f"提取日期: {m.get('extracted_at', '?')}")
        print(f"{'─'*40}")
        print(f"节点总数: {m.get('total_nodes', '?')}")
        print(f"  Python: {s.get('py_nodes', 0)}")
        print(f"  JavaScript: {s.get('js_nodes', 0)}")
        print(f"  启发式: {s.get('heuristic_nodes', 0)}")
        print(f"  UI 节点: {s.get('ui_nodes', 0)}")
        print(f"总代码行数: {s.get('total_code_lines', 0)}")
        print(f"重复代码组: {s.get('duplicate_groups', 0)} (重复节点: {s.get('duplicate_nodes', 0)})")
        edges = m.get("edges", [])
        print(f"Edges 总数: {len(edges)}")


def cmd_trace(args):
    mf = Path(args.project_path) / ".extracted_nodes" / "manifest.json"
    if not mf.exists():
        sys.exit("错误: manifest.json 不存在，请先运行 extract")
    m = json.loads(mf.read_text(encoding="utf-8"))
    nodes = {n["node_id"]: n for n in m["nodes"]}
    edges = m.get("edges", [])
    var = args.variable_name
    depth = args.depth or 10

    if not edges:
        print("[警告] manifest 无 edges 数据，降级为全局变量名匹配模式 [推测]")
        producers = [n for n in m["nodes"] if var in n.get("output_vars", {})]
        consumers = [n for n in m["nodes"] if var in n.get("input_vars", {})]
        if producers:
            print(f"\n[上游 - 推测生产者]")
            for p in producers:
                print(f"  N{p['seq']} ({p['show_name']}) → 产出 {var}")
        if consumers:
            print(f"\n[下游 - 推测消费者]")
            for c in consumers:
                print(f"  N{c['seq']} ({c['show_name']}) → 消费 {var}")
        if not producers and not consumers:
            print(f"变量 '{var}' 未出现在任何节点的 input_vars 或 output_vars 中")
        return

    if args.direction in ("up", "both"):
        rev_adj: dict[str, list[str]] = {}
        for e in edges:
            rev_adj.setdefault(e["targetNode"], []).append(e["sourceNode"])
        visited = set()
        q = deque([(nid, 0) for nid in nodes if var in nodes[nid].get("output_vars", {})])
        print(f"\n[上游 - 生产者]")
        while q:
            nid, d = q.popleft()
            if nid in visited or d > depth:
                continue
            visited.add(nid)
            if nid in nodes:
                print(f"  N{nodes[nid]['seq']} ({nodes[nid]['show_name']}) → 产出 {var}")
            for prev in rev_adj.get(nid, []):
                if prev not in visited:
                    q.append((prev, d + 1))

    if args.direction in ("down", "both"):
        adj: dict[str, list[str]] = {}
        for e in edges:
            adj.setdefault(e["sourceNode"], []).append(e["targetNode"])
        visited = set()
        q = deque([(nid, 0) for nid in nodes if var in nodes[nid].get("output_vars", {})])
        print(f"\n[下游 - 消费者]")
        while q:
            nid, d = q.popleft()
            if nid in visited or d > depth:
                continue
            visited.add(nid)
            for nxt in adj.get(nid, []):
                if nxt not in visited and nxt in nodes and var in nodes[nxt].get("input_vars", {}):
                    print(f"  N{nodes[nid]['seq']}/{var} → N{nodes[nxt]['seq']} ({nodes[nxt]['show_name']}) → 消费 {var}")
                    q.append((nxt, d + 1))


def cmd_compare(args):
    mf1 = Path(args.proj1) / ".extracted_nodes" / "manifest.json"
    mf2 = Path(args.proj2) / ".extracted_nodes" / "manifest.json"
    if not mf1.exists() or not mf2.exists():
        sys.exit("错误: 两个项目都需要先运行 extract")
    m1 = json.loads(mf1.read_text(encoding="utf-8"))
    m2 = json.loads(mf2.read_text(encoding="utf-8"))

    if args.mode in ("shared-code", "all"):
        hashes1 = {n["code_hash"] for n in m1["nodes"] if n.get("code_hash")}
        hashes2 = {n["code_hash"] for n in m2["nodes"] if n.get("code_hash")}
        shared = hashes1 & hashes2
        print(f"跨项目共享代码节点: {len(shared)}")
        for h in list(shared)[:10]:
            n1 = [n for n in m1["nodes"] if n.get("code_hash") == h][0]
            n2 = [n for n in m2["nodes"] if n.get("code_hash") == h][0]
            print(f"  hash={h[:12]} → {m1['project']}/N{n1['seq']} = {m2['project']}/N{n2['seq']}")

    if args.mode in ("component-diff", "all"):
        comp1, comp2 = {}, {}
        for n in m1["nodes"]:
            c = n.get("component", "")
            comp1[c] = comp1.get(c, 0) + 1
        for n in m2["nodes"]:
            c = n.get("component", "")
            comp2[c] = comp2.get(c, 0) + 1
        only1 = {c: comp1[c] for c in comp1 if c not in comp2}
        only2 = {c: comp2[c] for c in comp2 if c not in comp1}
        common = {c: (comp1[c], comp2[c]) for c in comp1 if c in comp2}
        print(f"\n仅 {m1['project']}: {len(only1)} 种组件")
        print(f"仅 {m2['project']}: {len(only2)} 种组件")
        print(f"共同: {len(common)} 种组件")


def main():
    parser = argparse.ArgumentParser(description="IPA Studio RPA Node Extractor")
    sub = parser.add_subparsers(dest="command")

    p_extract = sub.add_parser("extract", help="提取代码节点")
    p_extract.add_argument("project_path")
    p_extract.add_argument("--force", action="store_true")
    p_extract.add_argument("--no-edges", action="store_true")

    p_list = sub.add_parser("list", help="列出节点")
    p_list.add_argument("project_path")
    p_list.add_argument("--type", choices=["py", "js", "heuristic", "all"])
    p_list.add_argument("--flow")
    p_list.add_argument("--format", choices=["table", "json"], default="table")

    p_stats = sub.add_parser("stats", help="统计摘要")
    p_stats.add_argument("project_path")
    p_stats.add_argument("--json", action="store_true")

    p_trace = sub.add_parser("trace", help="变量血缘追踪")
    p_trace.add_argument("project_path")
    p_trace.add_argument("variable_name")
    p_trace.add_argument("--direction", choices=["up", "down", "both"], default="both")
    p_trace.add_argument("--depth", type=int, default=10)

    p_compare = sub.add_parser("compare", help="跨项目对比")
    p_compare.add_argument("proj1")
    p_compare.add_argument("proj2")
    p_compare.add_argument("--mode", choices=["shared-code", "component-diff", "all"], default="all")

    p_diff = sub.add_parser("diff", help="对比 hash_snapshot 与当前 manifest")
    p_diff.add_argument("project_path")
    p_diff.add_argument("--json", action="store_true")
    p_diff.add_argument("--out")

    p_skel = sub.add_parser("skeleton", help="从 manifest 生成报告骨架（无 LLM）")
    p_skel.add_argument("project_path")
    p_skel.add_argument("--depth", choices=["quick", "standard", "deep"], default="standard")

    p_patch = sub.add_parser("patch", help="按 #### 节点 N{n} 锚点补丁报告")
    p_patch.add_argument("report")
    p_patch.add_argument("--node", type=int)
    p_patch.add_argument("--from-file")
    p_patch.add_argument("--delete", action="store_true")
    p_patch.add_argument("--meta")
    p_patch.add_argument("--dry-run", action="store_true")

    p_apply = sub.add_parser(
        "apply",
        help="将 .extracted_nodes 中修改后的代码精准写回对应 flow JSON 节点",
    )
    p_apply.add_argument("project_path")
    p_apply.add_argument("--dry-run", action="store_true",
                        help="只预览，不写盘、不备份")
    p_apply.add_argument("--node", type=int, action="append", dest="nodes",
                        help="节点序号，可重复，如 --node 55")
    p_apply.add_argument("--file", action="append", dest="files",
                        help="相对 .extracted_nodes 的文件名或 glob")
    p_apply.add_argument("--force", action="store_true",
                        help="即使与流程内代码 hash 一致也写入")

    args = parser.parse_args()

    if args.command == "extract" or args.command is None:
        if args.command is None:
            p_extract.print_help()
            sys.exit(1)
        cmd_extract(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "trace":
        cmd_trace(args)
    elif args.command == "compare":
        cmd_compare(args)
    elif args.command == "diff":
        from diff_nodes import diff_project, main as diff_main
        # Reuse CLI via argv shim
        sys.argv = ["diff_nodes.py", args.project_path] + (
            ["--json"] if args.json else []) + (["--out", args.out] if args.out else [])
        diff_main()
    elif args.command == "skeleton":
        from generate_skeleton import generate
        generate(args.project_path, args.depth)
    elif args.command == "patch":
        from patch_report import main as patch_main
        argv = ["patch_report.py", args.report]
        if args.node is not None:
            argv += ["--node", str(args.node)]
        if args.from_file:
            argv += ["--from-file", args.from_file]
        if args.delete:
            argv.append("--delete")
        if args.meta:
            argv += ["--meta", args.meta]
        if args.dry_run:
            argv.append("--dry-run")
        sys.argv = argv
        patch_main()
    elif args.command == "apply":
        from _extract.apply import apply_project
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


if __name__ == "__main__":
    main()
