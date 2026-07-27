from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
import re
import unicodedata
from typing import Any

from memory_crystal.p03.model import canonical_digest, kc144_gid_to_grid


class TruthState(StrEnum):
    FAIL = "FAIL"
    RESID = "RESID"
    AMBIG = "AMBIG"
    NEAR = "NEAR"
    OK = "OK"


class OriginClass(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    INTERNAL_HISTORY = "internal_history"
    GOOGLE_DOC = "google_doc"
    GITHUB_SEED = "github_seed"
    LOCAL_FILE = "local_file"
    RUNTIME = "runtime"
    DERIVED = "derived"


class LifecycleState(StrEnum):
    RETRIEVED_FRAGMENT = "RETRIEVED_FRAGMENT"
    EVIDENCE_CANDIDATE = "EVIDENCE_CANDIDATE"
    SOURCE_BOUND = "SOURCE_BOUND"
    DEPENDENCY_COLLAPSED = "DEPENDENCY_COLLAPSED"
    CONFLICT_CHECKED = "CONFLICT_CHECKED"
    IC10_TESTED = "IC10_TESTED"
    VERSION_EVENT = "VERSION_EVENT"
    PROMOTED = "PROMOTED"


LEQ = {
    (TruthState.FAIL, TruthState.FAIL),
    (TruthState.FAIL, TruthState.RESID),
    (TruthState.FAIL, TruthState.AMBIG),
    (TruthState.FAIL, TruthState.NEAR),
    (TruthState.FAIL, TruthState.OK),
    (TruthState.RESID, TruthState.RESID),
    (TruthState.RESID, TruthState.NEAR),
    (TruthState.RESID, TruthState.OK),
    (TruthState.AMBIG, TruthState.AMBIG),
    (TruthState.AMBIG, TruthState.NEAR),
    (TruthState.AMBIG, TruthState.OK),
    (TruthState.NEAR, TruthState.NEAR),
    (TruthState.NEAR, TruthState.OK),
    (TruthState.OK, TruthState.OK),
}


def truth_meet(left: TruthState, right: TruthState) -> TruthState:
    order = (
        TruthState.FAIL,
        TruthState.RESID,
        TruthState.AMBIG,
        TruthState.NEAR,
        TruthState.OK,
    )
    lowers = [state for state in order if (state, left) in LEQ and (state, right) in LEQ]
    greatest = [
        state
        for state in lowers
        if all((candidate, state) in LEQ for candidate in lowers)
    ]
    return greatest[0] if greatest else TruthState.FAIL


def normalize_text(value: str) -> str:
    folded = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", folded))


@dataclass(frozen=True, slots=True)
class FrameworkAddress:
    gid: int
    station: str
    domain: str
    node: str
    epoch: str = "KC144.V1"

    def __post_init__(self) -> None:
        if not 1 <= self.gid <= 144:
            raise ValueError("GID must be in [1, 144]")
        if not all((self.station, self.domain, self.node, self.epoch)):
            raise ValueError("complete framework address required")

    @property
    def grid(self) -> str:
        row, column = kc144_gid_to_grid(self.gid)
        return f"R{row:02d}C{column:02d}"

    @property
    def key(self) -> str:
        return (
            f"{self.epoch}::GID{self.gid:03d}::{self.station}"
            f"::D.{self.domain}::N.{self.node}"
        )

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "FrameworkAddress":
        return cls(
            gid=int(value["gid"]),
            station=value["station"],
            domain=value["domain"],
            node=value["node"],
            epoch=value.get("epoch", "KC144.V1"),
        )


@dataclass(frozen=True, slots=True)
class SourceRef:
    carrier: str
    source_id: str
    revision: str
    locator: str
    authority: str
    evidence_root: str
    observed_at: str | None = None

    def __post_init__(self) -> None:
        if not all(
            (
                self.carrier,
                self.source_id,
                self.revision,
                self.locator,
                self.authority,
                self.evidence_root,
            )
        ):
            raise ValueError("source references require immutable identity and evidence root")

    @property
    def key(self) -> str:
        return canonical_digest(
            {
                "type": "KC144.InternalNav.SourceRef.V1",
                "carrier": self.carrier,
                "source_id": self.source_id,
                "revision": self.revision,
                "locator": self.locator,
            }
        )

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SourceRef":
        return cls(**value)


@dataclass(frozen=True, slots=True)
class ContextAtom:
    atom_id: str
    source: SourceRef
    address: FrameworkAddress
    exact_text: str
    normalized_text: str
    origin_class: OriginClass
    truth: TruthState
    lifecycle: LifecycleState
    tags: tuple[str, ...]
    dependencies: tuple[str, ...]
    witnesses: tuple[str, ...]
    lineage_return: str
    payload_digest: str

    @classmethod
    def build(
        cls,
        *,
        source: SourceRef,
        address: FrameworkAddress,
        exact_text: str,
        origin_class: OriginClass,
        truth: TruthState = TruthState.RESID,
        lifecycle: LifecycleState = LifecycleState.SOURCE_BOUND,
        tags: tuple[str, ...] = (),
        dependencies: tuple[str, ...] = (),
        witnesses: tuple[str, ...] = (),
        lineage_return: str | None = None,
    ) -> "ContextAtom":
        if not exact_text.strip():
            raise ValueError("context atom text is required")
        if truth == TruthState.OK and not witnesses:
            raise ValueError("OK requires at least one explicit witness")
        if lifecycle == LifecycleState.PROMOTED and "IC10_AUTHORIZED" not in tags:
            raise ValueError("direct promotion is forbidden without IC10_AUTHORIZED")
        atom_id = canonical_digest(
            {
                "type": "KC144.InternalNav.ContextAtom.Identity.V1",
                "source_key": source.key,
                "address": address.key,
            }
        )
        payload_digest = canonical_digest(
            {
                "exact_text": exact_text,
                "origin_class": origin_class.value,
                "truth": truth.value,
                "tags": sorted(tags),
                "dependencies": sorted(dependencies),
                "witnesses": sorted(witnesses),
            }
        )
        return cls(
            atom_id=atom_id,
            source=source,
            address=address,
            exact_text=exact_text,
            normalized_text=normalize_text(exact_text),
            origin_class=origin_class,
            truth=truth,
            lifecycle=lifecycle,
            tags=tuple(sorted(set(tags))),
            dependencies=tuple(sorted(set(dependencies))),
            witnesses=tuple(sorted(set(witnesses))),
            lineage_return=lineage_return or source.locator,
            payload_digest=payload_digest,
        )

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ContextAtom":
        return cls.build(
            source=SourceRef.from_dict(value["source"]),
            address=FrameworkAddress.from_dict(value["address"]),
            exact_text=value["exact_text"],
            origin_class=OriginClass(value["origin_class"]),
            truth=TruthState(value.get("truth", "RESID")),
            lifecycle=LifecycleState(value.get("lifecycle", "SOURCE_BOUND")),
            tags=tuple(value.get("tags", ())),
            dependencies=tuple(value.get("dependencies", ())),
            witnesses=tuple(value.get("witnesses", ())),
            lineage_return=value.get("lineage_return"),
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["origin_class"] = self.origin_class.value
        value["truth"] = self.truth.value
        value["lifecycle"] = self.lifecycle.value
        value["address"]["key"] = self.address.key
        value["address"]["grid"] = self.address.grid
        value["source"]["key"] = self.source.key
        return value


@dataclass(frozen=True, slots=True)
class QueryBundle:
    query_id: str
    goal: str
    terms: tuple[str, ...]
    domains: tuple[str, ...] = ()
    operators: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()
    boundaries: tuple[str, ...] = ()
    evidence_floor: TruthState = TruthState.RESID
    start_coordinates: tuple[str, ...] = ()
    route_budget: int = 27
    return_mode: str = "SYNTHESIS_PACKET"

    def __post_init__(self) -> None:
        if not self.query_id or not self.goal:
            raise ValueError("query_id and goal are required")
        if self.route_budget < 1:
            raise ValueError("route_budget must be positive")

    @classmethod
    def build(
        cls,
        *,
        goal: str,
        terms: tuple[str, ...],
        domains: tuple[str, ...] = (),
        operators: tuple[str, ...] = (),
        invariants: tuple[str, ...] = (),
        boundaries: tuple[str, ...] = (),
        evidence_floor: TruthState = TruthState.RESID,
        start_coordinates: tuple[str, ...] = (),
        route_budget: int = 27,
        return_mode: str = "SYNTHESIS_PACKET",
    ) -> "QueryBundle":
        body = {
            "goal": goal,
            "terms": sorted(set(terms)),
            "domains": sorted(set(domains)),
            "operators": sorted(set(operators)),
            "invariants": sorted(set(invariants)),
            "boundaries": sorted(set(boundaries)),
            "evidence_floor": evidence_floor.value,
            "start_coordinates": sorted(set(start_coordinates)),
            "route_budget": route_budget,
            "return_mode": return_mode,
        }
        return cls(
            query_id=canonical_digest({"type": "KC144.QueryBundle.V1", **body}),
            goal=goal,
            terms=tuple(body["terms"]),
            domains=tuple(body["domains"]),
            operators=tuple(body["operators"]),
            invariants=tuple(body["invariants"]),
            boundaries=tuple(body["boundaries"]),
            evidence_floor=evidence_floor,
            start_coordinates=tuple(body["start_coordinates"]),
            route_budget=route_budget,
            return_mode=return_mode,
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["evidence_floor"] = self.evidence_floor.value
        return value

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "QueryBundle":
        return cls(
            query_id=value["query_id"],
            goal=value["goal"],
            terms=tuple(value.get("terms", ())),
            domains=tuple(value.get("domains", ())),
            operators=tuple(value.get("operators", ())),
            invariants=tuple(value.get("invariants", ())),
            boundaries=tuple(value.get("boundaries", ())),
            evidence_floor=TruthState(value.get("evidence_floor", "RESID")),
            start_coordinates=tuple(value.get("start_coordinates", ())),
            route_budget=int(value.get("route_budget", 27)),
            return_mode=value.get("return_mode", "SYNTHESIS_PACKET"),
        )


@dataclass(frozen=True, slots=True)
class RouteHit:
    atom_id: str
    address: str
    score: float
    reasons: tuple[str, ...]
    path: tuple[str, ...]
    invariants: tuple[str, ...]
    defects: tuple[str, ...]
    witnesses: tuple[str, ...]
    truth: TruthState
    evidence_root: str


@dataclass(frozen=True, slots=True)
class SynthesisCluster:
    cluster_id: str
    normalized_claim: str
    atom_ids: tuple[str, ...]
    independent_roots: tuple[str, ...]
    truth: TruthState
    active_conflicts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SynthesisPacket:
    query_id: str
    selected: tuple[RouteHit, ...]
    suspended_branches: tuple[str, ...]
    clusters: tuple[SynthesisCluster, ...]
    conflicts: tuple[str, ...]
    unresolved: tuple[str, ...]
    receipt_digest: str
    next_seed: str


@dataclass(frozen=True, slots=True)
class ReplayPacket:
    query: QueryBundle
    visited_nodes: tuple[str, ...]
    route_signature: str
    branch_ledger: tuple[tuple[str, str], ...]
    observer_states: tuple[str, ...]
    results: tuple[str, ...]
    unresolved: tuple[str, ...]
    next_seed: str
    terminal_receipt_digest: str
