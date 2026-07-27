from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kc144_crystal.holonomy import measure_holonomy, replay_ablation
from kc144_crystal.navigation import (
    DECLARED_BRIDGES,
    RETURN_ARM,
    adjacency,
    bridge_registry,
    components,
    navigation_relations,
    navigation_report,
    shortest_path,
)
from kc144_crystal.station import build_station_bodies, station_population_report
from kc144_crystal.systematic import compile_systematic_framework, frontier_ledger
from kc144_crystal.wave import WaveQuery, propagate


class StationPopulationTests(unittest.TestCase):
    def test_every_seat_has_a_holographic_body(self) -> None:
        bodies = build_station_bodies()
        self.assertEqual(len(bodies), 144)
        self.assertTrue(all(body["governing_question"] for body in bodies))
        self.assertTrue(all(set(body["four_pole"]) == {"11", "10", "00", "01"} for body in bodies))
        self.assertTrue(all(body["raw_cid"].startswith("sha256:") for body in bodies))

    def test_population_axes_are_not_collapsed(self) -> None:
        report = station_population_report()
        self.assertEqual(report["structural_population"], "144/144")
        self.assertEqual(report["source_domain_population"], "86/144")
        self.assertEqual(report["domain_open"], 58)

    def test_generated_body_never_promotes(self) -> None:
        self.assertTrue(all(body["promotion_effect"] == "NONE" for body in build_station_bodies()))


class NavigationGraphTests(unittest.TestCase):
    def test_native_bands_are_eight_islands(self) -> None:
        graph = adjacency(navigation_relations(include_bridges=False))
        self.assertEqual(
            sorted((len(component) for component in components(graph)), reverse=True),
            [37, 27, 21, 16, 15, 12, 10, 6],
        )

    def test_declared_bridges_connect_the_graph(self) -> None:
        report = navigation_report()
        self.assertEqual(len(DECLARED_BRIDGES), 28)
        self.assertEqual(report["components"], 1)
        self.assertEqual(report["reachable_from_H06"], 144)
        self.assertEqual(report["diameter"], 18)
        self.assertEqual(report["radius"], 9)
        self.assertEqual(report["centers"], [{"gid": 43, "station": "B21"}])

    def test_counts_reproduce_navigation_archive(self) -> None:
        report = navigation_report()
        self.assertEqual(report["distinct_intra_adjacency_edges"], 247)
        self.assertEqual(report["distinct_adjacency_edges"], 274)

    def test_return_arm_is_traversable(self) -> None:
        graph = adjacency(navigation_relations())
        self.assertTrue(all(right in graph[left] for left, right in zip(RETURN_ARM, RETURN_ARM[1:])))
        self.assertEqual(navigation_report()["return_arm"]["verdict"], "PASS")

    def test_shortest_route_is_bounded_and_explicit(self) -> None:
        graph = adjacency(navigation_relations())
        path = shortest_path(6, 53, graph)
        self.assertEqual(path[0], 6)
        self.assertEqual(path[-1], 53)
        self.assertLessEqual(len(path) - 1, 15)

    def test_bridges_are_not_silently_certified(self) -> None:
        self.assertTrue(all(bridge.standing == "DECLARED_UNCERTIFIED" for bridge in DECLARED_BRIDGES))
        registry = bridge_registry()
        self.assertEqual(registry["certified_transport_count"], 0)
        self.assertEqual(registry["count"], 28)


class HolonomyTests(unittest.TestCase):
    def test_five_routes_are_valid_and_nonredundant(self) -> None:
        report = measure_holonomy()
        self.assertEqual(len(report["routes"]), 5)
        self.assertTrue(report["all_paths_valid"])
        self.assertTrue(report["all_pairwise_holonomy_nonzero"])
        self.assertEqual(report["shared_carry_all_routes"], [])

    def test_multiplicity_resolution_is_typed(self) -> None:
        counts = replay_ablation()["resolution_counts"]
        self.assertEqual(
            counts,
            {
                "failing_gate_types": 1,
                "failure_modes": 2,
                "causal_replay_units": 87,
                "affected_instances": 144,
            },
        )

    def test_ablation_is_not_mislabeled_live_replay(self) -> None:
        report = replay_ablation()
        self.assertIn("NOT_INDEPENDENT_LIVE_REPLAY", report["standing"])
        self.assertEqual(report["actual_live_promotions"], 0)


class NavigationWaveTests(unittest.TestCase):
    def test_h06_wave_reaches_the_whole_crystal(self) -> None:
        report = propagate(WaveQuery("test.h06", (6,), route_budget=18))
        self.assertEqual(report["coverage"], "144/144")
        self.assertFalse(report["base_graph_mutated"])
        self.assertTrue(all(row["truth_effect"] == "NONE" for row in report["relation_weight_overlay"]))

    def test_route_budget_is_respected(self) -> None:
        report = propagate(WaveQuery("test.small", (6,), route_budget=2))
        self.assertTrue(all(node["nearest_distance"] <= 2 for node in report["nodes"]))
        self.assertLess(report["reached"], 144)

    def test_multi_source_wave_records_interference(self) -> None:
        report = propagate(WaveQuery("test.multi", (1, 144), route_budget=18))
        self.assertTrue(report["interference_nodes"])
        self.assertTrue(any(len(node["basin"]) > 1 for node in report["nodes"]))

    def test_path_signatures_are_stable(self) -> None:
        first = propagate(WaveQuery("test.stable", (6,), route_budget=4))
        second = propagate(WaveQuery("test.stable", (6,), route_budget=4))
        self.assertEqual(
            [node["path_signature"] for node in first["nodes"]],
            [node["path_signature"] for node in second["nodes"]],
        )


class SystematicCompilerTests(unittest.TestCase):
    def test_frontier_is_actionable_and_nonpromoting(self) -> None:
        frontier = frontier_ledger()
        self.assertEqual(frontier["promotion_effect"], "NONE")
        self.assertEqual(len(frontier["obligations"]), 6)
        self.assertEqual(frontier["next_seed"], "KC144.V3::NAV-PASS-002::ATTRACTOR_QUERY_OVERLAY")

    def test_compiler_emits_complete_registry_set(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            release = compile_systematic_framework(temporary)
            self.assertEqual(release["verdict"], "PASS")
            self.assertEqual(len(release["artifacts"]), 9)
            for filename in release["artifacts"] + ["systematic_release.json"]:
                document = json.loads((Path(temporary) / filename).read_text(encoding="utf-8"))
                self.assertIsInstance(document, dict)


if __name__ == "__main__":
    unittest.main()
