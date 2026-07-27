from __future__ import annotations

import unittest
from pathlib import Path

from athena_git_brain.core import validate_registry
from athena_immune.ic10 import IC10Context, IC10Evaluator
from kc144.registry import load_atlas
from memory_crystal.internal_nav import SourceRef, build_active_atlas


ROOT = Path(__file__).resolve().parents[1]


class RuntimeIntegrationTests(unittest.TestCase):
    def test_frozen_atlas_loads_through_original_runtime(self) -> None:
        seats = load_atlas(ROOT / "registry" / "atlas_frozen.json")
        self.assertEqual(len(seats), 144)

    def test_git_brain_reference_graph_passes(self) -> None:
        report = validate_registry(ROOT)
        self.assertEqual(report["status"], "PASS", report["errors"])

    def test_internal_navigation_generates_same_address_plane(self) -> None:
        source = SourceRef.from_dict(
            {
                "carrier": "local_file",
                "source_id": "complete-crystal",
                "revision": "2.0.0",
                "locator": "registry/crystal.json",
                "authority": "structural-coordinate-authority",
                "evidence_root": "kc144:complete-crystal:v2",
            }
        )
        atlas = build_active_atlas(source)
        self.assertEqual(len(atlas), 144)
        self.assertEqual({cell.grid for cell in atlas}, {f"R{r:02d}C{c:02d}" for r in range(1, 13) for c in range(1, 13)})

    def test_immune_gate_blocks_unwitnessed_rotation(self) -> None:
        context = IC10Context(
            address_ok=True,
            schema_hash_ok=True,
            witness_refs=[],
            warrant_typed=True,
            contradiction_classified=True,
            authority_ok=False,
            consent_ok=True,
            repair_layer_match=True,
            replay_class="STRUCTURAL",
            trust_delta_justified=False,
            residual_scope_declared=True,
            blocking_residuals=["ROTATION_IS_NOT_EVIDENCE"],
            nonblocking_residuals=[],
            successor_seed_ref=None,
            reentry_target_declared=False,
        )
        results = IC10Evaluator().evaluate(context)
        self.assertTrue(any(result.verdict.value != "PASS" for result in results))


if __name__ == "__main__":
    unittest.main()
