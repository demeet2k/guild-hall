from __future__ import annotations

import hashlib
import json
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from itertools import combinations
from math import isqrt
from typing import Any, Iterable

from .lattice import K4, generate_seats
from .navigation import navigation_relations


class ParallelRouteError(ValueError):
    pass


@dataclass(frozen=True)
class RouteSimulation:
    route_id: str
    prefix: tuple[int, ...]
    target: int
    graph_reading: str
    route_budget: int = 18
    witness_limit: int = 8

    def __post_init__(self) -> None:
        if not self.route_id:
            raise ParallelRouteError("route_id is required")
        if not self.prefix or any(not 1 <= gid <= 144 for gid in self.prefix):
            raise ParallelRouteError("prefix must contain KC144 GIDs")
        if not 1 <= self.target <= 144:
            raise ParallelRouteError("target must be a KC144 GID")
        if self.graph_reading not in {"schedule", "algebra", "both"}:
            raise ParallelRouteError("graph_reading must be schedule, algebra, or both")
        if self.route_budget < len(self.prefix) - 1:
            raise ParallelRouteError("route_budget cannot be shorter than the prefix")
        if not 1 <= self.witness_limit <= 64:
            raise ParallelRouteError("witness_limit must be in [1, 64]")


@dataclass(frozen=True)
class AgentTask:
    task_id: str
    execution_mode: str
    depends_on: tuple[str, ...] = ()
    read_set: tuple[str, ...] = ()
    write_set: tuple[str, ...] = ()
    priority: int = 100
    independent_agent_required: bool = False

    def __post_init__(self) -> None:
        if not self.task_id:
            raise ParallelRouteError("task_id is required")
        if self.execution_mode not in {
            "PARALLEL_WORKER",
            "SOLO_WORKER",
            "COORDINATOR_ONLY",
            "DETERMINISTIC_REDUCER",
        }:
            raise ParallelRouteError("unknown execution mode")
        if self.task_id in self.depends_on:
            raise ParallelRouteError("a task cannot depend on itself")


DEFAULT_SIMULATIONS = (
    RouteSimulation("A_X16_CONTRACT", (7, 11, 15, 19), 90, "schedule"),
    RouteSimulation(
        "B_BR21_ADVERSARIAL", (25, 28, 31, 34, 37, 40, 43), 90, "algebra"
    ),
    RouteSimulation("C_KC27_CUBE", (110, 119, 128), 90, "both"),
    RouteSimulation("D_KC15_SUPPORT", (91, 95, 101, 105), 90, "algebra"),
    RouteSimulation(
        "E_IC10_ADJUDICATION", tuple(range(81, 91)), 90, "both"
    ),
)

_SEATS = {seat.gid: seat for seat in generate_seats()}


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    for divisor in range(2, isqrt(value) + 1):
        if value % divisor == 0:
            return False
    return True


def _prime_projection(gid: int) -> dict[str, Any]:
    primes = [value for value in range(2, 146) if _is_prime(value)]
    previous = max((value for value in primes if value <= gid), default=None)
    following = min((value for value in primes if value >= gid), default=None)
    return {
        "is_prime": _is_prime(gid),
        "prime_rank": sum(value <= gid for value in primes),
        "previous_or_self": previous,
        "next_or_self": following,
    }


