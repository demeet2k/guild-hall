from __future__ import annotations

import base64
import binascii
from dataclasses import asdict, dataclass
from datetime import datetime
from itertools import combinations
from typing import Any, Mapping, Sequence

from .ceremony_v10 import ROLES
from .population import digest


SELECTION_ID = "KC144.CANDIDATE.COHORT.SELECTION.V13"
SHA256_PREFIX = "sha256:"
CONTROL_FIELDS = (
    "authority_root",
    "funding_root",
    "data_control_root",
    "staff_control_root",
    "technology_control_root",
)
INDEPENDENCE_FIELDS = (
    "identity_claim_root",
    "public_key_b64",
    "institution_root",
    "lineage_root",
    "jurisdiction_root",
    "primary_domain_root",
    *CONTROL_FIELDS,
)


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if not value.startswith(SHA256_PREFIX) or len(value) != 71:
        return False
    try:
        int(value[7:], 16)
    except ValueError:
        return False
    return value[7:] == value[7:].lower()


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed


@dataclass(frozen=True)
class CandidateNomination:
    nomination_id: str
    candidate_id: str
    status: str
    test_only: bool
    algorithm: str
    public_key_b64: str
    eligible_roles: tuple[str, ...]
    identity_claim_root: str
    external_identity_verification_root: str
    external_independence_verification_root: str
    institution_root: str
    lineage_root: str
    jurisdiction_root: str
    primary_domain_root: str
    authority_root: str
    funding_root: str
    data_control_root: str
    staff_control_root: str
    technology_control_root: str
    conflict_disclosure_root: str
    conflict_status: str
    conflict_resolution_root: str | None
    nomination_evidence_root: str
    not_before: str
    not_after: str

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
    ) -> "CandidateNomination":
        body = dict(value)
        body.pop("schema", None)
        body["eligible_roles"] = tuple(body["eligible_roles"])
        return cls(**body)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "KC144.CandidateNomination.V13",
            **asdict(self),
            "eligible_roles": list(self.eligible_roles),
        }


def candidate_selection_contract() -> dict[str, Any]:
    body = {
        "schema": "KC144.CandidateSelectionContract.V13",
        "selection_id": SELECTION_ID,
        "roles": list(ROLES),
        "required_candidates": 5,
        "required_pairwise_audits": 10,
        "independence_dimensions": list(INDEPENDENCE_FIELDS),
        "hard_control_dimensions": list(CONTROL_FIELDS),
        "admission_law": (
            "nominations are declared candidates only; syntactic admission "
            "and graph selection grant no governance authority"
        ),
        "cohort_law": (
            "one distinct eligible candidate fills each role and every one "
            "of the ten candidate pairs must be free of identity, key, "
            "institution, lineage, jurisdiction, domain, and hard-control "
            "collisions"
        ),
        "ambiguity_law": (
            "NO_COHORT and MULTIPLE_COHORTS both produce no selected cohort; "
            "multiple lawful cohorts require explicit source-authorized "
            "selection"
        ),
        "budget_law": (
            "solver budget exhaustion is HOLD and never implies uniqueness"
        ),
        "promotion_law": (
            "even a unique cohort is provisional until exact V12 packets "
            "are delivered and V10 signed responses independently verify"
        ),
        "truth_effect": "NONE",
    }
    return {**body, "contract_digest": digest(body)}


