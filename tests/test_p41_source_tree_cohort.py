from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from kc144_crystal.agent_receipts import canonical_bytes
from kc144_crystal.p41_runtime import (
    P41_COHORT_FREEZE,
    P41_LANES,
    P41_LOOKUP_KEY,
    PUBLIC_P40_RESULT_ID,
    SOURCE_SIBLING_RESULT_ID,
    _IC10_ENROLLMENT_DOMAIN,
    build_heldout_event,
    build_p41_ic10_enrollment,
    build_p41_ic10_return,
    compile_p41_cycle,
    compile_p41_release,
    empty_p41_ic10_registry,
    enroll_p41_ic10_signer,
    freeze_heldout_cohort,
    p41_contract,
    p41_parallel_lineage,
    p41_repository_forest,
    p41_source_manifest,
    verify_p41_cycle,
)


def _key(index: int = 0) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(bytes([index + 31]) * 32)


def ready_events() -> list[dict]:
    rows = []
    for index in range(5):
        rows.append(
            build_heldout_event(
                event_id=f"p41-heldout-{index}",
                outcome_class=(
                    "TASK_OUTCOME" if index % 2 == 0 else "EMPIRICAL_RESULT"
                ),
                observed_at=f"2026-07-28T08:{index:02d}:00.000000Z",
                source_surface=f"SURFACE_{index % 3}",
                route_id=f"ROUTE_{index % 3}",
                detail=f"sealed outcome detail {index}",
            )
        )
    return rows


def ready_registry() -> tuple[dict, Ed25519PrivateKey, dict]:
    key = _key()
    enrollment = build_p41_ic10_enrollment(
        signer_id="external-signer-1",
        organization_id="external-organization-1",
        control_root="sha256:" + "a" * 64,
        public_key=key.public_key(),
        valid_from="2026-07-28T07:30:00.000000Z",
        valid_until="2026-07-29T09:00:00.000000Z",
    )
    enrollment_body = {
        name: value
        for name, value in enrollment.items()
        if name != "enrollment_digest"
    }
    proof = key.sign(_IC10_ENROLLMENT_DOMAIN + canonical_bytes(enrollment_body))
    registry = enroll_p41_ic10_signer(
        empty_p41_ic10_registry(),
        enrollment,
        __import__("base64").urlsafe_b64encode(proof).decode().rstrip("="),
    )
    return registry, key, enrollment


def ready_cycle(*, namespace: str = "TEST") -> dict:
    events = ready_events()
    registry, key, enrollment = ready_registry()
    first = compile_p41_cycle(
        heldout_events=events,
        ic10_registry=registry,
        namespace=namespace,
    )
    ic10_return = build_p41_ic10_return(
        edge_candidate_root=first["edge_candidate"]["edge_candidate_root"],
        source_manifest_root=first["source_manifest"]["manifest_root"],
        repository_forest_root=first["repository_forest"]["forest_root"],
        heldout_cohort_root=first["heldout_cohort"]["cohort_root"],
        signer_id=enrollment["signer_id"],
        organization_id=enrollment["organization_id"],
        control_root=enrollment["control_root"],
        private_key=key,
        issued_at="2026-07-28T08:30:00.000000Z",
        expires_at="2026-07-28T09:30:00.000000Z",
        nonce="p41-independent-return-1",
    )
    return compile_p41_cycle(
        heldout_events=events,
        ic10_registry=registry,
        ic10_returns=[ic10_return],
        namespace=namespace,
    )


