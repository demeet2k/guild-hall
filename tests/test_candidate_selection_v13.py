from __future__ import annotations

import base64
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
)

from kc144_crystal.ceremony_v10 import ROLES
from kc144_crystal.dispatch_v11 import (
    issue_governance_challenge_batch,
)
from kc144_crystal.population import digest
from kc144_crystal.selection_v13 import (
    CandidateNomination,
    candidate_pair_audit,
    candidate_registry,
    candidate_registry_integrity,
    solve_candidate_cohort,
    verify_candidate_nomination,
)
from kc144_crystal.v11 import compile_governance_dispatch_runtime
from kc144_crystal.v13 import compile_candidate_selection_runtime


CHECKED = "2026-07-27T12:00:00+00:00"
ISSUED = "2026-07-27T08:39:35+00:00"
EXPIRES = "2026-08-26T08:39:35+00:00"


def public_b64() -> str:
    private = Ed25519PrivateKey.generate()
    return base64.b64encode(
        private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    ).decode("ascii")


def nomination(
    index: int,
    roles: tuple[str, ...],
    **overrides,
) -> CandidateNomination:
    values = {
        "nomination_id": f"V13-NOMINATION-{index}",
        "candidate_id": f"V13-CANDIDATE-{index}",
        "status": "NOMINATED",
        "test_only": False,
        "algorithm": "ED25519",
        "public_key_b64": public_b64(),
        "eligible_roles": roles,
        "identity_claim_root": digest(("identity", index)),
        "external_identity_verification_root": digest(
            ("identity-verification", index)
        ),
        "external_independence_verification_root": digest(
            ("independence-verification", index)
        ),
        "institution_root": digest(("institution", index)),
        "lineage_root": digest(("lineage", index)),
        "jurisdiction_root": digest(("jurisdiction", index)),
        "primary_domain_root": digest(("domain", index)),
        "authority_root": digest(("authority", index)),
        "funding_root": digest(("funding", index)),
        "data_control_root": digest(("data-control", index)),
        "staff_control_root": digest(("staff-control", index)),
        "technology_control_root": digest(
            ("technology-control", index)
        ),
        "conflict_disclosure_root": digest(("conflict", index)),
        "conflict_status": "CLEAR",
        "conflict_resolution_root": None,
        "nomination_evidence_root": digest(
            ("nomination-evidence", index)
        ),
        "not_before": "2026-01-01T00:00:00+00:00",
        "not_after": "2027-01-01T00:00:00+00:00",
    }
    values.update(overrides)
    return CandidateNomination(**values)


def unique_cohort() -> tuple[CandidateNomination, ...]:
    return tuple(
        nomination(index, (role,))
        for index, role in enumerate(ROLES, start=1)
    )


class NominationTests(unittest.TestCase):
    def test_well_formed_nomination_is_declared_not_authorized(self) -> None:
        report = verify_candidate_nomination(
            nomination(1, (ROLES[0],)),
            checked_at=CHECKED,
        )
        self.assertEqual(report["verdict"], "PASS")
        self.assertFalse(report["governance_authority_granted"])

    def test_test_nomination_is_held(self) -> None:
        report = verify_candidate_nomination(
            nomination(1, (ROLES[0],), test_only=True),
            checked_at=CHECKED,
        )
        self.assertEqual(report["verdict"], "HOLD")
        self.assertFalse(report["checks"]["not_test_only"])

    def test_registry_tampering_fails_integrity(self) -> None:
        registry = candidate_registry(unique_cohort())
        self.assertTrue(candidate_registry_integrity(registry))
        registry["nomination_count"] = 4
        self.assertFalse(candidate_registry_integrity(registry))


class IndependenceGraphTests(unittest.TestCase):
    def test_distinct_pair_passes(self) -> None:
        report = candidate_pair_audit(
            nomination(1, (ROLES[0],)),
            nomination(2, (ROLES[1],)),
        )
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(report["collisions"], [])

    def test_shared_institution_is_a_collision(self) -> None:
        shared = digest("shared institution")
        report = candidate_pair_audit(
            nomination(
                1,
                (ROLES[0],),
                institution_root=shared,
            ),
            nomination(
                2,
                (ROLES[1],),
                institution_root=shared,
            ),
        )
        self.assertEqual(report["verdict"], "HOLD")
        self.assertIn("institution_root", report["collisions"])

    def test_shared_funding_is_a_hard_control_edge(self) -> None:
        shared = digest("shared funding")
        report = candidate_pair_audit(
            nomination(1, (ROLES[0],), funding_root=shared),
            nomination(2, (ROLES[1],), funding_root=shared),
        )
        self.assertIn("funding_root", report["hard_control_edges"])
        self.assertFalse(report["compatible"])


