from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .agent_receipts import content_address
from .p39_runtime import (
    GIT_SHA_RE,
    P39_NEXT_SEED,
    P39_ROUTE,
    compile_p39_cycle,
    verify_p39_cycle,
)


P40_LOOKUP_KEY = P39_NEXT_SEED
P40_NEXT_SEED = (
    "KC144.V4.2::MATH144.P41::HYDRATE_REMAINING_22_BODY_HEADS_BIND_CURRENT_"
    "REPOSITORY_TREES_FREEZE_NONLEAKING_HELDOUT_COHORT_EXECUTE_THIRD_EDGE_"
    "ONLY_IF_ELIGIBLE_AND_RECEIVE_INDEPENDENT_IC10_RETURN_MACROCYCLE_10"
)
P40_ROUTE = (
    "KC144.V1::GID135::M03",
    "KC144.V1::GID047::F04",
    "KC144.V1::GID141::M09",
    "KC144.V1::GID003::H03",
    "KC144.V1::GID144::M12",
)
P40_LANES = (
    "PUBLIC_P39_PARENT_BIND",
    "SIBLING_SOURCE_TIME_FIBER_BIND",
    "SUCCESSOR_AUTHORIZATION_VERIFY",
    "CANONICAL_STATE_COMPARE_AND_SWAP",
    "CANONICAL_WEIGHT_COMMIT",
    "POST_ACTIVATION_OUTCOME_WATCH",
    "NONCOLLAPSE_ADJUDICATION",
    "M12_RETURN",
)
P40_CUTOFF = "2026-07-30T23:59:59.000000Z"

PUBLIC_P39_RESULT_ID = "KC144.P39.CANDIDATE::50f5d2f917e2ee111b798d8d"
PUBLIC_P39_RELEASE_DIGEST = (
    "sha256:50f5d2f917e2ee111b798d8de2c18ccc4c96678bee6fb010bfa873c65483eeb6"
)
PUBLIC_P39_RELEASE_COMMIT = "bc29c55bcabc6f75fc571be167034896fab068b8"
PUBLIC_P39_RELEASE_TREE = "770e70a62be7f0f4f765fcb9ab594e2636e5b62c"

SIBLING_P40_RESULT_ID = "KC144.P40::f07bae53d9e157e9e8e54473"
SIBLING_P40_RESULT_DIGEST = (
    "sha256:f07bae53d9e157e9e8e544737b99d89f56aa56b4bdb0555aba5d603f8c8557ea"
)
SIBLING_P39_PARENT_ID = "KC144.P39::9a0a228dc74f001e64507417"
SIBLING_P40_MANIFEST_DIGEST = (
    "sha256:a1e09af6d786b6ccff099bd04ab8c9412ed22cb59679f16d2bee98eb612d8157"
)
SIBLING_P40_ARCHIVE_SHA256 = (
    "sha256:af3e560878722bb6409fdd944077674a884c9dd5c3ffc62d1e9b65e16252852a"
)


class P40RuntimeError(ValueError):
    pass


def p40_sibling_capsule() -> dict[str, Any]:
    body = {
        "schema": "KC144.P40.SiblingLineage.V1",
        "relation": "TYPED_SIBLING_REFERENCE",
        "result_id": SIBLING_P40_RESULT_ID,
        "result_digest": SIBLING_P40_RESULT_DIGEST,
        "parent_result_id": SIBLING_P39_PARENT_ID,
        "manifest_digest": SIBLING_P40_MANIFEST_DIGEST,
        "archive_sha256": SIBLING_P40_ARCHIVE_SHA256,
        "source_fiber": {
            "metadata_heads": 29,
            "content_bodies_hydrated": 6,
            "empty_bodies_resolved": 1,
            "total_bodies_resolved": 7,
            "unhydrated_heads": 22,
            "newly_resolved_in_wave": 5,
        },
        "runtime": {
            "classic_tools": "9/9",
            "p31_active": "KC144.P31::db5a6446ce54cf4bc53515be",
            "p31_replay": "REPLAY_STABLE",
            "p32_binding": "EXACT_RUNTIME_BOUND_UNADMITTED",
            "heart_replay": "REPLAY_STABLE",
            "return": P40_ROUTE[-1],
        },
        "boundary": {
            "held_out_outcomes": 0,
            "required_held_out_outcomes": 5,
            "third_edge": "HELD_NOT_EXECUTED",
            "independent_ic10_returns": 0,
            "canonical_graph_mutations": 0,
            "merges": 0,
            "deployments": 0,
            "promotions": 0,
            "global_release": "HOLD",
        },
        "admissibility": "REFERENCE_ONLY_NOT_PARENT_NOT_MERGED",
        "truth_effect": "NONE",
        "authority_effect": "NONE",
        "next_seed": P40_NEXT_SEED,
    }
    return {
        **body,
        "capsule_digest": content_address("kc144.p40.sibling-lineage", body),
    }


