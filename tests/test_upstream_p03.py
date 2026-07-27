from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from memory_crystal.p03 import (
    AdapterCompiler,
    CarrierKind,
    ConversationAdapter,
    Coordinate,
    CrossCarrierMetro,
    GitRepositoryAdapter,
    GoogleDocAdapter,
    LocalFileAdapter,
    ProjectionStatus,
    ReturnClass,
    TypedEdge,
    kc144_gid_to_grid,
    kc144_grid_to_gid,
)
from memory_crystal.p03.model import verify_receipt_chain

FACES = frozenset({"address", "source", "transform", "return", "replay"})
COMMIT = "8" * 40


class CoordinateTests(unittest.TestCase):
    def test_all_144_grid_round_trips(self):
        for gid in range(1, 145):
            self.assertEqual(kc144_grid_to_gid(*kc144_gid_to_grid(gid)), gid)

    def test_out_of_range_grid_rejected(self):
        with self.assertRaises(ValueError):
            kc144_grid_to_gid(0, 1)

    def test_same_words_do_not_merge_carriers(self):
        a = Coordinate(CarrierKind.CONVERSATION, "x", "same", "r")
        b = Coordinate(CarrierKind.GOOGLE_DOC, "x", "same", "r")
        self.assertNotEqual(a.identity_key, b.identity_key)


class AdapterTests(unittest.TestCase):
    def test_conversation_without_turn_is_partial(self):
        _, status = ConversationAdapter().compile({"conversation_id": "c1"})
        self.assertEqual(status, ProjectionStatus.PARTIAL)

    def test_google_doc_url_and_revision_are_exact(self):
        coord, status = GoogleDocAdapter().compile(
            {
                "url": "https://docs.google.com/document/d/abc-123/edit",
                "revision_id": "rev-7",
            }
        )
        self.assertEqual((coord.object_id, status), ("abc-123", ProjectionStatus.EXACT))

    def test_git_branch_cannot_substitute_for_commit(self):
        with self.assertRaises(ValueError):
            GitRepositoryAdapter().compile(
                {
                    "owner": "demeet2k",
                    "repository": "Athena",
                    "commit_sha": "main",
                    "path": "README.md",
                }
            )

    def test_git_immutable_coordinate(self):
        coord, status = GitRepositoryAdapter().compile(
            {
                "owner": "demeet2k",
                "repository": "Athena",
                "commit_sha": COMMIT,
                "path": "README.md",
            }
        )
        self.assertEqual(status, ProjectionStatus.EXACT)
        self.assertEqual(coord.revision, COMMIT)

    def test_local_file_detects_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "a.txt")
            path.write_text("alpha", encoding="utf-8")
            adapter = LocalFileAdapter()
            coord, _ = adapter.compile({"path": path, "root": tmp})
            path.write_text("beta", encoding="utf-8")
            _, defect = adapter.return_coordinate(coord)
            self.assertTrue(defect.digest_changed)

    def test_compiler_dispatches_all_carriers(self):
        compiler = AdapterCompiler()
        coord, _ = compiler.compile(
            "google_doc", {"document_id": "doc", "revision_id": "r1"}
        )
        self.assertEqual(coord.carrier, CarrierKind.GOOGLE_DOC)


class MetroTests(unittest.TestCase):
    def setUp(self):
        self.metro = CrossCarrierMetro()
        self.conversation = Coordinate(
            CarrierKind.CONVERSATION, "chatgpt", "conversation-1", "turn-1"
        )
        self.doc = Coordinate(
            CarrierKind.GOOGLE_DOC, "docs.google.com", "document-1", "revision-1"
        )
        self.git = Coordinate(
            CarrierKind.GIT_REPOSITORY,
            "github.com/demeet2k/Athena",
            "00_SEED/kc144-p03.seed.json",
            COMMIT,
        )
        self.ck = self.metro.register(self.conversation)
        self.dk = self.metro.register(self.doc)
        self.gk = self.metro.register(self.git)
        self.metro.add_edge(
            TypedEdge(
                self.ck,
                self.dk,
                "grounds",
                "conversation-to-document",
                "secondary-to-primary",
                FACES,
                inverse_relation="contextualizes",
            ),
            add_inverse=True,
        )
        self.metro.add_edge(
            TypedEdge(
                self.dk,
                self.gk,
                "compresses-to",
                "document-to-git-seed",
                "primary-to-executable",
                FACES,
                inverse_relation="returns-to",
            ),
            add_inverse=True,
        )

    def test_exact_cross_carrier_route(self):
        receipt = self.metro.compile_route(
            self.ck,
            lambda c: c.carrier == CarrierKind.GIT_REPOSITORY,
            query_intent="find executable seed",
        )
        self.assertEqual(receipt.projection_status, ProjectionStatus.EXACT)
        self.assertEqual(len(receipt.candidate_paths[0]), 2)

    def test_route_is_relation_conditioned(self):
        receipt = self.metro.compile_route(
            self.ck,
            lambda c: c.carrier == CarrierKind.GIT_REPOSITORY,
            query_intent="only returns",
            allowed_relations=frozenset({"returns-to"}),
        )
        self.assertEqual(receipt.return_class, ReturnClass.UNRESOLVED)

    def test_five_face_failure_is_rejected(self):
        with self.assertRaises(ValueError):
            self.metro.add_edge(
                TypedEdge(
                    self.ck,
                    self.gk,
                    "shortcut",
                    "unsafe",
                    "derived",
                    frozenset({"address"}),
                )
            )

    def test_identity_collision_is_preserved(self):
        changed = replace(self.doc, digest="a" * 64)
        self.metro.register(changed)
        self.assertEqual(len(self.metro.collisions[self.dk]), 2)

    def test_set_valued_routes_are_not_scalarized(self):
        second_git = Coordinate(
            CarrierKind.GIT_REPOSITORY,
            "github.com/demeet2k/Athena",
            "01_LAWS/kc144-p03.laws.json",
            COMMIT,
        )
        second_key = self.metro.register(second_git)
        self.metro.add_edge(
            TypedEdge(
                self.dk,
                second_key,
                "compresses-to",
                "document-to-law-seed",
                "primary-to-executable",
                FACES,
            )
        )
        receipt = self.metro.compile_route(
            self.ck,
            lambda c: c.carrier == CarrierKind.GIT_REPOSITORY,
            query_intent="all executable projections",
        )
        self.assertEqual(receipt.projection_status, ProjectionStatus.SET_VALUED)
        self.assertEqual(len(receipt.candidate_paths), 2)

    def test_receipt_chain_detects_reordering(self):
        for intent in ("first", "second", "third"):
            self.metro.compile_route(
                self.ck,
                lambda c: c.carrier == CarrierKind.GIT_REPOSITORY,
                query_intent=intent,
            )
        receipts = list(self.metro.receipts)
        head = receipts[-1].digest
        self.assertEqual(
            verify_receipt_chain(receipts, expected_head=head), (True, [])
        )
        self.assertFalse(verify_receipt_chain(list(reversed(receipts)))[0])
        self.assertFalse(
            verify_receipt_chain(
                [receipts[0], receipts[2]], expected_head=head
            )[0]
        )
        self.assertFalse(
            verify_receipt_chain(receipts[:-1], expected_head=head)[0]
        )


if __name__ == "__main__":
    unittest.main()
