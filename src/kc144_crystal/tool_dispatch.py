from __future__ import annotations

import re
import json
from pathlib import Path
from typing import Any, Mapping

from .agent_receipts import (
    canonical_bytes,
    compile_agent_run_receipts,
    content_address,
    verify_agent_run_receipts,
    build_agent_run_plan,
)
from .navigation import adjacency, navigation_relations, shortest_path
from .parallel_routes import (
    AgentTask,
    compile_execution_waves,
    compile_parallel_route_crystal,
)
from .tool_registry import (
    AGENT_RECEIPT_LOOKUP_KEY,
    DISPATCH_LOOKUP_KEY,
    PARALLEL_ROUTE_LOOKUP_KEY,
    locate_mycelium_tool,
    mycelium_tool_registry,
)


GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
PUBLISHED_PARENT_COMMIT = "4f3bd71a1e88130109edd03437b72f21c0e14096"
PUBLISHED_PARENT_TREE = "c15740c445baa1f98e20b3172fb8637c9b44271a"
PARENT_RUNTIME_COMMIT = "91cf0e3c2e8da10ed0787ebf1c0c0105aaf988a9"
PARENT_RUNTIME_TREE = "bc44c4f14b25894a8251e8c1289b718e04eef32a"
PARALLEL_ROUTE_COMMIT = "475259f5ca3e5da3528eddda59f411baf37e57c0"
PARALLEL_ROUTE_DIGEST = (
    "sha256:c8e1a1a7c55a144b7bf20b49ff3fd01ca292a0cd34f134ce0a0abf0d9ac0bc1d"
)
PARENT_RUN_ID = (
    "sha256:0277d691593684417720414f2a2fd00436811e86d946cdc4eb2b1c0e975beb04"
)
PARENT_BUNDLE_DIGEST = (
    "sha256:52b8b2896a7bd1fff45dc3df84ac031172a3bc469375e3d3c775c8e9cb0aef59"
)
P31_ARCHIVE_DIGEST = (
    "sha256:77629d53ef00c970cf115d7cbf94d5e4c9b97928814a702ada8d3f883212d091"
)
ZERO_DIGEST = "sha256:" + ("0" * 64)

PREFLIGHT_LANES = (
    ("IDENTITY", 3, "tool, operation, request, registry, and handler identity"),
    ("SOURCE_HEAD", 5, "exact implementation, parent, and source heads"),
    ("CAPABILITY", 6, "caller ceiling contains every required capability"),
    ("ROUTE_RETURN", 141, "addressable forward route and exact return"),
    ("AUTHORITY_EFFECT", 144, "zero truth, authority, witness, and transport effect"),
)

ALLOWED_HANDLER_OPERATIONS = {
    "kc144.parallel-routes.v1": frozenset({"compile"}),
    "kc144.agent-receipts.v1": frozenset({"plan", "run", "verify"}),
    "kc144.tool-dispatch.v1": frozenset({"registry", "locate"}),
}


class ToolDispatchError(ValueError):
    pass


def _body_address(domain: str, value: Mapping[str, Any], field: str) -> str:
    return content_address(
        domain, {key: item for key, item in value.items() if key != field}
    )


def _is_digest(value: object) -> bool:
    return isinstance(value, str) and bool(DIGEST_PATTERN.fullmatch(value))


def _is_git_sha(value: object) -> bool:
    return isinstance(value, str) and bool(GIT_SHA_PATTERN.fullmatch(value))


