from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from athena_git_brain.core import (
    PROMOTION_GATES,
    compile_route,
    load_registry,
    promotion_ready,
    validate_registry,
)


ROOT = Path(__file__).resolve().parents[1]


class RegistryTests(unittest.TestCase):
    def test_reference_registry_passes(self) -> None:
        report = validate_registry(ROOT)
        self.assertEqual(report["status"], "PASS", report["errors"])
        self.assertEqual(report["resource_versions"], 4)
        self.assertEqual(report["edges"], 6)

    def test_route_is_witnessed_and_returnable(self) -> None:
        receipt = compile_route(
            ROOT,
            "athena.doc.meta-memory",
            "athena.runtime.route-compiler",
        )
        self.assertEqual(receipt["verdict"], "FOUND")
        self.assertEqual(
            receipt["hops"],
            [
                "edge.meta-to-constitution",
                "edge.constitution-to-control",
                "edge.control-to-runtime",
            ],
        )
        self.assertEqual(
            receipt["return_plan"],
            [
                "edge.runtime-to-control",
                "edge.control-to-constitution",
                "edge.constitution-to-meta",
            ],
        )
        self.assertTrue(receipt["witnesses"])

    def test_unknown_identity_is_not_fuzzy_resolved(self) -> None:
        receipt = compile_route(ROOT, "KC144", "athena.runtime.route-compiler")
        self.assertEqual(receipt["verdict"], "INVALID_ADDRESS")

    def test_witnessless_active_edge_fails_validation(self) -> None:
        federation, edges = load_registry(ROOT)
        damaged = copy.deepcopy(edges)
        damaged[0]["witnesses"] = []
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "registry").mkdir()
            (root / "registry/federation.json").write_text(
                json.dumps(federation), encoding="utf-8"
            )
            (root / "registry/edges.jsonl").write_text(
                "\n".join(json.dumps(row) for row in damaged) + "\n",
                encoding="utf-8",
            )
            report = validate_registry(root)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("no witnesses" in error for error in report["errors"]))

    def test_promotion_is_conjunctive(self) -> None:
        gates = {
            gate: {"verdict": "PASS", "witnesses": [f"witness:{gate}"]}
            for gate in PROMOTION_GATES
        }
        self.assertTrue(promotion_ready(gates)["ready"])
        gates["I07_return"] = {"verdict": "HOLD", "witnesses": ["open:return"]}
        result = promotion_ready(gates)
        self.assertFalse(result["ready"])
        self.assertEqual(result["verdict"], "HOLD")


if __name__ == "__main__":
    unittest.main()

