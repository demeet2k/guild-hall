from __future__ import annotations

import base64
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from kc144_crystal.crosswalk import (
    ACTIVE_EPOCH_CENSUS,
    ACTIVE_EPOCH_ID,
    compile_coordinate_crosswalk,
    domain_binding_for_subject,
    graph_slice_registry,
)
from kc144_crystal.bridge2pc import (
    CommitAuthorization,
    commit_bridge,
    prepare_bridge_commit,
)
from kc144_crystal.evidence_v7 import (
    AuthorityKey,
    SignedEvidenceEnvelope,
    admit_signed_envelope,
    envelope_signing_bytes,
    seal_authority_registry,
    verify_signed_envelope,
)
from kc144_crystal.population import digest
from kc144_crystal.repair import (
    EvidenceAuthority,
    M12EvidencePacket,
    admit_evidence,
    empty_repair_ledger,
    evidence_packet_contract,
    evidence_summary,
    verify_repair_ledger,
)
from kc144_crystal.v7 import compile_production_evidence_kernel
from kc144_crystal.witness import BridgeWitnessPacket


ROOT = Path(__file__).resolve().parents[1]
ISSUED_AT = "2026-07-27T00:00:00+00:00"
REPLAY_CLASS = {
    "BRIDGE_CERTIFICATION": "B3",
    "DOMAIN_POPULATION": "B2",
    "INDEPENDENT_REPLAY": "EXACT",
    "DEFECT_CLOSURE": "EXACT",
    "IC10_PROMOTION": "EXACT",
}
REPAIR_LAYER = {
    "BRIDGE_CERTIFICATION": "TRANSPORT",
    "DOMAIN_POPULATION": "SOURCE_BINDING",
    "INDEPENDENT_REPLAY": "REPLAY",
    "DEFECT_CLOSURE": "DEFECT",
    "IC10_PROMOTION": "PROMOTION",
}


def fixture_packet(
    kind: str,
    subject: str,
    ledger: dict,
) -> M12EvidencePacket:
    if kind == "BRIDGE_CERTIFICATION":
        payload = {
            "bridge_id": subject,
            "standing": "TEST_ONLY_TRANSPORT_COMMIT",
            "commit_digest": digest((kind, subject, "commit")),
            "transport_evaluation_digest": digest(
                (kind, subject, "evaluation")
            ),
            "return_witness_root": digest((kind, subject, "return")),
        }
    elif kind == "DOMAIN_POPULATION":
        payload = {
            "gid": int(subject[3:]),
            "source_object_id": f"SOURCE::{subject}",
            "content_digest": digest((kind, subject, "content")),
            "carrier": "SOURCE_BOUND_STATION_BODY",
        }
    elif kind == "INDEPENDENT_REPLAY":
        root = digest((kind, subject, "state"))
        payload = {
            "gid": int(subject[3:]),
            "expected_state_root": root,
            "replayed_state_root": root,
            "result": "EXACT",
        }
    elif kind == "DEFECT_CLOSURE":
        payload = {
            "defect_id": subject,
            "result": "CLOSED",
            "closure_root": digest((kind, subject, "closure")),
        }
    else:
        payload = {
            "candidate_id": subject,
            "decision": "PROMOTED",
            "state_root": ledger["frozen_base"]["state_root"],
            "gate_vector": {
                f"I{index:02d}": "PASS" for index in range(1, 11)
            },
            "successor_seed": "KC144.V2::POPULATE_MATH144",
        }
    scope = (
        f"KC144.IC10.PROMOTION::{subject}"
        if kind == "IC10_PROMOTION"
        else f"KC144.M12.{kind}::{subject}"
    )
    return M12EvidencePacket(
        packet_id=f"SIM::{kind}::{subject}",
        kind=kind,
        subject_id=subject,
        namespace="TEST",
        evidence_class="TEST_FIXTURE",
        evidence_root=digest((kind, subject, "evidence")),
        source_ref=f"test://{kind}/{subject}",
        replay_class=REPLAY_CLASS[kind],
        contradiction_class="NONE_FOUND",
        repair_layer=REPAIR_LAYER[kind],
        trust_revision_witness=f"TRUST::{kind}::{subject}",
        reentry_permit_id=f"REENTRY::{kind}::{subject}",
        payload=payload,
        payload_digest=digest(payload),
        authority=EvidenceAuthority(
            authority_id=f"AUTH::{kind}",
            scope=scope,
            signature_status="VERIFIED",
            independent=True,
            test_only=True,
        ),
    )


