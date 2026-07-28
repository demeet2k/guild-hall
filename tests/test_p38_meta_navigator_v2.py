from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from kc144_crystal.agent_receipts import canonical_bytes, content_address
from kc144_crystal.p37_reconciliation import (
    P35_EXACT_FILES,
    PUBLIC_P36_RESULT_ID,
    SOURCE_P37_PARENT_RESULT_ID,
    SOURCE_P37_RESULT_ID,
    ReconciliationError,
    bind_exact_p35_registry,
    expected_p35_registry_binding,
    p37_public_reconciliation,
    source_p37_capsule,
    verify_p35_registry_binding,
    verify_reconciliation,
)
from kc144_crystal.p38_runtime import (
    P38_CRYSTALS,
    P38_CUTOFF,
    P38_LANES,
    P38_LOOKUP_KEY,
    P38_ROUTE,
    P38RuntimeError,
    build_doc_revision_event,
    build_ic10_return,
    build_outcome,
    build_repository_byte_event,
    compile_multi_crystal_query,
    compile_outcome_calibration,
    compile_p38_cycle,
    compile_p38_release,
    coordinate_tensor_144,
    empty_signer_registry,
    enroll_trusted_signer,
    p38_contract,
    route_source_events,
    second_edge_experiment,
    signer_enrollment_challenge,
    verify_p38_cycle,
    verify_signer_registry,
)


def query() -> dict:
    return {
        "schema": "KC144.P38.Query.V1",
        "goal": "parallel rotation source integration return",
        "terms": ["navigation", "compress", "expand"],
        "crystals": list(P38_CRYSTALS),
        "source_surfaces": ["GITHUB", "GOOGLE_DRIVE"],
    }


def repository_event() -> dict:
    return build_repository_byte_event(
        repository="demeet2k/guild-hall",
        branch="kc144-mycelium-tool-dispatch-v1",
        commit="1" * 40,
        tree="2" * 40,
        observed_at="2026-07-28T02:00:00.000000Z",
        files=[
            {
                "path": "src/kc144_crystal/p38_runtime.py",
                "blob": "3" * 40,
                "sha256": "sha256:" + "4" * 64,
                "size": 123,
            }
        ],
    )


def verified_binding() -> dict:
    files = [
        {
            "name": name,
            "rows": descriptor["rows"],
            "sha256": descriptor["sha256"],
            "row_root": "sha256:" + f"{index + 1:064x}",
            "errors": [],
            "verdict": "PASS",
        }
        for index, (name, descriptor) in enumerate(sorted(P35_EXACT_FILES.items()))
    ]
    body = {
        "schema": "KC144.P35.ExactSubscriptionRegistryBinding.V1",
        "state": "EXACT_BYTES_VERIFIED",
        "files": files,
        "counts": {
            "action_subscriptions": 360,
            "gid_subscriptions": 144,
            "carrier_subscriptions": 37,
            "total_rows": 541,
        },
        "row_commitment_root": "sha256:" + "f" * 64,
        "private_source_metadata_included": False,
        "truth_effect": "NONE",
        "authority_effect": "NONE",
        "errors": [],
    }
    return {
        **body,
        "binding_digest": content_address(
            "kc144.p35.exact-subscription-registry", body
        ),
    }


def outcomes() -> list[dict]:
    result = []
    for index in range(12):
        result.append(
            build_outcome(
                outcome_class=(
                    "TASK_OUTCOME" if index % 2 == 0 else "EMPIRICAL_RESULT"
                ),
                origin_class="CONNECTOR_OBSERVED",
                observed_at=f"2026-07-28T01:{index:02d}:00.000000Z",
                source_surface=f"SURFACE_{index % 3}",
                source_commitment="sha256:" + f"{index + 1:064x}",
                route_id=f"ROUTE_{index % 3}",
                metric="success",
                value=float(index % 2),
            )
        )
    return result


