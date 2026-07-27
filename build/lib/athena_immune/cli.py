from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import uuid4

from .canonical import canonical_dumps
from .ledger import AppendOnlyLedger
from .models import RoleAssignments, TrustEvidence, TrustVector
from .runtime import ImmuneRuntime


def demo(db_path: Path) -> dict[str, object]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    cycle_id = f"ATHENA.IMMUNE.DEMO.{uuid4().hex[:12]}"
    runtime = ImmuneRuntime(db_path)
    result = runtime.run_cycle(
        cycle_id=cycle_id,
        act={
            "action": "PROMOTE_CLAIM",
            "claim_ref": "CLAIM.TORAH.CRYSTAL.001",
            "actor": "athena",
        },
        contradiction={
            "proposition_a_ref": "CLAIM.TORAH.CRYSTAL.001",
            "proposition_b_ref": "WITNESS.CORPUS.001",
            "proposition_a_warrant": "RHETORICAL",
            "proposition_b_warrant": "SOURCE_TEXT",
            "contradiction_classes": ["WARRANT_INFLATION"],
            "witness_refs": ["WITNESS.CORPUS.001"],
            "counterwitness_refs": ["WITNESS.AUDIT.001"],
            "severity": 0.8,
            "authority_ok": True,
            "consent_ok": True,
            "candidate_repairs": [
                {
                    "residual_code": "LAN-EVIDENCE",
                    "damaged_layer": "epistemic",
                    "operation": "DOWNGRADE_EVIDENCE",
                    "required_witnesses": ["WITNESS.CORPUS.001"],
                    "blockers": ["WARRANT_INFLATION"],
                    "propagation_radius": 4,
                    "severity": 0.8,
                    "replay_blocking": True,
                }
            ],
        },
        repair_receipts=[
            {
                "residual_code": "LAN-EVIDENCE",
                "repair_layer": "epistemic",
                "operation": "DOWNGRADE_EVIDENCE",
                "status": "VERIFIED",
                "witness_refs": ["WITNESS.CORPUS.001", "WITNESS.AUDIT.001"],
            }
        ],
        prior_trust=TrustVector(),
        trust_evidence=TrustEvidence(
            outcome={"epistemic": 0.7, "correction": 0.9, "replay": 1.0},
            witness_refs={
                "epistemic": ["WITNESS.CORPUS.001"],
                "correction": ["REPAIR.VERIFIED.001"],
                "replay": ["REPLAY.EXACT.001"],
            },
            eta=0.5,
        ),
        assignments=RoleAssignments(
            proposer="agent.proposer",
            skeptic="agent.skeptic",
            integrator="agent.integrator",
            immune_steward="agent.steward",
            replay_auditor="agent.replay",
            meta_observer="agent.meta",
        ),
        omega_gate=True,
        sigma_gate=True,
        source_addresses=[
            "ATHENA.CORE.V7::IMMUNE_KERNEL.P01",
            "KC144.V1::GID005::H05",
            "KC144.V1::GID006::H06",
        ],
        next_route="ATHENA.CORE.V7::IMMUNE_KERNEL.P03::LIVE_INGESTION",
        admitted_scope=["CLAIM.TORAH.CRYSTAL.001"],
    )
    verification = runtime.ledger.verify()
    output: dict[str, object] = {
        "cycle": result.to_dict(),
        "ledger_verification": verification,
        "ledger_head": runtime.ledger.head(),
    }
    runtime.ledger.close()
    return output


def verify(db_path: Path) -> dict[str, object]:
    with AppendOnlyLedger(db_path) as ledger:
        return ledger.verify()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="athena-immune")
    subparsers = parser.add_subparsers(dest="command", required=True)
    demo_parser = subparsers.add_parser("demo", help="run one lawful immune cycle")
    demo_parser.add_argument("--db", type=Path, default=Path("demo/immune.db"))
    verify_parser = subparsers.add_parser("verify", help="verify an existing ledger")
    verify_parser.add_argument("--db", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = demo(args.db) if args.command == "demo" else verify(args.db)
    print(canonical_dumps(result))
    return 0 if result.get("verdict", result.get("ledger_verification", {}).get("verdict")) == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