def authority_material(namespace: str = "TEST"):
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    key = AuthorityKey(
        key_id=f"AUTH-V7-{namespace}",
        algorithm="ED25519",
        public_key_b64=base64.b64encode(public).decode("ascii"),
        scopes=("KC144.M12.*", "KC144.IC10.PROMOTION::*"),
        namespaces=(namespace,),
        status="ACTIVE",
        independent=True,
        test_only=namespace == "TEST",
        not_before="2026-01-01T00:00:00+00:00",
        not_after="2027-01-01T00:00:00+00:00",
    )
    return private, key, seal_authority_registry([key])


def bind_packet(
    packet: M12EvidencePacket,
    ledger: dict,
    key: AuthorityKey,
) -> M12EvidencePacket:
    crosswalk = compile_coordinate_crosswalk()
    graph = graph_slice_registry()
    algebra = next(
        row for row in graph["slices"] if row["slice_id"] == "X16_ALGEBRA"
    )
    payload = {
        **packet.payload,
        "epoch_id": ACTIVE_EPOCH_ID,
        "frozen_base_root": ledger["frozen_base"]["state_root"],
        "crosswalk_digest": crosswalk["crosswalk_digest"],
    }
    if packet.kind in {"BRIDGE_CERTIFICATION", "INDEPENDENT_REPLAY"}:
        payload.update(
            {
                "graph_slice": "X16_ALGEBRA",
                "graph_slice_digest": algebra["slice_digest"],
            }
        )
    if packet.kind == "DOMAIN_POPULATION":
        coordinate_binding = domain_binding_for_subject(packet.subject_id)
        payload["coordinate_binding"] = coordinate_binding
        if coordinate_binding.get("adjudication_required"):
            payload.update(
                {
                    "adjudication_status": "RESOLVED",
                    "adjudication_receipt_root": digest(
                        ("ADJUDICATION", packet.subject_id)
                    ),
                }
            )
    if packet.kind == "IC10_PROMOTION":
        vector = {f"I{index:02d}": "PASS" for index in range(1, 11)}
        payload.update(
            {
                "constitutional_gate_vector": vector,
                "immune_gate_vector": vector,
            }
        )
    scope = (
        f"KC144.IC10.PROMOTION::{packet.subject_id}"
        if packet.kind == "IC10_PROMOTION"
        else f"KC144.M12.{packet.kind}::{packet.subject_id}"
    )
    return replace(
        packet,
        payload=payload,
        payload_digest=digest(payload),
        authority=EvidenceAuthority(
            authority_id=key.key_id,
            scope=scope,
            signature_status="VERIFIED",
            independent=key.independent,
            test_only=key.test_only,
        ),
    )


def signed_envelope(
    private: Ed25519PrivateKey,
    key: AuthorityKey,
    ledger: dict,
    packets: list[M12EvidencePacket],
    *,
    envelope_id: str = "ENV-V7-TEST",
) -> SignedEvidenceEnvelope:
    crosswalk = compile_coordinate_crosswalk()
    graph = graph_slice_registry()
    algebra = next(
        row for row in graph["slices"] if row["slice_id"] == "X16_ALGEBRA"
    )
    unsigned = SignedEvidenceEnvelope(
        envelope_id=envelope_id,
        namespace=ledger["namespace"],
        epoch_id=ACTIVE_EPOCH_ID,
        epoch_census=ACTIVE_EPOCH_CENSUS,
        frozen_base_root=ledger["frozen_base"]["state_root"],
        crosswalk_digest=crosswalk["crosswalk_digest"],
        graph_slice="X16_ALGEBRA",
        graph_slice_digest=algebra["slice_digest"],
        issued_at=ISSUED_AT,
        signer_key_id=key.key_id,
        packets=tuple(packets),
        signature_b64="",
    )
    signature = private.sign(envelope_signing_bytes(unsigned))
    return replace(
        unsigned,
        signature_b64=base64.b64encode(signature).decode("ascii"),
    )


