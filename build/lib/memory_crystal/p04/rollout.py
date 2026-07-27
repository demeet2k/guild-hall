from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from memory_crystal.p03.model import canonical_digest, canonical_json

from .model import (
    REQUIRED_SEED_FILES,
    RepositoryRelation,
    RepositorySnapshot,
    RolloutFinding,
    RolloutReceipt,
    RolloutState,
)

EXTERNAL_RELATION_TARGETS = frozenset(
    {
        "athenachka-collective",
        "qshrink",
    }
)


class FederationRollout:
    """Compile a verified repository inventory into non-destructive seed contracts."""

    def __init__(
        self,
        snapshots: tuple[RepositorySnapshot, ...],
        *,
        control_plane_repo_id: str,
        source_ledger_id: str,
        source_ledger_digest: str,
        observed_at: str,
    ) -> None:
        self.snapshots = snapshots
        self.control_plane_repo_id = control_plane_repo_id
        self.source_ledger_id = source_ledger_id
        self.source_ledger_digest = source_ledger_digest
        self.observed_at = observed_at
        self._by_id = {snapshot.repo_id: snapshot for snapshot in snapshots}
        if len(self._by_id) != len(snapshots):
            raise ValueError("duplicate repo_id in federation")
        if len({item.full_name for item in snapshots}) != len(snapshots):
            raise ValueError("duplicate full_name in federation")
        if len({item.github_id for item in snapshots}) != len(snapshots):
            raise ValueError("duplicate github_id in federation")
        if control_plane_repo_id not in self._by_id:
            raise ValueError("control plane must be present in federation")
        if len(source_ledger_digest) != 64:
            raise ValueError("source ledger digest must be SHA-256")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FederationRollout":
        snapshots: list[RepositorySnapshot] = []
        for raw in data["repositories"]:
            snapshots.append(
                RepositorySnapshot(
                    repo_id=raw["repo_id"],
                    github_id=str(raw["github_id"]),
                    full_name=raw["full_name"],
                    role=raw["role"],
                    registry_status=raw["registry_status"],
                    address=raw["address"],
                    default_branch=raw["default_branch"],
                    head_commit=raw["head_commit"],
                    visibility=raw["visibility"],
                    archived=bool(raw["archived"]),
                    relations=tuple(
                        RepositoryRelation(
                            relation=relation["relation"],
                            target=relation["target"],
                        )
                        for relation in raw.get("relations", ())
                    ),
                    contract_presence=tuple(
                        (name, bool(raw["contract_presence"][name]))
                        for name in REQUIRED_SEED_FILES
                    ),
                )
            )
        return cls(
            tuple(snapshots),
            control_plane_repo_id=data["control_plane_repo_id"],
            source_ledger_id=data["source_ledger"]["ledger_id"],
            source_ledger_digest=data["source_ledger"]["sha256"],
            observed_at=data["observed_at"],
        )

    @classmethod
    def from_path(cls, path: Path) -> "FederationRollout":
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))

    @property
    def repository_ids(self) -> frozenset[str]:
        return frozenset(self._by_id)

    def unresolved_relations(
        self, snapshot: RepositorySnapshot
    ) -> tuple[str, ...]:
        return tuple(
            relation.target
            for relation in snapshot.relations
            if relation.target not in self._by_id
            and relation.target not in EXTERNAL_RELATION_TARGETS
        )

    def audit(self) -> tuple[RolloutFinding, ...]:
        findings: list[RolloutFinding] = []
        findings.append(
            RolloutFinding(
                "P04.F001",
                "info",
                None,
                "repository_inventory_is_identity_unique",
                f"{len(self.snapshots)} repositories have unique repo, GitHub, and full-name identities.",
            )
        )
        for snapshot in self.snapshots:
            if snapshot.archived:
                findings.append(
                    RolloutFinding(
                        f"P04.{snapshot.repo_id}.ARCHIVED",
                        "block",
                        snapshot.repo_id,
                        "repository_is_not_archived",
                        f"{snapshot.full_name} is archived.",
                    )
                )
            unresolved = self.unresolved_relations(snapshot)
            if unresolved:
                findings.append(
                    RolloutFinding(
                        f"P04.{snapshot.repo_id}.RELATION",
                        "block",
                        snapshot.repo_id,
                        "relation_targets_resolve",
                        f"Unresolved targets: {', '.join(unresolved)}.",
                    )
                )
            missing = snapshot.missing_contract_files
            findings.append(
                RolloutFinding(
                    f"P04.{snapshot.repo_id}.CONTRACT",
                    "warn" if missing else "info",
                    snapshot.repo_id,
                    "minimum_seed_contract_is_present",
                    (
                        f"Missing {len(missing)}/6 files: {', '.join(missing)}."
                        if missing
                        else "All six minimum seed files are present."
                    ),
                )
            )
        return tuple(findings)

    def receipts(self) -> tuple[RolloutReceipt, ...]:
        receipts: list[RolloutReceipt] = []
        previous = "0" * 64
        for index, snapshot in enumerate(self.snapshots):
            presence = dict(snapshot.contract_presence)
            receipt = RolloutReceipt(
                call_index=index,
                repo_id=snapshot.repo_id,
                snapshot_id=snapshot.snapshot_id,
                prepared_files=snapshot.generated_contract_files,
                preexisting_files=tuple(
                    name for name in REQUIRED_SEED_FILES if presence[name]
                ),
                unresolved_relations=self.unresolved_relations(snapshot),
                rollout_state=(
                    RolloutState.BLOCKED
                    if snapshot.archived or self.unresolved_relations(snapshot)
                    else RolloutState.PREPARED
                ),
                previous_digest=previous,
            )
            receipts.append(receipt)
            previous = receipt.digest
        return tuple(receipts)

    def _seed_json(self, snapshot: RepositorySnapshot) -> dict[str, Any]:
        return {
            "schema": "athena.federated-seed/v2",
            "seed_id": snapshot.repo_id,
            "repository": {
                "github_id": snapshot.github_id,
                "full_name": snapshot.full_name,
                "default_branch": snapshot.default_branch,
                "pinned_head": snapshot.head_commit,
                "visibility": snapshot.visibility,
                "snapshot_id": snapshot.snapshot_id,
            },
            "role": snapshot.role,
            "registry_status": snapshot.registry_status,
            "canonical_address": snapshot.address,
            "framework": {
                "kc144": "FEDERATED_GIT_BODY",
                "br21": "ADMIT→EXPAND→NAVIGATE→TRANSFORM→TEST→COMPRESS→RETURN",
                "kc27": "QUERY_AND_ROUTE_ADMISSION",
                "kc54": "FORWARD_AND_RETURN_RECEIPT_PAIR",
                "x16": "11_BODY→10_TRANSFORM→00_DEFECT→01_RETURN→11_PRIME",
            },
            "identity_law": (
                "repository GitHub ID + full name + immutable commit; "
                "branch names and content similarity are not identity"
            ),
            "publication_state": RolloutState.PREPARED.value,
        }

    def _provenance_json(self, snapshot: RepositorySnapshot) -> dict[str, Any]:
        control = self._by_id[self.control_plane_repo_id]
        return {
            "schema": "athena.federated-provenance/v2",
            "seed_id": snapshot.repo_id,
            "source_ledger": {
                "ledger_id": self.source_ledger_id,
                "sha256": self.source_ledger_digest,
                "authority": "source, claim, evidence, and version registry",
            },
            "control_plane": {
                "repo_id": control.repo_id,
                "full_name": control.full_name,
                "head_commit": control.head_commit,
            },
            "observed_repository": {
                "github_id": snapshot.github_id,
                "full_name": snapshot.full_name,
                "head_commit": snapshot.head_commit,
                "observed_at": self.observed_at,
            },
            "anti_inflation": [
                "registry membership does not prove implementation",
                "shared ancestry does not create independent evidence",
                "a prepared contract is not a published contract",
                "a structural pass is not empirical certification",
            ],
        }

    def _relations_json(self, snapshot: RepositorySnapshot) -> dict[str, Any]:
        relations = []
        for relation in snapshot.relations:
            target = self._by_id.get(relation.target)
            relations.append(
                {
                    "relation": relation.relation,
                    "target": relation.target,
                    "target_snapshot_id": target.snapshot_id if target else None,
                    "target_class": (
                        "internal_repository"
                        if target
                        else "declared_external"
                        if relation.target in EXTERNAL_RELATION_TARGETS
                        else "unresolved"
                    ),
                }
            )
        return {
            "schema": "athena.federated-relations/v2",
            "seed_id": snapshot.repo_id,
            "relations": relations,
            "composition_law": (
                "relations compose only when source, target, transform, authority, "
                "return, and replay contracts are compatible"
            ),
            "unresolved_targets": list(self.unresolved_relations(snapshot)),
        }

    def _state_json(self, snapshot: RepositorySnapshot) -> dict[str, Any]:
        presence = dict(snapshot.contract_presence)
        return {
            "schema": "athena.federated-state/v2",
            "seed_id": snapshot.repo_id,
            "snapshot_id": snapshot.snapshot_id,
            "observed_at": self.observed_at,
            "observed_head": snapshot.head_commit,
            "pre_rollout_contract_presence": presence,
            "prepared_files": list(snapshot.generated_contract_files),
            "preserved_files": [
                name for name in REQUIRED_SEED_FILES if presence[name]
            ],
            "publication_state": RolloutState.PREPARED.value,
            "promotion": {
                "structural_contract": "prepared",
                "repository_write": "not_executed",
                "live_replay": "not_run",
                "ic10": "not_run",
                "ssn_commit": "not_run",
            },
        }

    def _return_md(self, snapshot: RepositorySnapshot) -> str:
        control = self._by_id[self.control_plane_repo_id]
        relations = "\n".join(
            f"- `{relation.relation}` → `{relation.target}`"
            for relation in snapshot.relations
        ) or "- No outbound relation declared."
        return f"""# Return Contract — {snapshot.full_name}

This repository is a federated Athena seed at immutable snapshot
`{snapshot.head_commit}`. The branch name `{snapshot.default_branch}` is a
discovery pointer, not the identity of this return packet.

## Return path

1. Read `SEED.json` for identity and role.
2. Read `PROVENANCE.json` for the source ledger and control-plane witness.
3. Read `RELATIONS.json` for typed lateral routes.
4. Read `STATE.json` before treating this packet as published or replayed.
5. Return to `{control.full_name}` at `{control.head_commit}`.

## Declared routes

{relations}

## Refusal law

If the pinned commit, source-ledger digest, or target identity cannot be
recovered, return `UNRESOLVED` with the failed coordinate. Do not substitute a
branch head, a similarly named repository, or a textually similar artifact.
"""

    def render_contract(self, snapshot: RepositorySnapshot) -> dict[str, str]:
        rendered = {
            "SEED.json": canonical_json(self._seed_json(snapshot)) + "\n",
            "PROVENANCE.json": canonical_json(self._provenance_json(snapshot))
            + "\n",
            "RELATIONS.json": canonical_json(self._relations_json(snapshot)) + "\n",
            "STATE.json": canonical_json(self._state_json(snapshot)) + "\n",
            "RETURN.md": self._return_md(snapshot),
        }
        return {
            name: content
            for name, content in rendered.items()
            if name in snapshot.generated_contract_files
        }

    def write_bundle(self, root: Path) -> dict[str, Any]:
        root.mkdir(parents=True, exist_ok=True)
        packet_digests: dict[str, dict[str, str]] = {}
        for snapshot in self.snapshots:
            repo_dir = root / snapshot.full_name.replace("/", "__")
            repo_dir.mkdir(parents=True, exist_ok=True)
            packet_digests[snapshot.repo_id] = {}
            for name, content in self.render_contract(snapshot).items():
                path = repo_dir / name
                path.write_text(content, encoding="utf-8")
                packet_digests[snapshot.repo_id][name] = canonical_digest(
                    {"filename": name, "utf8": content}
                )
        receipts = self.receipts()
        receipt_body = {
            "schema": "KC144.P04.FederationRollout.V1",
            "observed_at": self.observed_at,
            "control_plane_repo_id": self.control_plane_repo_id,
            "source_ledger": {
                "ledger_id": self.source_ledger_id,
                "sha256": self.source_ledger_digest,
            },
            "repository_count": len(self.snapshots),
            "contract_complete_before_rollout": sum(
                item.contract_complete for item in self.snapshots
            ),
            "prepared_repository_count": sum(
                receipt.rollout_state == RolloutState.PREPARED
                for receipt in receipts
            ),
            "prepared_file_count": sum(
                len(receipt.prepared_files) for receipt in receipts
            ),
            "publication_state": "not_executed",
            "packet_digests": packet_digests,
            "receipts": [
                {**receipt.body(), "digest": receipt.digest}
                for receipt in receipts
            ],
            "receipt_chain_head": receipts[-1].digest if receipts else "0" * 64,
            "findings": [asdict(finding) for finding in self.audit()],
        }
        (root / "ROLLOUT_RECEIPT.json").write_text(
            json.dumps(
                receipt_body,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return receipt_body


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
