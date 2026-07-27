from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from itertools import combinations
from typing import Any, Mapping

from .edge_manifest import edge_lookup, freeze_edge_manifest
from .lattice import BAND_COUNTS, generate_seats
from .population import crystallize, digest
from .query import QueryBundle, compile_query
from .wave import WaveQuery, propagate


@dataclass(frozen=True)
class SessionSpec:
    session_id: str
    epoch: str
    queries: tuple[QueryBundle, ...]
    execution_mode: str = "DETERMINISTIC_PARALLEL_BATCH"

    def __post_init__(self) -> None:
        if not self.session_id.strip() or not self.epoch.strip():
            raise ValueError("session_id and epoch are required")
        if not self.queries:
            raise ValueError("a session needs at least one QueryBundle")
        if self.execution_mode != "DETERMINISTIC_PARALLEL_BATCH":
            raise ValueError("unsupported execution_mode")

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "epoch": self.epoch,
            "queries": [query.to_dict() for query in self.queries],
            "execution_mode": self.execution_mode,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SessionSpec":
        return cls(
            session_id=str(value["session_id"]),
            epoch=str(value["epoch"]),
            queries=tuple(
                QueryBundle.from_dict(query) for query in value["queries"]
            ),
            execution_mode=str(
                value.get("execution_mode", "DETERMINISTIC_PARALLEL_BATCH")
            ),
        )


def _edge_id(
    lookup: Mapping[tuple[int, int, str], tuple[dict[str, Any], ...]],
    source: int,
    target: int,
    relation: str,
) -> str:
    rows = lookup[(min(source, target), max(source, target), relation)]
    return rows[0]["edge_id"]


def _receipt(
    sequence: int,
    previous: str,
    query: QueryBundle,
    compiled: dict[str, Any],
    wave: dict[str, Any],
    lookup: Mapping[tuple[int, int, str], tuple[dict[str, Any], ...]],
) -> dict[str, Any]:
    explicit_nodes: set[int] = set()
    explicit_edges: list[dict[str, Any]] = []
    branch_ledger: list[dict[str, Any]] = []
    for selected in compiled["selected"]:
        branch_ledger.append(
            {
                "gid": selected["gid"],
                "rank_vector": selected["rank_vector"],
                "route_standing": selected["route_standing"],
                "open_bridge_ids": selected["open_bridge_ids"],
            }
        )
        for route_class, route in (
            ("FORWARD", selected["forward_route"]),
            ("RETURN", selected["return_plan"]),
        ):
            explicit_nodes.update(route["path"])
            for segment in route["segments"]:
                explicit_edges.append(
                    {
                        "edge_id": _edge_id(
                            lookup,
                            segment["source"],
                            segment["target"],
                            segment["selected_relation"],
                        ),
                        "source": segment["source"],
                        "target": segment["target"],
                        "relation": segment["selected_relation"],
                        "route_class": route_class,
                    }
                )
    route_signature = digest(
        {
            "query_id": query.query_id,
            "branches": branch_ledger,
            "explicit_edges": explicit_edges,
            "wave_signatures": [
                {"gid": node["gid"], "path_signature": node["path_signature"]}
                for node in wave["nodes"]
            ],
        }
    )
    payload = {
        "sequence": sequence,
        "previous_receipt_digest": previous,
        "query": query.to_dict(),
        "compiled_result_digest": compiled["result_digest"],
        "status": compiled["status"],
        "explicit_visited_nodes": sorted(explicit_nodes),
        "explicit_edges": explicit_edges,
        "wave_reached_nodes": [node["gid"] for node in wave["nodes"]],
        "neural_relation_overlay": wave["relation_weight_overlay"],
        "route_signature": route_signature,
        "branch_ledger": branch_ledger,
        "unresolved": (
            [compiled["refusal"]] if compiled["refusal"] else []
        )
        + [
            {"code": "OPEN_BRIDGE_CERTIFICATION", "bridge_id": bridge_id}
            for bridge_id in sorted(
                {
                    bridge_id
                    for selected in compiled["selected"]
                    for bridge_id in selected["open_bridge_ids"]
                }
            )
        ],
        "truth_effect": "NONE",
    }
    return {**payload, "receipt_digest": digest(payload)}


