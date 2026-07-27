from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from .lattice import generate_edges, generate_seats
from .transform import br_mirror, kc27_transform


@dataclass(frozen=True)
class Bridge:
    bridge_id: str
    source: int
    target: int
    relation: str
    declaration: str
    standing: str = "DECLARED_UNCERTIFIED"


DECLARED_BRIDGES = (
    Bridge("BR001", 41, 81, "RETURN_TO_IC10", "RETURN/PLUS successor enters I01"),
    Bridge("BR002", 42, 81, "RETURN_TO_IC10", "RETURN/HINGE process parent enters I01"),
    Bridge("BR003", 43, 81, "RETURN_TO_IC10", "RETURN/STAR audit enters I01"),
    Bridge("BR004", 44, 81, "CARRIER_TO_IDENTITY", "F01 address feeds I01"),
    Bridge("BR005", 76, 81, "REPLAY_TO_IDENTITY", "F33 replay/Merkle feeds I01"),
    Bridge("BR006", 80, 81, "PUBLICATION_TO_IDENTITY", "F37 publication feeds I01"),
    Bridge("BR007", 29, 44, "NAVIGATE_TO_CARRIER", "NAVIGATE/PLUS consumes F01"),
    Bridge("BR008", 29, 58, "NAVIGATE_TO_CARRIER", "NAVIGATE/PLUS consumes F15"),
    Bridge("BR009", 34, 47, "TRANSFORM_TO_CARRIER", "TRANSFORM/STAR uses F04"),
    Bridge("BR010", 41, 44, "RETURN_TO_CARRIER", "RETURN/PLUS hands off to F01"),
    Bridge("BR011", 43, 76, "RETURN_TO_REPLAY", "RETURN/STAR exports to F33"),
    Bridge("BR012", 43, 141, "RETURN_TO_SIGNATURE", "RETURN/STAR exports to M09"),
    Bridge("BR013", 21, 43, "RETURN_CLOUD", "multivalued return receives RETURN/STAR"),
    Bridge("BR014", 22, 43, "RESEED_RETURN", "recursive reseed receives RETURN/STAR"),
    Bridge("BR015", 61, 30, "OBSTRUCTION_ROUTE", "invalid merge routes to F18"),
    Bridge("BR016", 40, 88, "REPAIR_TO_I08", "route repair enters bridge/return gate"),
    Bridge("BR017", 90, 119, "PROMOTION_TO_QSHRINK", "I10 emits to KC27-P13"),
    Bridge("BR018", 119, 144, "QSHRINK_TO_M12", "QSHRINK emits to M12"),
    Bridge("BR019", 144, 1, "SUCCESSOR_RESEED", "M12 reseeds provenance-bearing H01 prime"),
    Bridge("BR020", 88, 89, "I08_TO_I09", "bridge manifest enters replay gate"),
    Bridge("BR021", 85, 65, "DRIFT_WARNING", "invariant drift routes to F22"),
    Bridge("BR022", 16, 61, "INVARIANT_TO_OBSTRUCTION", "X-00-FL routes to F18"),
    Bridge("BR023", 13, 92, "POLE_SUPPORT", "branch carrier supports KC15 {10}"),
    Bridge("BR024", 7, 91, "POLE_SUPPORT", "object identity supports KC15 {11}"),
    Bridge("BR025", 15, 93, "POLE_SUPPORT", "zero taxonomy supports KC15 {00}"),
    Bridge("BR026", 19, 94, "POLE_SUPPORT", "return contract supports KC15 {01}"),
    Bridge("BR027", 6, 106, "ACTIVATION_TO_KC27", "H06 activation admits at KC27-P00"),
    Bridge("BR028", 140, 17, "HEALING_TO_DEFECT", "M08 healing receives X-00-CL defects"),
)

RETURN_ARM = (
    41,
    42,
    43,
    81,
    82,
    83,
    84,
    85,
    86,
    87,
    88,
    89,
    90,
    119,
    144,
    1,
)


def _pair(left: int, right: int) -> tuple[int, int]:
    return (left, right) if left < right else (right, left)


def navigation_relations(
    x16_reading: str = "algebra",
    *,
    include_mirrors: bool = True,
    include_bridges: bool = True,
) -> tuple[dict[str, Any], ...]:
    relations = [
        {
            "source": edge.source,
            "target": edge.target,
            "relation": edge.edge_class,
            "semantics": edge.semantics,
            "standing": "STRUCTURAL",
        }
        for edge in generate_edges(x16_reading)
    ]
    if include_mirrors:
        seen: set[tuple[int, int, str]] = set()
        for gid in range(23, 44):
            target = br_mirror(gid).target_gid
            pair = _pair(gid, target)
            if (*pair, "BR21_MIRROR") not in seen:
                relations.append(
                    {
                        "source": pair[0],
                        "target": pair[1],
                        "relation": "BR21_MIRROR",
                        "semantics": "conjugate operator view",
                        "standing": "STRUCTURAL",
                    }
                )
                seen.add((*pair, "BR21_MIRROR"))
        for gid in range(106, 133):
            target = kc27_transform(gid, signs=(-1, -1, -1)).target_gid
            pair = _pair(gid, target)
            if (*pair, "KC27_J") not in seen:
                relations.append(
                    {
                        "source": pair[0],
                        "target": pair[1],
                        "relation": "KC27_J",
                        "semantics": "signed-inversion mirror",
                        "standing": "STRUCTURAL",
                    }
                )
                seen.add((*pair, "KC27_J"))
    if include_bridges:
        relations.extend(
            {
                "source": bridge.source,
                "target": bridge.target,
                "relation": bridge.relation,
                "semantics": bridge.declaration,
                "standing": bridge.standing,
                "bridge_id": bridge.bridge_id,
            }
            for bridge in DECLARED_BRIDGES
        )
    relations.sort(key=lambda row: (row["source"], row["target"], row["relation"]))
    return tuple(relations)


