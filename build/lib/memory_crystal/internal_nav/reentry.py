from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from memory_crystal.p03.model import canonical_digest, kc144_gid_to_grid

from .model import QueryBundle, ReplayPacket, SynthesisPacket
from .store import NavStore


class ReentryStatus(StrEnum):
    VALID = "VALID"
    VALID_WITH_DRIFT = "VALID_WITH_DRIFT"
    STALE = "STALE"
    AMBIGUOUS = "AMBIGUOUS"
    ORPHANED = "ORPHANED"
    CORRUPT = "CORRUPT"
    FOREIGN_VERSION = "FOREIGN_VERSION"


class CoverageState(StrEnum):
    PRESENT = "PRESENT"
    MISSING_NODE = "MISSING_NODE"
    SOURCE_UNRESOLVED = "SOURCE_UNRESOLVED"


FAMILY_RANGES = (
    ("ROOT_CONTROL", 1, 6),
    ("ADAPTIVE_BINARY_X16", 7, 22),
    ("BR21", 23, 43),
    ("AQM_F37", 44, 80),
    ("IC10", 81, 90),
    ("KC15", 91, 105),
    ("KC27", 106, 132),
    ("SSN", 133, 144),
)


def family_for_gid(gid: int) -> str:
    for family, start, end in FAMILY_RANGES:
        if start <= gid <= end:
            return family
    raise ValueError(gid)


@dataclass(frozen=True, slots=True)
class CoverageCell:
    gid: int
    grid: str
    family: str
    state: CoverageState
    atom_ids: tuple[str, ...]
    source_roots: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CoverageReport:
    cells: tuple[CoverageCell, ...]
    node_coverage: float
    edge_coverage: float | None
    observed_return_coverage: float | None
    total_return_coverage: float | None
    source_or_typed_gap_coverage: float
    replay_coverage: float | None
    projective_coverage: float
    observed_nodes: int
    expected_nodes: int
    observed_edges: int
    expected_edges: int | None
    observed_scan_seats: int
    expected_scan_seats: int
    solid_state_candidate: bool
    eligibility_defects: tuple[str, ...]
    digest: str


@dataclass(frozen=True, slots=True)
class HealingEvent:
    event_id: str
    gid: int
    defect: str
    location: str
    before: str
    patch: str
    after: str
    verifier: str
    rollback: str
    residual_gap: str
    status: str = "OPEN_TYPED_GAP"


@dataclass(frozen=True, slots=True)
class SessionClose:
    session_id: str
    checkpoint_id: str
    query_id: str
    result_clusters: int
    unresolved: tuple[str, ...]
    receipt_head: str
    coverage_digest: str
    next_seed: str
    status: str


@dataclass(frozen=True, slots=True)
class ReentryPacket:
    checkpoint_id: str
    status: ReentryStatus
    query: QueryBundle | None
    restored_frontier: tuple[str, ...]
    defects: tuple[str, ...]
    rollback_target: str | None
    next_operation: str | None
    checkpoint_digest: str | None


@dataclass(frozen=True, slots=True)
class RollbackPacket:
    target_checkpoint: str
    current_checkpoint: str | None
    restore_atoms: tuple[str, ...]
    supersede_atoms: tuple[str, ...]
    restore_edges: tuple[str, ...]
    supersede_edges: tuple[str, ...]
    restore_atlas: tuple[str, ...]
    supersede_atlas: tuple[str, ...]
    restore_observations: tuple[str, ...]
    supersede_observations: tuple[str, ...]
    restore_claims: tuple[str, ...]
    supersede_claims: tuple[str, ...]
    mode: str = "APPEND_ONLY_COMPENSATING_ROLLBACK"


