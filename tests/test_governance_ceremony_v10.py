from __future__ import annotations

import base64
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from kc144_crystal.ceremony_v10 import (
    CEREMONY_ID,
    ROLES,
    ExternalCheckpointReceipt,
    GovernanceEnrollmentResponse,
    GovernanceRatification,
    activate_governance_society,
    assemble_pending_society,
    create_governance_challenge,
    enrollment_signing_bytes,
    pending_society_integrity,
    ratification_signing_bytes,
    verify_enrollment_response,
    verify_governance_ratification,
)
from kc144_crystal.evidence_v7 import empty_authority_registry
from kc144_crystal.handoff_v9 import (
    GovernanceMember,
    governance_registry_integrity,
    handoff_bundle,
)
from kc144_crystal.population import digest
from kc144_crystal.repair import empty_repair_ledger
from kc144_crystal.v10 import compile_governance_ceremony_runtime

ROOT = Path(__file__).resolve().parents[1]
ISSUED = "2026-07-27T00:00:00+00:00"
EXPIRES = "2026-07-28T00:00:00+00:00"
VERIFIED = "2026-07-27T12:00:00+00:00"
RATIFIED_VERIFIED = "2026-07-27T16:00:00+00:00"


def public_b64(private: Ed25519PrivateKey) -> str:
    return base64.b64encode(
        private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    ).decode("ascii")