def _node_state(receipts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seats = generate_seats()
    rows: list[dict[str, Any]] = []
    for seat in seats:
        explicit_queries = [
            receipt["query"]["query_id"]
            for receipt in receipts
            if seat.gid in receipt["explicit_visited_nodes"]
        ]
        wave_queries = [
            receipt["query"]["query_id"]
            for receipt in receipts
            if seat.gid in receipt["wave_reached_nodes"]
        ]
        selected_queries = [
            receipt["query"]["query_id"]
            for receipt in receipts
            if any(branch["gid"] == seat.gid for branch in receipt["branch_ledger"])
        ]
        rows.append(
            {
                "gid": seat.gid,
                "station": seat.station,
                "band": seat.band,
                "explicit_visit_count": len(explicit_queries),
                "wave_activation_count": len(wave_queries),
                "selected_count": len(selected_queries),
                "explicit_query_ids": explicit_queries,
                "wave_query_ids": wave_queries,
                "selected_query_ids": selected_queries,
                "truth_effect": "NONE",
            }
        )
    return rows


def _edge_state(
    manifest: dict[str, Any],
    receipts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    explicit = Counter(
        edge["edge_id"]
        for receipt in receipts
        for edge in receipt["explicit_edges"]
    )
    neural: Counter[str] = Counter()
    lookup = edge_lookup(manifest)
    for receipt in receipts:
        for row in receipt["neural_relation_overlay"]:
            edge_id = _edge_id(
                lookup, row["source"], row["target"], row["relation"]
            )
            neural[edge_id] += row["weight"]
    return [
        {
            "edge_id": record["edge_id"],
            "source": record["source"],
            "target": record["target"],
            "relation": record["relation"],
            "standing": record["standing"],
            "explicit_traversal_count": explicit[record["edge_id"]],
            "neural_activation_weight": neural[record["edge_id"]],
            "carry": record["carry"],
            "loss": record["loss"],
            "truth_effect": "NONE",
        }
        for record in manifest["records"]
    ]


def _projective_synapses(receipts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected = [
        (receipt["query"]["query_id"], branch["gid"], set(receipt["explicit_visited_nodes"]))
        for receipt in receipts
        for branch in receipt["branch_ledger"]
    ]
    synapses: list[dict[str, Any]] = []
    for (left_query, left_gid, left_path), (
        right_query,
        right_gid,
        right_path,
    ) in combinations(selected, 2):
        if left_gid == right_gid:
            continue
        shared = sorted(left_path & right_path)
        if not shared:
            continue
        body = {
            "source_gid": min(left_gid, right_gid),
            "target_gid": max(left_gid, right_gid),
            "left_query": left_query,
            "right_query": right_query,
            "shared_route_nodes": shared,
            "weight": len(shared),
            "standing": "PROJECTIVE_COACTIVATION_OVERLAY",
            "truth_effect": "NONE",
        }
        synapses.append({**body, "synapse_id": digest(body)})
    synapses.sort(key=lambda row: (row["source_gid"], row["target_gid"], row["synapse_id"]))
    return synapses


def _solid_state(
    node_rows: list[dict[str, Any]],
    edge_rows: list[dict[str, Any]],
    receipts: list[dict[str, Any]],
    *,
    certified_bridges: int,
    independent_replays: int,
    domain_population: int,
    blocking_defects: int,
    ic10_promoted: bool,
) -> dict[str, Any]:
    compiled_receipts = [row for row in receipts if row["status"] == "COMPILED"]
    gates = {
        "M12_NODE_ACTIVATION_144": sum(
            row["wave_activation_count"] > 0 for row in node_rows
        )
        == 144,
        "M12_EDGE_MANIFEST_FROZEN": len(edge_rows) == 276,
        "M12_TOTAL_RETURN": bool(compiled_receipts)
        and all(
            any(edge["route_class"] == "RETURN" for edge in row["explicit_edges"])
            for row in compiled_receipts
        ),
        "M12_PROJECTIVE_COVERAGE": bool(_projective_synapses(receipts)),
        "M12_BRIDGES_CERTIFIED_28": certified_bridges == 28,
        "M12_DOMAIN_POPULATION_144": domain_population == 144,
        "M12_INDEPENDENT_REPLAY_144": independent_replays == 144,
        "M12_IC10_DECISION_PROMOTED": ic10_promoted,
        "M12_BLOCKING_DEFECTS_EMPTY": blocking_defects == 0,
    }
    certified = all(gates.values())
    certificate_body = {
        "schema": "KC144.M12Certificate.V6",
        "gate_vector": {
            name: "PASS" if passed else "FAIL" for name, passed in gates.items()
        },
        "certified_bridges": certified_bridges,
        "domain_population": domain_population,
        "independent_replays": independent_replays,
        "blocking_defects": blocking_defects,
        "ic10_promoted": ic10_promoted,
    }
    return {
        "verdict": "CERTIFIED" if certified else "HOLD",
        "gates": {
            name: "PASS" if passed else "FAIL" for name, passed in gates.items()
        },
        "passed": sum(gates.values()),
        "total": len(gates),
        "certificate": (
            {**certificate_body, "certificate_digest": digest(certificate_body)}
            if certified
            else None
        ),
        "law": (
            "coverage telemetry never substitutes for domain population, independent "
            "replay, certified transport, IC10 promotion, or debt closure"
        ),
    }


def compile_session(
    spec: SessionSpec,
    *,
    evidence_overlay: Mapping[int, Mapping[str, Any]] | None = None,
    certified_bridges: int = 0,
    independent_replays: int = 0,
    domain_population: int = 86,
    blocking_defects: int = 1,
    ic10_promoted: bool = False,
) -> dict[str, Any]:
    manifest = freeze_edge_manifest()
    lookup = edge_lookup(manifest)
    compiled = [
        compile_query(query, evidence_overlay=evidence_overlay) for query in spec.queries
    ]
    waves = [
        propagate(
            WaveQuery(
                query_id=f"{query.query_id}::NEURAL",
                starts=query.start_coordinates,
                route_budget=query.route_budget,
            )
        )
        for query in spec.queries
    ]
    receipts: list[dict[str, Any]] = []
    previous = "GENESIS"
    for sequence, (query, query_result, wave) in enumerate(
        zip(spec.queries, compiled, waves), start=1
    ):
        receipt = _receipt(sequence, previous, query, query_result, wave, lookup)
        receipts.append(receipt)
        previous = receipt["receipt_digest"]

    node_rows = _node_state(receipts)
    edge_rows = _edge_state(manifest, receipts)
    synapses = _projective_synapses(receipts)
    explicit_nodes = {
        gid for receipt in receipts for gid in receipt["explicit_visited_nodes"]
    }
    activated_nodes = {
        gid for receipt in receipts for gid in receipt["wave_reached_nodes"]
    }
    explicit_edges = {
        edge["edge_id"] for receipt in receipts for edge in receipt["explicit_edges"]
    }
    neural_edges = {
        row["edge_id"] for row in edge_rows if row["neural_activation_weight"] > 0
    }
    band_rows = []
    for band, total in BAND_COUNTS.items():
        gids = {row["gid"] for row in node_rows if row["band"] == band}
        band_rows.append(
            {
                "band": band,
                "seats": total,
                "explicit": len(gids & explicit_nodes),
                "activated": len(gids & activated_nodes),
            }
        )
    thought_matrix = [
        {
            "query_id": receipt["query"]["query_id"],
            "status": receipt["status"],
            "bands": dict(
                Counter(
                    next(seat.band for seat in generate_seats() if seat.gid == gid)
                    for gid in receipt["explicit_visited_nodes"]
                )
            ),
        }
        for receipt in receipts
    ]
    solid = _solid_state(
        node_rows,
        edge_rows,
        receipts,
        certified_bridges=certified_bridges,
        independent_replays=independent_replays,
        domain_population=domain_population,
        blocking_defects=blocking_defects,
        ic10_promoted=ic10_promoted,
    )
    observatory = {
        "M01_NODE_STATE_LEDGER": node_rows,
        "M02_EDGE_STATE_LEDGER": edge_rows,
        "M03_PARALLEL_WAVE_ENGINE": {
            "queries": len(waves),
            "mode": "ALL_BOUNDED_SHORTEST_PATHS_AS_NEURONS",
            "base_graph_mutated": False,
        },
        "M04_IN_BETWEEN_REGION_LEDGER": {
            "explicit_untraversed_edges": len(edge_rows) - len(explicit_edges),
            "neural_unactivated_edges": len(edge_rows) - len(neural_edges),
            "open_bridge_ids": sorted(
                {
                    unresolved["bridge_id"]
                    for receipt in receipts
                    for unresolved in receipt["unresolved"]
                    if unresolved["code"] == "OPEN_BRIDGE_CERTIFICATION"
                }
            ),
        },
        "M05_HYBRID_DENSITY_MAP": band_rows,
        "M06_THOUGHT_PATTERN_MATRIX": thought_matrix,
        "M07_COMMITMENT_BOUNDARY": {
            "truth_mutations": 0,
            "evidence_mutations": 0,
            "production_bridge_commits": certified_bridges,
        },
        "M08_HEALING_AND_GAP_LEDGER": {
            "refused_queries": [
                receipt["query"]["query_id"]
                for receipt in receipts
                if receipt["status"] == "REFUSED"
            ],
            "blocking_defects": blocking_defects,
        },
        "M09_PATH_SIGNATURE_REGISTRY": [
            {
                "query_id": receipt["query"]["query_id"],
                "route_signature": receipt["route_signature"],
                "receipt_digest": receipt["receipt_digest"],
            }
            for receipt in receipts
        ],
        "M10_PROJECTIVE_SYNAPSE_MAP": synapses,
        "M11_ROUTE_COVERAGE_AUDIT": {
            "explicit_node_coverage": f"{len(explicit_nodes)}/144",
            "wave_node_coverage": f"{len(activated_nodes)}/144",
            "explicit_edge_record_coverage": f"{len(explicit_edges)}/{len(edge_rows)}",
            "neural_edge_record_coverage": f"{len(neural_edges)}/{len(edge_rows)}",
            "returnable_compiled_queries": sum(
                row["status"] == "COMPILED"
                and any(edge["route_class"] == "RETURN" for edge in row["explicit_edges"])
                for row in receipts
            ),
            "compiled_queries": sum(row["status"] == "COMPILED" for row in receipts),
        },
        "M12_SOLID_STATE": solid,
    }
    session_body = {
        "schema": "KC144.TraversalSession.V5",
        "spec": spec.to_dict(),
        "crystal_digest": crystallize()["digest"],
        "edge_manifest_digest": manifest["manifest_digest"],
        "receipts": receipts,
        "receipt_root": previous,
        "observatory": observatory,
        "truth_effect": "NONE",
    }
    session = {**session_body, "session_digest": digest(session_body)}
    seed_body = {
        "schema": "KC144.ReentrySeed.V5",
        "session_id": spec.session_id,
        "epoch": spec.epoch,
        "queries": [query.to_dict() for query in spec.queries],
        "execution_mode": spec.execution_mode,
        "edge_manifest_digest": manifest["manifest_digest"],
        "expected_receipt_root": session["receipt_root"],
        "expected_session_digest": session["session_digest"],
    }
    session["reentry_seed"] = {**seed_body, "seed_digest": digest(seed_body)}
    return session


def cold_reconstruct(seed: Mapping[str, Any]) -> dict[str, Any]:
    spec = SessionSpec.from_dict(
        {
            "session_id": seed["session_id"],
            "epoch": seed["epoch"],
            "queries": seed["queries"],
            "execution_mode": seed["execution_mode"],
        }
    )
    replay = compile_session(spec)
    checks = {
        "edge_manifest_exact": replay["edge_manifest_digest"]
        == seed["edge_manifest_digest"],
        "receipt_root_exact": replay["receipt_root"] == seed["expected_receipt_root"],
        "session_digest_exact": replay["session_digest"]
        == seed["expected_session_digest"],
    }
    return {
        "schema": "KC144.ColdReconstruction.V5",
        "verdict": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "replay_level": (
            "N5_DETERMINISTIC_SELF_REPLAY"
            if all(checks.values())
            else "BELOW_N5"
        ),
        "independent_replay": False,
        "promotion_effect": "NONE",
        "replayed_receipt_root": replay["receipt_root"],
        "replayed_session_digest": replay["session_digest"],
    }