def verify_candidate_nomination(
    nomination: CandidateNomination,
    *,
    checked_at: str,
) -> dict[str, Any]:
    public_key_valid = False
    time_valid = False
    try:
        public_key_valid = (
            len(
                base64.b64decode(
                    nomination.public_key_b64,
                    validate=True,
                )
            )
            == 32
        )
        checked = _parse_time(checked_at)
        before = _parse_time(nomination.not_before)
        after = _parse_time(nomination.not_after)
        time_valid = before <= checked <= after and before < after
    except (ValueError, TypeError, binascii.Error):
        pass
    root_fields = (
        nomination.identity_claim_root,
        nomination.external_identity_verification_root,
        nomination.external_independence_verification_root,
        nomination.institution_root,
        nomination.lineage_root,
        nomination.jurisdiction_root,
        nomination.primary_domain_root,
        nomination.authority_root,
        nomination.funding_root,
        nomination.data_control_root,
        nomination.staff_control_root,
        nomination.technology_control_root,
        nomination.conflict_disclosure_root,
        nomination.nomination_evidence_root,
    )
    conflict_disposed = (
        nomination.conflict_status == "CLEAR"
        and nomination.conflict_resolution_root is None
    ) or (
        nomination.conflict_status == "RESOLVED"
        and _is_sha256(nomination.conflict_resolution_root)
    )
    checks = {
        "nomination_id_present": bool(nomination.nomination_id.strip()),
        "candidate_id_present": bool(nomination.candidate_id.strip()),
        "status_nominated": nomination.status == "NOMINATED",
        "not_test_only": not nomination.test_only,
        "algorithm_ed25519": nomination.algorithm == "ED25519",
        "public_key_well_formed": public_key_valid,
        "eligible_roles_nonempty_valid": (
            bool(nomination.eligible_roles)
            and len(nomination.eligible_roles)
            == len(set(nomination.eligible_roles))
            and set(nomination.eligible_roles).issubset(ROLES)
        ),
        "all_roots_valid": all(_is_sha256(root) for root in root_fields),
        "conflict_disposed": conflict_disposed,
        "validity_window_current": time_valid,
    }
    verdict = "PASS" if all(checks.values()) else "HOLD"
    body = {
        "schema": "KC144.CandidateNominationVerification.V13",
        "nomination_id": nomination.nomination_id,
        "candidate_id": nomination.candidate_id,
        "eligible_roles": list(nomination.eligible_roles),
        "verdict": verdict,
        "status": (
            "DECLARED_CANDIDATE_ADMITTED_TO_SOLVER"
            if verdict == "PASS"
            else "NOMINATION_HOLD"
        ),
        "checks": checks,
        "governance_authority_granted": False,
        "truth_effect": "NONE",
    }
    return {**body, "verification_digest": digest(body)}


def candidate_pair_audit(
    left: CandidateNomination,
    right: CandidateNomination,
) -> dict[str, Any]:
    collisions = [
        field
        for field in INDEPENDENCE_FIELDS
        if getattr(left, field) == getattr(right, field)
    ]
    hard_control_edges = [
        field for field in CONTROL_FIELDS if field in collisions
    ]
    body = {
        "schema": "KC144.CandidatePairAudit.V13",
        "left_candidate_id": left.candidate_id,
        "right_candidate_id": right.candidate_id,
        "collisions": collisions,
        "hard_control_edges": hard_control_edges,
        "compatible": not collisions,
        "verdict": "PASS" if not collisions else "HOLD",
    }
    return {**body, "audit_digest": digest(body)}


def candidate_registry(
    nominations: Sequence[CandidateNomination],
) -> dict[str, Any]:
    ordered = sorted(
        nominations,
        key=lambda nomination: (
            nomination.candidate_id,
            nomination.nomination_id,
        ),
    )
    body = {
        "schema": "KC144.CandidateNominationRegistry.V13",
        "selection_id": SELECTION_ID,
        "nominations": [
            nomination.to_dict() for nomination in ordered
        ],
        "nomination_count": len(ordered),
        "authority_effect": "NONE",
        "truth_effect": "NONE",
    }
    return {**body, "registry_root": digest(body)}


def candidate_registry_integrity(registry: Mapping[str, Any]) -> bool:
    expected_keys = {
        "schema",
        "selection_id",
        "nominations",
        "nomination_count",
        "authority_effect",
        "truth_effect",
        "registry_root",
    }
    try:
        nominations = [
            CandidateNomination.from_dict(value)
            for value in registry["nominations"]
        ]
        expected = candidate_registry(nominations)
    except (KeyError, TypeError, ValueError):
        return False
    return set(registry) == expected_keys and dict(registry) == expected


