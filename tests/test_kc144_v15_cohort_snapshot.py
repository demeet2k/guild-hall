from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "kc144_v15_cohort_snapshot",
    ROOT / "tools" / "kc144_v15_cohort_snapshot.py",
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def observation(
    application_digest: str,
    issue_number: int,
    *,
    candidate_id: str,
    key_digest: str,
    institution_root: str,
    exclusion: dict | None = None,
) -> dict:
    dimensions = {
        field: f"sha256:{issue_number:064x}"
        for field in MODULE.INDEPENDENCE_FIELDS
    }
    dimensions["institution_root"] = institution_root
    return {
        "application_digest": application_digest,
        "receipt_digest": f"sha256:{(issue_number + 100):064x}",
        "issue_number": issue_number,
        "source_path": (
            f"ledger/v15/sources/github-issues/{issue_number:012d}.json"
        ),
        "application_path": (
            f"ledger/v15/objects/sha256/{application_digest[7:9]}/"
            f"{application_digest[7:]}.application.json"
        ),
        "receipt_path": (
            f"ledger/v15/receipts/sha256/{issue_number:02x}/"
            f"{issue_number:064x}.receipt.json"
        ),
        "application_id": f"APPLICATION-{application_digest[-4:]}",
        "envelope_id": f"ENVELOPE-{application_digest[-4:]}",
        "nomination_id": f"NOMINATION-{application_digest[-4:]}",
        "candidate_id": candidate_id,
        "candidate_public_key_digest": key_digest,
        "role": "CUSTODIAN",
        "independence_dimensions": dimensions,
        "exclusion": exclusion,
    }


class CohortAggregationTests(unittest.TestCase):
    def test_repeated_sources_collapse_before_candidate_counting(self) -> None:
        digest = "sha256:" + "1" * 64
        first = observation(
            digest,
            21,
            candidate_id="CANDIDATE-1",
            key_digest="sha256:" + "a" * 64,
            institution_root="sha256:" + "b" * 64,
        )
        second = dict(first)
        second.update(
            {
                "issue_number": 22,
                "receipt_digest": "sha256:" + "2" * 64,
                "source_path": (
                    "ledger/v15/sources/github-issues/000000000022.json"
                ),
            }
        )
        rows = MODULE.group_applications([first, second])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source_count"], 2)
        self.assertEqual(rows[0]["source_issue_numbers"], [21, 22])

    def test_duplicate_status_is_symmetric(self) -> None:
        shared_key = "sha256:" + "a" * 64
        shared_institution = "sha256:" + "b" * 64
        rows = MODULE.group_applications(
            [
                observation(
                    "sha256:" + "1" * 64,
                    31,
                    candidate_id="SHARED-CANDIDATE",
                    key_digest=shared_key,
                    institution_root=shared_institution,
                ),
                observation(
                    "sha256:" + "2" * 64,
                    32,
                    candidate_id="SHARED-CANDIDATE",
                    key_digest=shared_key,
                    institution_root=shared_institution,
                ),
            ]
        )
        duplicates = MODULE.duplicate_sets(rows)
        MODULE.apply_global_states(rows, duplicates)
        for row in rows:
            self.assertFalse(row["global_unique"])
            self.assertIn("candidate_id", row["duplicate_fields"])
            self.assertIn(
                "candidate_public_key_digest", row["duplicate_fields"]
            )
            self.assertIn(
                "independence_dimensions.institution_root",
                row["duplicate_fields"],
            )

    def test_one_exclusion_excludes_entire_application_digest(self) -> None:
        digest = "sha256:" + "3" * 64
        first = observation(
            digest,
            41,
            candidate_id="SYNTHETIC",
            key_digest="sha256:" + "c" * 64,
            institution_root="sha256:" + "d" * 64,
        )
        second = dict(first)
        second.update(
            {
                "issue_number": 42,
                "receipt_digest": "sha256:" + "4" * 64,
                "source_path": (
                    "ledger/v15/sources/github-issues/000000000042.json"
                ),
                "exclusion": {
                    "classification": "SYNTHETIC_TEST_ARTIFACT"
                },
            }
        )
        rows = MODULE.group_applications([first, second])
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["excluded"])
        self.assertEqual(
            rows[0]["exclusion_classifications"],
            ["SYNTHETIC_TEST_ARTIFACT"],
        )


if __name__ == "__main__":
    unittest.main()
