from __future__ import annotations

"""Dependency-free audit for ATHENA Synapse node manifests.

A manifest is an evidence-bound declaration of a node's native surface. It is
not proof that the server started, a route worked, an adapter is active, or a
foreign consumer incorporated anything.
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "ATHENA.SYNAPSE.NODE.MANIFEST.V1"
STANDINGS = {"DECLARED_NO_ADAPTER", "PROPOSED_ADAPTER", "ACTIVE_ADAPTER", "HOLD"}
SURFACE_KINDS = {"MCP_RESOURCE", "MCP_TOOL_MODULE", "STATE_SURFACE", "PROTOCOL", "DATA", "OTHER"}
MUTATION_CLASSES = {"READ_ONLY", "READ_WRITE", "MIXED", "UNKNOWN"}
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_NODE_RE = re.compile(r"^[a-z][a-z0-9-]{1,63}$")
_REV_RE = re.compile(r"^[A-Fa-f0-9]{7,64}$")


def _unique_strings(value: Any, *, nonempty: bool = False) -> bool:
    return (
        isinstance(value, list)
        and (not nonempty or bool(value))
        and len(value) == len(set(value))
        and all(isinstance(x, str) and bool(x.strip()) for x in value)
    )


def audit_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    if manifest.get("schema") != SCHEMA:
        errors.append({"code": "BAD_SCHEMA"})
    node_id = str(manifest.get("node_id") or "").strip()
    repository = str(manifest.get("repository") or "").strip()
    branch = str(manifest.get("default_branch") or "").strip()
    role = str(manifest.get("role") or "").strip()
    standing = str(manifest.get("standing") or "").strip()
    revision = str(manifest.get("observed_revision") or "").strip()
    authority = str(manifest.get("authority_class") or "").strip()
    truth = str(manifest.get("truth_ceiling") or "").strip()

    if not _NODE_RE.fullmatch(node_id):
        errors.append({"code": "BAD_NODE_ID", "value": node_id})
    if not _REPO_RE.fullmatch(repository):
        errors.append({"code": "BAD_REPOSITORY", "value": repository})
    if not branch:
        errors.append({"code": "DEFAULT_BRANCH_REQUIRED"})
    if not role:
        errors.append({"code": "ROLE_REQUIRED"})
    if standing not in STANDINGS:
        errors.append({"code": "BAD_STANDING", "value": standing})
    if not _REV_RE.fullmatch(revision):
        errors.append({"code": "BAD_OBSERVED_REVISION", "value": revision})
    if not authority:
        errors.append({"code": "AUTHORITY_CLASS_REQUIRED"})
    if not truth:
        errors.append({"code": "TRUTH_CEILING_REQUIRED"})

    profiles = manifest.get("synapse_profiles")
    imports = manifest.get("import_profiles")
    returns = manifest.get("return_routes")
    evidence = manifest.get("evidence_refs")
    residuals = manifest.get("residuals")
    for name, value, nonempty in (
        ("synapse_profiles", profiles, False),
        ("import_profiles", imports, False),
        ("return_routes", returns, True),
        ("evidence_refs", evidence, True),
        ("residuals", residuals, False),
    ):
        if not _unique_strings(value, nonempty=nonempty):
            errors.append({"code": "BAD_STRING_LIST", "field": name})

    if standing == "DECLARED_NO_ADAPTER" and (profiles or imports):
        errors.append({"code": "NO_ADAPTER_CANNOT_CLAIM_PROFILE"})
    if standing in {"PROPOSED_ADAPTER", "ACTIVE_ADAPTER"} and not profiles:
        errors.append({"code": "ADAPTER_STANDING_REQUIRES_PROFILE"})
    if standing == "ACTIVE_ADAPTER" and not any(str(x).startswith("test:") or str(x).startswith("ci:") for x in (evidence or [])):
        errors.append({"code": "ACTIVE_ADAPTER_REQUIRES_EXECUTION_EVIDENCE"})

    surfaces = manifest.get("native_surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        errors.append({"code": "NATIVE_SURFACE_REQUIRED"})
        surfaces = []
    surface_ids: set[str] = set()
    refs: set[str] = set()
    for index, raw in enumerate(surfaces):
        if not isinstance(raw, Mapping):
            errors.append({"code": "SURFACE_NOT_OBJECT", "index": index})
            continue
        sid = str(raw.get("surface_id") or "").strip()
        kind = str(raw.get("kind") or "").strip()
        ref = str(raw.get("reference") or "").strip()
        mutation = str(raw.get("mutation_class") or "").strip()
        ev = str(raw.get("evidence_ref") or "").strip()
        if not sid:
            errors.append({"code": "SURFACE_ID_REQUIRED", "index": index})
        elif sid in surface_ids:
            errors.append({"code": "DUPLICATE_SURFACE_ID", "surface_id": sid})
        else:
            surface_ids.add(sid)
        if kind not in SURFACE_KINDS:
            errors.append({"code": "BAD_SURFACE_KIND", "surface_id": sid, "kind": kind})
        if not ref:
            errors.append({"code": "SURFACE_REFERENCE_REQUIRED", "surface_id": sid})
        elif ref in refs:
            warnings.append({"code": "DUPLICATE_SURFACE_REFERENCE", "surface_id": sid, "reference": ref})
        else:
            refs.add(ref)
        if mutation not in MUTATION_CLASSES:
            errors.append({"code": "BAD_MUTATION_CLASS", "surface_id": sid, "value": mutation})
        if not ev:
            errors.append({"code": "SURFACE_EVIDENCE_REQUIRED", "surface_id": sid})
        elif isinstance(evidence, list) and ev not in evidence:
            errors.append({"code": "SURFACE_EVIDENCE_NOT_IN_MANIFEST_EVIDENCE", "surface_id": sid, "evidence_ref": ev})

    if standing == "DECLARED_NO_ADAPTER" and not any("ADAPTER" in str(x).upper() for x in (residuals or [])):
        warnings.append({"code": "NO_ADAPTER_WITHOUT_EXPLICIT_ADAPTER_RESIDUAL"})
    if not any("RUNTIME" in str(x).upper() for x in (residuals or [])):
        warnings.append({"code": "RUNTIME_STANDING_NOT_EXPLICIT"})

    return {
        "artifact": "ATHENA.SYNAPSE.NODE.MANIFEST.AUDIT.V1",
        "ok": not errors,
        "node_id": node_id or None,
        "repository": repository or None,
        "standing": standing or None,
        "surface_count": len(surfaces),
        "errors": errors,
        "warnings": warnings,
        "laws": [
            "MANIFEST != RUNTIME_WITNESS",
            "NATIVE_SURFACE != SYNAPSE_ADAPTER",
            "DECLARED_NO_ADAPTER => NO_PROFILE_CLAIM",
            "ACTIVE_ADAPTER => EXECUTION_EVIDENCE_REQUIRED",
            "OBSERVED_REVISION_BOUNDS_THE_DECLARATION",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args(argv)
    reports = []
    for raw in args.paths:
        value = json.loads(Path(raw).read_text(encoding="utf-8"))
        reports.append(audit_manifest(value))
    result = {"artifact": "ATHENA.SYNAPSE.NODE.MANIFEST.AUDIT.SET.V1", "ok": all(r["ok"] for r in reports), "reports": reports}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
