from __future__ import annotations

"""Fail-closed audit for the four elemental repository identity surfaces.

Repository labels are routing addresses, not proof of distinct runtime identity.
The audit therefore promotes collisions to explicit HOLD evidence instead of
manufacturing four adapter profiles from four repository names.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

ARTIFACT = "ATHENA.SYNAPSE.ELEMENTAL.IDENTITY.V1"
EXPECTED_NODES = {"water", "air", "earth", "fire"}
HOLD = "HOLD_IDENTITY_DISCRIMINATOR_REQUIRED"
REQUIRED_DISCRIMINATORS = {
    "repository", "revision", "stable_native_node_id", "role_source_ref",
    "native_event_or_packet_type", "deterministic_identity_rule",
    "return_or_reconstruction_rule", "truth_or_authority_ceiling", "runtime_witness",
}


def _dup_groups(rows: list[Mapping[str, Any]], key: str) -> list[list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        value = str(row.get(key) or "")
        if value:
            groups[value].append(str(row.get("node_id") or ""))
    return sorted(sorted(nodes) for nodes in groups.values() if len(nodes) > 1)


def audit_identity(registry: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    if registry.get("artifact") != ARTIFACT:
        errors.append({"code": "BAD_ARTIFACT"})
    rows = registry.get("nodes")
    if not isinstance(rows, list):
        errors.append({"code": "NODES_REQUIRED"})
        rows = []

    by_id = {str(row.get("node_id") or ""): row for row in rows if isinstance(row, Mapping)}
    if set(by_id) != EXPECTED_NODES:
        errors.append({"code": "ELEMENT_SET_MISMATCH", "observed": sorted(by_id)})
    if len(rows) != len(by_id):
        errors.append({"code": "DUPLICATE_NODE_ID"})

    repos = []
    for node_id, row in sorted(by_id.items()):
        repository = str(row.get("repository") or "")
        revision = str(row.get("revision") or "")
        tree_sha = str(row.get("tree_sha") or "")
        repos.append(repository)
        if "/" not in repository:
            errors.append({"code": "BAD_REPOSITORY", "node_id": node_id})
        for field, value in (("revision", revision), ("tree_sha", tree_sha)):
            if len(value) != 40:
                errors.append({"code": "BAD_GIT_SHA", "node_id": node_id, "field": field})
        if row.get("admission") != HOLD:
            errors.append({"code": "ELEMENT_NOT_HELD", "node_id": node_id})
    if len(repos) != len(set(repos)):
        errors.append({"code": "DUPLICATE_REPOSITORY_ADDRESS"})

    native = registry.get("common_native_config")
    kernel = registry.get("common_runtime_kernel")
    if not isinstance(native, Mapping) or native.get("path") != ".mcp.json" or len(str(native.get("blob_sha") or "")) != 40:
        errors.append({"code": "COMMON_NATIVE_CONFIG_REQUIRED"})
    if not isinstance(kernel, Mapping) or len(kernel) < 4 or any(len(str(value)) != 40 for value in kernel.values()):
        errors.append({"code": "COMMON_RUNTIME_KERNEL_REQUIRED"})

    tree_dups = _dup_groups(rows, "tree_sha")
    crystal_dups = _dup_groups(rows, "crystal_tree_sha")
    data_dups = _dup_groups(rows, "data_tree_sha")
    if ["fire", "water"] not in tree_dups:
        errors.append({"code": "EXPECTED_FIRE_WATER_TREE_MIRROR_MISSING", "groups": tree_dups})
    if ["earth", "fire", "water"] not in crystal_dups:
        errors.append({"code": "EXPECTED_CRYSTAL_COLLISION_MISSING", "groups": crystal_dups})

    collisions = registry.get("collision_groups")
    if not isinstance(collisions, list):
        errors.append({"code": "COLLISION_GROUPS_REQUIRED"})
        collisions = []
    collision_kinds = {str(row.get("kind") or "") for row in collisions if isinstance(row, Mapping)}
    for required in {
        "NATIVE_CONFIG_IDENTITY_COLLISION", "RUNTIME_KERNEL_COLLISION",
        "EXACT_REPOSITORY_TREE_MIRROR", "CRYSTAL_SUBTREE_COLLISION",
    }:
        if required not in collision_kinds:
            errors.append({"code": "MISSING_COLLISION_CLASS", "kind": required})

    manifest = registry.get("required_discriminator_manifest")
    fields = set(manifest.get("fields") or []) if isinstance(manifest, Mapping) else set()
    if not isinstance(manifest, Mapping) or manifest.get("required_before_profile_admission") is not True:
        errors.append({"code": "DISCRIMINATOR_GATE_REQUIRED"})
    if fields != REQUIRED_DISCRIMINATORS:
        errors.append({"code": "DISCRIMINATOR_FIELD_SET_MISMATCH", "observed": sorted(fields)})
    forbidden = set(manifest.get("must_not_use_alone") or []) if isinstance(manifest, Mapping) else set()
    if not {"repository_name", "element_name", "shared_crystal_address", "shared_kernel_blob"}.issubset(forbidden):
        errors.append({"code": "WEAK_IDENTITY_KEYS_NOT_FORBIDDEN"})

    schemas = registry.get("shared_nervous_system_contracts")
    if not isinstance(schemas, Mapping):
        errors.append({"code": "SHARED_CONTRACT_EVIDENCE_REQUIRED"})
    else:
        synapse = schemas.get("synapse_schema") or {}
        if synapse.get("semantic_kind") != "LEGACY_RELATION_EDGE":
            errors.append({"code": "LEGACY_SYNAPSE_TYPE_NOT_DISTINGUISHED"})
        if synapse.get("blob_sha") != "b938a55d8d7f06c459991a330cd1ccf4fa119d76":
            errors.append({"code": "LEGACY_SYNAPSE_BLOB_DRIFT"})

    if tree_dups:
        warnings.append({"code": "CONTENT_MIRROR_GROUPS", "groups": tree_dups})
    if crystal_dups:
        warnings.append({"code": "CRYSTAL_SUBTREE_COLLISIONS", "groups": crystal_dups})

    return {
        "artifact": "ATHENA.SYNAPSE.ELEMENTAL.IDENTITY.AUDIT.V1",
        "ok": not errors,
        "node_count": len(by_id),
        "repository_count": len(set(repos)),
        "distinct_tree_count": len({str(row.get('tree_sha') or '') for row in rows if isinstance(row, Mapping)}),
        "tree_mirror_groups": tree_dups,
        "crystal_collision_groups": crystal_dups,
        "data_collision_groups": data_dups,
        "errors": errors,
        "warnings": warnings,
        "standing": "HOLD_ELEMENT_PROFILE_INFERENCE" if not errors else "INVALID_IDENTITY_EVIDENCE",
        "laws": [
            "REPOSITORY_ID != NATIVE_RUNTIME_IDENTITY",
            "SAME_TREE => CONTENT_IDENTITY_NOT_ROLE_IDENTITY",
            "SHARED_CRYSTAL_ADDRESS != UNIQUE_NODE_IDENTITY",
            "LEGACY_SYNAPSE_EDGE != CORE_SYNAPSE_PACKET",
            "IDENTITY_COLLISION => HOLD_UNTIL_TYPED_DISCRIMINATOR",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="registry/ATHENA_SYNAPSE_ELEMENTAL_IDENTITY_V1.json")
    args = parser.parse_args(argv)
    registry = json.loads(Path(args.path).read_text(encoding="utf-8"))
    result = audit_identity(registry)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
