from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
import hashlib
import json
from typing import Any

CANON_PROFILE = "KC144.CANON.JSON.V1"
HASH_POLICY = "sha256"


class CarrierKind(StrEnum):
    CONVERSATION = "conversation"
    GOOGLE_DOC = "google_doc"
    LOCAL_FILE = "local_file"
    GIT_REPOSITORY = "git_repository"


class ProjectionStatus(StrEnum):
    EXACT = "exact"
    PARTIAL = "partial"
    SET_VALUED = "set_valued"
    UNRESOLVED = "unresolved"


class ReturnClass(StrEnum):
    IDENTITY = "identity"
    ALIAS = "alias"
    COLLISION = "collision"
    LOSSY = "lossy"
    UNRESOLVED = "unresolved"


def canonical_json(value: Any) -> str:
    """Deterministic, type-preserving JSON profile used by P03 receipts."""
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def kc144_gid_to_grid(gid: int) -> tuple[int, int]:
    if not 1 <= gid <= 144:
        raise ValueError("KC144 GID must be in [1, 144]")
    zero = gid - 1
    return zero // 12 + 1, zero % 12 + 1


def kc144_grid_to_gid(row: int, column: int) -> int:
    if not 1 <= row <= 12 or not 1 <= column <= 12:
        raise ValueError("KC144 grid coordinates must be in [1, 12]^2")
    return (row - 1) * 12 + column


@dataclass(frozen=True, slots=True)
class Coordinate:
    carrier: CarrierKind
    namespace: str
    object_id: str
    revision: str | None
    fragment: str | None = None
    digest: str | None = None
    epoch: str | None = None
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.namespace or not self.object_id:
            raise ValueError("coordinate namespace and object_id are required")
        if self.digest is not None and (
            len(self.digest) != 64
            or any(char not in "0123456789abcdef" for char in self.digest)
        ):
            raise ValueError("coordinate digest must be lowercase SHA-256")

    @property
    def identity_key(self) -> str:
        # Carrier tag is mandatory: equal wording or hashes never collapse carriers.
        return canonical_digest(
            {
                "type": "KC144.UniversalCoordinate.Identity.V1",
                "carrier": self.carrier.value,
                "namespace": self.namespace,
                "object_id": self.object_id,
                "revision": self.revision,
                "fragment": self.fragment,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "carrier": self.carrier.value,
            "namespace": self.namespace,
            "object_id": self.object_id,
            "revision": self.revision,
            "fragment": self.fragment,
            "digest": self.digest,
            "epoch": self.epoch,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class RoundTripDefect:
    carrier_changed: bool = False
    namespace_changed: bool = False
    object_changed: bool = False
    revision_lost: bool = False
    fragment_lost: bool = False
    digest_changed: bool = False
    extra_candidates: int = 0

    @property
    def is_zero(self) -> bool:
        return not any(
            (
                self.carrier_changed,
                self.namespace_changed,
                self.object_changed,
                self.revision_lost,
                self.fragment_lost,
                self.digest_changed,
                self.extra_candidates,
            )
        )

    @classmethod
    def compare(
        cls, source: Coordinate, returned: tuple[Coordinate, ...]
    ) -> "RoundTripDefect":
        if not returned:
            return cls(
                carrier_changed=True,
                namespace_changed=True,
                object_changed=True,
                revision_lost=source.revision is not None,
                fragment_lost=source.fragment is not None,
                digest_changed=source.digest is not None,
            )
        target = returned[0]
        return cls(
            carrier_changed=source.carrier != target.carrier,
            namespace_changed=source.namespace != target.namespace,
            object_changed=source.object_id != target.object_id,
            revision_lost=source.revision != target.revision,
            fragment_lost=source.fragment != target.fragment,
            digest_changed=source.digest != target.digest,
            extra_candidates=max(0, len(returned) - 1),
        )


@dataclass(frozen=True, slots=True)
class RouteStep:
    source_key: str
    target_key: str
    relation: str
    transform: str
    authority: str


@dataclass(frozen=True, slots=True)
class RouteReceipt:
    run_id: str
    call_index: int
    query_intent: str
    source_key: str
    candidate_paths: tuple[tuple[RouteStep, ...], ...]
    projection_status: ProjectionStatus
    return_class: ReturnClass
    invariant_outcomes: tuple[tuple[str, bool], ...]
    previous_digest: str = "0" * 64
    schema: str = field(default="KC144.RouteReceipt.V1", init=False)
    canon_profile: str = field(default=CANON_PROFILE, init=False)
    hash_policy: str = field(default=HASH_POLICY, init=False)

    def body(self) -> dict[str, Any]:
        data = asdict(self)
        data["projection_status"] = self.projection_status.value
        data["return_class"] = self.return_class.value
        return data

    @property
    def digest(self) -> str:
        return canonical_digest(self.body())


def verify_receipt_chain(
    receipts: list[RouteReceipt], *, expected_head: str | None = None
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    expected = "0" * 64
    for index, receipt in enumerate(receipts):
        if receipt.call_index != index:
            errors.append(f"receipt {index}: call_index mismatch")
        if receipt.previous_digest != expected:
            errors.append(f"receipt {index}: previous_digest mismatch")
        expected = receipt.digest
    if expected_head is not None and expected != expected_head:
        errors.append("receipt chain: anchored head mismatch")
    return not errors, errors
