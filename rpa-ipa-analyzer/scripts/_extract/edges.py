from __future__ import annotations
from .result_types import FlowEdge


def collect_edges_from_flow(flow: dict, flow_file: str) -> list[FlowEdge]:
    """Extract edges from graphData.edges[] with flow_file attribution."""
    edges = []
    graph = flow.get("graphData", {})
    raw_edges = graph.get("edges", [])
    if not isinstance(raw_edges, list):
        return edges
    for e in raw_edges:
        edges.append(FlowEdge(
            sourceNode=e.get("sourceNode", ""),
            targetNode=e.get("targetNode", ""),
            source=e.get("source", ""),
            target=e.get("target", ""),
            flow_file=flow_file,
        ))
    return edges


def build_adjacency(edges: list[FlowEdge]) -> dict[str, list[str]]:
    """Build adjacency list: sourceNode -> [targetNode, ...]."""
    adj: dict[str, list[str]] = {}
    for e in edges:
        adj.setdefault(e.sourceNode, []).append(e.targetNode)
    return adj