class P38MetaNavigatorTests(unittest.TestCase):
    def test_all_p37_p38_schemas_parse(self) -> None:
        root = Path(__file__).resolve().parents[1] / "schemas" / "kc144"
        schemas = sorted(root.glob("p3[78]-*.schema.json"))
        self.assertEqual(len(schemas), 7)
        for path in schemas:
            value = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(
                value["$schema"],
                "https://json-schema.org/draft/2020-12/schema",
            )

    def test_reconciliation_preserves_both_distinct_p36_parents(self) -> None:
        value = p37_public_reconciliation()
        self.assertEqual(
            value["public_branch_parent"]["result_id"], PUBLIC_P36_RESULT_ID
        )
        self.assertEqual(value["source_sibling"]["result_id"], SOURCE_P37_RESULT_ID)
        self.assertEqual(
            value["source_sibling"]["source_parent_result_id"],
            SOURCE_P37_PARENT_RESULT_ID,
        )
        self.assertNotEqual(
            value["public_branch_parent"]["result_id"],
            value["source_sibling"]["source_parent_result_id"],
        )
        self.assertEqual(verify_reconciliation(value)["verdict"], "PASS")

    def test_reconciliation_tamper_is_detected(self) -> None:
        value = p37_public_reconciliation()
        value["relation"] = "DIRECT_CHILD"
        self.assertEqual(verify_reconciliation(value)["verdict"], "FAIL")

    def test_source_capsule_is_hold_and_truth_neutral(self) -> None:
        capsule = source_p37_capsule()
        self.assertEqual(capsule["release_state"], "HOLD")
        self.assertEqual(capsule["truth_effect"], "NONE")
        self.assertEqual(capsule["verified_census"]["receipts"]["passed"], 627)

    def test_expected_registry_is_commitment_not_false_verification(self) -> None:
        binding = expected_p35_registry_binding()
        self.assertEqual(binding["state"], "EXPECTED_EXACT_BYTES")
        self.assertEqual(binding["counts"]["total_rows"], 541)
        self.assertFalse(binding["private_source_metadata_included"])
        self.assertEqual(verify_p35_registry_binding(binding)["verdict"], "PASS")

    def test_exact_registry_verifier_checks_bytes_rows_and_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rows = {
                "action_crosswalk_360.ndjson": [
                    {
                        "crosswalk_id": "KC144.P35.CROSSWALK.001",
                        "truth_effect": "NONE",
                        "matching_production_events_observed": 0,
                        "state_after": (
                            "SUBSCRIBED_WAITING_FOR_MATCHING_PRODUCTION_EVENT"
                        ),
                    },
                    {
                        "crosswalk_id": "KC144.P35.CROSSWALK.002",
                        "truth_effect": "NONE",
                        "matching_production_events_observed": 0,
                        "state_after": (
                            "SUBSCRIBED_WAITING_FOR_MATCHING_PRODUCTION_EVENT"
                        ),
                    },
                ],
                "carrier_subscriptions_37.ndjson": [{"carrier_id": "F01"}],
                "gid_subscriptions_144.ndjson": [{"gid": "GID001"}],
            }
            descriptors = {}
            for name, values in rows.items():
                raw = "".join(
                    json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
                    for value in values
                ).encode()
                (root / name).write_bytes(raw)
                descriptors[name] = {
                    "rows": len(values),
                    "sha256": "sha256:" + hashlib.sha256(raw).hexdigest(),
                    "identity_field": (
                        "crosswalk_id"
                        if name.startswith("action")
                        else "carrier_id"
                        if name.startswith("carrier")
                        else "gid"
                    ),
                    "identity_prefix": (
                        "KC144.P35.CROSSWALK."
                        if name.startswith("action")
                        else "F"
                        if name.startswith("carrier")
                        else "GID"
                    ),
                }
            with patch.dict(P35_EXACT_FILES, descriptors, clear=True):
                binding = bind_exact_p35_registry(root)
            self.assertEqual(binding["state"], "EXACT_BYTES_VERIFIED")
            self.assertEqual(binding["counts"]["total_rows"], 4)

    def test_exact_registry_rejects_one_byte_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in P35_EXACT_FILES:
                (root / name).write_text("{}\n", encoding="utf-8")
            with self.assertRaises(ReconciliationError):
                bind_exact_p35_registry(root)

    def test_contract_freezes_seven_lanes_and_route(self) -> None:
        contract = p38_contract()
        self.assertEqual([row["lane"] for row in contract["lanes"]], list(P38_LANES))
        self.assertEqual(contract["route"], list(P38_ROUTE))
        self.assertEqual(contract["lookup_key"], P38_LOOKUP_KEY)

    def test_coordinate_tensor_covers_every_gid_and_math_view(self) -> None:
        tensor = coordinate_tensor_144()
        self.assertEqual(len(tensor["coordinates"]), 144)
        self.assertEqual(
            [row["gid"] for row in tensor["coordinates"]], list(range(1, 145))
        )
        self.assertEqual(tensor["census"]["kc54_duplex_nodes"], 27)
        self.assertGreater(tensor["census"]["d4_views"], 1000)
        self.assertGreater(tensor["census"]["local_orbit_memberships"], 1000)

    def test_coordinate_transform_orbits_never_claim_truth(self) -> None:
        tensor = coordinate_tensor_144()
        self.assertTrue(
            all(
                row["transform"]["truth_effect"] == "NONE"
                and row["transform"]["identity_preserved"]
                for row in tensor["coordinates"]
            )
        )

    def test_multi_crystal_query_routes_all_seven_lenses(self) -> None:
        compiled = compile_multi_crystal_query(query())
        self.assertEqual([row["crystal"] for row in compiled["lanes"]], list(P38_CRYSTALS))
        self.assertEqual(compiled["parallel_width"], 7)
        self.assertRegex(compiled["query_digest"], r"^sha256:[0-9a-f]{64}$")

    def test_query_crystal_order_does_not_change_output(self) -> None:
        left = compile_multi_crystal_query(query())
        value = query()
        value["crystals"] = list(reversed(value["crystals"]))
        right = compile_multi_crystal_query(value)
        self.assertEqual(left, right)

    def test_query_rejects_unknown_crystal(self) -> None:
        value = query()
        value["crystals"] = ["KC144", "FAKE"]
        with self.assertRaises(P38RuntimeError):
            compile_multi_crystal_query(value)

    def test_repository_byte_event_binds_commit_tree_blob_and_sha256(self) -> None:
        event = repository_event()
        source = event["source"]
        self.assertEqual(source["version_type"], "GIT_COMMIT_TREE_AND_BLOB")
        self.assertEqual(len(source["commit"]), 40)
        self.assertEqual(len(event["files"][0]["blob"]), 40)
        self.assertRegex(event["files"][0]["sha256"], r"^sha256:[0-9a-f]{64}$")

    def test_source_router_keeps_docs_and_repository_bytes_distinct(self) -> None:
        doc = build_doc_revision_event(
            body_sha256="sha256:" + "5" * 64,
            revision_commitment="sha256:" + "6" * 64,
            issuer_commitment="sha256:" + "7" * 64,
            observed_at="2026-07-28T01:00:00.000000Z",
        )
        routed = route_source_events([repository_event(), doc], cutoff=P38_CUTOFF)
        self.assertEqual(routed["counts"]["repository_byte_events"], 1)
        self.assertEqual(routed["counts"]["doc_revision_events"], 1)
        self.assertTrue(
            all(row["status"] == "ADMITTED_NON_PROMOTING" for row in routed["receipts"])
        )

    def test_source_event_tamper_is_rejected(self) -> None:
        event = repository_event()
        event["source"]["tree"] = "8" * 40
        routed = route_source_events([event], cutoff=P38_CUTOFF)
        self.assertEqual(routed["receipts"][0]["status"], "REJECTED")
        self.assertIn("E_EVENT_DIGEST", routed["receipts"][0]["errors"])

    def test_second_edge_is_only_a_proposal_graph_intervention(self) -> None:
        edge = second_edge_experiment(prerequisites_pass=True)
        self.assertTrue(edge["executed_in_proposal_graph"])
        self.assertFalse(edge["executed_in_canonical_graph"])
        self.assertEqual(edge["measurement"]["global_distance_reduction"], 1050)
        self.assertEqual(edge["measurement"]["global_diameter_after"], 10)
        self.assertEqual(edge["real_world_outcome"], "UNMEASURED")

    def test_empty_outcome_corpus_is_hold(self) -> None:
        value = compile_outcome_calibration([], cutoff=P38_CUTOFF)
        self.assertEqual(value["status"], "CORPUS_HOLD")
        self.assertEqual(value["canonical_weight_updates_executed"], 0)

    def test_route_generated_outcome_is_rejected(self) -> None:
        packet = build_outcome(
            outcome_class="TASK_OUTCOME",
            origin_class="CONNECTOR_OBSERVED",
            observed_at="2026-07-28T01:00:00.000000Z",
            source_surface="SURFACE",
            source_commitment="sha256:" + "9" * 64,
            route_id="ROUTE",
            metric="success",
            value=1.0,
        )
        packet["route_generated"] = True
        value = compile_outcome_calibration([packet], cutoff=P38_CUTOFF)
        self.assertEqual(value["census"]["accepted"], 0)
        self.assertIn("E_ROUTE_GENERATED", value["rejected"][0]["errors"])

    def test_held_out_corpus_requires_size_source_and_route_diversity(self) -> None:
        value = compile_outcome_calibration(outcomes(), cutoff=P38_CUTOFF)
        self.assertEqual(value["status"], "CALIBRATION_READY")
        self.assertEqual(value["census"]["accepted"], 12)
        self.assertEqual(len(value["proposed_weight_updates"]), 3)
        self.assertEqual(value["canonical_weight_updates_executed"], 0)

    def test_empty_signer_registry_grants_no_authority(self) -> None:
        registry = empty_signer_registry()
        self.assertEqual(verify_signer_registry(registry)["verdict"], "PASS")
        self.assertFalse(registry["authority_granted_by_enrollment"])

    def _enrolled(self):
        key = Ed25519PrivateKey.generate()
        challenge = signer_enrollment_challenge(
            signer_id="independent-reviewer-1",
            public_key=key.public_key(),
            valid_from="2026-07-28T00:00:00.000000Z",
            valid_until="2026-07-29T23:59:59.000000Z",
        )
        proof = key.sign(
            b"KC144.P38.SIGNER-ENROLLMENT.V1\0" + canonical_bytes(challenge)
        )
        registry = enroll_trusted_signer(
            empty_signer_registry(),
            challenge,
            __import__("base64").urlsafe_b64encode(proof).decode().rstrip("="),
        )
        return key, registry

    def test_signer_enrollment_requires_proof_of_possession(self) -> None:
        key = Ed25519PrivateKey.generate()
        challenge = signer_enrollment_challenge(
            signer_id="reviewer",
            public_key=key.public_key(),
            valid_from="2026-07-28T00:00:00.000000Z",
            valid_until="2026-07-29T00:00:00.000000Z",
        )
        with self.assertRaises(P38RuntimeError):
            enroll_trusted_signer(empty_signer_registry(), challenge, "invalid")

    def test_enrollment_is_valid_but_not_authority(self) -> None:
        _, registry = self._enrolled()
        self.assertEqual(verify_signer_registry(registry)["verdict"], "PASS")
        self.assertFalse(registry["entries"][0]["authority_granted"])

    def test_default_cycle_is_honest_hold(self) -> None:
        cycle = compile_p38_cycle(
            query=query(),
            registry_binding=expected_p35_registry_binding(),
        )
        self.assertEqual(cycle["state"]["global_release"], "HOLD")
        self.assertEqual(cycle["state"]["truth_effect"], "NONE")
        self.assertEqual(cycle["state"]["independent_ic10_returns"], 0)
        self.assertEqual(verify_p38_cycle(cycle)["verdict"], "PASS")

    def test_exact_binding_and_repo_event_execute_only_second_proposal_edge(
        self,
    ) -> None:
        binding = verified_binding()
        cycle = compile_p38_cycle(
            query=query(),
            registry_binding=binding,
            source_events=[repository_event()],
        )
        self.assertEqual(cycle["state"]["proposal_edges_executed_this_cycle"], 1)
        self.assertEqual(cycle["state"]["canonical_edges_executed_this_cycle"], 0)
        self.assertEqual(cycle["state"]["global_release"], "HOLD")

    def test_forged_exact_binding_cannot_execute_second_edge(self) -> None:
        binding = verified_binding()
        binding["files"][0]["sha256"] = "sha256:" + "0" * 64
        cycle = compile_p38_cycle(
            query=query(),
            registry_binding=binding,
            source_events=[repository_event()],
        )
        self.assertEqual(cycle["state"]["registry_verification"], "FAIL")
        self.assertEqual(cycle["state"]["proposal_edges_executed_this_cycle"], 0)

    def test_valid_independent_ic10_return_can_close_only_the_authority_gate(
        self,
    ) -> None:
        key, registry = self._enrolled()
        binding = verified_binding()
        first = compile_p38_cycle(
            query=query(),
            registry_binding=binding,
            source_events=[repository_event()],
            outcomes=outcomes(),
            signer_registry=registry,
        )
        packet = build_ic10_return(
            candidate_root=first["state"]["candidate_root"],
            calibration_digest=first["calibration"]["calibration_digest"],
            source_routing_digest=first["source_routing"]["routing_digest"],
            signer_id="independent-reviewer-1",
            private_key=key,
            issued_at="2026-07-28T02:00:00.000000Z",
            expires_at="2026-07-29T02:00:00.000000Z",
            nonce="unique-nonce-1",
        )
        final = compile_p38_cycle(
            query=query(),
            registry_binding=binding,
            source_events=[repository_event()],
            outcomes=outcomes(),
            signer_registry=registry,
            ic10_returns=[packet],
        )
        self.assertEqual(final["state"]["independent_ic10_returns"], 1)
        self.assertEqual(final["state"]["global_release"], "READY")
        self.assertEqual(final["state"]["truth_effect"], "NONE")
        self.assertFalse(final["state"]["production_mutated"])

    def test_ic10_tamper_fails_closed(self) -> None:
        key, registry = self._enrolled()
        binding = verified_binding()
        first = compile_p38_cycle(
            query=query(),
            registry_binding=binding,
            source_events=[repository_event()],
            outcomes=outcomes(),
            signer_registry=registry,
        )
        packet = build_ic10_return(
            candidate_root=first["state"]["candidate_root"],
            calibration_digest=first["calibration"]["calibration_digest"],
            source_routing_digest=first["source_routing"]["routing_digest"],
            signer_id="independent-reviewer-1",
            private_key=key,
            issued_at="2026-07-28T02:00:00.000000Z",
            expires_at="2026-07-29T02:00:00.000000Z",
            nonce="unique-nonce-2",
        )
        packet["decision"] = "AUTHORIZE_ANYTHING"
        final = compile_p38_cycle(
            query=query(),
            registry_binding=binding,
            source_events=[repository_event()],
            outcomes=outcomes(),
            signer_registry=registry,
            ic10_returns=[packet],
        )
        self.assertEqual(final["state"]["global_release"], "HOLD")

    def test_cycle_tamper_is_detected(self) -> None:
        cycle = compile_p38_cycle(
            query=query(),
            registry_binding=expected_p35_registry_binding(),
        )
        tampered = copy.deepcopy(cycle)
        tampered["state"]["production_mutated"] = True
        verification = verify_p38_cycle(tampered)
        self.assertEqual(verification["verdict"], "FAIL")
        self.assertIn("E_ENVELOPE_DIGEST", verification["errors"])
        self.assertIn("E_PROTECTED_STATE_ESCALATION", verification["errors"])

    def test_release_is_reproducible_candidate_hold(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            kwargs = {
                "implementation_commit": "a" * 40,
                "implementation_tree": "b" * 40,
            }
            left = compile_p38_release(first, **kwargs)
            right = compile_p38_release(second, **kwargs)
            self.assertEqual(left, right)
            self.assertEqual(left["status"], "CANDIDATE_HOLD")
            self.assertEqual(left["registry_binding_state"], "EXPECTED_EXACT_BYTES")
            self.assertEqual(
                (Path(first) / "SHA256SUMS").read_text(),
                (Path(second) / "SHA256SUMS").read_text(),
            )

    def test_public_artifacts_contain_no_private_docs_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            compile_p38_release(
                temporary,
                implementation_commit="c" * 40,
                implementation_tree="d" * 40,
            )
            payload = "\n".join(
                path.read_text(encoding="utf-8")
                for path in Path(temporary).glob("*.json")
            ).lower()
            for forbidden in (
                "docs.google.com",
                "drive.google.com",
                "document_id",
                "native_revision",
                "issuer_email",
            ):
                self.assertNotIn(forbidden, payload)


if __name__ == "__main__":
    unittest.main()
