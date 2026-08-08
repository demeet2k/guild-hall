import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

from tools.alchemy_capability_ir import compile_capability_ir

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "quests/generated/GH-ALCHEMY-AZOTH-001/capability_ir.schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA)

HELD_OUT_GOALS = [
    "Build a compiler that converts plain-English goals into typed work plans; it must preserve unknowns; use Git metadata and verify every leaf has an acceptance test.",
    "Design a biology analysis tool to classify microscopy images without exposing patient identifiers; verify accuracy on held-out data using de-identified image fixtures.",
    "Create a finance dashboard that compares budgets with actual spend under a 2 second latency target using CSV inputs; test reconciliation totals.",
    "Implement a robot route planner that maps obstacles and optimizes path length while preventing unsafe commands; validate collision-free routes with simulator fixtures.",
    "Generate a physics simulation that calculates orbital trajectories and tests energy conservation using initial-state JSON; results must remain reproducible.",
]


class CapabilityIRTests(unittest.TestCase):
    def assertSchemaValid(self, value):
        errors = sorted(VALIDATOR.iter_errors(value), key=lambda e: list(e.path))
        self.assertEqual(errors, [], "\n".join(e.message for e in errors))

    def test_five_held_out_domains_are_schema_valid(self):
        domains = set()
        for goal in HELD_OUT_GOALS:
            ir = compile_capability_ir(goal)
            self.assertSchemaValid(ir)
            self.assertEqual(ir["evidence"]["observations"], [])
            self.assertGreaterEqual(len(ir["capabilities"]), 1)
            domains.add(ir["target"]["domain_hint"])
        self.assertGreaterEqual(len(domains), 4)

    def test_compilation_is_deterministic(self):
        goal = HELD_OUT_GOALS[0]
        self.assertEqual(compile_capability_ir(goal), compile_capability_ir(goal))

    def test_mythic_absolutes_are_quarantined_not_observed(self):
        ir = compile_capability_ir("Build a perfect engine that instantly knows everything forever.")
        self.assertSchemaValid(ir)
        joined = " ".join(ir["unknowns"]).lower()
        for marker in ("perfect", "instantly", "everything", "forever"):
            self.assertIn(marker, joined)
        self.assertEqual(ir["evidence"], {"standing": "PARSED_NOT_OBSERVED", "observations": []})

    def test_simple_contradiction_is_surfaced(self):
        ir = compile_capability_ir("Build a logger; it must store logs; it must not store logs; test the contradiction handling.")
        self.assertSchemaValid(ir)
        self.assertTrue(ir["contradictions"])
        self.assertIn("store logs", ir["contradictions"][0])

    def test_unrecognized_goal_fails_to_unresolved_capability(self):
        ir = compile_capability_ir("Quantum banana transfiguration, immediately.")
        self.assertSchemaValid(ir)
        self.assertEqual(ir["capabilities"][0]["standing"], "FALLBACK_UNRESOLVED")
        self.assertTrue(any("not lexically recoverable" in item for item in ir["unknowns"]))

    def test_schema_forbids_minting_observations(self):
        ir = compile_capability_ir(HELD_OUT_GOALS[1])
        mutated = copy.deepcopy(ir)
        mutated["evidence"]["observations"] = ["model says it worked"]
        errors = list(VALIDATOR.iter_errors(mutated))
        self.assertTrue(errors)

    def test_schema_forbids_untyped_extra_fields(self):
        ir = compile_capability_ir(HELD_OUT_GOALS[2])
        mutated = copy.deepcopy(ir)
        mutated["magic_score"] = 9001
        errors = list(VALIDATOR.iter_errors(mutated))
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
