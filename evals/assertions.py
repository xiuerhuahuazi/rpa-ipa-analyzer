"""Assertion library for rpa-ipa-analyzer evals."""
import json, re, shutil, subprocess, sys, tempfile
from pathlib import Path


def assert_manifest_diff(new_manifest, golden_manifest, tolerance=None):
    """Compare new manifest against golden. Returns score dict."""
    score = 0
    max_score = 40
    failures = []
    nt = new_manifest.get("total_nodes", 0)
    gt = golden_manifest.get("total_nodes", 0)
    if nt == gt:
        score += 10
    else:
        failures.append({"field": "total_nodes", "expected": gt, "actual": nt})
    ns = new_manifest.get("stats", {})
    gs = golden_manifest.get("stats", {})
    for key in ["py_nodes", "js_nodes", "heuristic_nodes"]:
        if ns.get(key) == gs.get(key):
            score += 5
        else:
            failures.append({"field": f"stats.{key}", "expected": gs.get(key), "actual": ns.get(key)})
    if ns.get("total_code_lines") == gs.get("total_code_lines"):
        score += 5
    else:
        failures.append({"field": "stats.total_code_lines", "expected": gs.get("total_code_lines"), "actual": ns.get("total_code_lines")})
    new_hashes = {n.get("code_hash") for n in new_manifest.get("nodes", []) if n.get("code_hash")}
    golden_hashes = {n.get("code_hash") for n in golden_manifest.get("nodes", []) if n.get("code_hash")}
    missing = golden_hashes - new_hashes
    extra = new_hashes - golden_hashes
    hash_penalty = min(10, len(missing) * 2 + len(extra) * 2)
    score += (10 - hash_penalty)
    if missing:
        failures.append({"field": "code_hashes_missing", "count": len(missing)})
    return {"case_id": "extract_golden_diff", "score": score, "max_score": max_score, "pass": score >= 30, "failures": failures}


def assert_report_structure(report_path, structure_config=None):
    """Check report structural completeness."""
    score = 0
    max_score = 25
    failures = []
    if not Path(report_path).exists():
        return {"case_id": "report_structure", "score": 0, "max_score": max_score, "pass": False, "failures": [{"field": "file", "error": "report not found"}]}
    text = Path(report_path).read_text(encoding="utf-8")
    chapters = (structure_config or {}).get("required_chapters", [
        "^## 一、整体工作流分析", "^## 二、节点级详细拆解",
        "^## 三、全局参数与配置分析", "^## 四、业务逻辑深度解读",
        "^## 五、综合分析", "^## 附录"
    ])
    chapter_score = 15 // max(len(chapters), 1)
    for ch in chapters:
        if re.search(ch, text, re.MULTILINE):
            score += chapter_score
        else:
            failures.append({"field": "chapter", "missing": ch})
    elements = (structure_config or {}).get("required_elements", ["```mermaid", "Appendix B"])
    for elem in elements:
        if elem in text:
            score += 2
        else:
            failures.append({"field": "element", "missing": elem})
    min_refs = (structure_config or {}).get("min_node_references", 5)
    refs = len(re.findall(r"N\d+", text))
    if refs >= min_refs:
        score += 5
    else:
        failures.append({"field": "node_references", "expected_min": min_refs, "actual": refs})
    final_score = min(max_score, score)
    return {"case_id": "report_structure", "score": final_score, "max_score": max_score, "pass": final_score >= 18, "failures": failures}


def _load_nodes_edges(flow_path):
    data = json.loads(Path(flow_path).read_text(encoding="utf-8"))
    g = data.get("graphData", {})
    return data, (g.get("nodes") or []), (g.get("edges") or [])


