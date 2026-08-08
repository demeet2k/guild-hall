import unittest

from tools.observable_liminal_harness import (
    AXES,
    LiminalCoordinate,
    TransitRecord,
    replay,
    topology_length,
    validate_route,
)


def C(t, *, x=0, y=0, q=0, r=0, c=0, f=0, m=2455, n=0, h=1, o=1, z=0):
    return LiminalCoordinate(x, y, z, t, q, r, c, f, m, n, h, o)


class LiminalHarnessTests(unittest.TestCase):
    def test_coordinate_round_trip_and_lookup(self):
        c = C(7, x=10, y=4, q=2, r=1, f=2, n=1, h=2, o=2)
        self.assertEqual(LiminalCoordinate.from_mapping(c.as_mapping()), c)
        self.assertEqual(set(c.as_mapping()), set(AXES))
        self.assertEqual(c.lookup(), "@10.4.0.7|2.1.0|2.2455.1.2.2")

    def test_delta_reports_coded_axis_change(self):
        a = C(2, x=8, y=3, q=0, r=0, f=2, n=3, h=1, o=1)
        b = C(3, x=10, y=4, q=2, r=1, f=2, n=1, h=2, o=2)
        e = TransitRecord(a, b, "acquire quest", "quest blob sha", "GitHub.fetch_file")
        e.validate()
        self.assertIn("Xs", e.changed_axes())
        self.assertIn("Ts", e.changed_axes())
        self.assertIn("Ωs", e.changed_axes())
        self.assertEqual(len(e.delta()), 12)

    def test_missing_evidence_is_not_movement(self):
        with self.assertRaisesRegex(ValueError, "prediction is not movement"):
            TransitRecord(C(0), C(1), "imagine move", "", "self").validate()

    def test_noncontiguous_route_is_rejected(self):
        e1 = TransitRecord(C(0), C(1, x=1), "read", "A", "tool")
        e2 = TransitRecord(C(2, x=99), C(3, x=2), "jump", "B", "tool")
        with self.assertRaisesRegex(ValueError, "non-contiguous"):
            validate_route([e1, e2])

    def test_replay_preserves_exact_observed_path(self):
        c0 = C(0, x=1, y=0, f=1, o=1)
        c1 = C(1, x=2, y=1, f=1, n=1, h=2, o=2)
        c2 = C(2, x=8, y=3, f=2, n=3, h=1, o=2)
        records = [
            TransitRecord(c0, c1, "hydrate manifest", "blob:5225528d", "GitHub.fetch_file"),
            TransitRecord(c1, c2, "transfer to guild hall", "head:dfca982e", "GitHub.get_repo"),
        ]
        path = replay(records)
        self.assertEqual(len(path), 3)
        self.assertEqual(topology_length(records), 2)
        self.assertEqual(path[0], c0.lookup())
        self.assertEqual(path[-1], c2.lookup())


if __name__ == "__main__":
    unittest.main()
