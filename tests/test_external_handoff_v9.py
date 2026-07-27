from __future__ import annotations

import base64
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from kc144_crystal.campaign_v8 import (
    ACTIVE_EPOCH_ID,
    ENROLLMENT_BOUNDARY,
    AuthorityEnrollmentProof,
    enrollment_signing_bytes,
)
from kc144_crystal.evidence_v7 import (
    empty_authority_registry,
    envelope_signing_bytes,
    authority_registry_integrity,
)
from kc144_crystal.handoff_v9 import (
    GOVERNANCE_ID,
    GovernanceApproval,
    GovernanceMember,
    AuthorityPinProposal,
    governance_registry_integrity,
    governance_signing_bytes,
    handoff_bundle,
    pin_authority_from_proposal,
    run_handoff_to_barrier,
    seal_governance_registry,
    verify_authority_pin_proposal,
    verify_source_harvest,
)
from kc144_crystal.population import digest
from kc144_crystal.repair import empty_repair_ledger, evidence_summary
from kc144_crystal.v9 import compile_external_handoff_runtime

from tests.test_parallel_campaign_v8 import campaign_envelopes
from tests.test_production_evidence_v7 import ISSUED_AT, authority_material


ROOT = Path(__file__).resolve().parents[1]
ROLES = (
    "CUSTODIAN",
    "INDEPENDENT_REVIEWER",
    "REPLAY_WITNESS",
    "SOURCE_AUDITOR",
    "RETURN_AUDITOR",
)


def governance_material():
    private_keys = []
    members = []
    for index, role in enumerate(ROLES, start=1):
        private = Ed25519PrivateKey.generate()
        public = private.public_key().public_bytes(
            Encoding.Raw,
            PublicFormat.Raw,
        )
        private_keys.append(private)
        members.append(
            GovernanceMember(
                member_id=f"GOV-V9-{index}",
                algorithm="ED25519",
                public_key_b64=base64.b64encode(public).decode("ascii"),
                role=role,
                status="ACTIVE",
                independent=True,
                test_only=False,
                not_before="2026-01-01T00:00:00+00:00",
                not_after="2027-01-01T00:00:00+00:00",
            )
        )
    return private_keys, members, seal_governance_registry(members)


def signed_candidate_proof(private, key):
    unsigned = AuthorityEnrollmentProof(
        request_id="ENROLL-V9-CANDIDATE",
        epoch_id=ACTIVE_EPOCH_ID,
        nonce="0123456789abcdef0123456789abcdef",
        issued_at=ISSUED_AT,
        key=key,
        boundary_claim=ENROLLMENT_BOUNDARY,
        signature_b64="",
    )
    return replace(
        unsigned,
        signature_b64=base64.b64encode(
            private.sign(enrollment_signing_bytes(unsigned))
        ).decode("ascii"),
    )


def pin_proposal(candidate_proof, governance_registry, authority_registry):
    return AuthorityPinProposal(
        proposal_id="PIN-V9-CANDIDATE",
        epoch_id=ACTIVE_EPOCH_ID,
        governance_registry_digest=governance_registry["registry_digest"],
        authority_registry_digest=authority_registry["registry_digest"],
        issued_at="2026-07-27T00:00:00+00:00",
        expires_at="2026-07-28T00:00:00+00:00",
        candidate_proof=candidate_proof,
        approvals=(),
    )


def add_approvals(proposal, private_keys, members, count):
    signing_bytes = governance_signing_bytes(proposal)
    approvals = tuple(
        GovernanceApproval(
            member_id=members[index].member_id,
            signature_b64=base64.b64encode(
                private_keys[index].sign(signing_bytes)
            ).decode("ascii"),
        )
        for index in range(count)
    )
    return replace(proposal, approvals=approvals)


def bind_handoff_envelopes(envelopes, ledger, private):
    bundle = handoff_bundle(ledger)
    request_by_shard = {
        request["campaign_shard_id"]: request
        for request in bundle["requests"]
    }
    result = {}
    for shard_id, envelope in envelopes.items():
        request = request_by_shard[shard_id]
        packets = []
        for packet in envelope.packets:
            payload = {
                **packet.payload,
                "handoff_bundle_root": bundle["bundle_root"],
                "handoff_request_digest": request["request_digest"],
                "source_manifest_root": digest(
                    ("SOURCE-MANIFEST", packet.subject_id)
                ),
                "source_claim_root": digest(
                    ("SOURCE-CLAIM", packet.subject_id)
                ),
            }
            packets.append(
                replace(
                    packet,
                    payload=payload,
                    payload_digest=digest(payload),
                )
            )
        unsigned = replace(
            envelope,
            packets=tuple(packets),
            signature_b64="",
        )
        result[shard_id] = replace(
            unsigned,
            signature_b64=base64.b64encode(
                private.sign(envelope_signing_bytes(unsigned))
            ).decode("ascii"),
        )
    return result