def coordinate_vector(gid: int) -> dict[str, Any]:
    """Project one immutable GID through all declared observer coordinates.

    Native coordinates retain the generated KC144 seat identity. Other entries
    are explicitly named observer projections; they never overwrite the native
    band or station.
    """
    if gid not in _SEATS:
        raise ParallelRouteError(f"GID outside KC144: {gid}")
    seat = _SEATS[gid]
    index = gid - 1
    row, column = divmod(index, 12)
    d4 = {
        12 * row + column + 1,
        12 * column + (11 - row) + 1,
        12 * (11 - row) + (11 - column) + 1,
        12 * (11 - column) + row + 1,
        12 * row + (11 - column) + 1,
        12 * (11 - row) + column + 1,
        12 * column + row + 1,
        12 * (11 - column) + (11 - row) + 1,
    }
    return {
        "canonical": {
            "gid": gid,
            "grid": seat.grid,
            "band": seat.band,
            "station": seat.station,
        },
        "native_coordinates": seat.coordinates,
        "adaptive_binary_mod4": {
            "pole": K4[index % 4],
            "turn": index % 4,
        },
        "dls_4x4_in_12x12": {
            "tile": [row // 4 + 1, column // 4 + 1],
            "local": [row % 4 + 1, column % 4 + 1],
        },
        "grid16_injection": {
            "row": (row * 16) // 12 + 1,
            "column": (column * 16) // 12 + 1,
        },
        "br21_modular": {
            "cycle": index // 21,
            "residue": index % 21 + 1,
        },
        "kc27_modular": {
            "cycle": index // 27,
            "residue": index % 27,
        },
        "kc54_duplex": {
            "cycle": index // 54,
            "sheet": (index // 27) % 2,
            "residue": index % 27,
        },
        "c144": {
            "index": index,
            "inverse": ((-index) % 144) + 1,
            "antipode": ((index + 72) % 144) + 1,
        },
        "angle360": {
            "numerator": 5 * index,
            "denominator": 2,
            "degrees": 2.5 * index,
        },
        "great_year25920": {
            "phase_year": 180 * index,
            "period_years": 25920,
        },
        "prime": _prime_projection(gid),
        "d4_orbit": sorted(d4),
        "liminal": {
            "row_boundary": column in {0, 11},
            "column_boundary": row in {0, 11},
            "dls_tile_boundary": row % 4 in {0, 3} or column % 4 in {0, 3},
            "native_band_boundary": gid in {
                1,
                6,
                7,
                22,
                23,
                43,
                44,
                80,
                81,
                90,
                91,
                105,
                106,
                132,
                133,
                144,
            },
        },
    }


def coordinate_delta(source: int, target: int) -> dict[str, Any]:
    left = coordinate_vector(source)
    right = coordinate_vector(target)
    lenses = sorted(left)
    preserved = [lens for lens in lenses if left[lens] == right[lens]]
    changed = [lens for lens in lenses if left[lens] != right[lens]]
    removed = [{"lens": lens, "value": left[lens]} for lens in changed]
    added = [{"lens": lens, "value": right[lens]} for lens in changed]
    return {
        "source_gid": source,
        "target_gid": target,
        "preserved_lenses": preserved,
        "changed_lenses": changed,
        "removed_coordinate_states": removed,
        "added_coordinate_states": added,
        "preserved_count": len(preserved),
        "changed_count": len(changed),
        "information_effect": "LOSSLESS_TRACE_PRESERVES_BOTH_ENDPOINTS",
        "truth_effect": "NONE",
    }


def _relation_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row["source"],
        row["target"],
        row["relation"],
        row["standing"],
        row["semantics"],
        row.get("bridge_id", ""),
    )


def _typed_relations(reading: str) -> tuple[dict[str, Any], ...]:
    unique = {_relation_key(row): dict(row) for row in navigation_relations(reading)}
    result = []
    for key in sorted(unique):
        row = unique[key]
        row["edge_id"] = _digest(
            {
                "source": row["source"],
                "target": row["target"],
                "relation": row["relation"],
                "standing": row["standing"],
                "semantics": row["semantics"],
                "bridge_id": row.get("bridge_id"),
            }
        )
        result.append(row)
    return tuple(result)


def _arc(row: dict[str, Any], source: int, target: int) -> dict[str, Any]:
    return {
        "edge_id": row["edge_id"],
        "source": source,
        "target": target,
        "relation": row["relation"],
        "semantics": row["semantics"],
        "standing": row["standing"],
        "bridge_id": row.get("bridge_id"),
    }


def _adjacency(
    relations: Iterable[dict[str, Any]],
) -> dict[int, list[tuple[int, dict[str, Any]]]]:
    graph: dict[int, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    for row in relations:
        graph[row["source"]].append((row["target"], row))
        graph[row["target"]].append((row["source"], row))
    for gid in range(1, 145):
        graph[gid].sort(key=lambda item: (item[0], _relation_key(item[1])))
    return graph


def _edge_options(
    source: int,
    target: int,
    graph: dict[int, list[tuple[int, dict[str, Any]]]],
) -> list[dict[str, Any]]:
    options = [
        _arc(row, source, target)
        for neighbor, row in graph[source]
        if neighbor == target
    ]
    return sorted(
        options,
        key=lambda arc: (
            arc["standing"] != "STRUCTURAL",
            arc["relation"],
            arc["edge_id"],
        ),
    )


def _shortest_language(
    start: int,
    target: int,
    graph: dict[int, list[tuple[int, dict[str, Any]]]],
    witness_limit: int,
) -> tuple[int | None, int, list[list[dict[str, Any]]]]:
    distance = {start: 0}
    count = {start: 1}
    parents: dict[int, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for neighbor, row in graph[node]:
            proposed = distance[node] + 1
            arc = _arc(row, node, neighbor)
            if neighbor not in distance:
                distance[neighbor] = proposed
                count[neighbor] = count[node]
                parents[neighbor].append((node, arc))
                queue.append(neighbor)
            elif proposed == distance[neighbor]:
                count[neighbor] += count[node]
                parents[neighbor].append((node, arc))
    if target not in distance:
        return None, 0, []

    for node in parents:
        parents[node].sort(
            key=lambda item: (
                item[0],
                item[1]["standing"] != "STRUCTURAL",
                item[1]["relation"],
                item[1]["edge_id"],
            )
        )

    witnesses: list[list[dict[str, Any]]] = []

    def backtrack(node: int, reverse_arcs: list[dict[str, Any]]) -> None:
        if len(witnesses) >= witness_limit:
            return
        if node == start:
            witnesses.append(list(reversed(reverse_arcs)))
            return
        for parent, arc in parents[node]:
            backtrack(parent, reverse_arcs + [arc])
            if len(witnesses) >= witness_limit:
                return

    backtrack(target, [])
    return distance[target], count[target], witnesses


def _bounded_walk_counts(
    start: int,
    target: int,
    graph: dict[int, list[tuple[int, dict[str, Any]]]],
    budget: int,
) -> dict[int, int]:
    state = {start: 1}
    result = {0: 1 if start == target else 0}
    for length in range(1, budget + 1):
        successor: dict[int, int] = defaultdict(int)
        for node, paths in sorted(state.items()):
            for neighbor, _ in graph[node]:
                successor[neighbor] += paths
        state = dict(successor)
        result[length] = state.get(target, 0)
    return result


def _analyze_path(
    nodes: list[int], arcs: list[dict[str, Any]]
) -> dict[str, Any]:
    if len(nodes) != len(arcs) + 1:
        raise ParallelRouteError("node/arc cardinality mismatch")
    transitions = []
    for left, right, arc in zip(nodes, nodes[1:], arcs):
        if arc["source"] != left or arc["target"] != right:
            raise ParallelRouteError("arc endpoints do not match node path")
        delta = coordinate_delta(left, right)
        transitions.append(
            {
                **arc,
                "coordinate_delta": delta,
                "transform_contract": {
                    "domain": f"GID{left:03d}",
                    "codomain": f"GID{right:03d}",
                    "preconditions": [
                        f"EDGE_ID::{arc['edge_id']}",
                        f"STANDING::{arc['standing']}",
                    ],
                    "preserved": delta["preserved_lenses"],
                    "changed": delta["changed_lenses"],
                    "removed": delta["removed_coordinate_states"],
                    "added": delta["added_coordinate_states"],
                    "carry": [
                        "source_coordinate_vector",
                        "target_coordinate_vector",
                        "typed_edge_identity",
                    ],
                    "loss": [],
                    "residual": (
                        []
                        if arc["standing"] == "STRUCTURAL"
                        else ["transport_certification_required"]
                    ),
                    "return_class": (
                        "STRUCTURAL_RETRACE"
                        if arc["standing"] == "STRUCTURAL"
                        else "DECLARED_RETRACE_UNCERTIFIED"
                    ),
                    "inverse_witness": {
                        "edge_id": arc["edge_id"],
                        "reverse_source": right,
                        "reverse_target": left,
                    },
                    "truth_effect": "NONE",
                },
            }
        )
    uncertified = sum(
        transition["standing"] != "STRUCTURAL" for transition in transitions
    )
    body = {
        "nodes": nodes,
        "edges": transitions,
        "hops": len(arcs),
        "revisited_nodes": sorted(
            gid for gid in set(nodes) if nodes.count(gid) > 1
        ),
        "net_coordinate_delta": coordinate_delta(nodes[0], nodes[-1]),
        "navigation_valid": True,
        "content_transport_certified": False,
        "uncertified_bridge_count": uncertified,
        "standing": (
            "DECLARED_NAVIGATION_WITH_UNCERTIFIED_BRIDGES"
            if uncertified
            else "STRUCTURAL_NAVIGATION_ONLY"
        ),
        "why_valid": [
            "every consecutive pair is bound to an exact typed relation record",
            "the complete route stays inside its declared hop budget",
            "coordinate changes retain both endpoint states in the trace",
            "navigation standing is kept separate from transport certification",
            "no route changes evidence, governance authority, or production truth",
        ],
        "truth_effect": "NONE",
    }
    return {**body, "path_signature": _digest(body)}


def simulate_route(spec: RouteSimulation) -> dict[str, Any]:
    relations = _typed_relations(spec.graph_reading)
    graph = _adjacency(relations)
    prefix_arcs: list[dict[str, Any]] = []
    prefix_alternatives = 1
    for left, right in zip(spec.prefix, spec.prefix[1:]):
        options = _edge_options(left, right, graph)
        if not options:
            raise ParallelRouteError(
                f"{spec.route_id}: undeclared prefix edge {left}->{right}"
            )
        prefix_alternatives *= len(options)
        prefix_arcs.append(options[0])

    prefix_hops = len(prefix_arcs)
    remaining = spec.route_budget - prefix_hops
    suffix_distance, suffix_count, suffix_witnesses = _shortest_language(
        spec.prefix[-1], spec.target, graph, spec.witness_limit
    )
    if suffix_distance is None or suffix_distance > remaining:
        raise ParallelRouteError(
            f"{spec.route_id}: target is outside the declared route budget"
        )

    walk_counts = _bounded_walk_counts(
        spec.prefix[-1], spec.target, graph, remaining
    )
    counts_by_total_hops = {
        str(prefix_hops + length): count * prefix_alternatives
        for length, count in walk_counts.items()
        if count
    }
    expanded_witnesses = []
    compact_witnesses = []
    for suffix in suffix_witnesses:
        arcs = prefix_arcs + suffix
        nodes = list(spec.prefix) + [arc["target"] for arc in suffix]
        expanded = _analyze_path(nodes, arcs)
        expanded_witnesses.append(expanded)
        compact_witnesses.append(
            {
                "nodes": expanded["nodes"],
                "edge_ids": [edge["edge_id"] for edge in expanded["edges"]],
                "hops": expanded["hops"],
                "standing": expanded["standing"],
                "path_signature": expanded["path_signature"],
            }
        )

    body = {
        "route_id": spec.route_id,
        "task_mode": "INDEPENDENT_SOLO_SIMULATION",
        "input": asdict(spec),
        "graph": {
            "reading": spec.graph_reading,
            "typed_relation_count": len(relations),
            "graph_digest": _digest(relations),
        },
        "prefix": {
            "nodes": list(spec.prefix),
            "typed_alternative_count": prefix_alternatives,
            "valid": True,
        },
        "shortest_language": {
            "suffix_hops": suffix_distance,
            "total_hops": prefix_hops + suffix_distance,
            "typed_path_count": prefix_alternatives * suffix_count,
            "witnesses_emitted": len(compact_witnesses),
            "witness_limit": spec.witness_limit,
        },
        "bounded_path_universe": {
            "semantics": "EVERY_TYPED_WALK_AFTER_THE_FIXED_PREFIX_UP_TO_ROUTE_BUDGET",
            "includes_cycles": True,
            "finite_because": "route_budget",
            "target_path_count_by_total_hops": counts_by_total_hops,
            "target_path_count_total": sum(counts_by_total_hops.values()),
        },
        "canonical_path": expanded_witnesses[0],
        "shortest_path_witnesses": compact_witnesses,
        "truth_effect": "NONE",
    }
    return {**body, "simulation_digest": _digest(body)}


def _pairwise_holonomy(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    report = []
    for left, right in combinations(results, 2):
        left_path = left["canonical_path"]
        right_path = right["canonical_path"]
        left_edges = {row["edge_id"] for row in left_path["edges"]}
        right_edges = {row["edge_id"] for row in right_path["edges"]}
        left_nodes = set(left_path["nodes"])
        right_nodes = set(right_path["nodes"])
        edge_omega = len(left_edges ^ right_edges)
        node_omega = len(left_nodes ^ right_nodes)
        report.append(
            {
                "left": left["route_id"],
                "right": right["route_id"],
                "shared_target": left_path["nodes"][-1]
                == right_path["nodes"][-1],
                "edge_holonomy": edge_omega,
                "node_holonomy": node_omega,
                "omega": edge_omega + node_omega,
                "shared_edges": len(left_edges & right_edges),
                "shared_nodes": len(left_nodes & right_nodes),
            }
        )
    return report


def _claim_overlap(left: str, right: str) -> bool:
    left = left.rstrip("/")
    right = right.rstrip("/")
    return left == right or left.startswith(right + "/") or right.startswith(left + "/")


def _tasks_conflict(left: AgentTask, right: AgentTask) -> bool:
    return any(
        _claim_overlap(write, claim)
        for write in left.write_set
        for claim in right.read_set + right.write_set
    ) or any(
        _claim_overlap(write, claim)
        for write in right.write_set
        for claim in left.read_set + left.write_set
    )


def compile_execution_waves(
    tasks: Iterable[AgentTask], *, worker_capacity: int = 5
) -> list[list[str]]:
    if worker_capacity < 1:
        raise ParallelRouteError("worker_capacity must be positive")
    task_rows = tuple(tasks)
    by_id = {task.task_id: task for task in task_rows}
    if len(by_id) != len(task_rows):
        raise ParallelRouteError("duplicate task ID")
    for task in task_rows:
        missing = set(task.depends_on) - set(by_id)
        if missing:
            raise ParallelRouteError(
                f"{task.task_id}: missing dependencies {sorted(missing)}"
            )

    completed: set[str] = set()
    pending = set(by_id)
    waves: list[list[str]] = []
    while pending:
        ready = sorted(
            (
                task
                for task_id, task in by_id.items()
                if task_id in pending and set(task.depends_on) <= completed
            ),
            key=lambda task: (task.priority, task.task_id),
        )
        if not ready:
            raise ParallelRouteError("task dependency graph contains a cycle")

        selected: list[AgentTask] = []
        for task in ready:
            exclusive = task.execution_mode in {
                "SOLO_WORKER",
                "COORDINATOR_ONLY",
                "DETERMINISTIC_REDUCER",
            }
            if not selected and exclusive:
                selected = [task]
                break
            if exclusive:
                break
            if len(selected) == worker_capacity:
                break
            if any(_tasks_conflict(task, prior) for prior in selected):
                continue
            selected.append(task)
        if not selected:
            selected = [ready[0]]
        wave = [task.task_id for task in selected]
        waves.append(wave)
        pending -= set(wave)
        completed |= set(wave)
    return waves


def scheduler_plan(
    simulations: Iterable[RouteSimulation] = DEFAULT_SIMULATIONS,
) -> dict[str, Any]:
    routes = sorted(simulations, key=lambda item: item.route_id)
    task_models = [
        AgentTask(
            task_id=f"SIMULATE::{spec.route_id}",
            execution_mode="PARALLEL_WORKER",
            read_set=("KC144_FROZEN_ATLAS", f"GRAPH::{spec.graph_reading}"),
            write_set=(f"RESULT::{spec.route_id}",),
        )
        for spec in routes
    ]
    integrate_model = AgentTask(
        task_id="INTEGRATE::PARALLEL_ROUTE_CRYSTAL",
        execution_mode="DETERMINISTIC_REDUCER",
        depends_on=tuple(task.task_id for task in task_models),
        read_set=tuple(task.write_set[0] for task in task_models),
        write_set=("RESULT::PARALLEL_ROUTE_CRYSTAL",),
    )
    models = task_models + [integrate_model]
    task_rows = [
        {
            **asdict(task),
            "depends_on": list(task.depends_on),
            "read_set": list(task.read_set),
            "write_set": list(task.write_set),
            "merge_authority": task.execution_mode == "DETERMINISTIC_REDUCER",
            "work_id": _digest(asdict(task)),
        }
        for task in models
    ]
    body = {
        "schema": "KC144.ParallelAgentPlan.V1",
        "capacity_requested": len(routes),
        "maximum_parallel_width": len(routes),
        "tasks": task_rows,
        "execution_waves": compile_execution_waves(models, worker_capacity=len(routes)),
        "dispatch_order": "DEPENDENCY_RANK_THEN_TASK_ID",
        "merge_order": [task.task_id for task in task_models]
        + [integrate_model.task_id],
        "spawn_fallback": (
            "WHEN_AGENT_SLOTS_ARE_UNAVAILABLE_RUN_THE_SAME_TASK_ENVELOPES_"
            "SEQUENTIALLY_IN_CANONICAL_ORDER"
        ),
        "laws": [
            "workers produce isolated results; only the reducer merges",
            "arrival order never changes merge order",
            "parallel and sequential execution produce identical canonical output",
            "write-set overlap is forbidden inside a parallel wave",
            "independent-agent requirements may not be simulated locally",
        ],
    }
    return {**body, "plan_digest": _digest(body)}


def compile_parallel_route_crystal(
    simulations: Iterable[RouteSimulation] = DEFAULT_SIMULATIONS,
    *,
    executor_workers: int = 5,
    coordinate_binding: dict[str, str] | None = None,
) -> dict[str, Any]:
    specs = tuple(sorted(simulations, key=lambda item: item.route_id))
    if not specs:
        raise ParallelRouteError("at least one route simulation is required")
    if executor_workers < 1:
        raise ParallelRouteError("executor_workers must be positive")
    if len({spec.route_id for spec in specs}) != len(specs):
        raise ParallelRouteError("route IDs must be unique")

    with ThreadPoolExecutor(max_workers=min(executor_workers, len(specs))) as pool:
        futures = {spec.route_id: pool.submit(simulate_route, spec) for spec in specs}
        results = [futures[route_id].result() for route_id in sorted(futures)]

    pairwise = _pairwise_holonomy(results)
    plan = scheduler_plan(specs)
    binding = coordinate_binding or {"standing": "UNBOUND_LOCAL_REPLAY"}
    if coordinate_binding is not None:
        required = {
            "immutable_commit",
            "immutable_tree",
            "compiler_commit",
            "compiler_tree",
        }
        if set(coordinate_binding) != required:
            raise ParallelRouteError(
                f"coordinate_binding must contain exactly {sorted(required)}"
            )
        if any(
            len(value) != 40 or any(character not in "0123456789abcdef" for character in value)
            for value in coordinate_binding.values()
        ):
            raise ParallelRouteError("coordinate binding values must be lowercase Git SHAs")
    body = {
        "schema": "KC144.ParallelRouteCrystal.V1",
        "lookup_key": "KC144.V1::PARALLEL_ROUTE_CRYSTAL",
        "mode": "FIVE_SIMULATIONS_THEN_DETERMINISTIC_REDUCTION",
        "coordinate_binding": binding,
        "scheduler": plan,
        "simulations": results,
        "simultaneous_projection_matrix": [
            {
                "route_id": result["route_id"],
                "source": result["canonical_path"]["nodes"][0],
                "target": result["canonical_path"]["nodes"][-1],
                "changed_lenses": result["canonical_path"][
                    "net_coordinate_delta"
                ]["changed_lenses"],
                "preserved_lenses": result["canonical_path"][
                    "net_coordinate_delta"
                ]["preserved_lenses"],
                "bounded_target_paths": result["bounded_path_universe"][
                    "target_path_count_total"
                ],
                "standing": result["canonical_path"]["standing"],
            }
            for result in results
        ],
        "pairwise_holonomy": pairwise,
        "all_routes_navigation_valid": all(
            result["canonical_path"]["navigation_valid"] for result in results
        ),
        "all_pairwise_holonomy_nonzero": all(
            row["omega"] > 0 for row in pairwise
        ),
        "content_transport_certified": False,
        "governance_authority_granted": False,
        "production_truth_effect": "NONE",
        "interpretation": [
            "all bounded typed paths are counted; representative shortest paths are expanded",
            "each GID is projected through native, grid, DLS, K4, BR21, KC27, KC54, C144, 360-degree, great-year, prime, D4, and liminal coordinates",
            "added and removed coordinate states describe observer-frame change, not deletion of source identity",
            "path equivalence requires more than a common endpoint; edge and node holonomy remain explicit",
            "structural navigation and declared bridges never imply certified transport or truth",
        ],
    }
    return {**body, "crystal_digest": _digest(body)}
