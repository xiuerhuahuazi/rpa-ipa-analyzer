#!/usr/bin/env python3
"""Generate structural report skeleton from .extracted_nodes (no LLM).

Writes: {project}/.extracted_nodes/report_skeleton.md
Contains: §1.2-ish path, §3 param table stub, Appendix B, node index for §2.2 links.

Usage:
    python generate_skeleton.py <project_path> [--depth quick|standard|deep]
"""
from __future__ import annotations
import argparse, json, sys
from collections import defaultdict, deque
from datetime import date
from pathlib import Path


def _load_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _build_adj(edges: list):
    fwd = defaultdict(list)
    rev = defaultdict(list)
    for e in edges:
        s, t = e.get("sourceNode"), e.get("targetNode")
        if s and t:
            fwd[s].append(t)
            rev[t].append(s)
    return fwd, rev


def _topo_paths(nodes_by_id: dict, edges: list, flow_file: str = None):
    """BFS from nodes with no incoming edges within optional flow filter."""
    fe = [e for e in edges if (flow_file is None or e.get("flow_file") == flow_file)]
    fwd, rev = _build_adj(fe)
    ids = set()
    for e in fe:
        ids.add(e.get("sourceNode"))
        ids.add(e.get("targetNode"))
    for nid in nodes_by_id:
        if flow_file is None or nodes_by_id[nid].get("flow_file") == flow_file:
            ids.add(nid)
    starts = [i for i in ids if i and not rev.get(i)]
    if not starts and ids:
        starts = [next(iter(ids))]

    ordered, seen = [], set()
    q = deque(starts)
    while q:
        cur = q.popleft()
        if cur in seen:
            continue
        seen.add(cur)
        ordered.append(cur)
        for nxt in fwd.get(cur, []):
            if nxt not in seen:
                q.append(nxt)
    return ordered