class CoverageAuditor:
    def __init__(self, store: NavStore) -> None:
        self.store = store

    def audit(
        self,
        *,
        expected_edges: int | None = None,
        required_replays: int | None = None,
        successful_replays: int = 0,
        observed_scan_seats: int = 0,
        expected_scan_seats: int = 13320,
    ) -> CoverageReport:
        atoms = self.store.atoms()
        by_gid: dict[int, list[Any]] = {}
        for atom in atoms:
            by_gid.setdefault(atom.address.gid, []).append(atom)
        typed_gaps = self.store.healed_gap_gids()
        cells: list[CoverageCell] = []
        for gid in range(1, 145):
            row, column = kc144_gid_to_grid(gid)
            found = by_gid.get(gid, [])
            if found:
                state = CoverageState.PRESENT
            elif gid in typed_gaps:
                state = CoverageState.SOURCE_UNRESOLVED
            else:
                state = CoverageState.MISSING_NODE
            cells.append(
                CoverageCell(
                    gid=gid,
                    grid=f"R{row:02d}C{column:02d}",
                    family=family_for_gid(gid),
                    state=state,
                    atom_ids=tuple(sorted(atom.atom_id for atom in found)),
                    source_roots=tuple(
                        sorted({atom.source.evidence_root for atom in found})
                    ),
                )
            )
        observed_nodes = len(by_gid)
        edges = self.store.edges()
        observed_edges = len(edges)
        node_coverage = observed_nodes / 144
        edge_coverage = (
            observed_edges / expected_edges if expected_edges not in (None, 0) else None
        )
        observed_return_coverage = (
            sum(bool(edge.inverse_relation and edge.return_address) for edge in edges)
            / observed_edges
            if observed_edges
            else None
        )
        total_return_coverage = (
            sum(bool(edge.inverse_relation and edge.return_address) for edge in edges)
            / expected_edges
            if expected_edges not in (None, 0)
            else None
        )
        replay_coverage = (
            successful_replays / required_replays
            if required_replays not in (None, 0)
            else None
        )
        projective_coverage = observed_scan_seats / expected_scan_seats
        source_coverage = sum(
            cell.state in {CoverageState.PRESENT, CoverageState.SOURCE_UNRESOLVED}
            for cell in cells
        ) / 144
        defects: list[str] = []
        if node_coverage != 1:
            defects.append("NODE_COVERAGE_INCOMPLETE")
        if expected_edges is None:
            defects.append("FROZEN_EDGE_MANIFEST_UNBOUND")
        elif edge_coverage != 1:
            defects.append("EDGE_COVERAGE_INCOMPLETE")
        if total_return_coverage is None:
            defects.append("TOTAL_RETURN_DENOMINATOR_UNBOUND")
        elif total_return_coverage != 1:
            defects.append("RETURN_COVERAGE_INCOMPLETE")
        if source_coverage != 1:
            defects.append("SOURCE_OR_TYPED_GAP_COVERAGE_INCOMPLETE")
        if required_replays is None:
            defects.append("REQUIRED_REPLAY_MANIFEST_UNBOUND")
        elif replay_coverage != 1:
            defects.append("REPLAY_COVERAGE_INCOMPLETE")
        if projective_coverage != 1:
            defects.append("PROJECTIVE_COVERAGE_INCOMPLETE")
        body = {
            "cells": [
                {
                    "gid": cell.gid,
                    "state": cell.state.value,
                    "atom_ids": cell.atom_ids,
                }
                for cell in cells
            ],
            "node_coverage": node_coverage,
            "edge_coverage": edge_coverage,
            "return_coverage": total_return_coverage,
            "source_coverage": source_coverage,
            "replay_coverage": replay_coverage,
            "projective_coverage": projective_coverage,
            "defects": defects,
        }
        return CoverageReport(
            cells=tuple(cells),
            node_coverage=node_coverage,
            edge_coverage=edge_coverage,
            observed_return_coverage=observed_return_coverage,
            total_return_coverage=total_return_coverage,
            source_or_typed_gap_coverage=source_coverage,
            replay_coverage=replay_coverage,
            projective_coverage=projective_coverage,
            observed_nodes=observed_nodes,
            expected_nodes=144,
            observed_edges=observed_edges,
            expected_edges=expected_edges,
            observed_scan_seats=observed_scan_seats,
            expected_scan_seats=expected_scan_seats,
            solid_state_candidate=not defects,
            eligibility_defects=tuple(defects),
            digest=canonical_digest(body),
        )


