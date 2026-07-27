from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from .parallel_routes import (
    AgentTask,
    ParallelRouteError,
    compile_execution_waves,
    compile_parallel_route_crystal,
)


LOOKUP_KEY = "KC144.V1::CONTENT_ADDRESSED_AGENT_RUN_RECEIPTS"
PARENT_LOOKUP_KEY = "KC144.V1::PARALLEL_ROUTE_CRYSTAL"
ZERO_DIGEST = "sha256:" + ("0" * 64)
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
RETRYABLE_ERROR_CODES = (
    "E_LEASE_EXPIRED",
    "E_MERGE_BASE_TRANSITION",
    "E_SPAWN_TRANSPORT",
    "E_TOOL_TRANSIENT",
    "E_TRUNCATED_ENVELOPE",
)


class AgentReceiptError(ValueError):
    pass


@dataclass(frozen=True)
class LeaseGrant:
    run_id: str
    plan_digest: str
    work_id: str
    task_id: str
    attempt: int
    logical_epoch: int
    logical_slot: int
    input_manifest_digest: str
    allowed_capabilities: tuple[str, ...]
    read_set: tuple[str, ...]
    write_set: tuple[str, ...]
    output_schema: str
    expires_after_epoch: int
    supersedes_lease_id: str | None = None


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def content_address(domain: str, value: object) -> str:
    envelope = {"domain": domain, "version": 1, "value": value}
    return "sha256:" + hashlib.sha256(canonical_bytes(envelope)).hexdigest()


def _address_body(domain: str, value: Mapping[str, Any], field: str) -> str:
    return content_address(
        domain,
        {key: item for key, item in value.items() if key != field},
    )


def _require_digest(value: object, label: str) -> str:
    if not isinstance(value, str) or not DIGEST_PATTERN.fullmatch(value):
        raise AgentReceiptError(f"{label} must be a lowercase SHA-256 address")
    return value


def _sorted_unique(values: Iterable[str]) -> list[str]:
    result = sorted(set(values))
    if any(not value for value in result):
        raise AgentReceiptError("canonical string sets cannot contain empty values")
    return result


def _resource_covers(claim: str, resource: str) -> bool:
    claim_parts = tuple(part for part in claim.strip("/").split("/") if part)
    resource_parts = tuple(part for part in resource.strip("/").split("/") if part)
    return resource_parts[: len(claim_parts)] == claim_parts


def _source_crystal_integrity(source_crystal: Mapping[str, Any]) -> None:
    if source_crystal.get("schema") != "KC144.ParallelRouteCrystal.V1":
        raise AgentReceiptError("source must be KC144.ParallelRouteCrystal.V1")
    expected = content_address(
        "kc144.parallel-route-crystal.compat",
        {
            key: value
            for key, value in source_crystal.items()
            if key != "crystal_digest"
        },
    )
    # ParallelRouteCrystal.V1 predates domain-separated addresses. Preserve its
    # exact native digest law while binding it into this domain-separated graph.
    legacy_expected = "sha256:" + hashlib.sha256(
        canonical_bytes(
            {
                key: value
                for key, value in source_crystal.items()
                if key != "crystal_digest"
            }
        )
    ).hexdigest()
    actual = _require_digest(source_crystal.get("crystal_digest"), "crystal_digest")
    if actual not in {expected, legacy_expected}:
        raise AgentReceiptError("source crystal digest mismatch")


def _task_body(
    *,
    task_id: str,
    phase: str,
    instruction: Mapping[str, Any],
    execution_mode: str,
    depends_on: Iterable[str],
    capabilities: Iterable[str],
    read_set: Iterable[str],
    write_set: Iterable[str],
    expected_result_digest: str,
    base_digest: str,
    priority: int = 100,
    attempt_limit: int = 2,
    independent_agent_required: bool = False,
    merge_authority: bool = False,
) -> dict[str, Any]:
    body = {
        "schema": "KC144.AgentTask.V1",
        "task_id": task_id,
        "phase": phase,
        "instruction_digest": content_address(
            "kc144.agent.instruction", instruction
        ),
        "execution_mode": execution_mode,
        "depends_on": _sorted_unique(depends_on),
        "capabilities": _sorted_unique(capabilities),
        "read_set": _sorted_unique(read_set),
        "write_set": _sorted_unique(write_set),
        "expected_result_digest": _require_digest(
            expected_result_digest, "expected_result_digest"
        ),
        "base_digest": _require_digest(base_digest, "base_digest"),
        "priority": priority,
        "attempt_limit": attempt_limit,
        "output_schema": "KC144.AgentTaskResult.V1",
        "independent_agent_required": independent_agent_required,
        "merge_authority": merge_authority,
        "truth_effect": "NONE",
    }
    return {
        **body,
        "work_id": content_address("kc144.agent.task", body),
    }


