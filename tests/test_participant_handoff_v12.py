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
    GovernanceChallenge,
    GovernanceEnrollmentResponse,
    enrollment_signing_bytes,
)
from kc144_crystal.dispatch_v11 import (
    issue_governance_challenge_batch,
)
from kc144_crystal.handoff_v12 import (
    HANDOFF_BARRIER,
    participant_handoff_manifest,
    participant_handoff_manifest_integrity,
    participant_handoff_packet,
    participant_handoff_packet_integrity,
    verify_response_for_handoff_packet,
)
from kc144_crystal.handoff_v9 import GovernanceMember
from kc144_crystal.population import digest
from kc144_crystal.v11 import compile_governance_dispatch_runtime
from kc144_crystal.v12 import compile_participant_handoff_runtime


ISSUED = "2026-07-27T08:39:35+00:00"
EXPIRES = "2026-08-26T08:39:35+00:00"
VERIFIED = "2026-07-27T12:00:00+00:00"
AUTHORITY_ROOT = digest("V12 authority")
HANDOFF_ROOT = digest("V12 evidence handoff")


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
    challenge = GovernanceChallenge.from_dict(
        next(
            value
            for value in batch["challenges"]
            if value["role"] == role
        )
    )
    member = GovernanceMember(
        member_id=f"V12-MEMBER-{index}",
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
        response_id=f"V12-RESPONSE-{index}",
        challenge=challenge,
        member=member,
        identity_claim_root=digest(("identity", index)),
        institution_root=digest(("institution", index)),
        lineage_root=digest(("lineage", index)),
        external_identity_verification_root=digest(
            ("identity-verification", index)
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


def batch_fixture() -> dict:
    return issue_governance_challenge_batch(
        authority_registry_digest=AUTHORITY_ROOT,
        handoff_bundle_root=HANDOFF_ROOT,
        issued_at=ISSUED,
        expires_at=EXPIRES,
    )


class ParticipantPacketTests(unittest.TestCase):
    def setUp(self) -> None:
        self.batch = batch_fixture()
        self.packets = [
            participant_handoff_packet(self.batch, role)
            for role in ROLES
        ]

    def test_all_five_role_packets_are_complete_and_integral(self) -> None:
        self.assertEqual(
            [packet["role"] for packet in self.packets],
            list(ROLES),
        )
        self.assertTrue(
            all(
                participant_handoff_packet_integrity(
                    self.batch,
                    packet,
                )
                for packet in self.packets
            )
        )

    def test_packets_do_not_fabricate_recipients_or_delivery(self) -> None:
        for packet in self.packets:
            self.assertEqual(
                packet["delivery_state"],
                "READY_UNADDRESSED_UNDELIVERED",
            )
            self.assertIsNone(packet["recipient_identity_root"])
            self.assertIsNone(packet["delivery_receipt_root"])
            self.assertEqual(packet["truth_effect"], "NONE")

    def test_packet_tampering_fails_integrity(self) -> None:
        tampered = json.loads(json.dumps(self.packets[0]))
        tampered["mission"] = "substituted mission"
        self.assertFalse(
            participant_handoff_packet_integrity(
                self.batch,
                tampered,
            )
        )

    def test_manifest_binds_every_packet(self) -> None:
        manifest = participant_handoff_manifest(
            self.batch,
            self.packets,
        )
        self.assertTrue(
            participant_handoff_manifest_integrity(
                self.batch,
                manifest,
                self.packets,
            )
        )
        self.assertEqual(manifest["packet_count"], 5)
        self.assertEqual(manifest["delivered_count"], 0)
        self.assertEqual(manifest["barrier"], HANDOFF_BARRIER)


class HandoffReturnTests(unittest.TestCase):
    def setUp(self) -> None:
        self.batch = batch_fixture()
        self.packet = participant_handoff_packet(
            self.batch,
            ROLES[0],
        )

    def test_exact_signed_return_passes_without_activation(self) -> None:
        response = signed_response(self.batch, ROLES[0], 1)
        report = verify_response_for_handoff_packet(
            self.batch,
            self.packet,
            response,
            verified_at=VERIFIED,
        )
        self.assertEqual(report["verdict"], "PASS")
        self.assertFalse(report["governance_activated"])

    def test_other_batch_return_cannot_cross_packet_boundary(self) -> None:
        other = batch_fixture()
        response = signed_response(other, ROLES[0], 1)
        report = verify_response_for_handoff_packet(
            self.batch,
            self.packet,
            response,
            verified_at=VERIFIED,
        )
        self.assertEqual(report["verdict"], "HOLD")
        self.assertFalse(report["checks"]["challenge_exact"])

    def test_other_role_return_cannot_fill_packet(self) -> None:
        response = signed_response(self.batch, ROLES[1], 2)
        report = verify_response_for_handoff_packet(
            self.batch,
            self.packet,
            response,
            verified_at=VERIFIED,
        )
        self.assertEqual(report["verdict"], "HOLD")
        self.assertFalse(report["checks"]["role_exact"])


class V12RuntimeTests(unittest.TestCase):
    def test_all_v12_schemas_parse(self) -> None:
        root = Path(__file__).resolve().parents[1]
        paths = sorted(
            (root / "schemas" / "kc144").glob("*-v12.schema.json")
        )
        self.assertEqual(len(paths), 5)
        for path in paths:
            self.assertIsInstance(
                json.loads(path.read_text(encoding="utf-8")),
                dict,
            )

    def test_runtime_prepares_all_packets_and_stops_at_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            compile_governance_dispatch_runtime(temporary)
            dispatch_plan = json.loads(
                (
                    Path(temporary)
                    / "governance_dispatch_plan_v11.json"
                ).read_text(encoding="utf-8")
            )
            batch = issue_governance_challenge_batch(
                authority_registry_digest=dispatch_plan[
                    "authority_registry_digest"
                ],
                handoff_bundle_root=dispatch_plan[
                    "handoff_bundle_root"
                ],
                issued_at=ISSUED,
                expires_at=EXPIRES,
            )
            release = compile_participant_handoff_runtime(
                temporary,
                challenge_batch=batch,
            )
            self.assertEqual(release["verdict"], "PASS")
            self.assertEqual(release["prepared_packets"], 5)
            self.assertEqual(release["addressed_packets"], 0)
            self.assertEqual(release["delivered_packets"], 0)
            self.assertEqual(
                release["operational_status"],
                HANDOFF_BARRIER,
            )
            self.assertFalse(release["governance_activated"])


if __name__ == "__main__":
    unittest.main()
