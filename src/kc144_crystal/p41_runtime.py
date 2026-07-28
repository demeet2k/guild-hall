from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .agent_receipts import canonical_bytes, content_address
from .p39_runtime import GIT_SHA_RE
from .p40_runtime import P40_NEXT_SEED


P41_LOOKUP_KEY = P40_NEXT_SEED
P41_NEXT_SEED = (
    "KC144.V4.3::MATH144.P42::BIND_EXACT_SOURCE_ENUMERATION_WITNESS_"
    "INGEST_FIRST_FIVE_NONLEAKING_HELDOUT_OUTCOMES_RECEIVE_EXTERNAL_IC10_"
    "EDGE_AUTHORIZATION_EXECUTE_THIRD_EDGE_ONCE_AND_FREEZE_POST_EDGE_WATCH_"
    "MACROCYCLE_11"
)
P41_ROUTE = (
    "KC144.V1::GID005::H05",
    "KC144.V1::GID084::I04",
    "KC144.V1::GID047::F04",
    "KC144.V1::GID090::IC10",
    "KC144.V1::GID141::M09",
    "KC144.V1::GID144::M12",
)
P41_LANES = (
    "PUBLIC_P40_PARENT_BIND",
    "SIBLING_SOURCE_FIBER_BIND",
    "HISTORICAL_BODY_REHYDRATION",
    "PUBLIC_REPOSITORY_TREE_BIND",
    "NONLEAKING_HELDOUT_COHORT_FREEZE",
    "INDEPENDENT_IC10_RETURN_INTAKE",
    "THIRD_EDGE_ELIGIBILITY_AND_EXECUTION",
    "PARALLEL_P41_NONCOLLAPSE",
    "M12_RETURN",
)
P41_COHORT_FREEZE = "2026-07-28T07:15:00.000000Z"

PUBLIC_P40_RESULT_ID = "KC144.P40.CANDIDATE::8343b08a8ee5152ed117f281"
PUBLIC_P40_RELEASE_DIGEST = (
    "sha256:8343b08a8ee5152ed117f28189c3172c7a56e8d9912e004b8ea8461c5bb18150"
)
PUBLIC_P40_RELEASE_COMMIT = "ba252f77832520f069ff84af45982df2fdab6017"
PUBLIC_P40_RELEASE_TREE = "92ac9565b2f6e229722faf2a4b02e543ab07072e"

SOURCE_SIBLING_RESULT_ID = "KC144.P40::f07bae53d9e157e9e8e54473"
SOURCE_SIBLING_PARENT_ID = "KC144.P39::9a0a228dc74f001e64507417"
SOURCE_SIBLING_CAPSULE_DIGEST = (
    "sha256:3a78f985957347a12889cc1c7e77e3bd297588b97cec671c30f632f6f62a905f"
)

THIRD_EDGE = {
    "edge_id": "P41.EDGE.003",
    "source": "KC144.V1::GID084::I04",
    "target": "KC144.V1::GID047::F04",
    "operation": "BIDIRECTIONAL_CAUSAL_ABLATION",
}

_IC10_ENROLLMENT_DOMAIN = b"KC144.P41.IC10-ENROLLMENT.V1\0"
_IC10_RETURN_DOMAIN = b"KC144.P41.IC10-RETURN.V1\0"

