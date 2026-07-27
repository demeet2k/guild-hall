from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable

from .agent_receipts import LOOKUP_KEY, content_address
from .lattice import generate_seats
from .navigation import adjacency, navigation_relations, shortest_path


_ALIASES = (
    "agent receipts",
    "content addressed agent run",
    "deterministic parallel receipts",
    "parallel audit chain",
    "run receipt verifier",
)

_BINDINGS = (
    (
        3,
        "LOCATE",
        "stable lookup key and typed tool-route registry",
    ),
    (
        5,
        "BIND_SOURCE",
        "source snapshot, compiler commit/tree, schema version, and content digests",
    ),
    (
        6,
        "ACTIVATE_REPLAY_RESEED",
        "open the run, invoke it, replay it, or emit its successor",
    ),
    (
        135,
        "EXECUTE_WAVES",
        "dependency-aware maximum-width deterministic scheduler",
    ),
    (
        141,
        "INDEX_RECEIPTS",
        "run, path, lease, receipt, and audit-root registry",
    ),
    (
        144,
        "VERIFY_AND_RETURN",
        "conjunctive run verification, HOLD on defect, then successor reentry",
    ),
)


def _normalize_alias(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).lower()
    normalized = re.sub(r"[_\-\s]+", " ", normalized).strip()
    return normalized


def agent_run_receipt_tool_descriptor() -> dict[str, Any]:
    seats = {seat.gid: seat for seat in generate_seats()}
    bindings = [
        {
            "gid": gid,
            "station": seats[gid].station,
            "grid": seats[gid].grid,
            "band": seats[gid].band,
            "role": role,
            "meaning": meaning,
        }
        for gid, role, meaning in _BINDINGS
    ]
    body = {
        "schema": "KC144.MyceliumToolDescriptor.V1",
        "lookup_key": LOOKUP_KEY,
        "parent_lookup_key": "KC144.V1::PARALLEL_ROUTE_CRYSTAL",
        "aliases": list(_ALIASES),
        "capabilities": [
            "CONTENT_ADDRESS_TASKS",
            "COMPILE_DEPENDENCY_WAVES",
            "LEASE_WORK",
            "RECEIVE_ISOLATED_RESULTS",
            "DETERMINISTIC_REDUCE",
            "SEAL_AUDIT_CHAIN",
            "VERIFY_RUN_REPLAY",
        ],
        "coordinate_bindings": bindings,
        "commands": {
            "locate": [
                "kc144-crystal",
                "mycelium-locate",
                LOOKUP_KEY,
            ],
            "plan": [
                "kc144-crystal",
                "agent-run-plan",
                "{parallel_route_snapshot}",
            ],
            "run": [
                "kc144-crystal",
                "agent-run-receipts",
                "{parallel_route_snapshot}",
                "--workers",
                "5",
            ],
            "verify": [
                "kc144-crystal",
                "agent-run-verify",
                "{run_receipt_bundle}",
                "--source",
                "{parallel_route_snapshot}",
            ],
        },
        "input_schemas": [
            "KC144.ParallelRouteCrystal.V1",
            "KC144.AgentRunPlan.V1",
        ],
        "output_schemas": [
            "KC144.AgentRunReceipt.V1",
            "KC144.AgentRunManifest.V1",
            "KC144.AgentRunReceiptBundle.V1",
        ],
        "base_graph_mutated": False,
        "content_transport_certified": False,
        "governance_authority_granted": False,
        "production_truth_effect": "NONE",
    }
    return {
        **body,
        "descriptor_digest": content_address(
            "kc144.mycelium.tool-descriptor", body
        ),
    }


def mycelium_tool_registry() -> dict[str, Any]:
    descriptor = agent_run_receipt_tool_descriptor()
    alias_index = {
        _normalize_alias(alias): LOOKUP_KEY for alias in descriptor["aliases"]
    }
    body = {
        "schema": "KC144.MyceliumToolRegistry.V1",
        "keyspace": "EXACT_LOOKUP_KEY",
        "descriptors": {LOOKUP_KEY: descriptor},
        "alias_index": alias_index,
        "base_graph_mutated": False,
        "content_transport_certified": False,
        "governance_authority_granted": False,
        "truth_effect": "NONE",
    }
    return {
        **body,
        "registry_digest": content_address(
            "kc144.mycelium.tool-registry", body
        ),
    }


