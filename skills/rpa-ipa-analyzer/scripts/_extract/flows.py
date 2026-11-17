from __future__ import annotations
from .extractors import extract_node_meta
from .edges import collect_edges_from_flow
from .result_types import NodeMeta, FlowEdge


def _find_block(blocks: list[dict], block_id: str) -> dict | None:
    for blk in blocks:
        if blk.get("id") == block_id:
            return blk
    return None


def _block_display_name(node: dict, block_data: dict, block_id: str) -> str:
    """Resolve a function-block node's display name.

    Prefer the value bound to the node's first property param (what the designer
    shows), then the block's own ``name``, then the block id.
    """
    props = node.get("properties") or []
    if isinstance(props, list):
        params = props[0].get("params", []) if isinstance(props[0], dict) else []
        if isinstance(params, list) and params:
            value = params[0].get("value", "")
            if isinstance(value, str) and value.strip().strip('"'):
                return value.strip().strip('"')
    name = block_data.get("name", "") if isinstance(block_data, dict) else ""
    if name:
        return name
    return block_id


def _collect_nodes(
    nodes: list[dict],
    blocks: list[dict],
    flow_path: str,
    parent_block: str,
    metas: list[NodeMeta],
    edges: list[FlowEdge],
    visited: set[str],
) -> None:
    """Recursively walk a node list, descending into function blocks.

    IPA flow files use a flat top-level ``blocks[]`` table. A ``process_function_block``
    node inside any graph references one of those entries by its ``id`` (its own
    ``id`` equals the entry's ``id``).  Children live in that block's
    ``graphData.nodes`` and may themselves contain further ``process_function_block``
    nodes, so we recurse instead of stopping at depth one.

    ``visited`` guards against cycles (a block referencing itself) so a
    pathological project cannot loop forever.
    """
    for node in nodes:
        meta = extract_node_meta(node, flow_path)
        if meta:
            if parent_block:
                meta.parent_block = parent_block
            metas.append(meta)
        if node.get("component_id") != "process_function_block":
            continue
        block_id = node.get("id", "")
        if not block_id or block_id in visited:
            continue
        block_data = _find_block(blocks, block_id)
        if not block_data or not isinstance(block_data, dict):
            continue
        block_graph = block_data.get("graphData", {})
        block_nodes = block_graph.get("nodes", [])
        if not isinstance(block_nodes, list):
            block_nodes = []
        block_name = _block_display_name(node, block_data, block_id)
        nested_path = f"{flow_path}::{block_name}"
        nested_parent = f"{parent_block}::{block_name}" if parent_block else block_name
        edges.extend(collect_edges_from_flow(block_data, nested_path))
        visited.add(block_id)
        _collect_nodes(block_nodes, blocks, nested_path, nested_parent,
                       metas, edges, visited)


def extract_nodes_from_flow(flow: dict, flow_path: str) -> tuple[list[NodeMeta], list[FlowEdge]]:
    """Extract code nodes and edges from a flow JSON, including nested blocks.

    Walks the whole block tree (block nodes reference entries in the flat
    ``blocks[]`` table, recursively), so nodes inside nested function blocks are
    no longer dropped.
    """
    all_metas: list[NodeMeta] = []
    all_edges: list[FlowEdge] = []

    all_edges.extend(collect_edges_from_flow(flow, flow_path))

    graph = flow.get("graphData", {})
    nodes = graph.get("nodes", [])
    if not isinstance(nodes, list):
        nodes = []
    blocks = flow.get("blocks", [])
    if not isinstance(blocks, list):
        blocks = []

    _collect_nodes(nodes, blocks, flow_path, "", all_metas, all_edges, set())
    return all_metas, all_edges