class CrosswalkTests(unittest.TestCase):
    def test_all_difference_is_typed_without_mutating_identity(self) -> None:
        crosswalk = compile_coordinate_crosswalk()
        self.assertEqual(crosswalk["epoch_id"], ACTIVE_EPOCH_ID)
        self.assertTrue(crosswalk["kc15"]["bijection"])
        self.assertEqual(crosswalk["kc15"]["relocated"], 10)
        self.assertTrue(crosswalk["kc27"]["exact"])
        self.assertEqual(len(crosswalk["ssn12"]["entries"]), 12)
        self.assertTrue(crosswalk["ssn12"]["collapse_forbidden"])
        self.assertEqual(len(crosswalk["f37_branch_ledger"]["entries"]), 3)

    def test_graph_slices_are_simultaneous_but_not_collapsed(self) -> None:
        registry = graph_slice_registry()
        counts = {
            row["slice_id"]: row["relation_record_count"]
            for row in registry["slices"]
        }
        self.assertEqual(
            counts,
            {
                "X16_SCHEDULE": 268,
                "X16_ALGEBRA": 276,
                "X16_MULTIPLEX": 308,
            },
        )
        self.assertEqual(registry["active_frozen_slice"], "X16_ALGEBRA")
        self.assertEqual(registry["maximum_union_slice"], "X16_MULTIPLEX")


