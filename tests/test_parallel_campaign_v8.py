from __future__ import annotations

import base64
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from kc144_crystal.campaign_v8 import (
    ACTIVE_EPOCH_ID,
    CAMPAIGN_ID,
    ENROLLMENT_BOUNDARY,
    AuthorityEnrollmentProof,
    campaign_manifest,
    campaign_state,
    enrollment_signing_bytes,
    run_to_barrier,
    verify_authority_enrollment,
)
from kc144_crystal.evidence_v7 import envelope_signing_bytes
from kc144_crystal.population import digest
from kc144_crystal.repair import empty_repair_ledger, evidence_summary
from kc144_crystal.v8 import compile_parallel_campaign_runtime

from tests.test_production_evidence_v7 import (
    ISSUED_AT,
    authority_material,
    bind_packet,
    fixture_packet,
    signed_envelope,
)


ROOT = Path(__file__).resolve().parents[1]


def bind_campaign_packet(packet, shard_id: str):
    manifest = campaign_manifest()
    payload = {
        **packet.payload,
        "campaign_id": CAMPAIGN_ID,
        "campaign_topology_root": manifest["topology_root"],
        "campaign_shard_id": shard_id,
    }
    return replace(
        packet,
        payload=payload,
        payload_digest=digest(payload),
    )


def campaign_envelopes(private, key, ledger):
    result = {}
    for shard in campaign_manifest()["shards"]:
        packets = [
            bind_campaign_packet(
                bind_packet(
                    fixture_packet(
                        shard["evidence_kind"],
                        subject,
                        ledger,
                    ),
                    ledger,
                    key,
                ),
                shard["shard_id"],
            )
            for subject in shard["subject_ids"]
        ]
        result[shard["shard_id"]] = signed_envelope(
            private,
            key,
            ledger,
            packets,
            envelope_id=f"ENV-V8::{shard['shard_id']}",
        )
    return result


class CampaignTopologyTests(unittest.TestCase):
    def test_campaign_is_exact_partition_with_holographic_navigation(self) -> None:
        manifest = campaign_manifest()
        self.assertEqual(manifest["shard_count"], 16)
        self.assertEqual(manifest["packet_count"], 232)
        self.assertEqual(manifest["maximum_parallel_width"], 14)
        self.assertEqual(
            [row["packet_count"] for row in manifest["shards"]],
            [28, 9, 3, 15, 27, 4, 6, 16, 21, 37, 10, 15, 27, 12, 1, 1],
        )
        self.assertEqual(
            set(manifest["hologram"]),
            {
                "ID",
                "Coordinate",
                "Kernel",
                "Delta",
                "Routes",
                "Boundary",
                "Return",
                "Seed",
            },
        )

    def test_empty_production_state_stops_at_true_authority_barrier(self) -> None:
        ledger = empty_repair_ledger(namespace="PRODUCTION")
        from kc144_crystal.evidence_v7 import empty_authority_registry

        state = campaign_state(ledger, empty_authority_registry())
        self.assertEqual(state["completed_shards"], 0)
        self.assertEqual(len(state["structurally_ready_shards"]), 14)
        self.assertEqual(state["actionable_shards"], [])
        self.assertEqual(
            state["barrier"],
            "EXTERNAL_AUTHORITY_PIN_REQUIRED",
        )


class AuthorityEnrollmentTests(unittest.TestCase):
    def test_proof_of_possession_does_not_self_grant_authority(self) -> None:
        private, key, _ = authority_material("PRODUCTION")
        unsigned = AuthorityEnrollmentProof(
            request_id="ENROLL-V8-EXTERNAL-001",
            epoch_id=ACTIVE_EPOCH_ID,
            nonce="0123456789abcdef0123456789abcdef",
            issued_at=ISSUED_AT,
            key=key,
            boundary_claim=ENROLLMENT_BOUNDARY,
            signature_b64="",
        )
        proof = replace(
            unsigned,
            signature_b64=base64.b64encode(
                private.sign(enrollment_signing_bytes(unsigned))
            ).decode("ascii"),
        )
        report = verify_authority_enrollment(proof)
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(
            report["status"],
            "PROOF_VALID_AWAITING_EXTERNAL_GOVERNANCE_PIN",
        )
        self.assertFalse(report["registry_mutated"])
        self.assertFalse(report["authority_granted"])

    def test_tampered_enrollment_claim_fails(self) -> None:
        private, key, _ = authority_material("PRODUCTION")
        unsigned = AuthorityEnrollmentProof(
            request_id="ENROLL-V8-EXTERNAL-002",
            epoch_id=ACTIVE_EPOCH_ID,
            nonce="fedcba9876543210fedcba9876543210",
            issued_at=ISSUED_AT,
            key=key,
            boundary_claim=ENROLLMENT_BOUNDARY,
            signature_b64="",
        )
        signed = replace(
            unsigned,
            signature_b64=base64.b64encode(
                private.sign(enrollment_signing_bytes(unsigned))
            ).decode("ascii"),
        )
        tampered = replace(signed, nonce="tampered-nonce-value")
        report = verify_authority_enrollment(tampered)
        self.assertEqual(report["verdict"], "HOLD")
        self.assertFalse(report["checks"]["proof_of_possession"])


class RunToBarrierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ledger = empty_repair_ledger(namespace="TEST")
        cls.private, cls.key, cls.registry = authority_material("TEST")
        cls.envelopes = campaign_envelopes(
            cls.private,
            cls.key,
            cls.ledger,
        )

    def test_dependency_bound_envelope_is_deferred(self) -> None:
        report = run_to_barrier(
            self.ledger,
            self.registry,
            {
                "B_DEFECT_CLOSURE": self.envelopes[
                    "B_DEFECT_CLOSURE"
                ]
            },
        )
        self.assertEqual(report["admitted_shards"], [])
        self.assertEqual(
            report["deferred_shards"],
            ["B_DEFECT_CLOSURE"],
        )
        self.assertEqual(report["ledger"]["records"], [])

    def test_invalid_shard_is_held_while_independent_shard_advances(self) -> None:
        shard_id = "A_DOMAIN_KC15"
        envelope = self.envelopes[shard_id]
        first = envelope.packets[0]
        payload = {
            **first.payload,
            "campaign_shard_id": "A_DOMAIN_KC27",
        }
        tampered_packet = replace(
            first,
            payload=payload,
            payload_digest=digest(payload),
        )
        unsigned = replace(
            envelope,
            packets=(tampered_packet, *envelope.packets[1:]),
            signature_b64="",
        )
        tampered_envelope = replace(
            unsigned,
            signature_b64=base64.b64encode(
                self.private.sign(envelope_signing_bytes(unsigned))
            ).decode("ascii"),
        )
        report = run_to_barrier(
            self.ledger,
            self.registry,
            {
                shard_id: tampered_envelope,
                "A_DOMAIN_SSN12": self.envelopes["A_DOMAIN_SSN12"],
            },
        )
        self.assertEqual(report["held_shards"], [shard_id])
        self.assertEqual(report["admitted_shards"], ["A_DOMAIN_SSN12"])
        self.assertEqual(len(report["ledger"]["records"]), 4)

    def test_full_signed_campaign_runs_all_ready_subgraphs(self) -> None:
        report = run_to_barrier(
            self.ledger,
            self.registry,
            self.envelopes,
        )
        self.assertEqual(report["status"], "COMPLETE")
        self.assertEqual(len(report["admitted_shards"]), 16)
        self.assertEqual(report["held_shards"], [])
        self.assertEqual(report["deferred_shards"], [])
        self.assertEqual(
            report["barrier"],
            "TEST_CAMPAIGN_COMPLETE_NO_PRODUCTION_EFFECT",
        )
        self.assertEqual(len(report["ledger"]["records"]), 232)
        summary = evidence_summary(report["ledger"])
        self.assertEqual(
            summary["observed_state"],
            {
                "certified_bridges": 28,
                "domain_population": 144,
                "independent_replays": 144,
                "blocking_defects": 0,
                "ic10_promoted": True,
            },
        )
        self.assertEqual(summary["production_truth_effect"], "NONE")
        self.assertEqual(
            summary["production_effective_state"]["domain_population"],
            86,
        )


class V8ReleaseTests(unittest.TestCase):
    def test_release_compiles_to_explicit_external_barrier(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            release = compile_parallel_campaign_runtime(temporary)
            self.assertEqual(release["verdict"], "PASS")
            self.assertEqual(release["campaign_shards"], 16)
            self.assertEqual(release["campaign_packets"], 232)
            self.assertEqual(release["maximum_parallel_width"], 14)
            self.assertEqual(
                release["operational_status"],
                "EXTERNAL_AUTHORITY_PIN_REQUIRED",
            )
            self.assertFalse(release["production_certificate_issued"])

    def test_all_v8_schemas_parse(self) -> None:
        for path in sorted(
            (ROOT / "schemas" / "kc144").glob("*-v8.schema.json")
        ):
            self.assertIsInstance(
                json.loads(path.read_text(encoding="utf-8")),
                dict,
            )


if __name__ == "__main__":
    unittest.main()
