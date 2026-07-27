from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from memory_crystal.internal_nav import (
    ContextAtom,
    CoverageAuditor,
    FrameworkAddress,
    InternalNavigator,
    HealingPlanner,
    NavStore,
    OriginClass,
    PersonalContextAdapter,
    QueryBundle,
    SourceRef,
    SessionManager,
    TruthState,
)
from memory_crystal.internal_nav.model import LifecycleState, truth_meet


def atom(
    serial: str,
    text: str,
    *,
    gid: int = 6,
    station: str = "H06",
    domain: str = "QUERY_REPLAY",
    node: str = "QUERYBUNDLE",
    root: str | None = None,
    truth: TruthState = TruthState.NEAR,
    carrier: str = "internal_history",
    lifecycle: LifecycleState = LifecycleState.SOURCE_BOUND,
    tags: tuple[str, ...] = (),
) -> ContextAtom:
    return ContextAtom.build(
        source=SourceRef(
            carrier=carrier,
            source_id=f"source-{serial}",
            revision="v1",
            locator=f"thread:{serial}",
            authority="decision-and-process",
            evidence_root=root or f"root:{serial}",
        ),
        address=FrameworkAddress(gid, station, domain, node),
        exact_text=text,
        origin_class=(
            OriginClass.GOOGLE_DOC
            if carrier == "google_doc"
            else OriginClass.INTERNAL_HISTORY
        ),
        truth=truth,
        lifecycle=lifecycle,
        tags=tags,
        witnesses=(f"witness:{serial}",),
    )


class ModelTests(unittest.TestCase):
    def test_gid_grid_projection(self):
        self.assertEqual(FrameworkAddress(144, "M12", "SSN", "RETURN").grid, "R12C12")

    def test_truth_meet_is_weakest_corridor(self):
        self.assertEqual(truth_meet(TruthState.OK, TruthState.NEAR), TruthState.NEAR)
        self.assertEqual(truth_meet(TruthState.RESID, TruthState.AMBIG), TruthState.FAIL)

    def test_same_text_different_conversations_have_distinct_identity(self):
        left = atom("left", "same claim")
        right = atom("right", "same claim")
        self.assertNotEqual(left.atom_id, right.atom_id)

    def test_direct_promotion_is_rejected(self):
        with self.assertRaises(ValueError):
            atom(
                "bad-promotion",
                "unsupported promotion",
                lifecycle=LifecycleState.PROMOTED,
            )

    def test_ok_without_witness_is_rejected(self):
        source = SourceRef("runtime", "x", "v1", "runtime:x", "runtime", "root:x")
        with self.assertRaises(ValueError):
            ContextAtom.build(
                source=source,
                address=FrameworkAddress(1, "H01", "ROOT", "IDENTITY"),
                exact_text="claim",
                origin_class=OriginClass.RUNTIME,
                truth=TruthState.OK,
            )

    def test_personal_context_fallback_is_retrieval_scoped(self):
        adapter = PersonalContextAdapter()
        result = adapter.compile_hits(
            query_receipt_id="qr-1",
            hits=({"content": "prior navigation rule"},),
            address=FrameworkAddress(6, "H06", "QUERY_REPLAY", "RETRIEVED"),
        )
        self.assertEqual(result[0].source.carrier, "conversation_retrieval")
        self.assertIn("qr-1:result:0", result[0].source.source_id)
        self.assertEqual(result[0].truth, TruthState.RESID)

    def test_personal_context_native_turn_preserves_coordinates(self):
        adapter = PersonalContextAdapter()
        result = adapter.compile_hits(
            query_receipt_id="qr-2",
            hits=(
                {
                    "thread_id": "thread-9",
                    "turn_id": "turn-3",
                    "content": "exact prior turn",
                    "evidence_root": "root:thread-9",
                },
            ),
            address=FrameworkAddress(6, "H06", "QUERY_REPLAY", "RETRIEVED"),
        )
        self.assertEqual(result[0].source.carrier, "conversation")
        self.assertEqual(result[0].source.source_id, "thread-9")
        self.assertEqual(result[0].source.revision, "turn-3")


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.store = NavStore()

    def tearDown(self):
        self.store.close()

    def test_repeat_ingestion_is_idempotent(self):
        item = atom("idempotent", "claim")
        self.assertEqual(self.store.ingest_atom(item), "INSERTED")
        self.assertEqual(self.store.ingest_atom(item), "IDEMPOTENT")
        self.assertEqual(self.store.counts()["atoms"], 1)

    def test_changed_payload_at_same_identity_is_collision(self):
        item = atom("collision", "first")
        self.store.ingest_atom(item)
        changed = replace(
            item,
            exact_text="second",
            normalized_text="second",
            payload_digest="a" * 64,
        )
        self.assertEqual(self.store.ingest_atom(changed), "IDENTITY_COLLISION")
        self.assertEqual(self.store.counts()["identity_collisions"], 1)
        self.assertEqual(self.store.atom(item.atom_id).exact_text, "first")

    def test_untyped_edge_is_rejected(self):
        left = atom("edge-left", "left")
        right = atom("edge-right", "right", gid=29, station="B07")
        self.store.ingest_atom(left)
        self.store.ingest_atom(right)
        with self.assertRaises(ValueError):
            self.store.add_edge(
                source_atom=left.atom_id,
                target_atom=right.atom_id,
                relation="activates",
                inverse_relation="",
                invariants=("query-id",),
                witnesses=("route-witness",),
                return_address=left.address.key,
            )

    def test_receipt_chain_verifies(self):
        first = self.store.append_receipt("q1", {"selected": []})
        head = self.store.append_receipt("q2", {"selected": ["x"]})
        self.assertEqual(self.store.verify_receipts(expected_head=head), (True, []))
        self.assertNotEqual(first, head)


