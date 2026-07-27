from __future__ import annotations

import base64
import binascii
import re
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .crosswalk import (
    ACTIVE_EPOCH_CENSUS,
    ACTIVE_EPOCH_ID,
    compile_coordinate_crosswalk,
    domain_binding_for_subject,
    graph_slice_registry,
)
from .population import canonical_json, digest
from .repair import (
    EvidenceAuthority,
    M12EvidencePacket,
    admit_evidence,
    verify_repair_ledger,
)


SHA256_PREFIX = "sha256:"
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
IC10_GATES = tuple(f"I{index:02d}" for index in range(1, 11))


@dataclass(frozen=True)
class AuthorityKey:
    key_id: str
    algorithm: str
    public_key_b64: str
    scopes: tuple[str, ...]
    namespaces: tuple[str, ...]
    status: str
    independent: bool
    test_only: bool
    not_before: str | None = None
    not_after: str | None = None

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AuthorityKey":
        data = dict(value)
        data["scopes"] = tuple(data.get("scopes", ()))
        data["namespaces"] = tuple(data.get("namespaces", ()))
        return cls(**data)


@dataclass(frozen=True)
class SignedEvidenceEnvelope:
    envelope_id: str
    namespace: str
    epoch_id: str
    epoch_census: str
    frozen_base_root: str
    crosswalk_digest: str
    graph_slice: str
    graph_slice_digest: str
    issued_at: str
    signer_key_id: str
    packets: tuple[M12EvidencePacket, ...]
    signature_b64: str

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SignedEvidenceEnvelope":
        data = dict(value)
        data["packets"] = tuple(
            M12EvidencePacket.from_dict(packet)
            for packet in data.get("packets", ())
        )
        return cls(**data)

    def signing_body(self) -> dict[str, Any]:
        body = asdict(self)
        body.pop("signature_b64")
        return body

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def empty_authority_registry() -> dict[str, Any]:
    body = {
        "schema": "KC144.AuthorityRegistry.V7",
        "epoch_id": ACTIVE_EPOCH_ID,
        "keys": [],
        "revoked_key_ids": [],
        "law": (
            "no production evidence is admitted without an active pinned "
            "Ed25519 key whose scope, namespace, independence, and validity "
            "interval cover the signed envelope"
        ),
    }
    return {**body, "registry_digest": digest(body)}


def seal_authority_registry(
    keys: tuple[AuthorityKey, ...] | list[AuthorityKey],
    *,
    revoked_key_ids: tuple[str, ...] | list[str] = (),
) -> dict[str, Any]:
    key_ids = [key.key_id for key in keys]
    if any(not key_id for key_id in key_ids) or len(key_ids) != len(
        set(key_ids)
    ):
        raise ValueError("authority key identifiers must be nonempty and unique")
    body = {
        "schema": "KC144.AuthorityRegistry.V7",
        "epoch_id": ACTIVE_EPOCH_ID,
        "keys": [asdict(key) for key in keys],
        "revoked_key_ids": sorted(set(revoked_key_ids)),
        "law": (
            "no production evidence is admitted without an active pinned "
            "Ed25519 key whose scope, namespace, independence, and validity "
            "interval cover the signed envelope"
        ),
    }
    return {**body, "registry_digest": digest(body)}


def envelope_signing_bytes(envelope: SignedEvidenceEnvelope) -> bytes:
    return canonical_json(envelope.signing_body()).encode("utf-8")


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed


def _scope_allows(grant: str, required: str) -> bool:
    if grant == required:
        return True
    if grant.endswith("*"):
        return required.startswith(grant[:-1])
    return False


def _authority_key_well_formed(key: AuthorityKey) -> bool:
    try:
        public_bytes = base64.b64decode(key.public_key_b64, validate=True)
        not_before = (
            _parse_time(key.not_before) if key.not_before is not None else None
        )
        not_after = (
            _parse_time(key.not_after) if key.not_after is not None else None
        )
    except (ValueError, TypeError, binascii.Error):
        return False
    return (
        bool(key.key_id)
        and key.algorithm == "ED25519"
        and len(public_bytes) == 32
        and bool(key.scopes)
        and len(key.scopes) == len(set(key.scopes))
        and bool(key.namespaces)
        and len(key.namespaces) == len(set(key.namespaces))
        and set(key.namespaces) <= {"PRODUCTION", "TEST"}
        and key.status in {"ACTIVE", "REVOKED", "EXPIRED"}
        and isinstance(key.independent, bool)
        and isinstance(key.test_only, bool)
        and (
            not_before is None
            or not_after is None
            or not_before <= not_after
        )
    )


