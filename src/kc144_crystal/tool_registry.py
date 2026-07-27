from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable

from .agent_receipts import (
    LOOKUP_KEY as AGENT_RECEIPT_LOOKUP_KEY,
    PARENT_LOOKUP_KEY as PARALLEL_ROUTE_LOOKUP_KEY,
    content_address,
)
from .lattice import generate_seats
from .navigation import adjacency, navigation_relations, shortest_path


DISPATCH_LOOKUP_KEY = "KC144.V1::MYCELIUM_LOCATABLE_TOOL_DISPATCH"
P31_LIVE_LOOKUP_KEY = "KC144.P31::LIVE_COGNITION_NAVIGATE"

_AGENT_RECEIPT_ALIASES = (
    "agent receipts",
    "content addressed agent run",
    "deterministic parallel receipts",
    "parallel audit chain",
    "run receipt verifier",
)

_DISPATCH_BINDINGS = (
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

_PARALLEL_ROUTE_ALIASES = (
    "parallel route crystal",
    "five route simulations",
    "kc144 route crystal",
)

_DISPATCH_ALIASES = (
    "mycelium tool dispatch",
    "dynamic tool dispatch",
    "locate and execute tool",
    "content addressed dispatch",
)

_P31_LIVE_ALIASES = (
    "p31 live navigate",
    "live cognition navigate",
    "tool kc144 live navigate",
)


def _normalize_alias(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).lower()
    normalized = re.sub(r"[_\-\s]+", " ", normalized).strip()
    return normalized


def _bindings() -> list[dict[str, Any]]:
    seats = {seat.gid: seat for seat in generate_seats()}
    return [
        {
            "gid": gid,
            "station": seats[gid].station,
            "grid": seats[gid].grid,
            "band": seats[gid].band,
            "role": role,
            "meaning": meaning,
        }
        for gid, role, meaning in _DISPATCH_BINDINGS
    ]


def _seal_descriptor(body: dict[str, Any]) -> dict[str, Any]:
    return {
        **body,
        "descriptor_digest": content_address(
            "kc144.mycelium.tool-descriptor", body
        ),
    }


def agent_run_receipt_tool_descriptor() -> dict[str, Any]:
    body = {
        "schema": "KC144.MyceliumToolDescriptor.V1",
        "lookup_key": AGENT_RECEIPT_LOOKUP_KEY,
        "tool_uri": "tool://kc144/agent-run-receipts",
        "parent_lookup_key": PARALLEL_ROUTE_LOOKUP_KEY,
        "aliases": list(_AGENT_RECEIPT_ALIASES),
        "capabilities": [
            "CONTENT_ADDRESS_TASKS",
            "COMPILE_DEPENDENCY_WAVES",
            "LEASE_WORK",
            "RECEIVE_ISOLATED_RESULTS",
            "DETERMINISTIC_REDUCE",
            "SEAL_AUDIT_CHAIN",
            "VERIFY_RUN_REPLAY",
        ],
        "coordinate_bindings": _bindings(),
        "execution_binding": "IN_PROCESS_ONLY",
        "handler_id": "kc144.agent-receipts.v1",
        "operations": {
            "plan": {
                "required_inputs": ["parallel_route_snapshot"],
                "required_capabilities": ["CONTENT_ADDRESS_TASKS"],
            },
            "run": {
                "required_inputs": ["parallel_route_snapshot"],
                "optional_inputs": ["runtime_binding"],
                "required_capabilities": [
                    "COMPILE_DEPENDENCY_WAVES",
                    "DETERMINISTIC_REDUCE",
                    "SEAL_AUDIT_CHAIN",
                ],
            },
            "verify": {
                "required_inputs": ["run_receipt_bundle"],
                "optional_inputs": ["parallel_route_snapshot"],
                "required_capabilities": ["VERIFY_RUN_REPLAY"],
            },
        },
        "commands": {
            "locate": [
                "kc144-crystal",
                "mycelium-locate",
                AGENT_RECEIPT_LOOKUP_KEY,
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
    return _seal_descriptor(body)


def parallel_route_tool_descriptor() -> dict[str, Any]:
    body = {
        "schema": "KC144.MyceliumToolDescriptor.V1",
        "lookup_key": PARALLEL_ROUTE_LOOKUP_KEY,
        "tool_uri": "tool://kc144/parallel-routes",
        "parent_lookup_key": None,
        "aliases": list(_PARALLEL_ROUTE_ALIASES),
        "capabilities": [
            "COMPILE_FIVE_ROUTE_SIMULATIONS",
            "DETERMINISTIC_REDUCE",
            "MEASURE_PAIRWISE_HOLONOMY",
        ],
        "coordinate_bindings": _bindings(),
        "execution_binding": "IN_PROCESS_ONLY",
        "handler_id": "kc144.parallel-routes.v1",
        "operations": {
            "compile": {
                "required_inputs": [],
                "optional_inputs": ["coordinate_binding"],
                "required_capabilities": [
                    "COMPILE_FIVE_ROUTE_SIMULATIONS",
                    "DETERMINISTIC_REDUCE",
                ],
            }
        },
        "commands": {
            "compile": [
                "kc144-crystal",
                "parallel-routes",
                "--workers",
                "5",
            ]
        },
        "input_schemas": [],
        "output_schemas": ["KC144.ParallelRouteCrystal.V1"],
        "base_graph_mutated": False,
        "content_transport_certified": False,
        "governance_authority_granted": False,
        "production_truth_effect": "NONE",
    }
    return _seal_descriptor(body)


def dispatch_tool_descriptor() -> dict[str, Any]:
    body = {
        "schema": "KC144.MyceliumToolDescriptor.V1",
        "lookup_key": DISPATCH_LOOKUP_KEY,
        "tool_uri": "tool://kc144/tool-dispatch",
        "parent_lookup_key": AGENT_RECEIPT_LOOKUP_KEY,
        "aliases": list(_DISPATCH_ALIASES),
        "capabilities": [
            "RESOLVE_EXACT_TOOL_CARD",
            "BIND_AUTHORITATIVE_HEADS",
            "COMPILE_FAIL_CLOSED_DISPATCH",
            "EXECUTE_REGISTERED_IN_PROCESS_HANDLER",
            "SEAL_KC54_RETURN_RECEIPT",
            "VERIFY_COLD_REPLAY",
        ],
        "coordinate_bindings": _bindings(),
        "execution_binding": "IN_PROCESS_ONLY",
        "handler_id": "kc144.tool-dispatch.v1",
        "operations": {
            "registry": {
                "required_inputs": [],
                "required_capabilities": ["RESOLVE_EXACT_TOOL_CARD"],
            },
            "locate": {
                "required_inputs": ["query"],
                "required_capabilities": ["RESOLVE_EXACT_TOOL_CARD"],
            },
        },
        "commands": {
            "registry": ["kc144-crystal", "mycelium-tools"],
            "locate": [
                "kc144-crystal",
                "mycelium-locate",
                "{query}",
            ],
        },
        "input_schemas": ["KC144.ToolDispatchRequest.V1"],
        "output_schemas": [
            "KC144.ToolDispatchPlan.V1",
            "KC144.ToolDispatchResult.V1",
            "KC144.ToolDispatchVerification.V1",
        ],
        "base_graph_mutated": False,
        "content_transport_certified": False,
        "governance_authority_granted": False,
        "production_truth_effect": "NONE",
    }
    return _seal_descriptor(body)


def p31_live_navigate_tool_descriptor() -> dict[str, Any]:
    body = {
        "schema": "KC144.MyceliumToolDescriptor.V1",
        "lookup_key": P31_LIVE_LOOKUP_KEY,
        "tool_uri": "tool://kc144/live.navigate",
        "parent_lookup_key": "KC144.P30::1f40beaa81e8c0ba956ce835",
        "aliases": list(_P31_LIVE_ALIASES),
        "capabilities": ["P31_LIVE_RUNTIME"],
        "coordinate_bindings": _bindings(),
        "execution_binding": "EXTERNAL_RUNTIME_REQUIRED",
        "handler_id": None,
        "operations": {
            "navigate": {
                "required_inputs": ["query"],
                "required_capabilities": ["P31_LIVE_RUNTIME"],
            }
        },
        "commands": {
            "navigate": ["tool://kc144/live.navigate"],
        },
        "input_schemas": ["KC144.P31.Query.V1"],
        "output_schemas": ["KC144.P31.MyceliumReceipt.V1"],
        "lineage": {
            "release_id": "KC144_P31_LIVE_COGNITION_OS_V3_3",
            "result_id": "KC144.P31::db5a6446ce54cf4bc53515be",
            "archive_sha256": (
                "sha256:"
                "77629d53ef00c970cf115d7cbf94d5e4c9b97928814a702ada8d3f883212d091"
            ),
            "structural_parent_result_id": (
                "KC144.P30::1f40beaa81e8c0ba956ce835"
            ),
        },
        "base_graph_mutated": False,
        "content_transport_certified": False,
        "governance_authority_granted": False,
        "production_truth_effect": "NONE",
    }
    return _seal_descriptor(body)


def mycelium_tool_registry() -> dict[str, Any]:
    descriptors = {
        descriptor["lookup_key"]: descriptor
        for descriptor in (
            parallel_route_tool_descriptor(),
            agent_run_receipt_tool_descriptor(),
            dispatch_tool_descriptor(),
            p31_live_navigate_tool_descriptor(),
        )
    }
    aliases: dict[str, list[str]] = {}
    for lookup_key, descriptor in descriptors.items():
        for alias in descriptor["aliases"]:
            aliases.setdefault(_normalize_alias(alias), []).append(lookup_key)
    alias_index = {
        alias: sorted(set(lookup_keys))
        for alias, lookup_keys in sorted(aliases.items())
    }
    body = {
        "schema": "KC144.MyceliumToolRegistry.V2",
        "keyspace": "EXACT_LOOKUP_KEY",
        "descriptors": descriptors,
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
        candidates = registry["alias_index"].get(_normalize_alias(query), [])
        if len(candidates) > 1:
            body = {
                "schema": "KC144.MyceliumToolLocation.V2",
                "query": query,
                "resolved_lookup_key": None,
                "candidate_lookup_keys": candidates,
                "status": "AMBIGUOUS",
                "resolution": "AMBIGUOUS_EXACT_ALIAS",
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
        resolved = candidates[0] if candidates else None
        resolution = "EXACT_ALIAS" if resolved else "NONE"
    if resolved is None:
        body = {
            "schema": "KC144.MyceliumToolLocation.V2",
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
        "schema": "KC144.MyceliumToolLocation.V2",
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
