from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .agent_receipts import canonical_bytes, content_address
from .p39_runtime import GIT_SHA_RE
from .p44_runtime import P44_NEXT_SEED, compile_p44_cycle, verify_p44_cycle


P45_LOOKUP_KEY = P44_NEXT_SEED
P45_NEXT_SEED = (
    "KC144.V4.7::MATH144.P46::ADMIT_REVERSIBLE_EDGE_RETENTION_DECISION_"
    "ACCUMULATE_THIRD_FORWARD_WINDOW_VERIFY_TEMPORAL_STABILITY_AND_RECEIVE_"
    "INDEPENDENT_IC10_CANONICALIZATION_AUTHORIZATION_MACROCYCLE_15"
)
P45_ROUTE = (
    "KC144.V1::GID084::I04",
    "KC144.V1::GID047::F04",
    "KC144.V1::GID005::H05",
    "KC144.V1::GID141::M09",
    "KC144.V1::GID090::IC10",
    "KC144.V1::GID144::M12",
)
P45_LANES = (
    "PUBLIC_P44_PARENT_BIND",
    "CANONICAL_EDGE_EFFECT_ADMISSION",
    "SECOND_FORWARD_OUTCOME_INTAKE",
    "CROSS_WINDOW_CAUSAL_NONREUSE",
    "ROUTE_STABILITY_COMPARISON",
    "SURFACE_STABILITY_COMPARISON",
    "SECOND_WINDOW_NONDEGRADATION",
    "REVERSIBLE_EDGE_RETENTION_DECISION",
    "PARALLEL_P45_NONCOLLAPSE",
    "M12_RETURN_AND_P46_RESEED",
)

PUBLIC_P44_RESULT_ID = "KC144.P44.CANDIDATE::1073b6a2be78da5a66b068e2"
PUBLIC_P44_RELEASE_DIGEST = (
    "sha256:1073b6a2be78da5a66b068e2da8f23dccb0a0e4d6c01a0ab3f042fd55649e6fb"
)
PUBLIC_P44_RELEASE_COMMIT = "1022d7735c38c5557fbaadfeba7aeb5e6aef4a0c"
PUBLIC_P44_RELEASE_TREE = "068e950092013d5a4f74db4a027da0838a58c345"


class P45RuntimeError(ValueError):
    pass


def p45_public_parent() -> dict[str, Any]:
    body = {
        "schema": "KC144.P45.PublicParentBinding.V1",
        "result_id": PUBLIC_P44_RESULT_ID,
        "release_digest": PUBLIC_P44_RELEASE_DIGEST,
        "release_commit": PUBLIC_P44_RELEASE_COMMIT,
        "release_tree": PUBLIC_P44_RELEASE_TREE,
        "relation": "EXACT_PUBLIC_PARENT",
    }
    return {**body, "binding_digest": content_address("kc144.p45.parent", body)}


def p45_parallel_lineage() -> dict[str, Any]:
    body = {
        "schema": "KC144.P45.ParallelLineage.V1",
        "parallel_label": "ATHENA_GIT_BRAIN_V2.P45",
        "relation": "PARALLEL_LABEL_COLLISION_NOT_PARENT_NOT_MERGED",
        "private_semantic_role": "PRESERVED_OPAQUE_NOT_INFERRED",
        "private_locator_published": False,
        "private_receipt_embedded": False,
        "merge_executed": False,
        "truth_effect": "NONE",
    }
    return {**body, "lineage_digest": content_address("kc144.p45.parallel", body)}


