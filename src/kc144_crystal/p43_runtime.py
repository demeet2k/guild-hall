from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .agent_receipts import canonical_bytes, content_address
from .p39_runtime import GIT_SHA_RE
from .p42_runtime import (
    P42_NEXT_SEED,
    compile_p42_cycle,
    empty_p42_signer_registry,
    verify_p42_cycle,
)


P43_LOOKUP_KEY = P42_NEXT_SEED
P43_NEXT_SEED = (
    "KC144.V4.5::MATH144.P44::ACCUMULATE_FORWARD_POST_EDGE_OUTCOMES_"
    "VERIFY_EXACTLY_ONCE_LEDGER_FINALITY_MEASURE_NONDEGRADATION_ACROSS_"
    "DIVERSE_ROUTES_AND_FREEZE_CANONICAL_EDGE_EFFECT_MACROCYCLE_13"
)
P43_FREEZE = "2026-07-28T09:30:00.000000Z"
P43_ROUTE = (
    "KC144.V1::GID005::H05",
    "KC144.V1::GID090::IC10",
    "KC144.V1::GID084::I04",
    "KC144.V1::GID047::F04",
    "KC144.V1::GID141::M09",
    "KC144.V1::GID144::M12",
)
P43_LANES = (
    "PUBLIC_P42_PARENT_BIND",
    "EXACT_ENUMERATION_ADMISSION",
    "NONLEAKING_COHORT_COMPLETION",
    "INDEPENDENT_IC10_AUTHORIZATION_ADMISSION",
    "P41_EDGE_003_EXACTLY_ONCE_EXECUTION",
    "TRANSACTION_FINALITY_AND_REPLAY",
    "FORWARD_POST_EDGE_WATCH_EVALUATION",
    "CAUSAL_NONREUSE_AND_TRUTH_NONCOLLAPSE",
    "PARALLEL_P43_NONCOLLAPSE",
    "M12_RETURN_AND_P44_RESEED",
)

PUBLIC_P42_RESULT_ID = "KC144.P42.CANDIDATE::57435ce8483f620adc52b3c6"
PUBLIC_P42_RELEASE_DIGEST = (
    "sha256:57435ce8483f620adc52b3c6ddd02f4b69816d00ef5fbabe43a6b0ee657518c7"
)
PUBLIC_P42_RELEASE_COMMIT = "d661fcd6de5c897e2bf614b9f377789dd59b27c7"
PUBLIC_P42_RELEASE_TREE = "37dd1399c4bc5f0d23d61a1d8543be3651ae14cf"


class P43RuntimeError(ValueError):
    pass


def p43_public_parent() -> dict[str, Any]:
    body = {
        "schema": "KC144.P43.PublicParentBinding.V1",
        "result_id": PUBLIC_P42_RESULT_ID,
        "release_digest": PUBLIC_P42_RELEASE_DIGEST,
        "release_commit": PUBLIC_P42_RELEASE_COMMIT,
        "release_tree": PUBLIC_P42_RELEASE_TREE,
        "relation": "EXACT_PUBLIC_PARENT",
    }
    return {**body, "binding_digest": content_address("kc144.p43.parent", body)}


def p43_parallel_lineage() -> dict[str, Any]:
    body = {
        "schema": "KC144.P43.ParallelLineage.V1",
        "parallel_label": "ATHENA_GIT_BRAIN_V2.P43",
        "relation": "PARALLEL_LABEL_COLLISION_NOT_PARENT_NOT_MERGED",
        "private_semantic_role": "PRESERVED_OPAQUE_NOT_INFERRED",
        "private_locator_published": False,
        "private_receipt_embedded": False,
        "merge_executed": False,
        "truth_effect": "NONE",
        "authority_effect": "NONE",
    }
    return {**body, "lineage_digest": content_address("kc144.p43.parallel", body)}


