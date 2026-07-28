from __future__ import annotations

import os
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path

from kc144_crystal.p31_adapter import (
    ExactP31Archive,
    P31AdapterError,
    P31_ARCHIVE_SHA256,
    P31_RESULT_ID,
    P31_RETURN_ADDRESS,
    navigate_exact_p31,
)


KNOWN_LOCAL_ARCHIVES = (
    Path(
        "/workspace/scratch/efa905fc4fe5/output/"
        "KC144_P31_LIVE_COGNITION_OS_V3_3.zip"
    ),
    Path(os.environ.get("KC144_P31_RUNTIME_PATH", "/nonexistent")),
)


def exact_archive_path() -> Path | None:
    for candidate in KNOWN_LOCAL_ARCHIVES:
        if candidate.is_file():
            return candidate
    return None


class P31AdapterTests(unittest.TestCase):
    def test_wrong_archive_digest_fails_before_metadata_is_trusted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fake.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(
                    "KC144_P31_LIVE_COGNITION_OS_V3_3/BUILD_RECEIPT.json",
                    '{"release_id":"KC144_P31_LIVE_COGNITION_OS_V3_3"}',
                )
            with self.assertRaisesRegex(
                P31AdapterError, "P31_ARCHIVE_SHA256_MISMATCH"
            ):
                ExactP31Archive(path)

    def test_container_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "unsafe.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("../escape.py", "raise SystemExit")
            candidate = object.__new__(ExactP31Archive)
            candidate.path = path
            with self.assertRaisesRegex(
                P31AdapterError, "P31_ARCHIVE_UNSAFE_PATH"
            ):
                candidate._validate_container()

    def test_container_rejects_symlink_member(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "symlink.zip"
            info = zipfile.ZipInfo("runtime/link")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(info, "target")
            candidate = object.__new__(ExactP31Archive)
            candidate.path = path
            with self.assertRaisesRegex(P31AdapterError, "P31_ARCHIVE_SYMLINK"):
                candidate._validate_container()

    @unittest.skipUnless(exact_archive_path(), "exact P31 archive not materialized")
    def test_exact_archive_identity_is_bound(self) -> None:
        archive = ExactP31Archive(exact_archive_path())
        status = archive.status()
        self.assertEqual(
            status["archive_sha256"], "sha256:" + P31_ARCHIVE_SHA256
        )
        self.assertEqual(status["result_id"], P31_RESULT_ID)
        self.assertEqual(status["truth_credit_assigned"], 0)
        self.assertEqual(status["real_user_outcomes_claimed"], 0)
        self.assertEqual(status["production_authority"], "HOLD")

    @unittest.skipUnless(exact_archive_path(), "exact P31 archive not materialized")
    def test_exact_navigation_replays_and_returns_without_path_leak(self) -> None:
        result = navigate_exact_p31(
            "Route P36 event intake through GID006 and return to M12.",
            archive_path=exact_archive_path(),
        )
        self.assertEqual(result["receipt"]["replay_status"], "REPLAY_STABLE")
        self.assertEqual(result["receipt"]["return_address"], P31_RETURN_ADDRESS)
        self.assertEqual(result["boundary"]["truth_credit_assigned"], 0)
        self.assertEqual(result["boundary"]["independent_witness_count"], 0)
        self.assertNotIn(str(exact_archive_path()), str(result))


if __name__ == "__main__":
    unittest.main()
