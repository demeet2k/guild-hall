from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from .lattice import BAND_COUNTS
from .navigation import (
    RETURN_ARM,
    adjacency,
    distances,
    navigation_relations,
    shortest_path,
)
from .population import crystallize, digest
from .station import build_station_bodies

EVIDENCE_FLOORS = (
    "STRUCTURAL",
    "SOURCE_DECLARED",
    "INDEPENDENT_REPLAY",
    "PROMOTABLE",
)
RETURN_MODES = ("NONE", "RETRACE", "TYPED_RETRACE", "RETURN_ARM")

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "through",
    "to",
    "what",
    "which",
    "with",
}


@dataclass(frozen=True)
class QueryBundle:
    query_id: str
    goal: str
    terms: tuple[str, ...] = ()
    domains: tuple[str, ...] = ()
    operators: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()
    boundaries: tuple[str, ...] = ()
    evidence_floor: str = "STRUCTURAL"
    start_coordinates: tuple[int, ...] = (6,)
    route_budget: int = 18
    return_mode: str = "RETURN_ARM"
    max_results: int = 12

    def __post_init__(self) -> None:
        if not self.query_id.strip() or not self.goal.strip():
            raise ValueError("query_id and goal are required")
        unknown_domains = set(self.domains) - set(BAND_COUNTS)
        if unknown_domains:
            raise ValueError(f"unknown domains: {sorted(unknown_domains)}")
        if self.evidence_floor not in EVIDENCE_FLOORS:
            raise ValueError(f"evidence_floor must be one of {EVIDENCE_FLOORS}")
        if self.return_mode not in RETURN_MODES:
            raise ValueError(f"return_mode must be one of {RETURN_MODES}")
        if not self.start_coordinates or any(
            not 1 <= gid <= 144 for gid in self.start_coordinates
        ):
            raise ValueError("start_coordinates must contain GIDs 1..144")
        if not 0 <= self.route_budget <= 144:
            raise ValueError("route_budget must be 0..144")
        if not 1 <= self.max_results <= 144:
            raise ValueError("max_results must be 1..144")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "QueryBundle":
        tuple_fields = {
            "terms",
            "domains",
            "operators",
            "invariants",
            "boundaries",
            "start_coordinates",
        }
        data = dict(value)
        for field in tuple_fields:
            if field in data:
                data[field] = tuple(data[field])
        return cls(**data)


def query_contract() -> dict[str, Any]:
    return {
        "schema": "KC144.QueryContract.V4",
        "notation": (
            "Q=<query_id,goal,terms,domains,operators,invariants,boundaries,"
            "evidence_floor,start_coordinates,route_budget,return_mode>"
        ),
        "evidence_floors": list(EVIDENCE_FLOORS),
        "return_modes": list(RETURN_MODES),
        "laws": [
            "query ranking does not mutate truth or evidence",
            "evidence floors filter; they never promote",
            "semantic resonance and graph distance remain separate rank dimensions",
            "a declared bridge exposes a certification obligation",
            "a structural retrace is not automatically a semantic inverse",
        ],
    }


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if token not in _STOPWORDS
    }


def _phrase_hit(phrase: str, tokens: set[str]) -> bool:
    phrase_tokens = _tokens(phrase)
    return bool(phrase_tokens) and phrase_tokens <= tokens


def _evidence_allowed(
    body: Mapping[str, Any],
    floor: str,
    overlay: Mapping[int, Mapping[str, Any]],
) -> bool:
    if floor == "STRUCTURAL":
        return True
    if floor == "SOURCE_DECLARED":
        return body["domain_state"] == "SOURCE_DECLARED"
    state = overlay.get(int(body["gid"]), {})
    if floor == "INDEPENDENT_REPLAY":
        return bool(state.get("independent_replay"))
    return bool(state.get("promotable"))


def _relation_index(
    relations: tuple[dict[str, Any], ...],
) -> dict[tuple[int, int], tuple[dict[str, Any], ...]]:
    index: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for relation in relations:
        pair = tuple(sorted((relation["source"], relation["target"])))
        index.setdefault(pair, []).append(relation)
    return {
        pair: tuple(
            sorted(
                rows,
                key=lambda row: (
                    row["standing"] != "STRUCTURAL",
                    row["relation"],
                    row.get("bridge_id", ""),
                ),
            )
        )
        for pair, rows in index.items()
    }


