from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .dispatch_v11 import challenge_batch_integrity
from .nomination_v14 import (
    INTAKE_ID,
    SignedCandidateNomination,
    cohort_packet_assignment_manifest,
    cohort_packet_assignment_manifest_integrity,
    nomination_call_manifest,
    nomination_call_manifest_integrity,
    nomination_intake_contract,
    nomination_receipt_ledger,
    nomination_receipt_ledger_integrity,
    nomination_role_call,
    nomination_role_call_integrity,
    public_nomination_receipt_ledger,
)
from .ceremony_v10 import ROLES
from .population import digest
from .v13 import compile_candidate_selection_runtime


def _next_seed(solution_status: str, submission_count: int) -> str:
    if solution_status == "UNIQUE_PROVISIONAL_COHORT":
        return (
            "KC144.V14::DELIVER-FIVE-BOUND-PARTICIPANT-PACKETS-AND-"
            "ROUTE-SIGNED-RETURNS"
        )
    if solution_status == "MULTIPLE_COHORTS":
        return (
            "KC144.V14::OBTAIN-SOURCE-AUTHORIZED-COHORT-SELECTION"
        )
    if solution_status == "SOLVER_BUDGET_EXHAUSTED":
        return (
            "KC144.V14::REFINE-CANDIDATE-SET-OR-INCREASE-BOUNDED-"
            "SOLVER-BUDGET"
        )
    if submission_count:
        return (
            "KC144.V14::INGEST-ADDITIONAL-INDEPENDENCE-QUALIFIED-"
            "SIGNED-NOMINATIONS"
        )
    return (
        "KC144.V14::PUBLISH-FIVE-ROLE-CALLS-AND-INGEST-REAL-SIGNED-"
        "NOMINATIONS"
    )


