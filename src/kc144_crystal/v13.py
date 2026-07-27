from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .ceremony_v10 import GovernanceEnrollmentResponse
from .population import digest
from .selection_v13 import (
    SELECTION_ID,
    CandidateNomination,
    candidate_registry,
    candidate_registry_integrity,
    candidate_selection_contract,
    solve_candidate_cohort,
)
from .v12 import compile_participant_handoff_runtime


def compile_candidate_selection_runtime(
    output_directory: str | Path,
    *,
    challenge_batch: Mapping[str, Any],
    nominations: Sequence[CandidateNomination] = (),
    checked_at: str | None = None,
    node_budget: int = 100_000,
    ledger: Mapping[str, Any] | None = None,
    authority_registry: Mapping[str, Any] | None = None,
    governance_registry: Mapping[str, Any] | None = None,
    responses: Sequence[GovernanceEnrollmentResponse] = (),
) -> dict[str, Any]:
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    batch = dict(challenge_batch)
    effective_time = checked_at or str(batch["issued_at"])
    v12_release = compile_participant_handoff_runtime(
        output,
        ledger=ledger,
        authority_registry=authority_registry,
        governance_registry=governance_registry,
        challenge_batch=batch,
        responses=responses,
        verified_at=checked_at,
    )
    contract = candidate_selection_contract()
    registry = candidate_registry(nominations)
    solver = solve_candidate_cohort(
        nominations,
        checked_at=effective_time,
        node_budget=node_budget,
    )
    internal_checks = {
        "v12_runtime_pass": v12_release["verdict"] == "PASS",
        "selection_identity_exact": contract["selection_id"]
        == SELECTION_ID,
        "registry_integrity": candidate_registry_integrity(registry),
        "ten_pair_law_exact": contract["required_pairwise_audits"] == 10,
        "solver_fail_closed": (
            solver["selected_cohort"] is None
            if solver["solution_status"]
            in {
                "NO_COHORT",
                "MULTIPLE_COHORTS",
                "SOLVER_BUDGET_EXHAUSTED",
            }
            else solver["selected_pairwise_audits"] == 10
        ),
        "no_inferred_live_candidates": (
            len(nominations) > 0
            or (
                solver["admitted_candidate_count"] == 0
                and solver["selected_cohort"] is None
            )
        ),
        "no_authority_grant": not solver[
            "governance_authority_granted"
        ],
        "no_delivery_claim": not solver["packets_delivered"],
        "truth_effect_none": solver["truth_effect"] == "NONE",
    }
    internal_verdict = (
        "PASS" if all(internal_checks.values()) else "FAIL"
    )
    runtime_body = {
        "schema": "KC144.CandidateSelectionRuntimeState.V13",
        "release": "KC144.CANDIDATE.SELECTION.RUNTIME.V13",
        "parent_release": v12_release["release"],
        "selection_id": SELECTION_ID,
        "selection_contract_digest": contract["contract_digest"],
        "candidate_registry_root": registry["registry_root"],
        "conflict_graph_root": solver["conflict_graph"]["graph_root"],
        "solver_digest": solver["solver_digest"],
        "nomination_count": solver["nomination_count"],
        "admitted_candidate_count": solver[
            "admitted_candidate_count"
        ],
        "solution_status": solver["solution_status"],
        "selected_cohort": solver["selected_cohort"],
        "selected_pairwise_audits": solver[
            "selected_pairwise_audits"
        ],
        "internal_readiness": {
            "verdict": internal_verdict,
            "checks": internal_checks,
        },
        "barrier": solver["barrier"],
        "governance_activated": False,
        "production_certificate_issued": False,
        "production_truth_effect": "NONE",
        "frozen_crystal_mutated": False,
        "next_seed": (
            "KC144.V13::INGEST-REAL-CANDIDATE-NOMINATIONS-AND-"
            "SOLVE-INDEPENDENCE-QUALIFIED-COHORT"
            if solver["solution_status"] == "NO_COHORT"
            else f"KC144.V13::{solver['barrier']}"
        ),
    }
    runtime = {
        **runtime_body,
        "runtime_state_digest": digest(runtime_body),
    }
    documents = {
        "candidate_selection_contract_v13.json": contract,
        "candidate_nomination_registry_v13.json": registry,
        "candidate_conflict_graph_v13.json": solver["conflict_graph"],
        "candidate_cohort_solver_v13.json": solver,
        "candidate_selection_runtime_state_v13.json": runtime,
    }
    for filename, document in documents.items():
        (output / filename).write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    release_body = {
        "schema": "KC144.CandidateSelectionRelease.V13",
        "release": "KC144.CANDIDATE.SELECTION.RUNTIME.V13",
        "parent_release": v12_release["release"],
        "verdict": (
            "PASS"
            if v12_release["verdict"] == "PASS"
            and internal_verdict == "PASS"
            else "FAIL"
        ),
        "operational_status": solver["barrier"],
        "nomination_count": solver["nomination_count"],
        "admitted_candidate_count": solver[
            "admitted_candidate_count"
        ],
        "solution_status": solver["solution_status"],
        "selected_cohort": solver["selected_cohort"],
        "selected_pairwise_audits": solver[
            "selected_pairwise_audits"
        ],
        "governance_activated": False,
        "production_certificate_issued": False,
        "frozen_crystal_mutated": False,
        "added_artifacts": sorted(documents),
        "next_seed": runtime["next_seed"],
    }
    release = {**release_body, "release_digest": digest(release_body)}
    (output / "candidate_selection_release_v13.json").write_text(
        json.dumps(release, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return release