def p45_contract() -> dict[str, Any]:
    body = {
        "schema": "KC144.P45.Contract.V1",
        "lookup_key": P45_LOOKUP_KEY,
        "public_parent": p45_public_parent(),
        "route": list(P45_ROUTE),
        "lanes": [
            {
                "lane_id": f"P45.L{index:02d}",
                "lane": lane,
                "parallel_group": 1 if index <= 4 else 2 if index <= 8 else 3,
                "return": P45_ROUTE[-1],
            }
            for index, lane in enumerate(P45_LANES, 1)
        ],
        "second_window_law": (
            "AT_LEAST_FIVE_STRICTLY_LATER_NONREUSED_OUTCOMES_ACROSS_THREE_"
            "ROUTES_THREE_SURFACES_AND_TWO_EVENT_TYPES"
        ),
        "stability_law": (
            "ALL_FIRST_WINDOW_ROUTES_AND_SURFACES_MUST_REAPPEAR_AND_EACH_"
            "MEAN_EFFECT_DRIFT_MUST_NOT_EXCEED_0.15"
        ),
        "decision_law": (
            "RETAIN_REVERSIBLY_ONLY_AFTER_FROZEN_P44_EFFECT_SECOND_WINDOW_"
            "NONDEGRADATION_AND_ROUTE_AND_SURFACE_STABILITY; COMPLETE_MEASURED_"
            "DEGRADATION_OR_INSTABILITY_RETRACTS_THE_PROPOSAL; INCOMPLETE_INPUT_HOLDS"
        ),
        "noncollapse": [
            "RETENTION_DECISION_IS_NOT_GRAPH_MUTATION",
            "RETRACTION_PROPOSAL_IS_NOT_RETROACTIVE_ERASURE",
            "TWO_WINDOWS_ARE_NOT_GENERAL_OPTIMALITY",
            "STABILITY_IS_NOT_PROPOSITION_TRUTH",
            "IC10_REVIEW_LOCATION_IS_NOT_IC10_AUTHORIZATION",
            "PARALLEL_P45_LABEL_IS_NOT_THIS_PUBLIC_LINEAGE",
        ],
        "default_state": "HOLD_P44_EDGE_EFFECT_AND_SECOND_WINDOW_ABSENT",
        "next_seed": P45_NEXT_SEED,
    }
    return {**body, "contract_digest": content_address("kc144.p45.contract", body)}


