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

    # 节点的 input_vars / output_vars 是 {脚本内名: 流程变量名} 映射。
    # 调用方可能用任一命名空间查询，因此两个命名空间都要匹配：
    #   flow  : var 命中 value 侧，如 OutputPath / out_workpath / FlagPath
    #   local : var 命中 key 侧，  如 OUTPUT_PATH / workpath
    def _produces(node, mode):
        mapping = node.get("output_vars") or {}
        return var in (list(mapping.values()) if mode == "flow" else mapping)

    def _consumes(node, mode):
        mapping = node.get("input_vars") or {}
        return var in (list(mapping.values()) if mode == "flow" else mapping)

    all_nodes = list(nodes.values())
    if any(_produces(n, "flow") or _consumes(n, "flow") for n in all_nodes):
        mode = "flow"
    else:
        mode = "local"
    label = "流程变量名" if mode == "flow" else "脚本内变量名"

    producers = [n for n in all_nodes if _produces(n, mode)]
    consumers = [n for n in all_nodes if _consumes(n, mode)]

    if not producers and not consumers:
        print(
            f"变量 '{var}' 未出现在任何节点的 input_vars 或 output_vars 中"
            f"（已按流程变量名与脚本内变量名两种命名空间查找）"
        )
        return

    def _mapping(node, field):
        mapping = node.get(field) or {}
        if mode == "flow":
            hit = [f"{k} → {v}" for k, v in mapping.items() if v == var]
        else:
            hit = [f"{k} → {v}" for k, v in mapping.items() if k == var]
        return "; ".join(hit) if hit else "-"

    def _show(node, field, verb):
        print(
            f"  N{node['seq']} ({node['show_name']}) {verb} '{var}'"
            f"  [{_mapping(node, field)}]  ({node.get('flow_file', '?')})"
        )

    if args.direction in ("up", "both"):
        print(f"\n[上游 - 生产者]（匹配方式：{label}）")
        if producers:
            for n in sorted(producers, key=lambda x: x["seq"]):
                _show(n, "output_vars", "产出")
        else:
            print("  （无节点产出该变量；它可能来自项目参数 globalParams.json 或流程 global_vars）")

    if args.direction in ("down", "both"):
        print(f"\n[下游 - 消费者]（匹配方式：{label}）")
        if consumers:
            for n in sorted(consumers, key=lambda x: x["seq"]):
                _show(n, "input_vars", "消费")
        else:
            print("  （无节点消费该变量）")

    # IPA 每个 flow 文件各有一份 global_vars[]，跨流程必须两侧都登记。
    flows_used = sorted({n.get("flow_file", "?") for n in producers + consumers})
    if len(flows_used) > 1:
        print(f"\n[跨流程] 该变量出现在 {len(flows_used)} 个流程文件：{', '.join(flows_used)}")
        print(
            "  硬约束：生产侧与消费侧流程的 global_vars 都要登记该 key，"
            "否则运行报「出参定义解析失败，变量/参数表内不存在【xxx】」。"
        )
        for b in all_nodes:
            is_sub = str(b.get("node_id", "")).startswith("sub_process") or str(b.get("component") or "") == "sub_process"
            if is_sub:
                print(f"  子流程桥接：N{b['seq']} ({b['show_name']})  ({b.get('flow_file', '?')})")

    if not edges:
        print("\n[提示] manifest 无 edges 数据，无法还原执行路径。")
        return

    # 血缘链：只在「同一流程文件内」的生产者→消费者之间沿 edges 求最短路径。
    # 只打印真正产出/消费该变量的节点，不再把途经的祖先误标为「生产者」。
    adj = {}
    for e in edges:
        adj.setdefault(e["sourceNode"], []).append(e["targetNode"])

    def _path(src, dst, limit):
        q = deque([(src, [src])])
        seen = {src}
        while q:
            nid, path = q.popleft()
            if nid == dst:
                return path
            if len(path) - 1 >= limit:
                continue
            for nxt in adj.get(nid, []):
                if nxt not in seen:
                    seen.add(nxt)
                    q.append((nxt, path + [nxt]))
        return None

    chains = []
    for p in producers:
        for c in consumers:
            if p["node_id"] == c["node_id"] or p.get("flow_file") != c.get("flow_file"):
                continue
            found = _path(p["node_id"], c["node_id"], depth)
            if found:
                chains.append((p, found))

    if chains:
        print("\n[血缘链]（同流程内沿 edges 的最短执行路径）")
        for p, path in chains:
            hops = " → ".join(
                f"N{nodes[x]['seq']}" if x in nodes else str(x) for x in path
            )
            print(f"  {hops}   （{p.get('flow_file', '?')}）")
    elif producers and consumers:
        print(
            "\n[血缘链] 无同流程内的生产者→消费者直连路径"
            "（生产与消费为同一节点、二者不在同一流程文件，或其间无 edges 连通；"
            "跨流程连接由 sub_process 节点承担，manifest edges 不跨文件）。"
        )


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

    def _add_node_selector(p):
        g = p.add_mutually_exclusive_group(required=True)
        g.add_argument("--node", type=int, dest="node_seq", help="节点序号 N，如 --node 22")
        g.add_argument("--id", dest="node_id", help="节点 ID，如 --id script_python_execute4098849778077")

    p_mapping = sub.add_parser(
        "mapping",
        help="补丁节点入/出参映射与流程 global_vars（apply 不改这些字段）",
    )
    p_mapping.add_argument("project_path")
    _add_node_selector(p_mapping)
    p_mapping.add_argument("--input", action="append", default=[], dest="inputs",
                           metavar="脚本名=流程变量名", help="设置/覆盖入参映射，可重复")
    p_mapping.add_argument("--output", action="append", default=[], dest="outputs",
                           metavar="脚本名=流程变量名", help="设置/覆盖出参映射，可重复")
    p_mapping.add_argument("--remove-input", action="append", default=[], dest="del_inputs",
                           metavar="脚本名", help="删除入参映射，可重复")
    p_mapping.add_argument("--remove-output", action="append", default=[], dest="del_outputs",
                           metavar="脚本名", help="删除出参映射，可重复")
    p_mapping.add_argument("--ensure-global-var", action="append", default=[],
                           dest="ensure_global_vars", metavar="KEY",
                           help="在该流程 global_vars 中登记 key（缺则新增），可重复")
    p_mapping.add_argument("--description", default="", help="配合 --ensure-global-var 的说明文字")
    p_mapping.add_argument("--dry-run", action="store_true")

    p_remove = sub.add_parser("remove-node", help="删除孤立节点（默认拒绝删除仍被引用的节点）")
    p_remove.add_argument("project_path")
    _add_node_selector(p_remove)
    p_remove.add_argument("--force", action="store_true", help="即使仍被引用也强行删除")
    p_remove.add_argument("--dry-run", action="store_true")

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
    elif args.command == "mapping":
        from pathlib import Path as _Path
        from _extract.patch import patch_mapping
        ref = {"node_id": args.node_id} if args.node_id else {"seq": args.node_seq}
        st = patch_mapping(
            _Path(args.project_path),
            ref,
            set_inputs=args.inputs,
            set_outputs=args.outputs,
            del_inputs=args.del_inputs,
            del_outputs=args.del_outputs,
            global_var_needs=args.ensure_global_vars,
            description=args.description,
            dry_run=args.dry_run,
        )
        tag = "[dry-run] " if st.get("dry_run") else ""
        print(f"{tag}N{st['seq']} {st['node_id']} @ {st['flow']}")
        for k in st["global_vars_added"]:
            print(f"  [global_vars] + {k}")
        for v in st["input_added"]:
            print(f"  [入参] + {v}")
        for v in st["output_added"]:
            print(f"  [出参] + {v}")
        for v in st["removed"]:
            print(f"  [删除映射] {v}")
        for w in st["warnings"]:
            print(f"  [警告] {w}")
        if st.get("backup"):
            print(f"  [备份] {st['backup']}")
        if not (st["input_added"] or st["output_added"] or st["removed"] or st["global_vars_added"]):
            print("  （没有变化）")
    elif args.command == "remove-node":
        from pathlib import Path as _Path
        from _extract.patch import remove_node
        ref = {"node_id": args.node_id} if args.node_id else {"seq": args.node_seq}
        st = remove_node(_Path(args.project_path), ref, force=args.force, dry_run=args.dry_run)
        tag = "[dry-run] " if st.get("dry_run") else ""
        print(f"{tag}N{st['seq']} ({st['show_name']}) {st['node_id']} @ {st['flow']}")
        print(f"  nodes {st['nodes_before']} → {st['nodes_after']}")
        if st.get("backup"):
            print(f"  [备份] {st['backup']}")
        if st["refs"]:
            print("  [强制删除] 仍被引用：")
            for r in st["refs"]:
                print(f"    - {r}")


if __name__ == "__main__":
    main()