def authority_registry_integrity(registry: Mapping[str, Any]) -> bool:
    body = {key: value for key, value in registry.items() if key != "registry_digest"}
    raw_keys = registry.get("keys", ())
    revoked = registry.get("revoked_key_ids", ())
    if not isinstance(raw_keys, (list, tuple)) or not isinstance(
        revoked, (list, tuple)
    ):
        return False
    try:
        keys = [AuthorityKey.from_dict(key) for key in raw_keys]
    except (TypeError, ValueError):
        return False
    key_ids = [key.key_id for key in keys]
    revoked_set = set(revoked)
    return (
        registry.get("schema") == "KC144.AuthorityRegistry.V7"
        and registry.get("epoch_id") == ACTIVE_EPOCH_ID
        and all(_authority_key_well_formed(key) for key in keys)
        and len(key_ids) == len(set(key_ids))
        and all(isinstance(key_id, str) and key_id for key_id in revoked)
        and len(revoked) == len(set(revoked))
        and all(
            (key.key_id in revoked_set) == (key.status == "REVOKED")
            for key in keys
        )
        and registry.get("registry_digest") == digest(body)
    )


def _graph_slice_lookup() -> dict[str, dict[str, Any]]:
    return {
        row["slice_id"]: row for row in graph_slice_registry()["slices"]
    }


def _authority_scope(packet: M12EvidencePacket) -> str:
    return (
        f"KC144.IC10.PROMOTION::{packet.subject_id}"
        if packet.kind == "IC10_PROMOTION"
        else f"KC144.M12.{packet.kind}::{packet.subject_id}"
    )


def _paired_ic10_passes(packet: M12EvidencePacket) -> bool:
    if packet.kind != "IC10_PROMOTION":
        return True
    payload = packet.payload
    for name in ("constitutional_gate_vector", "immune_gate_vector"):
        vector = payload.get(name, {})
        if set(vector) != set(IC10_GATES):
            return False
        if any(vector[gate] != "PASS" for gate in IC10_GATES):
            return False
    return True


def _contradiction_admissible(packet: M12EvidencePacket) -> bool:
    if packet.contradiction_class in {"CONTESTED", "UNRESOLVED"}:
        return False
    if packet.contradiction_class == "CONFIRMED":
        return packet.kind == "DEFECT_CLOSURE"
    return packet.contradiction_class == "NONE_FOUND"


def _packet_binding_checks(
    packet: M12EvidencePacket,
    envelope: SignedEvidenceEnvelope,
) -> dict[str, bool]:
    payload = packet.payload
    graph_bound = packet.kind in {
        "BRIDGE_CERTIFICATION",
        "INDEPENDENT_REPLAY",
    }
    domain_bound = packet.kind == "DOMAIN_POPULATION"
    expected_domain_binding = None
    if domain_bound:
        try:
            expected_domain_binding = domain_binding_for_subject(
                packet.subject_id
            )
        except ValueError:
            expected_domain_binding = None
    adjudication_required = bool(
        expected_domain_binding
        and expected_domain_binding.get("adjudication_required")
    )
    return {
        "packet_namespace": packet.namespace == envelope.namespace,
        "packet_authority_id": packet.authority.authority_id
        == envelope.signer_key_id,
        "packet_scope_exact": packet.authority.scope == _authority_scope(packet),
        "packet_signature_claim": packet.authority.signature_status == "VERIFIED",
        "packet_independence_claim": packet.authority.independent,
        "epoch_bound": payload.get("epoch_id") == envelope.epoch_id,
        "base_root_bound": payload.get("frozen_base_root")
        == envelope.frozen_base_root,
        "crosswalk_bound": payload.get("crosswalk_digest")
        == envelope.crosswalk_digest,
        "graph_slice_bound": (
            not graph_bound
            or payload.get("graph_slice") == envelope.graph_slice
        ),
        "active_graph_slice_bound": (
            not graph_bound
            or envelope.namespace != "PRODUCTION"
            or envelope.graph_slice
            == graph_slice_registry()["active_frozen_slice"]
        ),
        "graph_digest_bound": (
            not graph_bound
            or payload.get("graph_slice_digest")
            == envelope.graph_slice_digest
        ),
        "domain_coordinate_binding": (
            not domain_bound
            or (
                expected_domain_binding is not None
                and payload.get("coordinate_binding")
                == expected_domain_binding
            )
        ),
        "domain_adjudication_binding": (
            not adjudication_required
            or (
                payload.get("adjudication_status") == "RESOLVED"
                and bool(
                    SHA256.fullmatch(
                        str(payload.get("adjudication_receipt_root", ""))
                    )
                )
            )
        ),
        "contradiction_admissible": _contradiction_admissible(packet),
        "paired_ic10_conjunctive": _paired_ic10_passes(packet),
    }


