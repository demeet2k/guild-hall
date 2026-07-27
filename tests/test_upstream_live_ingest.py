from __future__ import annotations

import unittest

from memory_crystal.internal_nav import (
    AtlasCoverageAuditor,
    CoverageAuditor,
    InternalNavigator,
    LiveContextCompiler,
    LiveObservation,
    NavStore,
    ObservationKind,
    QueryBundle,
    SessionManager,
    SourceRef,
    build_active_atlas,
)


ATLAS_SOURCE = {
    "carrier": "google_doc",
    "source_id": "atlas-doc",
    "revision": "revision-1",
    "locator": "https://docs.google.com/document/d/atlas-doc/edit",
    "authority": "coordinate-authority",
    "evidence_root": "root:atlas-doc:revision-1",
}


def bundle(
    *,
    kind: str = "NATIVE_EXCERPT",
    basis: str = "EXPLICIT_COORDINATE",
    station: str = "KC15-01",
    exact_text: str = "GID091 | R08C07 | KC15-01 | {11}",
):
    return {
        "schema": "KC144.LiveContextBundle.V1",
        "atlas_source": ATLAS_SOURCE,
        "observations": [
            {
                "alias": "kc15-row",
                "carrier": "google_doc",
                "source_id": "prompt-doc",
                "revision": "revision-2",
                "locator": "https://docs.google.com/document/d/prompt-doc/edit",
                "fragment": "kc15-census-row-091",
                "authority": "primary-documentary",
                "evidence_root": "root:prompt-doc:revision-2",
                "kind": kind,
                "content": "GID091 | R08C07 | KC15-01 | {11}",
            }
        ],
        "claims": [
            {
                "observation": "kc15-row",
                "basis": basis,
                "address": {
                    "gid": 91,
                    "station": station,
                    "domain": "KC15",
                    "node": "SUPPORT-11",
                },
                "exact_text": exact_text,
                "origin_class": "google_doc",
                "truth": "RESID",
                "witnesses": ["Drive revision revision-2"],
            }
        ],
    }


class AtlasRegistryTests(unittest.TestCase):
    def setUp(self):
        self.store = NavStore()

    def tearDown(self):
        self.store.close()

    def test_active_atlas_is_bijective_and_structural_only(self):
        source = SourceRef.from_dict(ATLAS_SOURCE)
        cells = build_active_atlas(source)
        self.assertEqual(len(cells), 144)
        self.assertEqual(len({cell.gid for cell in cells}), 144)
        self.assertEqual(len({cell.grid for cell in cells}), 144)
        for cell in cells:
            self.store.register_atlas_cell(cell.to_dict())
        report = AtlasCoverageAuditor(self.store).audit()
        self.assertEqual(report.structural_coverage, 1.0)
        self.assertEqual(report.content_coverage, 0.0)
        self.assertEqual(report.source_bound_coverage, 0.0)

    def test_atlas_reingestion_is_idempotent(self):
        compiler = LiveContextCompiler(self.store)
        first = compiler.ingest_bundle(bundle())
        second = compiler.ingest_bundle(bundle())
        self.assertEqual(dict(first.atlas), {"INSERTED": 144})
        self.assertEqual(dict(second.atlas), {"IDEMPOTENT": 144})
        self.assertEqual(self.store.counts()["atlas_cells"], 144)
        self.assertEqual(self.store.counts()["live_observations"], 1)
        self.assertEqual(self.store.counts()["admission_claims"], 1)


class LiveAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.store = NavStore()
        self.compiler = LiveContextCompiler(self.store)

    def tearDown(self):
        self.store.close()

    def test_explicit_native_excerpt_populates_source_bound_content(self):
        result = self.compiler.ingest_bundle(bundle())
        self.assertEqual(result.claims[0].status.value, "ADMITTED")
        report = AtlasCoverageAuditor(self.store).audit()
        self.assertEqual(report.content_gids, (91,))
        self.assertEqual(report.source_bound_gids, (91,))
        self.assertEqual(report.retrieval_only_gids, ())

    def test_search_hit_is_visible_as_retrieval_only(self):
        self.compiler.ingest_bundle(bundle(kind="SEARCH_HIT"))
        report = AtlasCoverageAuditor(self.store).audit()
        self.assertEqual(report.content_gids, (91,))
        self.assertEqual(report.source_bound_gids, ())
        self.assertEqual(report.retrieval_only_gids, (91,))
        self.assertIn("RETRIEVAL_ONLY_CONTENT_PRESENT", report.defects)

    def test_derived_mapping_is_quarantined_without_atom(self):
        result = self.compiler.ingest_bundle(bundle(basis="DERIVED_COORDINATE"))
        self.assertEqual(result.claims[0].status.value, "QUARANTINED")
        self.assertEqual(self.store.counts()["atoms"], 0)

    def test_excerpt_must_be_exact_substring(self):
        result = self.compiler.ingest_bundle(bundle(exact_text="invented body"))
        self.assertEqual(result.claims[0].status.value, "QUARANTINED")
        self.assertEqual(
            result.claims[0].reason,
            "EXCERPT_NOT_EXACT_SUBSTRING_OF_OBSERVATION",
        )

    def test_explicit_basis_requires_gid_token(self):
        value = bundle(exact_text="KC15-01")
        value["observations"][0]["content"] = "KC15-01"
        result = self.compiler.ingest_bundle(value)
        self.assertEqual(result.claims[0].status.value, "QUARANTINED")
        self.assertEqual(
            result.claims[0].reason,
            "EXPLICIT_GID_TOKEN_ABSENT_FROM_EXCERPT",
        )

    def test_station_mismatch_is_quarantined(self):
        result = self.compiler.ingest_bundle(bundle(station="KC15-15"))
        self.assertEqual(result.claims[0].status.value, "QUARANTINED")
        self.assertIn("STATION_MISMATCH", result.claims[0].reason)

    def test_legacy_station_alias_is_accepted(self):
        legacy = bundle(station="I10")
        legacy["claims"][0]["address"]["gid"] = 90
        legacy["claims"][0]["address"]["domain"] = "IC10"
        legacy["claims"][0]["address"]["node"] = "PROMOTION"
        legacy["observations"][0]["content"] = "GID090 | I10 | promotion"
        legacy["claims"][0]["exact_text"] = "GID090 | I10 | promotion"
        result = self.compiler.ingest_bundle(legacy)
        self.assertEqual(result.claims[0].status.value, "ADMITTED")

    def test_observation_versions_form_lineage_without_overwrite(self):
        first = LiveObservation.build(
            carrier="google_doc",
            source_id="doc-1",
            revision="r1",
            locator="https://docs.google.com/document/d/doc-1/edit",
            fragment="heading-1",
            authority="primary-documentary",
            evidence_root="root:doc-1",
            kind=ObservationKind.NATIVE_EXCERPT,
            content="first",
        )
        second = LiveObservation.build(
            carrier="google_doc",
            source_id="doc-1",
            revision="r2",
            locator="https://docs.google.com/document/d/doc-1/edit",
            fragment="heading-1",
            authority="primary-documentary",
            evidence_root="root:doc-1",
            kind=ObservationKind.NATIVE_EXCERPT,
            content="second",
        )
        self.store.save_observation(first.to_dict())
        self.store.save_observation(second.to_dict())
        lineage = self.store.observation_lineage(
            "google_doc", "doc-1", "heading-1"
        )
        self.assertEqual([item["revision"] for item in lineage], ["r1", "r2"])

    def test_same_observation_identity_with_changed_payload_is_collision(self):
        first = LiveObservation.build(
            carrier="google_doc",
            source_id="doc-1",
            revision="r1",
            locator="https://docs.google.com/document/d/doc-1/edit",
            fragment="heading-1",
            authority="primary-documentary",
            evidence_root="root:doc-1",
            kind=ObservationKind.NATIVE_EXCERPT,
            content="first",
        )
        changed = LiveObservation.build(
            carrier="google_doc",
            source_id="doc-1",
            revision="r1",
            locator="https://docs.google.com/document/d/doc-1/edit",
            fragment="heading-1",
            authority="primary-documentary",
            evidence_root="root:doc-1",
            kind=ObservationKind.NATIVE_EXCERPT,
            content="changed",
        )
        self.assertEqual(self.store.save_observation(first.to_dict()), "INSERTED")
        self.assertEqual(
            self.store.save_observation(changed.to_dict()),
            "OBSERVATION_COLLISION",
        )
        self.assertEqual(self.store.counts()["observation_collisions"], 1)


class LiveCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.store = NavStore()
        self.compiler = LiveContextCompiler(self.store)
        self.compiler.ingest_bundle(bundle())
        self.navigator = InternalNavigator(self.store)
        self.session = SessionManager(self.store)

    def tearDown(self):
        self.store.close()

    def close_checkpoint(self):
        query = QueryBundle.build(
            goal="live source context",
            terms=("KC15",),
            route_budget=10,
        )
        packet = self.navigator.query(query)
        replay = self.navigator.close_session(query, packet)
        coverage = CoverageAuditor(self.store).audit()
        return self.session.close(query, packet, replay, coverage)

    def standalone_observation(self, revision: str = "r1"):
        return LiveObservation.build(
            carrier="github_seed",
            source_id="demeet2k/Athena:README.md",
            revision=revision,
            locator="https://github.com/demeet2k/Athena/blob/main/README.md",
            fragment="runtime-law",
            authority="private-git-control-plane",
            evidence_root="root:github:athena",
            kind=ObservationKind.REPOSITORY_FILE,
            content=f"runtime law {revision}",
        )

    def test_new_context_after_checkpoint_is_valid_with_drift(self):
        closed = self.close_checkpoint()
        observation = self.standalone_observation()
        self.store.save_observation(observation.to_dict())
        packet = self.session.warm_reentry(closed.checkpoint_id)
        self.assertEqual(packet.status.value, "VALID_WITH_DRIFT")
        self.assertTrue(any("NEW_CONTEXT=1" in defect for defect in packet.defects))
        rollback = self.session.rollback_packet(closed.checkpoint_id)
        self.assertEqual(
            rollback.supersede_observations,
            (observation.observation_id,),
        )
        self.assertEqual(rollback.mode, "APPEND_ONLY_COMPENSATING_ROLLBACK")

    def test_missing_checkpointed_observation_is_stale(self):
        observation = self.standalone_observation()
        self.store.save_observation(observation.to_dict())
        closed = self.close_checkpoint()
        with self.store.connection:
            self.store.connection.execute(
                "DELETE FROM live_observations WHERE observation_id = ?",
                (observation.observation_id,),
            )
        packet = self.session.warm_reentry(closed.checkpoint_id)
        self.assertEqual(packet.status.value, "STALE")
        self.assertTrue(any("SOURCE_DECAY" in defect for defect in packet.defects))


if __name__ == "__main__":
    unittest.main()