def build_dispatch_head_registry(
    *,
    implementation_commit: str,
    implementation_tree: str,
    supersedes_registry_digest: str | None = None,
) -> dict[str, Any]:
    if not _is_git_sha(implementation_commit):
        raise ToolDispatchError("implementation_commit must be a lowercase Git SHA")
    if not _is_git_sha(implementation_tree):
        raise ToolDispatchError("implementation_tree must be a lowercase Git SHA")
    if supersedes_registry_digest is not None and not _is_digest(
        supersedes_registry_digest
    ):
        raise ToolDispatchError(
            "supersedes_registry_digest must be a lowercase SHA-256 address"
        )
    body = {
        "schema": "KC144.DispatchHeadRegistry.V1",
        "lookup_key": DISPATCH_LOOKUP_KEY,
        "repository": "demeet2k/guild-hall",
        "publication_parent": {
            "commit": PUBLISHED_PARENT_COMMIT,
            "tree": PUBLISHED_PARENT_TREE,
        },
        "implementation_head": {
            "commit": implementation_commit,
            "tree": implementation_tree,
        },
        "source_heads": {
            PARALLEL_ROUTE_LOOKUP_KEY: {
                "commit": PARALLEL_ROUTE_COMMIT,
                "content_digest": PARALLEL_ROUTE_DIGEST,
            },
            AGENT_RECEIPT_LOOKUP_KEY: {
                "commit": PUBLISHED_PARENT_COMMIT,
                "runtime_commit": PARENT_RUNTIME_COMMIT,
                "runtime_tree": PARENT_RUNTIME_TREE,
                "run_id": PARENT_RUN_ID,
                "bundle_digest": PARENT_BUNDLE_DIGEST,
            },
            "KC144.P31::LIVE_COGNITION_NAVIGATE": {
                "release_id": "KC144_P31_LIVE_COGNITION_OS_V3_3",
                "result_id": "KC144.P31::db5a6446ce54cf4bc53515be",
                "archive_digest": P31_ARCHIVE_DIGEST,
                "structural_parent_result_id": (
                    "KC144.P30::1f40beaa81e8c0ba956ce835"
                ),
            },
        },
        "supersedes_registry_digest": supersedes_registry_digest,
        "standing": "FROZEN_PUBLIC_CODE_IDENTITY",
        "meaning_of_authoritative": (
            "SELECTED_CODE_IDENTITY_FOR_DETERMINISTIC_REPLAY_ONLY"
        ),
        "governance_authority_granted": False,
        "content_transport_certified": False,
        "truth_effect": "NONE",
    }
    return {
        **body,
        "registry_digest": content_address("kc144.dispatch.head-registry", body),
    }


def verify_dispatch_head_registry(registry: Mapping[str, Any]) -> list[str]:
    errors: set[str] = set()
    if registry.get("schema") != "KC144.DispatchHeadRegistry.V1":
        errors.add("E_SCHEMA")
    if registry.get("lookup_key") != DISPATCH_LOOKUP_KEY:
        errors.add("E_HEAD_STALE")
    if registry.get("repository") != "demeet2k/guild-hall":
        errors.add("E_HEAD_STALE")
    if _body_address(
        "kc144.dispatch.head-registry", registry, "registry_digest"
    ) != registry.get("registry_digest"):
        errors.add("E_HEAD_REGISTRY_DIGEST")
    for record in (
        registry.get("publication_parent", {}),
        registry.get("implementation_head", {}),
    ):
        if not _is_git_sha(record.get("commit")) or not _is_git_sha(
            record.get("tree")
        ):
            errors.add("E_HEAD_STALE")
    if registry.get("publication_parent") != {
        "commit": PUBLISHED_PARENT_COMMIT,
        "tree": PUBLISHED_PARENT_TREE,
    }:
        errors.add("E_HEAD_STALE")
    source_heads = registry.get("source_heads", {})
    if source_heads.get(PARALLEL_ROUTE_LOOKUP_KEY, {}).get(
        "content_digest"
    ) != PARALLEL_ROUTE_DIGEST:
        errors.add("E_HEAD_STALE")
    if source_heads.get(AGENT_RECEIPT_LOOKUP_KEY, {}).get(
        "run_id"
    ) != PARENT_RUN_ID:
        errors.add("E_HEAD_STALE")
    p31 = source_heads.get("KC144.P31::LIVE_COGNITION_NAVIGATE", {})
    if (
        p31.get("archive_digest") != P31_ARCHIVE_DIGEST
        or p31.get("result_id") != "KC144.P31::db5a6446ce54cf4bc53515be"
        or p31.get("structural_parent_result_id")
        != "KC144.P30::1f40beaa81e8c0ba956ce835"
    ):
        errors.add("E_HEAD_STALE")
    if any(
        (
            registry.get("governance_authority_granted") is not False,
            registry.get("content_transport_certified") is not False,
            registry.get("truth_effect") != "NONE",
        )
    ):
        errors.add("E_AUTHORITY_ESCALATION")
    return sorted(errors)


