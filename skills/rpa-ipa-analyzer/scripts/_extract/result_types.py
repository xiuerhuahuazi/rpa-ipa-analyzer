from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class FlowEdge:
    sourceNode: str
    targetNode: str
    source: str
    target: str
    flow_file: str


@dataclass
class NodeMeta:
    node_id: str
    component_id: str
    show_name: str
    code: str
    code_field: str
    input_vars: dict[str, Any]
    output_vars: dict[str, Any]
    ext: str
    flow_path: str
    code_hash: str
    code_lines: int
    extraction_method: str
    parent_block: str = ""


@dataclass
class ExtractResult:
    out_dir: Path
    manifest: dict
    manifest_path: Path
    project_name: str
    stats: dict
    promotion_candidates: list[str] = field(default_factory=list)