def solve_candidate_cohort(
    nominations: Sequence[CandidateNomination],
    *,
    checked_at: str,
    node_budget: int = 100_000,
) -> dict[str, Any]:
    if node_budget < 1:
        raise ValueError("node budget must be positive")
    ordered = sorted(
        nominations,
        key=lambda nomination: (
            nomination.candidate_id,
            nomination.nomination_id,
        ),
    )
    verification_rows = [
        verify_candidate_nomination(
            nomination,
            checked_at=checked_at,
        )
        for nomination in ordered
    ]
    globally_duplicated_nomination_ids = {
        value
        for value in {
            nomination.nomination_id for nomination in ordered
        }
        if sum(
            row.nomination_id == value for row in ordered
        )
        > 1
    }
    globally_duplicated_candidate_ids = {
        value
        for value in {
            nomination.candidate_id for nomination in ordered
        }
        if sum(row.candidate_id == value for row in ordered) > 1
    }
    admitted = [
        nomination
        for nomination, report in zip(ordered, verification_rows)
        if report["verdict"] == "PASS"
        and nomination.nomination_id
        not in globally_duplicated_nomination_ids
        and nomination.candidate_id
        not in globally_duplicated_candidate_ids
    ]
    pair_reports = {
        tuple(
            sorted((left.candidate_id, right.candidate_id))
        ): candidate_pair_audit(left, right)
        for left, right in combinations(admitted, 2)
    }
    candidates_by_role = {
        role: [
            candidate
            for candidate in admitted
            if role in candidate.eligible_roles
        ]
        for role in ROLES
    }
    search_roles = sorted(
        ROLES,
        key=lambda role: (len(candidates_by_role[role]), ROLES.index(role)),
    )
    solutions: list[dict[str, CandidateNomination]] = []
    explored_nodes = 0
    budget_exhausted = False

    def compatible(
        candidate: CandidateNomination,
        assignment: Mapping[str, CandidateNomination],
    ) -> bool:
        if any(
            prior.candidate_id == candidate.candidate_id
            for prior in assignment.values()
        ):
            return False
        return all(
            pair_reports[
                tuple(
                    sorted(
                        (
                            prior.candidate_id,
                            candidate.candidate_id,
                        )
                    )
                )
            ]["compatible"]
            for prior in assignment.values()
        )

    def search(
        index: int,
        assignment: dict[str, CandidateNomination],
    ) -> None:
        nonlocal explored_nodes, budget_exhausted
        if len(solutions) >= 2 or budget_exhausted:
            return
        if index == len(search_roles):
            solutions.append(dict(assignment))
            return
        role = search_roles[index]
        for candidate in candidates_by_role[role]:
            explored_nodes += 1
            if explored_nodes > node_budget:
                budget_exhausted = True
                return
            if compatible(candidate, assignment):
                assignment[role] = candidate
                search(index + 1, assignment)
                assignment.pop(role)
            if len(solutions) >= 2 or budget_exhausted:
                return

    search(0, {})
    serialized_solutions = [
        {
            role: solution[role].candidate_id
            for role in ROLES
        }
        for solution in solutions
    ]
    selected_cohort = None
    selected_pair_audits: list[dict[str, Any]] = []
    if budget_exhausted:
        solution_status = "SOLVER_BUDGET_EXHAUSTED"
        barrier = "SOLVER_BUDGET_OR_SEARCH_REFINEMENT_REQUIRED"
    elif not solutions:
        solution_status = "NO_COHORT"
        barrier = (
            "FIVE_EXTERNAL_CANDIDATE_NOMINATIONS_REQUIRED"
            if not nominations
            else "INDEPENDENCE_QUALIFIED_COHORT_REQUIRED"
        )
    elif len(solutions) > 1:
        solution_status = "MULTIPLE_COHORTS"
        barrier = "SOURCE_AUTHORIZED_COHORT_SELECTION_REQUIRED"
    else:
        solution_status = "UNIQUE_PROVISIONAL_COHORT"
        barrier = "FIVE_PACKET_DELIVERIES_REQUIRED"
        selected_cohort = serialized_solutions[0]
        selected_ids = set(selected_cohort.values())
        selected_pair_audits = [
            report
            for pair, report in sorted(pair_reports.items())
            if set(pair).issubset(selected_ids)
        ]
    conflict_graph = {
        "schema": "KC144.CandidateConflictGraph.V13",
        "selection_id": SELECTION_ID,
        "nodes": [
            {
                "candidate_id": nomination.candidate_id,
                "nomination_id": nomination.nomination_id,
                "admitted": nomination in admitted,
                "eligible_roles": list(nomination.eligible_roles),
            }
            for nomination in ordered
        ],
        "pair_audits": [
            report for _, report in sorted(pair_reports.items())
        ],
        "node_count": len(ordered),
        "admitted_node_count": len(admitted),
        "edge_count": len(pair_reports),
        "truth_effect": "NONE",
    }
    conflict_graph = {
        **conflict_graph,
        "graph_root": digest(conflict_graph),
    }
    body = {
        "schema": "KC144.CandidateCohortSolver.V13",
        "selection_id": SELECTION_ID,
        "checked_at": checked_at,
        "node_budget": node_budget,
        "explored_nodes": explored_nodes,
        "budget_exhausted": budget_exhausted,
        "nomination_count": len(ordered),
        "admitted_candidate_count": len(admitted),
        "nomination_verifications": verification_rows,
        "duplicate_nomination_ids": sorted(
            globally_duplicated_nomination_ids
        ),
        "duplicate_candidate_ids": sorted(
            globally_duplicated_candidate_ids
        ),
        "conflict_graph": conflict_graph,
        "solution_status": solution_status,
        "candidate_cohorts": serialized_solutions,
        "selected_cohort": selected_cohort,
        "selected_pair_audits": selected_pair_audits,
        "required_pairwise_audits": 10,
        "selected_pairwise_audits": len(selected_pair_audits),
        "barrier": barrier,
        "governance_authority_granted": False,
        "packets_delivered": False,
        "truth_effect": "NONE",
    }
    return {**body, "solver_digest": digest(body)}