def p43_contract() -> dict[str, Any]:
    body = {
        "schema": "KC144.P43.Contract.V1",
        "lookup_key": P43_LOOKUP_KEY,
        "public_parent": p43_public_parent(),
        "route": list(P43_ROUTE),
        "lanes": [
            {
                "lane_id": f"P43.L{index:02d}",
                "lane": lane,
                "parallel_group": 1 if index <= 4 else 2 if index <= 8 else 3,
                "return": P43_ROUTE[-1],
            }
            for index, lane in enumerate(P43_LANES, 1)
        ],
        "admission_law": (
            "P42_ENUMERATION_COHORT_AND_IC10_ARTIFACTS_ARE_REVALIDATED_TOGETHER_"
            "AGAINST_THE_EXACT_P42_TRANSACTION_ROOT"
        ),
        "execution_law": (
            "P41_EDGE_003_EXECUTES_AT_MOST_ONCE_ONLY_IN_PRODUCTION_AFTER_ALL_"
            "THREE_EXTERNAL_GATES_PASS"
        ),
        "finality_law": (
            "A_VALID_SINGLE_EXECUTION_RECORD_IS_REPLAY_STABLE_AND_A_SECOND_"
            "EXECUTION_REQUEST_IS_IDEMPOTENT"
        ),
        "watch_law": (
            "POST_EDGE_EVENTS_MUST_BE_STRICTLY_FORWARD_AND_CANNOT_REUSE_THE_"
            "AUTHORIZATION_COHORT"
        ),
        "noncollapse": [
            "NEXT_IS_NOT_EVIDENCE_OR_AUTHORIZATION",
            "ADMISSION_IS_NOT_TRUTH_PROMOTION",
            "TEST_SIMULATION_IS_NOT_PRODUCTION_EXECUTION",
            "EDGE_EXECUTION_IS_NOT_GENERAL_GOVERNANCE_AUTHORITY",
            "POST_EDGE_WATCH_CANNOT_AUTHORIZE_ITS_CAUSAL_PREDECESSOR",
            "REPLAY_IS_NOT_INDEPENDENT_EVIDENCE",
            "PARALLEL_P43_LABEL_IS_NOT_THIS_PUBLIC_LINEAGE",
        ],
        "default_state": "HOLD_EXTERNAL_INPUTS_ABSENT",
        "next_seed": P43_NEXT_SEED,
    }
    return {**body, "contract_digest": content_address("kc144.p43.contract", body)}