def compile_nomination_intake_runtime(
    output_directory: str | Path,
    *,
    challenge_batch: Mapping[str, Any],
    envelopes: Sequence[SignedCandidateNomination] = (),
    checked_at: str | None = None,
    node_budget: int = 100_000,
) -> dict[str, Any]:
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    batch = dict(challenge_batch)
    effective_time = checked_at or str(batch["issued_at"])
    ledger_internal = nomination_receipt_ledger(
        envelopes,
        checked_at=effective_time,
    )
    admitted_nominations = ledger_internal["_admitted_nominations"]
    receipt_ledger = public_nomination_receipt_ledger(ledger_internal)
    v13_release = compile_candidate_selection_runtime(
        output,
        challenge_batch=batch,
        nominations=admitted_nominations,
        checked_at=effective_time,
        node_budget=node_budget,
    )
    solver = json.loads(
        (output / "candidate_cohort_solver_v13.json").read_text(
            encoding="utf-8"
        )
    )
    contract = nomination_intake_contract()
    calls = [nomination_role_call(batch, role) for role in ROLES]
    call_manifest = nomination_call_manifest(batch, calls)
    assignment = cohort_packet_assignment_manifest(
        batch,
        calls,
        admitted_nominations,
        solver,
    )
    next_seed = _next_seed(
        str(solver["solution_status"]),
        len(envelopes),
    )
    internal_checks = {
        "v13_runtime_pass": v13_release["verdict"] == "PASS",
        "batch_integrity": challenge_batch_integrity(batch),
        "five_role_calls_exact": (
            len(calls) == 5
            and [call["role"] for call in calls] == list(ROLES)
        ),
        "all_role_calls_integral": all(
            nomination_role_call_integrity(batch, call)
            for call in calls
        ),
        "call_manifest_integrity": nomination_call_manifest_integrity(
            batch,
            call_manifest,
            calls,
        ),
        "receipt_ledger_integrity": nomination_receipt_ledger_integrity(
            envelopes,
            receipt_ledger,
            checked_at=effective_time,
        ),
        "assignment_manifest_integrity": (
            cohort_packet_assignment_manifest_integrity(
                batch,
                calls,
                admitted_nominations,
                solver,
                assignment,
            )
        ),
        "solver_receipt_count_exact": (
            solver["nomination_count"]
            == receipt_ledger["admitted_count"]
        ),
        "no_fabricated_publication": (
            call_manifest["published_count"] == 0
            and not call_manifest["publication_claimed"]
        ),
        "no_fabricated_delivery": (
            assignment["addressed_packets"] == 0
            and assignment["delivered_packets"] == 0
        ),
        "no_authority_grant": (
            not assignment["governance_authority_granted"]
        ),
        "truth_effect_none": assignment["truth_effect"] == "NONE",
    }
    internal_verdict = (
        "PASS" if all(internal_checks.values()) else "FAIL"
    )
    runtime_body = {
        "schema": "KC144.NominationIntakeRuntimeState.V14",
        "release": "KC144.CANDIDATE.NOMINATION.INTAKE.RUNTIME.V14",
        "parent_release": v13_release["release"],
        "intake_id": INTAKE_ID,
        "intake_contract_digest": contract["contract_digest"],
        "batch_id": batch["batch_id"],
        "batch_root": batch["batch_root"],
        "call_manifest_root": call_manifest["manifest_root"],
        "receipt_ledger_root": receipt_ledger["ledger_root"],
        "assignment_root": assignment["assignment_root"],
        "prepared_role_calls": 5,
        "published_role_calls": 0,
        "submission_count": receipt_ledger["submission_count"],
        "admitted_submission_count": receipt_ledger["admitted_count"],
        "held_submission_count": receipt_ledger["held_count"],
        "solution_status": solver["solution_status"],
        "assigned_packet_count": assignment["assigned_count"],
        "addressed_packet_count": 0,
        "delivered_packet_count": 0,
        "internal_readiness": {
            "verdict": internal_verdict,
            "checks": internal_checks,
        },
        "barrier": assignment["barrier"],
        "governance_activated": False,
        "production_certificate_issued": False,
        "production_truth_effect": "NONE",
        "frozen_crystal_mutated": False,
        "next_seed": next_seed,
    }
    runtime = {
        **runtime_body,
        "runtime_state_digest": digest(runtime_body),
    }
    documents: dict[str, Mapping[str, Any]] = {
        "nomination_intake_contract_v14.json": contract,
        "nomination_call_manifest_v14.json": call_manifest,
        "nomination_receipt_ledger_v14.json": receipt_ledger,
        "cohort_packet_assignment_manifest_v14.json": assignment,
        "nomination_intake_runtime_state_v14.json": runtime,
    }
    for call in calls:
        role_slug = str(call["role"]).lower()
        documents[f"nomination_call_{role_slug}_v14.json"] = call
    for filename, document in documents.items():
        (output / filename).write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    release_body = {
        "schema": "KC144.NominationIntakeRelease.V14",
        "release": "KC144.CANDIDATE.NOMINATION.INTAKE.RUNTIME.V14",
        "parent_release": v13_release["release"],
        "verdict": (
            "PASS"
            if v13_release["verdict"] == "PASS"
            and internal_verdict == "PASS"
            else "FAIL"
        ),
        "operational_status": assignment["barrier"],
        "prepared_role_calls": 5,
        "published_role_calls": 0,
        "submission_count": receipt_ledger["submission_count"],
        "admitted_submission_count": receipt_ledger["admitted_count"],
        "held_submission_count": receipt_ledger["held_count"],
        "solution_status": solver["solution_status"],
        "assigned_packet_count": assignment["assigned_count"],
        "addressed_packet_count": 0,
        "delivered_packet_count": 0,
        "governance_activated": False,
        "production_certificate_issued": False,
        "frozen_crystal_mutated": False,
        "added_artifacts": sorted(documents),
        "next_seed": next_seed,
    }
    release = {**release_body, "release_digest": digest(release_body)}
    (output / "nomination_intake_release_v14.json").write_text(
        json.dumps(release, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return release
