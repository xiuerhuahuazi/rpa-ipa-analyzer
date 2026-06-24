"""Assertion library for rpa-ipa-analyzer evals."""
import json, re
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
