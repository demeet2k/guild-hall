from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from .population import digest
from .witness import BridgeWitnessPacket, evaluate_bridge_witness


@dataclass(frozen=True)
class CommitAuthorization:
    authorization_id: str
    issuer_id: str
    authority_scope: str
    signature_status: str
    test_only: bool = False


def prepare_bridge_commit(packet: BridgeWitnessPacket) -> dict[str, Any]:
    evaluation = evaluate_bridge_witness(packet)
    body = {
        "packet_digest": digest(packet.to_dict()),
        "evaluation_digest": evaluation["evaluation_digest"],
        "bridge_id": packet.bridge_id,
        "packet_id": packet.packet_id,
    }
    prepared = evaluation["verdict"] == "CERTIFIED"
    return {
        "schema": "KC144.BridgePrepare.V5",
        "phase": "PREPARE",
        "status": "PREPARED" if prepared else "HOLD",
        **body,
        "prepare_token": digest(body) if prepared else None,
        "production_ledger_mutated": False,
        "evaluation": evaluation,
    }


def commit_bridge(
    preparation: dict[str, Any],
    packet: BridgeWitnessPacket,
    authorization: CommitAuthorization,
    *,
    ledger: Iterable[dict[str, Any]] = (),
    namespace: str = "PRODUCTION",
    verification_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    current = tuple(ledger)
    evaluation = evaluate_bridge_witness(packet)
    body = {
        "packet_digest": digest(packet.to_dict()),
        "evaluation_digest": evaluation["evaluation_digest"],
        "bridge_id": packet.bridge_id,
        "packet_id": packet.packet_id,
    }
    expected_token = digest(body)
    checks = {
        "prepared": preparation.get("status") == "PREPARED",
        "prepare_token_exact": preparation.get("prepare_token") == expected_token,
        "evaluation_certified": evaluation["verdict"] == "CERTIFIED",
        "authorization_signed": authorization.signature_status == "VERIFIED",
        "authority_scope": authorization.authority_scope
        in {"KC144.BRIDGE_COMMIT", f"KC144.BRIDGE_COMMIT::{packet.bridge_id}"},
        "packet_unique": all(
            row.get("packet_id") != packet.packet_id for row in current
        ),
        "bridge_unique": all(
            row.get("bridge_id") != packet.bridge_id for row in current
        ),
        "production_not_test": not (
            namespace == "PRODUCTION"
            and (
                authorization.test_only
                or "SYNTHETIC" in packet.packet_id.upper()
                or "SYNTHETIC" in packet.corridor.upper()
            )
        ),
        "cryptographic_envelope": (
            namespace != "PRODUCTION"
            or (
                verification_context is not None
                and verification_context.get("schema")
                == "KC144.CryptographicAdmissionContext.V7"
                and verification_context.get("verdict") == "PASS"
                and verification_context.get("packet_digest")
                == body["packet_digest"]
                and verification_context.get("authority_id")
                == authorization.issuer_id
                and verification_context.get("scope")
                == authorization.authority_scope
            )
        ),
    }
    committed = all(checks.values())
    record = None
    if committed:
        record_body = {
            "namespace": namespace,
            "bridge_id": packet.bridge_id,
            "packet_id": packet.packet_id,
            "packet_digest": body["packet_digest"],
            "prepare_token": expected_token,
            "authorization": asdict(authorization),
            "standing": (
                "TEST_ONLY_TRANSPORT_COMMIT"
                if namespace == "TEST"
                else "PRODUCTION_TRANSPORT_COMMIT"
            ),
            "station_promotion_effect": "NONE",
        }
        record = {**record_body, "commit_digest": digest(record_body)}
    return {
        "schema": "KC144.BridgeCommit.V5",
        "phase": "COMMIT",
        "namespace": namespace,
        "status": "COMMITTED" if committed else "HOLD",
        "checks": checks,
        "record": record,
        "ledger_before": len(current),
        "ledger_after": len(current) + (1 if committed else 0),
        "production_ledger_mutated": committed and namespace == "PRODUCTION",
        "station_promotion_effect": "NONE",
    }


def empty_production_bridge_commit_ledger() -> dict[str, Any]:
    return {
        "schema": "KC144.BridgeCommitLedger.V5",
        "namespace": "PRODUCTION",
        "records": [],
        "prepared": 0,
        "committed": 0,
        "declared_bridges": 28,
        "open_transport_obligations": 28,
        "station_promotion_effect": "NONE",
    }