def _validate_tool_registry(registry: Mapping[str, Any]) -> list[str]:
    errors: set[str] = set()
    if registry.get("schema") != "KC144.MyceliumToolRegistry.V2":
        errors.add("E_SCHEMA")
    if _body_address(
        "kc144.mycelium.tool-registry", registry, "registry_digest"
    ) != registry.get("registry_digest"):
        errors.add("E_TOOL_REGISTRY_DIGEST")
    descriptors = registry.get("descriptors", {})
    uris: set[str] = set()
    card_digests: set[str] = set()
    for lookup_key, descriptor in descriptors.items():
        if descriptor.get("lookup_key") != lookup_key:
            errors.add("E_TOOL_REGISTRY_DIGEST")
        if _body_address(
            "kc144.mycelium.tool-descriptor",
            descriptor,
            "descriptor_digest",
        ) != descriptor.get("descriptor_digest"):
            errors.add("E_TOOL_REGISTRY_DIGEST")
        uri = descriptor.get("tool_uri")
        if not isinstance(uri, str) or not uri.startswith("tool://kc144/"):
            errors.add("E_TOOL_REGISTRY_DIGEST")
        elif uri in uris:
            errors.add("E_TOOL_URI_COLLISION")
        else:
            uris.add(uri)
        digest = descriptor.get("descriptor_digest")
        if digest in card_digests:
            errors.add("E_TOOL_CARD_COLLISION")
        card_digests.add(digest)
    for candidates in registry.get("alias_index", {}).values():
        if not isinstance(candidates, list) or len(set(candidates)) != 1:
            errors.add("E_ALIAS_COLLISION")
        elif candidates[0] not in descriptors:
            errors.add("E_TOOL_REGISTRY_DIGEST")
    if any(
        (
            registry.get("base_graph_mutated") is not False,
            registry.get("content_transport_certified") is not False,
            registry.get("governance_authority_granted") is not False,
            registry.get("truth_effect") != "NONE",
        )
    ):
        errors.add("E_AUTHORITY_ESCALATION")
    return sorted(errors)


def build_tool_dispatch_request(
    *,
    lookup_query: str,
    operation: str,
    inputs: Mapping[str, Any],
    head_registry: Mapping[str, Any],
    allowed_capabilities: tuple[str, ...],
    expected_output_schema: str | None = None,
    start_coordinates: tuple[int, ...] = (6,),
    route_budget: int = 18,
    parent_receipt: str | None = PARENT_BUNDLE_DIGEST,
) -> dict[str, Any]:
    if not lookup_query or not operation:
        raise ToolDispatchError("lookup_query and operation are required")
    if not start_coordinates or any(not 1 <= gid <= 144 for gid in start_coordinates):
        raise ToolDispatchError("start_coordinates must contain KC144 GIDs")
    if route_budget < 0:
        raise ToolDispatchError("route_budget cannot be negative")
    if parent_receipt is not None and not _is_digest(parent_receipt):
        raise ToolDispatchError("parent_receipt must be a lowercase SHA-256 address")
    canonical_inputs = {key: inputs[key] for key in sorted(inputs)}
    body = {
        "schema": "KC144.ToolDispatchRequest.V1",
        "lookup_query": lookup_query,
        "operation": operation,
        "inputs": canonical_inputs,
        "input_manifest_digest": content_address(
            "kc144.dispatch.input-manifest", canonical_inputs
        ),
        "expected_output_schema": expected_output_schema,
        "start_coordinates": sorted(set(start_coordinates)),
        "route_budget": route_budget,
        "allowed_capabilities": sorted(set(allowed_capabilities)),
        "allowed_effects": ["PURE_COMPUTE"],
        "tool_registry_digest": mycelium_tool_registry()["registry_digest"],
        "head_registry_digest": head_registry.get("registry_digest"),
        "parent_receipt": parent_receipt,
        "production_truth_effect": "NONE",
        "governance_authority_granted": False,
        "content_transport_certified": False,
    }
    return {
        **body,
        "request_id": content_address("kc144.dispatch.request", body),
    }


def _resolution(
    request: Mapping[str, Any], registry: Mapping[str, Any]
) -> tuple[dict[str, Any] | None, str, list[str]]:
    errors = _validate_tool_registry(registry)
    query = request.get("lookup_query")
    descriptors = registry.get("descriptors", {})
    if query in descriptors:
        return descriptors[query], "EXACT_LOOKUP_KEY", errors
    normalized = ""
    if isinstance(query, str):
        import unicodedata

        normalized = unicodedata.normalize("NFKC", query).lower()
        normalized = re.sub(r"[_\-\s]+", " ", normalized).strip()
    candidates = registry.get("alias_index", {}).get(normalized, [])
    if len(candidates) > 1:
        errors.append("E_ALIAS_COLLISION")
        return None, "AMBIGUOUS_EXACT_ALIAS", sorted(set(errors))
    if len(candidates) == 1 and candidates[0] in descriptors:
        return descriptors[candidates[0]], "EXACT_ALIAS", sorted(set(errors))
    errors.append("E_TOOL_NOT_FOUND")
    return None, "NONE", sorted(set(errors))


