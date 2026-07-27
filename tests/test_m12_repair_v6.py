from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kc144_crystal.population import digest
from kc144_crystal.repair import (
    EvidenceAuthority,
    M12EvidencePacket,
    admit_evidence,
    empty_repair_ledger,
    evidence_packet_contract,
    evidence_summary,
    repair_plan,
    verify_repair_ledger,
)
from kc144_crystal.session import compile_session
from kc144_crystal.v5 import default_session_spec
from kc144_crystal.v6 import compile_repair_framework, compile_repair_state


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


def sha(value: object) -> str:
    return digest(value)


def payload(kind: str, subject: str, ledger: dict) -> dict:
    if kind == "BRIDGE_CERTIFICATION":
        return {
            "bridge_id": subject,
            "standing": "TEST_ONLY_TRANSPORT_COMMIT",
            "commit_digest": sha((kind, subject, "commit")),
            "transport_evaluation_digest": sha((kind, subject, "evaluation")),
            "return_witness_root": sha((kind, subject, "return")),
        }
    if kind == "DOMAIN_POPULATION":
        return {
            "gid": int(subject[3:]),
            "source_object_id": f"SOURCE::{subject}",
            "content_digest": sha((kind, subject, "content")),
            "carrier": "SOURCE_BOUND_STATION_BODY",
        }
    if kind == "INDEPENDENT_REPLAY":
        root = sha((kind, subject, "state"))
        return {
            "gid": int(subject[3:]),
            "expected_state_root": root,
            "replayed_state_root": root,
            "result": "EXACT",
        }
    if kind == "DEFECT_CLOSURE":
        return {
            "defect_id": subject,
            "result": "CLOSED",
            "closure_root": sha((kind, subject, "closure")),
        }
    return {
        "candidate_id": subject,
        "decision": "PROMOTED",
        "state_root": ledger["frozen_base"]["state_root"],
        "gate_vector": {f"I{index:02d}": "PASS" for index in range(1, 11)},
        "successor_seed": "KC144.V2::POPULATE_MATH144",
    }


def packet(kind: str, subject: str, ledger: dict) -> M12EvidencePacket:
    body = payload(kind, subject, ledger)
    authority_scope = (
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
        evidence_root=sha((kind, subject, "evidence")),
        source_ref=f"test://{kind}/{subject}",
        replay_class=REPLAY_CLASS[kind],
        contradiction_class="NONE_FOUND",
        repair_layer=REPAIR_LAYER[kind],
        trust_revision_witness=f"TRUST::{kind}::{subject}",
        reentry_permit_id=f"REENTRY::{kind}::{subject}",
        payload=body,
        payload_digest=sha(body),
        authority=EvidenceAuthority(
            authority_id=f"AUTH::{kind}",
            scope=authority_scope,
            signature_status="VERIFIED",
            independent=True,
            test_only=True,
        ),
    )


def admit(ledger: dict, kind: str, subject: str) -> dict:
    report = admit_evidence(ledger, packet(kind, subject, ledger))
    if report["status"] != "ADMITTED":
        raise AssertionError(report["checks"])
    return report["ledger"]


class EvidenceContractTests(unittest.TestCase):
    def test_contract_freezes_all_five_gate_channels(self) -> None:
        contract = evidence_packet_contract()
        self.assertEqual(len(contract["evidence_kinds"]), 5)
        self.assertEqual(
            contract["targets"]["BRIDGE_CERTIFICATION"]["required_subjects"], 28
        )
        self.assertEqual(
            contract["targets"]["DOMAIN_POPULATION"]["required_subjects"], 58
        )
        self.assertEqual(
            contract["targets"]["INDEPENDENT_REPLAY"]["required_subjects"], 144
        )
        self.assertIn("bounded reentry permit", contract["immune_reentry_law"])

    def test_empty_ledger_is_exact_and_append_only(self) -> None:
        ledger = empty_repair_ledger(namespace="TEST")
        self.assertEqual(verify_repair_ledger(ledger)["verdict"], "PASS")
        self.assertEqual(ledger["head_digest"], "GENESIS")
        self.assertEqual(ledger["records"], [])

    def test_tampering_breaks_ledger_integrity(self) -> None:
        ledger = admit(
            empty_repair_ledger(namespace="TEST"),
            "DOMAIN_POPULATION",
            evidence_packet_contract()["targets"]["DOMAIN_POPULATION"][
                "subject_ids"
            ][0],
        )
        ledger["records"][0]["packet"]["source_ref"] = "tampered"
        self.assertEqual(verify_repair_ledger(ledger)["verdict"], "FAIL")


