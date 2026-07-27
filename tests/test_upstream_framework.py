from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kc144.model import gid_to_grid, grid_to_gid, kc27_coordinate
from kc144.registry import by_gid, load_atlas
from kc144.router import Edge, bounded_routes
from kc144.validate import digest, validate_atlas_document, validate_route


class AddressTests(unittest.TestCase):
    def test_all_grid_round_trips(self) -> None:
        for gid in range(1, 145):
            row, col = gid_to_grid(gid)
            self.assertEqual(grid_to_gid(row, col), gid)

    def test_block_boundaries(self) -> None:
        atlas = load_atlas(ROOT / "registry" / "atlas.json")
        expected = {
            1: ("H6", "H01"),
            7: ("X16", "X-11-SQ"),
            23: ("BR21", "B01"),
            44: ("F37", "F01"),
            81: ("IC10", "I01"),
            91: ("KC15", "K01"),
            106: ("KC27", "P00"),
            133: ("SSN12", "M01"),
            144: ("SSN12", "M12"),
        }
        for gid, pair in expected.items():
            seat = by_gid(atlas, gid)
            self.assertEqual((seat.block, seat.station), pair)

    def test_kc27_center(self) -> None:
        self.assertEqual(kc27_coordinate(13), (1, 1, 1))
        atlas = load_atlas(ROOT / "registry" / "atlas.json")
        self.assertEqual(by_gid(atlas, 119).station, "P13")


class RegistryTests(unittest.TestCase):
    def test_atlas_validates(self) -> None:
        doc = json.loads((ROOT / "registry" / "atlas.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_atlas_document(doc), [])
        self.assertEqual(len(doc["seats"]), 144)

    def test_digest_is_stable(self) -> None:
        value = {"é": [1, 2], "a": "x"}
        self.assertEqual(digest(value), digest({"a": "x", "e\u0301": [1, 2]}))

    def test_epoch_collision_is_explicit(self) -> None:
        doc = json.loads((ROOT / "registry" / "epochs.json").read_text(encoding="utf-8"))
        collision = next(item for item in doc["collisions"] if item["gid"] == 135)
        self.assertEqual(collision["active"], "M03")
        self.assertEqual(collision["legacy"], "I01")
        self.assertEqual(collision["resolution"], "EPOCH_REQUIRED")


class RouteTests(unittest.TestCase):
    def test_one_way_needs_irreversibility(self) -> None:
        route = {
            "route_id": "r1",
            "source": "a",
            "target": "b",
            "edge_type": "TRANSFORM",
            "source_carrier": "A",
            "target_carrier": "B",
            "corridor": {},
            "preserved_invariants": [],
            "defect": {},
            "return_class": "ONE_WAY",
            "witness": {},
        }
        self.assertIn("ONE_WAY route requires irreversibility_witness", validate_route(route))

    def test_bounded_routing(self) -> None:
        edges = [
            Edge("H06", "P13", "ACTIVATE", True, "EXACT"),
            Edge("P13", "M08", "REPAIR", True, "EXACT"),
            Edge("M08", "M12", "CERTIFY", True, "EXACT"),
            Edge("H06", "BAD", "GUESS", False, "OBSTRUCTED"),
        ]
        self.assertEqual(bounded_routes(edges, "H06", {"M12"}, 2), [])
        routes = bounded_routes(edges, "H06", {"M12"}, 3)
        self.assertEqual([[edge.target for edge in route] for route in routes], [["P13", "M08", "M12"]])


if __name__ == "__main__":
    unittest.main()

