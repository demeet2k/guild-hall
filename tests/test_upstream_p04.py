from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from memory_crystal.p04 import (
    FederationRollout,
    GENERATED_SEED_FILES,
    REQUIRED_SEED_FILES,
    RepositorySnapshot,
    RolloutState,
    verify_rollout_receipts,
)

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "03_BODY" / "federation" / "kc144-p04.live-inventory.json"


class FederationInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rollout = FederationRollout.from_path(INVENTORY)

    def test_inventory_has_twelve_unique_live_repositories(self):
        self.assertEqual(len(self.rollout.snapshots), 12)
        self.assertEqual(len(self.rollout.repository_ids), 12)

    def test_control_plane_is_actual_private_athena_repository(self):
        snapshot = self.rollout._by_id["repo-athena"]
        self.assertEqual(snapshot.full_name, "demeet2k/Athena")
        self.assertEqual(snapshot.visibility, "private")
        self.assertEqual(
            snapshot.head_commit, "850a7af91b2b418adfb70547a9473a182abd9b6a"
        )

    def test_all_heads_are_immutable_commits(self):
        self.assertTrue(
            all(len(snapshot.head_commit) == 40 for snapshot in self.rollout.snapshots)
        )

    def test_live_scan_found_only_readme_of_six_contract_files(self):
        for snapshot in self.rollout.snapshots:
            presence = dict(snapshot.contract_presence)
            self.assertEqual(sum(presence.values()), 1)
            self.assertTrue(presence["README.md"])

    def test_no_internal_relation_target_is_unresolved(self):
        self.assertTrue(
            all(
                not self.rollout.unresolved_relations(snapshot)
                for snapshot in self.rollout.snapshots
            )
        )

    def test_a_branch_name_cannot_replace_a_commit(self):
        base = self.rollout.snapshots[0]
        with self.assertRaises(ValueError):
            replace(base, head_commit=base.default_branch)

    def test_duplicate_repository_identity_is_rejected(self):
        duplicate = self.rollout.snapshots + (self.rollout.snapshots[0],)
        with self.assertRaises(ValueError):
            FederationRollout(
                duplicate,
                control_plane_repo_id="repo-athena",
                source_ledger_id=self.rollout.source_ledger_id,
                source_ledger_digest=self.rollout.source_ledger_digest,
                observed_at=self.rollout.observed_at,
            )


class ContractCompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rollout = FederationRollout.from_path(INVENTORY)

    def test_contract_compiler_prepares_exactly_five_missing_files(self):
        for snapshot in self.rollout.snapshots:
            rendered = self.rollout.render_contract(snapshot)
            self.assertEqual(tuple(rendered), GENERATED_SEED_FILES)

    def test_existing_readme_is_never_overwritten(self):
        for snapshot in self.rollout.snapshots:
            self.assertNotIn("README.md", self.rollout.render_contract(snapshot))

    def test_seed_binds_repository_id_and_immutable_head(self):
        snapshot = self.rollout.snapshots[0]
        seed = json.loads(self.rollout.render_contract(snapshot)["SEED.json"])
        self.assertEqual(seed["repository"]["github_id"], snapshot.github_id)
        self.assertEqual(seed["repository"]["pinned_head"], snapshot.head_commit)
        self.assertEqual(seed["repository"]["snapshot_id"], snapshot.snapshot_id)

    def test_provenance_binds_h05_and_control_plane(self):
        snapshot = self.rollout.snapshots[1]
        provenance = json.loads(
            self.rollout.render_contract(snapshot)["PROVENANCE.json"]
        )
        self.assertEqual(
            provenance["source_ledger"]["ledger_id"],
            self.rollout.source_ledger_id,
        )
        self.assertEqual(
            provenance["control_plane"]["full_name"], "demeet2k/Athena"
        )

    def test_publication_state_is_honest(self):
        for snapshot in self.rollout.snapshots:
            state = json.loads(self.rollout.render_contract(snapshot)["STATE.json"])
            self.assertEqual(state["publication_state"], "prepared_not_published")
            self.assertEqual(state["promotion"]["repository_write"], "not_executed")

    def test_receipt_chain_covers_all_repositories(self):
        receipts = list(self.rollout.receipts())
        head = receipts[-1].digest
        self.assertEqual(len(receipts), 12)
        self.assertEqual(
            verify_rollout_receipts(receipts, expected_head=head), (True, [])
        )
        self.assertTrue(
            all(receipt.rollout_state == RolloutState.PREPARED for receipt in receipts)
        )

    def test_receipt_chain_detects_omission_and_reordering(self):
        receipts = list(self.rollout.receipts())
        self.assertFalse(verify_rollout_receipts(receipts[1:])[0])
        self.assertFalse(verify_rollout_receipts(list(reversed(receipts)))[0])

    def test_write_bundle_creates_sixty_contract_files_plus_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.rollout.write_bundle(Path(tmp))
            files = [path for path in Path(tmp).rglob("*") if path.is_file()]
            self.assertEqual(len(files), 61)
            self.assertEqual(result["repository_count"], 12)
            self.assertEqual(result["prepared_file_count"], 60)
            self.assertEqual(result["contract_complete_before_rollout"], 0)

    def test_contract_required_file_set_remains_six(self):
        self.assertEqual(len(REQUIRED_SEED_FILES), 6)


if __name__ == "__main__":
    unittest.main()