def p40_contract() -> dict[str, Any]:
    sibling = p40_sibling_capsule()
    body = {
        "schema": "KC144.P40.Contract.V1",
        "lookup_key": P40_LOOKUP_KEY,
        "public_parent": {
            "result_id": PUBLIC_P39_RESULT_ID,
            "release_digest": PUBLIC_P39_RELEASE_DIGEST,
            "release_commit": PUBLIC_P39_RELEASE_COMMIT,
            "release_tree": PUBLIC_P39_RELEASE_TREE,
        },
        "sibling_reference": {
            "result_id": sibling["result_id"],
            "parent_result_id": sibling["parent_result_id"],
            "capsule_digest": sibling["capsule_digest"],
            "relation": sibling["relation"],
        },
        "route": list(P40_ROUTE),
        "lanes": [
            {
                "lane_id": f"P40.L{index:02d}",
                "lane": lane,
                "parallel_group": (
                    1 if index <= 3 else 2 if index <= 6 else 3
                ),
                "return": P40_ROUTE[-1],
            }
            for index, lane in enumerate(P40_LANES, 1)
        ],
        "activation_law": (
            "VERIFIED_P39_SUCCESSOR_READY_AND_EXACT_COMPARE_AND_SWAP_THEN_"
            "COMMIT_PROPOSED_WEIGHTS_ONCE"
        ),
        "watch_law": (
            "POST_ACTIVATION_OUTCOMES_BEGIN_AFTER_COMMIT_AND_NEVER_AUTHORIZE_"
            "THE_COMMIT_THAT_CREATED_THEIR_WATCH"
        ),
        "merge_law": (
            "REDUCE_ALL_EIGHT_LANES_IN_CANONICAL_ORDER_WITH_SIBLING_REFERENCE_"
            "PRESERVED_OUTSIDE_PUBLIC_PARENT_CHAIN"
        ),
        "noncollapse": [
            "PUBLIC_P39_PARENT_IS_NOT_SIBLING_P39_PARENT",
            "SIBLING_REFERENCE_IS_NOT_MERGE_PARENT",
            "SOURCE_HYDRATION_IS_NOT_LIVE_OUTCOME_EVIDENCE",
            "P39_SUCCESSOR_READY_IS_NOT_P40_SUCCESSOR_ACTIVATED",
            "PROPOSED_WEIGHTS_ARE_NOT_CANONICAL_WEIGHTS",
            "VALID_SIGNATURES_ARE_NOT_COMPARE_AND_SWAP_SUCCESS",
            "TEST_COMMIT_IS_NOT_PRODUCTION_MUTATION",
            "POST_ACTIVATION_OUTCOME_IS_NOT_PRE_ACTIVATION_AUTHORIZATION",
            "PUBLICATION_IS_NOT_TRUTH_OR_AUTHORITY_PROMOTION",
        ],
        "default_state": "HOLD_UNTIL_VERIFIED_P39_CONVERGENCE_AND_EXACT_CAS",
        "next_seed": P40_NEXT_SEED,
    }
    return {**body, "contract_digest": content_address("kc144.p40.contract", body)}