class NavigatorTests(unittest.TestCase):
    def setUp(self):
        self.store = NavStore()
        self.navigator = InternalNavigator(self.store)

    def tearDown(self):
        self.store.close()

    def test_budget_suspends_without_deleting(self):
        items = [atom(str(index), f"navigation claim {index}") for index in range(4)]
        self.navigator.ingest(items)
        query = QueryBundle.build(
            goal="navigate",
            terms=("navigation",),
            route_budget=2,
        )
        packet = self.navigator.query(query)
        self.assertEqual(len(packet.selected), 2)
        self.assertEqual(len(packet.suspended_branches), 2)
        self.assertEqual(self.store.counts()["atoms"], 4)
        replay = self.navigator.close_session(query, packet)
        self.assertEqual(len(replay.route_signature), 64)
        self.assertEqual(
            sum(state == "SUSPENDED_BUDGET" for _, state in replay.branch_ledger), 2
        )

    def test_same_evidence_root_is_not_independent_witness(self):
        text = "H06 returns replayable successor seed"
        internal = atom("internal", text, root="root:prompt-006")
        doc_view = atom(
            "doc",
            text,
            root="root:prompt-006",
            carrier="google_doc",
        )
        self.navigator.ingest((internal, doc_view))
        packet = self.navigator.query(
            QueryBundle.build(goal="H06", terms=("successor",), route_budget=10)
        )
        self.assertEqual(len(packet.clusters), 1)
        self.assertEqual(packet.clusters[0].independent_roots, ("root:prompt-006",))
        self.assertEqual(len(packet.clusters[0].atom_ids), 2)

    def test_explicit_conflict_prevents_near_or_ok_cluster(self):
        left = atom("conflict-left", "claim A")
        right = atom("conflict-right", "claim B")
        self.navigator.ingest((left, right))
        conflict_id = self.store.add_conflict(
            left.atom_id,
            right.atom_id,
            kind="CONTRADICTS",
            reopen_condition="new source witness",
        )
        packet = self.navigator.query(
            QueryBundle.build(goal="claims", terms=("claim",), route_budget=10)
        )
        self.assertIn(conflict_id, packet.conflicts)
        self.assertTrue(
            all(cluster.truth in {TruthState.AMBIG, TruthState.FAIL} for cluster in packet.clusters)
        )

    def test_exact_start_and_graph_route_are_recorded(self):
        start = atom("start", "query compiler", gid=6, station="H06")
        target = atom(
            "target",
            "parallel navigation",
            gid=30,
            station="B08",
            domain="BR21_NAVIGATE",
            node="NAVIGATE-HINGE",
        )
        self.navigator.ingest((start, target))
        self.store.add_edge(
            source_atom=start.atom_id,
            target_atom=target.atom_id,
            relation="activates",
            inverse_relation="returns",
            invariants=("query-id", "branch-ledger"),
            witnesses=("route-witness",),
            return_address=start.address.key,
        )
        packet = self.navigator.query(
            QueryBundle.build(
                goal="route",
                terms=("navigation",),
                start_coordinates=(start.address.key,),
                route_budget=10,
            )
        )
        hits = {hit.atom_id: hit for hit in packet.selected}
        self.assertEqual(hits[target.atom_id].path, (start.atom_id, target.atom_id))
        self.assertTrue(any(reason.startswith("EXACT-START") for reason in hits[start.atom_id].reasons))

    def test_ranking_does_not_promote_truth(self):
        highly_ranked = atom("rank", "navigation navigation", truth=TruthState.RESID)
        self.navigator.ingest((highly_ranked,))
        packet = self.navigator.query(
            QueryBundle.build(goal="navigation", terms=("navigation",))
        )
        self.assertEqual(packet.selected[0].truth, TruthState.RESID)
        self.assertEqual(packet.clusters[0].truth, TruthState.RESID)