# These rows are a nonleaking public projection of a connector-retrieved
# historical revision cohort. Raw document IDs, titles, revision numbers,
# timestamps, authors, and bodies are intentionally absent.
_SOURCE_ROWS = (
    ("ab7c44a39c0c70c7c283d7f79c214b39a3a5a856488cb8eda664d2cedc577a06", "020b604b5fb3406b04a2ff19037ec1886deebbc48ab7db1714035aea5b269dc8", "CONTENT"),
    ("c409d9aa7f19bdd68bb87decda1c82f99dea82aedcf9686d6d5f757ccf983ec3", "e6f39a7895f1fd087dee7cb986f907b377a56fc0a7090e4a161711395279a745", "CONTENT"),
    ("15b22f22b13e319c54d0092d6f4142ea6ec56181b7e70c4e1c85d4403f538445", "2fb457d8df4ab3ba4983a67ced6688f622f03cfee62d1c596525a92e84b8bfbc", "CONTENT"),
    ("b33003b1db90bdcebfff552385c39160be9de8c08ca6531c4ad059286e0f6432", "929e5e42630a163430d4dea44e62e783f63246eb3aed95911cafa609666f7d44", "CONTENT"),
    ("3bf600aa0fde8da92220fa839855d5432ca587558229ea9aaa43d48378516695", "bb811a5761d338430a876e73b39b9fb5c715f83a83fbcf0bca31cf8bda268707", "EXACT_EMPTY"),
    ("2671cf94702ed10da80b403412c5f205d9a528e0141c86e936d07e88e067f1ae", "329290f4410db2ec4f284f1d6591175cab314f7d3fa473789811c15c9eb25a85", "CONTENT"),
    ("d522c7e216a9ae8d4a019e6b5c2e5167c176a8c4603a20b4fbcf0403fa0bc5cc", "faab897c05b137d013a4b3d5078edc95a3487de2e5ac48dc9c5015b087e6993d", "CONTENT"),
    ("470b09b405e5ac2a5cc548e86bed7994c2fb6c27f66b4b44e4b416c46be72481", "3de0bb1ce15eaba8b52e16fd8df1a00ae19149d80f74fe3886595fb64cf7bc04", "CONTENT"),
    ("39b2e588ef3acaa65c3794a9c43cb06193b7257dbff762a9ec0880583c9be8ea", "f93f6023387422990d30827faa1718b4b108d1a7e15b81abd7fe0cc6fa1f22bc", "CONTENT"),
    ("0fb7d527a7d9fa857e43fbacadb290b14b0c9003c65c5e9674d5f7bec394c24e", "c2e967d82a5d8ad059d71edf88b508d3f82520b5a1811044b79c15408d02bed2", "CONTENT"),
    ("984140868f7daa95a9bbd372c597eb0df11515a102ddfbe9e116d0bd434a168b", "02f2980c77e8d6c17e37e7bedcc62f811387375114067ad615e8209ada947e9c", "CONTENT"),
    ("94d430090bd4ea38ebc2db140fc604cc66e51b815744c9328873379d89ac3b39", "20172b1b7402a8e442eb100b6ca41aaacf9fe4aca0f29c483fdc06224f5c3f7c", "CONTENT"),
    ("7c296b1a3f6ae52997d60a47cb674ff96d5c274b04489e735f23d6719538b263", "7a62b96dda8f7fcd8d6ad6df75778be503c00dc0f40ea9d2b5edc5a9106d2798", "CONTENT"),
    ("3a0b22c2327d60dd9937cdaa179a2da2b36ffb63274b3f2da7a935e6a6c22b43", "0fba0d78375194d860209ce7993f2c70509784107426163e9171501c11fa0f65", "CONTENT"),
    ("e0edc61edb69c482c99fc93ecf8eaff9bafa5af8b5d4bc4703a7c7e13e1f995b", "ca773e553eb01c6c04cfb7dee9aa7e6b81826fc761d65b89dd03072ba56f591d", "CONTENT"),
    ("74297d0950ea1e217006e59af0e73036a4e56be262695c3f240b26805e005f72", "d6d04f5edd2e1e4beb7c47aec70d13bcc10d6b2a275324d5a33aeb635ef06bdf", "CONTENT"),
    ("948f2a29045f6de51cfaa8baa6aa7521e691f69161fc6cc0fb0a2fd60d76d786", "bb811a5761d338430a876e73b39b9fb5c715f83a83fbcf0bca31cf8bda268707", "EXACT_EMPTY"),
    ("365a263d3617f1a7bade6ad398a559c454cc75608bbf8d4b163da351c2176dc8", "9f50cccfccfa1682a256b46d7ceb4ac5030ee3441f0ddd43fe7f7723b71d90b6", "CONTENT"),
    ("a6ccf1322b72b762e6e685826d904d43c517ac37890b98276ef631ccbfeccfce", "684673c79f3c0216c2e5a344de25845d93bbf8c84333e132934a2b4a14e3983a", "CONTENT"),
    ("9afd8d3bb08b4eb0bc2842d25c2185726edb75c26860b86cc5967f1e47299dbb", "70c0c2a5bf9c0808478019771d4256320bd78813d16889aab2ff170aeef2dfe6", "CONTENT"),
    ("f7836a0c5e46fc46b68b38a00544f27d2aa25421ee610fee2353fe3152548b26", "bc6c0fdc5ac548f6c0a10b0d813424586d264a6bef25b1b03f618fe19aac65e8", "CONTENT"),
    ("41bc86cd41f92dd5ab5766062e534c20929b72dd75b8e98eb36c859992c744ed", "d89b516a774bf0c9927858a6ac7ccdeac6d56834910218ccded7e8853cf253b0", "CONTENT"),
    ("0c7f36ac0bf5c402ad0ced5f7d5f75fba62808227265685318722e3273be6bd2", "0f22b5dc150d955ef37a26bbcb43172e4422664faf1098cbd38b290ba35512b0", "CONTENT"),
    ("18303827c2a40c5f88440939a4b4cc253c83a728c49a52121e7d4d2746bd68dc", "8075e3f85bca0ade8a9bf2ff1d9e429b48e84fc649d98ba47d7188e6b92d9ad3", "CONTENT"),
    ("771d5eddaa9f3040f48e2c9a62192cea769d1095c63fb439931ea0271be6c348", "ac0e59ec439fd8ca8fb5a3f272673b721849136855903e99ea65bfb694c04007", "CONTENT"),
    ("bc7e9c6a7d4648b45afdb3f377fa1eb97e82f5ef0f8e1e458306be86cf66b8a7", "09d4de6bb6bff7b7fb60633e290c4443293278fab71f91e98d1231bf9243435a", "CONTENT"),
    ("bb6a3196a832c163a1a51c5f204e455495c7e487e772318ba4a6e0b13b1e5dc7", "e9ba9c01d50444134d535fa81e63b551848d53ff3cec73bdf7efb2e3f5da5eca", "CONTENT"),
    ("1521d746f80e2a9c81a4c7310768cf11e5b0be48c16988a48162dfba5f10555a", "b440815033e0a5ec09e801b235cbe7e164d92fe72342e921cf27ed5b244af037", "CONTENT"),
    ("7a46f08d10a4645d1de7f92f5b78545748ba79039a8b6e607dc65d3dd9e39880", "e9ba9c01d50444134d535fa81e63b551848d53ff3cec73bdf7efb2e3f5da5eca", "CONTENT"),
)

_PUBLIC_REPOSITORIES = (
    {
        "repository": "AthenachkaCollective/Athenachka",
        "default_branch": "main",
        "commit": "e97663e81f7c464a7a53383c796cc09226776422",
        "tree": "f3c07ab1be604aed3610e51b48ff944c303448c6",
        "path_count": 39,
    },
    {
        "repository": "AthenachkaCollective/Athenachka-Nexus",
        "default_branch": "main",
        "commit": "0122591467a9f164848b60389ccadeb49801f19e",
        "tree": "bce1537e9261816dc35235c72e85e550dc93ee38",
        "path_count": 33,
    },
    {
        "repository": "AthenachkaCollective/Athenachka-Collective",
        "default_branch": "main",
        "commit": "26921c516c7554285d8e952b87168e536f05972c",
        "tree": "6293abdafd0ffdb0b32a0da54576acebecf3367c",
        "path_count": 26,
    },
    {
        "repository": "AthenachkaCollective/AthenachkaCollective",
        "default_branch": "main",
        "commit": "394597e22e2ff89c3476b5a368d4c49544b83473",
        "tree": "a0ffb3f0c48c7042514fb688d3f9e8b1f164212e",
        "path_count": 1,
    },
)