def _anchor_holonomy(route_budget: int) -> dict[str, Any]:
    anchors = (6, 3, 5, 141, 144)
    graph = adjacency(navigation_relations("both"))

    def path_chain(sequence: tuple[int, ...]) -> list[list[int]]:
        return [
            shortest_path(left, right, graph)
            for left, right in zip(sequence, sequence[1:])
        ]

    forward = path_chain(anchors)
    returned = path_chain(tuple(reversed(anchors)))
    forward_flat = [
        gid for index, path in enumerate(forward) for gid in path[index > 0 :]
    ]
    return_flat = [
        gid for index, path in enumerate(returned) for gid in path[index > 0 :]
    ]
    forward_hops = sum(max(0, len(path) - 1) for path in forward)
    return_hops = sum(max(0, len(path) - 1) for path in returned)
    exact_retrace = return_flat == list(reversed(forward_flat))
    bridge_ids = sorted(
        {
            segment.get("bridge_id")
            for left, right in zip(forward_flat, forward_flat[1:])
            for segment in navigation_relations("both")
            if {segment["source"], segment["target"]} == {left, right}
            and segment.get("bridge_id")
            and segment.get("standing") != "STRUCTURAL"
        }
    )
    body = {
        "schema": "KC144.KC54DispatchHolonomyReceipt.V1",
        "mode": "EXACT_TYPED_RETRACE",
        "anchor_sequence": list(anchors),
        "forward_paths": forward,
        "return_paths": returned,
        "forward_flat_path": forward_flat,
        "return_flat_path": return_flat,
        "forward_hops": forward_hops,
        "return_hops": return_hops,
        "route_budget": route_budget,
        "within_budget": forward_hops <= route_budget,
        "exact_retrace": exact_retrace,
        "translation_defect": 0 if exact_retrace else 1,
        "open_bridge_ids": bridge_ids,
        "transport_standing": (
            "DECLARED_ROUTE_WITH_OPEN_TRANSPORT_CERTIFICATION"
            if bridge_ids
            else "STRUCTURAL_ROUTE"
        ),
        "content_transport_certified": False,
        "truth_effect": "NONE",
    }
    return {
        **body,
        "holonomy_digest": content_address("kc144.dispatch.holonomy", body),
    }


def _preflight_tasks() -> tuple[AgentTask, ...]:
    tasks = [
        AgentTask(
            task_id=f"PREFLIGHT::{name}",
            execution_mode="PARALLEL_WORKER",
            read_set=(f"DISPATCH/{name}",),
            write_set=(f"PREFLIGHT/{name}",),
            priority=100,
        )
        for name, _, _ in PREFLIGHT_LANES
    ]
    ids = tuple(task.task_id for task in tasks)
    tasks.append(
        AgentTask(
            task_id="REDUCE::PREFLIGHT",
            execution_mode="DETERMINISTIC_REDUCER",
            depends_on=ids,
            read_set=("PREFLIGHT",),
            write_set=("PLAN/DISPATCH",),
            priority=200,
        )
    )
    tasks.append(
        AgentTask(
            task_id="RETURN::M12",
            execution_mode="COORDINATOR_ONLY",
            depends_on=("REDUCE::PREFLIGHT",),
            read_set=("PLAN/DISPATCH",),
            write_set=("RECEIPT/M12",),
            priority=300,
        )
    )
    return tuple(tasks)


