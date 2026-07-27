from __future__ import annotations

import copy
import unittest

from kc144_crystal.audit import audit_crystal
from kc144_crystal.lattice import BAND_COUNTS, edge_census, generate_edges, generate_seats
from kc144_crystal.population import crystallize
from kc144_crystal.transform import (
    br_mirror,
    coactivation_sigma,
    f37_reflect,
    grid_d4_view,
    kc15_permute,
    kc27_transform,
    x16_algebra_translate,
    x16_schedule_rotate,
)


class WholeCrystalTests(unittest.TestCase):
    def test_disjoint_orbits_generate_exactly_144(self) -> None:
        seats = generate_seats()
        self.assertEqual(len(seats), 144)
        self.assertEqual({seat.gid for seat in seats}, set(range(1, 145)))
        self.assertEqual(
            {band: sum(seat.band == band for seat in seats) for band in BAND_COUNTS},
            BAND_COUNTS,
        )

    def test_population_is_complete_without_erasing_residuals(self) -> None:
        crystal = crystallize()
        self.assertEqual(len(crystal["seats"]), 144)
        self.assertTrue(all(row["architectural_label"] for row in crystal["seats"]))
        self.assertEqual(len(crystal["residuals"]), 12)
        self.assertEqual(crystal["evidence_census"]["UNMAPPED"], 7)
        self.assertEqual(crystal["evidence_census"]["ROUTED_ONLY"], 5)

    def test_generation_never_promotes(self) -> None:
        crystal = crystallize()
        self.assertTrue(all(row["promotion_effect"] == "NONE" for row in crystal["seats"]))

    def test_digest_detects_mutation(self) -> None:
        crystal = crystallize()
        changed = copy.deepcopy(crystal)
        changed["seats"][0]["architectural_label"] = "mutated"
        self.assertNotEqual(audit_crystal(changed)["verdict"], "PASS")

    def test_complete_audit_passes(self) -> None:
        report = audit_crystal()
        self.assertEqual(report["verdict"], "PASS", report["failures"])
        self.assertEqual(report["checks_passed"], report["checks_total"])


class TypedEdgeTests(unittest.TestCase):
    def test_two_x16_edge_classes_remain_distinct(self) -> None:
        census = edge_census()
        self.assertEqual(census["X16_SCHEDULE"], 32)
        self.assertEqual(census["X16_ALGEBRA"], 40)

    def test_global_denominators(self) -> None:
        self.assertEqual(len(generate_edges("schedule")), 215)
        self.assertEqual(len(generate_edges("algebra")), 223)
        self.assertEqual(len(generate_edges("both")), 255)

    def test_kc54_is_cube_edges(self) -> None:
        self.assertEqual(edge_census()["KC54_EDGE"], 54)
        self.assertEqual(2 * 27, 54)  # duplex cardinality, explicitly another type


class TransformationTests(unittest.TestCase):
    def test_grid_rotation_has_order_four(self) -> None:
        gid = 17
        for _ in range(4):
            gid = grid_d4_view(gid, "r90").target_gid
        self.assertEqual(gid, 17)

    def test_x16_schedule_action_is_bijective(self) -> None:
        image = {x16_schedule_rotate(gid, 1, 1).target_gid for gid in range(7, 23)}
        self.assertEqual(image, set(range(7, 23)))

    def test_x16_v4_translation_is_self_inverse(self) -> None:
        once = x16_algebra_translate(7, "10").target_gid
        twice = x16_algebra_translate(once, "10").target_gid
        self.assertEqual(twice, 7)

    def test_br_mirror_is_involution(self) -> None:
        self.assertEqual(br_mirror(br_mirror(24).target_gid).target_gid, 24)

    def test_f37_reflection_is_involution(self) -> None:
        self.assertEqual(f37_reflect(f37_reflect(44).target_gid).target_gid, 44)

    def test_sigma_is_bijection_but_not_truth_transport(self) -> None:
        receipts = [coactivation_sigma(gid) for gid in range(7, 44)]
        self.assertEqual({r.target_gid for r in receipts}, set(range(44, 81)))
        self.assertTrue(all(r.truth_effect == "NONE" for r in receipts))
        self.assertTrue(all(r.identity_effect == "COACTIVATION_CANDIDATE" for r in receipts))

    def test_kc15_s4_preserves_cardinality(self) -> None:
        seats = generate_seats()
        target = kc15_permute(95, (1, 0, 2, 3)).target_gid
        self.assertEqual(
            seats[94].coordinates["cardinality"],
            seats[target - 1].coordinates["cardinality"],
        )

    def test_kc27_signed_permutation_is_bijective(self) -> None:
        image = {
            kc27_transform(gid, (2, 0, 1), (-1, 1, -1)).target_gid
            for gid in range(106, 133)
        }
        self.assertEqual(image, set(range(106, 133)))
        self.assertEqual(kc27_transform(119, signs=(-1, -1, -1)).target_gid, 119)


if __name__ == "__main__":
    unittest.main()