class P41RuntimeError(ValueError):
    pass


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def p41_public_parent() -> dict[str, Any]:
    body = {
        "schema": "KC144.P41.PublicParentBinding.V1",
        "result_id": PUBLIC_P40_RESULT_ID,
        "release_digest": PUBLIC_P40_RELEASE_DIGEST,
        "release_commit": PUBLIC_P40_RELEASE_COMMIT,
        "release_tree": PUBLIC_P40_RELEASE_TREE,
        "relation": "EXACT_PUBLIC_PARENT",
        "verification": "PINNED_RELEASE_IDENTITY",
    }
    return {**body, "binding_digest": content_address("kc144.p41.parent", body)}


def p41_source_manifest() -> dict[str, Any]:
    rows = [
        {
            "source_slot": f"P41.SRC.{index:03d}",
            "locator_commitment": f"sha256:{locator}",
            "body_commitment": f"sha256:{body}",
            "body_state": state,
        }
        for index, (locator, body, state) in enumerate(_SOURCE_ROWS, 1)
    ]
    body = {
        "schema": "KC144.P41.SourceCommitmentManifest.V1",
        "source_predecessor": {
            "result_id": SOURCE_SIBLING_RESULT_ID,
            "parent_result_id": SOURCE_SIBLING_PARENT_ID,
            "capsule_digest": SOURCE_SIBLING_CAPSULE_DIGEST,
            "relation": "TYPED_SOURCE_FIBER_NOT_PUBLIC_PARENT",
        },
        "cohort_basis": {
            "lower_exclusive": "2026-07-28T01:37:13.494Z",
            "upper_inclusive": "2026-07-28T05:00:00.000Z",
            "relation": "REVISION_RECONSTRUCTED_COUNT_MATCH_NOT_ORIGINAL_ENUMERATION",
            "exact_original_enumeration_claimed": False,
        },
        "census": {
            "metadata_heads": 29,
            "prior_resolved": 7,
            "prior_unhydrated": 22,
            "connector_rehydrated": 29,
            "net_heads_closed": 22,
            "content_bodies": 27,
            "exact_empty_bodies": 2,
            "transport_residuals": 0,
        },
        "rows": rows,
        "privacy": {
            "projection": "COMMITMENTS_ONLY",
            "raw_document_ids_published": 0,
            "titles_published": 0,
            "revision_ids_published": 0,
            "timestamps_published": 0,
            "raw_body_bytes_published": 0,
        },
        "status": "REHYDRATED_RECONSTRUCTED_COHORT",
        "truth_effect": "NONE",
        "evidence_effect": "SOURCE_RETRIEVAL_COMMITMENTS_ONLY",
    }
    return {
        **body,
        "manifest_root": content_address("kc144.p41.source-manifest", body),
    }


def p41_repository_forest() -> dict[str, Any]:
    rows = [dict(row) for row in _PUBLIC_REPOSITORIES]
    body = {
        "schema": "KC144.P41.RepositoryForest.V1",
        "epoch": "P41.CONNECTOR.READ.2026-07-28",
        "owner": "AthenachkaCollective",
        "visibility": "PUBLIC_ONLY",
        "repositories": rows,
        "repository_count": len(rows),
        "path_count": sum(int(row["path_count"]) for row in rows),
        "all_commits_pinned": all(GIT_SHA_RE.fullmatch(row["commit"]) for row in rows),
        "all_trees_pinned": all(GIT_SHA_RE.fullmatch(row["tree"]) for row in rows),
        "mutation_executed": False,
        "truth_effect": "NONE",
        "authority_effect": "NONE",
    }
    return {
        **body,
        "forest_root": content_address("kc144.p41.repository-forest", body),
    }


def p41_parallel_lineage() -> dict[str, Any]:
    body = {
        "schema": "KC144.P41.ParallelLineage.V1",
        "parallel_label": "ATHENA_GIT_BRAIN_V2.P41",
        "relation": "PARALLEL_LABEL_COLLISION_NOT_PARENT_NOT_MERGED",
        "semantic_role": "DURABLE_EVENT_DELIVERY_AND_ARTIFACT_PINS",
        "this_p41_role": "SOURCE_TREE_COHORT_EDGE_AND_IC10_MACROCYCLE",
        "private_repository_locator_published": False,
        "private_receipt_embedded": False,
        "merge_executed": False,
        "renumbering_executed": False,
        "truth_effect": "NONE",
        "authority_effect": "NONE",
    }
    return {
        **body,
        "lineage_digest": content_address("kc144.p41.parallel-lineage", body),
    }


def p41_contract() -> dict[str, Any]:
    body = {
        "schema": "KC144.P41.Contract.V1",
        "lookup_key": P41_LOOKUP_KEY,
        "public_parent": p41_public_parent(),
        "source_fiber": {
            "result_id": SOURCE_SIBLING_RESULT_ID,
            "relation": "TYPED_SOURCE_FIBER_NOT_PUBLIC_PARENT",
        },
        "route": list(P41_ROUTE),
        "lanes": [
            {
                "lane_id": f"P41.L{index:02d}",
                "lane": lane,
                "parallel_group": 1 if index <= 4 else 2 if index <= 6 else 3,
                "return": P41_ROUTE[-1],
            }
            for index, lane in enumerate(P41_LANES, 1)
        ],
        "third_edge": dict(THIRD_EDGE),
        "edge_law": (
            "SOURCE_COMMITMENT_COHORT_COMPLETE_AND_PUBLIC_REPOSITORY_FOREST_"
            "PINNED_AND_NONLEAKING_HELDOUT_COHORT_READY_AND_INDEPENDENT_IC10_"
            "RETURN_VERIFIED_THEN_EXECUTE_EXACTLY_ONCE"
        ),
        "privacy_law": (
            "PUBLIC_RELEASE_CONTAINS_ONLY_ONE_WAY_SOURCE_COMMITMENTS_AND_NEVER_"
            "RAW_PRIVATE_LOCATORS_TITLES_REVISIONS_OR_BODY_BYTES"
        ),
        "noncollapse": [
            "PUBLIC_P40_PARENT_IS_NOT_SOURCE_SIBLING_P40",
            "RECONSTRUCTED_COUNT_MATCH_IS_NOT_ORIGINAL_ENUMERATION_WITNESS",
            "BODY_RETRIEVAL_IS_NOT_HELDOUT_OUTCOME",
            "REPOSITORY_HEAD_IS_NOT_REPOSITORY_TREE",
            "REPOSITORY_TREE_BINDING_IS_NOT_MERGE_OR_DEPLOYMENT",
            "CONTINUATION_COMMAND_IS_NOT_HELDOUT_OUTCOME",
            "SEALED_OUTCOME_COMMITMENT_IS_NOT_UNBLINDED_LABEL",
            "TEST_EDGE_EXECUTION_IS_NOT_PRODUCTION_GRAPH_MUTATION",
            "SIGNED_RETURN_IS_NOT_VALID_UNLESS_REGISTRY_AND_ROOTS_MATCH",
            "PARALLEL_P41_LABEL_IS_NOT_THIS_P41_LINEAGE",
            "PUBLICATION_IS_NOT_TRUTH_OR_AUTHORITY_PROMOTION",
        ],
        "default_state": "HOLD_EXTERNAL_HELDOUT_AND_IC10_INPUTS_ABSENT",
        "next_seed": P41_NEXT_SEED,
    }
    return {**body, "contract_digest": content_address("kc144.p41.contract", body)}


