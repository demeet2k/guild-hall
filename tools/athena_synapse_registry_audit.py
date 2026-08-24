from __future__ import annotations

"""Fail-closed admission audit for the ATHENA Synapse node registry.

The registry is topology/admission evidence, not a discovery oracle. This tool
prevents profile collisions and standing inflation without contacting remote
repositories or inventing capabilities for manifestless nodes.
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any, Mapping

ARTIFACT = "ATHENA.SYNAPSE.NODE.REGISTRY.V1"
ADMISSION = {"CANONICAL_ABI", "PROPOSED_ADAPTER", "ACTIVE_ADAPTER", "MANIFEST_REQUIRED", "HOLD"}
_PROFILE_RE = re.compile(r"^[A-Z][A-Z0-9_.-]{2,127}$")
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def _strings(value: Any) -> bool:
    return isinstance(value, list) and len(value) == len(set(value)) and all(isinstance(x, str) and bool(x.strip()) for x in value)


def audit_registry(registry: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    nodes = registry.get("nodes")
    if registry.get("artifact") != ARTIFACT:
        errors.append({"code": "BAD_ARTIFACT", "detail": f"artifact must be {ARTIFACT}"})
    if not isinstance(nodes, list) or not nodes:
        errors.append({"code": "NODES_REQUIRED", "detail": "registry.nodes must be a non-empty array"})
        nodes = []

    node_owner: dict[str, int] = {}
    repo_owner: dict[str, str] = {}
    profile_owner: dict[str, str] = {}
    status_counts: dict[str, int] = {}

    for index, raw in enumerate(nodes):
        if not isinstance(raw, Mapping):
            errors.append({"code": "NODE_NOT_OBJECT", "index": index})
            continue
        node_id = str(raw.get("node_id") or "").strip()
        repository = str(raw.get("repository") or "").strip()
        branch = str(raw.get("default_branch") or "").strip()
        role = str(raw.get("role") or "").strip()
        status = str(raw.get("admission_status") or "").strip()
        profiles = raw.get("synapse_profiles")
        evidence = raw.get("evidence_refs")
        manifest_ref = raw.get("manifest_ref")

        if not node_id:
            errors.append({"code": "NODE_ID_REQUIRED", "index": index})
        elif node_id in node_owner:
            errors.append({"code": "DUPLICATE_NODE_ID", "node_id": node_id, "first_index": node_owner[node_id], "index": index})
        else:
            node_owner[node_id] = index

        if not _REPO_RE.fullmatch(repository):
            errors.append({"code": "BAD_REPOSITORY", "node_id": node_id, "repository": repository})
        elif repository in repo_owner:
            errors.append({"code": "DUPLICATE_REPOSITORY", "repository": repository, "nodes": [repo_owner[repository], node_id]})
        else:
            repo_owner[repository] = node_id

        if not branch:
            errors.append({"code": "DEFAULT_BRANCH_REQUIRED", "node_id": node_id})
        if not role:
            errors.append({"code": "ROLE_REQUIRED", "node_id": node_id})
        if status not in ADMISSION:
            errors.append({"code": "BAD_ADMISSION_STATUS", "node_id": node_id, "status": status})
        else:
            status_counts[status] = status_counts.get(status, 0) + 1

        if not _strings(profiles):
            errors.append({"code": "BAD_PROFILE_LIST", "node_id": node_id})
            profiles = []
        if not _strings(evidence):
            errors.append({"code": "BAD_EVIDENCE_LIST", "node_id": node_id})
            evidence = []
        if manifest_ref is not None and (not isinstance(manifest_ref, str) or not manifest_ref.strip()):
            errors.append({"code": "BAD_MANIFEST_REF", "node_id": node_id})

        for profile in profiles:
            if not _PROFILE_RE.fullmatch(profile):
                errors.append({"code": "BAD_PROFILE", "node_id": node_id, "profile": profile})
            if profile in profile_owner:
                errors.append({"code": "PROFILE_COLLISION", "profile": profile, "nodes": [profile_owner[profile], node_id]})
            else:
                profile_owner[profile] = node_id

        if status == "MANIFEST_REQUIRED":
            if profiles:
                errors.append({"code": "UNADMITTED_PROFILE_CLAIM", "node_id": node_id, "profiles": profiles})
            if manifest_ref is not None:
                errors.append({"code": "MANIFEST_REQUIRED_WITH_MANIFEST_REF", "node_id": node_id})
            if evidence:
                warnings.append({"code": "UNADJUDICATED_EVIDENCE_ON_MANIFEST_REQUIRED_NODE", "node_id": node_id})
        elif status == "PROPOSED_ADAPTER":
            if not profiles:
                errors.append({"code": "PROPOSED_ADAPTER_NEEDS_PROFILE", "node_id": node_id})
            if not evidence:
                errors.append({"code": "PROPOSED_ADAPTER_NEEDS_EVIDENCE", "node_id": node_id})
            if manifest_ref is not None:
                warnings.append({"code": "PROPOSED_ADAPTER_MANIFEST_NOT_ACTIVE_PROOF", "node_id": node_id})
        elif status == "ACTIVE_ADAPTER":
            if not profiles:
                errors.append({"code": "ACTIVE_ADAPTER_NEEDS_PROFILE", "node_id": node_id})
            if not evidence:
                errors.append({"code": "ACTIVE_ADAPTER_NEEDS_EVIDENCE", "node_id": node_id})
            if manifest_ref is None:
                errors.append({"code": "ACTIVE_ADAPTER_NEEDS_MANIFEST", "node_id": node_id})
        elif status == "CANONICAL_ABI":
            if not evidence or manifest_ref is None:
                errors.append({"code": "CANONICAL_ABI_NEEDS_MANIFEST_AND_EVIDENCE", "node_id": node_id})
            if profiles:
                warnings.append({"code": "CANONICAL_ABI_PROFILE_IS_NOT_NODE_ADAPTER_PROOF", "node_id": node_id})
        elif status == "HOLD" and profiles:
            warnings.append({"code": "HOLD_PROFILE_NOT_ACTIVE", "node_id": node_id, "profiles": profiles})

    if status_counts.get("CANONICAL_ABI", 0) != 1:
        errors.append({"code": "CANONICAL_ABI_CARDINALITY", "count": status_counts.get("CANONICAL_ABI", 0)})

    return {
        "artifact": "ATHENA.SYNAPSE.NODE.REGISTRY.AUDIT.V1",
        "ok": not errors,
        "node_count": len(nodes),
        "profile_count": len(profile_owner),
        "status_counts": dict(sorted(status_counts.items())),
        "errors": errors,
        "warnings": warnings,
        "laws": [
            "PROPOSED_ADAPTER != ACTIVE_ADAPTER",
            "MANIFEST_REQUIRED => NO_PROFILE_CLAIM",
            "ACTIVE_ADAPTER => MANIFEST_AND_EVIDENCE_REQUIRED",
            "PROFILE_IDENTITY_IS_GLOBALLY_UNIQUE_WITHIN_REGISTRY",
            "REGISTRY_TOPOLOGY != REMOTE_RUNTIME_OBSERVATION",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="registry/ATHENA_SYNAPSE_NODES_V1.json")
    args = parser.parse_args(argv)
    registry = json.loads(Path(args.path).read_text(encoding="utf-8"))
    result = audit_registry(registry)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