class HandoffBundleTests(unittest.TestCase):
    def test_bundle_is_exact_content_addressed_campaign(self) -> None:
        ledger = empty_repair_ledger(namespace="PRODUCTION")
        bundle = handoff_bundle(ledger)
        self.assertEqual(bundle["request_count"], 16)
        self.assertEqual(bundle["packet_count"], 232)
        self.assertEqual(len(bundle["requests"]), 16)
        self.assertEqual(
            len({row["request_digest"] for row in bundle["requests"]}),
            16,
        )
        adjudicated = next(
            row
            for row in bundle["requests"]
            if row["campaign_shard_id"]
            == "A_DOMAIN_F37_ADJUDICATED"
        )
        self.assertIn(
            "adjudication_receipt_root",
            adjudicated["required_payload_fields"],
        )

    def test_one_harvest_can_fan_out_with_individual_claims(self) -> None:
        ledger = empty_repair_ledger(namespace="PRODUCTION")
        bundle = handoff_bundle(ledger)
        source = {
            "schema": "KC144.SourceHarvestManifest.V9",
            "source_id": "SOURCE-EXTERNAL-001",
            "source_ref": "external://archive/object-001",
            "content_digest": digest("immutable source bytes"),
            "acquired_at": ISSUED_AT,
            "provenance_root": digest("source provenance"),
            "independent": True,
            "claims": [
                {
                    "subject_id": subject,
                    "extraction_digest": digest(("extract", subject)),
                    "relevance_digest": digest(("relevance", subject)),
                    "residual_state": "NONE",
                }
                for subject in ("GID091", "GID092", "GID093")
            ],
        }
        report = verify_source_harvest(source, bundle)
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(report["source_object_count"], 1)
        self.assertEqual(report["fanout_preserved"], 3)

    def test_production_placeholder_source_is_contamination(self) -> None:
        ledger = empty_repair_ledger(namespace="PRODUCTION")
        bundle = handoff_bundle(ledger)
        source = {
            "schema": "KC144.SourceHarvestManifest.V9",
            "source_id": "SOURCE-EXTERNAL-002",
            "source_ref": "placeholder://example",
            "content_digest": digest("bytes"),
            "acquired_at": ISSUED_AT,
            "provenance_root": digest("provenance"),
            "independent": True,
            "claims": [
                {
                    "subject_id": "GID091",
                    "extraction_digest": digest("extract"),
                    "relevance_digest": digest("relevance"),
                    "residual_state": "NONE",
                }
            ],
        }
        report = verify_source_harvest(source, bundle)
        self.assertEqual(report["verdict"], "HOLD")
        self.assertFalse(
            report["checks"]["production_contamination_absent"]
        )


class ThresholdGovernanceTests(unittest.TestCase):
    def setUp(self) -> None:
        (
            self.governance_private,
            self.members,
            self.governance_registry,
        ) = governance_material()
        (
            self.candidate_private,
            self.candidate_key,
            _,
        ) = authority_material("PRODUCTION")
        self.authority_registry = empty_authority_registry()
        self.proof = signed_candidate_proof(
            self.candidate_private,
            self.candidate_key,
        )
        self.proposal = pin_proposal(
            self.proof,
            self.governance_registry,
            self.authority_registry,
        )

    def test_two_signatures_cannot_pin_authority(self) -> None:
        proposal = add_approvals(
            self.proposal,
            self.governance_private,
            self.members,
            2,
        )
        report = verify_authority_pin_proposal(
            proposal,
            self.governance_registry,
            self.authority_registry,
            verified_at="2026-07-27T12:00:00+00:00",
        )
        self.assertEqual(report["verdict"], "HOLD")
        self.assertFalse(report["checks"]["threshold_met"])

    def test_three_independent_signatures_pin_candidate(self) -> None:
        proposal = add_approvals(
            self.proposal,
            self.governance_private,
            self.members,
            3,
        )
        report = pin_authority_from_proposal(
            proposal,
            self.governance_registry,
            self.authority_registry,
            verified_at="2026-07-27T12:00:00+00:00",
        )
        self.assertEqual(report["status"], "PINNED")
        self.assertTrue(report["authority_pinned"])
        self.assertEqual(
            report["verification"]["valid_approvers"],
            ["GOV-V9-1", "GOV-V9-2", "GOV-V9-3"],
        )
        self.assertTrue(authority_registry_integrity(report["registry"]))
        self.assertEqual(
            report["truth_effect"],
            "AUTHORITY_REGISTRY_ONLY",
        )

    def test_signed_proposal_tampering_invalidates_quorum(self) -> None:
        proposal = add_approvals(
            self.proposal,
            self.governance_private,
            self.members,
            3,
        )
        tampered = replace(
            proposal,
            expires_at="2026-07-29T00:00:00+00:00",
        )
        report = verify_authority_pin_proposal(
            tampered,
            self.governance_registry,
            self.authority_registry,
            verified_at="2026-07-27T12:00:00+00:00",
        )
        self.assertEqual(report["verdict"], "HOLD")
        self.assertEqual(report["valid_approvers"], [])

    def test_revoked_governor_is_not_counted_toward_threshold(self) -> None:
        revoked_members = [
            replace(self.members[0], status="REVOKED"),
            *self.members[1:],
        ]
        registry = seal_governance_registry(
            revoked_members,
            revoked_member_ids=["GOV-V9-1"],
            revocation_log=[
                {
                    "event_id": "REVOKE-GOV-V9-1",
                    "member_id": "GOV-V9-1",
                    "revoked_at": ISSUED_AT,
                    "reason": "TESTED_REVOCATION_PATH",
                }
            ],
        )
        proposal = pin_proposal(
            self.proof,
            registry,
            self.authority_registry,
        )
        proposal = add_approvals(
            proposal,
            self.governance_private,
            revoked_members,
            3,
        )
        report = verify_authority_pin_proposal(
            proposal,
            registry,
            self.authority_registry,
            verified_at="2026-07-27T12:00:00+00:00",
        )
        self.assertEqual(report["verdict"], "HOLD")
        self.assertEqual(
            report["valid_approvers"],
            ["GOV-V9-2", "GOV-V9-3"],
        )

    def test_governance_registry_rejects_reused_public_key(self) -> None:
        duplicated = [
            *self.members[:-1],
            replace(
                self.members[-1],
                public_key_b64=self.members[0].public_key_b64,
            ),
        ]
        with self.assertRaises(ValueError):
            seal_governance_registry(duplicated)


class ExternalHandoffRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ledger = empty_repair_ledger(namespace="TEST")
        cls.private, cls.key, cls.registry = authority_material("TEST")
        v8_envelopes = campaign_envelopes(
            cls.private,
            cls.key,
            cls.ledger,
        )
        cls.envelopes = bind_handoff_envelopes(
            v8_envelopes,
            cls.ledger,
            cls.private,
        )

    def test_full_handoff_roundtrip_is_resumable_and_nonproduction(self) -> None:
        report = run_handoff_to_barrier(
            self.ledger,
            self.registry,
            self.envelopes,
        )
        self.assertEqual(report["status"], "COMPLETE")
        self.assertEqual(report["handoff_held_shards"], [])
        self.assertEqual(len(report["ledger"]["records"]), 232)
        self.assertEqual(
            report["campaign_barrier"],
            "TEST_CAMPAIGN_COMPLETE_NO_PRODUCTION_EFFECT",
        )
        summary = evidence_summary(report["ledger"])
        self.assertEqual(summary["production_truth_effect"], "NONE")
        self.assertEqual(
            summary["production_effective_state"]["domain_population"],
            86,
        )

    def test_wrong_request_binding_is_held_before_v8_admission(self) -> None:
        shard_id = "A_DOMAIN_SSN12"
        envelope = self.envelopes[shard_id]
        first = envelope.packets[0]
        payload = {
            **first.payload,
            "handoff_request_digest": digest("wrong request"),
        }
        packet = replace(
            first,
            payload=payload,
            payload_digest=digest(payload),
        )
        unsigned = replace(
            envelope,
            packets=(packet, *envelope.packets[1:]),
            signature_b64="",
        )
        envelope = replace(
            unsigned,
            signature_b64=base64.b64encode(
                self.private.sign(envelope_signing_bytes(unsigned))
            ).decode("ascii"),
        )
        report = run_handoff_to_barrier(
            self.ledger,
            self.registry,
            {shard_id: envelope},
        )
        self.assertEqual(report["handoff_held_shards"], [shard_id])
        self.assertEqual(report["ledger"]["records"], [])


class V9ReleaseTests(unittest.TestCase):
    def test_release_stops_at_threshold_governance_barrier(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            release = compile_external_handoff_runtime(temporary)
            self.assertEqual(release["verdict"], "PASS")
            self.assertEqual(release["handoff_requests"], 16)
            self.assertEqual(release["handoff_packets"], 232)
            self.assertEqual(release["governance_threshold"], 3)
            self.assertEqual(
                release["operational_status"],
                "THRESHOLD_GOVERNANCE_MEMBERS_REQUIRED",
            )
            self.assertFalse(release["production_certificate_issued"])

    def test_all_v9_schemas_parse(self) -> None:
        for path in sorted(
            (ROOT / "schemas" / "kc144").glob("*-v9.schema.json")
        ):
            self.assertIsInstance(
                json.loads(path.read_text(encoding="utf-8")),
                dict,
            )


if __name__ == "__main__":
    unittest.main()
