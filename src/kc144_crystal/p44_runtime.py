from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .agent_receipts import canonical_bytes, content_address
from .p39_runtime import GIT_SHA_RE
from .p43_runtime import (
    P43_NEXT_SEED,
    compile_p43_cycle,
    verify_p43_cycle,
)


P44_LOOKUP_KEY = P43_NEXT_SEED
P44_NEXT_SEED = (
    "KC144.V4.6::MATH144.P45::ADMIT_CANONICAL_EDGE_EFFECT_RECEIPT_"
    "ACCUMULATE_SECOND_FORWARD_OUTCOME_WINDOW_COMPARE_ROUTE_AND_SURFACE_"
    "STABILITY_AND_DECIDE_REVERSIBLE_EDGE_RETENTION_MACROCYCLE_14"
)
P44_FREEZE = "2026-07-28T10:30:00.000000Z"
P44_ROUTE = (
    "KC144.V1::GID084::I04",
    "KC144.V1::GID047::F04",
    "KC144.V1::GID141::M09",
    "KC144.V1::GID090::IC10",
    "KC144.V1::GID144::M12",
)
P44_LANES = (
    "PUBLIC_P43_PARENT_BIND",
    "EXACTLY_ONCE_LEDGER_FINALITY_BIND",
    "FORWARD_POST_EDGE_OUTCOME_INTAKE",
    "CAUSAL_NONREUSE_FILTER",
    "ROUTE_DIVERSITY_FREEZE",
    "NONDEGRADATION_MEASUREMENT",
    "CANONICAL_EDGE_EFFECT_FREEZE_OR_HOLD",
    "EDGE_EFFECT_REPLAY_AND_TAMPER_AUDIT",
    "PARALLEL_P44_NONCOLLAPSE",
    "M12_RETURN_AND_P45_RESEED",
)

PUBLIC_P43_RESULT_ID = "KC144.P43.CANDIDATE::240473a1935faad593c1b8d5"
PUBLIC_P43_RELEASE_DIGEST = (
    "sha256:240473a1935faad593c1b8d5ea74b7171cac43bfac63ad597e0161238c424aa2"
)
PUBLIC_P43_RELEASE_COMMIT = "9a8818825697dd6501ed5286503018fd1d0a7466"
PUBLIC_P43_RELEASE_TREE = "31583ff01a91175093f969283c61106a55ac2455"


class P44RuntimeError(ValueError):
    pass


def p44_public_parent() -> dict[str, Any]:
    body = {
        "schema": "KC144.P44.PublicParentBinding.V1",
        "result_id": PUBLIC_P43_RESULT_ID,
        "release_digest": PUBLIC_P43_RELEASE_DIGEST,
        "release_commit": PUBLIC_P43_RELEASE_COMMIT,
        "release_tree": PUBLIC_P43_RELEASE_TREE,
        "relation": "EXACT_PUBLIC_PARENT",
    }
    return {**body, "binding_digest": content_address("kc144.p44.parent", body)}


def p44_parallel_lineage() -> dict[str, Any]:
    body = {
        "schema": "KC144.P44.ParallelLineage.V1",
        "parallel_label": "ATHENA_GIT_BRAIN_V2.P44",
        "relation": "PARALLEL_LABEL_COLLISION_NOT_PARENT_NOT_MERGED",
        "private_semantic_role": "PRESERVED_OPAQUE_NOT_INFERRED",
        "private_locator_published": False,
        "private_receipt_embedded": False,
        "merge_executed": False,
        "truth_effect": "NONE",
    }
    return {**body, "lineage_digest": content_address("kc144.p44.parallel", body)}