class HealingPlanner:
    def __init__(self, store: NavStore) -> None:
        self.store = store

    def type_missing_gaps(
        self, report: CoverageReport, *, limit: int = 144
    ) -> tuple[HealingEvent, ...]:
        missing = [
            cell for cell in report.cells if cell.state == CoverageState.MISSING_NODE
        ]
        missing.sort(
            key=lambda cell: (
                0 if cell.family == "ROOT_CONTROL" else 1,
                cell.gid,
            )
        )
        events: list[HealingEvent] = []
        for cell in missing[:limit]:
            body = {
                "gid": cell.gid,
                "defect": "MISSING_NODE",
                "location": f"KC144.V1::GID{cell.gid:03d}",
                "before": "UNTYPED_ABSENCE",
                "patch": "REGISTER_TYPED_SOURCE_GAP",
                "after": "SOURCE_UNRESOLVED",
                "verifier": "KC144.SSN-M11.COVERAGE-AUDITOR",
                "rollback": "APPEND_SUPERSEDING_GAP_EVENT",
                "residual_gap": "SOURCE_CONTENT_AND_STATION_BODY_STILL_MISSING",
                "status": "OPEN_TYPED_GAP",
            }
            event = HealingEvent(
                event_id=canonical_digest(
                    {"schema": "KC144.HealingEvent.V1", **body}
                ),
                **body,
            )
            self.store.save_healing_event(asdict(event))
            events.append(event)
        return tuple(events)