def build_heldout_event(
    *,
    event_id: str,
    outcome_class: str,
    observed_at: str,
    source_surface: str,
    route_id: str,
    detail: str,
) -> dict[str, Any]:
    if outcome_class not in {"TASK_OUTCOME", "EMPIRICAL_RESULT"}:
        raise P41RuntimeError("held-out event must be a task or empirical outcome")
    if not all((event_id, source_surface, route_id, detail)):
        raise P41RuntimeError("held-out event fields must be non-empty")
    if not observed_at.endswith("Z") or observed_at <= P41_COHORT_FREEZE:
        raise P41RuntimeError("held-out event must occur strictly after the freeze")
    private_body = {
        "event_id": event_id,
        "outcome_class": outcome_class,
        "observed_at": observed_at,
        "source_surface": source_surface,
        "route_id": route_id,
        "detail": detail,
    }
    public = {
        "schema": "KC144.P41.SealedHeldoutEvent.V1",
        "event_id": event_id,
        "outcome_class": outcome_class,
        "observed_at": observed_at,
        "source_surface": source_surface,
        "route_id": route_id,
        "partition": "HELD_OUT",
        "label_revealed": False,
        "continuation_only": False,
        "event_commitment": content_address(
            "kc144.p41.heldout-event-private", private_body
        ),
    }
    return {
        **public,
        "public_digest": content_address("kc144.p41.heldout-event", public),
    }