def _relation_for_segment(
    source: int,
    target: int,
    relations: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    options = [
        row
        for row in relations
        if {row["source"], row["target"]} == {source, target}
    ]
    if not options:
        raise ValueError(f"route segment {source}->{target} has no relation")
    row = sorted(
        options,
        key=lambda item: (
            item["standing"] != "STRUCTURAL",
            item["relation"],
            item.get("bridge_id", ""),
        ),
    )[0]
    return {
        "source": source,
        "target": target,
        "relation": row["relation"],
        "standing": row["standing"],
        "bridge_id": row.get("bridge_id"),
    }


def _coordinate_route(
    start: int,
    binding: dict[str, Any],
    *,
    route_budget: int,
    relations: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    path = shortest_path(start, binding["gid"], adjacency(relations))
    if not path or len(path) - 1 > route_budget:
        return {
            **binding,
            "path": [],
            "hops": None,
            "segments": [],
            "open_bridge_ids": [],
            "standing": "OUTSIDE_ROUTE_BUDGET",
        }
    segments = [
        _relation_for_segment(left, right, relations)
        for left, right in zip(path, path[1:])
    ]
    bridges = sorted(
        {
            segment["bridge_id"]
            for segment in segments
            if segment["bridge_id"] is not None
            and segment["standing"] != "STRUCTURAL"
        }
    )
    return {
        **binding,
        "path": path,
        "hops": len(path) - 1,
        "segments": segments,
        "open_bridge_ids": bridges,
        "standing": (
            "DECLARED_ROUTE_WITH_OPEN_TRANSPORT_CERTIFICATION"
            if bridges
            else "STRUCTURAL_ROUTE"
        ),
    }


def locate_mycelium_tool(
    query: str,
    *,
    start_coordinates: tuple[int, ...] = (6,),
    route_budget: int = 18,
) -> dict[str, Any]:
    if not query:
        raise ValueError("query is required")
    if not start_coordinates or any(
        not 1 <= gid <= 144 for gid in start_coordinates
    ):
        raise ValueError("start coordinates must be KC144 GIDs")
    if route_budget < 0:
        raise ValueError("route_budget cannot be negative")
    registry = mycelium_tool_registry()
    if query in registry["descriptors"]:
        resolved = query
        resolution = "EXACT_LOOKUP_KEY"
    else:
        resolved = registry["alias_index"].get(_normalize_alias(query))
        resolution = "EXACT_ALIAS" if resolved else "NONE"
    if resolved is None:
        body = {
            "schema": "KC144.MyceliumToolLocation.V1",
            "query": query,
            "resolved_lookup_key": None,
            "status": "NOT_FOUND",
            "resolution": resolution,
            "start_coordinates": list(start_coordinates),
            "route_budget": route_budget,
            "coordinate_routes": [],
            "commands": {},
            "base_graph_mutated": False,
            "content_transport_certified": False,
            "governance_authority_granted": False,
            "production_truth_effect": "NONE",
        }
        return {
            **body,
            "location_digest": content_address(
                "kc144.mycelium.tool-location", body
            ),
        }

    descriptor = registry["descriptors"][resolved]
    relations = navigation_relations("both")
    routes = [
        {
            "start_gid": start,
            **_coordinate_route(
                start,
                binding,
                route_budget=route_budget,
                relations=relations,
            ),
        }
        for start in sorted(set(start_coordinates))
        for binding in descriptor["coordinate_bindings"]
    ]
    body = {
        "schema": "KC144.MyceliumToolLocation.V1",
        "query": query,
        "resolved_lookup_key": resolved,
        "status": "FOUND",
        "resolution": resolution,
        "descriptor_digest": descriptor["descriptor_digest"],
        "start_coordinates": sorted(set(start_coordinates)),
        "route_budget": route_budget,
        "coordinate_routes": routes,
        "commands": descriptor["commands"],
        "base_graph_mutated": False,
        "content_transport_certified": False,
        "governance_authority_granted": False,
        "production_truth_effect": "NONE",
    }
    return {
        **body,
        "location_digest": content_address(
            "kc144.mycelium.tool-location", body
        ),
    }
