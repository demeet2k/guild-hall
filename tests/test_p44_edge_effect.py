from __future__ import annotations

import copy
import unittest

from kc144_crystal.p41_runtime import build_heldout_event
from kc144_crystal.p43_runtime import compile_p43_cycle
from kc144_crystal.p44_runtime import (
    P44_LANES,
    P44_LOOKUP_KEY,
    P44_NEXT_SEED,
    PUBLIC_P43_RESULT_ID,
    compile_p44_cycle,
    p44_contract,
    p44_parallel_lineage,
    verify_p44_cycle,
)
from tests.test_p42_exact_edge_transaction import ready_inputs


def executed_p43() -> dict:
    registry, witness, events, authorization = ready_inputs()
    return compile_p43_cycle(
        signer_registry=registry,
        enumeration_witness=witness,
        heldout_events=events,
        edge_authorizations=[authorization],
        namespace="PRODUCTION",
        execution_time="2026-07-28T10:45:00.000000Z",
    )


def forward_events(*, degrading: bool = False) -> list[dict]:
    rows = []
    for index in range(5):
        row = build_heldout_event(
            event_id=f"p44-forward-{index}",
            outcome_class=(
                "TASK_OUTCOME" if index % 2 == 0 else "EMPIRICAL_RESULT"
            ),
            observed_at=f"2026-07-28T11:{index:02d}:00.000000Z",
            source_surface=f"POST_SURFACE_{index % 3}",
            route_id=f"POST_ROUTE_{index % 3}",
            detail=f"forward effect observation {index}",
        )
        row["baseline_score"] = 0.7
        row["candidate_score"] = 0.4 if degrading else 0.72 + index * 0.01
        rows.append(row)
    return rows


class P44EdgeEffectTests(unittest.TestCase):
    def test_contract_is_whole_wave(self) -> None:
        contract = p44_contract()
        self.assertEqual(contract["lookup_key"], P44_LOOKUP_KEY)
        self.assertEqual(contract["next_seed"], P44_NEXT_SEED)
        self.assertEqual(len(contract["lanes"]), 10)
        self.assertEqual([row["lane"] for row in contract["lanes"]], list(P44_LANES))
        self.assertEqual(contract["route"][-1], "KC144.V1::GID144::M12")

    def test_default_is_honest_hold(self) -> None:
        cycle = compile_p44_cycle()
        self.assertEqual(
            cycle["public_parent_binding"]["result_id"], PUBLIC_P43_RESULT_ID
        )
        self.assertFalse(cycle["state"]["parent_finality_ready"])
        self.assertEqual(cycle["forward_window"]["event_count"], 0)
        self.assertEqual(cycle["canonical_edge_effect"]["status"], "HOLD")
        self.assertEqual(cycle["state"]["truth_effect"], "NONE")
        self.assertEqual(verify_p44_cycle(cycle)["verdict"], "PASS")

    def test_ready_forward_window_freezes_effect(self) -> None:
        cycle = compile_p44_cycle(
            p43_cycle=executed_p43(),
            forward_events=forward_events(),
        )
        self.assertTrue(cycle["state"]["parent_finality_ready"])
        self.assertEqual(cycle["forward_window"]["status"], "WINDOW_READY")
        self.assertEqual(
            cycle["nondegradation_measurement"]["status"],
            "PASS_NONDEGRADING",
        )
        self.assertEqual(
            cycle["canonical_edge_effect"]["status"],
            "FROZEN_CANONICAL_EDGE_EFFECT",
        )
        self.assertEqual(verify_p44_cycle(cycle)["verdict"], "PASS")

    def test_degrading_window_holds(self) -> None:
        cycle = compile_p44_cycle(
            p43_cycle=executed_p43(),
            forward_events=forward_events(degrading=True),
        )
        self.assertEqual(
            cycle["nondegradation_measurement"]["status"], "HOLD"
        )
        self.assertEqual(cycle["canonical_edge_effect"]["status"], "HOLD")

    def test_route_diversity_is_required(self) -> None:
        rows = forward_events()
        for row in rows:
            row["route_id"] = "ONE_ROUTE"
        cycle = compile_p44_cycle(p43_cycle=executed_p43(), forward_events=rows)
        self.assertEqual(cycle["forward_window"]["route_count"], 1)
        self.assertEqual(cycle["forward_window"]["status"], "HOLD")

    def test_retroactive_event_is_rejected(self) -> None:
        rows = forward_events()
        rows[0]["observed_at"] = "2026-07-28T10:00:00.000000Z"
        cycle = compile_p44_cycle(p43_cycle=executed_p43(), forward_events=rows)
        self.assertIn(
            "NOT_STRICTLY_FORWARD",
            {row["reason"] for row in cycle["forward_window"]["rejected"]},
        )

    def test_continuation_is_rejected(self) -> None:
        rows = forward_events()
        rows[0]["continuation_only"] = True
        cycle = compile_p44_cycle(p43_cycle=executed_p43(), forward_events=rows)
        self.assertEqual(cycle["forward_window"]["continuation_events_admitted"], 0)
        self.assertIn(
            "CONTINUATION_ONLY",
            {row["reason"] for row in cycle["forward_window"]["rejected"]},
        )

    def test_tampering_fails_replay(self) -> None:
        cycle = compile_p44_cycle()
        tampered = copy.deepcopy(cycle)
        tampered["state"]["truth_effect"] = "PROMOTED"
        self.assertEqual(verify_p44_cycle(tampered)["verdict"], "FAIL")

    def test_parallel_p44_is_not_merged(self) -> None:
        row = p44_parallel_lineage()
        self.assertEqual(
            row["relation"], "PARALLEL_LABEL_COLLISION_NOT_PARENT_NOT_MERGED"
        )
        self.assertFalse(row["private_locator_published"])
        self.assertFalse(row["merge_executed"])

    def test_effect_never_authorizes_weights_or_truth(self) -> None:
        cycle = compile_p44_cycle(
            p43_cycle=executed_p43(),
            forward_events=forward_events(),
        )
        effect = cycle["canonical_edge_effect"]
        self.assertFalse(effect["route_priority_delta_authorized"])
        self.assertFalse(effect["model_weight_mutation_authorized"])
        self.assertEqual(effect["truth_effect"], "NONE")
        self.assertEqual(cycle["state"]["production_authority"], "HOLD")


if __name__ == "__main__":
    unittest.main()