def participant_response(
    role: str,
    index: int,
    *,
    authority_root: str,
    bundle_root: str,
    institution_root: str | None = None,
    test_only: bool = False,
):
    private = Ed25519PrivateKey.generate()
    challenge = create_governance_challenge(
        role,
        authority_registry_digest=authority_root,
        handoff_bundle_root=bundle_root,
        issued_at=ISSUED,
        expires_at=EXPIRES,
        nonce=f"{index:064x}",
    )
    member = GovernanceMember(
        member_id=f"V10-MEMBER-{index}",
        algorithm="ED25519",
        public_key_b64=public_b64(private),
        role=role,
        status="ACTIVE",
        independent=True,
        test_only=test_only,
        not_before="2026-01-01T00:00:00+00:00",
        not_after="2027-01-01T00:00:00+00:00",
    )
    unsigned = GovernanceEnrollmentResponse(
        response_id=f"V10-RESPONSE-{index}",
        challenge=challenge,
        member=member,
        identity_claim_root=digest(("identity", index)),
        institution_root=institution_root
        or digest(("institution", index)),
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
    response = replace(
        unsigned,
        signature_b64=base64.b64encode(
            private.sign(enrollment_signing_bytes(unsigned))
        ).decode("ascii"),
    )
    return private, response


def participant_society():
    ledger = empty_repair_ledger(namespace="PRODUCTION")
    authority = empty_authority_registry()
    bundle = handoff_bundle(ledger)
    responses = [
        participant_response(
            role,
            index,
            authority_root=authority["registry_digest"],
            bundle_root=bundle["bundle_root"],
        )[1]
        for index, role in enumerate(ROLES, start=1)
    ]
    return responses, assemble_pending_society(
        responses,
        verified_at=VERIFIED,
    )


def signed_ratification(pending, anchor_count: int):
    private_keys = [Ed25519PrivateKey.generate() for _ in range(anchor_count)]
    unsigned_anchors = tuple(
        ExternalCheckpointReceipt(
            anchor_id=f"EXTERNAL-ANCHOR-{index}",
            algorithm="ED25519",
            public_key_b64=public_b64(private),
            institution_root=digest(("anchor-institution", index)),
            checkpoint_ref=f"external://checkpoint/{index}",
            checkpoint_root=digest(
                ("checkpoint", pending["ceremony_root"], index)
            ),
            observed_at="2026-07-27T15:00:00+00:00",
            signature_b64="",
        )
        for index, private in enumerate(private_keys, start=1)
    )
    unsigned = GovernanceRatification(
        ratification_id="V10-RATIFICATION-001",
        ceremony_root=pending["ceremony_root"],
        constitution_root_before=digest("constitution-before"),
        constitution_root_after=digest("constitution-after"),
        rollback_root=digest("rollback-state"),
        challenge_window_closed_at="2026-07-27T13:00:00+00:00",
        challenge_disposition_root=digest("challenge-disposition"),
        ratified_at="2026-07-27T14:00:00+00:00",
        anchors=unsigned_anchors,
    )
    signed_anchors = tuple(
        replace(
            anchor,
            signature_b64=base64.b64encode(
                private.sign(
                    ratification_signing_bytes(unsigned, anchor)
                )
            ).decode("ascii"),
        )
        for private, anchor in zip(private_keys, unsigned_anchors)
    )
    return replace(unsigned, anchors=signed_anchors)


class EnrollmentCeremonyTests(unittest.TestCase):
    def setUp(self) -> None:
        ledger = empty_repair_ledger(namespace="PRODUCTION")
        self.authority = empty_authority_registry()
        self.bundle = handoff_bundle(ledger)

    def test_challenges_are_role_bound_and_random_by_default(self) -> None:
        first = create_governance_challenge(
            ROLES[0],
            authority_registry_digest=self.authority["registry_digest"],
            handoff_bundle_root=self.bundle["bundle_root"],
            issued_at=ISSUED,
            expires_at=EXPIRES,
        )
        second = create_governance_challenge(
            ROLES[0],
            authority_registry_digest=self.authority["registry_digest"],
            handoff_bundle_root=self.bundle["bundle_root"],
            issued_at=ISSUED,
            expires_at=EXPIRES,
        )
        self.assertNotEqual(first.nonce, second.nonce)
        self.assertNotEqual(first.challenge_id, second.challenge_id)

    def test_signed_response_verifies_but_does_not_activate(self) -> None:
        _, response = participant_response(
            ROLES[0],
            1,
            authority_root=self.authority["registry_digest"],
            bundle_root=self.bundle["bundle_root"],
        )
        report = verify_enrollment_response(
            response,
            verified_at=VERIFIED,
        )
        self.assertEqual(report["verdict"], "PASS")
        self.assertFalse(report["governance_activated"])

    def test_challenge_tampering_invalidates_participant_signature(self) -> None:
        _, response = participant_response(
            ROLES[0],
            1,
            authority_root=self.authority["registry_digest"],
            bundle_root=self.bundle["bundle_root"],
        )
        tampered_challenge = replace(
            response.challenge,
            nonce="f" * 64,
        )
        tampered = replace(response, challenge=tampered_challenge)
        report = verify_enrollment_response(
            tampered,
            verified_at=VERIFIED,
        )
        self.assertEqual(report["verdict"], "HOLD")
        self.assertFalse(report["checks"]["proof_of_possession"])

    def test_test_participant_cannot_fill_production_seat(self) -> None:
        _, response = participant_response(
            ROLES[0],
            1,
            authority_root=self.authority["registry_digest"],
            bundle_root=self.bundle["bundle_root"],
            test_only=True,
        )
        report = verify_enrollment_response(
            response,
            verified_at=VERIFIED,
        )
        self.assertEqual(report["verdict"], "HOLD")
        self.assertFalse(report["checks"]["member_not_test_only"])

    def test_five_unique_responses_form_pending_society_only(self) -> None:
        responses, pending = participant_society()
        self.assertEqual(len(responses), 5)
        self.assertEqual(pending["verdict"], "PASS")
        self.assertEqual(
            pending["status"],
            "READY_FOR_EXTERNAL_RATIFICATION",
        )
        self.assertFalse(pending["governance_activated"])
        self.assertTrue(pending_society_integrity(pending))
        self.assertTrue(
            governance_registry_integrity(pending["pending_registry"])
        )

    def test_shared_institution_blocks_society_assembly(self) -> None:
        shared = digest("shared institution")
        responses = [
            participant_response(
                role,
                index,
                authority_root=self.authority["registry_digest"],
                bundle_root=self.bundle["bundle_root"],
                institution_root=shared if index <= 2 else None,
            )[1]
            for index, role in enumerate(ROLES, start=1)
        ]
        pending = assemble_pending_society(
            responses,
            verified_at=VERIFIED,
        )
        self.assertEqual(pending["verdict"], "HOLD")
        self.assertFalse(pending["checks"]["institutions_unique"])


class RatificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.responses, cls.pending = participant_society()

    def test_one_external_anchor_cannot_activate(self) -> None:
        ratification = signed_ratification(self.pending, 1)
        report = verify_governance_ratification(
            self.pending,
            ratification,
            verified_at=RATIFIED_VERIFIED,
        )
        self.assertEqual(report["verdict"], "HOLD")
        self.assertFalse(report["checks"]["two_external_anchors"])

    def test_two_external_anchors_activate_registry_only(self) -> None:
        ratification = signed_ratification(self.pending, 2)
        report = activate_governance_society(
            self.pending,
            ratification,
            verified_at=RATIFIED_VERIFIED,
        )
        self.assertEqual(report["status"], "ACTIVATED")
        self.assertTrue(report["governance_activated"])
        self.assertTrue(
            governance_registry_integrity(
                report["governance_registry"]
            )
        )
        self.assertEqual(
            report["truth_effect"],
            "GOVERNANCE_REGISTRY_ONLY",
        )

    def test_constitution_transition_tampering_breaks_anchor_signatures(self) -> None:
        ratification = signed_ratification(self.pending, 2)
        tampered = replace(
            ratification,
            constitution_root_after=digest("tampered constitution"),
        )
        report = verify_governance_ratification(
            self.pending,
            tampered,
            verified_at=RATIFIED_VERIFIED,
        )
        self.assertEqual(report["verdict"], "HOLD")
        self.assertEqual(report["valid_anchor_ids"], [])

    def test_pending_registry_substitution_is_rejected(self) -> None:
        ratification = signed_ratification(self.pending, 2)
        tampered = json.loads(json.dumps(self.pending))
        tampered["pending_registry"]["members"][0]["member_id"] = (
            "SUBSTITUTED-MEMBER"
        )
        report = verify_governance_ratification(
            tampered,
            ratification,
            verified_at=RATIFIED_VERIFIED,
        )
        self.assertEqual(report["verdict"], "HOLD")
        self.assertFalse(report["checks"]["pending_society_integrity"])

    def test_duplicate_external_checkpoint_is_rejected(self) -> None:
        ratification = signed_ratification(self.pending, 2)
        duplicated_anchor = replace(
            ratification.anchors[1],
            checkpoint_ref=ratification.anchors[0].checkpoint_ref,
            checkpoint_root=ratification.anchors[0].checkpoint_root,
            signature_b64="",
        )
        private = Ed25519PrivateKey.generate()
        duplicated_anchor = replace(
            duplicated_anchor,
            public_key_b64=public_b64(private),
        )
        unsigned = replace(
            ratification,
            anchors=(ratification.anchors[0], duplicated_anchor),
        )
        duplicated_anchor = replace(
            duplicated_anchor,
            signature_b64=base64.b64encode(
                private.sign(
                    ratification_signing_bytes(
                        unsigned,
                        duplicated_anchor,
                    )
                )
            ).decode("ascii"),
        )
        tampered = replace(
            unsigned,
            anchors=(ratification.anchors[0], duplicated_anchor),
        )
        report = verify_governance_ratification(
            self.pending,
            tampered,
            verified_at=RATIFIED_VERIFIED,
        )
        self.assertEqual(report["verdict"], "HOLD")
        self.assertFalse(
            report["checks"]["anchor_checkpoint_refs_unique"]
        )


class V10ReleaseTests(unittest.TestCase):
    def test_release_stops_at_external_participant_responses(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            release = compile_governance_ceremony_runtime(temporary)
            self.assertEqual(release["verdict"], "PASS")
            self.assertEqual(release["governance_roles"], 5)
            self.assertEqual(release["filled_seats"], 0)
            self.assertEqual(
                release["operational_status"],
                "FIVE_INDEPENDENT_PARTICIPANT_RESPONSES_REQUIRED",
            )
            self.assertFalse(release["governance_activated"])

    def test_all_v10_schemas_parse(self) -> None:
        for path in sorted(
            (ROOT / "schemas" / "kc144").glob("*-v10.schema.json")
        ):
            self.assertIsInstance(
                json.loads(path.read_text(encoding="utf-8")),
                dict,
            )


if __name__ == "__main__":
    unittest.main()
