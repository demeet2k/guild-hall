from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from kc144_crystal.agent_receipts import (
    AgentReceiptError,
    LeaseGrant,
    canonical_bytes,
    compile_agent_run_receipts,
    content_address,
    issue_lease,
    retry_allowed,
    validate_task_result,
    verify_agent_run_receipts,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "registry/parallel-navigation/v1/snapshots/sha256/c8/"
    "c8e1a1a7c55a144b7bf20b49ff3fd01ca292a0cd34f134ce0a0abf0d9ac0bc1d.json"
)


def rehash_result(result: dict[str, object]) -> None:
    body = {key: value for key, value in result.items() if key != "result_digest"}
    result["result_digest"] = content_address("kc144.agent.result", body)


class AgentRunReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = json.loads(SOURCE.read_text(encoding="utf-8"))
        cls.bundle = compile_agent_run_receipts(cls.source)

    def test_reference_run_is_five_workers_plus_one_reducer(self) -> None:
        bundle = self.bundle
        self.assertEqual(len(bundle["plan"]["execution_waves"]), 2)
        self.assertEqual(len(bundle["plan"]["execution_waves"][0]), 5)
        self.assertEqual(len(bundle["plan"]["execution_waves"][1]), 1)
        self.assertEqual(len(bundle["receipts"]), 6)
        self.assertEqual(len(bundle["leases"]), 6)
        self.assertEqual(len(bundle["results"]), 6)
        reducer = bundle["plan"]["task_registry"][
            bundle["plan"]["execution_waves"][1][0]
        ]
        self.assertTrue(reducer["merge_authority"])
        self.assertTrue(
            all(
                not task["merge_authority"]
                for task in bundle["plan"]["task_registry"].values()
                if task["phase"] == "ROUTE_SIMULATION"
            )
        )

    def test_worker_capacities_one_through_five_are_byte_identical(self) -> None:
        products = [
            canonical_bytes(
                compile_agent_run_receipts(
                    self.source,
                    executor_workers=workers,
                )
            )
            for workers in range(1, 6)
        ]
        self.assertTrue(all(product == products[0] for product in products))

    def test_complete_verifier_passes_with_source_replay(self) -> None:
        report = verify_agent_run_receipts(
            self.bundle,
            source_crystal=self.source,
        )
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["accepted_receipt_count"], 6)
        self.assertEqual(report["independent_witness_count"], 0)

    def test_every_address_is_transitively_bound(self) -> None:
        bundle = copy.deepcopy(self.bundle)
        bundle["audit_events"][7]["decision"] = "MUTATED"
        report = verify_agent_run_receipts(bundle, source_crystal=self.source)
        self.assertEqual(report["verdict"], "FAIL")
        self.assertIn("E_EVENT_HASH", report["errors"])
        self.assertIn("E_DIGEST_MISMATCH", report["errors"])

    def test_event_deletion_and_reorder_fail_closed(self) -> None:
        deleted = copy.deepcopy(self.bundle)
        del deleted["audit_events"][4]
        report = verify_agent_run_receipts(deleted)
        self.assertIn("E_EVENT_SEQUENCE", report["errors"])
        self.assertIn("E_EVENT_PREVIOUS_HASH", report["errors"])

        reordered = copy.deepcopy(self.bundle)
        reordered["audit_events"][5:7] = reversed(
            reordered["audit_events"][5:7]
        )
        report = verify_agent_run_receipts(reordered)
        self.assertEqual(report["verdict"], "FAIL")
        self.assertTrue(
            {"E_EVENT_SEQUENCE", "E_EVENT_PREVIOUS_HASH"} & set(report["errors"])
        )

    def test_undeclared_write_and_stale_base_are_atomic_rejections(self) -> None:
        result = copy.deepcopy(self.bundle["results"][0])
        result["artifacts"][0]["semantic_write_key"] = "RESULT/OTHER"
        result["artifacts"][0]["base_digest"] = "sha256:" + ("1" * 64)
        rehash_result(result)
        errors = validate_task_result(
            self.bundle["plan"],
            self.bundle["leases"],
            result,
            run_id=self.bundle["manifest"]["run_id"],
            logical_epoch=0,
        )
        self.assertIn("E_UNDECLARED_WRITE", errors)
        self.assertIn("E_STALE_BASE", errors)

    def test_segment_aware_writes_do_not_accept_string_prefix_collisions(self) -> None:
        result = copy.deepcopy(self.bundle["results"][0])
        declared = self.bundle["plan"]["task_registry"][result["work_id"]][
            "write_set"
        ][0]
        result["artifacts"][0]["semantic_write_key"] = declared + "-EVIL"
        rehash_result(result)
        errors = validate_task_result(
            self.bundle["plan"],
            self.bundle["leases"],
            result,
            run_id=self.bundle["manifest"]["run_id"],
            logical_epoch=0,
        )
        self.assertIn("E_UNDECLARED_WRITE", errors)

    def test_expired_and_superseded_lease_results_are_not_live(self) -> None:
        old_lease = self.bundle["leases"][0]
        task = self.bundle["plan"]["task_registry"][old_lease["work_id"]]
        successor = issue_lease(
            LeaseGrant(
                run_id=old_lease["run_id"],
                plan_digest=old_lease["plan_digest"],
                work_id=old_lease["work_id"],
                task_id=old_lease["task_id"],
                attempt=2,
                logical_epoch=1,
                logical_slot=0,
                input_manifest_digest=old_lease["input_manifest_digest"],
                allowed_capabilities=tuple(task["capabilities"]),
                read_set=tuple(task["read_set"]),
                write_set=tuple(task["write_set"]),
                output_schema=task["output_schema"],
                expires_after_epoch=1,
                supersedes_lease_id=old_lease["lease_id"],
            )
        )
        errors = validate_task_result(
            self.bundle["plan"],
            [*self.bundle["leases"], successor],
            self.bundle["results"][0],
            run_id=self.bundle["manifest"]["run_id"],
            logical_epoch=2,
        )
        self.assertIn("E_LEASE_LATE", errors)
        self.assertIn("E_LEASE_SUPERSEDED", errors)

    def test_retry_policy_is_frozen_and_attempt_bounded(self) -> None:
        work_id = self.bundle["plan"]["tasks"][0]
        self.assertTrue(
            retry_allowed(
                self.bundle["plan"],
                work_id,
                attempt=1,
                error_code="E_TOOL_TRANSIENT",
            )
        )
        self.assertFalse(
            retry_allowed(
                self.bundle["plan"],
                work_id,
                attempt=1,
                error_code="E_DIGEST_MISMATCH",
            )
        )
        self.assertFalse(
            retry_allowed(
                self.bundle["plan"],
                work_id,
                attempt=2,
                error_code="E_TOOL_TRANSIENT",
            )
        )

    def test_truth_authority_and_transport_are_isolated(self) -> None:
        self.assertFalse(self.bundle["content_transport_certified"])
        self.assertFalse(self.bundle["governance_authority_granted"])
        self.assertEqual(self.bundle["production_truth_effect"], "NONE")
        self.assertEqual(
            self.bundle["manifest"]["independent_witness_count"],
            0,
        )
        forged = copy.deepcopy(self.bundle)
        forged["manifest"]["truth_effect"] = "PROMOTE"
        report = verify_agent_run_receipts(forged)
        self.assertIn("E_AUTHORITY_ESCALATION", report["errors"])

    def test_runtime_binding_rejects_a_stale_source(self) -> None:
        with self.assertRaises(AgentReceiptError):
            compile_agent_run_receipts(
                self.source,
                runtime_binding={
                    "runtime_commit": "1" * 40,
                    "runtime_tree": "2" * 40,
                    "source_snapshot_digest": "sha256:" + ("3" * 64),
                },
            )


if __name__ == "__main__":
    unittest.main()