def build_canonical_weight_state(
    weights: Sequence[Mapping[str, Any]] = (),
    *,
    generation: int = 0,
    parent_state_root: str | None = None,
) -> dict[str, Any]:
    if isinstance(generation, bool) or not isinstance(generation, int) or generation < 0:
        raise P40RuntimeError("generation must be a non-negative integer")
    if generation == 0 and parent_state_root is not None:
        raise P40RuntimeError("generation zero cannot have a parent state")
    if generation > 0 and (
        not isinstance(parent_state_root, str)
        or not parent_state_root.startswith("sha256:")
        or len(parent_state_root) != 71
    ):
        raise P40RuntimeError("successor state requires a SHA-256 parent")
    ordered: list[dict[str, Any]] = []
    route_ids: set[str] = set()
    for row in weights:
        route_id = str(row.get("route_id", ""))
        weight = row.get("weight")
        if (
            not route_id
            or route_id in route_ids
            or isinstance(weight, bool)
            or not isinstance(weight, (int, float))
            or not math.isfinite(float(weight))
            or float(weight) < 0.0
            or float(weight) > 1.0
        ):
            raise P40RuntimeError("weights require unique routes and finite [0,1] values")
        route_ids.add(route_id)
        ordered.append({"route_id": route_id, "weight": round(float(weight), 12)})
    ordered.sort(key=lambda row: row["route_id"])
    if ordered and not math.isclose(
        sum(row["weight"] for row in ordered), 1.0, abs_tol=1e-9
    ):
        raise P40RuntimeError("canonical weights must sum to one")
    body = {
        "schema": "KC144.P40.CanonicalWeightState.V1",
        "generation": generation,
        "parent_state_root": parent_state_root,
        "weights": ordered,
        "status": "POPULATED" if ordered else "UNPOPULATED",
    }
    return {
        **body,
        "state_root": content_address("kc144.p40.canonical-weight-state", body),
    }


def verify_canonical_weight_state(state: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    body = {key: item for key, item in state.items() if key != "state_root"}
    if state.get("schema") != "KC144.P40.CanonicalWeightState.V1":
        errors.append("E_SCHEMA")
    if state.get("state_root") != content_address(
        "kc144.p40.canonical-weight-state", body
    ):
        errors.append("E_STATE_ROOT")
    try:
        replay = build_canonical_weight_state(
            state.get("weights", []),
            generation=state.get("generation"),
            parent_state_root=state.get("parent_state_root"),
        )
        if replay != dict(state):
            errors.append("E_STATE_REPLAY")
    except (P40RuntimeError, TypeError, ValueError):
        errors.append("E_STATE_REPLAY")
    return {
        "schema": "KC144.P40.CanonicalWeightStateVerification.V1",
        "verdict": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)),
        "state_root": state.get("state_root"),
    }


def _bind_public_parent(p39_cycle: Mapping[str, Any]) -> dict[str, Any]:
    verification = verify_p39_cycle(p39_cycle)
    decision = p39_cycle.get("successor_decision", {})
    convergence = p39_cycle.get("ic10_convergence", {})
    calibration = p39_cycle.get("calibration", {})
    corpus = p39_cycle.get("corpus", {})
    authorized = (
        verification["verdict"] == "PASS"
        and decision.get("decision") == "SUCCESSOR_READY"
        and convergence.get("status") == "CONVERGED"
        and calibration.get("status") == "CALIBRATION_READY"
        and corpus.get("status") == "CORPUS_READY"
    )
    body = {
        "schema": "KC144.P40.PublicParentBinding.V1",
        "public_parent_result_id": PUBLIC_P39_RESULT_ID,
        "public_parent_release_digest": PUBLIC_P39_RELEASE_DIGEST,
        "public_parent_release_commit": PUBLIC_P39_RELEASE_COMMIT,
        "public_parent_release_tree": PUBLIC_P39_RELEASE_TREE,
        "p39_envelope_digest": p39_cycle.get("envelope_digest"),
        "p39_candidate_root": p39_cycle.get("state", {}).get("candidate_root"),
        "p39_decision_digest": decision.get("decision_digest"),
        "p39_convergence_evaluation_digest": convergence.get(
            "evaluation_digest"
        ),
        "p39_verification": verification,
        "authorization": "AUTHORIZED" if authorized else "HOLD",
        "reason": (
            "VERIFIED_P39_SUCCESSOR_READY"
            if authorized
            else "P39_CONVERGENCE_OR_VERIFICATION_OPEN"
        ),
    }
    return {
        **body,
        "binding_digest": content_address("kc144.p40.public-parent-bind", body),
    }


