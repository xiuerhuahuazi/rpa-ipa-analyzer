from __future__ import annotations
from .extractors import extract_node_meta
from .edges import collect_edges_from_flow
from .result_types import NodeMeta, FlowEdge


def _find_block(blocks: list[dict], block_id: str) -> dict | None:
    for blk in blocks:
        if blk.get("id") == block_id:
            return blk
    return None


def extract_nodes_from_flow(flow: dict, flow_path: str) -> tuple[list[NodeMeta], list[FlowEdge]]:
    """Extract code nodes and edges from a flow JSON, including nested blocks."""
    all_metas: list[NodeMeta] = []
    all_edges: list[FlowEdge] = []

    all_edges.extend(collect_edges_from_flow(flow, flow_path))

    graph = flow.get("graphData", {})
    nodes = graph.get("nodes", [])
    blocks = flow.get("blocks", [])
    if not isinstance(blocks, list):
        blocks = []

    for node in nodes:
        meta = extract_node_meta(node, flow_path)
        if meta:
            all_metas.append(meta)
        if node.get("component_id") == "process_function_block":
            block_id = node.get("id", "")
            block_data = _find_block(blocks, block_id)
            if block_data and isinstance(block_data, dict):
                block_graph = block_data.get("graphData", {})
                block_nodes = block_graph.get("nodes", [])
                block_blocks = block_data.get("blocks", [])
                if not isinstance(block_blocks, list):
                    block_blocks = []
                block_name = (node.get("properties", [{}])[0].get("params", [{}])[0].get("value", "")
                              or block_data.get("name", block_id))
                nested_path = f"{flow_path}::{block_name}"
                all_edges.extend(collect_edges_from_flow(block_data, nested_path))
                for bnode in block_nodes:
                    bmeta = extract_node_meta(bnode, nested_path)
                    if bmeta:
                        bmeta.parent_block = block_name
                        all_metas.append(bmeta)
    return all_metas, all_edges