class CohortSolverTests(unittest.TestCase):
    def test_empty_registry_stops_at_nomination_barrier(self) -> None:
        report = solve_candidate_cohort((), checked_at=CHECKED)
        self.assertEqual(report["solution_status"], "NO_COHORT")
        self.assertEqual(
            report["barrier"],
            "FIVE_EXTERNAL_CANDIDATE_NOMINATIONS_REQUIRED",
        )
        self.assertIsNone(report["selected_cohort"])

    def test_unique_cohort_requires_all_ten_pair_audits(self) -> None:
        report = solve_candidate_cohort(
            unique_cohort(),
            checked_at=CHECKED,
        )
        self.assertEqual(
            report["solution_status"],
            "UNIQUE_PROVISIONAL_COHORT",
        )
        self.assertEqual(report["selected_pairwise_audits"], 10)
        self.assertEqual(set(report["selected_cohort"]), set(ROLES))
        self.assertFalse(report["governance_authority_granted"])

    def test_multiple_cohorts_are_not_arbitrarily_selected(self) -> None:
        nominations = tuple(
            nomination(index, tuple(ROLES))
            for index in range(1, 6)
        )
        report = solve_candidate_cohort(
            nominations,
            checked_at=CHECKED,
        )
        self.assertEqual(report["solution_status"], "MULTIPLE_COHORTS")
        self.assertEqual(len(report["candidate_cohorts"]), 2)
        self.assertIsNone(report["selected_cohort"])
        self.assertEqual(
            report["barrier"],
            "SOURCE_AUTHORIZED_COHORT_SELECTION_REQUIRED",
        )

    def test_required_shared_institution_produces_no_cohort(self) -> None:
        values = list(unique_cohort())
        values[1] = replace(
            values[1],
            institution_root=values[0].institution_root,
        )
        report = solve_candidate_cohort(values, checked_at=CHECKED)
        self.assertEqual(report["solution_status"], "NO_COHORT")
        self.assertEqual(
            report["barrier"],
            "INDEPENDENCE_QUALIFIED_COHORT_REQUIRED",
        )

    def test_budget_exhaustion_never_implies_uniqueness(self) -> None:
        nominations = tuple(
            nomination(index, tuple(ROLES))
            for index in range(1, 6)
        )
        report = solve_candidate_cohort(
            nominations,
            checked_at=CHECKED,
            node_budget=1,
        )
        self.assertEqual(
            report["solution_status"],
            "SOLVER_BUDGET_EXHAUSTED",
        )
        self.assertIsNone(report["selected_cohort"])


class V13RuntimeTests(unittest.TestCase):
    def test_all_v13_schemas_parse(self) -> None:
        root = Path(__file__).resolve().parents[1]
        paths = sorted(
            (root / "schemas" / "kc144").glob("*-v13.schema.json")
        )
        self.assertEqual(len(paths), 7)
        for path in paths:
            self.assertIsInstance(
                json.loads(path.read_text(encoding="utf-8")),
                dict,
            )

    def test_live_runtime_preserves_empty_candidate_registry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            compile_governance_dispatch_runtime(temporary)
            plan = json.loads(
                (
                    Path(temporary)
                    / "governance_dispatch_plan_v11.json"
                ).read_text(encoding="utf-8")
            )
            batch = issue_governance_challenge_batch(
                authority_registry_digest=plan[
                    "authority_registry_digest"
                ],
                handoff_bundle_root=plan["handoff_bundle_root"],
                issued_at=ISSUED,
                expires_at=EXPIRES,
            )
            release = compile_candidate_selection_runtime(
                temporary,
                challenge_batch=batch,
            )
            self.assertEqual(release["verdict"], "PASS")
            self.assertEqual(release["nomination_count"], 0)
            self.assertEqual(release["admitted_candidate_count"], 0)
            self.assertIsNone(release["selected_cohort"])
            self.assertEqual(
                release["operational_status"],
                "FIVE_EXTERNAL_CANDIDATE_NOMINATIONS_REQUIRED",
            )


if __name__ == "__main__":
    unittest.main()