def compile_tool_dispatch_plan(
    request: Mapping[str, Any],
    *,
    head_registry: Mapping[str, Any],
    tool_registry: Mapping[str, Any] | None = None,
    executor_workers: int = 5,
) -> dict[str, Any]:
    if not 1 <= executor_workers <= 5:
        raise ToolDispatchError("executor_workers must be in [1, 5]")
    registry = dict(tool_registry or mycelium_tool_registry())
    errors: set[str] = set()
    if request.get("schema") != "KC144.ToolDispatchRequest.V1":
        errors.add("E_SCHEMA")
    if _body_address(
        "kc144.dispatch.request", request, "request_id"
    ) != request.get("request_id"):
        errors.add("E_REQUEST_DIGEST")
    inputs = request.get("inputs", {})
    if not isinstance(inputs, Mapping) or content_address(
        "kc144.dispatch.input-manifest",
        {key: inputs[key] for key in sorted(inputs)} if isinstance(inputs, Mapping) else {},
    ) != request.get("input_manifest_digest"):
        errors.add("E_INPUT_DIGEST")
    errors.update(verify_dispatch_head_registry(head_registry))
    if request.get("head_registry_digest") != head_registry.get("registry_digest"):
        errors.add("E_HEAD_REGISTRY_DIGEST")
    if request.get("tool_registry_digest") != registry.get("registry_digest"):
        errors.add("E_TOOL_REGISTRY_DIGEST")
    descriptor, resolution, resolution_errors = _resolution(request, registry)
    errors.update(resolution_errors)
    operation = request.get("operation")
    operation_contract: Mapping[str, Any] = {}
    if descriptor is not None:
        operation_contract = descriptor.get("operations", {}).get(operation, {})
        if not operation_contract:
            errors.add("E_OPERATION_UNKNOWN")
        required_inputs = set(operation_contract.get("required_inputs", []))
        if not required_inputs <= set(inputs):
            errors.add("E_INPUT_SCHEMA")
        allowed = set(request.get("allowed_capabilities", []))
        required = set(operation_contract.get("required_capabilities", []))
        if not required <= allowed or not required <= set(
            descriptor.get("capabilities", [])
        ):
            errors.add("E_CAPABILITY_DENIED")
        if descriptor.get("execution_binding") != "IN_PROCESS_ONLY":
            errors.add("E_EXTERNAL_RUNTIME_REQUIRED")
        if not descriptor.get("handler_id"):
            errors.add("E_HANDLER_UNREGISTERED")
        elif operation not in ALLOWED_HANDLER_OPERATIONS.get(
            descriptor["handler_id"], frozenset()
        ):
            errors.add("E_HANDLER_UNREGISTERED")
    if any(
        (
            request.get("production_truth_effect") != "NONE",
            request.get("governance_authority_granted") is not False,
            request.get("content_transport_certified") is not False,
            request.get("allowed_effects") != ["PURE_COMPUTE"],
        )
    ):
        errors.add("E_AUTHORITY_ESCALATION")

    holonomy = _anchor_holonomy(request.get("route_budget", -1))
    if not holonomy["within_budget"]:
        errors.add("E_ROUTE_BUDGET")
    if not holonomy["exact_retrace"]:
        errors.add("E_ROUTE_INCOMPLETE")
    tasks = _preflight_tasks()
    waves = compile_execution_waves(tasks, worker_capacity=5)
    lane_reports = []
    lane_error_map = {
        "IDENTITY": {
            code
            for code in errors
            if code
            in {
                "E_SCHEMA",
                "E_REQUEST_DIGEST",
                "E_INPUT_DIGEST",
                "E_TOOL_REGISTRY_DIGEST",
                "E_ALIAS_COLLISION",
                "E_TOOL_CARD_COLLISION",
                "E_TOOL_URI_COLLISION",
                "E_TOOL_NOT_FOUND",
                "E_OPERATION_UNKNOWN",
                "E_HANDLER_UNREGISTERED",
                "E_EXTERNAL_RUNTIME_REQUIRED",
            }
        },
        "SOURCE_HEAD": {
            code
            for code in errors
            if code in {"E_HEAD_STALE", "E_HEAD_REGISTRY_DIGEST"}
        },
        "CAPABILITY": {
            code for code in errors if code in {"E_CAPABILITY_DENIED", "E_INPUT_SCHEMA"}
        },
        "ROUTE_RETURN": {
            code for code in errors if code in {"E_ROUTE_BUDGET", "E_ROUTE_INCOMPLETE"}
        },
        "AUTHORITY_EFFECT": {
            code
            for code in errors
            if code
            in {
                "E_AUTHORITY_ESCALATION",
                "E_TRANSPORT_ESCALATION",
                "E_TRUTH_ESCALATION",
            }
        },
    }
    for name, gid, purpose in PREFLIGHT_LANES:
        body = {
            "schema": "KC144.ToolDispatchPreflight.V1",
            "lane": name,
            "gid": gid,
            "purpose": purpose,
            "request_id": request.get("request_id"),
            "status": "PASS" if not lane_error_map[name] else "BLOCKED",
            "error_codes": sorted(lane_error_map[name]),
            "truth_effect": "NONE",
        }
        lane_reports.append(
            {
                **body,
                "report_digest": content_address(
                    "kc144.dispatch.preflight", body
                ),
            }
        )
    body = {
        "schema": "KC144.ToolDispatchPlan.V1",
        "lookup_key": DISPATCH_LOOKUP_KEY,
        "parent_lookup_key": AGENT_RECEIPT_LOOKUP_KEY,
        "request_id": request.get("request_id"),
        "tool_registry_digest": registry.get("registry_digest"),
        "head_registry_digest": head_registry.get("registry_digest"),
        "resolved_lookup_key": (
            descriptor.get("lookup_key") if descriptor is not None else None
        ),
        "descriptor_digest": (
            descriptor.get("descriptor_digest") if descriptor is not None else None
        ),
        "resolution": resolution,
        "operation": operation,
        "handler_id": descriptor.get("handler_id") if descriptor else None,
        "required_capabilities": sorted(
            operation_contract.get("required_capabilities", [])
        ),
        "status": "READY" if not errors else "BLOCKED",
        "error_codes": sorted(errors),
        "canonical_worker_capacity": 5,
        "requested_capacity_excluded_from_identity": True,
        "task_ids": [task.task_id for task in tasks],
        "execution_waves": waves,
        "preflight_reports": lane_reports,
        "holonomy": holonomy,
        "base_graph_mutated": False,
        "content_transport_certified": False,
        "governance_authority_granted": False,
        "truth_effect": "NONE",
    }
    return {
        **body,
        "plan_digest": content_address("kc144.dispatch.plan", body),
    }