def _pick_targets(flow_path, allowed_ids):
    """Find (edge_connected_id, removable_id) among the extracted nodes."""
    data, nodes, edges = _load_nodes_edges(flow_path)
    touched = set()
    for e in edges:
        touched.add(e.get("sourceNode"))
        touched.add(e.get("targetNode"))

    connected = None
    removable = None
    for n in nodes:
        nid = n.get("id")
        # Only consider nodes the extractor actually indexed: flow start nodes
        # (process_start* / node_start) never appear in the manifest.
        if nid not in allowed_ids:
            continue
        if nid in touched:
            if connected is None:
                connected = nid
            continue
        mentioned = False
        for other in nodes:
            if other.get("id") == nid:
                continue
            if nid in json.dumps(other, ensure_ascii=False):
                mentioned = True
                break
        if not mentioned:
            removable = nid
            break
    return connected, removable


def assert_patch_operations(extract_script, baseline, tmp_root=None, counts_file=None):
    """End-to-end checks for the `mapping` and `remove-node` subcommands.

    Everything runs against a throwaway copy of the golden baseline, so the
    fixture itself is never modified. ``component_usage_counts.json`` is
    snapshotted and restored, because `extract` bumps it and that would leak
    into the promotion eval.
    """
    extract_script = Path(extract_script)
    max_score, score, failures = 30, 0, []

    counts_backup = None
    if counts_file is not None and Path(counts_file).exists():
        counts_backup = Path(counts_file).read_text(encoding="utf-8")

    def restore_counts():
        if counts_backup is not None:
            Path(counts_file).write_text(counts_backup, encoding="utf-8")

    tmp = Path(tempfile.mkdtemp(prefix="rpa-patch-eval-", dir=tmp_root))
    proj = tmp / "baseline_project"
    shutil.copytree(str(baseline), str(proj))

    def run(args):
        # The child writes UTF-8 (it is launched with -X utf8); decode it as
        # UTF-8 explicitly. text=True would use the locale codec (GBK on
        # zh-CN Windows) and blow up on the first non-ASCII byte.
        return subprocess.run(
            [sys.executable, "-X", "utf8", str(extract_script)] + args,
            capture_output=True, encoding="utf-8", errors="replace",
            cwd=str(extract_script.parent), timeout=120,
        )

    def fail(check, detail):
        failures.append({"check": check, "detail": str(detail)[-400:]})

    # 1. extract against the copy
    p = run(["extract", str(proj), "--force"])
    if p.returncode == 0 and (proj / ".extracted_nodes" / "manifest.json").exists():
        score += 5
    else:
        fail("extract_on_copy", p.stderr)
        shutil.rmtree(str(tmp), ignore_errors=True)
        restore_counts()
        return {"case_id": "patch_operations", "score": score, "max_score": max_score,
                "pass": False, "failures": failures}

    flow = proj / "主流程.json"
    manifest = json.loads((proj / ".extracted_nodes" / "manifest.json").read_text(encoding="utf-8"))
    allowed_ids = {n.get("node_id") for n in manifest.get("nodes", [])}
    connected_id, removable_id = _pick_targets(flow, allowed_ids)
    seq_of = {n.get("node_id"): n.get("seq") for n in manifest.get("nodes", [])}
    declared = {g.get("key") for g in (json.loads(flow.read_text(encoding="utf-8")).get("global_vars") or [])}

    # 2. mapping: valid input mapping (value is a declared flow var)
    valid_var = sorted(declared)[0] if declared else None
    if valid_var and connected_id:
        p = run(["mapping", str(proj), "--id", connected_id, "--input", "probe_in=%s" % valid_var])
        after = json.loads(flow.read_text(encoding="utf-8"))
        node = next((n for n in after["graphData"]["nodes"] if n.get("id") == connected_id), None)
        got = None
        for g in (node or {}).get("properties") or []:
            for prm in g.get("params") or []:
                if str(prm.get("id", "")).endswith("input_variables"):
                    got = prm.get("value")
        if p.returncode == 0 and isinstance(got, dict) and got.get("probe_in") == valid_var:
            score += 5
        else:
            fail("mapping_valid_input", p.stdout + p.stderr)
    else:
        fail("mapping_valid_input", "fixture has no declared flow var / connected node")

    # 3. mapping: output to an undeclared flow var must be REJECTED
    p = run(["mapping", str(proj), "--id", connected_id, "--output", "PROBE=DefinitelyNotDeclared"])
    if p.returncode != 0 and "global_vars" in (p.stdout + p.stderr):
        score += 5
    else:
        fail("mapping_rejects_undeclared_output", "expected non-zero exit; got %s" % p.returncode)

    # 4. mapping: same call passes once the key is registered
    p = run(["mapping", str(proj), "--id", connected_id, "--output", "PROBE=DefinitelyNotDeclared",
             "--ensure-global-var", "DefinitelyNotDeclared"])
    after = json.loads(flow.read_text(encoding="utf-8"))
    keys = {g.get("key") for g in (after.get("global_vars") or [])}
    node = next((n for n in after["graphData"]["nodes"] if n.get("id") == connected_id), None)
    outs = None
    for g in (node or {}).get("properties") or []:
        for prm in g.get("params") or []:
            if str(prm.get("id", "")).endswith("script_execute_result"):
                outs = prm.get("value")
    if p.returncode == 0 and "DefinitelyNotDeclared" in keys and isinstance(outs, dict) and outs.get("PROBE") == "DefinitelyNotDeclared":
        score += 5
    else:
        fail("mapping_ensures_global_var", p.stdout + p.stderr)

    # 5. remove-node must REFUSE a node that is still referenced
    if connected_id and connected_id in seq_of:
        before = len(json.loads(flow.read_text(encoding="utf-8"))["graphData"]["nodes"])
        p = run(["remove-node", str(proj), "--node", str(seq_of[connected_id])])
        now = len(json.loads(flow.read_text(encoding="utf-8"))["graphData"]["nodes"])
        if p.returncode != 0 and now == before:
            score += 5
        else:
            fail("remove_node_refuses_referenced", p.stdout + p.stderr)
    else:
        fail("remove_node_refuses_referenced", "no referenced node found in fixture")

    # 6. remove-node must SUCCEED on a genuinely unreferenced node
    if removable_id and removable_id in seq_of:
        before = len(json.loads(flow.read_text(encoding="utf-8"))["graphData"]["nodes"])
        p = run(["remove-node", str(proj), "--node", str(seq_of[removable_id])])
        data = json.loads(flow.read_text(encoding="utf-8"))
        now = len(data["graphData"]["nodes"])
        still = any(n.get("id") == removable_id for n in data["graphData"]["nodes"])
        if p.returncode == 0 and now == before - 1 and not still:
            score += 5
        else:
            fail("remove_node_removes_orphan", p.stdout + p.stderr)
    else:
        fail("remove_node_removes_orphan", "fixture has no removable node")

    shutil.rmtree(str(tmp), ignore_errors=True)
    restore_counts()
    return {"case_id": "patch_operations", "score": score, "max_score": max_score,
            "pass": score >= 25, "failures": failures}


def assert_promotion_status(counts_file):
    """Check no component has count>=3 but promoted==false."""
    score = 10
    max_score = 10
    failures = []
    if not Path(counts_file).exists():
        return {"case_id": "promotion_mechanism", "score": 0, "max_score": max_score, "pass": False, "failures": [{"field": "file", "error": "not found"}]}
    data = json.loads(Path(counts_file).read_text(encoding="utf-8"))
    comps = data.get("components", {})
    degraded = []
    for cid, c in comps.items():
        if c.get("count", 0) >= 3 and not c.get("promoted", False):
            degraded.append(cid)
            score -= 5
    if degraded:
        failures.append({"field": "promotion", "degraded_components": degraded})
    return {"case_id": "promotion_mechanism", "score": max(0, score), "max_score": max_score, "pass": len(degraded) == 0, "failures": failures}
