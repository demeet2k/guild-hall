from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kc144_crystal.bridge2pc import (
    CommitAuthorization,
    commit_bridge,
    empty_production_bridge_commit_ledger,
    prepare_bridge_commit,
)
from kc144_crystal.edge_manifest import freeze_edge_manifest
from kc144_crystal.session import SessionSpec, cold_reconstruct, compile_session
from kc144_crystal.v5 import compile_global_state, default_session_spec
from kc144_crystal.witness import BridgeWitnessPacket


FIXTURE = (
    Path(__file__).parent / "fixtures" / "synthetic_bridge_witness.json"
)


def packet() -> BridgeWitnessPacket:
    return BridgeWitnessPacket.from_dict(
        json.loads(FIXTURE.read_text(encoding="utf-8"))
    )


class FrozenEdgeManifestTests(unittest.TestCase):
    def test_manifest_is_complete_and_loss_declaring(self) -> None:
        manifest = freeze_edge_manifest()
        self.assertEqual(manifest["status"], "FROZEN")
        self.assertEqual(manifest["relation_record_count"], 276)
        self.assertEqual(manifest["distinct_adjacency_count"], 274)
        self.assertEqual(
            manifest["standing_census"],
            {"STRUCTURAL": 248, "DECLARED_UNCERTIFIED": 28},
        )
        self.assertTrue(manifest["all_edges_declare_carry"])
        self.assertTrue(manifest["all_edges_declare_loss"])

    def test_manifest_digest_is_stable(self) -> None:
        self.assertEqual(
            freeze_edge_manifest()["manifest_digest"],
            freeze_edge_manifest()["manifest_digest"],
        )

    def test_edge_ids_are_unique(self) -> None:
        records = freeze_edge_manifest()["records"]
        self.assertEqual(len({record["edge_id"] for record in records}), 276)


class TraversalSessionTests(unittest.TestCase):
    def test_session_requires_queries(self) -> None:
        with self.assertRaises(ValueError):
            SessionSpec("empty", "epoch", ())

    def test_receipt_chain_is_append_only_and_exact(self) -> None:
        session = compile_session(default_session_spec())
        previous = "GENESIS"
        for sequence, receipt in enumerate(session["receipts"], start=1):
            self.assertEqual(receipt["sequence"], sequence)
            self.assertEqual(receipt["previous_receipt_digest"], previous)
            previous = receipt["receipt_digest"]
        self.assertEqual(session["receipt_root"], previous)

    def test_wave_and_explicit_coverage_are_not_collapsed(self) -> None:
        coverage = compile_session(default_session_spec())["observatory"][
            "M11_ROUTE_COVERAGE_AUDIT"
        ]
        self.assertEqual(coverage["wave_node_coverage"], "144/144")
        self.assertNotEqual(
            coverage["explicit_node_coverage"],
            coverage["wave_node_coverage"],
        )
        self.assertEqual(coverage["returnable_compiled_queries"], 2)
        self.assertEqual(coverage["compiled_queries"], 2)

    def test_projective_synapse_is_overlay_only(self) -> None:
        synapses = compile_session(default_session_spec())["observatory"][
            "M10_PROJECTIVE_SYNAPSE_MAP"
        ]
        self.assertTrue(synapses)
        self.assertTrue(
            all(synapse["truth_effect"] == "NONE" for synapse in synapses)
        )

    def test_ssn12_refuses_false_solid_state(self) -> None:
        solid = compile_session(default_session_spec())["observatory"][
            "M12_SOLID_STATE"
        ]
        self.assertEqual(solid["verdict"], "HOLD")
        self.assertEqual(solid["passed"], 4)
        self.assertEqual(solid["total"], 9)
        self.assertIsNone(solid["certificate"])
        for gate in (
            "M12_BRIDGES_CERTIFIED_28",
            "M12_DOMAIN_POPULATION_144",
            "M12_INDEPENDENT_REPLAY_144",
            "M12_IC10_DECISION_PROMOTED",
            "M12_BLOCKING_DEFECTS_EMPTY",
        ):
            self.assertEqual(solid["gates"][gate], "FAIL")

    def test_all_twelve_observatory_surfaces_exist(self) -> None:
        observatory = compile_session(default_session_spec())["observatory"]
        self.assertEqual(len(observatory), 12)
        self.assertEqual(
            sorted(observatory),
            sorted(
                key
                for key in observatory
                if key.startswith(tuple(f"M{i:02d}" for i in range(1, 13)))
            ),
        )


