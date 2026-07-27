from __future__ import annotations

import json
import unittest

from kc144_crystal.parallel_routes import (
    AgentTask,
    DEFAULT_SIMULATIONS,
    ParallelRouteError,
    RouteSimulation,
    compile_parallel_route_crystal,
    compile_execution_waves,
    coordinate_delta,
    coordinate_vector,
    scheduler_plan,
    simulate_route,
)


class ParallelCoordinateTests(unittest.TestCase):
    def test_every_gid_has_a_unique_native_coordinate(self) -> None:
        vectors = [coordinate_vector(gid) for gid in range(1, 145)]
        self.assertEqual(
            len({row["canonical"]["grid"] for row in vectors}),
            144,
        )
        self.assertEqual(
            {row["canonical"]["gid"] for row in vectors},
            set(range(1, 145)),
        )

    def test_gid049_is_locked_across_observer_systems(self) -> None:
        vector = coordinate_vector(49)
        self.assertEqual(vector["canonical"]["grid"], "R05C01")
        self.assertEqual(vector["dls_4x4_in_12x12"]["tile"], [2, 1])
        self.assertEqual(vector["dls_4x4_in_12x12"]["local"], [1, 1])
        self.assertEqual(vector["grid16_injection"], {"row": 6, "column": 1})
        self.assertEqual(vector["angle360"]["degrees"], 120.0)
        self.assertEqual(vector["great_year25920"]["phase_year"], 8640)

    def test_delta_records_both_frames_without_truth_effect(self) -> None:
        delta = coordinate_delta(49, 51)
        self.assertTrue(delta["changed_lenses"])
        self.assertEqual(
            len(delta["removed_coordinate_states"]),
            len(delta["added_coordinate_states"]),
        )
        self.assertEqual(
            delta["information_effect"],
            "LOSSLESS_TRACE_PRESERVES_BOTH_ENDPOINTS",
        )
        self.assertEqual(delta["truth_effect"], "NONE")


class ParallelSchedulerTests(unittest.TestCase):
    def test_five_tasks_run_before_one_deterministic_reducer(self) -> None:
        plan = scheduler_plan()
        self.assertEqual(plan["maximum_parallel_width"], 5)
        self.assertEqual(len(plan["execution_waves"]), 2)
        self.assertEqual(len(plan["execution_waves"][0]), 5)
        self.assertEqual(len(plan["execution_waves"][1]), 1)
        self.assertTrue(
            all(
                task["merge_authority"] is False
                for task in plan["tasks"]
                if task["execution_mode"] == "PARALLEL_WORKER"
            )
        )

    def test_worker_count_does_not_change_canonical_result(self) -> None:
        serial = compile_parallel_route_crystal(executor_workers=1)
        parallel = compile_parallel_route_crystal(executor_workers=5)
        self.assertEqual(serial, parallel)

    def test_invalid_prefix_fails_closed(self) -> None:
        spec = RouteSimulation("INVALID", (2, 144), 90, "algebra")
        with self.assertRaises(ParallelRouteError):
            simulate_route(spec)

    def test_write_conflicts_are_serialized(self) -> None:
        tasks = (
            AgentTask(
                "A",
                "PARALLEL_WORKER",
                write_set=("RESULT/shared",),
            ),
            AgentTask(
                "B",
                "PARALLEL_WORKER",
                read_set=("RESULT/shared",),
                write_set=("RESULT/b",),
            ),
            AgentTask(
                "C",
                "PARALLEL_WORKER",
                write_set=("RESULT/c",),
            ),
        )
        waves = compile_execution_waves(tasks, worker_capacity=5)
        self.assertEqual(waves, [["A", "C"], ["B"]])

    def test_cycles_and_missing_dependencies_fail_closed(self) -> None:
        with self.assertRaises(ParallelRouteError):
            compile_execution_waves(
                (
                    AgentTask("A", "PARALLEL_WORKER", depends_on=("B",)),
                    AgentTask("B", "PARALLEL_WORKER", depends_on=("A",)),
                )
            )
        with self.assertRaises(ParallelRouteError):
            compile_execution_waves(
                (AgentTask("A", "PARALLEL_WORKER", depends_on=("MISSING",)),)
            )


class ParallelRouteCrystalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.crystal = compile_parallel_route_crystal()

    def test_all_five_routes_converge_without_collapsing_paths(self) -> None:
        self.assertEqual(
            [row["route_id"] for row in self.crystal["simulations"]],
            [row.route_id for row in DEFAULT_SIMULATIONS],
        )
        self.assertTrue(self.crystal["all_routes_navigation_valid"])
        self.assertTrue(self.crystal["all_pairwise_holonomy_nonzero"])
        self.assertTrue(
            all(
                row["canonical_path"]["nodes"][-1] == 90
                for row in self.crystal["simulations"]
            )
        )

    def test_every_bounded_path_language_is_compressed_and_auditable(self) -> None:
        for simulation in self.crystal["simulations"]:
            universe = simulation["bounded_path_universe"]
            shortest = simulation["shortest_language"]
            self.assertGreaterEqual(
                universe["target_path_count_total"],
                shortest["typed_path_count"],
            )
            self.assertIn(
                str(shortest["total_hops"]),
                universe["target_path_count_by_total_hops"],
            )
            json.dumps(universe, sort_keys=True)

    def test_navigation_never_promotes_transport_or_truth(self) -> None:
        self.assertFalse(self.crystal["content_transport_certified"])
        self.assertFalse(self.crystal["governance_authority_granted"])
        self.assertEqual(self.crystal["production_truth_effect"], "NONE")
        self.assertTrue(
            all(
                row["canonical_path"]["content_transport_certified"] is False
                for row in self.crystal["simulations"]
            )
        )

    def test_crystal_digest_is_replay_stable(self) -> None:
        replay = compile_parallel_route_crystal()
        self.assertEqual(
            self.crystal["crystal_digest"],
            replay["crystal_digest"],
        )


if __name__ == "__main__":
    unittest.main()
