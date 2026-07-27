from __future__ import annotations

from collections import Counter
from typing import Any

from .navigation import navigation_relations
from .population import digest


def _carry_and_loss(relation: dict[str, Any]) -> tuple[list[str], list[str]]:
    if relation["standing"] == "STRUCTURAL":
        return (
            ["ADDRESS_ADJACENCY", "RELATION_TYPE", "RELATION_SEMANTICS"],
            ["TRUTH", "EVIDENCE", "AUTHORITY"],
        )
    return (
        ["DECLARED_GRAPH_REACHABILITY", "RELATION_TYPE", "DECLARATION_TEXT"],
        ["TRANSPORT_CERTIFICATION", "TRUTH", "EVIDENCE", "AUTHORITY"],
    )


def freeze_edge_manifest() -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for relation in navigation_relations():
        carry, loss = _carry_and_loss(relation)
        identity = {
            "source": relation["source"],
            "target": relation["target"],
            "relation": relation["relation"],
            "standing": relation["standing"],
            "bridge_id": relation.get("bridge_id"),
        }
        records.append(
            {
                "edge_id": "EDGE-" + digest(identity).split(":", 1)[1][:20],
                **relation,
                "carry": carry,
                "loss": loss,
                "graph_view": "UNDIRECTED_TRAVERSAL",
                "semantic_direction": (
                    "DECLARATION_SOURCE_TO_TARGET"
                    if "bridge_id" in relation
                    else "SYMMETRIC_STRUCTURAL_VIEW"
                ),
                "truth_effect": "NONE",
            }
        )
    records.sort(
        key=lambda row: (
            row["source"],
            row["target"],
            row["relation"],
            row.get("bridge_id", ""),
        )
    )
    distinct_pairs = {
        tuple(sorted((record["source"], record["target"]))) for record in records
    }
    manifest = {
        "schema": "KC144.FrozenEdgeManifest.V5",
        "status": "FROZEN",
        "node_count": 144,
        "relation_record_count": len(records),
        "distinct_adjacency_count": len(distinct_pairs),
        "standing_census": dict(Counter(record["standing"] for record in records)),
        "all_edges_declare_carry": all(record["carry"] for record in records),
        "all_edges_declare_loss": all(record["loss"] for record in records),
        "records": records,
    }
    manifest["manifest_digest"] = digest(manifest)
    return manifest


def edge_lookup(
    manifest: dict[str, Any],
) -> dict[tuple[int, int, str], tuple[dict[str, Any], ...]]:
    index: dict[tuple[int, int, str], list[dict[str, Any]]] = {}
    for record in manifest["records"]:
        key = (
            min(record["source"], record["target"]),
            max(record["source"], record["target"]),
            record["relation"],
        )
        index.setdefault(key, []).append(record)
    return {key: tuple(value) for key, value in index.items()}
