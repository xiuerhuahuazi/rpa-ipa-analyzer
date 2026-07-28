from __future__ import annotations
import json, sys
from datetime import date
from pathlib import Path
from .core import safe_name, flow_shortname
from .flows import extract_nodes_from_flow
from .headers import node_header_python, node_header_js
from .counts import update_component_counts
from .duplicates import detect_duplicates
from .result_types import ExtractResult
from .snapshot import write_hash_snapshot


def extract_project(project_path: str, force: bool = False,
                    collect_edges: bool = True) -> ExtractResult:
    """Extract all code nodes from an IPA Studio RPA project.

    Returns an ExtractResult with out_dir, manifest, stats, and promotion_candidates.
    """
    root = Path(project_path)
    if not root.is_dir():
        sys.exit(f"错误: 项目路径不存在: {root}")

    project_json = root / "project.json"
    if not project_json.exists():
        project_json = root / "project.rpa"
    if not project_json.exists():
        sys.exit(f"错误: 找不到 project.json 或 project.rpa: {root}")

    with open(project_json, "r", encoding="utf-8") as f:
        proj = json.load(f)

    project_name = proj.get("project_info", {}).get("project_name", root.name)
    process_list = proj.get("process_list", [])

    out_dir = root / ".extracted_nodes"

    if out_dir.exists() and not force:
        manifest_file = out_dir / "manifest.json"
        if manifest_file.exists():
            with open(manifest_file, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            existing_date = manifest.get("extracted_at", "")
            print(f"[跳过] .extracted_nodes 已存在 (提取日期: {existing_date})，使用 --force 强制重新提取")
            return ExtractResult(out_dir=out_dir, manifest=manifest, manifest_path=manifest_file,
                                project_name=project_name, stats=manifest.get("stats", {}))

    # Preserve previous manifest + hash snapshot for incremental diff (rpa-ipa-update)
    if force and (out_dir / "manifest.json").exists():
        try:
            old_text = (out_dir / "manifest.json").read_text(encoding="utf-8")
            (out_dir / "previous_manifest.json").write_text(old_text, encoding="utf-8")
            old_m = json.loads(old_text)
            write_hash_snapshot(old_m, out_dir / "hash_snapshot.txt")
            print("[快照] 已保存 previous_manifest.json + hash_snapshot.txt")
        except Exception as exc:
            print(f"[警告] 保存增量快照失败: {exc}")

    out_dir.mkdir(parents=True, exist_ok=True)
    all_metas: list[dict] = []
    all_edges: list[dict] = []
    seq = 0
    stats = {"py": 0, "js": 0, "heuristic": 0, "total_lines": 0, "ui_nodes": 0}

    for proc in process_list:
        flow_path_rel = proc.get("process_path", "")
        flow_path = root / flow_path_rel
        if not flow_path.exists():
            print(f"[警告] 流程文件不存在，跳过: {flow_path_rel}")
            continue

        print(f"[解析] {flow_path_rel}")
        with open(flow_path, "r", encoding="utf-8") as f:
            flow = json.load(f)

        metas, edges = extract_nodes_from_flow(flow, flow_path_rel)

        for edge in edges:
            all_edges.append({
                "sourceNode": edge.sourceNode, "targetNode": edge.targetNode,
                "source": edge.source, "target": edge.target,
                "flow_file": edge.flow_file,
            })

        for meta in metas:
            seq += 1
            is_heuristic = meta.extraction_method == "heuristic"
            short = flow_shortname(flow_path_rel)
            sname = safe_name(meta.show_name)
            block_suffix = f"_{safe_name(meta.parent_block, 12)}" if meta.parent_block else ""

            if is_heuristic:
                filename = f"N{seq}_{short}{block_suffix}_{sname}.heuristic.json"
                stats["heuristic"] += 1
                print(f"  → [启发式] {filename} ({meta.component_id}, fields: {list(meta.input_vars.keys())})")
            elif meta.ext == ".py":
                header = node_header_python(meta.__dict__, seq)
                stats["py"] += 1
                filename = f"N{seq}_{short}{block_suffix}_{sname}{meta.ext}"
                with open(out_dir / filename, "w", encoding="utf-8") as f:
                    f.write(header + "\n" + meta.code + "\n")
            else:
                header = node_header_js(meta.__dict__, seq)
                stats["js"] += 1
                filename = f"N{seq}_{short}{block_suffix}_{sname}{meta.ext}"
                with open(out_dir / filename, "w", encoding="utf-8") as f:
                    f.write(header + "\n" + meta.code + "\n")

            if not is_heuristic:
                stats["total_lines"] += meta.code_lines
                tag_parts = []
                if meta.parent_block:
                    tag_parts.append(f"block:{meta.parent_block}")
                tag_str = f" [{' | '.join(tag_parts)}]" if tag_parts else ""
                print(f"  → {filename} ({meta.code_lines} lines, {len(meta.code)} chars){tag_str}")

            all_metas.append({
                "seq": seq,
                "node_id": meta.node_id,
                "show_name": meta.show_name,
                "file": filename,
                "flow_file": meta.flow_path,
                "component": meta.component_id,
                "input_vars": meta.input_vars,
                "output_vars": meta.output_vars,
                "code_hash": meta.code_hash,
                "code_lines": meta.code_lines,
                "parent_block": meta.parent_block,
                "extraction_method": meta.extraction_method,
            })

    # Detect duplicates
    duplicates = detect_duplicates(all_metas)
    dup_groups = len(duplicates)
    dup_nodes = sum(len(v) - 1 for v in duplicates.values())

    manifest = {
        "project": project_name,
        "extracted_at": str(date.today()),
        "total_nodes": seq,
        "stats": {
            "py_nodes": stats["py"],
            "js_nodes": stats["js"],
            "heuristic_nodes": stats["heuristic"],
            "ui_nodes": stats["ui_nodes"],
            "total_code_lines": stats["total_lines"],
            "duplicate_groups": dup_groups,
            "duplicate_nodes": dup_nodes,
        },
        "duplicates": {h: seqs for h, seqs in duplicates.items()} if duplicates else {},
        "edges": all_edges if collect_edges else [],
        "nodes": all_metas,
        "_schema_version": "2.0",
    }
    manifest_path = out_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # Keep a post-extract snapshot so next --force can diff against this run
    try:
        # Only write current snapshot if none exists yet (first extract);
        # on --force we already wrote the *old* snapshot before overwrite.
        snap = out_dir / "hash_snapshot.txt"
        if not snap.exists():
            write_hash_snapshot(manifest, snap)
            print("[快照] 已初始化 hash_snapshot.txt")
    except Exception as exc:
        print(f"[警告] 写入 hash_snapshot 失败: {exc}")

    promotion_candidates = update_component_counts(all_metas)

    print(f"\n[完成] 提取 {seq} 个节点 → {out_dir}")
    print(f"   Python: {stats['py']} | JS: {stats['js']} | 启发式: {stats['heuristic']}")
    print(f"   UI节点: {stats['ui_nodes']} | 总代码行数: {stats['total_lines']}")
    if collect_edges:
        print(f"   Edges: {len(all_edges)}")
    if duplicates:
        print(f"   重复代码组: {dup_groups} (重复节点: {dup_nodes})")
    if promotion_candidates:
        print(f"   [自适应] 以下组件已达升级阈值(>=3次): {', '.join(promotion_candidates)}")
    print(f"   manifest: {manifest_path}")
    return ExtractResult(out_dir=out_dir, manifest=manifest, manifest_path=manifest_path,
                        project_name=project_name, stats=manifest["stats"],
                        promotion_candidates=promotion_candidates)
