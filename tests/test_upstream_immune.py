from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from athena_immune.canonical import canonical_dumps, content_hash, merkle_root
from athena_immune.ic10 import IC10Context, IC10Evaluator
from athena_immune.kc54 import KC54Auditor
from athena_immune.ledger import AppendOnlyLedger, LedgerIntegrityError
from athena_immune.models import (
    AdmissionClass,
    GateResult,
    GateVerdict,
    RepairItem,
    RoleAssignments,
    TrustEvidence,
    TrustVector,
)
from athena_immune.permit import ReentryPermitCompiler
from athena_immune.qshrink import QShrinkCodec
from athena_immune.runtime import ImmuneRuntime
from athena_immune.scheduler import RepairScheduler
from athena_immune.trust import TrustRevisionEngine


def passing_context(**overrides: object) -> IC10Context:
    values: dict[str, object] = {
        "address_ok": True,
        "schema_hash_ok": True,
        "witness_refs": ["W1"],
        "warrant_typed": True,
        "contradiction_classified": True,
        "authority_ok": True,
        "consent_ok": True,
        "repair_layer_match": True,
        "replay_class": "EXACT",
        "trust_delta_justified": True,
        "residual_scope_declared": True,
        "blocking_residuals": [],
        "nonblocking_residuals": [],
        "successor_seed_ref": "S1",
        "reentry_target_declared": True,
    }
    values.update(overrides)
    return IC10Context(**values)  # type: ignore[arg-type]


def assignments(**overrides: str) -> RoleAssignments:
    values = {
        "proposer": "proposer",
        "skeptic": "skeptic",
        "integrator": "integrator",
        "immune_steward": "steward",
        "replay_auditor": "auditor",
        "meta_observer": "meta",
    }
    values.update(overrides)
    return RoleAssignments(**values)


def compile_permit(
    gates: list[GateResult],
    *,
    roles: RoleAssignments | None = None,
    omega: bool = True,
    sigma: bool = True,
    blocking: list[str] | None = None,
    unresolved: list[str] | None = None,
) -> dict[str, object]:
    return ReentryPermitCompiler().compile(
        permit_id="P1",
        cycle_id="C1",
        repaired_act_id="A1",
        contradiction_packet_refs=["C1.CON"],
        repair_receipt_refs=["R1"],
        trust_revision_refs=["T1"],
        replay_receipt_ref="RP1",
        witness_root=merkle_root(["W1"]),
        gate_results=gates,
        omega_gate=omega,
        sigma_gate=sigma,
        unresolved_residuals=unresolved or [],
        blocking_residuals=blocking or [],
        admitted_scope=["OBJECT.1"],
        excluded_scope=[],
        allowed_operations=["REENTER"],
        forbidden_operations=["OVERWRITE_HISTORY"],
        assignments=roles or assignments(),
        successor_seed_ref="S1",
    )


class CanonicalTests(unittest.TestCase):
    def test_canonical_key_order_is_stable(self) -> None:
        self.assertEqual(canonical_dumps({"b": 2, "a": 1}), canonical_dumps({"a": 1, "b": 2}))

    def test_content_hash_ignores_packet_hash(self) -> None:
        original = {"x": 1}
        sealed = {"x": 1, "packet_hash": "wrong-but-ignored"}
        self.assertEqual(content_hash(original), content_hash(sealed))

    def test_merkle_root_is_order_independent(self) -> None:
        self.assertEqual(merkle_root(["b", "a"]), merkle_root(["a", "b"]))


class LedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger = AppendOnlyLedger()

    def tearDown(self) -> None:
        self.ledger.close()

    def test_append_and_verify_chain(self) -> None:
        self.ledger.append("ACT", "A1", "C1", {"value": 1})
        self.ledger.append("REPAIR", "R1", "C1", {"value": 2})
        report = self.ledger.verify()
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(report["checked_entries"], 2)

    def test_duplicate_packet_id_is_rejected(self) -> None:
        self.ledger.append("ACT", "A1", "C1", {"value": 1})
        with self.assertRaises(LedgerIntegrityError):
            self.ledger.append("ACT", "A1", "C1", {"value": 2})

    def test_declared_bad_packet_hash_is_rejected(self) -> None:
        with self.assertRaises(LedgerIntegrityError):
            self.ledger.append("ACT", "A1", "C1", {"value": 1, "packet_hash": "bad"})

    def test_update_is_database_forbidden(self) -> None:
        self.ledger.append("ACT", "A1", "C1", {"value": 1})
        with self.assertRaises(sqlite3.DatabaseError):
            self.ledger.connection.execute(
                "UPDATE ledger_entries SET packet_type = 'MUTATED' WHERE packet_id = 'A1'"
            )

    def test_delete_is_database_forbidden(self) -> None:
        self.ledger.append("ACT", "A1", "C1", {"value": 1})
        with self.assertRaises(sqlite3.DatabaseError):
            self.ledger.connection.execute("DELETE FROM ledger_entries WHERE packet_id = 'A1'")

    def test_round_trip_payload(self) -> None:
        self.ledger.append("ACT", "A1", "C1", {"nested": {"z": [1, 2]}})
        loaded = self.ledger.get("A1")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["payload"]["nested"], {"z": [1, 2]})  # type: ignore[index]


