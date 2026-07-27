from __future__ import annotations

from itertools import combinations
from typing import Any

from .navigation import adjacency, navigation_relations

ROUTES: dict[str, dict[str, Any]] = {
    "A_X16_CONTRACT": {
        "path": [7, 11, 15, 19],
        "grammar": "contract",
        "carry": {
            "instance_count:144",
            "operator_count:1",
            "zero_split:86_constraint/58_missing",
            "return_classes:typed",
        },
        "result": "two failure modes with different return classes",
    },
    "B_BR21_ADVERSARIAL": {
        "path": [25, 28, 31, 34, 37, 40, 43],
        "grammar": "adversarial",
        "carry": {
            "gate_may_be_composite",
            "self_supplied_replay_packet",
            "collapse_not_invertible",
            "return_type:pseudoinverse",
            "falsifier:single_seat_replay",
            "loss_requires_carry",
            "reversibility_requires_carry",
        },
        "result": "one-defect language is a lossy projection unless carry is retained",
    },
    "C_KC27_CUBE": {
        "path": [110, 119, 128],
        "grammar": "localize-compress-lift",
        "carry": {
            "rank:1_in_gate_space",
            "compression:exact_with_two_element_carry",
            "lift:closed_verifier_property",
        },
        "result": "rank one in gate space and a configuration property after scale lift",
    },
    "D_KC15_SUPPORT": {
        "path": [91, 95, 101, 105],
        "grammar": "expressibility",
        "carry": {
            "expressible:count",
            "expressible:ratio",
            "expressible:invariant",
            "wellposedness:full_support",
            "answer:one_obligation_144_instances",
        },
        "result": "one return obligation with 144 instances; question needs full support",
    },
    "E_IC10_ADJUDICATION": {
        "path": list(range(81, 91)),
        "grammar": "adjudication",
        "carry": {
            "corridor:this_sweep",
            "defect:self_chosen_parameter",
            "analysis_replay:B4",
            "verdict:structural_hold_empirical",
        },
        "result": "analysis is reproducible while subjects remain independently unwitnessed",
    },
}


def measure_holonomy() -> dict[str, Any]:
    graph = adjacency(navigation_relations())
    route_reports: dict[str, Any] = {}
    for route_id, route in ROUTES.items():
        path = route["path"]
        route_reports[route_id] = {
            "path": path,
            "grammar": route["grammar"],
            "path_valid": all(
                right in graph[left] for left, right in zip(path, path[1:])
            ),
            "carry": sorted(route["carry"]),
            "result": route["result"],
            "adjudication_target": 90,
        }

    shared = set.intersection(*(set(route["carry"]) for route in ROUTES.values()))
    pairwise: list[dict[str, Any]] = []
    for left, right in combinations(ROUTES, 2):
        left_carry = set(ROUTES[left]["carry"])
        right_carry = set(ROUTES[right]["carry"])
        pairwise.append(
            {
                "left": left,
                "right": right,
                "omega": len(left_carry ^ right_carry),
                "shared": len(left_carry & right_carry),
            }
        )

    return {
        "schema": "KC144.RouteHolonomy.V3",
        "question": "I09 fails on all 144 seats: one defect or 144?",
        "destination": {
            "gid": 90,
            "resolution": "one gate; two modes; 87 causal replay units; 144 instances",
        },
        "routes": route_reports,
        "all_paths_valid": all(report["path_valid"] for report in route_reports.values()),
        "shared_carry_all_routes": sorted(shared),
        "all_pairwise_holonomy_nonzero": all(row["omega"] > 0 for row in pairwise),
        "pairwise": pairwise,
        "laws_earned": [
            "same destination does not imply same path",
            "shared value does not imply shared cause",
            "structure alone never promotes",
        ],
        "truth_effect": "NONE",
    }


def replay_ablation() -> dict[str, Any]:
    return {
        "schema": "KC144.ReplayAblation.V3",
        "standing": "STRUCTURAL_COUNTERFACTUAL_NOT_INDEPENDENT_LIVE_REPLAY",
        "scenarios": [
            {"scenario": "baseline", "gates_9_of_9": 0, "kernel_promotions": 0},
            {"scenario": "one_documented_seat", "gates_9_of_9": 1, "kernel_promotions": 1},
            {"scenario": "generator", "gates_9_of_9": 58, "kernel_promotions": 0},
            {"scenario": "everything", "gates_9_of_9": 144, "kernel_promotions": 86},
        ],
        "actual_live_promotions": 0,
        "resolution_counts": {
            "failing_gate_types": 1,
            "failure_modes": 2,
            "causal_replay_units": 87,
            "affected_instances": 144,
        },
        "promotion_ceiling_from_replay_alone": "86/144",
        "remaining_domain_population": 58,
    }
