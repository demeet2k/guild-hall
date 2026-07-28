from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from .agent_receipts import canonical_bytes, content_address


PUBLIC_P36_RESULT_ID = "KC144.P36.CANDIDATE::2dc88c9f2bf39ccb97e883f2"
PUBLIC_P36_RELEASE_DIGEST = (
    "sha256:2dc88c9f2bf39ccb97e883f2c10a2269a628cadf96a50097d4f9fb1a2d808782"
)
PUBLIC_P36_IMPLEMENTATION_COMMIT = "f35697e4baf8afa00f1a2a91a1eff18aa8acfe5f"
PUBLIC_P36_IMPLEMENTATION_TREE = "30377647415d9df054da9db8b536d4363d43d702"
PUBLIC_P36_RELEASE_COMMIT = "9d64c5d9d9f29af7f5d310f9720f84bdb886a913"
PUBLIC_P36_RELEASE_TREE = "fc4b50ca1bb3d5f27c5baa616092304c1d48916d"

SOURCE_P37_RESULT_ID = "KC144.P37::039d3622874ac1ef067ce4da"
SOURCE_P37_RESULT_DIGEST = (
    "sha256:039d3622874ac1ef067ce4da0cec4ea4c2ba4016881cb4b84abdf7dd43140d84"
)
SOURCE_P37_PARENT_RESULT_ID = "KC144.P36::f40dc654ea7fc32651f1ebd6"
SOURCE_P37_RELEASE_ARCHIVE_SHA256 = (
    "sha256:4bf1869290a388a4adf332458bd82232c8f592b09c6d49b5d8d98fe5cc8076a2"
)
SOURCE_P37_IMPLEMENTATION_ARCHIVE_SHA256 = (
    "sha256:2bda9785f0c519c09b155b7cc17d3128914f8bf42666dd511852ce55b881b158"
)
SOURCE_P37_MANIFEST_SHA256 = (
    "sha256:d0ffa0bdab13e28f8c6de218d91256106a46bf44165c6f47f8a43e5f38d51a9f"
)
SOURCE_P37_SEAL_SHA256 = (
    "sha256:9ec2319d3123e8f82f89b3151995fbfd59eb5b255bae54274dea933a2831078d"
)
META_ATLAS_V10_SHA256 = (
    "sha256:ea0c786a66493c97037ff3674355cc309bf8bb3d2b18483b8054d00587f2a16d"
)

P35_EXACT_FILES = {
    "action_crosswalk_360.ndjson": {
        "rows": 360,
        "sha256": "sha256:33ecff871f5fc570f54b83727e3e1ab7243dcfb42be806ee645b80c6aef3097f",
        "identity_field": "crosswalk_id",
        "identity_prefix": "KC144.P35.CROSSWALK.",
    },
    "carrier_subscriptions_37.ndjson": {
        "rows": 37,
        "sha256": "sha256:72626390853bef0d834094acd770f9708fb12900fe95543522ca17dcb37897a1",
        "identity_field": "carrier_id",
        "identity_prefix": "F",
    },
    "gid_subscriptions_144.ndjson": {
        "rows": 144,
        "sha256": "sha256:ad7b281b8984328bf42eaf37ba6164c97a6573a1fd43af6585a1a129f1b534dc",
        "identity_field": "gid",
        "identity_prefix": "GID",
    },
}
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