def _execute_handler(
    handler_id: str, operation: str, inputs: Mapping[str, Any]
) -> dict[str, Any]:
    if handler_id == "kc144.parallel-routes.v1" and operation == "compile":
        return compile_parallel_route_crystal(
            executor_workers=5,
            coordinate_binding=inputs.get("coordinate_binding"),
        )
    if handler_id == "kc144.agent-receipts.v1":
        if operation == "plan":
            return build_agent_run_plan(inputs["parallel_route_snapshot"])
        if operation == "run":
            return compile_agent_run_receipts(
                inputs["parallel_route_snapshot"],
                executor_workers=5,
                runtime_binding=inputs.get("runtime_binding"),
            )
        if operation == "verify":
            return verify_agent_run_receipts(
                inputs["run_receipt_bundle"],
                source_crystal=inputs.get("parallel_route_snapshot"),
            )
    if handler_id == "kc144.tool-dispatch.v1":
        if operation == "registry":
            return mycelium_tool_registry()
        if operation == "locate":
            return locate_mycelium_tool(inputs["query"])
    raise ToolDispatchError("handler/operation pair is not statically registered")


def _protected_effect_errors(value: object) -> set[str]:
    errors: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key == "content_transport_certified" and item is not False:
                errors.add("E_TRANSPORT_ESCALATION")
            elif key == "governance_authority_granted" and item is not False:
                errors.add("E_AUTHORITY_ESCALATION")
            elif key in {"production_truth_effect", "truth_effect"} and item != "NONE":
                errors.add("E_TRUTH_ESCALATION")
            elif key in {
                "independent_witness_count",
                "actual_live_promotions",
                "real_external_applications",
            } and item != 0:
                errors.add("E_AUTHORITY_ESCALATION")
            errors.update(_protected_effect_errors(item))
    elif isinstance(value, list):
        for item in value:
            errors.update(_protected_effect_errors(item))
    return errors


def dispatch_mycelium_tool(
    request: Mapping[str, Any],
    *,
    head_registry: Mapping[str, Any],
    tool_registry: Mapping[str, Any] | None = None,
    executor_workers: int = 5,
) -> dict[str, Any]:
    registry = dict(tool_registry or mycelium_tool_registry())
    plan = compile_tool_dispatch_plan(
        request,
        head_registry=head_registry,
        tool_registry=registry,
        executor_workers=executor_workers,
    )
    status = "BLOCKED"
    output: dict[str, Any] | None = None
    error_codes = list(plan["error_codes"])
    if plan["status"] == "READY":
        try:
            output = _execute_handler(
                plan["handler_id"], plan["operation"], request["inputs"]
            )
            status = "EXECUTED"
        except (KeyError, TypeError, ValueError, ToolDispatchError):
            error_codes.append("E_HANDLER_FAILED")
            status = "FAILED"
    expected_schema = request.get("expected_output_schema")
    if (
        output is not None
        and expected_schema is not None
        and output.get("schema") != expected_schema
    ):
        error_codes.append("E_OUTPUT_SCHEMA")
        status = "FAILED"
    output_digest = (
        content_address("kc144.dispatch.output", output)
        if output is not None
        else None
    )
    output_effect_errors = (
        _protected_effect_errors(output) if output is not None else set()
    )
    if output_effect_errors:
        error_codes.extend(output_effect_errors)
        status = "FAILED"
        output = None
        output_digest = None
    events: list[dict[str, Any]] = []
    previous = ZERO_DIGEST
    for sequence, (event_type, subject) in enumerate(
        (
            ("REQUEST_ACCEPTED", request.get("request_id")),
            ("PLAN_COMPILED", plan["plan_digest"]),
            (
                "HANDLER_EXECUTED" if status == "EXECUTED" else "DISPATCH_HELD",
                output_digest or plan["plan_digest"],
            ),
            ("M12_RETURN_SEALED", plan["holonomy"]["holonomy_digest"]),
        )
    ):
        event_body = {
            "schema": "KC144.ToolDispatchEvent.V1",
            "sequence": sequence,
            "event_type": event_type,
            "subject_digest": subject,
            "previous_event_hash": previous,
            "truth_effect": "NONE",
        }
        event = {
            **event_body,
            "event_hash": content_address("kc144.dispatch.event", event_body),
        }
        events.append(event)
        previous = event["event_hash"]
    result_body = {
        "schema": "KC144.ToolDispatchResult.V1",
        "lookup_key": DISPATCH_LOOKUP_KEY,
        "request": dict(request),
        "request_id": request.get("request_id"),
        "plan": plan,
        "plan_digest": plan["plan_digest"],
        "status": status,
        "error_codes": sorted(set(error_codes)),
        "resolved_lookup_key": plan["resolved_lookup_key"],
        "descriptor_digest": plan["descriptor_digest"],
        "operation": plan["operation"],
        "handler_id": plan["handler_id"],
        "output": output,
        "output_digest": output_digest,
        "audit_events": events,
        "audit_root": previous,
        "holonomy_receipt": plan["holonomy"],
        "replay_capsule": {
            "request_id": request.get("request_id"),
            "tool_registry_digest": registry.get("registry_digest"),
            "head_registry_digest": head_registry.get("registry_digest"),
            "implementation_head": head_registry.get("implementation_head"),
            "status": "COLD_REPLAY_READY",
        },
        "independent_witness_count": 0,
        "base_graph_mutated": False,
        "content_transport_certified": False,
        "governance_authority_granted": False,
        "production_truth_effect": "NONE",
    }
    return {
        **result_body,
        "result_digest": content_address("kc144.dispatch.result", result_body),
    }


