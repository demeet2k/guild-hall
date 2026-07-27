from __future__ import annotations

import argparse
from dataclasses import asdict
from enum import Enum
import json
from pathlib import Path
from typing import Any

from .engine import InternalNavigator
from .live_ingest import AtlasCoverageAuditor, LiveContextCompiler
from .model import ContextAtom, QueryBundle, TruthState
from .reentry import CoverageAuditor, HealingPlanner, SessionManager
from .store import NavStore


def _json_default(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return list(value)
    raise TypeError(type(value).__name__)


def _load_bundle(path: Path) -> tuple[dict[str, Any], list[ContextAtom], dict[str, ContextAtom]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    rows = value.get("atoms", value)
    atoms = [ContextAtom.from_dict(item) for item in rows]
    aliases = {
        item["alias"]: atom
        for item, atom in zip(rows, atoms, strict=True)
        if item.get("alias")
    }
    return value, atoms, aliases


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="athena-internal-nav")
    parser.add_argument("--db", type=Path, default=Path("local/internal-nav.sqlite3"))
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest")
    ingest.add_argument("input", type=Path)
    live_ingest = sub.add_parser("ingest-live")
    live_ingest.add_argument("input", type=Path)
    query = sub.add_parser("query")
    query.add_argument("goal")
    query.add_argument("terms", nargs="+")
    query.add_argument("--domain", action="append", default=[])
    query.add_argument("--start", action="append", default=[])
    query.add_argument("--budget", type=int, default=27)
    query.add_argument(
        "--evidence-floor",
        choices=[state.value for state in TruthState],
        default="RESID",
    )
    sub.add_parser("status")
    sub.add_parser("atlas-coverage")
    coverage = sub.add_parser("coverage")
    coverage.add_argument("--heal", action="store_true")
    coverage.add_argument("--heal-limit", type=int, default=144)
    reenter = sub.add_parser("reenter")
    reenter.add_argument("checkpoint_id")
    rollback = sub.add_parser("rollback")
    rollback.add_argument("checkpoint_id")
    snapshot = sub.add_parser("snapshot")
    snapshot.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    args.db.parent.mkdir(parents=True, exist_ok=True)
    store = NavStore(args.db)
    navigator = InternalNavigator(store)
    try:
        if args.command == "ingest":
            value, atoms, aliases = _load_bundle(args.input)
            output = {"atoms": navigator.ingest(atoms), "edges": 0, "conflicts": 0}
            for edge in value.get("edges", ()):
                store.add_edge(
                    source_atom=aliases[edge["source"]].atom_id,
                    target_atom=aliases[edge["target"]].atom_id,
                    relation=edge["relation"],
                    inverse_relation=edge["inverse_relation"],
                    invariants=tuple(edge["invariants"]),
                    defects=tuple(edge.get("defects", ())),
                    witnesses=tuple(edge["witnesses"]),
                    return_address=edge["return_address"],
                    status=edge.get("status", "CERTIFIED"),
                )
                output["edges"] += 1
            for conflict in value.get("conflicts", ()):
                store.add_conflict(
                    aliases[conflict["left"]].atom_id,
                    aliases[conflict["right"]].atom_id,
                    kind=conflict["kind"],
                    status=conflict.get("status", "ACTIVE"),
                    reopen_condition=conflict["reopen_condition"],
                )
                output["conflicts"] += 1
        elif args.command == "ingest-live":
            value = json.loads(args.input.read_text(encoding="utf-8"))
            result = LiveContextCompiler(store).ingest_bundle(value)
            output = {
                "atlas": dict(result.atlas),
                "observations": dict(result.observations),
                "claims": [claim.to_dict() for claim in result.claims],
                "coverage": asdict(AtlasCoverageAuditor(store).audit()),
            }
        elif args.command == "query":
            bundle = QueryBundle.build(
                goal=args.goal,
                terms=tuple(args.terms),
                domains=tuple(args.domain),
                start_coordinates=tuple(args.start),
                route_budget=args.budget,
                evidence_floor=TruthState(args.evidence_floor),
            )
            packet = navigator.query(bundle)
            replay = navigator.close_session(bundle, packet)
            coverage_report = CoverageAuditor(store).audit()
            session_close = SessionManager(store).close(
                bundle, packet, replay, coverage_report
            )
            output = {
                "synthesis": asdict(packet),
                "replay": asdict(replay),
                "coverage": asdict(coverage_report),
                "session_close": asdict(session_close),
            }
        elif args.command == "coverage":
            auditor = CoverageAuditor(store)
            before = auditor.audit()
            events = ()
            after = before
            if args.heal:
                events = HealingPlanner(store).type_missing_gaps(
                    before, limit=args.heal_limit
                )
                after = auditor.audit()
            output = {
                "before": asdict(before),
                "healing_events": [asdict(event) for event in events],
                "after": asdict(after),
            }
        elif args.command == "atlas-coverage":
            output = asdict(AtlasCoverageAuditor(store).audit())
        elif args.command == "reenter":
            output = asdict(SessionManager(store).warm_reentry(args.checkpoint_id))
        elif args.command == "rollback":
            output = asdict(SessionManager(store).rollback_packet(args.checkpoint_id))
        elif args.command == "snapshot":
            output = store.export_snapshot()
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(
                    json.dumps(output, indent=2, default=_json_default) + "\n",
                    encoding="utf-8",
                )
        else:
            output = {
                "schema": "KC144.InternalNavigationStatus.V1",
                "counts": store.counts(),
                "receipt_chain": store.verify_receipts(),
            }
        print(json.dumps(output, indent=2, default=_json_default))
        return 0
    finally:
        store.close()
