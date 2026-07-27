from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kc144_crystal.query import QueryBundle, compile_query, query_contract
from kc144_crystal.v4 import compile_mycelium_framework, default_query_bundles
from kc144_crystal.witness import (
    BridgeWitnessPacket,
    WitnessAttestation,
    bridge_witness_contract,
    evaluate_bridge_witness,
)


def witness_packet(*, self_authored: bool = False) -> BridgeWitnessPacket:
    return BridgeWitnessPacket(
        packet_id="SYNTHETIC-TEST-BR001",
        bridge_id="BR001",
        source=41,
        target=81,
        transport="synthetic identity-preserving test transport",
        preserved_invariants=("GID identity", "raw CID"),
        declared_loss="NONE_IN_SYNTHETIC_TEST_CORRIDOR",
        corridor="SYNTHETIC_TEST_ONLY",
        return_path=(81, 41),
        attestations=(
            WitnessAttestation(
                witness_id="SYNTHETIC-W01",
                evidence_root="sha256:" + "a" * 64,
                author_id="author-A",
                verifier_id="author-A" if self_authored else "verifier-B",
                replay_class="B3",
                signature_status="VERIFIED",
                authority=True,
            ),
        ),
    )


class QueryBundleTests(unittest.TestCase):
    def test_contract_preserves_all_h06_fields(self) -> None:
        contract = query_contract()
        for field in (
            "query_id",
            "goal",
            "terms",
            "domains",
            "operators",
            "invariants",
            "boundaries",
            "evidence_floor",
            "start_coordinates",
            "route_budget",
            "return_mode",
        ):
            self.assertIn(field, contract["notation"])

    def test_invalid_domain_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            QueryBundle("bad", "bad domain", domains=("NOT_A_BAND",))

    def test_mapping_round_trip(self) -> None:
        original = default_query_bundles()[0]
        self.assertEqual(QueryBundle.from_dict(original.to_dict()), original)


class QueryCompilerTests(unittest.TestCase):
    def test_default_structural_query_compiles(self) -> None:
        report = compile_query(default_query_bundles()[0])
        self.assertEqual(report["status"], "COMPILED")
        self.assertTrue(report["selected"])
        self.assertFalse(report["base_graph_mutated"])
        self.assertFalse(report["evidence_overlay_mutated"])
        self.assertEqual(report["truth_effect"], "NONE")

    def test_routes_obey_budget_and_expose_bridges(self) -> None:
        report = compile_query(default_query_bundles()[0])
        for result in report["selected"]:
            self.assertLessEqual(
                result["forward_route"]["hops"],
                report["query"]["route_budget"],
            )
            self.assertEqual(
                result["route_standing"],
                (
                    "DECLARED_ROUTE_WITH_OPEN_TRANSPORT_CERTIFICATION"
                    if result["open_bridge_ids"]
                    else "STRUCTURAL_ROUTE"
                ),
            )

    def test_source_floor_does_not_admit_derived_seats(self) -> None:
        report = compile_query(default_query_bundles()[1])
        self.assertEqual(report["status"], "COMPILED")
        self.assertTrue(report["selected"])
        self.assertTrue(
            all(result["domain_state"] == "SOURCE_DECLARED" for result in report["selected"])
        )

    def test_independent_replay_floor_refuses_without_evidence(self) -> None:
        report = compile_query(default_query_bundles()[2])
        self.assertEqual(report["status"], "REFUSED")
        self.assertEqual(report["refusal"]["code"], "EVIDENCE_FLOOR_UNSATISFIED")
        self.assertEqual(report["selected"], [])

    def test_independent_overlay_enables_only_bound_gid(self) -> None:
        query = QueryBundle(
            "overlay",
            "activation replay reseed",
            terms=("activation",),
            evidence_floor="INDEPENDENT_REPLAY",
            start_coordinates=(6,),
            route_budget=0,
            return_mode="NONE",
        )
        report = compile_query(query, evidence_overlay={6: {"independent_replay": True}})
        self.assertEqual([result["gid"] for result in report["selected"]], [6])

    def test_ranking_is_pareto_and_disclosed(self) -> None:
        report = compile_query(default_query_bundles()[0])
        self.assertIn("Pareto", report["ranking_law"])
        self.assertTrue(all(result["rank_vector"] for result in report["selected"]))


class BridgeWitnessTests(unittest.TestCase):
    def test_contract_retains_full_beta_tuple(self) -> None:
        contract = bridge_witness_contract()
        for field in (
            "F_i",
            "F_j",
            "T_ij",
            "K_preserved",
            "Delta_ij",
            "R_ji",
            "W_ij",
        ):
            self.assertIn(field, contract["notation"])

    def test_self_authored_witness_holds(self) -> None:
        report = evaluate_bridge_witness(witness_packet(self_authored=True))
        self.assertEqual(report["verdict"], "HOLD")
        self.assertEqual(report["bridge_truth_effect"], "NONE")
        self.assertFalse(report["production_registry_mutated"])

    def test_complete_independent_packet_certifies_only_transport(self) -> None:
        report = evaluate_bridge_witness(witness_packet())
        self.assertEqual(report["verdict"], "CERTIFIED")
        self.assertEqual(
            report["bridge_truth_effect"],
            "TRANSPORT_CERTIFIED_INSIDE_DECLARED_CORRIDOR",
        )
        self.assertEqual(report["station_promotion_effect"], "NONE")
        self.assertFalse(report["production_registry_mutated"])

    def test_wrong_endpoints_hold(self) -> None:
        packet = witness_packet()
        wrong = BridgeWitnessPacket(
            **{**packet.to_dict(), "target": 82, "attestations": packet.attestations}
        )
        report = evaluate_bridge_witness(wrong)
        self.assertEqual(report["verdict"], "HOLD")


class MyceliumReleaseTests(unittest.TestCase):
    def test_v4_compiler_emits_release_and_refusal_probe(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            release = compile_mycelium_framework(temporary)
            self.assertEqual(release["verdict"], "PASS")
            self.assertEqual(release["bridge_runtime"]["certified"], 0)
            for filename in release["added_artifacts"] + ["mycelium_release.json"]:
                document = json.loads(
                    (Path(temporary) / filename).read_text(encoding="utf-8")
                )
                self.assertIsInstance(document, dict)
            queries = json.loads(
                (Path(temporary) / "compiled_queries.json").read_text(encoding="utf-8")
            )["queries"]
            self.assertEqual([query["status"] for query in queries], [
                "COMPILED",
                "COMPILED",
                "REFUSED",
            ])


if __name__ == "__main__":
    unittest.main()
