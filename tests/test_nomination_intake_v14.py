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
from kc144_crystal.nomination_v14 import (
    SIGNATURE_DOMAIN,
    SignedCandidateNomination,
    cohort_packet_assignment_manifest,
    nomination_call_manifest,
    nomination_call_manifest_integrity,
    nomination_receipt_ledger,
    nomination_role_call,
    nomination_role_call_integrity,
    nomination_signing_bytes,
    public_nomination_receipt_ledger,
    verify_signed_candidate_nomination,
)
from kc144_crystal.population import digest
from kc144_crystal.selection_v13 import (
    CandidateNomination,
    solve_candidate_cohort,
)
from kc144_crystal.v11 import compile_governance_dispatch_runtime
from kc144_crystal.v14 import compile_nomination_intake_runtime


CHECKED = "2026-07-27T12:00:00+00:00"
ISSUED = "2026-07-27T08:39:35+00:00"
EXPIRES = "2026-08-26T08:39:35+00:00"


def batch_fixture() -> dict:
    return issue_governance_challenge_batch(
        authority_registry_digest=digest("V14 authority"),
        handoff_bundle_root=digest("V14 handoff"),
        issued_at=ISSUED,
        expires_at=EXPIRES,
    )


def signed_nomination(
    index: int,
    roles: tuple[str, ...],
    **overrides,
) -> SignedCandidateNomination:
    private = Ed25519PrivateKey.generate()
    public = base64.b64encode(
        private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    ).decode("ascii")
    values = {
        "nomination_id": f"V14-NOMINATION-{index}",
        "candidate_id": f"V14-CANDIDATE-{index}",
        "status": "NOMINATED",
        "test_only": False,
        "algorithm": "ED25519",
        "public_key_b64": public,
        "eligible_roles": roles,
        "identity_claim_root": digest(("identity", index)),
        "external_identity_verification_root": digest(
            ("external-identity", index)
        ),
        "external_independence_verification_root": digest(
            ("external-independence", index)
        ),
        "institution_root": digest(("institution", index)),
        "lineage_root": digest(("lineage", index)),
        "jurisdiction_root": digest(("jurisdiction", index)),
        "primary_domain_root": digest(("domain", index)),
        "authority_root": digest(("authority", index)),
        "funding_root": digest(("funding", index)),
        "data_control_root": digest(("data", index)),
        "staff_control_root": digest(("staff", index)),
        "technology_control_root": digest(("technology", index)),
        "conflict_disclosure_root": digest(("conflict", index)),
        "conflict_status": "CLEAR",
        "conflict_resolution_root": None,
        "nomination_evidence_root": digest(("nomination", index)),
        "not_before": "2026-01-01T00:00:00+00:00",
        "not_after": "2027-01-01T00:00:00+00:00",
    }
    values.update(overrides)
    nomination = CandidateNomination(**values)
    unsigned = SignedCandidateNomination(
        envelope_id=f"V14-ENVELOPE-{index}",
        nomination=nomination,
        signature_domain=SIGNATURE_DOMAIN,
        signature_b64="",
    )
    return replace(
        unsigned,
        signature_b64=base64.b64encode(
            private.sign(nomination_signing_bytes(unsigned))
        ).decode("ascii"),
    )


def unique_envelopes() -> tuple[SignedCandidateNomination, ...]:
    return tuple(
        signed_nomination(index, (role,))
        for index, role in enumerate(ROLES, start=1)
    )


