from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import asdict
from typing import Iterable

from memory_crystal.p03.model import canonical_digest

from .model import (
    ContextAtom,
    QueryBundle,
    ReplayPacket,
    RouteHit,
    SynthesisCluster,
    SynthesisPacket,
    TruthState,
    normalize_text,
    truth_meet,
)
from .store import EdgeRecord, NavStore

EVIDENCE_LEVEL = {
    TruthState.FAIL: 0,
    TruthState.RESID: 1,
    TruthState.AMBIG: 1,
    TruthState.NEAR: 2,
    TruthState.OK: 3,
}


class InternalNavigator:
    def __init__(self, store: NavStore) -> None:
        self.store = store

    def ingest(self, atoms: Iterable[ContextAtom]) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for atom in atoms:
            counts[self.store.ingest_atom(atom)] += 1
        return dict(counts)

    def query(self, bundle: QueryBundle) -> SynthesisPacket:
        atoms = self.store.atoms()
        paths = self._route_paths(bundle, atoms)
        candidates: list[RouteHit] = []
        terms = tuple(normalize_text(term) for term in bundle.terms if normalize_text(term))
        for atom in atoms:
            if EVIDENCE_LEVEL[atom.truth] < EVIDENCE_LEVEL[bundle.evidence_floor]:
                continue
            score = 0.0
            reasons: list[str] = []
            if atom.address.key in bundle.start_coordinates:
                score += 1.0
                reasons.append("EXACT-START::1.00")
            if any(term == normalize_text(atom.address.key) for term in terms):
                score += 0.98
                reasons.append("EXACT-LOOKUP-KEY::0.98")
            if atom.atom_id in paths:
                hops = max(0, len(paths[atom.atom_id]) - 1)
                graph_score = 0.82 / (1 + hops)
                score += graph_score
                reasons.append(f"GRAPH-CONTINUITY::{graph_score:.4f}")
            if bundle.domains and atom.address.domain in bundle.domains:
                score += 0.75
                reasons.append("DOMAIN-MATCH::0.75")
            matched = [term for term in terms if term and term in atom.normalized_text]
            if terms and matched:
                semantic_score = 0.45 * len(set(matched)) / len(set(terms))
                score += semantic_score
                reasons.append(f"SEMANTIC-CONTINUITY::{semantic_score:.4f}")
            operator_matches = set(bundle.operators) & set(atom.tags)
            if operator_matches:
                score += 0.60
                reasons.append("OPERATOR-MATCH::0.60")
            if score == 0:
                continue
            path = paths.get(atom.atom_id, (atom.atom_id,))
            candidates.append(
                RouteHit(
                    atom_id=atom.atom_id,
                    address=atom.address.key,
                    score=round(score, 8),
                    reasons=tuple(reasons),
                    path=path,
                    invariants=tuple(bundle.invariants),
                    defects=(),
                    witnesses=atom.witnesses,
                    truth=atom.truth,
                    evidence_root=atom.source.evidence_root,
                )
            )
        candidates.sort(key=lambda hit: (-hit.score, hit.address, hit.atom_id))
        selected = tuple(candidates[: bundle.route_budget])
        suspended = tuple(hit.atom_id for hit in candidates[bundle.route_budget :])
        clusters, conflicts, unresolved = self._synthesize(selected)
        receipt_body = {
            "query": bundle.to_dict(),
            "selected": [asdict(hit) for hit in selected],
            "suspended_branches": suspended,
            "clusters": [asdict(cluster) for cluster in clusters],
            "conflicts": conflicts,
            "unresolved": unresolved,
            "laws": [
                "ranking_schedules_attention_not_truth",
                "budget_exhaustion_suspends_not_deletes",
                "same_text_does_not_merge_source_identity",
                "derived_copy_does_not_add_independent_root",
                "no_direct_route_to_promoted",
            ],
        }
        receipt_digest = self.store.append_receipt(bundle.query_id, receipt_body)
        return SynthesisPacket(
            query_id=bundle.query_id,
            selected=selected,
            suspended_branches=suspended,
            clusters=clusters,
            conflicts=conflicts,
            unresolved=unresolved,
            receipt_digest=receipt_digest,
            next_seed=f"KC144.INTERNAL-NAV::{bundle.query_id[:16]}::SUCCESSOR",
        )

    def close_session(
        self,
        bundle: QueryBundle,
        packet: SynthesisPacket,
        *,
        observer_states: tuple[str, ...] = ("V80::DEFAULT",),
    ) -> ReplayPacket:
        visited = tuple(dict.fromkeys(node for hit in packet.selected for node in hit.path))
        branch_ledger = tuple(
            [(atom_id, "SELECTED") for atom_id in (hit.atom_id for hit in packet.selected)]
            + [(atom_id, "SUSPENDED_BUDGET") for atom_id in packet.suspended_branches]
        )
        return ReplayPacket(
            query=bundle,
            visited_nodes=visited,
            route_signature=canonical_digest(
                {
                    "query_id": bundle.query_id,
                    "ordered_paths": [hit.path for hit in packet.selected],
                    "terminal_receipt": packet.receipt_digest,
                }
            ),
            branch_ledger=branch_ledger,
            observer_states=observer_states,
            results=tuple(cluster.cluster_id for cluster in packet.clusters),
            unresolved=packet.unresolved,
            next_seed=packet.next_seed,
            terminal_receipt_digest=packet.receipt_digest,
        )

    def _route_paths(
        self, bundle: QueryBundle, atoms: list[ContextAtom]
    ) -> dict[str, tuple[str, ...]]:
        by_address: dict[str, list[str]] = defaultdict(list)
        for atom in atoms:
            by_address[atom.address.key].append(atom.atom_id)
        starts = [
            atom_id
            for address in bundle.start_coordinates
            for atom_id in by_address.get(address, ())
        ]
        if not starts:
            return {}
        adjacency: dict[str, list[str]] = defaultdict(list)
        for edge in self.store.edges():
            if edge.status not in {"CERTIFIED", "PASS_WITH_DEFECT"}:
                continue
            adjacency[edge.source_atom].append(edge.target_atom)
            adjacency[edge.target_atom].append(edge.source_atom)
        paths = {start: (start,) for start in starts}
        queue = deque(starts)
        while queue:
            current = queue.popleft()
            for target in sorted(adjacency.get(current, ())):
                candidate = paths[current] + (target,)
                existing = paths.get(target)
                if existing is None or len(candidate) < len(existing):
                    paths[target] = candidate
                    queue.append(target)
        return paths

    def _synthesize(
        self, selected: tuple[RouteHit, ...]
    ) -> tuple[tuple[SynthesisCluster, ...], tuple[str, ...], tuple[str, ...]]:
        atoms = {hit.atom_id: self.store.atom(hit.atom_id) for hit in selected}
        active_conflicts = self.store.active_conflicts()
        conflict_by_atom: dict[str, list[str]] = defaultdict(list)
        for conflict in active_conflicts:
            conflict_by_atom[conflict["left_atom"]].append(conflict["conflict_id"])
            conflict_by_atom[conflict["right_atom"]].append(conflict["conflict_id"])
        groups: dict[str, list[ContextAtom]] = defaultdict(list)
        for atom in atoms.values():
            if atom is not None:
                groups[atom.normalized_text].append(atom)
        clusters: list[SynthesisCluster] = []
        unresolved: list[str] = []
        for normalized, group in sorted(groups.items()):
            roots = tuple(sorted({atom.source.evidence_root for atom in group}))
            truth = group[0].truth
            for atom in group[1:]:
                truth = truth_meet(truth, atom.truth)
            conflict_ids = tuple(
                sorted(
                    {
                        conflict
                        for atom in group
                        for conflict in conflict_by_atom.get(atom.atom_id, ())
                    }
                )
            )
            if conflict_ids:
                truth = truth_meet(truth, TruthState.AMBIG)
                unresolved.append(f"ACTIVE_CONFLICT::{','.join(conflict_ids)}")
            if not any(atom.witnesses for atom in group):
                unresolved.append(
                    f"WITNESS_REQUIRED::{canonical_digest(normalized)[:16]}"
                )
            cluster_id = canonical_digest(
                {
                    "normalized_claim": normalized,
                    "atoms": sorted(atom.atom_id for atom in group),
                    "roots": roots,
                }
            )
            clusters.append(
                SynthesisCluster(
                    cluster_id=cluster_id,
                    normalized_claim=normalized,
                    atom_ids=tuple(sorted(atom.atom_id for atom in group)),
                    independent_roots=roots,
                    truth=truth,
                    active_conflicts=conflict_ids,
                )
            )
        return (
            tuple(clusters),
            tuple(conflict["conflict_id"] for conflict in active_conflicts),
            tuple(sorted(set(unresolved))),
        )