class ColdReconstructionTests(unittest.TestCase):
    def test_reentry_seed_reconstructs_exactly(self) -> None:
        session = compile_session(default_session_spec())
        replay = cold_reconstruct(session["reentry_seed"])
        self.assertEqual(replay["verdict"], "PASS")
        self.assertEqual(replay["replay_level"], "N5_DETERMINISTIC_SELF_REPLAY")
        self.assertFalse(replay["independent_replay"])
        self.assertEqual(replay["promotion_effect"], "NONE")

    def test_mutated_expected_root_is_detected(self) -> None:
        session = compile_session(default_session_spec())
        seed = {**session["reentry_seed"], "expected_receipt_root": "sha256:" + "0" * 64}
        replay = cold_reconstruct(seed)
        self.assertEqual(replay["verdict"], "FAIL")
        self.assertFalse(replay["checks"]["receipt_root_exact"])


class BridgeTwoPhaseCommitTests(unittest.TestCase):
    def test_prepare_does_not_mutate_production(self) -> None:
        prepared = prepare_bridge_commit(packet())
        self.assertEqual(prepared["status"], "PREPARED")
        self.assertFalse(prepared["production_ledger_mutated"])

    def test_synthetic_packet_cannot_commit_to_production(self) -> None:
        prepared = prepare_bridge_commit(packet())
        authorization = CommitAuthorization(
            "AUTH-TEST",
            "test-authority",
            "KC144.BRIDGE_COMMIT::BR001",
            "VERIFIED",
            test_only=True,
        )
        committed = commit_bridge(prepared, packet(), authorization)
        self.assertEqual(committed["status"], "HOLD")
        self.assertFalse(committed["production_ledger_mutated"])

    def test_synthetic_packet_can_exercise_test_ledger_only(self) -> None:
        prepared = prepare_bridge_commit(packet())
        authorization = CommitAuthorization(
            "AUTH-TEST",
            "test-authority",
            "KC144.BRIDGE_COMMIT::BR001",
            "VERIFIED",
            test_only=True,
        )
        committed = commit_bridge(
            prepared,
            packet(),
            authorization,
            namespace="TEST",
        )
        self.assertEqual(committed["status"], "COMMITTED")
        self.assertEqual(committed["record"]["standing"], "TEST_ONLY_TRANSPORT_COMMIT")
        self.assertFalse(committed["production_ledger_mutated"])
        self.assertEqual(committed["station_promotion_effect"], "NONE")

    def test_production_commit_ledger_starts_empty(self) -> None:
        ledger = empty_production_bridge_commit_ledger()
        self.assertEqual(ledger["committed"], 0)
        self.assertEqual(ledger["open_transport_obligations"], 28)


class GlobalStateReleaseTests(unittest.TestCase):
    def test_global_state_compiler_emits_complete_v5(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            release = compile_global_state(temporary)
            self.assertEqual(release["verdict"], "PASS")
            self.assertEqual(release["edge_manifest"]["records"], 276)
            self.assertEqual(release["cold_reconstruction"], "N5_DETERMINISTIC_SELF_REPLAY")
            self.assertFalse(release["independent_replay"])
            self.assertEqual(release["solid_state"], "HOLD")
            for filename in release["added_artifacts"] + [
                "global_state_release_v5.json"
            ]:
                document = json.loads(
                    (Path(temporary) / filename).read_text(encoding="utf-8")
                )
                self.assertIsInstance(document, dict)


if __name__ == "__main__":
    unittest.main()