def verify_signed_envelope(
    envelope: SignedEvidenceEnvelope,
    registry: Mapping[str, Any],
    ledger: Mapping[str, Any],
) -> dict[str, Any]:
    keys = {
        key.key_id: key
        for key in (
            AuthorityKey.from_dict(value) for value in registry.get("keys", ())
        )
    }
    key = keys.get(envelope.signer_key_id)
    crosswalk = compile_coordinate_crosswalk()
    graph_slices = _graph_slice_lookup()
    graph_slice = graph_slices.get(envelope.graph_slice)
    signature_valid = False
    public_key_valid = False
    issued_at_valid = False
    if key is not None:
        try:
            issued = _parse_time(envelope.issued_at)
            issued_at_valid = (
                (key.not_before is None or issued >= _parse_time(key.not_before))
                and (key.not_after is None or issued <= _parse_time(key.not_after))
            )
            public_bytes = base64.b64decode(key.public_key_b64, validate=True)
            public_key_valid = len(public_bytes) == 32
            signature = base64.b64decode(envelope.signature_b64, validate=True)
            if public_key_valid:
                Ed25519PublicKey.from_public_bytes(public_bytes).verify(
                    signature,
                    envelope_signing_bytes(envelope),
                )
                signature_valid = True
        except (
            ValueError,
            TypeError,
            binascii.Error,
            InvalidSignature,
        ):
            signature_valid = False

    required_scopes = [_authority_scope(packet) for packet in envelope.packets]
    scopes_cover = bool(
        key
        and all(
            any(_scope_allows(grant, required) for grant in key.scopes)
            for required in required_scopes
        )
    )
    packet_reports = [
        {
            "packet_id": packet.packet_id,
            "subject_id": packet.subject_id,
            "checks": _packet_binding_checks(packet, envelope),
        }
        for packet in envelope.packets
    ]
    all_packet_bindings = bool(packet_reports) and all(
        all(report["checks"].values()) for report in packet_reports
    )
    checks = {
        "ledger_integrity": verify_repair_ledger(ledger)["verdict"] == "PASS",
        "registry_integrity": authority_registry_integrity(registry),
        "registry_epoch": registry.get("epoch_id") == ACTIVE_EPOCH_ID,
        "key_resolved": key is not None,
        "key_algorithm": bool(key and key.algorithm == "ED25519"),
        "key_active": bool(key and key.status == "ACTIVE"),
        "key_not_revoked": bool(
            key and key.key_id not in registry.get("revoked_key_ids", ())
        ),
        "key_independent": bool(key and key.independent),
        "key_namespace": bool(key and envelope.namespace in key.namespaces),
        "key_test_boundary": bool(
            key
            and not (
                envelope.namespace == "PRODUCTION"
                and key.test_only
            )
        ),
        "key_validity_interval": issued_at_valid,
        "public_key_valid": public_key_valid,
        "signature_valid": signature_valid,
        "authority_scopes_cover": scopes_cover,
        "namespace_exact": envelope.namespace == ledger.get("namespace"),
        "epoch_exact": envelope.epoch_id == ACTIVE_EPOCH_ID,
        "epoch_census_exact": envelope.epoch_census == ACTIVE_EPOCH_CENSUS,
        "base_root_exact": envelope.frozen_base_root
        == ledger.get("frozen_base", {}).get("state_root"),
        "crosswalk_exact": envelope.crosswalk_digest
        == crosswalk["crosswalk_digest"],
        "graph_slice_known": graph_slice is not None,
        "graph_slice_exact": bool(
            graph_slice
            and envelope.graph_slice_digest == graph_slice["slice_digest"]
        ),
        "packet_bindings": all_packet_bindings,
    }
    verdict = "PASS" if all(checks.values()) else "HOLD"
    body = {
        "schema": "KC144.SignedEnvelopeVerification.V7",
        "envelope_id": envelope.envelope_id,
        "verdict": verdict,
        "checks": checks,
        "packet_reports": packet_reports,
        "packet_count": len(envelope.packets),
        "production_truth_effect": "NONE",
    }
    return {**body, "verification_digest": digest(body)}