class ReentryAndCoverageTests(unittest.TestCase):
    def setUp(self):
        self.store = NavStore()
        self.navigator = InternalNavigator(self.store)
        self.session = SessionManager(self.store)

    def tearDown(self):
        self.store.close()

    def close_one_session(self):
        item = atom("checkpoint", "navigation replay checkpoint")
        self.navigator.ingest((item,))
        query = QueryBundle.build(
            goal="checkpoint navigation",
            terms=("navigation",),
            start_coordinates=(item.address.key,),
        )
        packet = self.navigator.query(query)
        replay = self.navigator.close_session(query, packet)
        coverage = CoverageAuditor(self.store).audit()
        closed = self.session.close(query, packet, replay, coverage)
        return item, query, packet, closed

    def test_coverage_is_truthful_and_not_solid_state(self):
        self.navigator.ingest((atom("coverage", "one node"),))
        report = CoverageAuditor(self.store).audit()
        self.assertEqual(report.observed_nodes, 1)
        self.assertEqual(report.node_coverage, 1 / 144)
        self.assertIsNone(report.edge_coverage)
        self.assertFalse(report.solid_state_candidate)
        self.assertIn("FROZEN_EDGE_MANIFEST_UNBOUND", report.eligibility_defects)

    def test_healing_types_gaps_without_inventing_nodes(self):
        self.navigator.ingest((atom("gap", "one node"),))
        auditor = CoverageAuditor(self.store)
        before = auditor.audit()
        events = HealingPlanner(self.store).type_missing_gaps(before)
        after = auditor.audit()
        self.assertEqual(len(events), 143)
        self.assertEqual(after.observed_nodes, 1)
        self.assertEqual(after.node_coverage, before.node_coverage)
        self.assertEqual(after.source_or_typed_gap_coverage, 1.0)
        self.assertTrue(
            all(event.residual_gap.endswith("STILL_MISSING") for event in events)
        )

    def test_warm_reentry_validates_exact_checkpoint(self):
        _, query, _, closed = self.close_one_session()
        packet = self.session.warm_reentry(closed.checkpoint_id)
        self.assertEqual(packet.status.value, "VALID")
        self.assertEqual(packet.query.query_id, query.query_id)
        self.assertEqual(packet.next_operation, closed.next_seed)

    def test_warm_reentry_accepts_monotonic_growth_as_drift(self):
        _, _, _, closed = self.close_one_session()
        self.navigator.ingest(
            (
                atom(
                    "new-after-checkpoint",
                    "new node",
                    gid=29,
                    station="B07",
                    domain="BR21_NAVIGATE",
                    node="PLUS",
                ),
            )
        )
        packet = self.session.warm_reentry(closed.checkpoint_id)
        self.assertEqual(packet.status.value, "VALID_WITH_DRIFT")
        self.assertTrue(any("MONOTONIC_DRIFT" in defect for defect in packet.defects))

    def test_warm_reentry_detects_memory_decay(self):
        item, _, _, closed = self.close_one_session()
        with self.store.connection:
            self.store.connection.execute(
                "DELETE FROM atoms WHERE atom_id = ?", (item.atom_id,)
            )
        packet = self.session.warm_reentry(closed.checkpoint_id)
        self.assertEqual(packet.status.value, "STALE")
        self.assertTrue(any("MEMORY_DECAY" in defect for defect in packet.defects))

    def test_checkpoint_receipt_prefix_survives_later_receipts(self):
        _, _, _, closed = self.close_one_session()
        later_query = QueryBundle.build(goal="later", terms=("later",))
        self.store.append_receipt(later_query.query_id, {"later": True})
        packet = self.session.warm_reentry(closed.checkpoint_id)
        self.assertEqual(packet.status.value, "VALID")

    def test_identical_session_close_is_idempotent(self):
        item = atom("checkpoint-idempotent", "navigation replay checkpoint")
        self.navigator.ingest((item,))
        query = QueryBundle.build(
            goal="checkpoint navigation",
            terms=("navigation",),
            start_coordinates=(item.address.key,),
        )
        packet = self.navigator.query(query)
        replay = self.navigator.close_session(query, packet)
        coverage = CoverageAuditor(self.store).audit()
        first = self.session.close(query, packet, replay, coverage)
        second = self.session.close(query, packet, replay, coverage)
        self.assertEqual(first, second)
        self.assertEqual(self.store.counts()["checkpoints"], 1)

    def test_missing_checkpoint_totalizes_to_orphaned(self):
        packet = self.session.warm_reentry("missing")
        self.assertEqual(packet.status.value, "ORPHANED")
        self.assertEqual(packet.defects, ("CHECKPOINT_NOT_FOUND",))

    def test_rollback_is_append_only_plan(self):
        _, _, _, closed = self.close_one_session()
        packet = self.session.rollback_packet(closed.checkpoint_id)
        self.assertEqual(packet.mode, "APPEND_ONLY_COMPENSATING_ROLLBACK")


if __name__ == "__main__":
    unittest.main()