def _compile_segments(
    path: list[int],
    relation_index: Mapping[tuple[int, int], tuple[dict[str, Any], ...]],
) -> tuple[list[dict[str, Any]], list[str]]:
    segments: list[dict[str, Any]] = []
    bridge_ids: list[str] = []
    for source, target in zip(path, path[1:]):
        choices = relation_index[tuple(sorted((source, target)))]
        selected = choices[0]
        segment = {
            "source": source,
            "target": target,
            "selected_relation": selected["relation"],
            "selected_standing": selected["standing"],
            "available_relations": [
                {
                    "relation": row["relation"],
                    "standing": row["standing"],
                    **(
                        {"bridge_id": row["bridge_id"]}
                        if "bridge_id" in row
                        else {}
                    ),
                }
                for row in choices
            ],
        }
        if selected["standing"] != "STRUCTURAL":
            bridge_id = selected["bridge_id"]
            segment["bridge_id"] = bridge_id
            bridge_ids.append(bridge_id)
        segments.append(segment)
    return segments, bridge_ids


def _return_plan(
    mode: str,
    forward_path: list[int],
    return_obligation: str,
    graph: dict[int, set[int]],
    relation_index: Mapping[tuple[int, int], tuple[dict[str, Any], ...]],
) -> dict[str, Any]:
    if mode == "NONE":
        return {
            "mode": mode,
            "path": [],
            "segments": [],
            "standing": "NO_RETURN_REQUESTED",
            "open_bridge_ids": [],
        }
    if mode in {"RETRACE", "TYPED_RETRACE"}:
        path = list(reversed(forward_path))
        standing = (
            "STRUCTURAL_RETRACE_NOT_SEMANTIC_INVERSE"
            if mode == "RETRACE"
            else f"TYPED_AS_{return_obligation}_PENDING_TRANSPORT_WITNESS"
        )
    else:
        target = forward_path[-1]
        ingress = shortest_path(target, RETURN_ARM[0], graph)
        path = ingress + list(RETURN_ARM[1:])
        standing = "DECLARED_RETURN_ARM_TO_GID001_PRIME"
    segments, bridge_ids = _compile_segments(path, relation_index)
    return {
        "mode": mode,
        "path": path,
        "segments": segments,
        "standing": standing,
        "open_bridge_ids": sorted(set(bridge_ids)),
    }


