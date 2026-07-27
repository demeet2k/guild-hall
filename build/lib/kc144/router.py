from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    edge_type: str
    certified: bool
    return_class: str


def bounded_routes(
    edges: Iterable[Edge],
    start: str,
    targets: set[str],
    budget: int,
) -> list[list[Edge]]:
    """Return certified routes without silently exceeding the route budget."""
    if budget < 0:
        raise ValueError("budget must be nonnegative")
    adjacency: dict[str, list[Edge]] = {}
    for edge in edges:
        if edge.certified:
            adjacency.setdefault(edge.source, []).append(edge)

    found: list[list[Edge]] = []
    queue: deque[tuple[str, list[Edge], frozenset[str]]] = deque(
        [(start, [], frozenset({start}))]
    )
    while queue:
        node, path, seen = queue.popleft()
        if node in targets:
            found.append(path)
            continue
        if len(path) >= budget:
            continue
        for edge in adjacency.get(node, []):
            if edge.target not in seen:
                queue.append((edge.target, path + [edge], seen | {edge.target}))
    return found

