from __future__ import annotations


def detect_duplicates(all_metas: list[dict]) -> dict[str, list[int]]:
    hash_to_seqs: dict[str, list[int]] = {}
    for meta in all_metas:
        h = meta.get("code_hash", "")
        if h:
            hash_to_seqs.setdefault(h, []).append(meta["seq"])
    return {h: seqs for h, seqs in hash_to_seqs.items() if len(seqs) > 1}


def detect_cross_project_shared(manifests: list[dict]) -> dict:
    hash_map: dict[str, list[dict]] = {}
    for m in manifests:
        proj = m.get("project", "unknown")
        for n in m.get("nodes", []):
            h = n.get("code_hash", "")
            if not h:
                continue
            hash_map.setdefault(h, []).append({
                "project": proj, "seq": n["seq"],
                "show_name": n["show_name"],
                "component": n.get("component", ""),
            })
    cross = {}
    for h, entries in hash_map.items():
        projects = set(e["project"] for e in entries)
        if len(projects) > 1:
            cross[h] = entries
    return cross