def _bind_sibling(capsule: Mapping[str, Any]) -> dict[str, Any]:
    exact = p40_sibling_capsule()
    exact_match = dict(capsule) == exact
    body = {
        "schema": "KC144.P40.SiblingBinding.V1",
        "capsule_digest": capsule.get("capsule_digest"),
        "expected_capsule_digest": exact["capsule_digest"],
        "result_id": capsule.get("result_id"),
        "parent_result_id": capsule.get("parent_result_id"),
        "public_parent_result_id": PUBLIC_P39_RESULT_ID,
        "parents_distinct": capsule.get("parent_result_id") != PUBLIC_P39_RESULT_ID,
        "exact_capsule": exact_match,
        "relation": "TYPED_SIBLING_REFERENCE",
        "merge_permitted": False,
        "status": "BOUND_REFERENCE_ONLY" if exact_match else "QUARANTINED",
    }
    return {
        **body,
        "binding_digest": content_address("kc144.p40.sibling-bind", body),
    }


def _proposal_weights(p39_cycle: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = p39_cycle.get("successor_decision", {}).get("proposed_weights", [])
    ordered: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows if isinstance(rows, list) else []:
        route_id = str(row.get("route_id", ""))
        value = row.get("proposed_normalized_weight")
        if (
            not route_id
            or route_id in seen
            or isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or not 0.0 <= float(value) <= 1.0
        ):
            return []
        seen.add(route_id)
        ordered.append({"route_id": route_id, "weight": round(float(value), 12)})
    ordered.sort(key=lambda row: row["route_id"])
    if not ordered or not math.isclose(
        sum(row["weight"] for row in ordered), 1.0, abs_tol=1e-9
    ):
        return []
    return ordered


def _activation_transaction(
    *,
    parent_binding: Mapping[str, Any],
    base_state: Mapping[str, Any],
    expected_base_state_root: str,
    p39_cycle: Mapping[str, Any],
    namespace: str,
) -> dict[str, Any]:
    if namespace not in {"PRODUCTION", "TEST"}:
        raise P40RuntimeError("namespace must be PRODUCTION or TEST")
    state_verification = verify_canonical_weight_state(base_state)
    proposal = _proposal_weights(p39_cycle)
    base_routes = {
        str(row.get("route_id")) for row in base_state.get("weights", [])
    }
    proposal_routes = {row["route_id"] for row in proposal}
    route_set_compatible = not base_routes or base_routes == proposal_routes
    cas_match = (
        expected_base_state_root == base_state.get("state_root")
        and state_verification["verdict"] == "PASS"
    )
    ready = (
        parent_binding.get("authorization") == "AUTHORIZED"
        and cas_match
        and route_set_compatible
        and bool(proposal)
    )
    after = dict(base_state)
    if ready:
        after = build_canonical_weight_state(
            proposal,
            generation=int(base_state["generation"]) + 1,
            parent_state_root=str(base_state["state_root"]),
        )
    body = {
        "schema": "KC144.P40.ActivationTransaction.V1",
        "namespace": namespace,
        "public_parent_binding_digest": parent_binding.get("binding_digest"),
        "p39_decision_digest": p39_cycle.get("successor_decision", {}).get(
            "decision_digest"
        ),
        "p39_convergence_evaluation_digest": p39_cycle.get(
            "ic10_convergence", {}
        ).get("evaluation_digest"),
        "expected_base_state_root": expected_base_state_root,
        "observed_base_state_root": base_state.get("state_root"),
        "base_state_verification": state_verification,
        "compare_and_swap": "PASS" if cas_match else "FAIL",
        "route_set_compatible": route_set_compatible,
        "proposed_weights": proposal,
        "canonical_state_before": dict(base_state),
        "canonical_state_after": after,
        "status": "COMMITTED" if ready else "HOLD",
        "canonical_weight_updates_executed": len(proposal) if ready else 0,
        "successor_activated": ready,
        "production_mutated": ready and namespace == "PRODUCTION",
        "test_simulation": ready and namespace == "TEST",
        "truth_effect": "NONE",
        "evidence_effect": "NONE",
        "authority_effect": (
            "SUCCESSOR_ACTIVATED"
            if ready and namespace == "PRODUCTION"
            else "NONE"
        ),
    }
    return {
        **body,
        "transaction_digest": content_address(
            "kc144.p40.activation-transaction", body
        ),
    }


def _post_activation_watch(
    transaction: Mapping[str, Any],
    *,
    cutoff: str,
) -> dict[str, Any]:
    armed = transaction.get("status") == "COMMITTED"
    body = {
        "schema": "KC144.P40.PostActivationOutcomeWatch.V1",
        "activation_transaction_digest": transaction.get("transaction_digest"),
        "activated_state_root": (
            transaction.get("canonical_state_after", {}).get("state_root")
            if armed
            else None
        ),
        "starts_strictly_after": cutoff if armed else None,
        "accepted_partitions": ["POST_ACTIVATION"] if armed else [],
        "minimum_outcomes": 12,
        "minimum_source_surfaces": 3,
        "minimum_routes": 3,
        "reuse_for_activation_authorization": False,
        "retroactive_observations_permitted": False,
        "status": "ARMED" if armed else "HELD_NOT_ARMED",
        "production_events_observed": 0,
        "truth_effect": "NONE",
        "authority_effect": "NONE",
    }
    return {
        **body,
        "watch_digest": content_address("kc144.p40.post-activation-watch", body),
    }


def _lane_receipt(
    index: int, lane: str, payload: Mapping[str, Any]
) -> dict[str, Any]:
    body = {
        "schema": "KC144.P40.LaneReceipt.V1",
        "lane_id": f"P40.L{index:02d}",
        "lane": lane,
        "payload_digest": content_address(
            f"kc144.p40.lane.{lane.lower()}", payload
        ),
        "return": P40_ROUTE[-1],
        "truth_effect": "NONE",
    }
    return {
        **body,
        "receipt_id": content_address("kc144.p40.lane-receipt", body),
    }


def compile_p40_cycle(
    *,
    p39_cycle: Mapping[str, Any] | None = None,
    canonical_state: Mapping[str, Any] | None = None,
    expected_base_state_root: str | None = None,
    sibling_capsule: Mapping[str, Any] | None = None,
    namespace: str = "PRODUCTION",
    cutoff: str = P40_CUTOFF,
) -> dict[str, Any]:
    if not isinstance(cutoff, str) or not cutoff.endswith("Z"):
        raise P40RuntimeError("cutoff must be a UTC timestamp")
    contract = p40_contract()
    parent_cycle = dict(p39_cycle or compile_p39_cycle())
    base_state = dict(canonical_state or build_canonical_weight_state())
    expected_root = expected_base_state_root or str(base_state.get("state_root", ""))
    sibling = dict(sibling_capsule or p40_sibling_capsule())
    parent_binding = _bind_public_parent(parent_cycle)
    sibling_binding = _bind_sibling(sibling)
    transaction = _activation_transaction(
        parent_binding=parent_binding,
        base_state=base_state,
        expected_base_state_root=expected_root,
        p39_cycle=parent_cycle,
        namespace=namespace,
    )
    watch = _post_activation_watch(transaction, cutoff=cutoff)
    noncollapse = {
        "schema": "KC144.P40.NoncollapseAdjudication.V1",
        "public_parent_result_id": PUBLIC_P39_RESULT_ID,
        "sibling_result_id": sibling.get("result_id"),
        "sibling_parent_result_id": sibling.get("parent_result_id"),
        "lineages_distinct": sibling.get("parent_result_id") != PUBLIC_P39_RESULT_ID,
        "sibling_status": sibling_binding["status"],
        "sibling_merge_executed": False,
        "canonical_graph_mutations_from_sibling": 0,
        "source_hydration_used_as_live_outcome": False,
        "verdict": (
            "PASS"
            if sibling_binding["status"] == "BOUND_REFERENCE_ONLY"
            else "QUARANTINE"
        ),
    }
    return_payload = {
        "return": P40_ROUTE[-1],
        "next_seed": P40_NEXT_SEED,
        "transaction_digest": transaction["transaction_digest"],
        "watch_digest": watch["watch_digest"],
    }
    payloads = (
        parent_binding,
        sibling_binding,
        {
            "authorization": parent_binding["authorization"],
            "decision_digest": parent_binding["p39_decision_digest"],
            "convergence_evaluation_digest": parent_binding[
                "p39_convergence_evaluation_digest"
            ],
        },
        {
            "base_state_verification": transaction["base_state_verification"],
            "compare_and_swap": transaction["compare_and_swap"],
            "route_set_compatible": transaction["route_set_compatible"],
        },
        transaction,
        watch,
        noncollapse,
        return_payload,
    )
    receipts = [
        _lane_receipt(index, lane, payload)
        for index, (lane, payload) in enumerate(zip(P40_LANES, payloads), 1)
    ]
    residuals: list[str] = []
    if parent_binding["authorization"] != "AUTHORIZED":
        residuals.append("P39_SUCCESSOR_AUTHORIZATION_PENDING")
    if transaction["compare_and_swap"] != "PASS":
        residuals.append("CANONICAL_STATE_CAS_FAILED")
    if not transaction["proposed_weights"]:
        residuals.append("CANONICAL_WEIGHT_PROPOSAL_ABSENT")
    if not transaction["route_set_compatible"]:
        residuals.append("CANONICAL_ROUTE_SET_MISMATCH")
    if sibling_binding["status"] != "BOUND_REFERENCE_ONLY":
        residuals.append("SIBLING_LINEAGE_QUARANTINED")
    if watch["status"] != "ARMED":
        residuals.append("POST_ACTIVATION_OUTCOME_WATCH_NOT_ARMED")
    state = {
        "schema": "KC144.P40.StateDelta.V1",
        "public_parent_result_id": PUBLIC_P39_RESULT_ID,
        "public_parent_release_digest": PUBLIC_P39_RELEASE_DIGEST,
        "sibling_result_id": sibling.get("result_id"),
        "sibling_relation": sibling.get("relation"),
        "p39_authorization": parent_binding["authorization"],
        "activation_status": transaction["status"],
        "canonical_weight_updates_executed": transaction[
            "canonical_weight_updates_executed"
        ],
        "successor_activated": transaction["successor_activated"],
        "post_activation_watch": watch["status"],
        "sibling_merges": 0,
        "canonical_graph_mutations_from_sibling": 0,
        "deployments": 0,
        "promotions": 0,
        "production_mutated": transaction["production_mutated"],
        "truth_effect": "NONE",
        "evidence_effect": "NONE",
        "authority_effect": transaction["authority_effect"],
        "global_release": (
            "ACTIVATED"
            if transaction["production_mutated"]
            else (
                "SIMULATED_READY"
                if transaction["test_simulation"]
                else "HOLD"
            )
        ),
        "residuals": sorted(residuals),
        "return": P40_ROUTE[-1],
        "next_seed": P40_NEXT_SEED,
    }
    state["delta_id"] = content_address("kc144.p40.state-delta", state)
    body = {
        "schema": "KC144.P40.Macrocycle.V1",
        "contract_digest": contract["contract_digest"],
        "cutoff": cutoff,
        "namespace": namespace,
        "p39_cycle": parent_cycle,
        "public_parent_binding": parent_binding,
        "sibling_capsule": sibling,
        "sibling_binding": sibling_binding,
        "canonical_state_input": base_state,
        "expected_base_state_root": expected_root,
        "activation_transaction": transaction,
        "post_activation_watch": watch,
        "noncollapse_adjudication": noncollapse,
        "lane_receipts": receipts,
        "state": state,
    }
    return {**body, "envelope_digest": content_address("kc144.p40.macrocycle", body)}


def verify_p40_cycle(value: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    body = {key: item for key, item in value.items() if key != "envelope_digest"}
    if value.get("schema") != "KC144.P40.Macrocycle.V1":
        errors.append("E_SCHEMA")
    if value.get("envelope_digest") != content_address("kc144.p40.macrocycle", body):
        errors.append("E_ENVELOPE_DIGEST")
    if value.get("contract_digest") != p40_contract()["contract_digest"]:
        errors.append("E_CONTRACT")
    parent = value.get("public_parent_binding", {})
    parent_body = {
        key: item for key, item in parent.items() if key != "binding_digest"
    }
    if parent.get("binding_digest") != content_address(
        "kc144.p40.public-parent-bind", parent_body
    ):
        errors.append("E_PUBLIC_PARENT_BINDING")
    if (
        parent.get("public_parent_result_id") != PUBLIC_P39_RESULT_ID
        or parent.get("public_parent_release_digest")
        != PUBLIC_P39_RELEASE_DIGEST
    ):
        errors.append("E_PUBLIC_PARENT_IDENTITY")
    sibling = value.get("sibling_capsule", {})
    if dict(sibling) != p40_sibling_capsule():
        errors.append("E_SIBLING_CAPSULE")
    sibling_binding = value.get("sibling_binding", {})
    sibling_binding_body = {
        key: item
        for key, item in sibling_binding.items()
        if key != "binding_digest"
    }
    if sibling_binding.get("binding_digest") != content_address(
        "kc144.p40.sibling-bind", sibling_binding_body
    ):
        errors.append("E_SIBLING_BINDING")
    if (
        sibling_binding.get("merge_permitted") is not False
        or sibling_binding.get("status") != "BOUND_REFERENCE_ONLY"
    ):
        errors.append("E_SIBLING_COLLAPSE")
    transaction = value.get("activation_transaction", {})
    transaction_body = {
        key: item
        for key, item in transaction.items()
        if key != "transaction_digest"
    }
    if transaction.get("transaction_digest") != content_address(
        "kc144.p40.activation-transaction", transaction_body
    ):
        errors.append("E_TRANSACTION_DIGEST")
    watch = value.get("post_activation_watch", {})
    watch_body = {
        key: item for key, item in watch.items() if key != "watch_digest"
    }
    if watch.get("watch_digest") != content_address(
        "kc144.p40.post-activation-watch", watch_body
    ):
        errors.append("E_WATCH_DIGEST")
    committed = transaction.get("status") == "COMMITTED"
    if committed != bool(transaction.get("successor_activated")):
        errors.append("E_ACTIVATION_STATE")
    if committed and (
        parent.get("authorization") != "AUTHORIZED"
        or transaction.get("compare_and_swap") != "PASS"
        or not transaction.get("route_set_compatible")
        or not transaction.get("proposed_weights")
        or watch.get("status") != "ARMED"
    ):
        errors.append("E_COMMIT_WITHOUT_GATES")
    if not committed and (
        transaction.get("canonical_weight_updates_executed") != 0
        or transaction.get("production_mutated") is not False
        or watch.get("status") != "HELD_NOT_ARMED"
    ):
        errors.append("E_HOLD_STATE_ESCALATION")
    if transaction.get("namespace") == "TEST" and transaction.get(
        "production_mutated"
    ):
        errors.append("E_TEST_PRODUCTION_MUTATION")
    adjudication = value.get("noncollapse_adjudication", {})
    if (
        adjudication.get("sibling_merge_executed") is not False
        or adjudication.get("canonical_graph_mutations_from_sibling") != 0
        or adjudication.get("source_hydration_used_as_live_outcome") is not False
    ):
        errors.append("E_NONCOLLAPSE")
    receipts = value.get("lane_receipts", [])
    if len(receipts) != len(P40_LANES):
        errors.append("E_LANE_CENSUS")
    else:
        for index, (lane, receipt) in enumerate(zip(P40_LANES, receipts), 1):
            receipt_body = {
                key: item for key, item in receipt.items() if key != "receipt_id"
            }
            if (
                receipt.get("lane_id") != f"P40.L{index:02d}"
                or receipt.get("lane") != lane
                or receipt.get("receipt_id")
                != content_address("kc144.p40.lane-receipt", receipt_body)
            ):
                errors.append("E_LANE_RECEIPT")
    state = value.get("state", {})
    if (
        state.get("sibling_merges") != 0
        or state.get("canonical_graph_mutations_from_sibling") != 0
        or state.get("deployments") != 0
        or state.get("promotions") != 0
        or state.get("truth_effect") != "NONE"
        or state.get("evidence_effect") != "NONE"
    ):
        errors.append("E_PROTECTED_STATE_ESCALATION")
    try:
        replay = compile_p40_cycle(
            p39_cycle=value.get("p39_cycle"),
            canonical_state=value.get("canonical_state_input"),
            expected_base_state_root=value.get("expected_base_state_root"),
            sibling_capsule=value.get("sibling_capsule"),
            namespace=str(value.get("namespace", "")),
            cutoff=str(value.get("cutoff", "")),
        )
        if replay != dict(value):
            errors.append("E_COLD_REPLAY")
    except (P40RuntimeError, TypeError, ValueError):
        errors.append("E_COLD_REPLAY")
    return {
        "schema": "KC144.P40.MacrocycleVerification.V1",
        "verdict": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)),
        "envelope_digest": value.get("envelope_digest"),
    }