def freeze_heldout_cohort(
    events: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    rows = sorted((dict(row) for row in events), key=lambda row: row.get("event_id", ""))
    errors: list[str] = []
    event_ids: set[str] = set()
    commitments: set[str] = set()
    for row in rows:
        event_id = str(row.get("event_id", ""))
        commitment = str(row.get("event_commitment", ""))
        public_body = {key: value for key, value in row.items() if key != "public_digest"}
        if row.get("schema") != "KC144.P41.SealedHeldoutEvent.V1":
            errors.append("E_EVENT_SCHEMA")
        if row.get("public_digest") != content_address(
            "kc144.p41.heldout-event", public_body
        ):
            errors.append("E_EVENT_DIGEST")
        if event_id in event_ids or commitment in commitments:
            errors.append("E_EVENT_REPLAY")
        event_ids.add(event_id)
        commitments.add(commitment)
        if row.get("outcome_class") not in {"TASK_OUTCOME", "EMPIRICAL_RESULT"}:
            errors.append("E_OUTCOME_CLASS")
        if row.get("partition") != "HELD_OUT":
            errors.append("E_PARTITION")
        if row.get("label_revealed") is not False:
            errors.append("E_LABEL_LEAK")
        if row.get("continuation_only") is not False:
            errors.append("E_CONTINUATION_ONLY")
        if str(row.get("observed_at", "")) <= P41_COHORT_FREEZE:
            errors.append("E_TEMPORAL_LEAK")
        if not commitment.startswith("sha256:") or len(commitment) != 71:
            errors.append("E_EVENT_COMMITMENT")
    event_types = {str(row.get("outcome_class", "")) for row in rows}
    surfaces = {str(row.get("source_surface", "")) for row in rows}
    routes = {str(row.get("route_id", "")) for row in rows}
    ready = (
        not errors
        and len(rows) >= 5
        and len(event_types) >= 2
        and len(surfaces) >= 3
        and len(routes) >= 3
    )
    body = {
        "schema": "KC144.P41.HeldoutCohort.V1",
        "freeze": P41_COHORT_FREEZE,
        "events": rows,
        "event_count": len(rows),
        "required_event_count": 5,
        "event_type_count": len(event_types),
        "source_surface_count": len(surfaces),
        "route_count": len(routes),
        "labels_revealed": 0,
        "continuation_events_admitted": 0,
        "errors": sorted(set(errors)),
        "status": "COHORT_READY" if ready else "HOLD",
        "truth_effect": "NONE",
        "authority_effect": "NONE",
    }
    return {
        **body,
        "cohort_root": content_address("kc144.p41.heldout-cohort", body),
    }


def empty_p41_ic10_registry() -> dict[str, Any]:
    body = {
        "schema": "KC144.P41.IC10Registry.V1",
        "entries": [],
        "authority": "EXTERNAL_REGISTRY_REQUIRED",
    }
    return {
        **body,
        "registry_root": content_address("kc144.p41.ic10-registry", body),
    }


def build_p41_ic10_enrollment(
    *,
    signer_id: str,
    organization_id: str,
    control_root: str,
    public_key: Ed25519PublicKey,
    valid_from: str,
    valid_until: str,
) -> dict[str, Any]:
    if not all((signer_id, organization_id, control_root, valid_from, valid_until)):
        raise P41RuntimeError("IC10 enrollment fields must be non-empty")
    if not control_root.startswith("sha256:") or len(control_root) != 71:
        raise P41RuntimeError("IC10 enrollment requires a control root")
    body = {
        "schema": "KC144.P41.IC10Enrollment.V1",
        "signer_id": signer_id,
        "organization_id": organization_id,
        "control_root": control_root,
        "public_key": _b64(
            public_key.public_bytes(
                serialization.Encoding.Raw,
                serialization.PublicFormat.Raw,
            )
        ),
        "valid_from": valid_from,
        "valid_until": valid_until,
    }
    return {
        **body,
        "enrollment_digest": content_address("kc144.p41.ic10-enrollment", body),
    }


def enroll_p41_ic10_signer(
    registry: Mapping[str, Any],
    enrollment: Mapping[str, Any],
    control_proof: str,
) -> dict[str, Any]:
    if registry.get("schema") != "KC144.P41.IC10Registry.V1":
        raise P41RuntimeError("invalid IC10 registry")
    body = {
        key: value
        for key, value in enrollment.items()
        if key != "enrollment_digest"
    }
    if enrollment.get("enrollment_digest") != content_address(
        "kc144.p41.ic10-enrollment", body
    ):
        raise P41RuntimeError("invalid IC10 enrollment digest")
    try:
        key = Ed25519PublicKey.from_public_bytes(_unb64(str(enrollment["public_key"])))
        key.verify(_unb64(control_proof), _IC10_ENROLLMENT_DOMAIN + canonical_bytes(body))
    except (InvalidSignature, ValueError, KeyError) as error:
        raise P41RuntimeError("invalid IC10 enrollment proof") from error
    entries = [dict(row) for row in registry.get("entries", [])]
    if any(
        row.get("signer_id") == enrollment.get("signer_id")
        or row.get("organization_id") == enrollment.get("organization_id")
        for row in entries
    ):
        raise P41RuntimeError("IC10 signer and organization must be unique")
    entries.append({**dict(enrollment), "control_proof": control_proof})
    entries.sort(key=lambda row: str(row["signer_id"]))
    reg_body = {
        "schema": "KC144.P41.IC10Registry.V1",
        "entries": entries,
        "authority": "EXTERNAL_REGISTRY_BOUND",
    }
    return {
        **reg_body,
        "registry_root": content_address("kc144.p41.ic10-registry", reg_body),
    }


def build_p41_ic10_return(
    *,
    edge_candidate_root: str,
    source_manifest_root: str,
    repository_forest_root: str,
    heldout_cohort_root: str,
    signer_id: str,
    organization_id: str,
    control_root: str,
    private_key: Ed25519PrivateKey,
    issued_at: str,
    expires_at: str,
    nonce: str,
) -> dict[str, Any]:
    body = {
        "schema": "KC144.P41.IC10Return.V1",
        "scope": "P41_THIRD_EDGE_AUTHORIZATION",
        "verdict": "AUTHORIZE_EDGE",
        "edge_candidate_root": edge_candidate_root,
        "source_manifest_root": source_manifest_root,
        "repository_forest_root": repository_forest_root,
        "heldout_cohort_root": heldout_cohort_root,
        "signer_id": signer_id,
        "organization_id": organization_id,
        "control_root": control_root,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "nonce": nonce,
    }
    signature = private_key.sign(_IC10_RETURN_DOMAIN + canonical_bytes(body))
    signed = {**body, "signature": _b64(signature)}
    return {
        **signed,
        "return_digest": content_address("kc144.p41.ic10-return", signed),
    }


def _edge_candidate(
    source_manifest: Mapping[str, Any],
    repository_forest: Mapping[str, Any],
    cohort: Mapping[str, Any],
) -> dict[str, Any]:
    body = {
        "schema": "KC144.P41.EdgeCandidate.V1",
        "edge": dict(THIRD_EDGE),
        "source_manifest_root": source_manifest.get("manifest_root"),
        "repository_forest_root": repository_forest.get("forest_root"),
        "heldout_cohort_root": cohort.get("cohort_root"),
        "execution_count_before": 0,
        "expected_execution_count_after": 1,
        "mutation_scope": "COPIED_PROPOSAL_GRAPH_ONLY",
    }
    return {
        **body,
        "edge_candidate_root": content_address("kc144.p41.edge-candidate", body),
    }


def _verify_ic10_registry(registry: Mapping[str, Any]) -> bool:
    body = {key: value for key, value in registry.items() if key != "registry_root"}
    if registry.get("schema") != "KC144.P41.IC10Registry.V1":
        return False
    if registry.get("registry_root") != content_address(
        "kc144.p41.ic10-registry", body
    ):
        return False
    seen_signers: set[str] = set()
    seen_orgs: set[str] = set()
    for entry in registry.get("entries", []):
        signer = str(entry.get("signer_id", ""))
        organization = str(entry.get("organization_id", ""))
        enrollment = {
            key: value for key, value in entry.items() if key != "control_proof"
        }
        enrollment_body = {
            key: value
            for key, value in enrollment.items()
            if key != "enrollment_digest"
        }
        if (
            not signer
            or not organization
            or signer in seen_signers
            or organization in seen_orgs
            or enrollment.get("enrollment_digest")
            != content_address("kc144.p41.ic10-enrollment", enrollment_body)
        ):
            return False
        try:
            key = Ed25519PublicKey.from_public_bytes(
                _unb64(str(entry["public_key"]))
            )
            key.verify(
                _unb64(str(entry["control_proof"])),
                _IC10_ENROLLMENT_DOMAIN + canonical_bytes(enrollment_body),
            )
        except (InvalidSignature, ValueError, KeyError):
            return False
        seen_signers.add(signer)
        seen_orgs.add(organization)
    return True


def _evaluate_ic10_returns(
    registry: Mapping[str, Any],
    returns: Sequence[Mapping[str, Any]],
    *,
    candidate: Mapping[str, Any],
    source_manifest: Mapping[str, Any],
    repository_forest: Mapping[str, Any],
    cohort: Mapping[str, Any],
) -> dict[str, Any]:
    registry_valid = _verify_ic10_registry(registry)
    entries = {
        str(row.get("signer_id")): row for row in registry.get("entries", [])
    }
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    seen_nonces: set[str] = set()
    seen_organizations: set[str] = set()
    for row_value in returns:
        row = dict(row_value)
        reason = ""
        signer = entries.get(str(row.get("signer_id")))
        signed_body = {
            key: value
            for key, value in row.items()
            if key not in {"signature", "return_digest"}
        }
        digest_body = {
            key: value for key, value in row.items() if key != "return_digest"
        }
        if not registry_valid:
            reason = "REGISTRY_INVALID"
        elif row.get("return_digest") != content_address(
            "kc144.p41.ic10-return", digest_body
        ):
            reason = "RETURN_DIGEST_INVALID"
        elif signer is None:
            reason = "SIGNER_NOT_ENROLLED"
        elif (
            row.get("organization_id") != signer.get("organization_id")
            or row.get("control_root") != signer.get("control_root")
        ):
            reason = "ENROLLMENT_BINDING_MISMATCH"
        elif row.get("scope") != "P41_THIRD_EDGE_AUTHORIZATION":
            reason = "SCOPE_MISMATCH"
        elif row.get("verdict") != "AUTHORIZE_EDGE":
            reason = "VERDICT_MISMATCH"
        elif row.get("edge_candidate_root") != candidate.get("edge_candidate_root"):
            reason = "EDGE_ROOT_MISMATCH"
        elif row.get("source_manifest_root") != source_manifest.get("manifest_root"):
            reason = "SOURCE_ROOT_MISMATCH"
        elif row.get("repository_forest_root") != repository_forest.get("forest_root"):
            reason = "REPOSITORY_ROOT_MISMATCH"
        elif row.get("heldout_cohort_root") != cohort.get("cohort_root"):
            reason = "COHORT_ROOT_MISMATCH"
        elif not (
            str(signer.get("valid_from")) <= str(row.get("issued_at"))
            < str(row.get("expires_at")) <= str(signer.get("valid_until"))
        ):
            reason = "VALIDITY_WINDOW_MISMATCH"
        elif str(row.get("nonce", "")) in seen_nonces:
            reason = "NONCE_REPLAY"
        elif str(row.get("organization_id", "")) in seen_organizations:
            reason = "ORGANIZATION_NOT_INDEPENDENT"
        else:
            try:
                key = Ed25519PublicKey.from_public_bytes(
                    _unb64(str(signer["public_key"]))
                )
                key.verify(
                    _unb64(str(row["signature"])),
                    _IC10_RETURN_DOMAIN + canonical_bytes(signed_body),
                )
            except (InvalidSignature, ValueError, KeyError):
                reason = "SIGNATURE_INVALID"
        if reason:
            rejected.append(
                {
                    "return_digest": str(row.get("return_digest", "")),
                    "reason": reason,
                }
            )
        else:
            accepted.append(row)
            seen_nonces.add(str(row["nonce"]))
            seen_organizations.add(str(row["organization_id"]))
    accepted.sort(key=lambda row: str(row["return_digest"]))
    rejected.sort(key=lambda row: (row["reason"], row["return_digest"]))
    body = {
        "schema": "KC144.P41.IC10Evaluation.V1",
        "registry_root": registry.get("registry_root"),
        "registry_valid": registry_valid,
        "required_independent_returns": 1,
        "accepted_returns": accepted,
        "accepted_return_count": len(accepted),
        "independent_organization_count": len(seen_organizations),
        "rejected_returns": rejected,
        "status": (
            "INDEPENDENT_RETURN_VERIFIED"
            if registry_valid and len(accepted) >= 1
            else "HOLD"
        ),
        "truth_effect": "NONE",
        "authority_effect": "EDGE_AUTHORIZATION_ONLY" if accepted else "NONE",
    }
    return {
        **body,
        "evaluation_digest": content_address("kc144.p41.ic10-evaluation", body),
    }


def _lane_receipt(index: int, lane: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    body = {
        "schema": "KC144.P41.LaneReceipt.V1",
        "lane_id": f"P41.L{index:02d}",
        "lane": lane,
        "payload_digest": content_address(f"kc144.p41.lane.{lane.lower()}", payload),
        "return": P41_ROUTE[-1],
        "truth_effect": "NONE",
    }
    return {
        **body,
        "receipt_id": content_address("kc144.p41.lane-receipt", body),
    }


def compile_p41_cycle(
    *,
    heldout_events: Sequence[Mapping[str, Any]] = (),
    ic10_registry: Mapping[str, Any] | None = None,
    ic10_returns: Sequence[Mapping[str, Any]] = (),
    namespace: str = "PRODUCTION",
) -> dict[str, Any]:
    if namespace not in {"PRODUCTION", "TEST"}:
        raise P41RuntimeError("namespace must be PRODUCTION or TEST")
    contract = p41_contract()
    parent = p41_public_parent()
    source = p41_source_manifest()
    repositories = p41_repository_forest()
    cohort = freeze_heldout_cohort(heldout_events)
    candidate = _edge_candidate(source, repositories, cohort)
    registry = dict(ic10_registry or empty_p41_ic10_registry())
    ic10 = _evaluate_ic10_returns(
        registry,
        ic10_returns,
        candidate=candidate,
        source_manifest=source,
        repository_forest=repositories,
        cohort=cohort,
    )
    parallel = p41_parallel_lineage()
    source_ready = (
        source["census"]["connector_rehydrated"] == 29
        and source["census"]["net_heads_closed"] == 22
        and source["census"]["transport_residuals"] == 0
    )
    repository_ready = (
        repositories["repository_count"] == 4
        and repositories["all_commits_pinned"]
        and repositories["all_trees_pinned"]
    )
    eligible = (
        source_ready
        and repository_ready
        and cohort["status"] == "COHORT_READY"
        and ic10["status"] == "INDEPENDENT_RETURN_VERIFIED"
    )
    edge = {
        "schema": "KC144.P41.ThirdEdgeExecution.V1",
        "candidate": candidate,
        "source_gate": "PASS" if source_ready else "HOLD",
        "repository_gate": "PASS" if repository_ready else "HOLD",
        "heldout_gate": cohort["status"],
        "ic10_gate": ic10["status"],
        "eligibility": "ELIGIBLE" if eligible else "HOLD",
        "execution_status": (
            "EXECUTED"
            if eligible and namespace == "PRODUCTION"
            else "SIMULATED_EXECUTION" if eligible else "HELD_NOT_EXECUTED"
        ),
        "execution_count": 1 if eligible else 0,
        "canonical_graph_mutations": 1 if eligible and namespace == "PRODUCTION" else 0,
        "test_simulation": eligible and namespace == "TEST",
        "production_mutated": eligible and namespace == "PRODUCTION",
        "truth_effect": "NONE",
        "evidence_effect": "NONE",
        "authority_effect": (
            "EDGE_EXECUTION_ONLY"
            if eligible and namespace == "PRODUCTION"
            else "NONE"
        ),
    }
    edge["execution_digest"] = content_address("kc144.p41.third-edge", edge)
    residuals: list[str] = []
    if not source["cohort_basis"]["exact_original_enumeration_claimed"]:
        residuals.append("ORIGINAL_29_HEAD_ENUMERATION_WITNESS_ABSENT")
    if cohort["status"] != "COHORT_READY":
        residuals.append("NONLEAKING_HELDOUT_COHORT_PENDING")
    if ic10["status"] != "INDEPENDENT_RETURN_VERIFIED":
        residuals.append("INDEPENDENT_IC10_RETURN_PENDING")
    if edge["execution_status"] == "HELD_NOT_EXECUTED":
        residuals.append("THIRD_EDGE_HELD")
    payloads = (
        parent,
        source["source_predecessor"],
        source,
        repositories,
        cohort,
        ic10,
        edge,
        parallel,
        {
            "return": P41_ROUTE[-1],
            "next_seed": P41_NEXT_SEED,
            "edge_execution_digest": edge["execution_digest"],
        },
    )
    receipts = [
        _lane_receipt(index, lane, payload)
        for index, (lane, payload) in enumerate(zip(P41_LANES, payloads), 1)
    ]
    state = {
        "schema": "KC144.P41.StateDelta.V1",
        "public_parent_result_id": PUBLIC_P40_RESULT_ID,
        "source_sibling_result_id": SOURCE_SIBLING_RESULT_ID,
        "source_heads_rehydrated": source["census"]["connector_rehydrated"],
        "net_source_heads_closed": source["census"]["net_heads_closed"],
        "public_repository_trees_bound": repositories["repository_count"],
        "heldout_outcomes": cohort["event_count"],
        "required_heldout_outcomes": cohort["required_event_count"],
        "independent_ic10_returns": ic10["accepted_return_count"],
        "third_edge": edge["execution_status"],
        "canonical_graph_mutations": edge["canonical_graph_mutations"],
        "parallel_p41_merges": 0,
        "deployments": 0,
        "promotions": 0,
        "production_mutated": edge["production_mutated"],
        "truth_effect": "NONE",
        "evidence_effect": "SOURCE_RETRIEVAL_COMMITMENTS_ONLY",
        "authority_effect": edge["authority_effect"],
        "global_release": "EXECUTED" if edge["production_mutated"] else "HOLD",
        "residuals": sorted(residuals),
        "return": P41_ROUTE[-1],
        "next_seed": P41_NEXT_SEED,
    }
    state["delta_id"] = content_address("kc144.p41.state-delta", state)
    body = {
        "schema": "KC144.P41.Macrocycle.V1",
        "contract_digest": contract["contract_digest"],
        "namespace": namespace,
        "public_parent_binding": parent,
        "source_manifest": source,
        "repository_forest": repositories,
        "heldout_cohort": cohort,
        "ic10_registry": registry,
        "edge_candidate": candidate,
        "ic10_evaluation": ic10,
        "third_edge_execution": edge,
        "parallel_lineage": parallel,
        "lane_receipts": receipts,
        "state": state,
    }
    return {**body, "envelope_digest": content_address("kc144.p41.macrocycle", body)}


def verify_p41_cycle(value: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    body = {key: item for key, item in value.items() if key != "envelope_digest"}
    if value.get("schema") != "KC144.P41.Macrocycle.V1":
        errors.append("E_SCHEMA")
    if value.get("envelope_digest") != content_address("kc144.p41.macrocycle", body):
        errors.append("E_ENVELOPE_DIGEST")
    if value.get("contract_digest") != p41_contract()["contract_digest"]:
        errors.append("E_CONTRACT")
    if value.get("public_parent_binding") != p41_public_parent():
        errors.append("E_PUBLIC_PARENT")
    if value.get("source_manifest") != p41_source_manifest():
        errors.append("E_SOURCE_MANIFEST")
    if value.get("repository_forest") != p41_repository_forest():
        errors.append("E_REPOSITORY_FOREST")
    if value.get("parallel_lineage") != p41_parallel_lineage():
        errors.append("E_PARALLEL_LINEAGE")
    cohort = value.get("heldout_cohort", {})
    cohort_body = {
        key: item for key, item in cohort.items() if key != "cohort_root"
    }
    if cohort.get("cohort_root") != content_address(
        "kc144.p41.heldout-cohort", cohort_body
    ):
        errors.append("E_COHORT_ROOT")
    if cohort.get("labels_revealed") != 0 or cohort.get(
        "continuation_events_admitted"
    ) != 0:
        errors.append("E_COHORT_LEAK")
    candidate = value.get("edge_candidate", {})
    candidate_body = {
        key: item
        for key, item in candidate.items()
        if key != "edge_candidate_root"
    }
    if candidate.get("edge_candidate_root") != content_address(
        "kc144.p41.edge-candidate", candidate_body
    ):
        errors.append("E_EDGE_CANDIDATE")
    edge = value.get("third_edge_execution", {})
    edge_body = {
        key: item for key, item in edge.items() if key != "execution_digest"
    }
    if edge.get("execution_digest") != content_address(
        "kc144.p41.third-edge", edge_body
    ):
        errors.append("E_EDGE_DIGEST")
    eligible = edge.get("eligibility") == "ELIGIBLE"
    if eligible and (
        edge.get("source_gate") != "PASS"
        or edge.get("repository_gate") != "PASS"
        or edge.get("heldout_gate") != "COHORT_READY"
        or edge.get("ic10_gate") != "INDEPENDENT_RETURN_VERIFIED"
    ):
        errors.append("E_EDGE_WITHOUT_GATES")
    if not eligible and (
        edge.get("execution_count") != 0
        or edge.get("canonical_graph_mutations") != 0
        or edge.get("production_mutated") is not False
    ):
        errors.append("E_HELD_EDGE_MUTATION")
    if value.get("namespace") == "TEST" and (
        edge.get("canonical_graph_mutations") != 0
        or edge.get("production_mutated")
    ):
        errors.append("E_TEST_PRODUCTION_MUTATION")
    state = value.get("state", {})
    if (
        state.get("parallel_p41_merges") != 0
        or state.get("deployments") != 0
        or state.get("promotions") != 0
        or state.get("truth_effect") != "NONE"
    ):
        errors.append("E_PROTECTED_STATE_ESCALATION")
    receipts = value.get("lane_receipts", [])
    if len(receipts) != len(P41_LANES):
        errors.append("E_LANE_CENSUS")
    else:
        for index, (lane, receipt) in enumerate(zip(P41_LANES, receipts), 1):
            receipt_body = {
                key: item
                for key, item in receipt.items()
                if key != "receipt_id"
            }
            if (
                receipt.get("lane_id") != f"P41.L{index:02d}"
                or receipt.get("lane") != lane
                or receipt.get("receipt_id")
                != content_address("kc144.p41.lane-receipt", receipt_body)
            ):
                errors.append("E_LANE_RECEIPT")
    try:
        replay = compile_p41_cycle(
            heldout_events=value.get("heldout_cohort", {}).get("events", []),
            ic10_registry=value.get("ic10_registry"),
            ic10_returns=value.get("ic10_evaluation", {}).get(
                "accepted_returns", []
            )
            + [
                {
                    "return_digest": row.get("return_digest"),
                }
                for row in value.get("ic10_evaluation", {}).get(
                    "rejected_returns", []
                )
            ],
            namespace=str(value.get("namespace", "")),
        )
        # Rejected return bodies are intentionally not retained. Cold replay is
        # exact when no rejected inputs were supplied.
        if (
            not value.get("ic10_evaluation", {}).get("rejected_returns")
            and replay != dict(value)
        ):
            errors.append("E_COLD_REPLAY")
    except (P41RuntimeError, TypeError, ValueError):
        errors.append("E_COLD_REPLAY")
    return {
        "schema": "KC144.P41.MacrocycleVerification.V1",
        "verdict": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)),
        "envelope_digest": value.get("envelope_digest"),
    }


def compile_p41_release(
    output_directory: str | Path,
    *,
    implementation_commit: str,
    implementation_tree: str,
) -> dict[str, Any]:
    if not GIT_SHA_RE.fullmatch(implementation_commit):
        raise P41RuntimeError("implementation_commit must be a Git SHA")
    if not GIT_SHA_RE.fullmatch(implementation_tree):
        raise P41RuntimeError("implementation_tree must be a Git tree SHA")
    contract = p41_contract()
    source = p41_source_manifest()
    repositories = p41_repository_forest()
    cohort = freeze_heldout_cohort()
    parallel = p41_parallel_lineage()
    cycle = compile_p41_cycle()
    verification = verify_p41_cycle(cycle)
    release_core = {
        "schema": "KC144.P41.Release.V1",
        "release_id": "KC144_P41_SOURCE_TREE_COHORT_CANDIDATE_V1",
        "status": "CANDIDATE_HOLD",
        "implementation": {
            "repository": "demeet2k/guild-hall",
            "commit": implementation_commit,
            "tree": implementation_tree,
        },
        "public_parent_result_id": PUBLIC_P40_RESULT_ID,
        "public_parent_release_digest": PUBLIC_P40_RELEASE_DIGEST,
        "source_sibling_result_id": SOURCE_SIBLING_RESULT_ID,
        "source_manifest_root": source["manifest_root"],
        "repository_forest_root": repositories["forest_root"],
        "heldout_cohort_root": cohort["cohort_root"],
        "parallel_lineage_digest": parallel["lineage_digest"],
        "contract_digest": contract["contract_digest"],
        "envelope_digest": cycle["envelope_digest"],
        "verification_verdict": verification["verdict"],
        "source_heads_rehydrated": 29,
        "net_source_heads_closed": 22,
        "source_bodies_published": 0,
        "public_repository_trees_bound": 4,
        "heldout_outcomes": 0,
        "independent_ic10_returns": 0,
        "third_edge": "HELD_NOT_EXECUTED",
        "canonical_graph_mutations": 0,
        "parallel_p41_merges": 0,
        "production_authority": "HOLD",
        "production_mutated": False,
        "truth_effect": "NONE",
        "next_seed": P41_NEXT_SEED,
    }
    release_digest = content_address("kc144.p41.release", release_core)
    release = {
        **release_core,
        "release_digest": release_digest,
        "result_id": "KC144.P41.CANDIDATE::"
        + release_digest.removeprefix("sha256:")[:24],
    }
    artifacts = {
        "p41_contract_v1.json": contract,
        "p41_source_commitments_v1.json": source,
        "p41_repository_forest_v1.json": repositories,
        "p41_heldout_cohort_v1.json": cohort,
        "p41_parallel_lineage_v1.json": parallel,
        "p41_macrocycle_v1.json": cycle,
        "p41_verification_v1.json": verification,
        "p41_release_v1.json": release,
    }
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    for name, artifact in artifacts.items():
        (output / name).write_text(
            json.dumps(artifact, indent=2, ensure_ascii=False, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
    checksum_lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}"
        for path in sorted(output.glob("*.json"))
    ]
    (output / "SHA256SUMS").write_text(
        "\n".join(checksum_lines) + "\n", encoding="utf-8"
    )
    return release