def _dominates(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    maximize = (
        "goal_hits",
        "term_hits",
        "operator_hits",
        "invariant_hits",
        "boundary_hits",
    )
    no_worse = all(left[field] >= right[field] for field in maximize) and (
        left["distance"] <= right["distance"]
    )
    strictly_better = any(left[field] > right[field] for field in maximize) or (
        left["distance"] < right["distance"]
    )
    return no_worse and strictly_better


def compile_query(
    query: QueryBundle,
    *,
    evidence_overlay: Mapping[int, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    overlay = evidence_overlay or {}
    crystal = crystallize()
    bodies = build_station_bodies()
    relations = navigation_relations()
    graph = adjacency(relations)
    relation_index = _relation_index(relations)
    source_distances = {
        start: distances(start, graph) for start in sorted(set(query.start_coordinates))
    }
    goal_tokens = _tokens(query.goal)

    candidates: list[dict[str, Any]] = []
    evidence_eligible = 0
    for body in bodies:
        if query.domains and body["band"] not in query.domains:
            continue
        if not _evidence_allowed(body, query.evidence_floor, overlay):
            continue
        evidence_eligible += 1
        gid = body["gid"]
        nearest_start, distance = min(
            (
                (start, source_distances[start][gid])
                for start in source_distances
                if gid in source_distances[start]
            ),
            key=lambda pair: (pair[1], pair[0]),
        )
        if distance > query.route_budget:
            continue

        searchable = " ".join(
            [
                body["station"],
                body["architectural_label"],
                body["structural_role"],
                body["governing_question"],
                body["band_invariant"],
                body["return_obligation"],
                body["evidence_status"],
                body["domain_state"],
                *body["four_pole"].values(),
            ]
        )
        body_tokens = _tokens(searchable)
        incident_relations = {
            row["relation"]
            for row in relations
            if gid in (row["source"], row["target"])
        }
        relation_tokens = _tokens(" ".join(incident_relations))
        invariant_tokens = _tokens(body["band_invariant"])
        boundary_tokens = _tokens(
            " ".join(
                (
                    body["evidence_status"],
                    body["domain_state"],
                    body["return_obligation"],
                    body["band_invariant"],
                )
            )
        )
        vector = {
            "goal_hits": len(goal_tokens & body_tokens),
            "term_hits": sum(_phrase_hit(term, body_tokens) for term in query.terms),
            "operator_hits": sum(
                _phrase_hit(operator, relation_tokens | body_tokens)
                for operator in query.operators
            ),
            "invariant_hits": sum(
                _phrase_hit(invariant, invariant_tokens)
                for invariant in query.invariants
            ),
            "boundary_hits": sum(
                _phrase_hit(boundary, boundary_tokens)
                for boundary in query.boundaries
            ),
            "distance": distance,
        }
        if not any(
            vector[field]
            for field in (
                "goal_hits",
                "term_hits",
                "operator_hits",
                "invariant_hits",
                "boundary_hits",
            )
        ):
            continue
        candidates.append(
            {
                "gid": gid,
                "station": body["station"],
                "band": body["band"],
                "architectural_label": body["architectural_label"],
                "evidence_status": body["evidence_status"],
                "domain_state": body["domain_state"],
                "nearest_start": nearest_start,
                **vector,
            }
        )

    frontier = [
        candidate
        for candidate in candidates
        if not any(
            _dominates(other, candidate)
            for other in candidates
            if other["gid"] != candidate["gid"]
        )
    ]
    frontier.sort(
        key=lambda row: (
            -row["goal_hits"],
            -row["term_hits"],
            -row["operator_hits"],
            -row["invariant_hits"],
            -row["boundary_hits"],
            row["distance"],
            row["gid"],
        )
    )

    selected: list[dict[str, Any]] = []
    bodies_by_gid = {body["gid"]: body for body in bodies}
    for candidate in frontier[: query.max_results]:
        body = bodies_by_gid[candidate["gid"]]
        path = shortest_path(candidate["nearest_start"], candidate["gid"], graph)
        segments, bridge_ids = _compile_segments(path, relation_index)
        return_plan = _return_plan(
            query.return_mode,
            path,
            body["return_obligation"],
            graph,
            relation_index,
        )
        all_open_bridges = sorted(set(bridge_ids) | set(return_plan["open_bridge_ids"]))
        selected.append(
            {
                **candidate,
                "rank_vector": {
                    field: candidate[field]
                    for field in (
                        "goal_hits",
                        "term_hits",
                        "operator_hits",
                        "invariant_hits",
                        "boundary_hits",
                        "distance",
                    )
                },
                "forward_route": {
                    "path": path,
                    "segments": segments,
                    "hops": len(path) - 1,
                },
                "return_plan": return_plan,
                "open_bridge_ids": all_open_bridges,
                "route_standing": (
                    "DECLARED_ROUTE_WITH_OPEN_TRANSPORT_CERTIFICATION"
                    if all_open_bridges
                    else "STRUCTURAL_ROUTE"
                ),
                "promotion_effect": "NONE",
            }
        )

    if selected:
        status = "COMPILED"
        refusal = None
    elif evidence_eligible == 0:
        status = "REFUSED"
        refusal = {
            "code": "EVIDENCE_FLOOR_UNSATISFIED",
            "detail": (
                f"no station currently satisfies {query.evidence_floor}; "
                "the query compiler cannot manufacture that standing"
            ),
        }
    elif candidates:
        status = "REFUSED"
        refusal = {
            "code": "PARETO_FRONTIER_EMPTY",
            "detail": "candidate comparison produced no admissible frontier",
        }
    else:
        status = "REFUSED"
        refusal = {
            "code": "NO_MATCH_WITHIN_ROUTE_BUDGET",
            "detail": "no evidence-eligible semantic match lies within the route budget",
        }

    result = {
        "schema": "KC144.CompiledQuery.V4",
        "status": status,
        "query": query.to_dict(),
        "crystal_digest": crystal["digest"],
        "base_graph_mutated": False,
        "evidence_overlay_mutated": False,
        "evidence_eligible": evidence_eligible,
        "semantic_candidates": len(candidates),
        "pareto_frontier_size": len(frontier),
        "selected": selected,
        "refusal": refusal,
        "ranking_law": (
            "Pareto dominance over disclosed semantic/operator/invariant/boundary "
            "hits and graph distance; no hidden scalar score"
        ),
        "truth_effect": "NONE",
    }
    result["result_digest"] = digest(result)
    return result