def _second_window(
    events: Sequence[Mapping[str, Any]],
    *,
    first_events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    first_ids = {str(row.get("event_id", "")) for row in first_events}
    cutoff = max((str(row.get("observed_at", "")) for row in first_events), default=None)
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    seen: set[str] = set()
    for value in events:
        row = dict(value)
        event_id = str(row.get("event_id", ""))
        reason = ""
        if not cutoff:
            reason = "FIRST_WINDOW_ABSENT"
        elif not event_id or event_id in seen:
            reason = "DUPLICATE_OR_EMPTY_EVENT_ID"
        elif event_id in first_ids:
            reason = "FIRST_WINDOW_REUSE"
        elif str(row.get("observed_at", "")) <= cutoff:
            reason = "NOT_STRICTLY_AFTER_FIRST_WINDOW"
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
        elif not str(row.get("source_surface", "")):
            reason = "SURFACE_MISSING"
        if reason:
            rejected.append({"event_id": event_id, "reason": reason})
        else:
            accepted.append(row)
            seen.add(event_id)
    accepted.sort(key=lambda row: (str(row["observed_at"]), str(row["event_id"])))
    route_count = len({str(row["route_id"]) for row in accepted})
    surface_count = len({str(row["source_surface"]) for row in accepted})
    event_type_count = len({str(row["outcome_class"]) for row in accepted})
    body = {
        "schema": "KC144.P45.SecondForwardWindow.V1",
        "first_window_cutoff": cutoff,
        "events": accepted,
        "event_count": len(accepted),
        "required_event_count": 5,
        "route_count": route_count,
        "required_route_count": 3,
        "surface_count": surface_count,
        "required_surface_count": 3,
        "event_type_count": event_type_count,
        "rejected": sorted(rejected, key=lambda row: (row["reason"], row["event_id"])),
        "first_window_events_reused": 0,
        "status": (
            "WINDOW_READY"
            if len(accepted) >= 5
            and route_count >= 3
            and surface_count >= 3
            and event_type_count >= 2
            else "HOLD"
        ),
        "truth_effect": "NONE",
    }
    return {**body, "window_digest": content_address("kc144.p45.window", body)}


def _effect_mean(rows: Sequence[Mapping[str, Any]]) -> float | None:
    if not rows:
        return None
    return sum(
        float(row["candidate_score"]) - float(row["baseline_score"]) for row in rows
    ) / len(rows)


def _compare_dimension(
    first: Sequence[Mapping[str, Any]],
    second: Sequence[Mapping[str, Any]],
    key: str,
    schema: str,
    namespace: str,
) -> dict[str, Any]:
    rows = []
    for value in sorted({str(row[key]) for row in first}):
        first_rows = [row for row in first if str(row[key]) == value]
        second_rows = [row for row in second if str(row[key]) == value]
        first_effect = _effect_mean(first_rows)
        second_effect = _effect_mean(second_rows)
        drift = (
            abs(float(second_effect) - float(first_effect))
            if first_effect is not None and second_effect is not None
            else None
        )
        rows.append(
            {
                key: value,
                "first_count": len(first_rows),
                "second_count": len(second_rows),
                "first_effect_mean": first_effect,
                "second_effect_mean": second_effect,
                "absolute_effect_drift": drift,
                "status": (
                    "STABLE" if second_rows and drift is not None and drift <= 0.15
                    else "UNSTABLE"
                ),
            }
        )
    status = "PASS_STABLE" if rows and all(row["status"] == "STABLE" for row in rows) else "HOLD"
    body = {
        "schema": schema,
        "maximum_absolute_effect_drift": 0.15,
        "comparisons": rows,
        "status": status,
        "claim_ceiling": "TWO_FINITE_FORWARD_WINDOWS_ONLY",
        "truth_effect": "NONE",
    }
    return {**body, "comparison_digest": content_address(namespace, body)}


def _nondegradation(window: Mapping[str, Any]) -> dict[str, Any]:
    rows = list(window.get("events", []))
    baseline = sum(float(row["baseline_score"]) for row in rows) / len(rows) if rows else None
    candidate = sum(float(row["candidate_score"]) for row in rows) / len(rows) if rows else None
    count = sum(float(row["candidate_score"]) >= float(row["baseline_score"]) for row in rows)
    passed = (
        window.get("status") == "WINDOW_READY"
        and baseline is not None
        and candidate is not None
        and candidate >= baseline
        and count >= 3
    )
    body = {
        "schema": "KC144.P45.SecondWindowNondegradation.V1",
        "window_digest": window["window_digest"],
        "baseline_mean": baseline,
        "candidate_mean": candidate,
        "nondegrading_event_count": count,
        "required_nondegrading_events": 3,
        "status": "PASS_NONDEGRADING" if passed else "HOLD",
        "truth_effect": "NONE",
    }
    return {**body, "measurement_digest": content_address("kc144.p45.measurement", body)}


def compile_p45_cycle(
    *,
    p44_cycle: Mapping[str, Any] | None = None,
    second_forward_events: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    parent = dict(p44_cycle or compile_p44_cycle())
    parent_verification = verify_p44_cycle(parent)
    effect = parent.get("canonical_edge_effect", {})
    first = parent.get("forward_window", {}).get("events", [])
    effect_admitted = (
        parent_verification["verdict"] == "PASS"
        and effect.get("status") == "FROZEN_CANONICAL_EDGE_EFFECT"
    )
    window = _second_window(second_forward_events, first_events=first)
    route_stability = _compare_dimension(
        first, window["events"], "route_id",
        "KC144.P45.RouteStability.V1", "kc144.p45.route-stability",
    )
    surface_stability = _compare_dimension(
        first, window["events"], "source_surface",
        "KC144.P45.SurfaceStability.V1", "kc144.p45.surface-stability",
    )
    measurement = _nondegradation(window)
    complete = window["status"] == "WINDOW_READY"
    stable = (
        route_stability["status"] == "PASS_STABLE"
        and surface_stability["status"] == "PASS_STABLE"
    )
    nondegrading = measurement["status"] == "PASS_NONDEGRADING"
    if effect_admitted and complete and stable and nondegrading:
        verdict = "RETAIN_EDGE_REVERSIBLY"
    elif effect_admitted and complete and (not stable or not nondegrading):
        verdict = "RETRACT_EDGE_PROPOSAL"
    else:
        verdict = "HOLD"
    decision_body = {
        "schema": "KC144.P45.ReversibleEdgeRetentionDecision.V1",
        "edge_id": "P41.EDGE.003",
        "p44_effect_digest": effect.get("effect_digest"),
        "second_window_digest": window["window_digest"],
        "route_comparison_digest": route_stability["comparison_digest"],
        "surface_comparison_digest": surface_stability["comparison_digest"],
        "measurement_digest": measurement["measurement_digest"],
        "verdict": verdict,
        "reversible": True,
        "canonical_graph_mutation_executed": False,
        "route_priority_delta_authorized": False,
        "model_weight_mutation_authorized": False,
        "ic10_authorization_present": False,
        "truth_effect": "NONE",
        "authority_effect": "NONE",
    }
    decision = {
        **decision_body,
        "decision_digest": content_address("kc144.p45.decision", decision_body),
    }
    residuals = []
    if not effect_admitted:
        residuals.append("P44_CANONICAL_EDGE_EFFECT_NOT_ADMITTED")
    if not complete:
        residuals.append("SECOND_FORWARD_WINDOW_PENDING")
    if complete and not stable:
        residuals.append("CROSS_WINDOW_STABILITY_FAILED")
    if complete and not nondegrading:
        residuals.append("SECOND_WINDOW_NONDEGRADATION_FAILED")
    if verdict != "RETAIN_EDGE_REVERSIBLY":
        residuals.append("REVERSIBLE_EDGE_RETENTION_NOT_GRANTED")
    state = {
        "schema": "KC144.P45.StateDelta.V1",
        "public_parent_result_id": PUBLIC_P44_RESULT_ID,
        "p44_edge_effect_admitted": effect_admitted,
        "first_window_outcomes": len(first),
        "second_window_outcomes": window["event_count"],
        "second_window_routes": window["route_count"],
        "second_window_surfaces": window["surface_count"],
        "route_stability": route_stability["status"],
        "surface_stability": surface_stability["status"],
        "second_window_nondegradation": measurement["status"],
        "retention_decision": verdict,
        "canonical_graph_mutations": 0,
        "production_authority": "HOLD",
        "truth_effect": "NONE",
        "residuals": sorted(residuals),
        "return": P45_ROUTE[-1],
        "next_seed": P45_NEXT_SEED,
    }
    state["delta_id"] = content_address("kc144.p45.state", state)
    payloads = (
        p45_public_parent(), effect, window, {"rejected": window["rejected"]},
        route_stability, surface_stability, measurement, decision,
        p45_parallel_lineage(), state,
    )
    receipts = []
    for index, (lane, payload) in enumerate(zip(P45_LANES, payloads), 1):
        receipt = {
            "schema": "KC144.P45.LaneReceipt.V1",
            "lane_id": f"P45.L{index:02d}",
            "lane": lane,
            "payload_digest": content_address(f"kc144.p45.lane.{lane.lower()}", payload),
            "return": P45_ROUTE[-1],
            "truth_effect": "NONE",
        }
        receipt["receipt_id"] = content_address("kc144.p45.lane-receipt", receipt)
        receipts.append(receipt)
    body = {
        "schema": "KC144.P45.Macrocycle.V1",
        "contract_digest": p45_contract()["contract_digest"],
        "public_parent_binding": p45_public_parent(),
        "p44_cycle": parent,
        "second_forward_events": [dict(row) for row in second_forward_events],
        "second_forward_window": window,
        "route_stability": route_stability,
        "surface_stability": surface_stability,
        "second_window_nondegradation": measurement,
        "retention_decision": decision,
        "parallel_lineage": p45_parallel_lineage(),
        "lane_receipts": receipts,
        "state": state,
    }
    return {**body, "envelope_digest": content_address("kc144.p45.cycle", body)}


def verify_p45_cycle(value: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    try:
        replay = compile_p45_cycle(
            p44_cycle=value.get("p44_cycle"),
            second_forward_events=value.get("second_forward_events", []),
        )
    except Exception as error:
        replay = {}
        errors.append(f"REPLAY_EXCEPTION:{type(error).__name__}")
    if replay.get("envelope_digest") != value.get("envelope_digest"):
        errors.append("REPLAY_DRIFT")
    if value.get("public_parent_binding") != p45_public_parent():
        errors.append("PUBLIC_PARENT")
    if len(value.get("lane_receipts", [])) != len(P45_LANES):
        errors.append("LANE_COUNT")
    if value.get("state", {}).get("truth_effect") != "NONE":
        errors.append("TRUTH_INFLATION")
    if value.get("state", {}).get("canonical_graph_mutations") != 0:
        errors.append("GRAPH_MUTATION")
    body = {
        "schema": "KC144.P45.Verification.V1",
        "verdict": "PASS" if not errors else "FAIL",
        "errors": sorted(errors),
        "replay_envelope_digest": replay.get("envelope_digest"),
        "production_authority": "HOLD",
        "truth_effect": "NONE",
    }
    return {**body, "verification_digest": content_address("kc144.p45.verify", body)}


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_bytes(canonical_bytes(value) + b"\n")


def compile_p45_release(
    output: str | Path,
    *,
    implementation_commit: str,
    implementation_tree: str,
) -> dict[str, Any]:
    if not GIT_SHA_RE.fullmatch(implementation_commit):
        raise P45RuntimeError("implementation commit must be a Git SHA")
    if not GIT_SHA_RE.fullmatch(implementation_tree):
        raise P45RuntimeError("implementation tree must be a Git SHA")
    destination = Path(output)
    destination.mkdir(parents=True, exist_ok=True)
    cycle = compile_p45_cycle()
    verification = verify_p45_cycle(cycle)
    body = {
        "schema": "KC144.P45.Release.V1",
        "release_id": "KC144_P45_REVERSIBLE_EDGE_RETENTION_CANDIDATE_V1",
        "implementation": {
            "repository": "demeet2k/guild-hall",
            "commit": implementation_commit,
            "tree": implementation_tree,
        },
        "public_parent_result_id": PUBLIC_P44_RESULT_ID,
        "public_parent_release_digest": PUBLIC_P44_RELEASE_DIGEST,
        "status": "CANDIDATE_HOLD",
        "p44_edge_effect_admitted": False,
        "first_window_outcomes": 0,
        "second_window_outcomes": 0,
        "route_stability": "HOLD",
        "surface_stability": "HOLD",
        "second_window_nondegradation": "HOLD",
        "retention_decision": "HOLD",
        "canonical_graph_mutations": 0,
        "production_authority": "HOLD",
        "truth_effect": "NONE",
        "verification_verdict": verification["verdict"],
        "next_seed": P45_NEXT_SEED,
    }
    digest = content_address("kc144.p45.release", body)
    release = {
        **body,
        "release_digest": digest,
        "result_id": "KC144.P45.CANDIDATE::" + digest.split(":", 1)[1][:24],
    }
    artifacts = {
        "p45_contract_v1.json": p45_contract(),
        "p45_macrocycle_v1.json": cycle,
        "p45_second_forward_window_v1.json": cycle["second_forward_window"],
        "p45_route_stability_v1.json": cycle["route_stability"],
        "p45_surface_stability_v1.json": cycle["surface_stability"],
        "p45_nondegradation_v1.json": cycle["second_window_nondegradation"],
        "p45_retention_decision_v1.json": cycle["retention_decision"],
        "p45_parallel_lineage_v1.json": cycle["parallel_lineage"],
        "p45_verification_v1.json": verification,
        "p45_release_v1.json": release,
    }
    for name, value in artifacts.items():
        _write_json(destination / name, value)
    sums = [
        f"{hashlib.sha256((destination / name).read_bytes()).hexdigest()}  {name}"
        for name in sorted(artifacts)
    ]
    (destination / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
    return release