class SignedNominationTests(unittest.TestCase):
    def test_valid_signature_proves_key_control_not_independence(self) -> None:
        report = verify_signed_candidate_nomination(
            signed_nomination(1, (ROLES[0],)),
            checked_at=CHECKED,
        )
        self.assertEqual(report["verdict"], "PASS")
        self.assertTrue(
            report["checks"]["candidate_key_signature_valid"]
        )
        self.assertFalse(
            report["identity_independence_externally_proven"]
        )
        self.assertFalse(report["governance_authority_granted"])

    def test_post_signature_nomination_change_is_held(self) -> None:
        envelope = signed_nomination(1, (ROLES[0],))
        tampered = replace(
            envelope,
            nomination=replace(
                envelope.nomination,
                eligible_roles=(ROLES[1],),
            ),
        )
        report = verify_signed_candidate_nomination(
            tampered,
            checked_at=CHECKED,
        )
        self.assertEqual(report["verdict"], "HOLD")
        self.assertFalse(
            report["checks"]["candidate_key_signature_valid"]
        )

    def test_wrong_signature_domain_is_held(self) -> None:
        envelope = replace(
            signed_nomination(1, (ROLES[0],)),
            signature_domain="OTHER.DOMAIN",
        )
        report = verify_signed_candidate_nomination(
            envelope,
            checked_at=CHECKED,
        )
        self.assertEqual(report["verdict"], "HOLD")
        self.assertFalse(report["checks"]["signature_domain_exact"])


class RoleCallTests(unittest.TestCase):
    def setUp(self) -> None:
        self.batch = batch_fixture()
        self.calls = [
            nomination_role_call(self.batch, role) for role in ROLES
        ]

    def test_five_role_calls_bind_the_five_v12_packets(self) -> None:
        self.assertEqual(
            [call["role"] for call in self.calls],
            list(ROLES),
        )
        self.assertTrue(
            all(
                nomination_role_call_integrity(self.batch, call)
                for call in self.calls
            )
        )
        self.assertEqual(
            len(
                {
                    call["participant_packet_digest"]
                    for call in self.calls
                }
            ),
            5,
        )

    def test_calls_do_not_claim_publication_or_recipient(self) -> None:
        for call in self.calls:
            self.assertEqual(
                call["call_state"],
                "READY_UNADDRESSED_UNPUBLISHED",
            )
            self.assertIsNone(call["publication_receipt_root"])
            self.assertIsNone(call["recipient_identity_root"])
            self.assertFalse(call["governance_authority_granted"])

    def test_call_tampering_fails_integrity(self) -> None:
        tampered = json.loads(json.dumps(self.calls[0]))
        tampered["mission"] = "substituted"
        self.assertFalse(
            nomination_role_call_integrity(self.batch, tampered)
        )

    def test_call_manifest_is_integral_and_parallel(self) -> None:
        manifest = nomination_call_manifest(self.batch, self.calls)
        self.assertTrue(
            nomination_call_manifest_integrity(
                self.batch,
                manifest,
                self.calls,
            )
        )
        self.assertEqual(manifest["call_count"], 5)
        self.assertEqual(manifest["published_count"], 0)
        self.assertFalse(manifest["publication_claimed"])


class IntakeAndAssignmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.batch = batch_fixture()
        self.calls = [
            nomination_role_call(self.batch, role) for role in ROLES
        ]

    def test_duplicate_submission_ids_are_preserved_but_not_admitted(
        self,
    ) -> None:
        envelope = signed_nomination(1, (ROLES[0],))
        ledger = public_nomination_receipt_ledger(
            nomination_receipt_ledger(
                (envelope, envelope),
                checked_at=CHECKED,
            )
        )
        self.assertEqual(ledger["submission_count"], 2)
        self.assertEqual(ledger["admitted_count"], 0)
        self.assertEqual(ledger["held_count"], 2)
        self.assertEqual(
            ledger["duplicate_envelope_ids"],
            [envelope.envelope_id],
        )

    def test_invalid_signature_is_preserved_noncounting(self) -> None:
        envelope = replace(
            signed_nomination(1, (ROLES[0],)),
            signature_b64=base64.b64encode(b"x" * 64).decode("ascii"),
        )
        ledger = public_nomination_receipt_ledger(
            nomination_receipt_ledger(
                (envelope,),
                checked_at=CHECKED,
            )
        )
        self.assertEqual(ledger["admitted_count"], 0)
        self.assertEqual(
            ledger["receipts"][0]["status"],
            "PRESERVED_NONCOUNTING_SUBMISSION",
        )

    def test_unique_cohort_binds_all_packets_but_delivers_none(
        self,
    ) -> None:
        nominations = tuple(
            envelope.nomination for envelope in unique_envelopes()
        )
        solver = solve_candidate_cohort(
            nominations,
            checked_at=CHECKED,
        )
        assignment = cohort_packet_assignment_manifest(
            self.batch,
            self.calls,
            nominations,
            solver,
        )
        self.assertEqual(assignment["assigned_count"], 5)
        self.assertEqual(
            assignment["selected_pairwise_audits"],
            10,
        )
        self.assertEqual(assignment["addressed_packets"], 0)
        self.assertEqual(assignment["delivered_packets"], 0)
        self.assertFalse(assignment["governance_authority_granted"])

    def test_multiple_cohorts_bind_no_packets(self) -> None:
        envelopes = tuple(
            signed_nomination(index, tuple(ROLES))
            for index in range(1, 6)
        )
        nominations = tuple(
            envelope.nomination for envelope in envelopes
        )
        solver = solve_candidate_cohort(
            nominations,
            checked_at=CHECKED,
        )
        assignment = cohort_packet_assignment_manifest(
            self.batch,
            self.calls,
            nominations,
            solver,
        )
        self.assertEqual(
            assignment["assignment_state"],
            "AMBIGUOUS_COHORT_NO_BINDING",
        )
        self.assertEqual(assignment["bindings"], [])
        self.assertEqual(assignment["assigned_count"], 0)


class V14RuntimeTests(unittest.TestCase):
    @staticmethod
    def runtime_batch(temporary: str) -> dict:
        compile_governance_dispatch_runtime(temporary)
        plan = json.loads(
            (
                Path(temporary)
                / "governance_dispatch_plan_v11.json"
            ).read_text(encoding="utf-8")
        )
        return issue_governance_challenge_batch(
            authority_registry_digest=plan[
                "authority_registry_digest"
            ],
            handoff_bundle_root=plan["handoff_bundle_root"],
            issued_at=ISSUED,
            expires_at=EXPIRES,
        )

    def test_all_v14_schemas_parse(self) -> None:
        root = Path(__file__).resolve().parents[1]
        paths = sorted(
            (root / "schemas" / "kc144").glob("*-v14.schema.json")
        )
        self.assertEqual(len(paths), 8)
        for path in paths:
            self.assertIsInstance(
                json.loads(path.read_text(encoding="utf-8")),
                dict,
            )

    def test_live_runtime_stops_at_external_publication_and_intake(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            release = compile_nomination_intake_runtime(
                temporary,
                challenge_batch=self.runtime_batch(temporary),
            )
            self.assertEqual(release["verdict"], "PASS")
            self.assertEqual(release["prepared_role_calls"], 5)
            self.assertEqual(release["published_role_calls"], 0)
            self.assertEqual(release["submission_count"], 0)
            self.assertEqual(release["assigned_packet_count"], 0)
            self.assertEqual(
                release["operational_status"],
                "FIVE_EXTERNAL_CANDIDATE_NOMINATIONS_REQUIRED",
            )

    def test_unique_signed_runtime_routes_to_delivery_barrier(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            release = compile_nomination_intake_runtime(
                temporary,
                challenge_batch=self.runtime_batch(temporary),
                envelopes=unique_envelopes(),
                checked_at=CHECKED,
            )
            self.assertEqual(release["verdict"], "PASS")
            self.assertEqual(release["admitted_submission_count"], 5)
            self.assertEqual(
                release["solution_status"],
                "UNIQUE_PROVISIONAL_COHORT",
            )
            self.assertEqual(release["assigned_packet_count"], 5)
            self.assertEqual(release["delivered_packet_count"], 0)
            self.assertEqual(
                release["operational_status"],
                "FIVE_PACKET_DELIVERIES_REQUIRED",
            )
            self.assertFalse(release["governance_activated"])


if __name__ == "__main__":
    unittest.main()
