import copy
import unittest

from tools.observable_liminal_edge_receipt import (
    EdgeProvenance,
    EdgeReceiptError,
    ReplayableEdge,
    load_route_receipt,
    make_route_receipt,
)
from tools.observable_liminal_harness import LiminalCoordinate, TransitRecord


def C(t, x):
    return LiminalCoordinate(x, 1, 0, t, 5, 5, 2, 4, 2455, 6, 2, 3)


def E(t, x, locator, version):
    return ReplayableEdge(
        TransitRecord(C(t, x), C(t + 1, x + 1), f"move-{t}", f"evidence-{t}", f"witness-{t}"),
        EdgeProvenance(
            surface="GitHub",
            transport="fetch",
            native_locator=locator,
            native_version=version,
            return_locator=f"return:{locator}@{version}",
        ),
    )


class EdgeReceiptTests(unittest.TestCase):
    def test_exact_cold_round_trip(self):
        edges = [E(0, 1, "repo:file-a", "sha-a"), E(1, 2, "repo:file-b", "sha-b")]
        receipt = make_route_receipt(
            edges,
            registry_id="GH18-SOURCE-CONCEPT",
            registry_version="v1",
            carrier_id="ATHENA.LIMINAL.RUNTIME.v1",
        )
        rebuilt = load_route_receipt(
            receipt,
            expected_registry_id="GH18-SOURCE-CONCEPT",
            expected_registry_version="v1",
            expected_carrier_id="ATHENA.LIMINAL.RUNTIME.v1",
        )
        self.assertEqual(rebuilt, tuple(edges))

    def test_registry_identity_mismatch_fails_closed(self):
        receipt = make_route_receipt(
            [E(0, 7, "repo:A", "v1")],
            registry_id="registry-A",
            registry_version="1",
            carrier_id="carrier-A",
        )
        with self.assertRaisesRegex(EdgeReceiptError, "registry.id: mismatch"):
            load_route_receipt(receipt, expected_registry_id="registry-B")

    def test_registry_version_mismatch_fails_closed(self):
        receipt = make_route_receipt(
            [E(0, 7, "repo:A", "v1")],
            registry_id="registry-A",
            registry_version="1",
            carrier_id="carrier-A",
        )
        with self.assertRaisesRegex(EdgeReceiptError, "registry.version: mismatch"):
            load_route_receipt(receipt, expected_registry_version="2")

    def test_payload_tamper_is_detected(self):
        receipt = make_route_receipt(
            [E(0, 1, "repo:file", "sha")],
            registry_id="registry-A",
            registry_version="1",
            carrier_id="carrier-A",
        )
        tampered = copy.deepcopy(receipt)
        tampered["edges"][0]["evidence"] = "fabricated"
        with self.assertRaisesRegex(EdgeReceiptError, "payload_sha256: mismatch"):
            load_route_receipt(tampered)

    def test_missing_return_locator_is_rejected(self):
        bad = ReplayableEdge(
            TransitRecord(C(0, 1), C(1, 2), "move", "evidence", "witness"),
            EdgeProvenance("GitHub", "fetch", "repo:file", "sha", ""),
        )
        with self.assertRaisesRegex(EdgeReceiptError, "return_locator"):
            make_route_receipt(
                [bad], registry_id="registry-A", registry_version="1", carrier_id="carrier-A"
            )

    def test_noncontiguous_route_is_rejected(self):
        e1 = E(0, 1, "repo:a", "sha-a")
        e2 = E(2, 5, "repo:b", "sha-b")
        with self.assertRaisesRegex(ValueError, "non-contiguous"):
            make_route_receipt(
                [e1, e2], registry_id="registry-A", registry_version="1", carrier_id="carrier-A"
            )


if __name__ == "__main__":
    unittest.main()