def _input_bundle(
    *,
    signer_registry: Mapping[str, Any] | None,
    enumeration_witness: Mapping[str, Any] | None,
    heldout_events: Sequence[Mapping[str, Any]],
    edge_authorizations: Sequence[Mapping[str, Any]],
    execution_ledger: Sequence[Mapping[str, Any]],
    post_edge_events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    body = {
        "schema": "KC144.P43.InputBundle.V1",
        "signer_registry": dict(signer_registry or empty_p42_signer_registry()),
        "enumeration_witness": (
            dict(enumeration_witness) if enumeration_witness else None
        ),
        "heldout_events": [dict(row) for row in heldout_events],
        "edge_authorizations": [dict(row) for row in edge_authorizations],
        "execution_ledger": [dict(row) for row in execution_ledger],
        "post_edge_events": [dict(row) for row in post_edge_events],
    }
    return {**body, "bundle_digest": content_address("kc144.p43.inputs", body)}


def compile_p43_cycle(
    *,
    signer_registry: Mapping[str, Any] | None = None,
    enumeration_witness: Mapping[str, Any] | None = None,
    heldout_events: Sequence[Mapping[str, Any]] = (),
    edge_authorizations: Sequence[Mapping[str, Any]] = (),
    execution_ledger: Sequence[Mapping[str, Any]] = (),
    post_edge_events: Sequence[Mapping[str, Any]] = (),
    namespace: str = "PRODUCTION",
    execution_time: str = P43_FREEZE,
) -> dict[str, Any]:
    if namespace not in {"PRODUCTION", "TEST"}:
        raise P43RuntimeError("namespace must be PRODUCTION or TEST")
    inputs = _input_bundle(
        signer_registry=signer_registry,
        enumeration_witness=enumeration_witness,
        heldout_events=heldout_events,
        edge_authorizations=edge_authorizations,
        execution_ledger=execution_ledger,
        post_edge_events=post_edge_events,
    )
    p42 = compile_p42_cycle(
        signer_registry=inputs["signer_registry"],
        enumeration_witness=inputs["enumeration_witness"],
        heldout_events=inputs["heldout_events"],
        edge_authorizations=inputs["edge_authorizations"],
        execution_ledger=inputs["execution_ledger"],
        post_edge_events=inputs["post_edge_events"],
        namespace=namespace,
        execution_time=execution_time,
    )
    p42_verification = verify_p42_cycle(p42)
    enumeration_ready = (
        p42["enumeration_evaluation"]["status"] == "EXACT_ENUMERATION_VERIFIED"
    )
    cohort_ready = p42["heldout_cohort"]["status"] == "COHORT_READY"
    ic10_ready = p42["authorization_evaluation"]["status"] == "IC10_AUTHORIZED"
    transaction = p42["edge_transaction"]
    execution_final = (
        transaction["execution_count_after"] == 1
        and transaction["execution_status"] in {
            "EXECUTED",
            "ALREADY_EXECUTED_IDEMPOTENT",
        }
    )
    watch = p42["post_edge_watch"]
    residuals: list[str] = []
    if not enumeration_ready:
        residuals.append("EXACT_ENUMERATION_ADMISSION_PENDING")
    if not cohort_ready:
        residuals.append("NONLEAKING_HELDOUT_COHORT_PENDING")
    if not ic10_ready:
        residuals.append("INDEPENDENT_IC10_AUTHORIZATION_PENDING")
    if not execution_final:
        residuals.append("P41_EDGE_003_FINALITY_PENDING")
    if watch["status"] != "ARMED":
        residuals.append("FORWARD_POST_EDGE_WATCH_NOT_ARMED")
    admission = {
        "schema": "KC144.P43.AdmissionEvaluation.V1",
        "exact_enumeration": enumeration_ready,
        "cohort_complete": cohort_ready,
        "independent_ic10": ic10_ready,
        "all_external_gates_ready": (
            enumeration_ready and cohort_ready and ic10_ready
        ),
        "status": (
            "ADMITTED_FOR_EXACT_EXECUTION"
            if enumeration_ready and cohort_ready and ic10_ready
            else "HOLD"
        ),
        "truth_effect": "NONE",
    }
    admission["evaluation_digest"] = content_address(
        "kc144.p43.admission", admission
    )
    finality = {
        "schema": "KC144.P43.TransactionFinality.V1",
        "edge_id": "P41.EDGE.003",
        "execution_status": transaction["execution_status"],
        "execution_count": transaction["execution_count_after"],
        "ledger_valid": transaction["ledger_valid"],
        "replay_verdict": p42_verification["verdict"],
        "exactly_once_final": execution_final,
        "canonical_graph_mutations_this_cycle": transaction[
            "canonical_graph_mutations"
        ],
        "truth_effect": "NONE",
    }
    finality["finality_digest"] = content_address("kc144.p43.finality", finality)
    state = {
        "schema": "KC144.P43.StateDelta.V1",
        "public_parent_result_id": PUBLIC_P42_RESULT_ID,
        "external_gates_ready": admission["all_external_gates_ready"],
        "execution_status": transaction["execution_status"],
        "execution_count": transaction["execution_count_after"],
        "exactly_once_final": execution_final,
        "post_edge_watch": watch["status"],
        "post_edge_outcomes": watch["event_count"],
        "canonical_graph_mutations": transaction["canonical_graph_mutations"],
        "parallel_p43_merges": 0,
        "production_mutated": transaction["production_mutated"],
        "production_authority": (
            "EDGE_EXECUTION_ONLY" if execution_final else "HOLD"
        ),
        "truth_effect": "NONE",
        "residuals": sorted(residuals),
        "return": P43_ROUTE[-1],
        "next_seed": P43_NEXT_SEED,
    }
    state["delta_id"] = content_address("kc144.p43.state", state)
    payloads = (
        p43_public_parent(),
        p42["enumeration_evaluation"],
        p42["heldout_cohort"],
        p42["authorization_evaluation"],
        transaction,
        finality,
        watch,
        admission,
        p43_parallel_lineage(),
        state,
    )
    receipts = []
    for index, (lane, payload) in enumerate(zip(P43_LANES, payloads), 1):
        receipt = {
            "schema": "KC144.P43.LaneReceipt.V1",
            "lane_id": f"P43.L{index:02d}",
            "lane": lane,
            "payload_digest": content_address(
                f"kc144.p43.lane.{lane.lower()}", payload
            ),
            "return": P43_ROUTE[-1],
            "truth_effect": "NONE",
        }
        receipt["receipt_id"] = content_address("kc144.p43.lane-receipt", receipt)
        receipts.append(receipt)
    body = {
        "schema": "KC144.P43.Macrocycle.V1",
        "contract_digest": p43_contract()["contract_digest"],
        "namespace": namespace,
        "execution_time": execution_time,
        "public_parent_binding": p43_public_parent(),
        "inputs": inputs,
        "p42_transaction_cycle": p42,
        "admission_evaluation": admission,
        "transaction_finality": finality,
        "post_edge_watch": watch,
        "parallel_lineage": p43_parallel_lineage(),
        "lane_receipts": receipts,
        "state": state,
    }
    return {**body, "envelope_digest": content_address("kc144.p43.cycle", body)}


def verify_p43_cycle(value: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    inputs = value.get("inputs", {})
    if inputs.get("bundle_digest") != content_address(
        "kc144.p43.inputs",
        {key: item for key, item in inputs.items() if key != "bundle_digest"},
    ):
        errors.append("INPUT_BUNDLE_DIGEST")
    try:
        replay = compile_p43_cycle(
            signer_registry=inputs.get("signer_registry"),
            enumeration_witness=inputs.get("enumeration_witness"),
            heldout_events=inputs.get("heldout_events", []),
            edge_authorizations=inputs.get("edge_authorizations", []),
            execution_ledger=inputs.get("execution_ledger", []),
            post_edge_events=inputs.get("post_edge_events", []),
            namespace=str(value.get("namespace")),
            execution_time=str(value.get("execution_time")),
        )
    except Exception as error:
        errors.append(f"REPLAY_EXCEPTION:{type(error).__name__}")
        replay = {}
    if replay.get("envelope_digest") != value.get("envelope_digest"):
        errors.append("REPLAY_DRIFT")
    if value.get("public_parent_binding") != p43_public_parent():
        errors.append("PUBLIC_PARENT")
    if len(value.get("lane_receipts", [])) != len(P43_LANES):
        errors.append("LANE_COUNT")
    if value.get("state", {}).get("truth_effect") != "NONE":
        errors.append("TRUTH_INFLATION")
    body = {
        "schema": "KC144.P43.Verification.V1",
        "verdict": "PASS" if not errors else "FAIL",
        "errors": sorted(errors),
        "replay_envelope_digest": replay.get("envelope_digest"),
        "production_authority": value.get("state", {}).get(
            "production_authority", "HOLD"
        ),
        "truth_effect": "NONE",
    }
    return {**body, "verification_digest": content_address("kc144.p43.verify", body)}


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_bytes(canonical_bytes(value) + b"\n")


def compile_p43_release(
    output: str | Path,
    *,
    implementation_commit: str,
    implementation_tree: str,
) -> dict[str, Any]:
    if not GIT_SHA_RE.fullmatch(implementation_commit):
        raise P43RuntimeError("implementation commit must be a Git SHA")
    if not GIT_SHA_RE.fullmatch(implementation_tree):
        raise P43RuntimeError("implementation tree must be a Git SHA")
    destination = Path(output)
    destination.mkdir(parents=True, exist_ok=True)
    cycle = compile_p43_cycle()
    verification = verify_p43_cycle(cycle)
    release_body = {
        "schema": "KC144.P43.Release.V1",
        "release_id": "KC144_P43_ADMISSION_FINALITY_CANDIDATE_V1",
        "implementation": {
            "repository": "demeet2k/guild-hall",
            "commit": implementation_commit,
            "tree": implementation_tree,
        },
        "public_parent_result_id": PUBLIC_P42_RESULT_ID,
        "public_parent_release_digest": PUBLIC_P42_RELEASE_DIGEST,
        "status": "CANDIDATE_HOLD",
        "exact_enumeration_witnesses": 0,
        "heldout_outcomes": 0,
        "independent_ic10_authorizations": 0,
        "third_edge": "HELD_NOT_EXECUTED",
        "edge_execution_count": 0,
        "post_edge_watch": "HELD_NOT_ARMED",
        "canonical_graph_mutations": 0,
        "production_authority": "HOLD",
        "truth_effect": "NONE",
        "verification_verdict": verification["verdict"],
        "next_seed": P43_NEXT_SEED,
    }
    release_digest = content_address("kc144.p43.release", release_body)
    release = {
        **release_body,
        "release_digest": release_digest,
        "result_id": "KC144.P43.CANDIDATE::" + release_digest.split(":", 1)[1][:24],
    }
    artifacts = {
        "p43_contract_v1.json": p43_contract(),
        "p43_macrocycle_v1.json": cycle,
        "p43_admission_evaluation_v1.json": cycle["admission_evaluation"],
        "p43_transaction_finality_v1.json": cycle["transaction_finality"],
        "p43_post_edge_watch_v1.json": cycle["post_edge_watch"],
        "p43_parallel_lineage_v1.json": cycle["parallel_lineage"],
        "p43_verification_v1.json": verification,
        "p43_release_v1.json": release,
    }
    for name, value in artifacts.items():
        _write_json(destination / name, value)
    checksums = []
    for name in sorted(artifacts):
        checksums.append(
            f"{hashlib.sha256((destination / name).read_bytes()).hexdigest()}  {name}"
        )
    (destination / "SHA256SUMS").write_text(
        "\n".join(checksums) + "\n", encoding="utf-8"
    )
    return release