class CryptographicEnvelopeTests(unittest.TestCase):
    def test_direct_bridge_commit_is_fail_closed(self) -> None:
        fixture = BridgeWitnessPacket.from_dict(
            json.loads(
                (
                    ROOT
                    / "tests"
                    / "fixtures"
                    / "synthetic_bridge_witness.json"
                ).read_text(encoding="utf-8")
            )
        )
        external = replace(
            fixture,
            packet_id="EXTERNAL-BRIDGE-WITNESS-BR001",
            corridor="ACTIVE-EPOCH-TRANSPORT-CORRIDOR",
        )
        preparation = prepare_bridge_commit(external)
        self.assertEqual(preparation["status"], "PREPARED")
        authorization = CommitAuthorization(
            "AUTH-EXTERNAL-BR001",
            "AUTH-V7-PRODUCTION",
            "KC144.BRIDGE_COMMIT::BR001",
            "VERIFIED",
            test_only=False,
        )
        report = commit_bridge(
            preparation,
            external,
            authorization,
            namespace="PRODUCTION",
        )
        self.assertEqual(report["status"], "HOLD")
        self.assertFalse(report["checks"]["cryptographic_envelope"])

    def test_direct_v6_production_admission_is_fail_closed(self) -> None:
        ledger = empty_repair_ledger(namespace="PRODUCTION")
        subject = evidence_packet_contract()["targets"]["DOMAIN_POPULATION"][
            "subject_ids"
        ][0]
        packet = fixture_packet("DOMAIN_POPULATION", subject, ledger)
        production_packet = replace(
            packet,
            packet_id="EXTERNAL-DOMAIN-EVIDENCE",
            namespace="PRODUCTION",
            evidence_class="EXTERNAL",
            authority=replace(
                packet.authority,
                test_only=False,
            ),
        )
        report = admit_evidence(ledger, production_packet)
        self.assertEqual(report["status"], "HOLD")
        self.assertFalse(report["checks"]["cryptographic_envelope"])

    def test_real_ed25519_envelope_verifies_and_admits_atomically(self) -> None:
        ledger = empty_repair_ledger(namespace="TEST")
        private, key, registry = authority_material()
        subject = evidence_packet_contract()["targets"]["DOMAIN_POPULATION"][
            "subject_ids"
        ][0]
        packet = bind_packet(
            fixture_packet("DOMAIN_POPULATION", subject, ledger),
            ledger,
            key,
        )
        envelope = signed_envelope(private, key, ledger, [packet])
        verification = verify_signed_envelope(envelope, registry, ledger)
        self.assertEqual(verification["verdict"], "PASS")
        self.assertTrue(verification["checks"]["signature_valid"])
        admitted = admit_signed_envelope(ledger, envelope, registry)
        self.assertEqual(admitted["status"], "ADMITTED")
        self.assertTrue(admitted["atomic"])
        self.assertEqual(admitted["records_admitted"], 1)

    def test_production_record_retains_reverifiable_envelope_context(self) -> None:
        ledger = empty_repair_ledger(namespace="PRODUCTION")
        private, key, registry = authority_material("PRODUCTION")
        subject = evidence_packet_contract()["targets"]["DOMAIN_POPULATION"][
            "subject_ids"
        ][0]
        packet = bind_packet(
            fixture_packet("DOMAIN_POPULATION", subject, ledger),
            ledger,
            key,
        )
        packet = replace(
            packet,
            packet_id="EXTERNAL-DOMAIN-GID055",
            namespace="PRODUCTION",
            evidence_class="EXTERNAL",
            source_ref="external://source/GID055",
        )
        envelope = signed_envelope(
            private,
            key,
            ledger,
            [packet],
            envelope_id="ENV-V7-PRODUCTION-GID055",
        )
        report = admit_signed_envelope(ledger, envelope, registry)
        self.assertEqual(report["status"], "ADMITTED")
        self.assertEqual(len(report["ledger"]["v7_envelopes"]), 1)
        self.assertEqual(
            verify_repair_ledger(report["ledger"])["verdict"],
            "PASS",
        )
        self.assertEqual(
            evidence_summary(report["ledger"])[
                "production_effective_state"
            ]["domain_population"],
            87,
        )

    def test_signature_tampering_holds_without_mutation(self) -> None:
        ledger = empty_repair_ledger(namespace="TEST")
        private, key, registry = authority_material()
        subject = evidence_packet_contract()["targets"]["DOMAIN_POPULATION"][
            "subject_ids"
        ][0]
        packet = bind_packet(
            fixture_packet("DOMAIN_POPULATION", subject, ledger),
            ledger,
            key,
        )
        envelope = signed_envelope(private, key, ledger, [packet])
        tampered = replace(envelope, graph_slice="X16_SCHEDULE")
        report = admit_signed_envelope(ledger, tampered, registry)
        self.assertEqual(report["status"], "HOLD")
        self.assertEqual(report["records_admitted"], 0)
        self.assertEqual(report["ledger"]["head_digest"], "GENESIS")

    def test_wrong_domain_coordinate_binding_holds_atomically(self) -> None:
        ledger = empty_repair_ledger(namespace="TEST")
        private, key, registry = authority_material()
        packet = bind_packet(
            fixture_packet("DOMAIN_POPULATION", "GID091", ledger),
            ledger,
            key,
        )
        payload = {
            **packet.payload,
            "coordinate_binding": {
                **packet.payload["coordinate_binding"],
                "runtime_gid": 999,
            },
        }
        packet = replace(
            packet,
            payload=payload,
            payload_digest=digest(payload),
        )
        envelope = signed_envelope(private, key, ledger, [packet])
        report = admit_signed_envelope(ledger, envelope, registry)
        self.assertEqual(report["status"], "HOLD")
        self.assertEqual(report["records_admitted"], 0)
        self.assertFalse(
            report["verification"]["packet_reports"][0]["checks"][
                "domain_coordinate_binding"
            ]
        )

    def test_production_graph_packet_cannot_activate_multiplex_slice(self) -> None:
        ledger = empty_repair_ledger(namespace="PRODUCTION")
        private, key, registry = authority_material("PRODUCTION")
        packet = bind_packet(
            fixture_packet("INDEPENDENT_REPLAY", "GID001", ledger),
            ledger,
            key,
        )
        graph = graph_slice_registry()
        multiplex = next(
            row
            for row in graph["slices"]
            if row["slice_id"] == "X16_MULTIPLEX"
        )
        payload = {
            **packet.payload,
            "graph_slice": "X16_MULTIPLEX",
            "graph_slice_digest": multiplex["slice_digest"],
        }
        packet = replace(
            packet,
            packet_id="EXTERNAL-REPLAY-GID001",
            namespace="PRODUCTION",
            evidence_class="EXTERNAL",
            payload=payload,
            payload_digest=digest(payload),
        )
        envelope = signed_envelope(private, key, ledger, [packet])
        unsigned = replace(
            envelope,
            graph_slice="X16_MULTIPLEX",
            graph_slice_digest=multiplex["slice_digest"],
            signature_b64="",
        )
        envelope = replace(
            unsigned,
            signature_b64=base64.b64encode(
                private.sign(envelope_signing_bytes(unsigned))
            ).decode("ascii"),
        )
        report = admit_signed_envelope(ledger, envelope, registry)
        self.assertEqual(report["status"], "HOLD")
        self.assertTrue(report["verification"]["checks"]["signature_valid"])
        self.assertFalse(
            report["verification"]["packet_reports"][0]["checks"][
                "active_graph_slice_bound"
            ]
        )

    def test_duplicate_authority_identifier_fails_registry_integrity(self) -> None:
        ledger = empty_repair_ledger(namespace="TEST")
        private, key, registry = authority_material()
        packet = bind_packet(
            fixture_packet("DOMAIN_POPULATION", "GID055", ledger),
            ledger,
            key,
        )
        envelope = signed_envelope(private, key, ledger, [packet])
        body = {
            name: value
            for name, value in registry.items()
            if name != "registry_digest"
        }
        body["keys"] = [*body["keys"], dict(body["keys"][0])]
        duplicate_registry = {**body, "registry_digest": digest(body)}
        report = verify_signed_envelope(
            envelope,
            duplicate_registry,
            ledger,
        )
        self.assertEqual(report["verdict"], "HOLD")
        self.assertFalse(report["checks"]["registry_integrity"])

    def test_contested_packet_holds_the_whole_envelope(self) -> None:
        ledger = empty_repair_ledger(namespace="TEST")
        private, key, registry = authority_material()
        subjects = evidence_packet_contract()["targets"]["DOMAIN_POPULATION"][
            "subject_ids"
        ][:2]
        packets = [
            bind_packet(
                fixture_packet("DOMAIN_POPULATION", subject, ledger),
                ledger,
                key,
            )
            for subject in subjects
        ]
        packets[1] = replace(packets[1], contradiction_class="CONTESTED")
        envelope = signed_envelope(private, key, ledger, packets)
        report = admit_signed_envelope(ledger, envelope, registry)
        self.assertEqual(report["status"], "HOLD")
        self.assertEqual(report["records_admitted"], 0)
        self.assertEqual(report["ledger"]["records"], [])

    def test_full_signed_test_campaign_closes_mechanics_only(self) -> None:
        ledger = empty_repair_ledger(namespace="TEST")
        private, key, registry = authority_material()
        contract = evidence_packet_contract()
        packets = []
        for kind in (
            "BRIDGE_CERTIFICATION",
            "DOMAIN_POPULATION",
            "INDEPENDENT_REPLAY",
        ):
            for subject in contract["targets"][kind]["subject_ids"]:
                packets.append(
                    bind_packet(
                        fixture_packet(kind, subject, ledger),
                        ledger,
                        key,
                    )
                )
        packets.append(
            bind_packet(
                fixture_packet(
                    "DEFECT_CLOSURE",
                    "DEF-M12-OPEN-GATES",
                    ledger,
                ),
                ledger,
                key,
            )
        )
        packets.append(
            bind_packet(
                fixture_packet(
                    "IC10_PROMOTION",
                    "KC144.SSN12.GLOBAL_STATE.V5",
                    ledger,
                ),
                ledger,
                key,
            )
        )
        envelope = signed_envelope(
            private,
            key,
            ledger,
            packets,
            envelope_id="ENV-V7-FULL-TEST-CAMPAIGN",
        )
        report = admit_signed_envelope(ledger, envelope, registry)
        self.assertEqual(report["status"], "ADMITTED")
        self.assertEqual(report["records_admitted"], 232)
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
        self.assertEqual(
            summary["production_effective_state"]["certified_bridges"],
            0,
        )


