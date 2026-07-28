"""Hash snapshot helpers for incremental update."""
from __future__ import annotations
import json
from pathlib import Path


def write_hash_snapshot(manifest: dict, dest: Path) -> None:
    lines = []
    for n in manifest.get("nodes", []):
        lines.append(
            f"{n['seq']}|{n.get('show_name','')}|{n.get('code_hash','')}|"
            f"{n.get('flow_file','')}|"
            f"{json.dumps(n.get('input_vars', {}), sort_keys=True, ensure_ascii=False)}|"
            f"{json.dumps(n.get('output_vars', {}), sort_keys=True, ensure_ascii=False)}"
        )
    dest.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