class SessionManager:
    def __init__(self, store: NavStore) -> None:
        self.store = store

    def close(
        self,
        query: QueryBundle,
        synthesis: SynthesisPacket,
        replay: ReplayPacket,
        coverage: CoverageReport,
        *,
        epoch: str = "KC144.V1",
        atlas_version: str = "KC144.V1",
    ) -> SessionClose:
        state = self.store.state_manifest()
        checkpoint_id = canonical_digest(
            {
                "schema": "KC144.Checkpoint.Identity.V1",
                "query_id": query.query_id,
                "receipt_head": synthesis.receipt_digest,
                "snapshot_id": state["digest"],
            }
        )
        existing = self.store.checkpoint(checkpoint_id)
        if existing is None:
            parent = self.store.latest_checkpoint_id()
            checkpoint_body = {
                "schema": "KC144.Checkpoint.V1",
                "parent_checkpoint": parent,
                "atlas_version": atlas_version,
                "epoch": epoch,
                "snapshot_id": state["digest"],
                "query": query.to_dict(),
                "active_coordinates": sorted(
                    {hit.address for hit in synthesis.selected}
                ),
                "active_branches": [hit.atom_id for hit in synthesis.selected],
                "deferred_branch_generators": list(synthesis.suspended_branches),
                "quarantined_branches": list(synthesis.conflicts),
                "route_signature": replay.route_signature,
                "source_roots": sorted(
                    {hit.evidence_root for hit in synthesis.selected}
                ),
                "invariants": list(query.invariants),
                "defects": list(synthesis.unresolved),
                "missing_nodes": [
                    cell.gid
                    for cell in coverage.cells
                    if cell.state != CoverageState.PRESENT
                ],
                "return_target": "KC144.V1::GID006::H06",
                "next_operation": synthesis.next_seed,
                "receipt_head": synthesis.receipt_digest,
                "atom_digests": state["atoms"],
                "edge_ids": list(state["edges"]),
                "atlas_digests": state["atlas"],
                "observation_digests": state["observations"],
                "claim_ids": list(state["claims"]),
                "rollback_target": parent,
                "reconstruction_floor": "CONTROL_HUBS+PREDECESSOR+SUCCESSOR+ROUTE+DEFECT+RETURN",
            }
            checkpoint = {"checkpoint_id": checkpoint_id, **checkpoint_body}
            checkpoint["digest"] = canonical_digest(checkpoint)
            self.store.save_checkpoint(checkpoint)
        elif (
            canonical_digest(existing.get("query")) != canonical_digest(query.to_dict())
            or existing.get("receipt_head") != synthesis.receipt_digest
            or existing.get("snapshot_id") != state["digest"]
        ):
            raise ValueError(f"checkpoint identity collision: {checkpoint_id}")
        return SessionClose(
            session_id=canonical_digest(
                {
                    "checkpoint": checkpoint_id,
                    "query": query.query_id,
                    "receipt": synthesis.receipt_digest,
                }
            ),
            checkpoint_id=checkpoint_id,
            query_id=query.query_id,
            result_clusters=len(synthesis.clusters),
            unresolved=synthesis.unresolved,
            receipt_head=synthesis.receipt_digest,
            coverage_digest=coverage.digest,
            next_seed=synthesis.next_seed,
            status="CLOSED_WITH_RESIDUE" if coverage.eligibility_defects else "CLOSED",
        )

    def warm_reentry(self, checkpoint_id: str) -> ReentryPacket:
        checkpoint = self.store.checkpoint(checkpoint_id)
        if checkpoint is None:
            return ReentryPacket(
                checkpoint_id=checkpoint_id,
                status=ReentryStatus.ORPHANED,
                query=None,
                restored_frontier=(),
                defects=("CHECKPOINT_NOT_FOUND",),
                rollback_target=None,
                next_operation=None,
                checkpoint_digest=None,
            )
        stored_digest = checkpoint.pop("digest", None)
        computed_digest = canonical_digest(checkpoint)
        checkpoint["digest"] = stored_digest
        if stored_digest != computed_digest:
            return ReentryPacket(
                checkpoint_id=checkpoint_id,
                status=ReentryStatus.CORRUPT,
                query=None,
                restored_frontier=(),
                defects=("CHECKPOINT_DIGEST_MISMATCH",),
                rollback_target=checkpoint.get("rollback_target"),
                next_operation=None,
                checkpoint_digest=stored_digest,
            )
        defects: list[str] = []
        state = self.store.state_manifest()
        saved_atoms = checkpoint["atom_digests"]
        current_atoms = state["atoms"]
        missing_atoms = sorted(set(saved_atoms) - set(current_atoms))
        changed_atoms = sorted(
            atom_id
            for atom_id in set(saved_atoms) & set(current_atoms)
            if saved_atoms[atom_id] != current_atoms[atom_id]
        )
        missing_edges = sorted(set(checkpoint["edge_ids"]) - set(state["edges"]))
        new_atoms = sorted(set(current_atoms) - set(saved_atoms))
        new_edges = sorted(set(state["edges"]) - set(checkpoint["edge_ids"]))
        saved_atlas = checkpoint.get("atlas_digests", {})
        current_atlas = state.get("atlas", {})
        missing_atlas = sorted(set(saved_atlas) - set(current_atlas))
        changed_atlas = sorted(
            key
            for key in set(saved_atlas) & set(current_atlas)
            if saved_atlas[key] != current_atlas[key]
        )
        saved_observations = checkpoint.get("observation_digests", {})
        current_observations = state.get("observations", {})
        missing_observations = sorted(
            set(saved_observations) - set(current_observations)
        )
        changed_observations = sorted(
            key
            for key in set(saved_observations) & set(current_observations)
            if saved_observations[key] != current_observations[key]
        )
        saved_claims = set(checkpoint.get("claim_ids", ()))
        current_claims = set(state.get("claims", ()))
        missing_claims = sorted(saved_claims - current_claims)
        new_context = (
            sorted(set(current_atlas) - set(saved_atlas))
            + sorted(set(current_observations) - set(saved_observations))
            + sorted(current_claims - saved_claims)
        )
        if missing_atoms:
            defects.append(f"MEMORY_DECAY::MISSING_ATOMS::{len(missing_atoms)}")
        if changed_atoms:
            defects.append(f"MEMORY_DECAY::CHANGED_ATOMS::{len(changed_atoms)}")
        if missing_edges:
            defects.append(f"BROKEN_ROUTE::MISSING_EDGES::{len(missing_edges)}")
        if missing_atlas or changed_atlas:
            defects.append(
                "ATLAS_DECAY"
                f"::MISSING={len(missing_atlas)}"
                f"::CHANGED={len(changed_atlas)}"
            )
        if missing_observations or changed_observations:
            defects.append(
                "SOURCE_DECAY"
                f"::MISSING={len(missing_observations)}"
                f"::CHANGED={len(changed_observations)}"
            )
        if missing_claims:
            defects.append(f"CLAIM_DECAY::MISSING={len(missing_claims)}")
        receipt_ok, receipt_errors = self.store.verify_receipt_prefix(
            checkpoint["receipt_head"]
        )
        if not receipt_ok:
            defects.extend(f"REPLAY_DIVERGENCE::{error}" for error in receipt_errors)
        if checkpoint["atlas_version"] != "KC144.V1":
            status = ReentryStatus.FOREIGN_VERSION
        elif (
            missing_atoms
            or changed_atoms
            or missing_edges
            or missing_atlas
            or changed_atlas
            or missing_observations
            or changed_observations
            or missing_claims
            or not receipt_ok
        ):
            status = ReentryStatus.STALE
        elif new_atoms or new_edges or new_context:
            status = ReentryStatus.VALID_WITH_DRIFT
            defects.append(
                "MONOTONIC_DRIFT"
                f"::NEW_ATOMS={len(new_atoms)}"
                f"::NEW_EDGES={len(new_edges)}"
                f"::NEW_CONTEXT={len(new_context)}"
            )
        else:
            status = ReentryStatus.VALID
        frontier = tuple(
            checkpoint["deferred_branch_generators"]
            or checkpoint["active_branches"]
        )
        return ReentryPacket(
            checkpoint_id=checkpoint_id,
            status=status,
            query=QueryBundle.from_dict(checkpoint["query"]),
            restored_frontier=frontier,
            defects=tuple(defects),
            rollback_target=checkpoint.get("rollback_target"),
            next_operation=checkpoint.get("next_operation"),
            checkpoint_digest=stored_digest,
        )

    def rollback_packet(self, target_checkpoint: str) -> RollbackPacket:
        target = self.store.checkpoint(target_checkpoint)
        if target is None:
            raise KeyError(target_checkpoint)
        current_id = self.store.latest_checkpoint_id()
        current = self.store.state_manifest()
        target_atoms = set(target["atom_digests"])
        current_atoms = set(current["atoms"])
        target_edges = set(target["edge_ids"])
        current_edges = set(current["edges"])
        target_atlas = target.get("atlas_digests", {})
        current_atlas = current.get("atlas", {})
        changed_atlas = {
            key
            for key in set(target_atlas) & set(current_atlas)
            if target_atlas[key] != current_atlas[key]
        }
        target_observations = target.get("observation_digests", {})
        current_observations = current.get("observations", {})
        changed_observations = {
            key
            for key in set(target_observations) & set(current_observations)
            if target_observations[key] != current_observations[key]
        }
        target_claims = set(target.get("claim_ids", ()))
        current_claims = set(current.get("claims", ()))
        return RollbackPacket(
            target_checkpoint=target_checkpoint,
            current_checkpoint=current_id,
            restore_atoms=tuple(sorted(target_atoms - current_atoms)),
            supersede_atoms=tuple(sorted(current_atoms - target_atoms)),
            restore_edges=tuple(sorted(target_edges - current_edges)),
            supersede_edges=tuple(sorted(current_edges - target_edges)),
            restore_atlas=tuple(
                sorted((set(target_atlas) - set(current_atlas)) | changed_atlas)
            ),
            supersede_atlas=tuple(
                sorted((set(current_atlas) - set(target_atlas)) | changed_atlas)
            ),
            restore_observations=tuple(
                sorted(
                    (set(target_observations) - set(current_observations))
                    | changed_observations
                )
            ),
            supersede_observations=tuple(
                sorted(
                    (set(current_observations) - set(target_observations))
                    | changed_observations
                )
            ),
            restore_claims=tuple(sorted(target_claims - current_claims)),
            supersede_claims=tuple(sorted(current_claims - target_claims)),
        )