def generate(project_path: str, depth: str = "standard") -> Path:
    root = Path(project_path)
    ed = root / ".extracted_nodes"
    mf_path = ed / "manifest.json"
    if not mf_path.exists():
        sys.exit("错误: 请先运行 extract_nodes.py extract")

    manifest = _load_json(mf_path)
    nodes = manifest.get("nodes", [])
    edges = manifest.get("edges", [])
    nodes_by_id = {n["node_id"]: n for n in nodes if n.get("node_id")}
    by_seq = {int(n["seq"]): n for n in nodes}

    proj = _load_json(root / "project.json") or _load_json(root / "project.rpa") or {}
    gparams = _load_json(root / "globalParams.json") or {}
    process_result = _load_json(root / "processResult.json") or {}

    project_name = manifest.get("project") or proj.get("project_info", {}).get("project_name", root.name)
    version = proj.get("project_info", {}).get("version", "?")
    designer = proj.get("project_info", {}).get("designer_version", "?")
    executor = proj.get("project_info", {}).get("executor_version", "?")

    # Component type guess — processResult.json shapes vary (dict or list)
    comps = {}
    pr_items = []
    if isinstance(process_result, list):
        pr_items = process_result
    elif isinstance(process_result, dict):
        pr_items = (
            process_result.get("component_list")
            or process_result.get("components")
            or process_result.get("data")
            or []
        )
        if isinstance(pr_items, dict):
            pr_items = list(pr_items.values())
    if not isinstance(pr_items, list):
        pr_items = []
    for item in pr_items:
        if isinstance(item, dict):
            cid = item.get("component_id") or item.get("id") or item.get("name") or ""
            comps[cid] = comps.get(cid, 0) + int(item.get("usetotal") or item.get("count") or item.get("useTotal") or 1)
    # fallback from nodes
    if not comps:
        for n in nodes:
            c = n.get("component", "")
            comps[c] = comps.get(c, 0) + 1

    py_like = comps.get("script_python_execute", 0) + comps.get("log_task", 0)
    web_like = comps.get("mouse_single_click", 0) + comps.get("browser_inject_js_code", 0)
    if py_like >= web_like and py_like > 0:
        ptype = "data_processing"
    elif web_like > py_like:
        ptype = "web_automation"
    else:
        ptype = "mixed"

    lines = []
    lines.append(f"# {project_name} — IPA Studio RPA 分析报告")
    lines.append("")
    lines.append(
        f"> 项目版本：{version} | 设计器：{designer} | 执行器：{executor} | "
        f"分析日期：{date.today()} | 项目类型：{ptype} | 分析深度：{depth}"
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 一、整体工作流分析")
    lines.append("")
    lines.append("### 1.1 项目架构概览")
    lines.append(f"- 项目类型：`{ptype}`（脚本自动判定，可人工修正）")
    lines.append(f"- 代码节点：{manifest.get('total_nodes', len(nodes))} "
                 f"(py={manifest.get('stats', {}).get('py_nodes', 0)}, "
                 f"js={manifest.get('stats', {}).get('js_nodes', 0)}, "
                 f"heuristic={manifest.get('stats', {}).get('heuristic_nodes', 0)})")
    lines.append(f"- Edges：{len(edges)}")
    lines.append("")
    lines.append("```mermaid")
    lines.append("flowchart TB")
    proc_list = proj.get("process_list", [])
    if proc_list:
        lines.append("  Main[主流程]")
        for i, p in enumerate(proc_list[:20]):
            name = Path(p.get("process_path", f"proc{i}")).stem
            safe = re_safe(name)
            lines.append(f"  Main --> {safe}[{name}]")
    else:
        lines.append("  Main[主流程]")
    lines.append("```")
    lines.append("")
    lines.append("### 1.2 主流程完整路径（脚本生成，待润色）")
    lines.append("")

    # Prefer first process flow for path
    main_flow = None
    if proc_list:
        main_flow = proc_list[0].get("process_path")
    ordered = _topo_paths(nodes_by_id, edges, main_flow) if edges else []
    if not ordered:
        ordered = [n["node_id"] for n in sorted(nodes, key=lambda x: int(x["seq"]))[:80]]

    for i, nid in enumerate(ordered[:120], 1):
        n = nodes_by_id.get(nid)
        if not n:
            lines.append(f"[{i}] `{nid}`")
            continue
        kind = "Python" if str(n.get("file", "")).endswith(".py") else (
            "JS" if str(n.get("file", "")).endswith(".js") else n.get("component", "node"))
        inv = ",".join(n.get("input_vars", {}).keys()) or "-"
        outv = ",".join(n.get("output_vars", {}).keys()) or "-"
        lines.append(
            f"[{i}] N{n['seq']} [{kind}] {n.get('show_name','')} "
            f"— in: {inv} / out: {outv}"
        )
    lines.append("")

    lines.append("### 1.4 子流程调用关系")
    lines.append("")
    lines.append("| 子流程文件 | 节点数 | 调用方 | 传入变量 | 传出变量 |")
    lines.append("|-----------|--------|--------|----------|----------|")
    flow_counts = defaultdict(int)
    for n in nodes:
        flow_counts[n.get("flow_file", "")] += 1
    for fp, cnt in sorted(flow_counts.items()):
        lines.append(f"| {fp} | {cnt} |  |  |  |")
    lines.append("")

    lines.append("## 二、节点级详细拆解")
    lines.append("")
    lines.append("### 2.1 阶段划分")
    lines.append("（由 LLM 按业务逻辑填写）")
    lines.append("")

    if depth != "quick":
        lines.append("### 2.2 代码节点索引（代码外置，勿整段粘贴）")
        lines.append("")
        lines.append("| N# | 名称 | 类型 | 文件 | hash |")
        lines.append("|----|------|------|------|------|")
        for n in sorted(nodes, key=lambda x: int(x["seq"])):
            f = n.get("file", "")
            if not (f.endswith(".py") or f.endswith(".js")):
                continue
            lines.append(
                f"| N{n['seq']} | {n.get('show_name','')} | {n.get('component','')} | "
                f"`.extracted_nodes/{f}` | `{n.get('code_hash','')[:12]}` |"
            )
        lines.append("")
        lines.append("> §2.2 详解模板：引用上表文件路径，只写业务概述/规则/I-O，**禁止**粘贴完整源码。")
        lines.append("")

    lines.append("## 三、全局参数与配置分析")
    lines.append("")
    lines.append("### 3.1 参数完整列表")
    lines.append("")
    lines.append("| # | 参数Key | 类型 | 描述 | 默认值 | 使用位置 |")
    lines.append("|---|---------|------|------|--------|----------|")
    # globalParams shapes vary
    params = []
    if isinstance(gparams, dict):
        if "globalParams" in gparams and isinstance(gparams["globalParams"], list):
            params = gparams["globalParams"]
        elif "params" in gparams and isinstance(gparams["params"], list):
            params = gparams["params"]
        else:
            # key→value map
            for k, v in gparams.items():
                if k.startswith("_"):
                    continue
                if isinstance(v, dict):
                    params.append({"key": k, **v})
                else:
                    params.append({"key": k, "value": v, "type": type(v).__name__})
    for i, p in enumerate(params, 1):
        if not isinstance(p, dict):
            continue
        key = p.get("key") or p.get("name") or p.get("paramKey") or ""
        typ = p.get("type") or p.get("paramType") or ""
        desc = (p.get("desc") or p.get("description") or "").replace("|", "/")
        val = p.get("value") or p.get("default") or p.get("defaultValue") or ""
        if isinstance(val, (dict, list)):
            val = json.dumps(val, ensure_ascii=False)[:40]
        else:
            val = str(val)[:40].replace("|", "/")
        lines.append(f"| {i} | {key} | {typ} | {desc[:40]} | {val} |  |")
    if not params:
        lines.append("|  | （未解析到 globalParams） |  |  |  |  |")
    lines.append("")

    if depth != "quick":
        lines.append("## 四、业务逻辑深度解读")
        lines.append("")
        lines.append("### 4.1 整体业务目标")
        lines.append("（由 LLM 填写）")
        lines.append("")

    lines.append("## 五、综合分析")
    lines.append("")
    lines.append("### 5.1 组件统计")
    lines.append("")
    lines.append("| 组件 | 次数 |")
    lines.append("|------|------|")
    for c, cnt in sorted(comps.items(), key=lambda x: -x[1])[:40]:
        lines.append(f"| `{c}` | {cnt} |")
    lines.append("")

    lines.append("## 附录 B：节点索引")
    lines.append("")
    lines.append("| 序号 | 节点ID | 类型 | 名称 | 所在文件 |")
    lines.append("|------|--------|------|------|----------|")
    for n in sorted(nodes, key=lambda x: int(x["seq"])):
        lines.append(
            f"| N{n['seq']} | `{n.get('node_id','')}` | {n.get('component','')} | "
            f"{n.get('show_name','')} | {n.get('flow_file','')} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("> 本文件由 `generate_skeleton.py` 生成。LLM 应在此基础上润色业务语义，"
                 "不要重新解析原始 flow JSON。")

    ed.mkdir(parents=True, exist_ok=True)
    out = ed / "report_skeleton.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[完成] skeleton → {out} ({len(lines)} lines, depth={depth})")
    return out


def re_safe(name: str) -> str:
    import re
    s = re.sub(r"[^0-9A-Za-z_\u4e00-\u9fff]", "_", name)
    if s and s[0].isdigit():
        s = "n_" + s
    return s or "flow"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project_path")
    ap.add_argument("--depth", choices=["quick", "standard", "deep"], default="standard")
    args = ap.parse_args()
    generate(args.project_path, args.depth)


if __name__ == "__main__":
    main()
