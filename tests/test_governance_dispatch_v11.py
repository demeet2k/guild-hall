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

from kc144_crystal.ceremony_v10 import (
    ROLES,
    GovernanceEnrollmentResponse,
    enrollment_signing_bytes,
    pending_society_integrity,
)
from kc144_crystal.dispatch_v11 import (
    challenge_batch_integrity,
    governance_challenge_batch_state,
    issue_governance_challenge_batch,
    route_governance_responses,
)
from kc144_crystal.handoff_v9 import GovernanceMember
from kc144_crystal.population import digest
from kc144_crystal.v11 import compile_governance_dispatch_runtime


ISSUED = "2026-07-27T00:00:00+00:00"
EXPIRES = "2026-08-26T00:00:00+00:00"
VERIFIED = "2026-07-27T12:00:00+00:00"
AUTHORITY_ROOT = digest("V11 authority registry")
HANDOFF_ROOT = digest("V11 handoff bundle")


def public_b64(private: Ed25519PrivateKey) -> str:
    return base64.b64encode(
        private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    ).decode("ascii")


def signed_response(
    batch: dict,
    role: str,
    index: int,
) -> GovernanceEnrollmentResponse:
    private = Ed25519PrivateKey.generate()
    challenge_value = next(
        value for value in batch["challenges"] if value["role"] == role
    )
    from kc144_crystal.ceremony_v10 import GovernanceChallenge

    challenge = GovernanceChallenge.from_dict(challenge_value)
    member = GovernanceMember(
        member_id=f"V11-MEMBER-{index}",
        algorithm="ED25519",
        public_key_b64=public_b64(private),
        role=role,
        status="ACTIVE",
        independent=True,
        test_only=False,
        not_before="2026-01-01T00:00:00+00:00",
        not_after="2027-01-01T00:00:00+00:00",
    )
    unsigned = GovernanceEnrollmentResponse(
        response_id=f"V11-RESPONSE-{index}",
        challenge=challenge,
        member=member,
        identity_claim_root=digest(("identity", index)),
        institution_root=digest(("institution", index)),
        lineage_root=digest(("lineage", index)),
        external_identity_verification_root=digest(
            ("external-identity", index)
        ),
        conflict_disclosure_root=digest(("conflict", index)),
        conflict_status="CLEAR",
        conflict_resolution_root=None,
        consent_root=digest(("consent", index)),
        boundary_claim="PARTICIPANT_CONSENT_NOT_SELF_RATIFICATION",
        signature_b64="",
    )
    return replace(
        unsigned,
        signature_b64=base64.b64encode(
            private.sign(enrollment_signing_bytes(unsigned))
        ).decode("ascii"),
    )


class ChallengeBatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.batch = issue_governance_challenge_batch(
            authority_registry_digest=AUTHORITY_ROOT,
            handoff_bundle_root=HANDOFF_ROOT,
            issued_at=ISSUED,
            expires_at=EXPIRES,
        )

    def test_batch_is_complete_unique_and_integral(self) -> None:
        self.assertTrue(challenge_batch_integrity(self.batch))
        self.assertEqual(
            [value["role"] for value in self.batch["challenges"]],
            list(ROLES),
        )
        self.assertEqual(
            len({value["nonce"] for value in self.batch["challenges"]}),
            5,
        )

    def test_separate_batches_have_distinct_roots(self) -> None:
        second = issue_governance_challenge_batch(
            authority_registry_digest=AUTHORITY_ROOT,
            handoff_bundle_root=HANDOFF_ROOT,
            issued_at=ISSUED,
            expires_at=EXPIRES,
        )
        self.assertNotEqual(self.batch["batch_root"], second["batch_root"])
        self.assertNotEqual(self.batch["batch_id"], second["batch_id"])

    def test_batch_tampering_fails_integrity(self) -> None:
        tampered = json.loads(json.dumps(self.batch))
        tampered["challenges"][0]["nonce"] = "f" * 64
        self.assertFalse(challenge_batch_integrity(tampered))

    def test_expired_batch_is_preserved_but_closed(self) -> None:
        state = governance_challenge_batch_state(
            self.batch,
            checked_at="2026-08-27T00:00:00+00:00",
        )
        self.assertEqual(state["integrity"], "PASS")
        self.assertEqual(state["lifecycle"], "EXPIRED")
        self.assertFalse(state["accepting_responses"])


class ParallelResponseRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.batch = issue_governance_challenge_batch(
            authority_registry_digest=AUTHORITY_ROOT,
            handoff_bundle_root=HANDOFF_ROOT,
            issued_at=ISSUED,
            expires_at=EXPIRES,
        )

    def test_empty_wave_stops_at_exact_five_response_barrier(self) -> None:
        report = route_governance_responses(
            self.batch,
            (),
            verified_at=VERIFIED,
        )
        self.assertEqual(report["counted_response_count"], 0)
        self.assertEqual(
            report["barrier"],
            "FIVE_INDEPENDENT_PARTICIPANT_RESPONSES_REQUIRED",
        )
        self.assertFalse(report["governance_activated"])

    def test_one_exact_response_is_counted(self) -> None:
        response = signed_response(self.batch, ROLES[0], 1)
        report = route_governance_responses(
            self.batch,
            (response,),
            verified_at=VERIFIED,
        )
        self.assertEqual(report["counted_response_count"], 1)
        self.assertEqual(report["remaining_roles"], list(ROLES[1:]))

    def test_response_from_another_batch_is_rejected(self) -> None:
        other = issue_governance_challenge_batch(
            authority_registry_digest=AUTHORITY_ROOT,
            handoff_bundle_root=HANDOFF_ROOT,
            issued_at=ISSUED,
            expires_at=EXPIRES,
        )
        response = signed_response(other, ROLES[0], 1)
        report = route_governance_responses(
            self.batch,
            (response,),
            verified_at=VERIFIED,
        )
        self.assertEqual(report["counted_response_count"], 0)
        self.assertFalse(report["response_reports"][0]["challenge_exact"])

    def test_duplicate_response_collision_fails_closed(self) -> None:
        response = signed_response(self.batch, ROLES[0], 1)
        report = route_governance_responses(
            self.batch,
            (response, response),
            verified_at=VERIFIED,
        )
        self.assertEqual(report["counted_response_count"], 0)
        self.assertIn(
            "response_id",
            report["response_reports"][0]["collisions"],
        )

    def test_five_valid_responses_assemble_but_do_not_activate(self) -> None:
        responses = tuple(
            signed_response(self.batch, role, index)
            for index, role in enumerate(ROLES, start=1)
        )
        report = route_governance_responses(
            self.batch,
            responses,
            verified_at=VERIFIED,
        )
        self.assertEqual(report["counted_response_count"], 5)
        self.assertEqual(
            report["barrier"],
            "EXTERNAL_RATIFICATION_REQUIRED",
        )
        self.assertTrue(
            pending_society_integrity(report["pending_society"])
        )
        self.assertFalse(report["governance_activated"])

    def test_expired_batch_rejects_otherwise_valid_response(self) -> None:
        response = signed_response(self.batch, ROLES[0], 1)
        report = route_governance_responses(
            self.batch,
            (response,),
            verified_at="2026-08-27T00:00:00+00:00",
        )
        self.assertEqual(report["counted_response_count"], 0)
        self.assertEqual(
            report["barrier"],
            "CHALLENGE_BATCH_REISSUE_REQUIRED",
        )


class V11RuntimeTests(unittest.TestCase):
    def test_all_v11_schemas_parse(self) -> None:
        root = Path(__file__).resolve().parents[1]
        paths = sorted(
            (root / "schemas" / "kc144").glob("*-v11.schema.json")
        )
        self.assertEqual(len(paths), 6)
        for path in paths:
            self.assertIsInstance(
                json.loads(path.read_text(encoding="utf-8")),
                dict,
            )

    def test_default_runtime_stops_before_batch_issuance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            release = compile_governance_dispatch_runtime(temporary)
            self.assertEqual(release["verdict"], "PASS")
            self.assertFalse(release["batch_issued"])
            self.assertEqual(
                release["operational_status"],
                "CHALLENGE_BATCH_ISSUANCE_REQUIRED",
            )

    def test_runtime_consumes_existing_batch_without_responses(self) -> None:
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
            release = compile_governance_dispatch_runtime(
                temporary,
                challenge_batch=batch,
            )
            self.assertEqual(release["verdict"], "PASS")
            self.assertTrue(release["batch_issued"])
            self.assertEqual(
                release["operational_status"],
                "FIVE_INDEPENDENT_PARTICIPANT_RESPONSES_REQUIRED",
            )


if __name__ == "__main__":
    unittest.main()
