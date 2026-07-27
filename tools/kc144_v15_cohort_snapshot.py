#!/usr/bin/env python3
"""Compile a deterministic KC144 V15 cohort snapshot from one fixed ledger tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

SCHEMA = "KC144.FixedTreeCohortSnapshot.V15"
COMPILER_SCHEMA = "KC144.CohortSnapshotCompiler.V15"
SOURCE_SCHEMA = "KC144.GitHubIssueSourceBinding.V15"
RECEIPT_SCHEMA = "KC144.CryptographicPassReceipt.V15"
APPLICATION_SCHEMA = "KC144.BatchBoundCandidateApplication.V15"
EXCLUSION_SCHEMA = "KC144.LedgerExclusion.V15"
ROLES = (
    "CUSTODIAN",
    "INDEPENDENT_REVIEWER",
    "REPLAY_WITNESS",
    "SOURCE_AUDITOR",
    "RETURN_AUDITOR",
)
INDEPENDENCE_FIELDS = (
    "identity_claim_root",
    "external_identity_verification_root",
    "external_independence_verification_root",
    "institution_root",
    "lineage_root",
    "jurisdiction_root",
    "primary_domain_root",
    "authority_root",
    "funding_root",
    "data_control_root",
    "staff_control_root",
    "technology_control_root",
)
DIGEST_RE = re.compile(r"^sha256:([0-9a-f]{64})$")
HEX_RE = re.compile(r"^[0-9a-f]{40}$")
GIT_TREE_RE = re.compile(r"^[0-9a-f]{40}$")
ISSUE_SOURCE_RE = re.compile(r"^[0-9]{12}\.json$")


class CompileError(ValueError):
    """Raised when the fixed ledger tree violates its own contract."""


def _reject_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CompileError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise CompileError(f"non-finite JSON number: {value}")


def load_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_pairs,
            parse_constant=_reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CompileError(f"cannot parse {path.as_posix()}") from exc


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CompileError("value is not canonical JSON") from exc


def digest_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def require_digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or DIGEST_RE.fullmatch(value) is None:
        raise CompileError(f"invalid digest: {label}")
    return value


def require_keys(value: Any, required: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not required.issubset(value):
        raise CompileError(f"missing keys: {label}")
    return value


def safe_ledger_path(ledger_root: Path, relative: Any, label: str) -> Path:
    if not isinstance(relative, str) or relative.startswith("/"):
        raise CompileError(f"invalid ledger path: {label}")
    root = ledger_root.resolve()
    candidate = (ledger_root.parents[1] / relative).resolve()
    if candidate != root and root not in candidate.parents:
        raise CompileError(f"path escapes ledger root: {label}")
    if not candidate.is_file():
        raise CompileError(f"missing ledger file: {label}")
    return candidate


def verify_canonical_file(path: Path, value: Any, expected_digest: str) -> None:
    canonical = canonical_bytes(value)
    stored = path.read_bytes()
    if stored != canonical + b"\n":
        raise CompileError(f"non-canonical stored bytes: {path.as_posix()}")
    if digest_bytes(canonical) != expected_digest:
        raise CompileError(f"digest mismatch: {path.as_posix()}")


def public_key_digest(public_key_b64: Any) -> str:
    if not isinstance(public_key_b64, str) or not public_key_b64:
        raise CompileError("invalid candidate public key")
    return digest_bytes(public_key_b64.encode("utf-8"))


def exclusion_for(
    ledger_root: Path,
    source_name: str,
    application_digest: str,
    issue_number: int,
) -> dict[str, Any] | None:
    path = ledger_root / "exclusions" / "github-issues" / source_name
    if not path.exists():
        return None
    record = require_keys(
        load_json(path),
        {
            "schema",
            "application_digest",
            "issue_number",
            "source_binding_path",
            "classification",
            "counting_effect",
            "governance_authority_granted",
            "production_truth_effect",
        },
        "exclusion record",
    )
    if (
        record["schema"] != EXCLUSION_SCHEMA
        or record["application_digest"] != application_digest
        or record["issue_number"] != issue_number
        or record["classification"] != "SYNTHETIC_TEST_ARTIFACT"
        or record["counting_effect"] != "NONE"
        or record["governance_authority_granted"] is not False
        or record["production_truth_effect"] != "NONE"
    ):
        raise CompileError(f"invalid exclusion record: {path.as_posix()}")
    return record


def read_observations(ledger_root: Path) -> list[dict[str, Any]]:
    sources_root = ledger_root / "sources" / "github-issues"
    observations: list[dict[str, Any]] = []
    if not sources_root.exists():
        return observations
    for source_path in sorted(sources_root.glob("*.json")):
        if ISSUE_SOURCE_RE.fullmatch(source_path.name) is None:
            raise CompileError(f"unexpected source filename: {source_path.name}")
        source = require_keys(
            load_json(source_path),
            {
                "schema",
                "repository",
                "issue_number",
                "issue_body_digest",
                "application_digest",
                "application_path",
                "receipt_digest",
                "receipt_path",
            },
            "source binding",
        )
        if source["schema"] != SOURCE_SCHEMA:
            raise CompileError("wrong source schema")
        application_digest = require_digest(
            source["application_digest"], "source.application_digest"
        )
        receipt_digest = require_digest(
            source["receipt_digest"], "source.receipt_digest"
        )
        require_digest(source["issue_body_digest"], "source.issue_body_digest")
        issue_number = source["issue_number"]
        if (
            not isinstance(issue_number, int)
            or issue_number < 1
            or source_path.name != f"{issue_number:012d}.json"
        ):
            raise CompileError("issue source address mismatch")

        application_path = safe_ledger_path(
            ledger_root, source["application_path"], "application"
        )
        receipt_path = safe_ledger_path(
            ledger_root, source["receipt_path"], "receipt"
        )
        application = require_keys(
            load_json(application_path),
            {
                "schema",
                "application_id",
                "nomination_envelope",
                "target_calls",
            },
            "application",
        )
        receipt = require_keys(
            load_json(receipt_path),
            {
                "schema",
                "application_digest",
                "application_path",
                "declared_role",
                "source",
                "technical_verdict",
                "cohort_effect",
            },
            "receipt",
        )
        if application["schema"] != APPLICATION_SCHEMA:
            raise CompileError("wrong application schema")
        if receipt["schema"] != RECEIPT_SCHEMA:
            raise CompileError("wrong receipt schema")
        verify_canonical_file(application_path, application, application_digest)
        verify_canonical_file(receipt_path, receipt, receipt_digest)
        if (
            receipt["application_digest"] != application_digest
            or receipt["application_path"] != source["application_path"]
            or receipt["technical_verdict"]
            != "CRYPTOGRAPHIC_PREFLIGHT_PASS_NONCOUNTING"
            or receipt["cohort_effect"] != "NONE_PENDING_FIXED_TREE_SNAPSHOT"
            or receipt["source"].get("issue_number") != issue_number
            or receipt["source"].get("issue_body_digest")
            != source["issue_body_digest"]
        ):
            raise CompileError("receipt/source binding mismatch")

        envelope = require_keys(
            application["nomination_envelope"],
            {"envelope_id", "nomination"},
            "nomination envelope",
        )
        nomination = require_keys(
            envelope["nomination"],
            {
                "nomination_id",
                "candidate_id",
                "public_key_b64",
                "eligible_roles",
                "identity_claim_root",
                "external_identity_verification_root",
                "external_independence_verification_root",
                "institution_root",
                "lineage_root",
                "jurisdiction_root",
                "primary_domain_root",
                "authority_root",
                "funding_root",
                "data_control_root",
                "staff_control_root",
                "technology_control_root",
            },
            "nomination",
        )
        roles = nomination["eligible_roles"]
        target_calls = application["target_calls"]
        if (
            not isinstance(roles, list)
            or len(roles) != 1
            or roles[0] not in ROLES
            or not isinstance(target_calls, list)
            or len(target_calls) != 1
            or target_calls[0].get("role") != roles[0]
            or receipt["declared_role"] != roles[0]
        ):
            raise CompileError("role vector mismatch")

        exclusion = exclusion_for(
            ledger_root, source_path.name, application_digest, issue_number
        )
        observations.append(
            {
                "application_digest": application_digest,
                "receipt_digest": receipt_digest,
                "issue_number": issue_number,
                "source_path": source_path.relative_to(
                    ledger_root.parents[1]
                ).as_posix(),
                "application_path": source["application_path"],
                "receipt_path": source["receipt_path"],
                "application_id": application["application_id"],
                "envelope_id": envelope["envelope_id"],
                "nomination_id": nomination["nomination_id"],
                "candidate_id": nomination["candidate_id"],
                "candidate_public_key_digest": public_key_digest(
                    nomination["public_key_b64"]
                ),
                "role": roles[0],
                "independence_dimensions": {
                    key: nomination[key]
                    for key in INDEPENDENCE_FIELDS
                },
                "exclusion": exclusion,
            }
        )
    return observations


def group_applications(
    observations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for observation in observations:
        grouped[observation["application_digest"]].append(observation)
    rows: list[dict[str, Any]] = []
    identity_fields = (
        "application_id",
        "envelope_id",
        "nomination_id",
        "candidate_id",
        "candidate_public_key_digest",
    )
    for application_digest in sorted(grouped):
        group = grouped[application_digest]
        first = group[0]
        for observation in group[1:]:
            for field in (
                *identity_fields,
                "role",
                "application_path",
            ):
                if observation[field] != first[field]:
                    raise CompileError(
                        f"one application digest has inconsistent {field}"
                    )
            if (
                observation["independence_dimensions"]
                != first["independence_dimensions"]
            ):
                raise CompileError(
                    "one application digest has inconsistent dimensions"
                )
        exclusions = [
            observation["exclusion"]
            for observation in group
            if observation["exclusion"] is not None
        ]
        rows.append(
            {
                "application_digest": application_digest,
                "application_path": first["application_path"],
                "application_id": first["application_id"],
                "envelope_id": first["envelope_id"],
                "nomination_id": first["nomination_id"],
                "candidate_id": first["candidate_id"],
                "candidate_public_key_digest": first[
                    "candidate_public_key_digest"
                ],
                "role": first["role"],
                "independence_dimensions": first["independence_dimensions"],
                "source_count": len(group),
                "source_issue_numbers": sorted(
                    observation["issue_number"] for observation in group
                ),
                "receipt_digests": sorted(
                    {observation["receipt_digest"] for observation in group}
                ),
                "excluded": bool(exclusions),
                "exclusion_classifications": sorted(
                    {record["classification"] for record in exclusions}
                ),
            }
        )
    return rows


def duplicate_sets(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    active = [row for row in rows if not row["excluded"]]
    fields = (
        "application_id",
        "envelope_id",
        "nomination_id",
        "candidate_id",
        "candidate_public_key_digest",
    )
    dimensions = INDEPENDENCE_FIELDS
    result: dict[str, list[dict[str, Any]]] = {}
    for field in fields:
        indexed: dict[str, list[str]] = defaultdict(list)
        for row in active:
            indexed[str(row[field])].append(row["application_digest"])
        result[field] = [
            {
                "value": value,
                "application_digests": sorted(digests),
            }
            for value, digests in sorted(indexed.items())
            if len(digests) > 1
        ]
    for field in dimensions:
        key = f"independence_dimensions.{field}"
        indexed = defaultdict(list)
        for row in active:
            indexed[str(row["independence_dimensions"][field])].append(
                row["application_digest"]
            )
        result[key] = [
            {
                "value": value,
                "application_digests": sorted(digests),
            }
            for value, digests in sorted(indexed.items())
            if len(digests) > 1
        ]
    return result


def apply_global_states(
    rows: list[dict[str, Any]],
    duplicates: dict[str, list[dict[str, Any]]],
) -> None:
    duplicate_members: dict[str, set[str]] = defaultdict(set)
    for field, sets in duplicates.items():
        for duplicate_set in sets:
            for application_digest in duplicate_set["application_digests"]:
                duplicate_members[application_digest].add(field)
    for row in rows:
        duplicate_fields = sorted(duplicate_members[row["application_digest"]])
        row["duplicate_fields"] = duplicate_fields
        row["global_unique"] = not row["excluded"] and not duplicate_fields
        row["identity_independence_state"] = (
            "EXCLUDED_SYNTHETIC_TEST_ARTIFACT"
            if row["excluded"]
            else "NO_ADMISSIBLE_EXTERNAL_ADJUDICATION"
        )
        row["counting_eligible"] = False


def compile_snapshot(
    ledger_root: Path,
    ledger_commit: str,
    ledger_tree: str,
    compiler_commit: str,
) -> dict[str, Any]:
    if HEX_RE.fullmatch(ledger_commit) is None:
        raise CompileError("invalid ledger commit")
    if GIT_TREE_RE.fullmatch(ledger_tree) is None:
        raise CompileError("invalid ledger tree")
    if HEX_RE.fullmatch(compiler_commit) is None:
        raise CompileError("invalid compiler commit")
    observations = read_observations(ledger_root)
    rows = group_applications(observations)
    duplicates = duplicate_sets(rows)
    apply_global_states(rows, duplicates)
    role_vector = {
        role: sorted(
            row["application_digest"]
            for row in rows
            if row["role"] == role and row["counting_eligible"]
        )
        for role in ROLES
    }
    filled_role_count = sum(bool(values) for values in role_vector.values())
    counting_count = sum(row["counting_eligible"] for row in rows)
    excluded_count = sum(row["excluded"] for row in rows)
    duplicate_application_count = sum(
        bool(row["duplicate_fields"]) for row in rows
    )
    return {
        "schema": SCHEMA,
        "compiler_schema": COMPILER_SCHEMA,
        "compiler_commit": compiler_commit,
        "ledger": {
            "branch": "kc144-v15-pass-ledger",
            "commit": ledger_commit,
            "tree": ledger_tree,
        },
        "receipt_observation_count": len(observations),
        "technical_application_count": len(rows),
        "excluded_application_count": excluded_count,
        "unexcluded_application_count": len(rows) - excluded_count,
        "duplicate_application_count": duplicate_application_count,
        "globally_unique_application_count": sum(
            row["global_unique"] for row in rows
        ),
        "identity_independence_confirmed_count": 0,
        "counting_candidate_count": counting_count,
        "global_duplicate_sets": duplicates,
        "applications": rows,
        "role_vector": role_vector,
        "filled_role_count": filled_role_count,
        "required_role_count": len(ROLES),
        "cohort_state": (
            "FIVE_ROLE_COHORT_READY"
            if filled_role_count == len(ROLES)
            else "HOLD_EXTERNAL_IDENTITY_INDEPENDENCE_AND_ROLE_VECTOR_INCOMPLETE"
        ),
        "next_barrier": (
            "PACKET_DELIVERY_REQUIRED"
            if filled_role_count == len(ROLES)
            else "FIVE_REAL_EXTERNALLY_VERIFIED_INDEPENDENT_APPLICATIONS_REQUIRED"
        ),
        "synthetic_counting_effect": "NONE",
        "governance_authority_granted": False,
        "production_truth_effect": "NONE",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger-root", required=True, type=Path)
    parser.add_argument("--ledger-commit", required=True)
    parser.add_argument("--ledger-tree", required=True)
    parser.add_argument("--compiler-commit", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--binding-output", required=True, type=Path)
    arguments = parser.parse_args()

    snapshot = compile_snapshot(
        arguments.ledger_root,
        arguments.ledger_commit,
        arguments.ledger_tree,
        arguments.compiler_commit,
    )
    snapshot_bytes = canonical_bytes(snapshot)
    snapshot_digest = digest_bytes(snapshot_bytes)
    snapshot_hex = snapshot_digest.removeprefix("sha256:")
    snapshot_path = (
        f"cohort/v15/snapshots/sha256/{snapshot_hex[:2]}/"
        f"{snapshot_hex}.snapshot.json"
    )
    binding = {
        "schema": "KC144.LedgerTreeSnapshotBinding.V15",
        "ledger_branch": "kc144-v15-pass-ledger",
        "ledger_commit": arguments.ledger_commit,
        "ledger_tree": arguments.ledger_tree,
        "compiler_commit": arguments.compiler_commit,
        "snapshot_digest": snapshot_digest,
        "snapshot_path": snapshot_path,
        "cohort_state": snapshot["cohort_state"],
        "counting_candidate_count": snapshot["counting_candidate_count"],
        "filled_role_count": snapshot["filled_role_count"],
        "governance_authority_granted": False,
        "production_truth_effect": "NONE",
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.binding_output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_bytes(snapshot_bytes + b"\n")
    arguments.binding_output.write_bytes(canonical_bytes(binding) + b"\n")
    print(
        json.dumps(
            {
                "snapshot_digest": snapshot_digest,
                "snapshot_path": snapshot_path,
                "binding": binding,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
