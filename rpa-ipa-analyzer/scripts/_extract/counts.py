from __future__ import annotations
import json
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent


def update_component_counts(metas: list[dict]) -> list[str]:
    """Update component_usage_counts.json and return list of components
    hitting the promotion threshold (>= 3 counts, not yet promoted).
    Also computes confidence for every component."""
    counts_file = SCRIPT_DIR.parent / "component_usage_counts.json"

    if counts_file.exists():
        try:
            data = json.loads(counts_file.read_text(encoding="utf-8"))
        except Exception:
            data = {"components": {}}
    else:
        data = {"components": {}}

    today_str = str(date.today())
    components = data.setdefault("components", {})
    threshold_hits: list[str] = []

    # Count distinct component_ids across all metas
    seen_in_run: dict[str, list[str]] = {}
    for meta in metas:
        cid = meta.get("component_id") or meta.get("component", "")
        if not cid:
            continue
        if cid not in seen_in_run:
            seen_in_run[cid] = []
        for k in meta.get("input_vars", {}):
            if k not in seen_in_run[cid]:
                seen_in_run[cid].append(k)
        for k in meta.get("output_vars", {}):
            if k not in seen_in_run[cid]:
                seen_in_run[cid].append(k)

    for cid, field_names in seen_in_run.items():
        entry = components.get(cid)
        if entry is None:
            entry = {
                "count": 1,
                "first_seen": today_str,
                "last_seen": today_str,
                "sample_fields": sorted(field_names),
                "sample_flow_path": metas[0].get("flow_path", ""),
                "promoted": False,
                "promotion_date": None,
            }
            components[cid] = entry
        else:
            entry["count"] = entry.get("count", 0) + 1
            entry["last_seen"] = today_str
            existing_fields = set(entry.get("sample_fields", []))
            existing_fields.update(field_names)
            entry["sample_fields"] = sorted(existing_fields)
            if not entry.get("sample_flow_path"):
                entry["sample_flow_path"] = metas[0].get("flow_path", "")

        # Compute confidence
        cnt = entry["count"]
        entry["confidence"] = "high" if cnt >= 3 else ("medium" if cnt >= 2 else "low")

        if entry["count"] >= 3 and not entry.get("promoted"):
            threshold_hits.append(cid)

    # Print cleanup suggestion for low-confidence stale entries
    low_stale = []
    for cid, entry in components.items():
        if (entry.get("confidence") == "low"
                and entry.get("last_seen")
                and entry["last_seen"] < today_str):
            # crude check: last_seen < today = potentially stale
            if (date.today() - date.fromisoformat(entry["last_seen"])).days >= 90:
                low_stale.append(cid)

    counts_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    if low_stale:
        print(f"\n   [清理建议] {len(low_stale)} 个低置信度组件超过 90 天未出现:")
        for c in low_stale[:10]:
            print(f"     - {c} (最后出现: {components[c]['last_seen']})")
        if len(low_stale) > 10:
            print(f"     ... 共 {len(low_stale)} 个")

    return threshold_hits
