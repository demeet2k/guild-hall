from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable

from memory_crystal.p03.model import canonical_digest, canonical_json

from .model import ContextAtom, FrameworkAddress, LifecycleState, OriginClass, SourceRef, TruthState


@dataclass(frozen=True, slots=True)
class EdgeRecord:
    edge_id: str
    source_atom: str
    target_atom: str
    relation: str
    inverse_relation: str
    invariants: tuple[str, ...]
    defects: tuple[str, ...]
    witnesses: tuple[str, ...]
    return_address: str
    status: str


class NavStore:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def close(self) -> None:
        self.connection.close()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS sources (
                source_key TEXT PRIMARY KEY,
                carrier TEXT NOT NULL,
                source_id TEXT NOT NULL,
                revision TEXT NOT NULL,
                locator TEXT NOT NULL,
                authority TEXT NOT NULL,
                evidence_root TEXT NOT NULL,
                observed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS atoms (
                atom_id TEXT PRIMARY KEY,
                source_key TEXT NOT NULL REFERENCES sources(source_key),
                address_key TEXT NOT NULL,
                gid INTEGER NOT NULL,
                station TEXT NOT NULL,
                domain TEXT NOT NULL,
                node TEXT NOT NULL,
                exact_text TEXT NOT NULL,
                normalized_text TEXT NOT NULL,
                origin_class TEXT NOT NULL,
                truth TEXT NOT NULL,
                lifecycle TEXT NOT NULL,
                tags_json TEXT NOT NULL,
                dependencies_json TEXT NOT NULL,
                witnesses_json TEXT NOT NULL,
                lineage_return TEXT NOT NULL,
                payload_digest TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS identity_collisions (
                collision_id TEXT PRIMARY KEY,
                atom_id TEXT NOT NULL,
                existing_digest TEXT NOT NULL,
                candidate_digest TEXT NOT NULL,
                candidate_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS edges (
                edge_id TEXT PRIMARY KEY,
                source_atom TEXT NOT NULL REFERENCES atoms(atom_id),
                target_atom TEXT NOT NULL REFERENCES atoms(atom_id),
                relation TEXT NOT NULL,
                inverse_relation TEXT NOT NULL,
                invariants_json TEXT NOT NULL,
                defects_json TEXT NOT NULL,
                witnesses_json TEXT NOT NULL,
                return_address TEXT NOT NULL,
                status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS conflicts (
                conflict_id TEXT PRIMARY KEY,
                left_atom TEXT NOT NULL REFERENCES atoms(atom_id),
                right_atom TEXT NOT NULL REFERENCES atoms(atom_id),
                kind TEXT NOT NULL,
                status TEXT NOT NULL,
                reopen_condition TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS receipts (
                sequence INTEGER PRIMARY KEY,
                query_id TEXT NOT NULL,
                receipt_json TEXT NOT NULL,
                previous_digest TEXT NOT NULL,
                receipt_digest TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS checkpoints (
                checkpoint_id TEXT PRIMARY KEY,
                parent_checkpoint TEXT,
                checkpoint_json TEXT NOT NULL,
                checkpoint_digest TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS healing_events (
                event_id TEXT PRIMARY KEY,
                gid INTEGER NOT NULL,
                event_json TEXT NOT NULL,
                status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS atlas_cells (
                epoch TEXT NOT NULL,
                gid INTEGER NOT NULL,
                cell_json TEXT NOT NULL,
                structural_digest TEXT NOT NULL,
                PRIMARY KEY (epoch, gid)
            );
            CREATE TABLE IF NOT EXISTS atlas_collisions (
                collision_id TEXT PRIMARY KEY,
                epoch TEXT NOT NULL,
                gid INTEGER NOT NULL,
                existing_digest TEXT NOT NULL,
                candidate_digest TEXT NOT NULL,
                candidate_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS live_observations (
                observation_id TEXT PRIMARY KEY,
                carrier TEXT NOT NULL,
                source_id TEXT NOT NULL,
                revision TEXT NOT NULL,
                fragment TEXT NOT NULL,
                observation_json TEXT NOT NULL,
                payload_digest TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS observation_collisions (
                collision_id TEXT PRIMARY KEY,
                observation_id TEXT NOT NULL,
                existing_digest TEXT NOT NULL,
                candidate_digest TEXT NOT NULL,
                candidate_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS admission_claims (
                claim_id TEXT PRIMARY KEY,
                observation_id TEXT NOT NULL
                    REFERENCES live_observations(observation_id),
                gid INTEGER NOT NULL,
                status TEXT NOT NULL,
                atom_id TEXT,
                claim_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_atoms_address ON atoms(address_key);
            CREATE INDEX IF NOT EXISTS idx_atoms_domain ON atoms(domain);
            CREATE INDEX IF NOT EXISTS idx_sources_root ON sources(evidence_root);
            CREATE INDEX IF NOT EXISTS idx_observation_lineage
                ON live_observations(carrier, source_id, fragment, revision);
            CREATE INDEX IF NOT EXISTS idx_claims_gid
                ON admission_claims(gid, status);
            """
        )
        self.connection.commit()

    def ingest_atom(self, atom: ContextAtom) -> str:
        with self.connection:
            self.connection.execute(
                """
                INSERT OR IGNORE INTO sources VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    atom.source.key,
                    atom.source.carrier,
                    atom.source.source_id,
                    atom.source.revision,
                    atom.source.locator,
                    atom.source.authority,
                    atom.source.evidence_root,
                    atom.source.observed_at,
                ),
            )
            existing = self.connection.execute(
                "SELECT payload_digest FROM atoms WHERE atom_id = ?", (atom.atom_id,)
            ).fetchone()
            if existing is not None:
                if existing["payload_digest"] == atom.payload_digest:
                    return "IDEMPOTENT"
                collision_id = canonical_digest(
                    {
                        "atom_id": atom.atom_id,
                        "existing": existing["payload_digest"],
                        "candidate": atom.payload_digest,
                    }
                )
                self.connection.execute(
                    """
                    INSERT OR IGNORE INTO identity_collisions
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        collision_id,
                        atom.atom_id,
                        existing["payload_digest"],
                        atom.payload_digest,
                        canonical_json(atom.to_dict()),
                    ),
                )
                return "IDENTITY_COLLISION"
            self.connection.execute(
                """
                INSERT INTO atoms VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    atom.atom_id,
                    atom.source.key,
                    atom.address.key,
                    atom.address.gid,
                    atom.address.station,
                    atom.address.domain,
                    atom.address.node,
                    atom.exact_text,
                    atom.normalized_text,
                    atom.origin_class.value,
                    atom.truth.value,
                    atom.lifecycle.value,
                    canonical_json(atom.tags),
                    canonical_json(atom.dependencies),
                    canonical_json(atom.witnesses),
                    atom.lineage_return,
                    atom.payload_digest,
                ),
            )
        return "INSERTED"

    def add_edge(
        self,
        *,
        source_atom: str,
        target_atom: str,
        relation: str,
        inverse_relation: str,
        invariants: tuple[str, ...],
        defects: tuple[str, ...] = (),
        witnesses: tuple[str, ...],
        return_address: str,
        status: str = "CERTIFIED",
    ) -> str:
        required = (
            source_atom,
            target_atom,
            relation,
            inverse_relation,
            invariants,
            witnesses,
            return_address,
        )
        if not all(required):
            raise ValueError("typed edge requires relation, inverse, invariants, witness, and return")
        for atom_id in (source_atom, target_atom):
            if self.connection.execute(
                "SELECT 1 FROM atoms WHERE atom_id = ?", (atom_id,)
            ).fetchone() is None:
                raise KeyError(atom_id)
        edge_id = canonical_digest(
            {
                "source": source_atom,
                "target": target_atom,
                "relation": relation,
                "inverse": inverse_relation,
                "return": return_address,
            }
        )
        with self.connection:
            self.connection.execute(
                """
                INSERT OR IGNORE INTO edges VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    edge_id,
                    source_atom,
                    target_atom,
                    relation,
                    inverse_relation,
                    canonical_json(invariants),
                    canonical_json(defects),
                    canonical_json(witnesses),
                    return_address,
                    status,
                ),
            )
        return edge_id

    def add_conflict(
        self,
        left_atom: str,
        right_atom: str,
        *,
        kind: str,
        status: str = "ACTIVE",
        reopen_condition: str,
    ) -> str:
        conflict_id = canonical_digest(
            {
                "left": min(left_atom, right_atom),
                "right": max(left_atom, right_atom),
                "kind": kind,
            }
        )
        with self.connection:
            self.connection.execute(
                "INSERT OR REPLACE INTO conflicts VALUES (?, ?, ?, ?, ?, ?)",
                (
                    conflict_id,
                    left_atom,
                    right_atom,
                    kind,
                    status,
                    reopen_condition,
                ),
            )
        return conflict_id

    def atoms(self) -> list[ContextAtom]:
        rows = self.connection.execute(
            """
            SELECT a.*, s.carrier, s.source_id, s.revision, s.locator,
                   s.authority, s.evidence_root, s.observed_at
            FROM atoms a JOIN sources s USING (source_key)
            ORDER BY a.gid, a.station, a.atom_id
            """
        ).fetchall()
        return [self._row_to_atom(row) for row in rows]

    def atom(self, atom_id: str) -> ContextAtom | None:
        row = self.connection.execute(
            """
            SELECT a.*, s.carrier, s.source_id, s.revision, s.locator,
                   s.authority, s.evidence_root, s.observed_at
            FROM atoms a JOIN sources s USING (source_key)
            WHERE atom_id = ?
            """,
            (atom_id,),
        ).fetchone()
        return self._row_to_atom(row) if row else None

    def edges(self) -> list[EdgeRecord]:
        rows = self.connection.execute("SELECT * FROM edges ORDER BY edge_id").fetchall()
        return [
            EdgeRecord(
                edge_id=row["edge_id"],
                source_atom=row["source_atom"],
                target_atom=row["target_atom"],
                relation=row["relation"],
                inverse_relation=row["inverse_relation"],
                invariants=tuple(json.loads(row["invariants_json"])),
                defects=tuple(json.loads(row["defects_json"])),
                witnesses=tuple(json.loads(row["witnesses_json"])),
                return_address=row["return_address"],
                status=row["status"],
            )
            for row in rows
        ]

    def active_conflicts(self) -> list[dict[str, str]]:
        return [
            dict(row)
            for row in self.connection.execute(
                "SELECT * FROM conflicts WHERE status = 'ACTIVE' ORDER BY conflict_id"
            ).fetchall()
        ]

    def append_receipt(self, query_id: str, body: dict[str, Any]) -> str:
        last = self.connection.execute(
            "SELECT sequence, receipt_digest FROM receipts ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        sequence = int(last["sequence"]) + 1 if last else 0
        previous = last["receipt_digest"] if last else "0" * 64
        envelope = {
            "schema": "KC144.InternalRouteReceipt.V1",
            "sequence": sequence,
            "query_id": query_id,
            "body": body,
            "previous_digest": previous,
        }
        digest = canonical_digest(envelope)
        with self.connection:
            self.connection.execute(
                "INSERT INTO receipts VALUES (?, ?, ?, ?, ?)",
                (sequence, query_id, canonical_json(envelope), previous, digest),
            )
        return digest

    def verify_receipts(self, *, expected_head: str | None = None) -> tuple[bool, list[str]]:
        rows = self.connection.execute(
            "SELECT * FROM receipts ORDER BY sequence"
        ).fetchall()
        errors: list[str] = []
        previous = "0" * 64
        for expected_sequence, row in enumerate(rows):
            if row["sequence"] != expected_sequence:
                errors.append(f"receipt {expected_sequence}: sequence mismatch")
            if row["previous_digest"] != previous:
                errors.append(f"receipt {expected_sequence}: predecessor mismatch")
            envelope = json.loads(row["receipt_json"])
            if canonical_digest(envelope) != row["receipt_digest"]:
                errors.append(f"receipt {expected_sequence}: digest mismatch")
            previous = row["receipt_digest"]
        if expected_head is not None and previous != expected_head:
            errors.append("receipt chain: anchored head mismatch")
        return not errors, errors

    def verify_receipt_prefix(self, expected_head: str) -> tuple[bool, list[str]]:
        rows = self.connection.execute(
            "SELECT * FROM receipts ORDER BY sequence"
        ).fetchall()
        errors: list[str] = []
        previous = "0" * 64
        found = False
        for expected_sequence, row in enumerate(rows):
            if row["sequence"] != expected_sequence:
                errors.append(f"receipt {expected_sequence}: sequence mismatch")
            if row["previous_digest"] != previous:
                errors.append(f"receipt {expected_sequence}: predecessor mismatch")
            envelope = json.loads(row["receipt_json"])
            if canonical_digest(envelope) != row["receipt_digest"]:
                errors.append(f"receipt {expected_sequence}: digest mismatch")
            previous = row["receipt_digest"]
            if previous == expected_head:
                found = True
                break
        if not found:
            errors.append("receipt chain: checkpoint head not found")
        return not errors, errors

    def counts(self) -> dict[str, int]:
        names = (
            "sources",
            "atoms",
            "identity_collisions",
            "edges",
            "conflicts",
            "receipts",
            "checkpoints",
            "healing_events",
            "atlas_cells",
            "atlas_collisions",
            "live_observations",
            "observation_collisions",
            "admission_claims",
        )
        return {
            name: self.connection.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            for name in names
        }

    def export_snapshot(self) -> dict[str, Any]:
        receipts = [
            json.loads(row["receipt_json"])
            for row in self.connection.execute(
                "SELECT receipt_json FROM receipts ORDER BY sequence"
            ).fetchall()
        ]
        snapshot = {
            "schema": "KC144.InternalNavigationSnapshot.V1",
            "counts": self.counts(),
            "atoms": [atom.to_dict() for atom in self.atoms()],
            "edges": [
                {
                    **edge.__dict__
                }
                if hasattr(edge, "__dict__")
                else {
                    "edge_id": edge.edge_id,
                    "source_atom": edge.source_atom,
                    "target_atom": edge.target_atom,
                    "relation": edge.relation,
                    "inverse_relation": edge.inverse_relation,
                    "invariants": edge.invariants,
                    "defects": edge.defects,
                    "witnesses": edge.witnesses,
                    "return_address": edge.return_address,
                    "status": edge.status,
                }
                for edge in self.edges()
            ],
            "conflicts": self.active_conflicts(),
            "receipts": receipts,
            "checkpoints": self.checkpoints(),
            "healing_events": self.healing_events(),
            "atlas_cells": self.atlas_cells(),
            "atlas_collisions": self.atlas_collisions(),
            "live_observations": self.observations(),
            "observation_collisions": self.observation_collisions(),
            "admission_claims": self.admission_claims(),
        }
        snapshot["snapshot_digest"] = canonical_digest(snapshot)
        return snapshot

    def state_manifest(self) -> dict[str, Any]:
        atoms = {
            atom.atom_id: atom.payload_digest
            for atom in self.atoms()
        }
        edges = tuple(sorted(edge.edge_id for edge in self.edges()))
        atlas = {
            f"{cell['epoch']}::{cell['gid']:03d}": cell["structural_digest"]
            for cell in self.atlas_cells()
        }
        observations = {
            item["observation_id"]: item["payload_digest"]
            for item in self.observations()
        }
        claims = tuple(sorted(item["claim_id"] for item in self.admission_claims()))
        value = {
            "schema": "KC144.InternalNavigationStateManifest.V1",
            "atoms": atoms,
            "edges": edges,
            "atlas": atlas,
            "observations": observations,
            "claims": claims,
        }
        value["digest"] = canonical_digest(value)
        return value

    def save_checkpoint(self, checkpoint: dict[str, Any]) -> str:
        encoded = canonical_json(checkpoint)
        existing = self.connection.execute(
            """
            SELECT checkpoint_json, checkpoint_digest
            FROM checkpoints
            WHERE checkpoint_id = ?
            """,
            (checkpoint["checkpoint_id"],),
        ).fetchone()
        if existing is not None:
            if (
                existing["checkpoint_digest"] == checkpoint["digest"]
                and existing["checkpoint_json"] == encoded
            ):
                return "IDEMPOTENT"
            raise ValueError(
                f"checkpoint identity collision: {checkpoint['checkpoint_id']}"
            )
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO checkpoints
                (checkpoint_id, parent_checkpoint, checkpoint_json, checkpoint_digest)
                VALUES (?, ?, ?, ?)
                """,
                (
                    checkpoint["checkpoint_id"],
                    checkpoint.get("parent_checkpoint"),
                    encoded,
                    checkpoint["digest"],
                ),
            )
        return "INSERTED"

    def checkpoint(self, checkpoint_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT checkpoint_json FROM checkpoints WHERE checkpoint_id = ?",
            (checkpoint_id,),
        ).fetchone()
        return json.loads(row["checkpoint_json"]) if row else None

    def checkpoints(self) -> list[dict[str, Any]]:
        return [
            json.loads(row["checkpoint_json"])
            for row in self.connection.execute(
                "SELECT checkpoint_json FROM checkpoints ORDER BY rowid"
            ).fetchall()
        ]

    def latest_checkpoint_id(self) -> str | None:
        row = self.connection.execute(
            "SELECT checkpoint_id FROM checkpoints ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        return row["checkpoint_id"] if row else None

    def save_healing_event(self, event: dict[str, Any]) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT OR IGNORE INTO healing_events VALUES (?, ?, ?, ?)",
                (
                    event["event_id"],
                    event["gid"],
                    canonical_json(event),
                    event["status"],
                ),
            )

    def healing_events(self) -> list[dict[str, Any]]:
        return [
            json.loads(row["event_json"])
            for row in self.connection.execute(
                "SELECT event_json FROM healing_events ORDER BY gid, event_id"
            ).fetchall()
        ]

    def healed_gap_gids(self) -> set[int]:
        return {
            int(row["gid"])
            for row in self.connection.execute(
                "SELECT DISTINCT gid FROM healing_events WHERE status = 'OPEN_TYPED_GAP'"
            ).fetchall()
        }

    def register_atlas_cell(self, cell: dict[str, Any]) -> str:
        epoch = str(cell["epoch"])
        gid = int(cell["gid"])
        if not 1 <= gid <= 144:
            raise ValueError("atlas GID must be in [1, 144]")
        encoded = canonical_json(cell)
        digest = str(cell["structural_digest"])
        existing = self.connection.execute(
            """
            SELECT cell_json, structural_digest
            FROM atlas_cells
            WHERE epoch = ? AND gid = ?
            """,
            (epoch, gid),
        ).fetchone()
        if existing is not None:
            if existing["structural_digest"] == digest and existing["cell_json"] == encoded:
                return "IDEMPOTENT"
            collision_id = canonical_digest(
                {
                    "schema": "KC144.AtlasCollision.V1",
                    "epoch": epoch,
                    "gid": gid,
                    "existing": existing["structural_digest"],
                    "candidate": digest,
                }
            )
            with self.connection:
                self.connection.execute(
                    """
                    INSERT OR IGNORE INTO atlas_collisions
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        collision_id,
                        epoch,
                        gid,
                        existing["structural_digest"],
                        digest,
                        encoded,
                    ),
                )
            return "ATLAS_COLLISION"
        with self.connection:
            self.connection.execute(
                "INSERT INTO atlas_cells VALUES (?, ?, ?, ?)",
                (epoch, gid, encoded, digest),
            )
        return "INSERTED"

    def atlas_cell(self, gid: int, *, epoch: str = "KC144.V1") -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT cell_json FROM atlas_cells WHERE epoch = ? AND gid = ?",
            (epoch, gid),
        ).fetchone()
        return json.loads(row["cell_json"]) if row else None

    def atlas_cells(self) -> list[dict[str, Any]]:
        return [
            json.loads(row["cell_json"])
            for row in self.connection.execute(
                "SELECT cell_json FROM atlas_cells ORDER BY epoch, gid"
            ).fetchall()
        ]

    def atlas_collisions(self) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self.connection.execute(
                "SELECT * FROM atlas_collisions ORDER BY epoch, gid, collision_id"
            ).fetchall()
        ]

    def save_observation(self, observation: dict[str, Any]) -> str:
        encoded = canonical_json(observation)
        observation_id = observation["observation_id"]
        digest = observation["payload_digest"]
        existing = self.connection.execute(
            """
            SELECT observation_json, payload_digest
            FROM live_observations
            WHERE observation_id = ?
            """,
            (observation_id,),
        ).fetchone()
        if existing is not None:
            if existing["payload_digest"] == digest and existing["observation_json"] == encoded:
                return "IDEMPOTENT"
            collision_id = canonical_digest(
                {
                    "schema": "KC144.ObservationCollision.V1",
                    "observation_id": observation_id,
                    "existing": existing["payload_digest"],
                    "candidate": digest,
                }
            )
            with self.connection:
                self.connection.execute(
                    """
                    INSERT OR IGNORE INTO observation_collisions
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        collision_id,
                        observation_id,
                        existing["payload_digest"],
                        digest,
                        encoded,
                    ),
                )
            return "OBSERVATION_COLLISION"
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO live_observations
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    observation_id,
                    observation["carrier"],
                    observation["source_id"],
                    observation["revision"],
                    observation["fragment"],
                    encoded,
                    digest,
                ),
            )
        return "INSERTED"

    def observation(self, observation_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            """
            SELECT observation_json
            FROM live_observations
            WHERE observation_id = ?
            """,
            (observation_id,),
        ).fetchone()
        return json.loads(row["observation_json"]) if row else None

    def observations(self) -> list[dict[str, Any]]:
        return [
            json.loads(row["observation_json"])
            for row in self.connection.execute(
                """
                SELECT observation_json
                FROM live_observations
                ORDER BY carrier, source_id, fragment, revision
                """
            ).fetchall()
        ]

    def observation_collisions(self) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self.connection.execute(
                """
                SELECT *
                FROM observation_collisions
                ORDER BY observation_id, collision_id
                """
            ).fetchall()
        ]

    def observation_lineage(
        self, carrier: str, source_id: str, fragment: str
    ) -> list[dict[str, Any]]:
        return [
            json.loads(row["observation_json"])
            for row in self.connection.execute(
                """
                SELECT observation_json
                FROM live_observations
                WHERE carrier = ? AND source_id = ? AND fragment = ?
                ORDER BY revision, observation_id
                """,
                (carrier, source_id, fragment),
            ).fetchall()
        ]

    def save_admission_claim(self, claim: dict[str, Any]) -> str:
        encoded = canonical_json(claim)
        existing = self.connection.execute(
            "SELECT claim_json FROM admission_claims WHERE claim_id = ?",
            (claim["claim_id"],),
        ).fetchone()
        if existing is not None:
            if existing["claim_json"] == encoded:
                return "IDEMPOTENT"
            raise ValueError(f"admission claim collision: {claim['claim_id']}")
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO admission_claims
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    claim["claim_id"],
                    claim["observation_id"],
                    claim["address"]["gid"],
                    claim["status"],
                    claim.get("atom_id"),
                    encoded,
                ),
            )
        return "INSERTED"

    def admission_claims(self) -> list[dict[str, Any]]:
        return [
            json.loads(row["claim_json"])
            for row in self.connection.execute(
                "SELECT claim_json FROM admission_claims ORDER BY gid, claim_id"
            ).fetchall()
        ]

    def _row_to_atom(self, row: sqlite3.Row) -> ContextAtom:
        source = SourceRef(
            carrier=row["carrier"],
            source_id=row["source_id"],
            revision=row["revision"],
            locator=row["locator"],
            authority=row["authority"],
            evidence_root=row["evidence_root"],
            observed_at=row["observed_at"],
        )
        address = FrameworkAddress(
            gid=row["gid"],
            station=row["station"],
            domain=row["domain"],
            node=row["node"],
        )
        return ContextAtom(
            atom_id=row["atom_id"],
            source=source,
            address=address,
            exact_text=row["exact_text"],
            normalized_text=row["normalized_text"],
            origin_class=OriginClass(row["origin_class"]),
            truth=TruthState(row["truth"]),
            lifecycle=LifecycleState(row["lifecycle"]),
            tags=tuple(json.loads(row["tags_json"])),
            dependencies=tuple(json.loads(row["dependencies_json"])),
            witnesses=tuple(json.loads(row["witnesses_json"])),
            lineage_return=row["lineage_return"],
            payload_digest=row["payload_digest"],
        )
