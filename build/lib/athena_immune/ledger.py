from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterator

from .canonical import canonical_dumps, content_hash, sha256_hex, utc_now


class LedgerIntegrityError(RuntimeError):
    """Raised when an append-only ledger invariant is violated."""


class AppendOnlyLedger:
    """SQLite-backed immutable packet ledger with hash-linked streams."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self._initialize()

    def _initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS ledger_entries (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                stream TEXT NOT NULL,
                packet_id TEXT NOT NULL UNIQUE,
                packet_type TEXT NOT NULL,
                cycle_id TEXT NOT NULL,
                previous_hash TEXT,
                payload_json TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                entry_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_ledger_stream_sequence
                ON ledger_entries(stream, sequence);
            CREATE INDEX IF NOT EXISTS idx_ledger_cycle
                ON ledger_entries(cycle_id, sequence);

            CREATE TRIGGER IF NOT EXISTS ledger_entries_no_update
            BEFORE UPDATE ON ledger_entries
            BEGIN
                SELECT RAISE(ABORT, 'append-only ledger: UPDATE forbidden');
            END;

            CREATE TRIGGER IF NOT EXISTS ledger_entries_no_delete
            BEFORE DELETE ON ledger_entries
            BEGIN
                SELECT RAISE(ABORT, 'append-only ledger: DELETE forbidden');
            END;
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "AppendOnlyLedger":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def head(self, stream: str = "main") -> str | None:
        row = self.connection.execute(
            "SELECT entry_hash FROM ledger_entries WHERE stream = ? ORDER BY sequence DESC LIMIT 1",
            (stream,),
        ).fetchone()
        return None if row is None else str(row["entry_hash"])

    def append(
        self,
        packet_type: str,
        packet_id: str,
        cycle_id: str,
        payload: dict[str, Any],
        *,
        stream: str = "main",
    ) -> dict[str, Any]:
        body = dict(payload)
        supplied_hash = body.pop("packet_hash", None)
        payload_hash = content_hash(body, omit=())
        if supplied_hash is not None and supplied_hash != payload_hash:
            raise LedgerIntegrityError(
                f"declared packet hash mismatch for {packet_id}: {supplied_hash} != {payload_hash}"
            )

        previous_hash = self.head(stream)
        declared_previous = body.get("prior_packet_hash")
        if declared_previous is not None and declared_previous != previous_hash:
            raise LedgerIntegrityError(
                f"declared prior hash mismatch for {packet_id}: "
                f"{declared_previous} != {previous_hash}"
            )

        stored_payload = dict(body)
        stored_payload["packet_hash"] = payload_hash
        created_at = str(stored_payload.get("created_at") or utc_now())
        entry_hash = sha256_hex(
            {
                "stream": stream,
                "packet_id": packet_id,
                "packet_type": packet_type,
                "cycle_id": cycle_id,
                "previous_hash": previous_hash,
                "payload_hash": payload_hash,
            }
        )

        try:
            with self.connection:
                cursor = self.connection.execute(
                    """
                    INSERT INTO ledger_entries (
                        stream, packet_id, packet_type, cycle_id, previous_hash,
                        payload_json, payload_hash, entry_hash, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        stream,
                        packet_id,
                        packet_type,
                        cycle_id,
                        previous_hash,
                        canonical_dumps(stored_payload),
                        payload_hash,
                        entry_hash,
                        created_at,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise LedgerIntegrityError(str(exc)) from exc

        return {
            "sequence": cursor.lastrowid,
            "stream": stream,
            "packet_id": packet_id,
            "packet_type": packet_type,
            "cycle_id": cycle_id,
            "previous_hash": previous_hash,
            "payload_hash": payload_hash,
            "entry_hash": entry_hash,
            "created_at": created_at,
        }

    def entries(
        self,
        *,
        stream: str | None = None,
        cycle_id: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        clauses: list[str] = []
        parameters: list[str] = []
        if stream is not None:
            clauses.append("stream = ?")
            parameters.append(stream)
        if cycle_id is not None:
            clauses.append("cycle_id = ?")
            parameters.append(cycle_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.connection.execute(
            f"SELECT * FROM ledger_entries {where} ORDER BY sequence",  # noqa: S608
            parameters,
        )
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            yield item

    def get(self, packet_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM ledger_entries WHERE packet_id = ?",
            (packet_id,),
        ).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["payload"] = json.loads(item.pop("payload_json"))
        return item

    def verify(self, *, stream: str | None = None) -> dict[str, Any]:
        streams = (
            [stream]
            if stream is not None
            else [
                str(row["stream"])
                for row in self.connection.execute(
                    "SELECT DISTINCT stream FROM ledger_entries ORDER BY stream"
                )
            ]
        )
        errors: list[str] = []
        checked = 0
        heads: dict[str, str | None] = {}

        for stream_name in streams:
            expected_previous: str | None = None
            for entry in self.entries(stream=stream_name):
                checked += 1
                payload = dict(entry["payload"])
                declared_payload_hash = payload.pop("packet_hash", None)
                recomputed_payload_hash = content_hash(payload, omit=())
                if declared_payload_hash != recomputed_payload_hash:
                    errors.append(f"{entry['packet_id']}: PAYLOAD_HASH_MISMATCH")
                if entry["payload_hash"] != recomputed_payload_hash:
                    errors.append(f"{entry['packet_id']}: STORED_PAYLOAD_HASH_MISMATCH")
                if entry["previous_hash"] != expected_previous:
                    errors.append(f"{entry['packet_id']}: PREVIOUS_HASH_MISMATCH")
                recomputed_entry_hash = sha256_hex(
                    {
                        "stream": entry["stream"],
                        "packet_id": entry["packet_id"],
                        "packet_type": entry["packet_type"],
                        "cycle_id": entry["cycle_id"],
                        "previous_hash": entry["previous_hash"],
                        "payload_hash": entry["payload_hash"],
                    }
                )
                if entry["entry_hash"] != recomputed_entry_hash:
                    errors.append(f"{entry['packet_id']}: ENTRY_HASH_MISMATCH")
                expected_previous = entry["entry_hash"]
            heads[stream_name] = expected_previous

        return {
            "verdict": "PASS" if not errors else "FAIL",
            "checked_entries": checked,
            "streams": streams,
            "heads": heads,
            "errors": errors,
        }