def p44_contract() -> dict[str, Any]:
    body = {
        "schema": "KC144.P44.Contract.V1",
        "lookup_key": P44_LOOKUP_KEY,
        "public_parent": p44_public_parent(),
        "route": list(P44_ROUTE),
        "lanes": [
            {
                "lane_id": f"P44.L{index:02d}",
                "lane": lane,
                "parallel_group": 1 if index <= 4 else 2 if index <= 8 else 3,
                "return": P44_ROUTE[-1],
            }
            for index, lane in enumerate(P44_LANES, 1)
        ],
        "forward_window_law": (
            "AT_LEAST_FIVE_STRICTLY_POST_EXECUTION_NONREUSED_TASK_OR_EMPIRICAL_"
            "OUTCOMES_ACROSS_THREE_ROUTES_AND_TWO_EVENT_TYPES"
        ),
        "measurement_law": (
            "MEAN_CANDIDATE_SCORE_MUST_NOT_BE_BELOW_MEAN_BASELINE_SCORE_AND_AT_"
            "LEAST_THREE_EVENTS_MUST_BE_NONDEGRADING"
        ),
        "freeze_law": (
            "CANONICAL_EDGE_EFFECT_FREEZES_ONLY_AFTER_EXACTLY_ONCE_FINALITY_"
            "FORWARD_WATCH_AND_ROUTE_DIVERSE_NONDEGRADATION_ALL_PASS"
        ),
        "noncollapse": [
            "CONTINUATION_IS_NOT_FORWARD_OUTCOME",
            "TEST_FIXTURE_IS_NOT_EXTERNAL_EVIDENCE",
            "EDGE_EFFECT_IS_NOT_PROPOSITION_TRUTH",
            "NONDEGRADATION_IS_NOT_GENERAL_OPTIMALITY",
            "FROZEN_EFFECT_IS_NOT_MODEL_WEIGHT_AUTHORITY",
            "PARALLEL_P44_LABEL_IS_NOT_THIS_PUBLIC_LINEAGE",
        ],
        "default_state": "HOLD_PARENT_FINALITY_AND_FORWARD_OUTCOMES_ABSENT",
        "next_seed": P44_NEXT_SEED,
    }
    return {**body, "contract_digest": content_address("kc144.p44.contract", body)}


def _validate_forward_events(
    events: Sequence[Mapping[str, Any]],
    *,
    cutoff: str | None,
    authorization_event_ids: set[str],
) -> dict[str, Any]:
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    seen: set[str] = set()
    for value in events:
        row = dict(value)
        event_id = str(row.get("event_id", ""))
        reason = ""
        if not cutoff:
            reason = "PARENT_EXECUTION_ABSENT"
        elif not event_id or event_id in seen:
            reason = "DUPLICATE_OR_EMPTY_EVENT_ID"
        elif event_id in authorization_event_ids:
            reason = "AUTHORIZATION_COHORT_REUSE"
        elif str(row.get("observed_at", "")) <= cutoff:
            reason = "NOT_STRICTLY_FORWARD"
        elif row.get("outcome_class") not in {"TASK_OUTCOME", "EMPIRICAL_RESULT"}:
            reason = "INELIGIBLE_EVENT_CLASS"
        elif row.get("continuation_only") is not False:
            reason = "CONTINUATION_ONLY"
        elif not isinstance(row.get("baseline_score"), (int, float)):
            reason = "BASELINE_SCORE_MISSING"
        elif not isinstance(row.get("candidate_score"), (int, float)):
            reason = "CANDIDATE_SCORE_MISSING"
        elif not str(row.get("route_id", "")):
            reason = "ROUTE_MISSING"
        if reason:
            rejected.append({"event_id": event_id, "reason": reason})
        else:
            accepted.append(row)
            seen.add(event_id)
    accepted.sort(key=lambda row: (str(row["observed_at"]), str(row["event_id"])))
    rejected.sort(key=lambda row: (row["reason"], row["event_id"]))
    body = {
        "schema": "KC144.P44.ForwardOutcomeWindow.V1",
        "execution_cutoff": cutoff,
        "events": accepted,
        "event_count": len(accepted),
        "required_event_count": 5,
        "event_type_count": len({row["outcome_class"] for row in accepted}),
        "route_count": len({row["route_id"] for row in accepted}),
        "rejected": rejected,
        "authorization_events_reused": 0,
        "continuation_events_admitted": 0,
        "status": (
            "WINDOW_READY"
            if len(accepted) >= 5
            and len({row["outcome_class"] for row in accepted}) >= 2
            and len({row["route_id"] for row in accepted}) >= 3
            else "HOLD"
        ),
        "truth_effect": "NONE",
    }
    return {**body, "window_digest": content_address("kc144.p44.window", body)}


def _measure_non_degradation(window: Mapping[str, Any]) -> dict[str, Any]:
    rows = list(window.get("events", []))
    baseline_mean = (
        sum(float(row["baseline_score"]) for row in rows) / len(rows)
        if rows else None
    )
    candidate_mean = (
        sum(float(row["candidate_score"]) for row in rows) / len(rows)
        if rows else None
    )
    nondegrading = sum(
        float(row["candidate_score"]) >= float(row["baseline_score"])
        for row in rows
    )
    pass_gate = (
        window.get("status") == "WINDOW_READY"
        and baseline_mean is not None
        and candidate_mean is not None
        and candidate_mean >= baseline_mean
        and nondegrading >= 3
    )
    per_route = []
    for route in sorted({str(row["route_id"]) for row in rows}):
        route_rows = [row for row in rows if row["route_id"] == route]
        per_route.append(
            {
                "route_id": route,
                "event_count": len(route_rows),
                "baseline_mean": sum(
                    float(row["baseline_score"]) for row in route_rows
                ) / len(route_rows),
                "candidate_mean": sum(
                    float(row["candidate_score"]) for row in route_rows
                ) / len(route_rows),
            }
        )
    body = {
        "schema": "KC144.P44.NondegradationMeasurement.V1",
        "window_digest": window["window_digest"],
        "baseline_mean": baseline_mean,
        "candidate_mean": candidate_mean,
        "nondegrading_event_count": nondegrading,
        "required_nondegrading_events": 3,
        "per_route": per_route,
        "status": "PASS_NONDEGRADING" if pass_gate else "HOLD",
        "claim_ceiling": "FINITE_FORWARD_WINDOW_ONLY",
        "truth_effect": "NONE",
    }
    return {
        **body,
        "measurement_digest": content_address("kc144.p44.measurement", body),
    }