class EvidenceAdmissionTests(unittest.TestCase):
    def test_test_packet_never_enters_production(self) -> None:
        test_ledger = empty_repair_ledger(namespace="TEST")
        subject = evidence_packet_contract()["targets"]["DOMAIN_POPULATION"][
            "subject_ids"
        ][0]
        test_packet = packet("DOMAIN_POPULATION", subject, test_ledger)
        production = empty_repair_ledger(namespace="PRODUCTION")
        report = admit_evidence(production, test_packet)
        self.assertEqual(report["status"], "HOLD")
        self.assertFalse(report["checks"]["namespace_exact"])
        self.assertEqual(len(report["ledger"]["records"]), 0)

    def test_packet_and_subject_cannot_be_admitted_twice(self) -> None:
        ledger = empty_repair_ledger(namespace="TEST")
        subject = evidence_packet_contract()["targets"]["DOMAIN_POPULATION"][
            "subject_ids"
        ][0]
        first = admit_evidence(ledger, packet("DOMAIN_POPULATION", subject, ledger))
        second = admit_evidence(
            first["ledger"],
            packet("DOMAIN_POPULATION", subject, first["ledger"]),
        )
        self.assertEqual(first["status"], "ADMITTED")
        self.assertEqual(second["status"], "HOLD")
        self.assertFalse(second["checks"]["subject_unique"])

    def test_defect_closure_is_dependency_blocked(self) -> None:
        ledger = empty_repair_ledger(namespace="TEST")
        report = admit_evidence(
            ledger,
            packet("DEFECT_CLOSURE", "DEF-M12-OPEN-GATES", ledger),
        )
        self.assertEqual(report["status"], "HOLD")
        self.assertFalse(report["checks"]["dependency_ready"])


class RepairSchedulerTests(unittest.TestCase):
    def test_default_frontier_runs_three_evidence_waves_in_parallel(self) -> None:
        ledger = empty_repair_ledger()
        plan = repair_plan(ledger)
        self.assertEqual(
            plan["next_frontier"],
            [
                "R01_CERTIFY_BRIDGES",
                "R02_POPULATE_DOMAINS",
                "R03_REPLAY_STATIONS",
            ],
        )
        self.assertTrue(
            all(
                task["execution"] == "PARALLEL_WAVE"
                for task in plan["tasks"][:3]
            )
        )
        self.assertEqual(plan["tasks"][3]["status"], "BLOCKED")

    def test_full_test_overlay_unlocks_dag_but_not_production(self) -> None:
        contract = evidence_packet_contract()
        ledger = empty_repair_ledger(namespace="TEST")
        for kind in (
            "BRIDGE_CERTIFICATION",
            "DOMAIN_POPULATION",
            "INDEPENDENT_REPLAY",
        ):
            for subject in contract["targets"][kind]["subject_ids"]:
                ledger = admit(ledger, kind, subject)
        self.assertEqual(
            repair_plan(ledger)["next_frontier"],
            ["R04_CLOSE_BLOCKING_DEFECTS"],
        )
        ledger = admit(ledger, "DEFECT_CLOSURE", "DEF-M12-OPEN-GATES")
        self.assertEqual(
            repair_plan(ledger)["next_frontier"],
            ["R05_IC10_ADJUDICATE"],
        )
        ledger = admit(
            ledger,
            "IC10_PROMOTION",
            "KC144.SSN12.GLOBAL_STATE.V5",
        )
        self.assertEqual(repair_plan(ledger)["next_frontier"], [])
        summary = evidence_summary(ledger)
        self.assertTrue(summary["observed_state"]["ic10_promoted"])
        self.assertFalse(
            summary["production_effective_state"]["ic10_promoted"]
        )
        base = {
            "global_state_digest": ledger["frozen_base"]["state_root"],
        }
        state = compile_repair_state(ledger, base_global_state=base)
        self.assertEqual(state["ssn12"]["verdict"], "HOLD")
        self.assertFalse(state["production_certificate_issued"])
        self.assertNotEqual(
            state["next_seed"], "KC144.V2::POPULATE_MATH144"
        )

    def test_m12_can_recompute_all_nine_gates_without_false_defaults(self) -> None:
        solid = compile_session(
            default_session_spec(),
            certified_bridges=28,
            domain_population=144,
            independent_replays=144,
            blocking_defects=0,
            ic10_promoted=True,
        )["observatory"]["M12_SOLID_STATE"]
        self.assertEqual(solid["verdict"], "CERTIFIED")
        self.assertEqual(solid["passed"], 9)
        self.assertIsNotNone(solid["certificate"])


class V6ReleaseTests(unittest.TestCase):
    def test_default_release_is_complete_but_honestly_on_hold(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            release = compile_repair_framework(temporary)
            self.assertEqual(release["verdict"], "PASS")
            self.assertEqual(release["operational_status"], "HOLD")
            self.assertEqual(release["production_packets_admitted"], 0)
            self.assertFalse(release["production_certificate_issued"])
            self.assertEqual(len(release["open_gates"]), 5)
            self.assertEqual(
                release["next_seed"],
                "KC144.V6::EVIDENCE-INTAKE::PARALLEL-WAVE-01",
            )
            for filename in release["added_artifacts"] + [
                "m12_repair_release_v6.json"
            ]:
                self.assertIsInstance(
                    json.loads(
                        (Path(temporary) / filename).read_text(encoding="utf-8")
                    ),
                    dict,
                )


if __name__ == "__main__":
    unittest.main()
