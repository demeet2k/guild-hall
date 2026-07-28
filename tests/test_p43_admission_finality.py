from __future__ import annotations

import copy
import unittest

from kc144_crystal.p43_runtime import (
    P43_LANES,
    P43_LOOKUP_KEY,
    P43_NEXT_SEED,
    PUBLIC_P42_RESULT_ID,
    compile_p43_cycle,
    p43_contract,
    p43_parallel_lineage,
    verify_p43_cycle,
)
from tests.test_p42_exact_edge_transaction import ready_inputs


class P43AdmissionFinalityTests(unittest.TestCase):
    def test_contract_is_whole_wave(self) -> None:
        contract = p43_contract()
        self.assertEqual(contract["lookup_key"], P43_LOOKUP_KEY)
        self.assertEqual(contract["next_seed"], P43_NEXT_SEED)
        self.assertEqual(len(contract["lanes"]), 10)
        self.assertEqual([row["lane"] for row in contract["lanes"]], list(P43_LANES))
        self.assertEqual(contract["route"][-1], "KC144.V1::GID144::M12")

    def test_parent_is_exact_public_p42(self) -> None:
        cycle = compile_p43_cycle()
        self.assertEqual(
            cycle["public_parent_binding"]["result_id"], PUBLIC_P42_RESULT_ID
        )

    def test_default_is_honest_hold(self) -> None:
        cycle = compile_p43_cycle()
        self.assertEqual(cycle["admission_evaluation"]["status"], "HOLD")
        self.assertFalse(cycle["transaction_finality"]["exactly_once_final"])
        self.assertEqual(cycle["post_edge_watch"]["status"], "HELD_NOT_ARMED")
        self.assertFalse(cycle["state"]["production_mutated"])
        self.assertEqual(cycle["state"]["truth_effect"], "NONE")
        self.assertEqual(verify_p43_cycle(cycle)["verdict"], "PASS")

    def test_test_namespace_never_executes(self) -> None:
        registry, witness, events, authorization = ready_inputs()
        cycle = compile_p43_cycle(
            signer_registry=registry,
            enumeration_witness=witness,
            heldout_events=events,
            edge_authorizations=[authorization],
            namespace="TEST",
        )
        self.assertEqual(
            cycle["p42_transaction_cycle"]["edge_transaction"]["execution_status"],
            "SIMULATED_EXECUTION",
        )
        self.assertFalse(cycle["transaction_finality"]["exactly_once_final"])
        self.assertFalse(cycle["state"]["production_mutated"])

    def test_ready_production_executes_and_is_final(self) -> None:
        registry, witness, events, authorization = ready_inputs()
        cycle = compile_p43_cycle(
            signer_registry=registry,
            enumeration_witness=witness,
            heldout_events=events,
            edge_authorizations=[authorization],
            namespace="PRODUCTION",
            execution_time="2026-07-28T10:45:00.000000Z",
        )
        self.assertEqual(
            cycle["admission_evaluation"]["status"],
            "ADMITTED_FOR_EXACT_EXECUTION",
        )
        self.assertTrue(cycle["transaction_finality"]["exactly_once_final"])
        self.assertEqual(cycle["state"]["execution_count"], 1)
        self.assertEqual(cycle["post_edge_watch"]["status"], "ARMED")
        self.assertEqual(verify_p43_cycle(cycle)["verdict"], "PASS")

    def test_second_execution_is_idempotent(self) -> None:
        registry, witness, events, authorization = ready_inputs()
        first = compile_p43_cycle(
            signer_registry=registry,
            enumeration_witness=witness,
            heldout_events=events,
            edge_authorizations=[authorization],
            namespace="PRODUCTION",
            execution_time="2026-07-28T10:45:00.000000Z",
        )
        ledger = first["p42_transaction_cycle"]["edge_transaction"]["ledger_after"]
        second = compile_p43_cycle(
            signer_registry=registry,
            enumeration_witness=witness,
            heldout_events=events,
            edge_authorizations=[authorization],
            execution_ledger=ledger,
            namespace="PRODUCTION",
            execution_time="2026-07-28T11:00:00.000000Z",
        )
        transaction = second["p42_transaction_cycle"]["edge_transaction"]
        self.assertEqual(transaction["execution_status"], "ALREADY_EXECUTED_IDEMPOTENT")
        self.assertEqual(transaction["execution_count_after"], 1)
        self.assertFalse(transaction["ledger_mutated"])

    def test_missing_ic10_cannot_execute(self) -> None:
        registry, witness, events, _ = ready_inputs()
        cycle = compile_p43_cycle(
            signer_registry=registry,
            enumeration_witness=witness,
            heldout_events=events,
            namespace="PRODUCTION",
        )
        self.assertEqual(cycle["admission_evaluation"]["status"], "HOLD")
        self.assertEqual(cycle["state"]["execution_count"], 0)

    def test_tampering_fails_replay(self) -> None:
        cycle = compile_p43_cycle()
        tampered = copy.deepcopy(cycle)
        tampered["state"]["truth_effect"] = "PROMOTED"
        self.assertEqual(verify_p43_cycle(tampered)["verdict"], "FAIL")

    def test_parallel_p43_does_not_merge(self) -> None:
        parallel = p43_parallel_lineage()
        self.assertEqual(
            parallel["relation"],
            "PARALLEL_LABEL_COLLISION_NOT_PARENT_NOT_MERGED",
        )
        self.assertFalse(parallel["private_locator_published"])
        self.assertFalse(parallel["merge_executed"])

    def test_next_is_not_an_outcome(self) -> None:
        cycle = compile_p43_cycle()
        self.assertEqual(
            cycle["p42_transaction_cycle"]["heldout_cohort"][
                "continuation_events_admitted"
            ],
            0,
        )
        self.assertEqual(cycle["state"]["production_authority"], "HOLD")


if __name__ == "__main__":
    unittest.main()