class V7ReleaseTests(unittest.TestCase):
    def test_default_release_is_internally_ready_and_externally_honest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            release = compile_production_evidence_kernel(temporary)
            self.assertEqual(release["verdict"], "PASS")
            self.assertEqual(
                release["operational_status"],
                "READY_AWAITING_PINNED_EXTERNAL_AUTHORITY",
            )
            self.assertEqual(release["m12_status"], "HOLD")
            self.assertFalse(release["production_certificate_issued"])
            state = json.loads(
                (
                    Path(temporary)
                    / "production_evidence_state_v7.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(state["internal_readiness"]["verdict"], "PASS")
            self.assertEqual(
                state["external_readiness"]["pinned_active_keys"],
                0,
            )

    def test_test_only_key_does_not_satisfy_production_readiness(self) -> None:
        _, _, registry = authority_material("TEST")
        with tempfile.TemporaryDirectory() as temporary:
            release = compile_production_evidence_kernel(
                temporary,
                authority_registry=registry,
            )
            self.assertEqual(release["verdict"], "PASS")
            self.assertEqual(
                release["operational_status"],
                "READY_AWAITING_PINNED_EXTERNAL_AUTHORITY",
            )

    def test_production_eligible_key_opens_ingress_not_m12(self) -> None:
        _, _, registry = authority_material("PRODUCTION")
        with tempfile.TemporaryDirectory() as temporary:
            release = compile_production_evidence_kernel(
                temporary,
                authority_registry=registry,
            )
            self.assertEqual(release["verdict"], "PASS")
            self.assertEqual(release["operational_status"], "READY")
            self.assertEqual(release["m12_status"], "HOLD")
            self.assertFalse(release["production_certificate_issued"])

    def test_all_v7_schemas_parse(self) -> None:
        for path in sorted((ROOT / "schemas" / "kc144").glob("*-v7.schema.json")):
            self.assertIsInstance(
                json.loads(path.read_text(encoding="utf-8")),
                dict,
            )


if __name__ == "__main__":
    unittest.main()