def verify_tool_dispatch_result(
    result: Mapping[str, Any],
    *,
    head_registry: Mapping[str, Any],
    tool_registry: Mapping[str, Any] | None = None,
    cold_replay: bool = True,
) -> dict[str, Any]:
    registry = dict(tool_registry or mycelium_tool_registry())
    errors: set[str] = set()
    if result.get("schema") != "KC144.ToolDispatchResult.V1":
        errors.add("E_SCHEMA")
    if _body_address(
        "kc144.dispatch.result", result, "result_digest"
    ) != result.get("result_digest"):
        errors.add("E_RESULT_DIGEST")
    request = result.get("request", {})
    try:
        expected_plan = compile_tool_dispatch_plan(
            request,
            head_registry=head_registry,
            tool_registry=registry,
            executor_workers=1,
        )
    except (TypeError, ValueError, ToolDispatchError):
        expected_plan = {}
        errors.add("E_REPLAY_DRIFT")
    if expected_plan != result.get("plan"):
        errors.add("E_REPLAY_DRIFT")
    if result.get("plan_digest") != expected_plan.get("plan_digest"):
        errors.add("E_REPLAY_DRIFT")
    events = result.get("audit_events", [])
    previous = ZERO_DIGEST
    for sequence, event in enumerate(events):
        if (
            event.get("sequence") != sequence
            or event.get("previous_event_hash") != previous
            or _body_address("kc144.dispatch.event", event, "event_hash")
            != event.get("event_hash")
        ):
            errors.add("E_EVENT_CHAIN")
        previous = event.get("event_hash", "")
    if result.get("audit_root") != previous or len(events) != 4:
        errors.add("E_EVENT_CHAIN")
    holonomy = result.get("holonomy_receipt", {})
    if (
        _body_address(
            "kc144.dispatch.holonomy", holonomy, "holonomy_digest"
        )
        != holonomy.get("holonomy_digest")
        or not holonomy.get("exact_retrace")
    ):
        errors.add("E_ROUTE_INCOMPLETE")
    if cold_replay and expected_plan.get("status") == "READY":
        try:
            replay_output = _execute_handler(
                expected_plan["handler_id"],
                expected_plan["operation"],
                request["inputs"],
            )
        except (KeyError, TypeError, ValueError, ToolDispatchError):
            replay_output = None
            errors.add("E_REPLAY_DRIFT")
        if replay_output != result.get("output"):
            errors.add("E_REPLAY_DRIFT")
        if (
            content_address("kc144.dispatch.output", replay_output)
            != result.get("output_digest")
        ):
            errors.add("E_OUTPUT_DIGEST")
    elif result.get("output") is not None:
        if content_address(
            "kc144.dispatch.output", result["output"]
        ) != result.get("output_digest"):
            errors.add("E_OUTPUT_DIGEST")
    if any(
        (
            result.get("independent_witness_count") != 0,
            result.get("base_graph_mutated") is not False,
            result.get("content_transport_certified") is not False,
            result.get("governance_authority_granted") is not False,
            result.get("production_truth_effect") != "NONE",
        )
    ):
        errors.add("E_AUTHORITY_ESCALATION")
    return {
        "schema": "KC144.ToolDispatchVerification.V1",
        "lookup_key": DISPATCH_LOOKUP_KEY,
        "verdict": "PASS" if not errors else "FAIL",
        "errors": sorted(errors),
        "request_id": request.get("request_id"),
        "plan_digest": result.get("plan_digest"),
        "result_digest": result.get("result_digest"),
        "audit_root": result.get("audit_root"),
        "replay_status": "REPLAY_STABLE" if not errors else "REPLAY_DRIFT",
        "independent_witness_count": 0,
        "content_transport_certified": False,
        "governance_authority_granted": False,
        "truth_effect": "NONE",
    }