class P41SourceTreeCohortTests(unittest.TestCase):
    def test_all_p41_schemas_parse(self) -> None:
        root = Path(__file__).resolve().parents[1] / "schemas" / "kc144"
        schemas = sorted(root.glob("p41-*.schema.json"))
        self.assertEqual(len(schemas), 5)
        for path in schemas:
            schema = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(
                schema["$schema"],
                "https://json-schema.org/draft/2020-12/schema",
            )

    def test_contract_freezes_nine_lane_macrocycle(self) -> None:
        contract = p41_contract()
        self.assertEqual(contract["lookup_key"], P41_LOOKUP_KEY)
        self.assertEqual([row["lane"] for row in contract["lanes"]], list(P41_LANES))
        self.assertIn(
            "CONTINUATION_COMMAND_IS_NOT_HELDOUT_OUTCOME",
            contract["noncollapse"],
        )

    def test_source_manifest_closes_aggregate_gap_without_private_locators(self) -> None:
        manifest = p41_source_manifest()
        self.assertEqual(manifest["census"]["metadata_heads"], 29)
        self.assertEqual(manifest["census"]["prior_unhydrated"], 22)
        self.assertEqual(manifest["census"]["net_heads_closed"], 22)
        self.assertEqual(manifest["census"]["content_bodies"], 27)
        self.assertEqual(manifest["census"]["exact_empty_bodies"], 2)
        self.assertEqual(len(manifest["rows"]), 29)
        self.assertEqual(manifest["privacy"]["raw_document_ids_published"], 0)
        self.assertEqual(manifest["privacy"]["raw_body_bytes_published"], 0)
        for row in manifest["rows"]:
            self.assertEqual(
                set(row),
                {
                    "source_slot",
                    "locator_commitment",
                    "body_commitment",
                    "body_state",
                },
            )

    def test_public_repository_forest_binds_commit_and_tree(self) -> None:
        forest = p41_repository_forest()
        self.assertEqual(forest["repository_count"], 4)
        self.assertEqual(forest["path_count"], 99)
        self.assertTrue(forest["all_commits_pinned"])
        self.assertTrue(forest["all_trees_pinned"])
        self.assertFalse(forest["mutation_executed"])

    def test_parallel_p41_label_is_not_merged(self) -> None:
        lineage = p41_parallel_lineage()
        self.assertEqual(
            lineage["relation"],
            "PARALLEL_LABEL_COLLISION_NOT_PARENT_NOT_MERGED",
        )
        self.assertFalse(lineage["private_repository_locator_published"])
        self.assertFalse(lineage["merge_executed"])

    def test_default_cycle_is_replayable_honest_hold(self) -> None:
        left = compile_p41_cycle()
        right = compile_p41_cycle()
        self.assertEqual(left, right)
        self.assertEqual(left["state"]["public_parent_result_id"], PUBLIC_P40_RESULT_ID)
        self.assertEqual(
            left["state"]["source_sibling_result_id"], SOURCE_SIBLING_RESULT_ID
        )
        self.assertEqual(left["state"]["source_heads_rehydrated"], 29)
        self.assertEqual(left["state"]["net_source_heads_closed"], 22)
        self.assertEqual(left["state"]["heldout_outcomes"], 0)
        self.assertEqual(left["state"]["independent_ic10_returns"], 0)
        self.assertEqual(left["state"]["third_edge"], "HELD_NOT_EXECUTED")
        self.assertEqual(left["state"]["canonical_graph_mutations"], 0)
        self.assertEqual(left["state"]["global_release"], "HOLD")
        self.assertEqual(verify_p41_cycle(left)["verdict"], "PASS")

    def test_continuation_cannot_be_built_as_heldout_event(self) -> None:
        with self.assertRaisesRegex(ValueError, "task or empirical"):
            build_heldout_event(
                event_id="next",
                outcome_class="CONTINUATION",
                observed_at="2026-07-28T08:00:00.000000Z",
                source_surface="CONVERSATION",
                route_id="ROUTE_0",
                detail="next",
            )

    def test_pre_freeze_event_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "strictly after"):
            build_heldout_event(
                event_id="old",
                outcome_class="TASK_OUTCOME",
                observed_at=P41_COHORT_FREEZE,
                source_surface="SURFACE_0",
                route_id="ROUTE_0",
                detail="old event",
            )

    def test_five_diverse_sealed_events_freeze_ready(self) -> None:
        cohort = freeze_heldout_cohort(ready_events())
        self.assertEqual(cohort["status"], "COHORT_READY")
        self.assertEqual(cohort["event_count"], 5)
        self.assertEqual(cohort["labels_revealed"], 0)
        self.assertEqual(cohort["continuation_events_admitted"], 0)

    def test_ready_inputs_simulate_edge_without_production_mutation(self) -> None:
        cycle = ready_cycle(namespace="TEST")
        self.assertEqual(
            cycle["ic10_evaluation"]["status"],
            "INDEPENDENT_RETURN_VERIFIED",
        )
        self.assertEqual(cycle["third_edge_execution"]["eligibility"], "ELIGIBLE")
        self.assertEqual(
            cycle["third_edge_execution"]["execution_status"],
            "SIMULATED_EXECUTION",
        )
        self.assertEqual(cycle["third_edge_execution"]["execution_count"], 1)
        self.assertEqual(cycle["third_edge_execution"]["canonical_graph_mutations"], 0)
        self.assertFalse(cycle["third_edge_execution"]["production_mutated"])
        self.assertEqual(verify_p41_cycle(cycle)["verdict"], "PASS")

    def test_ready_production_inputs_execute_exactly_once(self) -> None:
        cycle = ready_cycle(namespace="PRODUCTION")
        self.assertEqual(cycle["third_edge_execution"]["execution_status"], "EXECUTED")
        self.assertEqual(cycle["third_edge_execution"]["execution_count"], 1)
        self.assertEqual(cycle["third_edge_execution"]["canonical_graph_mutations"], 1)
        self.assertTrue(cycle["third_edge_execution"]["production_mutated"])
        self.assertEqual(cycle["state"]["global_release"], "EXECUTED")
        self.assertEqual(verify_p41_cycle(cycle)["verdict"], "PASS")

    def test_missing_ic10_keeps_ready_cohort_held(self) -> None:
        events = ready_events()
        cycle = compile_p41_cycle(heldout_events=events)
        self.assertEqual(cycle["heldout_cohort"]["status"], "COHORT_READY")
        self.assertEqual(cycle["ic10_evaluation"]["status"], "HOLD")
        self.assertEqual(
            cycle["third_edge_execution"]["execution_status"],
            "HELD_NOT_EXECUTED",
        )

    def test_tampered_cycle_is_detected(self) -> None:
        cycle = compile_p41_cycle()
        tampered = copy.deepcopy(cycle)
        tampered["state"]["parallel_p41_merges"] = 1
        verification = verify_p41_cycle(tampered)
        self.assertEqual(verification["verdict"], "FAIL")
        self.assertIn("E_ENVELOPE_DIGEST", verification["errors"])
        self.assertIn("E_PROTECTED_STATE_ESCALATION", verification["errors"])

    def test_release_is_reproducible_and_nonleaking(self) -> None:
        with (
            tempfile.TemporaryDirectory() as first,
            tempfile.TemporaryDirectory() as second,
        ):
            kwargs = {
                "implementation_commit": "a" * 40,
                "implementation_tree": "b" * 40,
            }
            left = compile_p41_release(first, **kwargs)
            right = compile_p41_release(second, **kwargs)
            self.assertEqual(left, right)
            self.assertEqual(left["status"], "CANDIDATE_HOLD")
            self.assertEqual(left["source_heads_rehydrated"], 29)
            self.assertEqual(left["net_source_heads_closed"], 22)
            self.assertEqual(left["source_bodies_published"], 0)
            self.assertEqual(left["third_edge"], "HELD_NOT_EXECUTED")
            self.assertFalse(left["production_mutated"])
            self.assertEqual(
                (Path(first) / "SHA256SUMS").read_text(),
                (Path(second) / "SHA256SUMS").read_text(),
            )


if __name__ == "__main__":
    unittest.main()