def admit_signed_envelope(
    ledger: Mapping[str, Any],
    envelope: SignedEvidenceEnvelope,
    registry: Mapping[str, Any],
) -> dict[str, Any]:
    verification = verify_signed_envelope(envelope, registry, ledger)
    if verification["verdict"] != "PASS":
        return {
            "schema": "KC144.SignedEnvelopeAdmission.V7",
            "status": "HOLD",
            "atomic": True,
            "verification": verification,
            "ledger": dict(ledger),
            "records_admitted": 0,
            "production_truth_effect": "NONE",
        }

    envelope_digest = digest(envelope.to_dict())
    envelope_receipt = {
        "envelope_digest": envelope_digest,
        "envelope": envelope.to_dict(),
        "verification": verification,
    }
    staged_body = {
        key: value for key, value in ledger.items() if key != "ledger_digest"
    }
    staged_body["v7_envelopes"] = [
        *ledger.get("v7_envelopes", ()),
        envelope_receipt,
    ]
    staged = {**staged_body, "ledger_digest": digest(staged_body)}
    for packet in envelope.packets:
        trusted_authority = replace(
            packet.authority,
            signature_status="VERIFIED",
        )
        trusted_packet = replace(packet, authority=trusted_authority)
        context = {
            "schema": "KC144.CryptographicAdmissionContext.V7",
            "verdict": "PASS",
            "envelope_digest": envelope_digest,
            "verification_digest": verification["verification_digest"],
            "packet_digest": digest(trusted_packet.to_dict()),
            "authority_id": envelope.signer_key_id,
            "scope": trusted_packet.authority.scope,
        }
        report = admit_evidence(
            staged,
            trusted_packet,
            verification_context=context,
        )
        if report["status"] != "ADMITTED":
            return {
                "schema": "KC144.SignedEnvelopeAdmission.V7",
                "status": "HOLD",
                "atomic": True,
                "verification": verification,
                "failed_packet_id": packet.packet_id,
                "packet_admission": {
                    key: value
                    for key, value in report.items()
                    if key != "ledger"
                },
                "ledger": dict(ledger),
                "records_admitted": 0,
                "production_truth_effect": "NONE",
            }
        staged = report["ledger"]

    body = {
        "schema": "KC144.SignedEnvelopeAdmission.V7",
        "status": "ADMITTED",
        "atomic": True,
        "verification": verification,
        "envelope_digest": envelope_digest,
        "records_admitted": len(envelope.packets),
        "ledger": staged,
        "production_truth_effect": (
            "EVIDENCE_OVERLAY_ONLY"
            if ledger.get("namespace") == "PRODUCTION"
            else "NONE"
        ),
    }
    return {**body, "admission_digest": digest({k: v for k, v in body.items() if k != "ledger"})}


def production_evidence_contract() -> dict[str, Any]:
    crosswalk = compile_coordinate_crosswalk()
    graph_registry = graph_slice_registry()
    return {
        "schema": "KC144.ProductionEvidenceContract.V7",
        "epoch_id": ACTIVE_EPOCH_ID,
        "epoch_census": ACTIVE_EPOCH_CENSUS,
        "crosswalk_digest": crosswalk["crosswalk_digest"],
        "active_graph_slice": graph_registry["active_frozen_slice"],
        "graph_slice_registry_digest": graph_registry["registry_digest"],
        "signature_algorithm": "ED25519",
        "envelope_atomicity": "ALL_PACKETS_OR_NONE",
        "production_contradiction_law": {
            "NONE_FOUND": "ADMISSIBLE_IF_ALL_OTHER_GATES_PASS",
            "CONFIRMED": "DEFECT_CLOSURE_ONLY",
            "CONTESTED": "PRESERVE_AND_HOLD",
            "UNRESOLVED": "PRESERVE_AND_HOLD",
        },
        "domain_binding_law": (
            "every domain-population packet must reproduce its active-epoch "
            "canonical/runtime coordinate binding; preserved F37 conflicts "
            "also require a signed resolution receipt"
        ),
        "ic10_law": (
            "promotion requires conjunctive PASS for both "
            "IC10_constitutional and IC10_immune vectors"
        ),
        "compression_law": (
            "one signed causal envelope may carry many subject packets; "
            "every affected subject retains an individual receipt"
        ),
        "direct_v6_production_admission": "FORBIDDEN_WITHOUT_V7_ENVELOPE_CONTEXT",
        "direct_v5_bridge_commit": "FORBIDDEN_WITHOUT_V7_ENVELOPE_CONTEXT",
    }