def compile_p44_cycle(
    *,
    p43_cycle: Mapping[str, Any] | None = None,
    forward_events: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    parent_cycle = dict(p43_cycle or compile_p43_cycle())
    parent_verification = verify_p43_cycle(parent_cycle)
    transaction = parent_cycle.get("p42_transaction_cycle", {}).get(
        "edge_transaction", {}
    )
    record = transaction.get("execution_record") or {}
    authorization_ids = {
        str(row.get("event_id"))
        for row in transaction.get("candidate", {}).get("heldout_events", [])
    }
    finality_ready = (
        parent_verification["verdict"] == "PASS"
        and parent_cycle.get("transaction_finality", {}).get(
            "exactly_once_final"
        )
        is True
        and transaction.get("execution_count_after") == 1
        and transaction.get("ledger_valid") is True
    )
    window = _validate_forward_events(
        forward_events,
        cutoff=record.get("executed_at"),
        authorization_event_ids=authorization_ids,
    )
    measurement = _measure_non_degradation(window)
    eligible = (
        finality_ready
        and parent_cycle.get("post_edge_watch", {}).get("status") == "ARMED"
        and measurement["status"] == "PASS_NONDEGRADING"
    )
    effect_body = {
        "schema": "KC144.P44.CanonicalEdgeEffect.V1",
        "edge_id": "P41.EDGE.003",
        "parent_p43_envelope": parent_cycle.get("envelope_digest"),
        "execution_record_digest": record.get("record_digest"),
        "window_digest": window["window_digest"],
        "measurement_digest": measurement["measurement_digest"],
        "status": "FROZEN_CANONICAL_EDGE_EFFECT" if eligible else "HOLD",
        "effect_scope": "FINITE_FORWARD_OUTCOME_WINDOW",
        "route_priority_delta_authorized": False,
        "model_weight_mutation_authorized": False,
        "truth_effect": "NONE",
        "authority_effect": "NONE",
    }
    effect = {
        **effect_body,
        "effect_digest": content_address("kc144.p44.edge-effect", effect_body),
    }
    residuals = []
    if not finality_ready:
        residuals.append("P43_EXACTLY_ONCE_FINALITY_PENDING")
    if window["status"] != "WINDOW_READY":
        residuals.append("FORWARD_ROUTE_DIVERSE_OUTCOME_WINDOW_PENDING")
    if measurement["status"] != "PASS_NONDEGRADING":
        residuals.append("NONDEGRADATION_PENDING")
    if effect["status"] != "FROZEN_CANONICAL_EDGE_EFFECT":
        residuals.append("CANONICAL_EDGE_EFFECT_NOT_FROZEN")
    state = {
        "schema": "KC144.P44.StateDelta.V1",
        "public_parent_result_id": PUBLIC_P43_RESULT_ID,
        "parent_finality_ready": finality_ready,
        "forward_outcomes": window["event_count"],
        "forward_routes": window["route_count"],
        "nondegradation": measurement["status"],
        "canonical_edge_effect": effect["status"],
        "edge_execution_count": transaction.get("execution_count_after", 0),
        "canonical_graph_mutations": 0,
        "parallel_p44_merges": 0,
        "production_authority": "HOLD",
        "truth_effect": "NONE",
        "residuals": sorted(residuals),
        "return": P44_ROUTE[-1],
        "next_seed": P44_NEXT_SEED,
    }
    state["delta_id"] = content_address("kc144.p44.state", state)
    payloads = (
        p44_public_parent(),
        parent_cycle.get("transaction_finality", {}),
        window,
        {"rejected": window["rejected"]},
        {"route_count": window["route_count"]},
        measurement,
        effect,
        {"parent_verification": parent_verification},
        p44_parallel_lineage(),
        state,
    )
    receipts = []
    for index, (lane, payload) in enumerate(zip(P44_LANES, payloads), 1):
        receipt = {
            "schema": "KC144.P44.LaneReceipt.V1",
            "lane_id": f"P44.L{index:02d}",
            "lane": lane,
            "payload_digest": content_address(
                f"kc144.p44.lane.{lane.lower()}", payload
            ),
            "return": P44_ROUTE[-1],
            "truth_effect": "NONE",
        }
        receipt["receipt_id"] = content_address("kc144.p44.lane-receipt", receipt)
        receipts.append(receipt)
    body = {
        "schema": "KC144.P44.Macrocycle.V1",
        "contract_digest": p44_contract()["contract_digest"],
        "public_parent_binding": p44_public_parent(),
        "p43_cycle": parent_cycle,
        "forward_events": [dict(row) for row in forward_events],
        "forward_window": window,
        "nondegradation_measurement": measurement,
        "canonical_edge_effect": effect,
        "parallel_lineage": p44_parallel_lineage(),
        "lane_receipts": receipts,
        "state": state,
    }
    return {**body, "envelope_digest": content_address("kc144.p44.cycle", body)}


def verify_p44_cycle(value: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    try:
        replay = compile_p44_cycle(
            p43_cycle=value.get("p43_cycle"),
            forward_events=value.get("forward_events", []),
        )
    except Exception as error:
        replay = {}
        errors.append(f"REPLAY_EXCEPTION:{type(error).__name__}")
    if replay.get("envelope_digest") != value.get("envelope_digest"):
        errors.append("REPLAY_DRIFT")
    if value.get("public_parent_binding") != p44_public_parent():
        errors.append("PUBLIC_PARENT")
    if len(value.get("lane_receipts", [])) != len(P44_LANES):
        errors.append("LANE_COUNT")
    if value.get("state", {}).get("truth_effect") != "NONE":
        errors.append("TRUTH_INFLATION")
    body = {
        "schema": "KC144.P44.Verification.V1",
        "verdict": "PASS" if not errors else "FAIL",
        "errors": sorted(errors),
        "replay_envelope_digest": replay.get("envelope_digest"),
        "production_authority": "HOLD",
        "truth_effect": "NONE",
    }
    return {**body, "verification_digest": content_address("kc144.p44.verify", body)}


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_bytes(canonical_bytes(value) + b"\n")


def compile_p44_release(
    output: str | Path,
    *,
    implementation_commit: str,
    implementation_tree: str,
) -> dict[str, Any]:
    if not GIT_SHA_RE.fullmatch(implementation_commit):
        raise P44RuntimeError("implementation commit must be a Git SHA")
    if not GIT_SHA_RE.fullmatch(implementation_tree):
        raise P44RuntimeError("implementation tree must be a Git SHA")
    destination = Path(output)
    destination.mkdir(parents=True, exist_ok=True)
    cycle = compile_p44_cycle()
    verification = verify_p44_cycle(cycle)
    body = {
        "schema": "KC144.P44.Release.V1",
        "release_id": "KC144_P44_EDGE_EFFECT_CANDIDATE_V1",
        "implementation": {
            "repository": "demeet2k/guild-hall",
            "commit": implementation_commit,
            "tree": implementation_tree,
        },
        "public_parent_result_id": PUBLIC_P43_RESULT_ID,
        "public_parent_release_digest": PUBLIC_P43_RELEASE_DIGEST,
        "status": "CANDIDATE_HOLD",
        "parent_finality_ready": False,
        "forward_outcomes": 0,
        "forward_routes": 0,
        "nondegradation": "HOLD",
        "canonical_edge_effect": "HOLD",
        "edge_execution_count": 0,
        "canonical_graph_mutations": 0,
        "production_authority": "HOLD",
        "truth_effect": "NONE",
        "verification_verdict": verification["verdict"],
        "next_seed": P44_NEXT_SEED,
    }
    digest = content_address("kc144.p44.release", body)
    release = {
        **body,
        "release_digest": digest,
        "result_id": "KC144.P44.CANDIDATE::" + digest.split(":", 1)[1][:24],
    }
    artifacts = {
        "p44_contract_v1.json": p44_contract(),
        "p44_macrocycle_v1.json": cycle,
        "p44_forward_window_v1.json": cycle["forward_window"],
        "p44_nondegradation_v1.json": cycle["nondegradation_measurement"],
        "p44_edge_effect_v1.json": cycle["canonical_edge_effect"],
        "p44_parallel_lineage_v1.json": cycle["parallel_lineage"],
        "p44_verification_v1.json": verification,
        "p44_release_v1.json": release,
    }
    for name, value in artifacts.items():
        _write_json(destination / name, value)
    sums = [
        f"{hashlib.sha256((destination / name).read_bytes()).hexdigest()}  {name}"
        for name in sorted(artifacts)
    ]
    (destination / "SHA256SUMS").write_text(
        "\n".join(sums) + "\n", encoding="utf-8"
    )
    return release