def tool_dispatch_contract() -> dict[str, Any]:
    body = {
        "schema": "KC144.ToolDispatchContract.V1",
        "lookup_key": DISPATCH_LOOKUP_KEY,
        "parent_lookup_key": AGENT_RECEIPT_LOOKUP_KEY,
        "route": ["GID006/H06", "GID003/H03", "GID005/H05", "GID141/M09", "GID144/M12"],
        "preflight_lanes": [name for name, _, _ in PREFLIGHT_LANES],
        "maximum_parallel_width": 5,
        "lookup_law": "EXACT_KEY_THEN_ONE_COMPLETE_NFKC_ALIAS_ONLY",
        "execution_law": "STATIC_IN_PROCESS_HANDLER_ALLOWLIST_ONLY",
        "blocked_is_receipted": True,
        "physical_capacity_excluded_from_identity": True,
        "p31_external_runtime_substitution": "FORBIDDEN",
        "cold_replay_is_independent_evidence": False,
        "base_graph_mutated": False,
        "content_transport_certified": False,
        "governance_authority_granted": False,
        "truth_effect": "NONE",
    }
    return {
        **body,
        "contract_digest": content_address("kc144.dispatch.contract", body),
    }


def compile_tool_dispatch_runtime(
    output_directory: str | Path,
    *,
    implementation_commit: str,
    implementation_tree: str,
    parallel_route_snapshot: Mapping[str, Any],
    run_receipt_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    heads = build_dispatch_head_registry(
        implementation_commit=implementation_commit,
        implementation_tree=implementation_tree,
    )
    registry = mycelium_tool_registry()
    request = build_tool_dispatch_request(
        lookup_query=AGENT_RECEIPT_LOOKUP_KEY,
        operation="verify",
        inputs={
            "parallel_route_snapshot": dict(parallel_route_snapshot),
            "run_receipt_bundle": dict(run_receipt_bundle),
        },
        head_registry=heads,
        allowed_capabilities=("VERIFY_RUN_REPLAY",),
        expected_output_schema="KC144.AgentRunVerification.V1",
    )
    result = dispatch_mycelium_tool(
        request,
        head_registry=heads,
        tool_registry=registry,
    )
    verification = verify_tool_dispatch_result(
        result,
        head_registry=heads,
        tool_registry=registry,
    )
    request_path = (
        "requests/sha256/"
        f"{request['request_id'][7:9]}/{request['request_id'][7:]}.json"
    )
    result_path = (
        "results/sha256/"
        f"{result['result_digest'][7:9]}/{result['result_digest'][7:]}.json"
    )
    documents = {
        "head_registry_v1.json": heads,
        "tool_registry_v2.json": registry,
        "dispatch_contract_v1.json": tool_dispatch_contract(),
        "dispatch_request_v1.json": request,
        "dispatch_result_v1.json": result,
        "dispatch_verification_v1.json": verification,
        request_path: request,
        result_path: result,
    }
    release_body = {
        "schema": "KC144.ToolDispatchRelease.V1",
        "release": DISPATCH_LOOKUP_KEY,
        "parent_lookup_key": AGENT_RECEIPT_LOOKUP_KEY,
        "implementation_head": heads["implementation_head"],
        "head_registry_digest": heads["registry_digest"],
        "tool_registry_digest": registry["registry_digest"],
        "request_id": request["request_id"],
        "plan_digest": result["plan_digest"],
        "result_digest": result["result_digest"],
        "audit_root": result["audit_root"],
        "holonomy_digest": result["holonomy_receipt"]["holonomy_digest"],
        "dispatch_status": result["status"],
        "verification_verdict": verification["verdict"],
        "replay_status": verification["replay_status"],
        "registered_tools": len(registry["descriptors"]),
        "preflight_lanes": len(result["plan"]["preflight_reports"]),
        "maximum_parallel_width": 5,
        "open_bridge_ids": result["holonomy_receipt"]["open_bridge_ids"],
        "independent_witness_count": 0,
        "real_external_applications": 0,
        "base_graph_mutated": False,
        "content_transport_certified": False,
        "governance_authority_granted": False,
        "production_truth_effect": "NONE",
        "next_seed": (
            "KC144.V1::P31_EXACT_RUNTIME_ADAPTER_"
            "AND_WITNESSED_TOOL_OUTCOME_INTAKE"
        ),
        "artifacts": sorted([*documents, "dispatch_release_v1.json"]),
    }
    release = {
        **release_body,
        "release_digest": content_address(
            "kc144.dispatch.release", release_body
        ),
    }
    documents["dispatch_release_v1.json"] = release
    for filename, document in documents.items():
        destination = output / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(
                document,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n",
            encoding="utf-8",
        )
    return release