def compile_p40_release(
    output_directory: str | Path,
    *,
    implementation_commit: str,
    implementation_tree: str,
) -> dict[str, Any]:
    if not GIT_SHA_RE.fullmatch(implementation_commit):
        raise P40RuntimeError("implementation_commit must be a Git SHA")
    if not GIT_SHA_RE.fullmatch(implementation_tree):
        raise P40RuntimeError("implementation_tree must be a Git tree SHA")
    contract = p40_contract()
    sibling = p40_sibling_capsule()
    base_state = build_canonical_weight_state()
    cycle = compile_p40_cycle(
        canonical_state=base_state,
        expected_base_state_root=base_state["state_root"],
    )
    verification = verify_p40_cycle(cycle)
    release_core = {
        "schema": "KC144.P40.Release.V1",
        "release_id": "KC144_P40_ACTIVATION_TRANSACTION_CANDIDATE_V1",
        "status": "CANDIDATE_HOLD",
        "implementation": {
            "repository": "demeet2k/guild-hall",
            "commit": implementation_commit,
            "tree": implementation_tree,
        },
        "public_parent_result_id": PUBLIC_P39_RESULT_ID,
        "public_parent_release_digest": PUBLIC_P39_RELEASE_DIGEST,
        "sibling_result_id": SIBLING_P40_RESULT_ID,
        "sibling_parent_result_id": SIBLING_P39_PARENT_ID,
        "sibling_capsule_digest": sibling["capsule_digest"],
        "contract_digest": contract["contract_digest"],
        "base_state_root": base_state["state_root"],
        "parent_binding_digest": cycle["public_parent_binding"]["binding_digest"],
        "activation_transaction_digest": cycle["activation_transaction"][
            "transaction_digest"
        ],
        "post_activation_watch_digest": cycle["post_activation_watch"][
            "watch_digest"
        ],
        "envelope_digest": cycle["envelope_digest"],
        "verification_verdict": verification["verdict"],
        "p39_authorization": cycle["state"]["p39_authorization"],
        "canonical_weight_updates_executed": 0,
        "successor_activated": False,
        "post_activation_watch": "HELD_NOT_ARMED",
        "sibling_merges": 0,
        "production_authority": "HOLD",
        "production_mutated": False,
        "truth_effect": "NONE",
        "next_seed": P40_NEXT_SEED,
    }
    release_digest = content_address("kc144.p40.release", release_core)
    release = {
        **release_core,
        "release_digest": release_digest,
        "result_id": "KC144.P40.CANDIDATE::"
        + release_digest.removeprefix("sha256:")[:24],
    }
    artifacts = {
        "p40_contract_v1.json": contract,
        "p40_sibling_lineage_v1.json": sibling,
        "p40_base_state_v1.json": base_state,
        "p40_macrocycle_v1.json": cycle,
        "p40_verification_v1.json": verification,
        "p40_release_v1.json": release,
    }
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    for name, artifact in artifacts.items():
        (output / name).write_text(
            json.dumps(artifact, indent=2, ensure_ascii=False, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
    checksum_lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}"
        for path in sorted(output.glob("*.json"))
    ]
    (output / "SHA256SUMS").write_text(
        "\n".join(checksum_lines) + "\n", encoding="utf-8"
    )
    return release