def build_agent_run_plan(
    source_crystal: Mapping[str, Any],
    *,
    receipt_runtime: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    _source_crystal_integrity(source_crystal)
    snapshot_digest = source_crystal["crystal_digest"]
    worker_tasks: list[dict[str, Any]] = []
    for simulation in sorted(
        source_crystal["simulations"], key=lambda row: row["route_id"]
    ):
        route_id = simulation["route_id"]
        worker_tasks.append(
            _task_body(
                task_id=f"SIMULATE::{route_id}",
                phase="ROUTE_SIMULATION",
                instruction={
                    "route_id": route_id,
                    "input": simulation["input"],
                    "graph": simulation["graph"],
                },
                execution_mode="PARALLEL_WORKER",
                depends_on=(),
                capabilities=("KC144_ROUTE_SIMULATOR_V1",),
                read_set=(
                    f"SNAPSHOT/{snapshot_digest}",
                    f"GRAPH/{simulation['graph']['graph_digest']}",
                ),
                write_set=(f"RESULT/{route_id}",),
                expected_result_digest=simulation["simulation_digest"],
                base_digest=snapshot_digest,
            )
        )
    worker_tasks.sort(key=lambda task: task["work_id"])

    worker_ids = [task["work_id"] for task in worker_tasks]
    reducer_task = _task_body(
        task_id="INTEGRATE::PARALLEL_ROUTE_CRYSTAL",
        phase="DETERMINISTIC_REDUCTION",
        instruction={
            "mode": source_crystal["mode"],
            "merge_order": worker_ids,
            "pairwise_holonomy": source_crystal["pairwise_holonomy"],
        },
        execution_mode="DETERMINISTIC_REDUCER",
        depends_on=worker_ids,
        capabilities=("KC144_PARALLEL_ROUTE_REDUCER_V1",),
        read_set=tuple(task["write_set"][0] for task in worker_tasks),
        write_set=("RESULT/PARALLEL_ROUTE_CRYSTAL",),
        expected_result_digest=snapshot_digest,
        base_digest=snapshot_digest,
        priority=200,
        merge_authority=True,
    )
    tasks = worker_tasks + [reducer_task]
    registry = {task["work_id"]: task for task in tasks}
    source_binding = source_crystal.get("coordinate_binding", {})
    frozen_source = {
        "repository": "demeet2k/guild-hall",
        "commit": source_binding.get("compiler_commit", "UNBOUND_LOCAL_REPLAY"),
        "tree": source_binding.get("compiler_tree", "UNBOUND_LOCAL_REPLAY"),
    }
    body = {
        "schema": "KC144.AgentRunPlan.V1",
        "lookup_key": LOOKUP_KEY,
        "parent_lookup_key": PARENT_LOOKUP_KEY,
        "frozen_source": frozen_source,
        "receipt_runtime": _runtime_binding(
            source_crystal, receipt_runtime
        ),
        "input_snapshot_digest": snapshot_digest,
        "capacity": 5,
        "tasks": [task["work_id"] for task in tasks],
        "task_registry": registry,
        "execution_waves": [worker_ids, [reducer_task["work_id"]]],
        "merge_order": worker_ids + [reducer_task["work_id"]],
        "retryable_error_codes": list(RETRYABLE_ERROR_CODES),
        "spawn_fallback": (
            "LOCAL_CANONICAL_EXECUTION_UNLESS_INDEPENDENT_REQUIRED"
        ),
        "truth_effect": "NONE",
    }
    return {
        **body,
        "plan_digest": content_address("kc144.agent.plan", body),
    }


def _root_input_manifest(plan: Mapping[str, Any]) -> str:
    return content_address(
        "kc144.agent.input-manifest",
        {
            "frozen_source": plan["frozen_source"],
            "source_snapshot_digest": plan["input_snapshot_digest"],
            "declared_read_object_digests": sorted(
                {
                    resource.split("/", 1)[1]
                    for task in plan["task_registry"].values()
                    for resource in task["read_set"]
                    if "/" in resource
                    and DIGEST_PATTERN.fullmatch(resource.split("/", 1)[1])
                }
            ),
        },
    )


def _task_input_manifest(
    plan: Mapping[str, Any],
    work_id: str,
    root_input_manifest_digest: str,
) -> str:
    task = plan["task_registry"][work_id]
    dependency_results = [
        plan["task_registry"][dependency]["expected_result_digest"]
        for dependency in task["depends_on"]
    ]
    return content_address(
        "kc144.agent.input-manifest",
        {
            "root_input_manifest_digest": root_input_manifest_digest,
            "work_id": work_id,
            "dependency_result_digests": dependency_results,
        },
    )


def _run_id(plan: Mapping[str, Any], root_input_manifest_digest: str) -> str:
    return content_address(
        "kc144.agent.run",
        {
            "lookup_key": LOOKUP_KEY,
            "plan_digest": plan["plan_digest"],
            "root_input_manifest_digest": root_input_manifest_digest,
            "canonical_runtime_config": {
                "capacity": plan["capacity"],
                "scheduler": "DEPENDENCY_READY_CONFLICT_FREE_V1",
                "merge": "PLAN_ORDER_V1",
                "retry_policy": list(RETRYABLE_ERROR_CODES),
                "receipt_schema": "KC144.AgentRunReceipt.V1",
            },
        },
    )


def issue_lease(grant: LeaseGrant) -> dict[str, Any]:
    if grant.attempt < 1:
        raise AgentReceiptError("lease attempts start at one")
    if grant.logical_epoch < 0 or grant.logical_slot < 0:
        raise AgentReceiptError("logical epoch and slot must be nonnegative")
    if grant.expires_after_epoch < grant.logical_epoch:
        raise AgentReceiptError("lease cannot expire before it is granted")
    body = {
        "schema": "KC144.AgentLease.V1",
        **asdict(grant),
        "allowed_capabilities": _sorted_unique(grant.allowed_capabilities),
        "read_set": _sorted_unique(grant.read_set),
        "write_set": _sorted_unique(grant.write_set),
        "deadline_policy": "EXPLICIT_LOGICAL_EPOCH_TRANSITION",
    }
    return {
        **body,
        "lease_id": content_address("kc144.agent.lease", body),
    }


def retry_allowed(
    plan: Mapping[str, Any],
    work_id: str,
    *,
    attempt: int,
    error_code: str,
) -> bool:
    task = plan["task_registry"].get(work_id)
    return bool(
        task
        and error_code in plan["retryable_error_codes"]
        and attempt < task["attempt_limit"]
    )


def _result_envelope(
    *,
    run_id: str,
    plan: Mapping[str, Any],
    task: Mapping[str, Any],
    lease: Mapping[str, Any],
    input_manifest_digest: str,
    result_payload: Mapping[str, Any],
) -> dict[str, Any]:
    result_digest = task["expected_result_digest"]
    artifact = {
        "artifact_key": "canonical-result",
        "destination": task["write_set"][0],
        "semantic_write_key": task["write_set"][0],
        "media_type": "application/json",
        "base_digest": task["base_digest"],
        "content_digest": result_digest,
        "byte_length": len(canonical_bytes(result_payload)),
    }
    body = {
        "schema": "KC144.AgentTaskResult.V1",
        "run_id": run_id,
        "plan_digest": plan["plan_digest"],
        "work_id": task["work_id"],
        "task_id": task["task_id"],
        "attempt": lease["attempt"],
        "lease_id": lease["lease_id"],
        "input_manifest_digest": input_manifest_digest,
        "status": "SUCCESS",
        "claims": [
            {
                "claim_key": "CANONICAL_RESULT_DIGEST",
                "evidence_ref": "artifact:canonical-result",
            }
        ],
        "artifacts": [artifact],
        "checks": [
            {
                "check_id": "expected-result-digest",
                "status": "PASS",
                "evidence_digest": result_digest,
            },
            {
                "check_id": "truth-isolation",
                "status": "PASS",
                "evidence_digest": content_address(
                    "kc144.agent.check",
                    {
                        "governance_authority_granted": False,
                        "content_transport_certified": False,
                        "truth_effect": "NONE",
                    },
                ),
            },
        ],
        "failure": None,
        "executor": {
            "kind": "LOCAL_DETERMINISTIC_SIMULATION",
            "independent_agent": False,
        },
        "truth_effect": "NONE",
    }
    return {
        **body,
        "result_digest": content_address("kc144.agent.result", body),
    }


def validate_task_result(
    plan: Mapping[str, Any],
    leases: Iterable[Mapping[str, Any]],
    result: Mapping[str, Any],
    *,
    run_id: str,
    logical_epoch: int,
    accepted_work_ids: Iterable[str] = (),
) -> list[str]:
    errors: set[str] = set()
    work_id = result.get("work_id")
    task = plan.get("task_registry", {}).get(work_id)
    lease_by_id = {lease.get("lease_id"): lease for lease in leases}
    lease = lease_by_id.get(result.get("lease_id"))
    if task is None:
        errors.add("E_TASK_BINDING")
    if result.get("run_id") != run_id:
        errors.add("E_RUN_BINDING")
    if result.get("plan_digest") != plan.get("plan_digest"):
        errors.add("E_PLAN_BINDING")
    if lease is None:
        errors.add("E_LEASE_UNKNOWN")
    else:
        if lease.get("run_id") != run_id:
            errors.add("E_RUN_BINDING")
        if lease.get("plan_digest") != plan.get("plan_digest"):
            errors.add("E_PLAN_BINDING")
        for field, code in (
            ("work_id", "E_TASK_BINDING"),
            ("task_id", "E_TASK_BINDING"),
            ("attempt", "E_ATTEMPT_BINDING"),
            ("input_manifest_digest", "E_INPUT_BINDING"),
        ):
            if result.get(field) != lease.get(field):
                errors.add(code)
        if logical_epoch > lease.get("expires_after_epoch", -1):
            errors.add("E_LEASE_LATE")
        same_work = [
            item
            for item in lease_by_id.values()
            if item.get("work_id") == work_id
        ]
        if any(
            item.get("attempt", 0) > lease.get("attempt", 0)
            for item in same_work
        ):
            errors.add("E_LEASE_SUPERSEDED")
    if work_id in set(accepted_work_ids):
        errors.add("E_LEASE_NOT_LIVE")
    if task is not None:
        if result.get("task_id") != task["task_id"]:
            errors.add("E_TASK_BINDING")
        if (
            result.get("executor", {}).get("independent_agent") is False
            and task["independent_agent_required"]
        ):
            errors.add("E_AUTHORITY_ESCALATION")
        if result.get("truth_effect") != "NONE":
            errors.add("E_TRUTH_ESCALATION")
        if _address_body(
            "kc144.agent.result", result, "result_digest"
        ) != result.get("result_digest"):
            errors.add("E_DIGEST_MISMATCH")
        artifacts = result.get("artifacts", [])
        for artifact in artifacts:
            destination = artifact.get("semantic_write_key", "")
            if not any(
                _resource_covers(claim, destination)
                for claim in task["write_set"]
            ):
                errors.add("E_UNDECLARED_WRITE")
            if artifact.get("base_digest") != task["base_digest"]:
                errors.add("E_STALE_BASE")
            if artifact.get("content_digest") != task["expected_result_digest"]:
                errors.add("E_ARTIFACT_DIGEST")
        if not artifacts:
            errors.add("E_CLAIM_EVIDENCE_MISSING")
    if result.get("status") not in {
        "SUCCESS",
        "NO_CHANGE",
        "BLOCKED",
        "RETRYABLE_FAILURE",
        "PERMANENT_FAILURE",
    }:
        errors.add("E_RESULT_STATUS")
    if any(check.get("status") != "PASS" for check in result.get("checks", [])):
        errors.add("E_CHECK_FAILED")
    return sorted(errors)


def _validation_receipt(
    *,
    result: Mapping[str, Any],
    decision: str,
    validation_errors: Iterable[str],
    pre_merge_snapshot_digest: str,
    post_merge_snapshot_digest: str,
) -> dict[str, Any]:
    body = {
        "schema": "KC144.AgentRunReceipt.V1",
        "run_id": result["run_id"],
        "plan_digest": result["plan_digest"],
        "work_id": result["work_id"],
        "attempt": result["attempt"],
        "lease_id": result["lease_id"],
        "result_digest": result["result_digest"],
        "decision": decision,
        "validation_errors": sorted(set(validation_errors)),
        "artifact_digests": sorted(
            artifact["content_digest"] for artifact in result["artifacts"]
        ),
        "pre_merge_snapshot_digest": pre_merge_snapshot_digest,
        "post_merge_snapshot_digest": post_merge_snapshot_digest,
    }
    return {
        **body,
        "receipt_digest": content_address("kc144.agent.receipt", body),
    }


def _append_event(
    events: list[dict[str, Any]],
    *,
    run_id: str,
    logical_epoch: int,
    event_type: str,
    subject_digest: str,
    work_id: str | None = None,
    attempt: int | None = None,
    lease_id: str | None = None,
    decision: str | None = None,
    reason_codes: Iterable[str] = (),
) -> None:
    body = {
        "schema": "KC144.AgentRunEvent.V1",
        "run_id": run_id,
        "sequence": len(events),
        "logical_epoch": logical_epoch,
        "event_type": event_type,
        "work_id": work_id,
        "attempt": attempt,
        "lease_id": lease_id,
        "subject_digest": subject_digest,
        "decision": decision,
        "reason_codes": sorted(set(reason_codes)),
        "previous_event_hash": (
            events[-1]["event_hash"] if events else ZERO_DIGEST
        ),
    }
    events.append(
        {
            **body,
            "event_hash": content_address("kc144.agent.event", body),
        }
    )


def _runtime_binding(
    source_crystal: Mapping[str, Any],
    binding: Mapping[str, str] | None,
) -> dict[str, str]:
    if binding is None:
        return {"standing": "UNBOUND_LOCAL_REPLAY"}
    if dict(binding) == {"standing": "UNBOUND_LOCAL_REPLAY"}:
        return {"standing": "UNBOUND_LOCAL_REPLAY"}
    required = {"runtime_commit", "runtime_tree", "source_snapshot_digest"}
    if set(binding) != required:
        raise AgentReceiptError(
            f"runtime_binding must contain exactly {sorted(required)}"
        )
    if not GIT_SHA_PATTERN.fullmatch(binding["runtime_commit"]):
        raise AgentReceiptError("runtime_commit must be a lowercase Git SHA")
    if not GIT_SHA_PATTERN.fullmatch(binding["runtime_tree"]):
        raise AgentReceiptError("runtime_tree must be a lowercase Git SHA")
    _require_digest(binding["source_snapshot_digest"], "source_snapshot_digest")
    if binding["source_snapshot_digest"] != source_crystal["crystal_digest"]:
        raise AgentReceiptError("runtime binding has a stale source snapshot")
    return dict(binding)


def compile_agent_run_receipts(
    source_crystal: Mapping[str, Any] | None = None,
    *,
    executor_workers: int = 5,
    runtime_binding: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    if not 1 <= executor_workers <= 5:
        raise AgentReceiptError("executor_workers must be in [1, 5]")
    source = (
        dict(source_crystal)
        if source_crystal is not None
        else compile_parallel_route_crystal(executor_workers=executor_workers)
    )
    _source_crystal_integrity(source)
    binding = _runtime_binding(source, runtime_binding)
    plan = build_agent_run_plan(source, receipt_runtime=binding)
    root_input = _root_input_manifest(plan)
    run_id = _run_id(plan, root_input)
    simulations = {
        row["route_id"]: row
        for row in source["simulations"]
    }
    reducer_payload = source

    leases: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    current_snapshot = plan["input_snapshot_digest"]
    accepted: set[str] = set()
    for epoch, wave in enumerate(plan["execution_waves"]):
        for slot, work_id in enumerate(wave):
            task = plan["task_registry"][work_id]
            input_manifest = _task_input_manifest(plan, work_id, root_input)
            lease = issue_lease(
                LeaseGrant(
                    run_id=run_id,
                    plan_digest=plan["plan_digest"],
                    work_id=work_id,
                    task_id=task["task_id"],
                    attempt=1,
                    logical_epoch=epoch,
                    logical_slot=slot,
                    input_manifest_digest=input_manifest,
                    allowed_capabilities=tuple(task["capabilities"]),
                    read_set=tuple(task["read_set"]),
                    write_set=tuple(task["write_set"]),
                    output_schema=task["output_schema"],
                    expires_after_epoch=epoch,
                )
            )
            payload = (
                simulations[task["task_id"].split("::", 1)[1]]
                if task["phase"] == "ROUTE_SIMULATION"
                else reducer_payload
            )
            result = _result_envelope(
                run_id=run_id,
                plan=plan,
                task=task,
                lease=lease,
                input_manifest_digest=input_manifest,
                result_payload=payload,
            )
            errors = validate_task_result(
                plan,
                leases + [lease],
                result,
                run_id=run_id,
                logical_epoch=epoch,
                accepted_work_ids=accepted,
            )
            if errors:
                raise AgentReceiptError(
                    f"generated result failed validation: {errors}"
                )
            post_snapshot = (
                task["expected_result_digest"]
                if task["merge_authority"]
                else content_address(
                    "kc144.agent.merge-state",
                    {
                        "previous": current_snapshot,
                        "work_id": work_id,
                        "result_digest": result["result_digest"],
                    },
                )
            )
            receipt = _validation_receipt(
                result=result,
                decision="ACCEPTED",
                validation_errors=(),
                pre_merge_snapshot_digest=current_snapshot,
                post_merge_snapshot_digest=post_snapshot,
            )
            current_snapshot = post_snapshot
            accepted.add(work_id)
            leases.append(lease)
            results.append(result)
            receipts.append(receipt)

    events: list[dict[str, Any]] = []
    _append_event(
        events,
        run_id=run_id,
        logical_epoch=0,
        event_type="RUN_OPENED",
        subject_digest=root_input,
    )
    _append_event(
        events,
        run_id=run_id,
        logical_epoch=0,
        event_type="PLAN_VALIDATED",
        subject_digest=plan["plan_digest"],
    )
    _append_event(
        events,
        run_id=run_id,
        logical_epoch=0,
        event_type="CAPACITY_FIXED",
        subject_digest=content_address(
            "kc144.agent.capacity", {"capacity": plan["capacity"]}
        ),
    )
    receipt_by_work = {receipt["work_id"]: receipt for receipt in receipts}
    result_by_work = {result["work_id"]: result for result in results}
    lease_by_work = {lease["work_id"]: lease for lease in leases}
    for epoch, wave in enumerate(plan["execution_waves"]):
        _append_event(
            events,
            run_id=run_id,
            logical_epoch=epoch,
            event_type="EPOCH_OPENED",
            subject_digest=content_address(
                "kc144.agent.epoch", {"epoch": epoch, "wave": wave}
            ),
        )
        _append_event(
            events,
            run_id=run_id,
            logical_epoch=epoch,
            event_type="WAVE_SELECTED",
            subject_digest=content_address("kc144.agent.wave", wave),
        )
        for work_id in wave:
            lease = lease_by_work[work_id]
            result = result_by_work[work_id]
            receipt = receipt_by_work[work_id]
            common = {
                "run_id": run_id,
                "logical_epoch": epoch,
                "work_id": work_id,
                "attempt": 1,
                "lease_id": lease["lease_id"],
            }
            _append_event(
                events,
                **common,
                event_type="LEASE_GRANTED",
                subject_digest=lease["lease_id"],
            )
            _append_event(
                events,
                **common,
                event_type="RESULT_RECEIVED",
                subject_digest=result["result_digest"],
            )
            _append_event(
                events,
                **common,
                event_type="RESULT_ACCEPTED",
                subject_digest=receipt["receipt_digest"],
                decision="ACCEPTED",
            )
            _append_event(
                events,
                **common,
                event_type="SNAPSHOT_COMMITTED",
                subject_digest=receipt["post_merge_snapshot_digest"],
            )
    _append_event(
        events,
        run_id=run_id,
        logical_epoch=len(plan["execution_waves"]),
        event_type="RUN_COMPLETED",
        subject_digest=current_snapshot,
        decision="ACCEPTED",
    )

    manifest_body = {
        "schema": "KC144.AgentRunManifest.V1",
        "lookup_key": LOOKUP_KEY,
        "run_id": run_id,
        "plan_digest": plan["plan_digest"],
        "root_input_manifest_digest": root_input,
        "accepted_receipts": sorted(
            receipt["receipt_digest"] for receipt in receipts
        ),
        "quarantined_receipts": [],
        "terminal_task_states": {
            work_id: "ACCEPTED" for work_id in sorted(accepted)
        },
        "output_snapshot_digest": current_snapshot,
        "event_count": len(events),
        "audit_root": events[-1]["event_hash"],
        "executor_claim": "LOCAL_DETERMINISTIC_SIMULATION",
        "independent_witness_count": 0,
        "governance_authority_granted": False,
        "content_transport_certified": False,
        "truth_effect": "NONE",
    }
    manifest = {
        **manifest_body,
        "manifest_digest": content_address(
            "kc144.agent.run-manifest", manifest_body
        ),
    }
    from .tool_registry import agent_run_receipt_tool_descriptor

    body = {
        "schema": "KC144.AgentRunReceiptBundle.V1",
        "lookup_key": LOOKUP_KEY,
        "parent_lookup_key": PARENT_LOOKUP_KEY,
        "coordinate_binding": binding,
        "source_snapshot": {
            "schema": source["schema"],
            "lookup_key": source["lookup_key"],
            "crystal_digest": source["crystal_digest"],
        },
        "plan": plan,
        "leases": leases,
        "results": results,
        "receipts": receipts,
        "audit_events": events,
        "manifest": manifest,
        "tool_descriptor": agent_run_receipt_tool_descriptor(),
        "canonical_telemetry_exclusions": [
            "wall_clock_time",
            "provider_agent_id",
            "provider_session_id",
            "host_process_id",
            "physical_worker_count",
            "result_arrival_order",
        ],
        "base_graph_mutated": False,
        "content_transport_certified": False,
        "governance_authority_granted": False,
        "production_truth_effect": "NONE",
    }
    return {
        **body,
        "bundle_digest": content_address("kc144.agent.bundle", body),
    }


def verify_agent_run_receipts(
    bundle: Mapping[str, Any],
    *,
    source_crystal: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    errors: set[str] = set()
    if bundle.get("schema") != "KC144.AgentRunReceiptBundle.V1":
        errors.add("E_SCHEMA")
    plan = bundle.get("plan", {})
    if _address_body(
        "kc144.agent.plan", plan, "plan_digest"
    ) != plan.get("plan_digest"):
        errors.add("E_DIGEST_MISMATCH")
    registry = plan.get("task_registry", {})
    tasks = plan.get("tasks", [])
    if len(tasks) != len(set(tasks)) or set(tasks) != set(registry):
        errors.add("E_TASK_DUPLICATE")
    human_ids: list[str] = []
    scheduler_models: list[AgentTask] = []
    for work_id, task in registry.items():
        if _address_body("kc144.agent.task", task, "work_id") != work_id:
            errors.add("E_DIGEST_MISMATCH")
        human_ids.append(task.get("task_id", ""))
        if work_id in task.get("depends_on", []):
            errors.add("E_DEPENDENCY_SELF")
        if not set(task.get("depends_on", [])) <= set(registry):
            errors.add("E_DEPENDENCY_MISSING")
        for field in (
            "depends_on",
            "capabilities",
            "read_set",
            "write_set",
        ):
            values = task.get(field, [])
            if values != sorted(set(values)):
                errors.add("E_NONCANONICAL_SET")
        try:
            scheduler_models.append(
                AgentTask(
                    task_id=work_id,
                    execution_mode=task["execution_mode"],
                    depends_on=tuple(task["depends_on"]),
                    read_set=tuple(task["read_set"]),
                    write_set=tuple(task["write_set"]),
                    priority=task["priority"],
                    independent_agent_required=task[
                        "independent_agent_required"
                    ],
                )
            )
        except (KeyError, ParallelRouteError):
            errors.add("E_SCHEMA")
    if len(human_ids) != len(set(human_ids)):
        errors.add("E_TASK_DUPLICATE")
    try:
        expected_waves = compile_execution_waves(
            scheduler_models,
            worker_capacity=plan.get("capacity", 0),
        )
    except ParallelRouteError as exc:
        expected_waves = []
        errors.add(
            "E_DEPENDENCY_CYCLE"
            if "cycle" in str(exc)
            else "E_WAVE_MISMATCH"
        )
    if plan.get("execution_waves") != expected_waves:
        errors.add("E_WAVE_MISMATCH")
    if plan.get("merge_order") != [
        work_id for wave in expected_waves for work_id in wave
    ]:
        errors.add("E_MERGE_ORDER_MISMATCH")
    if tasks != plan.get("merge_order"):
        errors.add("E_MERGE_ORDER_MISMATCH")

    root_input = bundle.get("manifest", {}).get(
        "root_input_manifest_digest", ""
    )
    if plan and root_input != _root_input_manifest(plan):
        errors.add("E_INPUT_BINDING")
    expected_run_id = _run_id(plan, root_input) if plan else ""
    run_id = bundle.get("manifest", {}).get("run_id")
    if run_id != expected_run_id:
        errors.add("E_RUN_BINDING")

    leases = bundle.get("leases", [])
    lease_ids: set[str] = set()
    current_attempt: dict[str, int] = {}
    for lease in leases:
        lease_id = lease.get("lease_id")
        if _address_body(
            "kc144.agent.lease", lease, "lease_id"
        ) != lease_id:
            errors.add("E_DIGEST_MISMATCH")
        if lease_id in lease_ids:
            errors.add("E_LEASE_DUPLICATE_LIVE")
        lease_ids.add(lease_id)
        work_id = lease.get("work_id", "")
        attempt = lease.get("attempt", 0)
        task = registry.get(work_id)
        if task is None:
            errors.add("E_TASK_BINDING")
        else:
            expected_input = _task_input_manifest(plan, work_id, root_input)
            if lease.get("input_manifest_digest") != expected_input:
                errors.add("E_INPUT_BINDING")
            for field in ("task_id", "read_set", "write_set", "output_schema"):
                expected_value = task.get(field)
                if lease.get(field) != expected_value:
                    errors.add("E_TASK_BINDING")
            if lease.get("allowed_capabilities") != task.get("capabilities"):
                errors.add("E_TASK_BINDING")
            if lease.get("logical_epoch") >= len(
                plan.get("execution_waves", [])
            ):
                errors.add("E_WAVE_MISMATCH")
            else:
                wave = plan["execution_waves"][lease["logical_epoch"]]
                if (
                    lease.get("logical_slot") >= len(wave)
                    or wave[lease["logical_slot"]] != work_id
                ):
                    errors.add("E_WAVE_MISMATCH")
        current_attempt[work_id] = max(current_attempt.get(work_id, 0), attempt)
    if [lease.get("work_id") for lease in leases] != plan.get("merge_order"):
        errors.add("E_MERGE_ORDER_MISMATCH")

    accepted: set[str] = set()
    result_by_work: dict[str, Mapping[str, Any]] = {}
    for result in bundle.get("results", []):
        result_by_work[result.get("work_id", "")] = result
        result_errors = validate_task_result(
            plan,
            leases,
            result,
            run_id=run_id,
            logical_epoch=next(
                (
                    lease["logical_epoch"]
                    for lease in leases
                    if lease["lease_id"] == result.get("lease_id")
                ),
                0,
            ),
            accepted_work_ids=(),
        )
        errors.update(result_errors)
    if [result.get("work_id") for result in bundle.get("results", [])] != plan.get(
        "merge_order"
    ):
        errors.add("E_MERGE_ORDER_MISMATCH")

    receipt_ids: set[str] = set()
    receipt_by_work: dict[str, Mapping[str, Any]] = {}
    for receipt in bundle.get("receipts", []):
        if _address_body(
            "kc144.agent.receipt", receipt, "receipt_digest"
        ) != receipt.get("receipt_digest"):
            errors.add("E_DIGEST_MISMATCH")
        receipt_ids.add(receipt.get("receipt_digest", ""))
        receipt_by_work[receipt.get("work_id", "")] = receipt
        if receipt.get("decision") == "ACCEPTED":
            accepted.add(receipt.get("work_id", ""))
        result = result_by_work.get(receipt.get("work_id", ""))
        if result is None or receipt.get("result_digest") != result.get(
            "result_digest"
        ):
            errors.add("E_MANIFEST_BINDING")
    if [
        receipt.get("work_id") for receipt in bundle.get("receipts", [])
    ] != plan.get("merge_order"):
        errors.add("E_MERGE_ORDER_MISMATCH")
    if accepted != set(registry):
        errors.add("E_MANIFEST_BINDING")

    events = bundle.get("audit_events", [])
    previous = ZERO_DIGEST
    for sequence, event in enumerate(events):
        if event.get("sequence") != sequence:
            errors.add("E_EVENT_SEQUENCE")
        if event.get("previous_event_hash") != previous:
            errors.add("E_EVENT_PREVIOUS_HASH")
        expected = _address_body(
            "kc144.agent.event", event, "event_hash"
        )
        if event.get("event_hash") != expected:
            errors.add("E_EVENT_HASH")
        previous = event.get("event_hash", "")
    if not events or events[-1].get("event_type") != "RUN_COMPLETED":
        errors.add("E_EVENT_STATE_TRANSITION")
    expected_timeline: list[tuple[str, int, str | None, str | None]] = [
        ("RUN_OPENED", 0, None, None),
        ("PLAN_VALIDATED", 0, None, None),
        ("CAPACITY_FIXED", 0, None, None),
    ]
    for epoch, wave in enumerate(plan.get("execution_waves", [])):
        expected_timeline.extend(
            [
                ("EPOCH_OPENED", epoch, None, None),
                ("WAVE_SELECTED", epoch, None, None),
            ]
        )
        for work_id in wave:
            lease_id = next(
                (
                    lease["lease_id"]
                    for lease in leases
                    if lease.get("work_id") == work_id
                ),
                None,
            )
            expected_timeline.extend(
                [
                    ("LEASE_GRANTED", epoch, work_id, lease_id),
                    ("RESULT_RECEIVED", epoch, work_id, lease_id),
                    ("RESULT_ACCEPTED", epoch, work_id, lease_id),
                    ("SNAPSHOT_COMMITTED", epoch, work_id, lease_id),
                ]
            )
    expected_timeline.append(
        ("RUN_COMPLETED", len(plan.get("execution_waves", [])), None, None)
    )
    actual_timeline = [
        (
            event.get("event_type"),
            event.get("logical_epoch"),
            event.get("work_id"),
            event.get("lease_id"),
        )
        for event in events
    ]
    if actual_timeline != expected_timeline:
        errors.add("E_EVENT_STATE_TRANSITION")

    manifest = bundle.get("manifest", {})
    if _address_body(
        "kc144.agent.run-manifest", manifest, "manifest_digest"
    ) != manifest.get("manifest_digest"):
        errors.add("E_DIGEST_MISMATCH")
    if manifest.get("accepted_receipts") != sorted(receipt_ids):
        errors.add("E_MANIFEST_BINDING")
    if manifest.get("event_count") != len(events):
        errors.add("E_MANIFEST_BINDING")
    if manifest.get("audit_root") != previous:
        errors.add("E_AUDIT_ROOT")
    if manifest.get("terminal_task_states") != {
        work_id: "ACCEPTED" for work_id in sorted(registry)
    }:
        errors.add("E_MANIFEST_BINDING")
    if manifest.get("output_snapshot_digest") != plan.get(
        "input_snapshot_digest"
    ):
        errors.add("E_MANIFEST_BINDING")
    source_snapshot = bundle.get("source_snapshot", {})
    if (
        source_snapshot.get("crystal_digest")
        != plan.get("input_snapshot_digest")
        or source_snapshot.get("lookup_key") != PARENT_LOOKUP_KEY
    ):
        errors.add("E_INPUT_BINDING")
    if bundle.get("coordinate_binding") != plan.get("receipt_runtime"):
        errors.add("E_RUN_BINDING")
    descriptor = bundle.get("tool_descriptor", {})
    if _address_body(
        "kc144.mycelium.tool-descriptor",
        descriptor,
        "descriptor_digest",
    ) != descriptor.get("descriptor_digest"):
        errors.add("E_DIGEST_MISMATCH")

    if source_crystal is not None:
        try:
            _source_crystal_integrity(source_crystal)
        except AgentReceiptError:
            errors.add("E_DIGEST_MISMATCH")
        if source_crystal.get("crystal_digest") != plan.get(
            "input_snapshot_digest"
        ):
            errors.add("E_INPUT_BINDING")
        expected_outputs = {
            f"SIMULATE::{row['route_id']}": row["simulation_digest"]
            for row in source_crystal.get("simulations", [])
        }
        expected_outputs["INTEGRATE::PARALLEL_ROUTE_CRYSTAL"] = (
            source_crystal.get("crystal_digest")
        )
        for task in registry.values():
            if expected_outputs.get(task["task_id"]) != task.get(
                "expected_result_digest"
            ):
                errors.add("E_ARTIFACT_DIGEST")

    if any(
        (
            bundle.get("content_transport_certified") is not False,
            bundle.get("governance_authority_granted") is not False,
            bundle.get("production_truth_effect") != "NONE",
            manifest.get("content_transport_certified") is not False,
            manifest.get("governance_authority_granted") is not False,
            manifest.get("truth_effect") != "NONE",
            manifest.get("independent_witness_count") != 0,
        )
    ):
        errors.add("E_AUTHORITY_ESCALATION")
    if _address_body(
        "kc144.agent.bundle", bundle, "bundle_digest"
    ) != bundle.get("bundle_digest"):
        errors.add("E_DIGEST_MISMATCH")
    return {
        "schema": "KC144.AgentRunVerification.V1",
        "lookup_key": LOOKUP_KEY,
        "verdict": "PASS" if not errors else "FAIL",
        "errors": sorted(errors),
        "run_id": run_id,
        "plan_digest": plan.get("plan_digest"),
        "manifest_digest": manifest.get("manifest_digest"),
        "audit_root": manifest.get("audit_root"),
        "task_count": len(registry),
        "accepted_receipt_count": len(receipt_ids),
        "independent_witness_count": manifest.get("independent_witness_count"),
        "content_transport_certified": False,
        "governance_authority_granted": False,
        "truth_effect": "NONE",
    }


def agent_run_receipt_contract() -> dict[str, Any]:
    body = {
        "schema": "KC144.AgentRunReceiptContract.V1",
        "lookup_key": LOOKUP_KEY,
        "parent_lookup_key": PARENT_LOOKUP_KEY,
        "identity_graph": [
            "TASK_WORK_ID",
            "PLAN_DIGEST",
            "INPUT_MANIFEST_DIGEST",
            "RUN_ID",
            "LEASE_ID",
            "RESULT_DIGEST",
            "RECEIPT_DIGEST",
            "EVENT_HASH_CHAIN",
            "MANIFEST_DIGEST",
            "BUNDLE_DIGEST",
        ],
        "maximum_parallel_width": 5,
        "canonical_order": "DEPENDENCY_WAVE_THEN_PLAN_MERGE_ORDER",
        "telemetry_excluded_from_identity": True,
        "late_or_superseded_results": "QUARANTINE_ONLY",
        "retryable_error_codes": list(RETRYABLE_ERROR_CODES),
        "local_fallback_independent_witness_effect": "ZERO",
        "base_graph_mutated": False,
        "content_transport_certified": False,
        "governance_authority_granted": False,
        "truth_effect": "NONE",
    }
    return {
        **body,
        "contract_digest": content_address(
            "kc144.agent.receipt-contract", body
        ),
    }
