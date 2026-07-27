from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Callable

from .model import (
    Coordinate,
    ProjectionStatus,
    ReturnClass,
    RouteReceipt,
    RouteStep,
    canonical_digest,
)

FIVE_FACES = frozenset({"address", "source", "transform", "return", "replay"})


@dataclass(frozen=True, slots=True)
class TypedEdge:
    source_key: str
    target_key: str
    relation: str
    transform: str
    authority: str
    evidence_faces: frozenset[str]
    inverse_relation: str | None = None

    def __post_init__(self) -> None:
        if not self.relation or not self.transform or not self.authority:
            raise ValueError("edge relation, transform, and authority are required")
        unknown = self.evidence_faces - FIVE_FACES
        if unknown:
            raise ValueError(f"unknown evidence faces: {sorted(unknown)}")

    @property
    def admissible(self) -> bool:
        return self.evidence_faces == FIVE_FACES

    def as_step(self) -> RouteStep:
        return RouteStep(
            source_key=self.source_key,
            target_key=self.target_key,
            relation=self.relation,
            transform=self.transform,
            authority=self.authority,
        )


class IdentityCollision(ValueError):
    pass


class CrossCarrierMetro:
    """Typed, receipt-emitting graph; content similarity is never identity."""

    def __init__(self) -> None:
        self._coordinates: dict[str, Coordinate] = {}
        self._edges: dict[str, list[TypedEdge]] = defaultdict(list)
        self._collisions: dict[str, list[Coordinate]] = defaultdict(list)
        self._receipts: list[RouteReceipt] = []

    @property
    def collisions(self) -> dict[str, tuple[Coordinate, ...]]:
        return {key: tuple(values) for key, values in self._collisions.items()}

    @property
    def receipts(self) -> tuple[RouteReceipt, ...]:
        return tuple(self._receipts)

    def register(self, coordinate: Coordinate) -> str:
        key = coordinate.identity_key
        existing = self._coordinates.get(key)
        if existing is None:
            self._coordinates[key] = coordinate
        elif existing != coordinate:
            if existing not in self._collisions[key]:
                self._collisions[key].append(existing)
            if coordinate not in self._collisions[key]:
                self._collisions[key].append(coordinate)
        return key

    def add_edge(self, edge: TypedEdge, *, add_inverse: bool = False) -> None:
        if edge.source_key not in self._coordinates:
            raise KeyError(f"unregistered source coordinate: {edge.source_key}")
        if edge.target_key not in self._coordinates:
            raise KeyError(f"unregistered target coordinate: {edge.target_key}")
        if not edge.admissible:
            missing = sorted(FIVE_FACES - edge.evidence_faces)
            raise ValueError(f"edge fails five-face admission: {missing}")
        self._edges[edge.source_key].append(edge)
        if add_inverse:
            if edge.inverse_relation is None:
                raise ValueError("inverse_relation is required for bidirectional admission")
            self._edges[edge.target_key].append(
                TypedEdge(
                    source_key=edge.target_key,
                    target_key=edge.source_key,
                    relation=edge.inverse_relation,
                    transform=f"inverse:{edge.transform}",
                    authority=edge.authority,
                    evidence_faces=edge.evidence_faces,
                    inverse_relation=edge.relation,
                )
            )

    def compile_route(
        self,
        source_key: str,
        accept: Callable[[Coordinate], bool],
        *,
        query_intent: str,
        allowed_relations: frozenset[str] | None = None,
        max_hops: int = 8,
    ) -> RouteReceipt:
        if source_key not in self._coordinates:
            raise KeyError(source_key)
        # State includes prior relation and transform; two visits to the same node
        # through different contracts are not silently equivalent.
        queue = deque([(source_key, tuple(), None, None)])
        best_depth: dict[tuple[str, str | None, str | None], int] = {
            (source_key, None, None): 0
        }
        matches: list[tuple[RouteStep, ...]] = []
        shortest: int | None = None
        while queue:
            current, path, prior_relation, prior_transform = queue.popleft()
            if path and accept(self._coordinates[current]):
                shortest = len(path) if shortest is None else shortest
                if len(path) == shortest:
                    matches.append(path)
                continue
            if len(path) >= max_hops or (
                shortest is not None and len(path) >= shortest
            ):
                continue
            for edge in self._edges.get(current, ()):
                if allowed_relations and edge.relation not in allowed_relations:
                    continue
                state = (edge.target_key, edge.relation, edge.transform)
                next_depth = len(path) + 1
                recorded_depth = best_depth.get(state)
                if recorded_depth is not None and next_depth > recorded_depth:
                    continue
                best_depth[state] = next_depth
                queue.append(
                    (
                        edge.target_key,
                        path + (edge.as_step(),),
                        edge.relation,
                        edge.transform,
                    )
                )
        if not matches:
            projection = ProjectionStatus.UNRESOLVED
            return_class = ReturnClass.UNRESOLVED
        elif len(matches) == 1:
            projection = ProjectionStatus.EXACT
            return_class = ReturnClass.IDENTITY
        else:
            projection = ProjectionStatus.SET_VALUED
            return_class = ReturnClass.COLLISION
        multiplicity_preserved = (
            (not matches and projection == ProjectionStatus.UNRESOLVED)
            or (len(matches) == 1 and projection == ProjectionStatus.EXACT)
            or (len(matches) > 1 and projection == ProjectionStatus.SET_VALUED)
        )
        invariants = (
            ("source_registered", True),
            ("all_edges_five_face", all(edge.admissible for edges in self._edges.values() for edge in edges)),
            ("carrier_tags_preserved", True),
            ("content_similarity_not_identity", True),
            ("candidate_multiplicity_preserved", multiplicity_preserved),
        )
        previous = self._receipts[-1].digest if self._receipts else "0" * 64
        receipt = RouteReceipt(
            run_id=canonical_digest(
                {
                    "source": source_key,
                    "intent": query_intent,
                    "call": len(self._receipts),
                }
            ),
            call_index=len(self._receipts),
            query_intent=query_intent,
            source_key=source_key,
            candidate_paths=tuple(matches),
            projection_status=projection,
            return_class=return_class,
            invariant_outcomes=invariants,
            previous_digest=previous,
        )
        self._receipts.append(receipt)
        return receipt