class SchedulerTests(unittest.TestCase):
    def test_blocking_harm_repair_ranks_first(self) -> None:
        low = RepairItem("R1", "C1", "X", "syntax", "DEFINE", severity=0.2)
        high = RepairItem(
            "R2",
            "C1",
            "Y",
            "boundary",
            "RESTORE_CONSENT",
            blockers=["CONSENT"],
            harm_sensitive=True,
            severity=0.8,
        )
        ranked = RepairScheduler().rank([low, high])
        self.assertEqual(ranked[0].repair_id, "R2")

    def test_empty_repairs_preserve_unresolved(self) -> None:
        plan = RepairScheduler().schedule(
            {"contradiction_id": "C1", "candidate_repairs": [], "severity": 1.0}
        )
        self.assertTrue(plan["unresolved_preserved"])


class IC10Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.evaluator = IC10Evaluator()

    def test_all_ten_gates_pass(self) -> None:
        gates = self.evaluator.evaluate(passing_context())
        self.assertEqual(len(gates), 10)
        self.assertEqual(self.evaluator.overall(gates), GateVerdict.PASS)

    def test_missing_witness_fails(self) -> None:
        gates = self.evaluator.evaluate(passing_context(witness_refs=[]))
        gate = next(g for g in gates if g.gate_id.startswith("I03"))
        self.assertEqual(gate.verdict, GateVerdict.FAIL)
        self.assertIn("NO_WITNESS", gate.reason_codes)

    def test_blocking_residual_fails(self) -> None:
        gates = self.evaluator.evaluate(passing_context(blocking_residuals=["RES.BLOCK"]))
        gate = next(g for g in gates if g.gate_id.startswith("I09"))
        self.assertEqual(gate.verdict, GateVerdict.FAIL)

    def test_nonblocking_residual_is_near(self) -> None:
        gates = self.evaluator.evaluate(passing_context(nonblocking_residuals=["RES.OPEN"]))
        gate = next(g for g in gates if g.gate_id.startswith("I09"))
        self.assertEqual(gate.verdict, GateVerdict.NEAR)

    def test_law_equivalent_replay_is_near(self) -> None:
        gates = self.evaluator.evaluate(passing_context(replay_class="LAW_EQUIV"))
        gate = next(g for g in gates if g.gate_id.startswith("I07"))
        self.assertEqual(gate.verdict, GateVerdict.NEAR)


class TrustTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = TrustRevisionEngine()

    def revise(self, evidence: TrustEvidence, **role_overrides: str) -> dict[str, object]:
        return self.engine.revise(
            revision_id="T1",
            cycle_id="C1",
            contradiction_id="CON1",
            subject_edge="A→B",
            prior=TrustVector(),
            evidence=evidence,
            evidence_refs=["W1"],
            repair_receipt_refs=["R1"],
            replay_receipt_ref="RP1",
            residual_refs=[],
            proposer=role_overrides.get("proposer", "proposer"),
            reviewer="integrator",
            replay_auditor=role_overrides.get("replay_auditor", "auditor"),
        )

    def test_witnessed_dimension_changes(self) -> None:
        revision = self.revise(
            TrustEvidence(
                outcome={"epistemic": 1.0},
                witness_refs={"epistemic": ["W1"]},
                eta=0.5,
            )
        )
        self.assertEqual(revision["resulting_trust_vector"]["epistemic"], 0.75)  # type: ignore[index]
        self.assertIn("epistemic", revision["dimensions_changed"])

    def test_unwitnessed_dimension_is_zeroed(self) -> None:
        revision = self.revise(
            TrustEvidence(
                outcome={"epistemic": 1.0},
                witness_refs={"epistemic": []},
                eta=0.5,
            )
        )
        self.assertEqual(revision["resulting_trust_vector"]["epistemic"], 0.5)  # type: ignore[index]
        self.assertEqual(revision["accepted_delta"]["epistemic"], 0.0)  # type: ignore[index]

    def test_role_conflict_refuses_revision(self) -> None:
        revision = self.revise(
            TrustEvidence(
                outcome={"epistemic": 1.0},
                witness_refs={"epistemic": ["W1"]},
            ),
            proposer="same",
            replay_auditor="same",
        )
        self.assertEqual(revision["authorization_status"], "REFUSED")
        self.assertFalse(self.engine.justified(revision))


class PermitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.evaluator = IC10Evaluator()

    def test_full_permit(self) -> None:
        permit = compile_permit(self.evaluator.evaluate(passing_context()))
        self.assertEqual(permit["admission_class"], AdmissionClass.FULL.value)
        self.assertTrue(permit["reentry_allowed"])

    def test_limited_permit_preserves_residual(self) -> None:
        gates = self.evaluator.evaluate(passing_context(nonblocking_residuals=["OPEN"]))
        permit = compile_permit(gates, unresolved=["OPEN"])
        self.assertEqual(permit["admission_class"], AdmissionClass.LIMITED.value)
        self.assertTrue(permit["reentry_allowed"])

    def test_hold_defers(self) -> None:
        gates = self.evaluator.evaluate(passing_context(warrant_typed=False))
        permit = compile_permit(gates)
        self.assertEqual(permit["admission_class"], AdmissionClass.DEFERRED.value)
        self.assertFalse(permit["reentry_allowed"])

    def test_blocker_quarantines(self) -> None:
        gates = self.evaluator.evaluate(passing_context(blocking_residuals=["B1"]))
        permit = compile_permit(gates, blocking=["B1"])
        self.assertEqual(permit["admission_class"], AdmissionClass.QUARANTINED.value)
        self.assertIsNone(permit["successor_seed_ref"])

    def test_role_concentration_refuses(self) -> None:
        permit = compile_permit(
            self.evaluator.evaluate(passing_context()),
            roles=assignments(proposer="same", replay_auditor="same"),
        )
        self.assertEqual(permit["admission_class"], AdmissionClass.REFUSED.value)

    def test_omega_failure_refuses(self) -> None:
        permit = compile_permit(self.evaluator.evaluate(passing_context()), omega=False)
        self.assertEqual(permit["admission_class"], AdmissionClass.REFUSED.value)


class KC54Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.auditor = KC54Auditor()

    def audit(
        self,
        forward: list[dict[str, object]],
        reverse: list[dict[str, object]],
        unresolved: list[str] | None = None,
    ) -> dict[str, object]:
        return self.auditor.audit(
            receipt_id="K1",
            cycle_id="C1",
            forward_route=forward,
            reconstructed_inverse_route=reverse,
            preserved_invariants=["IDENTITY"],
            unresolved_frontier=unresolved,
        )

    def test_exact(self) -> None:
        event = [{"packet_type": "ACT", "value": 1}]
        self.assertEqual(self.audit(event, event)["classification"], "EXACT")

    def test_law_equivalent_ignores_transient_fields(self) -> None:
        forward = [{"packet_type": "ACT", "value": 1, "created_at": "a"}]
        reverse = [{"packet_type": "ACT", "value": 1, "created_at": "b"}]
        self.assertEqual(self.audit(forward, reverse)["classification"], "LAW_EQUIV")

    def test_residualized_mismatch(self) -> None:
        self.assertEqual(
            self.audit(
                [{"packet_type": "ACT", "value": 1}],
                [{"packet_type": "ACT", "value": 2}],
                ["OPEN"],
            )["classification"],
            "RESIDUALIZED",
        )

    def test_illegal_untyped_mismatch(self) -> None:
        self.assertEqual(
            self.audit(
                [{"packet_type": "ACT", "value": 1}],
                [{"packet_type": "ACT", "value": 2}],
            )["classification"],
            "ILLEGAL",
        )


class QShrinkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = QShrinkCodec()
        self.cycle = {
            "act": {"act_id": "A1"},
            "contradiction": {"witness_refs": ["W1"]},
            "repair_plan": {"plan_id": "P1"},
            "repair_receipts": [{"repair_id": "R1"}],
            "replay_receipt": {"classification": "EXACT"},
            "trust_revision": {"evidence_refs": ["W1"]},
            "reentry_permit": {"permit_id": "PERMIT1"},
        }

    def seed(self) -> dict[str, object]:
        return self.codec.build_seed(
            seed_id="S1",
            cycle_id="C1",
            full_cycle=self.cycle,
            gate_vector={f"I{i:02d}": "PASS" for i in range(1, 11)},
            residual_vector={"blocking": [], "nonblocking": []},
            source_addresses=["H05", "H06"],
            next_route="P03",
        )

    def test_exact_replay(self) -> None:
        seed = self.seed()
        certificate = self.codec.replay(
            certificate_id="RC1",
            seed=seed,
            full_cycle=self.cycle,
        )
        self.assertEqual(certificate["classification"], "EXACT")
        self.assertTrue(all(certificate["component_match"].values()))

    def test_tamper_is_illegal(self) -> None:
        seed = self.seed()
        self.cycle["act"]["act_id"] = "TAMPERED"
        certificate = self.codec.replay(
            certificate_id="RC1",
            seed=seed,
            full_cycle=self.cycle,
        )
        self.assertEqual(certificate["classification"], "ILLEGAL")
        self.assertFalse(certificate["component_match"]["act"])


class RuntimeTests(unittest.TestCase):
    def run_cycle(
        self,
        path: Path,
        *,
        cycle_id: str = "CYCLE.1",
        blocking: list[str] | None = None,
        repair_layer: str = "epistemic",
    ):
        runtime = ImmuneRuntime(path)
        result = runtime.run_cycle(
            cycle_id=cycle_id,
            act={"action": "PROMOTE", "actor": "athena"},
            contradiction={
                "proposition_a_ref": "CLAIM.1",
                "proposition_b_ref": "WITNESS.1",
                "proposition_a_warrant": "RHETORICAL",
                "proposition_b_warrant": "SOURCE",
                "contradiction_classes": ["WARRANT_INFLATION"],
                "witness_refs": ["W1"],
                "counterwitness_refs": ["W2"],
                "candidate_repairs": [
                    {
                        "residual_code": "LAN-EVIDENCE",
                        "damaged_layer": "epistemic",
                        "operation": "DOWNGRADE_EVIDENCE",
                        "blockers": ["INFLATION"],
                    }
                ],
            },
            repair_receipts=[
                {
                    "residual_code": "LAN-EVIDENCE",
                    "repair_layer": repair_layer,
                    "operation": "DOWNGRADE_EVIDENCE",
                    "status": "VERIFIED",
                }
            ],
            prior_trust=TrustVector(),
            trust_evidence=TrustEvidence(
                outcome={"epistemic": 0.8, "replay": 1.0},
                witness_refs={"epistemic": ["W1"], "replay": ["RP1"]},
            ),
            assignments=assignments(),
            omega_gate=True,
            sigma_gate=True,
            source_addresses=["H05", "H06"],
            next_route="P03",
            admitted_scope=["CLAIM.1"],
            blocking_residuals=blocking,
        )
        return runtime, result

    def test_full_vertical_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, result = self.run_cycle(Path(directory) / "ledger.db")
            self.assertEqual(result.reentry_permit["admission_class"], "FULL")
            self.assertIsNotNone(result.successor_seed)
            self.assertEqual(result.replay_certificate["classification"], "EXACT")  # type: ignore[index]
            self.assertEqual(result.kc54_receipt["classification"], "EXACT")
            self.assertEqual(runtime.ledger.verify()["verdict"], "PASS")
            runtime.ledger.close()

    def test_blocked_cycle_emits_no_successor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, result = self.run_cycle(
                Path(directory) / "ledger.db",
                blocking=["RES.BLOCKING"],
            )
            self.assertEqual(result.reentry_permit["admission_class"], "QUARANTINED")
            self.assertIsNone(result.successor_seed)
            packet_types = [entry["packet_type"] for entry in runtime.ledger.entries()]
            self.assertNotIn("SUCCESSOR_SEED", packet_types)
            runtime.ledger.close()

    def test_wrong_layer_repair_blocks_reentry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, result = self.run_cycle(
                Path(directory) / "ledger.db",
                repair_layer="syntax",
            )
            gate = next(g for g in result.gate_results if g.gate_id.startswith("I06"))
            self.assertEqual(gate.verdict, GateVerdict.FAIL)
            self.assertFalse(result.reentry_permit["reentry_allowed"])
            runtime.ledger.close()


class SchemaTests(unittest.TestCase):
    def test_all_json_schemas_parse(self) -> None:
        schema_dir = Path(__file__).parents[1] / "schemas"
        paths = sorted(schema_dir.glob("*.json"))
        self.assertEqual(len(paths), 3)
        for path in paths:
            with self.subTest(path=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(data["$schema"], "https://json-schema.org/draft/2020-12/schema")
                self.assertIn("packet_hash", data["properties"])


if __name__ == "__main__":
    unittest.main()