def adjacency(relations: Iterable[dict[str, Any]]) -> dict[int, set[int]]:
    graph: dict[int, set[int]] = defaultdict(set)
    for relation in relations:
        source, target = relation["source"], relation["target"]
        graph[source].add(target)
        graph[target].add(source)
    for gid in range(1, 145):
        graph[gid]
    return graph


def components(graph: dict[int, set[int]]) -> list[set[int]]:
    unseen = set(range(1, 145))
    result: list[set[int]] = []
    while unseen:
        start = min(unseen)
        component = {start}
        queue = deque([start])
        unseen.remove(start)
        while queue:
            node = queue.popleft()
            for neighbor in graph[node]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    component.add(neighbor)
                    queue.append(neighbor)
        result.append(component)
    return result


def distances(start: int, graph: dict[int, set[int]]) -> dict[int, int]:
    result = {start: 0}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for neighbor in graph[node]:
            if neighbor not in result:
                result[neighbor] = result[node] + 1
                queue.append(neighbor)
    return result


def shortest_path(start: int, target: int, graph: dict[int, set[int]]) -> list[int]:
    parent: dict[int, int | None] = {start: None}
    queue = deque([start])
    while queue and target not in parent:
        node = queue.popleft()
        for neighbor in sorted(graph[node]):
            if neighbor not in parent:
                parent[neighbor] = node
                queue.append(neighbor)
    if target not in parent:
        return []
    path: list[int] = []
    node: int | None = target
    while node is not None:
        path.append(node)
        node = parent[node]
    return list(reversed(path))


def _metro_lines() -> dict[str, tuple[int, ...]]:
    lines: dict[str, tuple[int, ...]] = {
        "BR21_PLUS": (23, 26, 29, 32, 35, 38, 41),
        "BR21_HINGE": (24, 27, 30, 33, 36, 39, 42),
        "BR21_STAR": (25, 28, 31, 34, 37, 40, 43),
        "F37": tuple(range(44, 81)),
        "IC10": tuple(range(81, 91)),
        "SSN12": tuple(range(133, 145)),
        "H6": (1, 2, 3, 4, 5, 6, 1),
        "KC27_X": (118, 119, 120),
        "KC27_Y": (116, 119, 122),
        "KC27_Z": (110, 119, 128),
        "RETURN_ARM": RETURN_ARM,
    }
    for lens_index, lens in enumerate(("SQ", "FL", "CL", "FR")):
        lines[f"X16_{lens}"] = tuple(
            [7 + 4 * pole + lens_index for pole in range(4)] + [7 + lens_index]
        )
    return lines


def navigation_report() -> dict[str, Any]:
    intra_relations = navigation_relations(include_bridges=False)
    all_relations = navigation_relations(include_bridges=True)
    intra_graph = adjacency(intra_relations)
    graph = adjacency(all_relations)
    comps = components(graph)
    all_distances = {gid: distances(gid, graph) for gid in range(1, 145)}
    eccentricity = {gid: max(result.values()) for gid, result in all_distances.items()}
    radius = min(eccentricity.values())
    distinct_pairs = {_pair(row["source"], row["target"]) for row in all_relations}
    distinct_intra_pairs = {
        _pair(row["source"], row["target"]) for row in intra_relations
    }
    lines = _metro_lines()
    line_results = {
        name: all(right in graph[left] for left, right in zip(path, path[1:]))
        for name, path in lines.items()
    }
    seats = generate_seats()
    return {
        "schema": "KC144.NavigationGraph.V3",
        "reading": "X16_ALGEBRA_WITH_BR21_AND_KC27_MIRRORS",
        "intra_band_relation_records": len(intra_relations),
        "distinct_intra_adjacency_edges": len(distinct_intra_pairs),
        "declared_bridge_records": len(DECLARED_BRIDGES),
        "distinct_adjacency_edges": len(distinct_pairs),
        "relation_census": dict(Counter(row["relation"] for row in all_relations)),
        "components": len(comps),
        "component_sizes": sorted((len(component) for component in comps), reverse=True),
        "diameter": max(eccentricity.values()),
        "radius": radius,
        "centers": [
            {"gid": gid, "station": seats[gid - 1].station}
            for gid, value in eccentricity.items()
            if value == radius
        ],
        "reachable_from_H06": len(all_distances[6]),
        "max_hops_from_H06": max(all_distances[6].values()),
        "metro_lines": {
            name: {"path": list(lines[name]), "verdict": "PASS" if passed else "FAIL"}
            for name, passed in line_results.items()
        },
        "return_arm": {
            "path": list(RETURN_ARM),
            "verdict": "PASS" if line_results["RETURN_ARM"] else "FAIL",
            "successor_identity": "GID001_PRIME_APPEND_ONLY",
        },
        "bridge_standing": "DECLARED_GRAPH_CONNECTIVITY_NOT_TRANSPORT_CERTIFICATION",
        "relations": list(all_relations),
    }


def bridge_registry() -> dict[str, Any]:
    return {
        "schema": "KC144.DeclaredBridgeRegistry.V3",
        "count": len(DECLARED_BRIDGES),
        "standing": "DECLARED_GRAPH_CONNECTIVITY_NOT_TRANSPORT_CERTIFICATION",
        "certified_transport_count": 0,
        "bridges": [asdict(bridge) for bridge in DECLARED_BRIDGES],
    }
