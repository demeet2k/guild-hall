from __future__ import annotations

import copy
import unittest

from kc144_crystal.p41_runtime import build_heldout_event
from kc144_crystal.p44_runtime import compile_p44_cycle
from kc144_crystal.p45_runtime import (
    P45_LANES,
    P45_LOOKUP_KEY,
    P45_NEXT_SEED,
    PUBLIC_P44_RESULT_ID,
    compile_p45_cycle,
    p45_contract,
    p45_parallel_lineage,
    verify_p45_cycle,
)
from tests.test_p44_edge_effect import executed_p43, forward_events


def frozen_p44() -> dict:
    return compile_p44_cycle(
        p43_cycle=executed_p43(),
        forward_events=forward_events(),
    )


def second_events(*, degrading: bool = False, drift: bool = False) -> list[dict]:
    rows = []
    for index in range(6):
        row = build_heldout_event(
            event_id=f"p45-second-{index}",
            outcome_class="TASK_OUTCOME" if index % 2 == 0 else "EMPIRICAL_RESULT",
            observed_at=f"2026-07-28T12:{index:02d}:00.000000Z",
            source_surface=f"POST_SURFACE_{index % 3}",
            route_id=f"POST_ROUTE_{index % 3}",
            detail=f"independent second-window observation {index}",
        )
        row["baseline_score"] = 0.7
        row["candidate_score"] = (
            0.4 if degrading else 0.95 if drift else 0.74 + (index % 3) * 0.01
        )
        rows.append(row)
    return rows


class P45EdgeRetentionTests(unittest.TestCase):
    def test_contract_is_whole_wave(self) -> None:
        contract = p45_contract()
        self.assertEqual(contract["lookup_key"], P45_LOOKUP_KEY)
        self.assertEqual(contract["next_seed"], P45_NEXT_SEED)
        self.assertEqual(len(contract["lanes"]), 10)
        self.assertEqual([row["lane"] for row in contract["lanes"]], list(P45_LANES))
        self.assertEqual(contract["route"][-1], "KC144.V1::GID144::M12")

    def test_default_is_honest_hold(self) -> None:
        cycle = compile_p45_cycle()
        self.assertEqual(cycle["public_parent_binding"]["result_id"], PUBLIC_P44_RESULT_ID)
        self.assertFalse(cycle["state"]["p44_edge_effect_admitted"])
        self.assertEqual(cycle["state"]["second_window_outcomes"], 0)
        self.assertEqual(cycle["retention_decision"]["verdict"], "HOLD")
        self.assertEqual(verify_p45_cycle(cycle)["verdict"], "PASS")

    def test_stable_second_window_retains_reversibly(self) -> None:
        cycle = compile_p45_cycle(
            p44_cycle=frozen_p44(),
            second_forward_events=second_events(),
        )
        self.assertEqual(cycle["second_forward_window"]["status"], "WINDOW_READY")
        self.assertEqual(cycle["route_stability"]["status"], "PASS_STABLE")
        self.assertEqual(cycle["surface_stability"]["status"], "PASS_STABLE")
        self.assertEqual(
            cycle["retention_decision"]["verdict"], "RETAIN_EDGE_REVERSIBLY"
        )
        self.assertEqual(verify_p45_cycle(cycle)["verdict"], "PASS")

    def test_degrading_complete_window_retracts_proposal(self) -> None:
        cycle = compile_p45_cycle(
            p44_cycle=frozen_p44(),
            second_forward_events=second_events(degrading=True),
        )
        self.assertEqual(
            cycle["retention_decision"]["verdict"], "RETRACT_EDGE_PROPOSAL"
        )
        self.assertFalse(
            cycle["retention_decision"]["canonical_graph_mutation_executed"]
        )

    def test_excess_effect_drift_retracts_proposal(self) -> None:
        cycle = compile_p45_cycle(
            p44_cycle=frozen_p44(),
            second_forward_events=second_events(drift=True),
        )
        self.assertEqual(cycle["route_stability"]["status"], "HOLD")
        self.assertEqual(
            cycle["retention_decision"]["verdict"], "RETRACT_EDGE_PROPOSAL"
        )

    def test_first_window_reuse_is_rejected(self) -> None:
        rows = second_events()
        rows[0]["event_id"] = "p44-forward-0"
        cycle = compile_p45_cycle(p44_cycle=frozen_p44(), second_forward_events=rows)
        self.assertIn(
            "FIRST_WINDOW_REUSE",
            {row["reason"] for row in cycle["second_forward_window"]["rejected"]},
        )

    def test_surface_diversity_is_required(self) -> None:
        rows = second_events()
        for row in rows:
            row["source_surface"] = "ONE_SURFACE"
        cycle = compile_p45_cycle(p44_cycle=frozen_p44(), second_forward_events=rows)
        self.assertEqual(cycle["second_forward_window"]["surface_count"], 1)
        self.assertEqual(cycle["retention_decision"]["verdict"], "HOLD")

    def test_tampering_fails_replay(self) -> None:
        cycle = compile_p45_cycle()
        tampered = copy.deepcopy(cycle)
        tampered["state"]["canonical_graph_mutations"] = 1
        self.assertEqual(verify_p45_cycle(tampered)["verdict"], "FAIL")

    def test_parallel_p45_is_not_merged(self) -> None:
        row = p45_parallel_lineage()
        self.assertEqual(
            row["relation"], "PARALLEL_LABEL_COLLISION_NOT_PARENT_NOT_MERGED"
        )
        self.assertFalse(row["private_locator_published"])
        self.assertFalse(row["merge_executed"])

    def test_decision_never_authorizes_weights_truth_or_ic10(self) -> None:
        cycle = compile_p45_cycle(
            p44_cycle=frozen_p44(),
            second_forward_events=second_events(),
        )
        decision = cycle["retention_decision"]
        self.assertFalse(decision["route_priority_delta_authorized"])
        self.assertFalse(decision["model_weight_mutation_authorized"])
        self.assertFalse(decision["ic10_authorization_present"])
        self.assertEqual(decision["truth_effect"], "NONE")
        self.assertEqual(cycle["state"]["production_authority"], "HOLD")


if __name__ == "__main__":
    unittest.main()