class ReconciliationError(ValueError):
    pass


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _read_ndjson(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ReconciliationError(f"{path.name}:{number}: blank row")
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ReconciliationError(
                f"{path.name}:{number}: invalid JSON"
            ) from exc
        if not isinstance(value, dict):
            raise ReconciliationError(f"{path.name}:{number}: row is not an object")
        rows.append(value)
    return rows


def source_p37_capsule() -> dict[str, Any]:
    body = {
        "schema": "KC144.P37.ImmutableSiblingCapsule.V1",
        "result_id": SOURCE_P37_RESULT_ID,
        "result_digest": SOURCE_P37_RESULT_DIGEST,
        "source_parent_result_id": SOURCE_P37_PARENT_RESULT_ID,
        "release_archive_sha256": SOURCE_P37_RELEASE_ARCHIVE_SHA256,
        "implementation_archive_sha256": SOURCE_P37_IMPLEMENTATION_ARCHIVE_SHA256,
        "manifest_sha256": SOURCE_P37_MANIFEST_SHA256,
        "seal_sha256": SOURCE_P37_SEAL_SHA256,
        "meta_atlas": {
            "id": "KC144.META-ATLAS.V10",
            "sha256": META_ATLAS_V10_SHA256,
            "stations": 144,
            "undirected_logical_edges": 310,
        },
        "verified_census": {
            "repository_tests": {"passed": 484, "total": 484},
            "p37_tests": {"passed": 76, "total": 76},
            "receipts": {"passed": 627, "total": 627},
            "action_subscriptions_preserved": 360,
            "source_bodies_admitted": 3,
            "proposal_edges_executed": 1,
            "canonical_edges_executed": 0,
            "real_outcomes": 0,
            "independent_ic10_returns": 0,
        },
        "release_state": "HOLD",
        "truth_effect": "NONE",
        "evidence_effect": "NONE",
        "authority_effect": "NONE",
    }
    return {
        **body,
        "capsule_digest": content_address("kc144.p37.sibling-capsule", body),
    }


def p37_public_reconciliation() -> dict[str, Any]:
    source = source_p37_capsule()
    body = {
        "schema": "KC144.P37.PublicLineageReconciliation.V1",
        "public_branch_parent": {
            "result_id": PUBLIC_P36_RESULT_ID,
            "release_digest": PUBLIC_P36_RELEASE_DIGEST,
            "implementation_commit": PUBLIC_P36_IMPLEMENTATION_COMMIT,
            "implementation_tree": PUBLIC_P36_IMPLEMENTATION_TREE,
            "release_commit": PUBLIC_P36_RELEASE_COMMIT,
            "release_tree": PUBLIC_P36_RELEASE_TREE,
        },
        "source_sibling": {
            "result_id": source["result_id"],
            "result_digest": source["result_digest"],
            "source_parent_result_id": source["source_parent_result_id"],
            "capsule_digest": source["capsule_digest"],
        },
        "relation": "TYPED_SIBLING_IMPORT",
        "lineage_convergence": "NON_COLLAPSING_RECONCILIATION",
        "laws": [
            "PUBLIC_P36_REMAINS_THE_PUBLIC_BRANCH_PARENT",
            "SOURCE_P37_RETAINS_ITS_DISTINCT_SOURCE_PARENT",
            "SOURCE_P37_IS_IMPORTED_BY_IMMUTABLE_COMMITMENT_NOT_REPARENTED",
            "CONVERGENCE_CREATES_A_NEW_P38_CHILD_OF_PUBLIC_P36",
            "SOURCE_ATTESTATION_IS_NOT_INDEPENDENT_AUTHORITY",
        ],
        "truth_effect": "NONE",
        "evidence_effect": "NONE",
        "authority_effect": "NONE",
    }
    if body["public_branch_parent"]["result_id"] == SOURCE_P37_PARENT_RESULT_ID:
        raise ReconciliationError("the two P36 lineages unexpectedly collapsed")
    return {
        **body,
        "reconciliation_digest": content_address(
            "kc144.p37.public-lineage-reconciliation", body
        ),
    }


def expected_p35_registry_binding() -> dict[str, Any]:
    files = [
        {
            "name": name,
            "rows": descriptor["rows"],
            "sha256": descriptor["sha256"],
        }
        for name, descriptor in sorted(P35_EXACT_FILES.items())
    ]
    body = {
        "schema": "KC144.P35.ExactSubscriptionRegistryBinding.V1",
        "state": "EXPECTED_EXACT_BYTES",
        "files": files,
        "counts": {
            "action_subscriptions": 360,
            "gid_subscriptions": 144,
            "carrier_subscriptions": 37,
            "total_rows": 541,
        },
        "private_source_metadata_included": False,
        "truth_effect": "NONE",
        "authority_effect": "NONE",
    }
    return {
        **body,
        "binding_digest": content_address(
            "kc144.p35.exact-subscription-registry", body
        ),
    }


def bind_exact_p35_registry(directory: str | Path) -> dict[str, Any]:
    root = Path(directory)
    file_receipts: list[dict[str, Any]] = []
    row_commitments: list[str] = []
    all_errors: list[str] = []
    for name, descriptor in sorted(P35_EXACT_FILES.items()):
        path = root / name
        if not path.is_file():
            raise ReconciliationError(f"missing exact registry file: {name}")
        raw = path.read_bytes()
        rows = _read_ndjson(path)
        errors: list[str] = []
        actual_sha = _sha256_bytes(raw)
        if actual_sha != descriptor["sha256"]:
            errors.append("E_EXACT_FILE_SHA256")
        if len(rows) != descriptor["rows"]:
            errors.append("E_EXACT_ROW_CENSUS")
        identity_field = str(descriptor["identity_field"])
        identities = [str(row.get(identity_field, "")) for row in rows]
        if len(set(identities)) != len(identities) or any(
            not identity.startswith(str(descriptor["identity_prefix"]))
            for identity in identities
        ):
            errors.append("E_ROW_IDENTITY")
        if name == "action_crosswalk_360.ndjson":
            if any(row.get("truth_effect") != "NONE" for row in rows):
                errors.append("E_TRUTH_ESCALATION")
            if any(
                row.get("matching_production_events_observed") != 0
                for row in rows
            ):
                errors.append("E_UNSUPPORTED_PRODUCTION_EVENT")
            if any(
                row.get("state_after")
                != "SUBSCRIBED_WAITING_FOR_MATCHING_PRODUCTION_EVENT"
                for row in rows
            ):
                errors.append("E_SUBSCRIPTION_STATE")
        row_hashes = [
            _sha256_bytes(canonical_bytes(row))
            for row in rows
        ]
        row_commitments.extend(
            f"{name}:{index + 1}:{digest}"
            for index, digest in enumerate(row_hashes)
        )
        file_receipts.append(
            {
                "name": name,
                "rows": len(rows),
                "sha256": actual_sha,
                "row_root": content_address(
                    "kc144.p35.registry-file-rows", row_hashes
                ),
                "errors": sorted(errors),
                "verdict": "PASS" if not errors else "FAIL",
            }
        )
        all_errors.extend(f"{name}:{error}" for error in errors)
    body = {
        "schema": "KC144.P35.ExactSubscriptionRegistryBinding.V1",
        "state": "EXACT_BYTES_VERIFIED" if not all_errors else "REJECTED",
        "files": file_receipts,
        "counts": {
            "action_subscriptions": 360,
            "gid_subscriptions": 144,
            "carrier_subscriptions": 37,
            "total_rows": len(row_commitments),
        },
        "row_commitment_root": content_address(
            "kc144.p35.registry-all-rows", row_commitments
        ),
        "private_source_metadata_included": False,
        "truth_effect": "NONE",
        "authority_effect": "NONE",
        "errors": sorted(all_errors),
    }
    result = {
        **body,
        "binding_digest": content_address(
            "kc144.p35.exact-subscription-registry", body
        ),
    }
    if all_errors:
        raise ReconciliationError(
            "exact P35 registry verification failed: " + ", ".join(all_errors)
        )
    return result


def verify_p35_registry_binding(value: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if value.get("schema") != "KC144.P35.ExactSubscriptionRegistryBinding.V1":
        errors.append("E_SCHEMA")
    body = {key: item for key, item in value.items() if key != "binding_digest"}
    if value.get("binding_digest") != content_address(
        "kc144.p35.exact-subscription-registry", body
    ):
        errors.append("E_BINDING_DIGEST")
    if value.get("state") not in {"EXPECTED_EXACT_BYTES", "EXACT_BYTES_VERIFIED"}:
        errors.append("E_STATE")
    if value.get("counts") != {
        "action_subscriptions": 360,
        "gid_subscriptions": 144,
        "carrier_subscriptions": 37,
        "total_rows": 541,
    }:
        errors.append("E_CENSUS")
    if (
        value.get("private_source_metadata_included") is not False
        or value.get("truth_effect") != "NONE"
        or value.get("authority_effect") != "NONE"
    ):
        errors.append("E_EFFECT_OR_PRIVACY")
    files = value.get("files", [])
    by_name = {
        str(row.get("name")): row for row in files if isinstance(row, Mapping)
    }
    if set(by_name) != set(P35_EXACT_FILES):
        errors.append("E_FILE_SET")
    for name, descriptor in P35_EXACT_FILES.items():
        row = by_name.get(name, {})
        if (
            row.get("rows") != descriptor["rows"]
            or row.get("sha256") != descriptor["sha256"]
        ):
            errors.append("E_EXACT_FILE_IDENTITY")
        if value.get("state") == "EXACT_BYTES_VERIFIED" and (
            not DIGEST_PATTERN.fullmatch(str(row.get("row_root", "")))
            or row.get("errors") != []
            or row.get("verdict") != "PASS"
        ):
            errors.append("E_FILE_VERIFICATION_RECEIPT")
    if value.get("state") == "EXACT_BYTES_VERIFIED":
        if not DIGEST_PATTERN.fullmatch(str(value.get("row_commitment_root", ""))):
            errors.append("E_ROW_COMMITMENT_ROOT")
        if value.get("errors") != []:
            errors.append("E_BINDING_ERRORS")
    return {
        "schema": "KC144.P35.ExactSubscriptionRegistryBindingVerification.V1",
        "state": value.get("state"),
        "verdict": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)),
    }


def verify_reconciliation(value: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if value.get("schema") != "KC144.P37.PublicLineageReconciliation.V1":
        errors.append("E_SCHEMA")
    body = {key: item for key, item in value.items() if key != "reconciliation_digest"}
    expected = content_address("kc144.p37.public-lineage-reconciliation", body)
    if value.get("reconciliation_digest") != expected:
        errors.append("E_RECONCILIATION_DIGEST")
    public_parent = value.get("public_branch_parent", {})
    sibling = value.get("source_sibling", {})
    if public_parent.get("result_id") != PUBLIC_P36_RESULT_ID:
        errors.append("E_PUBLIC_PARENT")
    if sibling.get("result_id") != SOURCE_P37_RESULT_ID:
        errors.append("E_SOURCE_SIBLING")
    if sibling.get("source_parent_result_id") == public_parent.get("result_id"):
        errors.append("E_LINEAGE_COLLAPSE")
    if value.get("authority_effect") != "NONE":
        errors.append("E_AUTHORITY_ESCALATION")
    return {
        "schema": "KC144.P37.PublicLineageReconciliationVerification.V1",
        "verdict": "PASS" if not errors else "FAIL",
        "errors": sorted(errors),
    }
