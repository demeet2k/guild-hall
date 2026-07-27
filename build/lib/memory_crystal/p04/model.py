from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
import re
from typing import Any

from memory_crystal.p03.model import canonical_digest

HEX_COMMIT = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
REQUIRED_SEED_FILES = (
    "SEED.json",
    "PROVENANCE.json",
    "RELATIONS.json",
    "STATE.json",
    "RETURN.md",
    "README.md",
)
GENERATED_SEED_FILES = REQUIRED_SEED_FILES[:-1]


class RolloutState(StrEnum):
    DISCOVERED = "discovered"
    PREPARED = "prepared_not_published"
    DEPLOYED = "deployed"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class RepositoryRelation:
    relation: str
    target: str

    def __post_init__(self) -> None:
        if not self.relation or not self.target:
            raise ValueError("repository relation and target are required")


@dataclass(frozen=True, slots=True)
class RepositorySnapshot:
    repo_id: str
    github_id: str
    full_name: str
    role: str
    registry_status: str
    address: str
    default_branch: str
    head_commit: str
    visibility: str
    archived: bool
    relations: tuple[RepositoryRelation, ...] = ()
    contract_presence: tuple[tuple[str, bool], ...] = ()

    def __post_init__(self) -> None:
        if not self.repo_id or not self.github_id or not self.full_name:
            raise ValueError("repo_id, github_id, and full_name are required")
        if "/" not in self.full_name:
            raise ValueError("full_name must use owner/repository form")
        if not HEX_COMMIT.fullmatch(self.head_commit):
            raise ValueError("head_commit must be an immutable 40- or 64-hex SHA")
        if self.visibility not in {"public", "private", "internal"}:
            raise ValueError("unsupported repository visibility")
        presence = dict(self.contract_presence)
        if set(presence) != set(REQUIRED_SEED_FILES):
            raise ValueError("contract_presence must enumerate every required seed file")

    @property
    def snapshot_id(self) -> str:
        return canonical_digest(
            {
                "schema": "KC144.P04.RepositorySnapshot.Identity.V1",
                "github_id": self.github_id,
                "full_name": self.full_name,
                "head_commit": self.head_commit,
            }
        )

    @property
    def missing_contract_files(self) -> tuple[str, ...]:
        presence = dict(self.contract_presence)
        return tuple(name for name in REQUIRED_SEED_FILES if not presence[name])

    @property
    def generated_contract_files(self) -> tuple[str, ...]:
        return tuple(
            name for name in GENERATED_SEED_FILES if name in self.missing_contract_files
        )

    @property
    def contract_complete(self) -> bool:
        return not self.missing_contract_files

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo_id": self.repo_id,
            "github_id": self.github_id,
            "full_name": self.full_name,
            "role": self.role,
            "registry_status": self.registry_status,
            "address": self.address,
            "default_branch": self.default_branch,
            "head_commit": self.head_commit,
            "visibility": self.visibility,
            "archived": self.archived,
            "relations": [asdict(relation) for relation in self.relations],
            "contract_presence": dict(self.contract_presence),
            "snapshot_id": self.snapshot_id,
        }


@dataclass(frozen=True, slots=True)
class RolloutFinding:
    finding_id: str
    severity: str
    repo_id: str | None
    predicate: str
    detail: str

    def __post_init__(self) -> None:
        if self.severity not in {"info", "warn", "block"}:
            raise ValueError("finding severity must be info, warn, or block")


@dataclass(frozen=True, slots=True)
class RolloutReceipt:
    call_index: int
    repo_id: str
    snapshot_id: str
    prepared_files: tuple[str, ...]
    preexisting_files: tuple[str, ...]
    unresolved_relations: tuple[str, ...]
    rollout_state: RolloutState
    previous_digest: str = "0" * 64
    schema: str = field(default="KC144.P04.RolloutReceipt.V1", init=False)

    def body(self) -> dict[str, Any]:
        data = asdict(self)
        data["rollout_state"] = self.rollout_state.value
        return data

    @property
    def digest(self) -> str:
        return canonical_digest(self.body())


def verify_rollout_receipts(
    receipts: list[RolloutReceipt], *, expected_head: str | None = None
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    previous = "0" * 64
    for index, receipt in enumerate(receipts):
        if receipt.call_index != index:
            errors.append(f"receipt {index}: call_index mismatch")
        if receipt.previous_digest != previous:
            errors.append(f"receipt {index}: previous_digest mismatch")
        previous = receipt.digest
    if expected_head is not None and previous != expected_head:
        errors.append("receipt chain: anchored head mismatch")
    return not errors, errors
