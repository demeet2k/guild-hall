from __future__ import annotations

import hashlib
import json
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from typing import Any

from .navigation import adjacency, navigation_relations


@dataclass(frozen=True)
class WaveQuery:
    query_id: str
    starts: tuple[int, ...]
    route_budget: int = 18
    decay: float = 0.85

    def __post_init__(self) -> None:
        if not self.query_id:
            raise ValueError("query_id is required")
        if not self.starts or any(not 1 <= gid <= 144 for gid in self.starts):
            raise ValueError("starts must contain KC144 gids")
        if self.route_budget < 0:
            raise ValueError("route_budget must be nonnegative")
        if not 0 < self.decay <= 1:
            raise ValueError("decay must be in (0, 1]")


def _source_wave(start: int, graph: dict[int, set[int]], budget: int) -> tuple[dict[int, int], dict[int, int], dict[int, set[int]]]:
    distance = {start: 0}
    path_count = {start: 1}
    parents: dict[int, set[int]] = defaultdict(set)
    queue = deque([start])
    while queue:
        node = queue.popleft()
        if distance[node] == budget:
            continue
        for neighbor in sorted(graph[node]):
            proposed = distance[node] + 1
            if neighbor not in distance:
                distance[neighbor] = proposed
                path_count[neighbor] = path_count[node]
                parents[neighbor].add(node)
                queue.append(neighbor)
            elif proposed == distance[neighbor]:
                path_count[neighbor] += path_count[node]
                parents[neighbor].add(node)
    return distance, path_count, parents


def propagate(query: WaveQuery) -> dict[str, Any]:
    relations = navigation_relations()
    graph = adjacency(relations)
    waves = {
        start: _source_wave(start, graph, query.route_budget)
        for start in sorted(set(query.starts))
    }
    nodes: list[dict[str, Any]] = []
    for gid in range(1, 145):
        arrivals = {
            start: {
                "distance": waves[start][0][gid],
                "shortest_path_count": waves[start][1][gid],
            }
            for start in waves
            if gid in waves[start][0]
        }
        if not arrivals:
            continue
        nearest_distance = min(value["distance"] for value in arrivals.values())
        basin = sorted(
            start for start, value in arrivals.items() if value["distance"] == nearest_distance
        )
        activation = sum(
            query.decay ** value["distance"] for value in arrivals.values()
        )
        signature_body = {
            "query_id": query.query_id,
            "gid": gid,
            "arrivals": arrivals,
            "basin": basin,
        }
        signature = hashlib.sha256(
            json.dumps(signature_body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        nodes.append(
            {
                "gid": gid,
                "arrivals": arrivals,
                "nearest_distance": nearest_distance,
                "basin": basin,
                "interference": len(basin) > 1,
                "activation": round(activation, 12),
                "path_signature": f"sha256:{signature}",
            }
        )

    reached = {node["gid"] for node in nodes}
    frontier = sorted(
        node["gid"]
        for node in nodes
        if min(value["distance"] for value in node["arrivals"].values())
        == query.route_budget
    )
    relation_overlay: list[dict[str, Any]] = []
    for relation in relations:
        left, right = relation["source"], relation["target"]
        traversed_by = []
        for start, (distance, _, _) in waves.items():
            if (
                left in distance
                and right in distance
                and abs(distance[left] - distance[right]) == 1
                and max(distance[left], distance[right]) <= query.route_budget
            ):
                traversed_by.append(start)
        if traversed_by:
            relation_overlay.append(
                {
                    "source": left,
                    "target": right,
                    "relation": relation["relation"],
                    "wave_sources": traversed_by,
                    "weight": len(traversed_by),
                    "truth_effect": "NONE",
                }
            )

    return {
        "schema": "KC144.NavigationWave.V3",
        "query": asdict(query),
        "mode": "PARALLEL_BOUNDED_WAVEFRONT_OVER_ALL_DECLARED_RELATIONS",
        "base_graph_mutated": False,
        "reached": len(reached),
        "coverage": f"{len(reached)}/144",
        "frontier": frontier,
        "interference_nodes": [
            node["gid"] for node in nodes if node["interference"]
        ],
        "nodes": nodes,
        "relation_weight_overlay": relation_overlay,
        "laws": [
            "weights schedule attention; they do not certify truth",
            "the overlay is append-only and does not mutate the frozen graph",
            "route budget bounds traversal; unvisited does not mean nonexistent",
        ],
    }
