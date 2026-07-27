from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from .edge_manifest import freeze_edge_manifest
from .navigation import DECLARED_BRIDGES
from .population import crystallize, digest
from .station import build_station_bodies


EVIDENCE_KINDS = (
    "BRIDGE_CERTIFICATION",
    "DOMAIN_POPULATION",
    "INDEPENDENT_REPLAY",
    "DEFECT_CLOSURE",
    "IC10_PROMOTION",
)
REPAIR_LAYER = {
    "BRIDGE_CERTIFICATION": "TRANSPORT",
    "DOMAIN_POPULATION": "SOURCE_BINDING",
    "INDEPENDENT_REPLAY": "REPLAY",
    "DEFECT_CLOSURE": "DEFECT",
    "IC10_PROMOTION": "PROMOTION",
}
REPLAY_CLASSES = {
    "BRIDGE_CERTIFICATION": {"B3", "B4"},
    "DOMAIN_POPULATION": {"B2", "B3", "B4"},
    "INDEPENDENT_REPLAY": {"EXACT"},
    "DEFECT_CLOSURE": {"EXACT"},
    "IC10_PROMOTION": {"EXACT"},
}
IC10_GATES = tuple(f"I{index:02d}" for index in range(1, 11))
BASELINE_BLOCKING_DEFECTS = ("DEF-M12-OPEN-GATES",)
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class EvidenceAuthority:
    authority_id: str
    scope: str
    signature_status: str
    independent: bool
    test_only: bool = False

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EvidenceAuthority":
        return cls(**dict(value))


@dataclass(frozen=True)
class M12EvidencePacket:
    packet_id: str
    kind: str
    subject_id: str
    namespace: str
    evidence_class: str
    evidence_root: str
    source_ref: str
    replay_class: str
    contradiction_class: str
    repair_layer: str
    trust_revision_witness: str
    reentry_permit_id: str
    payload: Mapping[str, Any]
    payload_digest: str
    authority: EvidenceAuthority

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "M12EvidencePacket":
        body = dict(value)
        body["authority"] = EvidenceAuthority.from_dict(body["authority"])
        body["payload"] = dict(body["payload"])
        return cls(**body)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _domain_baseline() -> tuple[int, ...]:
    return tuple(
        body["gid"]
        for body in build_station_bodies()
        if body["domain_state"] == "SOURCE_DECLARED"
    )


def _targets() -> dict[str, tuple[str, ...]]:
    baseline = set(_domain_baseline())
    return {
        "BRIDGE_CERTIFICATION": tuple(
            sorted(bridge.bridge_id for bridge in DECLARED_BRIDGES)
        ),
        "DOMAIN_POPULATION": tuple(
            f"GID{gid:03d}" for gid in range(1, 145) if gid not in baseline
        ),
        "INDEPENDENT_REPLAY": tuple(
            f"GID{gid:03d}" for gid in range(1, 145)
        ),
        "DEFECT_CLOSURE": BASELINE_BLOCKING_DEFECTS,
        "IC10_PROMOTION": ("KC144.SSN12.GLOBAL_STATE.V5",),
    }


def evidence_packet_contract() -> dict[str, Any]:
    targets = _targets()
    return {
        "schema": "KC144.M12EvidenceContract.V6",
        "packet_schema": "KC144.M12EvidencePacket.V6",
        "evidence_kinds": list(EVIDENCE_KINDS),
        "targets": {
            kind: {
                "required_subjects": len(subjects),
                "subject_ids": list(subjects),
                "repair_layer": REPAIR_LAYER[kind],
                "replay_classes": sorted(REPLAY_CLASSES[kind]),
            }
            for kind, subjects in targets.items()
        },
        "authority_law": (
            "VERIFIED scope-bound authority and an independent evidence root are "
            "required; IC10 is the sole successor-promotion authority"
        ),
        "namespace_law": (
            "TEST packets can exercise mechanics only; they never affect production "
            "M12 state or emit a production successor"
        ),
        "immune_reentry_law": (
            "every packet types contradiction, names the matched repair layer, "
            "witnesses trust revision, and carries a bounded reentry permit"
        ),
    }


def _seal_ledger(body: Mapping[str, Any]) -> dict[str, Any]:
    plain = dict(body)
    return {**plain, "ledger_digest": digest(plain)}


def empty_repair_ledger(
    *,
    namespace: str = "PRODUCTION",
    base_state_root: str | None = None,
) -> dict[str, Any]:
    if namespace not in {"PRODUCTION", "TEST"}:
        raise ValueError("namespace must be PRODUCTION or TEST")
    crystal_digest = crystallize()["digest"]
    edge_manifest_digest = freeze_edge_manifest()["manifest_digest"]
    state_root = base_state_root or digest(
        {
            "release": "KC144.SSN12.GLOBAL_STATE.V5",
            "crystal_digest": crystal_digest,
            "edge_manifest_digest": edge_manifest_digest,
        }
    )
    body = {
        "schema": "KC144.M12RepairLedger.V6",
        "namespace": namespace,
        "frozen_base": {
            "release": "KC144.SSN12.GLOBAL_STATE.V5",
            "candidate_id": "KC144.SSN12.GLOBAL_STATE.V5",
            "state_root": state_root,
            "crystal_digest": crystal_digest,
            "edge_manifest_digest": edge_manifest_digest,
            "mutation_allowed": False,
        },
        "baseline": {
            "domain_population_gids": list(_domain_baseline()),
            "blocking_defect_ids": list(BASELINE_BLOCKING_DEFECTS),
            "certified_bridge_ids": [],
            "independent_replay_gids": [],
            "ic10_promotions": [],
        },
        "records": [],
        "head_digest": "GENESIS",
        "truth_effect": "NONE",
    }
    return _seal_ledger(body)


def verify_repair_ledger(ledger: Mapping[str, Any]) -> dict[str, Any]:
    records = list(ledger.get("records", ()))
    envelope_receipts = {
        row.get("envelope_digest"): row
        for row in ledger.get("v7_envelopes", ())
    }
    previous = "GENESIS"
    record_chain = True
    production_context_chain = True
    for sequence, record in enumerate(records, start=1):
        record_body = {
            key: value for key, value in record.items() if key != "record_digest"
        }
        if (
            record.get("sequence") != sequence
            or record.get("previous_record_digest") != previous
            or record.get("record_digest") != digest(record_body)
        ):
            record_chain = False
            break
        if ledger.get("namespace") == "PRODUCTION":
            context = record.get("cryptographic_context", {})
            envelope_receipt = envelope_receipts.get(
                context.get("envelope_digest")
            )
            if not (
                context.get("schema")
                == "KC144.CryptographicAdmissionContext.V7"
                and context.get("verdict") == "PASS"
                and context.get("packet_digest")
                == digest(record.get("packet", {}))
                and envelope_receipt is not None
                and digest(envelope_receipt.get("envelope", {}))
                == context.get("envelope_digest")
                and envelope_receipt.get("verification", {}).get("verdict")
                == "PASS"
                and envelope_receipt.get("verification", {}).get(
                    "verification_digest"
                )
                == context.get("verification_digest")
            ):
                production_context_chain = False
                break
        previous = str(record["record_digest"])
    ledger_body = {
        key: value for key, value in ledger.items() if key != "ledger_digest"
    }
    checks = {
        "schema": ledger.get("schema") == "KC144.M12RepairLedger.V6",
        "namespace": ledger.get("namespace") in {"PRODUCTION", "TEST"},
        "frozen_base": ledger.get("frozen_base", {}).get("mutation_allowed") is False,
        "record_chain": record_chain,
        "production_context_chain": production_context_chain,
        "head_exact": ledger.get("head_digest") == previous,
        "ledger_digest": ledger.get("ledger_digest") == digest(ledger_body),
    }
    return {
        "verdict": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "records": len(records),
        "head_digest": previous,
    }


def _payload_checks(
    packet: M12EvidencePacket,
    ledger: Mapping[str, Any],
) -> dict[str, bool]:
    payload = packet.payload
    checks: dict[str, bool] = {}
    if packet.kind == "BRIDGE_CERTIFICATION":
        checks.update(
            {
                "payload_subject_exact": payload.get("bridge_id")
                == packet.subject_id,
                "namespace_commit": payload.get("standing")
                == (
                    "PRODUCTION_TRANSPORT_COMMIT"
                    if packet.namespace == "PRODUCTION"
                    else "TEST_ONLY_TRANSPORT_COMMIT"
                ),
                "commit_digest": bool(SHA256.fullmatch(str(payload.get("commit_digest", "")))),
                "evaluation_digest": bool(
                    SHA256.fullmatch(
                        str(payload.get("transport_evaluation_digest", ""))
                    )
                ),
                "return_witness_root": bool(
                    SHA256.fullmatch(str(payload.get("return_witness_root", "")))
                ),
            }
        )
    elif packet.kind == "DOMAIN_POPULATION":
        checks.update(
            {
                "payload_subject_exact": payload.get("gid")
                == int(packet.subject_id[3:]),
                "source_object_id": bool(str(payload.get("source_object_id", "")).strip()),
                "content_digest": bool(
                    SHA256.fullmatch(str(payload.get("content_digest", "")))
                ),
                "carrier_typed": bool(str(payload.get("carrier", "")).strip()),
            }
        )
    elif packet.kind == "INDEPENDENT_REPLAY":
        checks.update(
            {
                "payload_subject_exact": payload.get("gid")
                == int(packet.subject_id[3:]),
                "expected_state_root": bool(
                    SHA256.fullmatch(str(payload.get("expected_state_root", "")))
                ),
                "replayed_state_root": payload.get("replayed_state_root")
                == payload.get("expected_state_root"),
                "result_exact": payload.get("result") == "EXACT",
            }
        )
    elif packet.kind == "DEFECT_CLOSURE":
        checks.update(
            {
                "payload_subject_exact": payload.get("defect_id")
                == packet.subject_id,
                "closure_exact": payload.get("result") == "CLOSED",
                "closure_root": bool(
                    SHA256.fullmatch(str(payload.get("closure_root", "")))
                ),
            }
        )
    elif packet.kind == "IC10_PROMOTION":
        vector = payload.get("gate_vector", {})
        checks.update(
            {
                "payload_subject_exact": payload.get("candidate_id")
                == packet.subject_id,
                "decision_promoted": payload.get("decision") == "PROMOTED",
                "state_root_exact": payload.get("state_root")
                == ledger.get("frozen_base", {}).get("state_root"),
                "ic10_conjunctive": set(vector) == set(IC10_GATES)
                and all(vector[gate] == "PASS" for gate in IC10_GATES),
                "successor_exact": payload.get("successor_seed")
                == "KC144.V2::POPULATE_MATH144",
            }
        )
    return checks


def evidence_summary(ledger: Mapping[str, Any]) -> dict[str, Any]:
    observed: dict[str, set[str]] = {kind: set() for kind in EVIDENCE_KINDS}
    for record in ledger.get("records", ()):
        packet = record["packet"]
        observed[packet["kind"]].add(packet["subject_id"])
    baseline_domains = {
        f"GID{gid:03d}"
        for gid in ledger.get("baseline", {}).get("domain_population_gids", ())
    }
    closed_defects = observed["DEFECT_CLOSURE"]
    open_defects = set(
        ledger.get("baseline", {}).get("blocking_defect_ids", ())
    ) - closed_defects
    observed_state = {
        "certified_bridges": len(observed["BRIDGE_CERTIFICATION"]),
        "domain_population": len(baseline_domains | observed["DOMAIN_POPULATION"]),
        "independent_replays": len(observed["INDEPENDENT_REPLAY"]),
        "blocking_defects": len(open_defects),
        "ic10_promoted": bool(observed["IC10_PROMOTION"]),
    }
    effective_state = (
        observed_state
        if ledger.get("namespace") == "PRODUCTION"
        else {
            "certified_bridges": 0,
            "domain_population": len(baseline_domains),
            "independent_replays": 0,
            "blocking_defects": len(
                ledger.get("baseline", {}).get("blocking_defect_ids", ())
            ),
            "ic10_promoted": False,
        }
    )
    return {
        "namespace": ledger.get("namespace"),
        "admitted_packet_counts": {
            kind: len(subjects) for kind, subjects in observed.items()
        },
        "observed_state": observed_state,
        "production_effective_state": effective_state,
        "open_defect_ids": sorted(open_defects),
        "production_truth_effect": (
            "EVIDENCE_OVERLAY_ONLY"
            if ledger.get("namespace") == "PRODUCTION" and ledger.get("records")
            else "NONE"
        ),
    }


def repair_plan(ledger: Mapping[str, Any]) -> dict[str, Any]:
    summary = evidence_summary(ledger)
    state = summary["observed_state"]
    empirical_complete = (
        state["certified_bridges"] == 28
        and state["domain_population"] == 144
        and state["independent_replays"] == 144
    )
    defects_complete = state["blocking_defects"] == 0
    ic10_complete = state["ic10_promoted"]
    definitions = (
        (
            "R01_CERTIFY_BRIDGES",
            "M12_BRIDGES_CERTIFIED_28",
            28,
            state["certified_bridges"],
            (),
            True,
        ),
        (
            "R02_POPULATE_DOMAINS",
            "M12_DOMAIN_POPULATION_144",
            144,
            state["domain_population"],
            (),
            True,
        ),
        (
            "R03_REPLAY_STATIONS",
            "M12_INDEPENDENT_REPLAY_144",
            144,
            state["independent_replays"],
            (),
            True,
        ),
        (
            "R04_CLOSE_BLOCKING_DEFECTS",
            "M12_BLOCKING_DEFECTS_EMPTY",
            1,
            1 - state["blocking_defects"],
            (
                "R01_CERTIFY_BRIDGES",
                "R02_POPULATE_DOMAINS",
                "R03_REPLAY_STATIONS",
            ),
            empirical_complete,
        ),
        (
            "R05_IC10_ADJUDICATE",
            "M12_IC10_DECISION_PROMOTED",
            1,
            int(ic10_complete),
            ("R04_CLOSE_BLOCKING_DEFECTS",),
            empirical_complete and defects_complete,
        ),
        (
            "R06_M12_RECOMPUTE",
            "M12_SOLID_STATE",
            1,
            int(empirical_complete and defects_complete and ic10_complete),
            ("R05_IC10_ADJUDICATE",),
            empirical_complete and defects_complete and ic10_complete,
        ),
    )
    tasks = []
    for task_id, gate, required, admitted, dependencies, ready in definitions:
        complete = admitted >= required
        tasks.append(
            {
                "task_id": task_id,
                "gate": gate,
                "required": required,
                "admitted": admitted,
                "remaining": max(0, required - admitted),
                "dependencies": list(dependencies),
                "execution": (
                    "PARALLEL_WAVE"
                    if task_id
                    in {
                        "R01_CERTIFY_BRIDGES",
                        "R02_POPULATE_DOMAINS",
                        "R03_REPLAY_STATIONS",
                    }
                    else "DEPENDENCY_BOUND"
                ),
                "status": (
                    "COMPLETE"
                    if complete
                    else "READY"
                    if ready
                    else "BLOCKED"
                ),
            }
        )
    return {
        "schema": "KC144.M12RepairPlan.V6",
        "scheduler": "DEPENDENCY_DAG_WITH_PARALLEL_EVIDENCE_WAVES",
        "tasks": tasks,
        "next_frontier": [
            task["task_id"] for task in tasks if task["status"] == "READY"
        ],
        "mutation_target": "APPEND_ONLY_EVIDENCE_OVERLAY",
        "frozen_crystal_mutated": False,
    }


def admit_evidence(
    ledger: Mapping[str, Any],
    packet: M12EvidencePacket,
    *,
    verification_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    targets = _targets()
    existing = list(ledger.get("records", ()))
    authority_scope = (
        f"KC144.IC10.PROMOTION::{packet.subject_id}"
        if packet.kind == "IC10_PROMOTION"
        else f"KC144.M12.{packet.kind}::{packet.subject_id}"
    )
    checks = {
        "ledger_integrity": verify_repair_ledger(ledger)["verdict"] == "PASS",
        "kind_known": packet.kind in EVIDENCE_KINDS,
        "subject_exact": packet.kind in targets
        and packet.subject_id in targets[packet.kind],
        "namespace_exact": packet.namespace == ledger.get("namespace"),
        "production_external": not (
            packet.namespace == "PRODUCTION"
            and (
                packet.evidence_class != "EXTERNAL"
                or packet.authority.test_only
                or any(
                    marker in packet.packet_id.upper()
                    for marker in ("SYNTHETIC", "FIXTURE", "TEST")
                )
            )
        ),
        "evidence_root": bool(SHA256.fullmatch(packet.evidence_root)),
        "source_ref": bool(packet.source_ref.strip()),
        "payload_digest_exact": packet.payload_digest == digest(packet.payload),
        "replay_class": packet.kind in REPLAY_CLASSES
        and packet.replay_class in REPLAY_CLASSES[packet.kind],
        "contradiction_typed": packet.contradiction_class
        in {"NONE_FOUND", "CONFIRMED", "CONTESTED", "UNRESOLVED"},
        "repair_layer_exact": packet.kind in REPAIR_LAYER
        and packet.repair_layer == REPAIR_LAYER[packet.kind],
        "trust_revision_witnessed": bool(packet.trust_revision_witness.strip()),
        "bounded_reentry_permit": bool(packet.reentry_permit_id.strip()),
        "authority_verified": packet.authority.signature_status == "VERIFIED",
        "authority_independent": packet.authority.independent,
        "authority_scope_exact": packet.authority.scope == authority_scope,
        "packet_unique": all(
            row["packet"]["packet_id"] != packet.packet_id for row in existing
        ),
        "evidence_root_unique": all(
            row["packet"]["evidence_root"] != packet.evidence_root
            for row in existing
        ),
        "subject_unique": all(
            not (
                row["packet"]["kind"] == packet.kind
                and row["packet"]["subject_id"] == packet.subject_id
            )
            for row in existing
        ),
        "cryptographic_envelope": (
            packet.namespace != "PRODUCTION"
            or (
                verification_context is not None
                and verification_context.get("schema")
                == "KC144.CryptographicAdmissionContext.V7"
                and verification_context.get("verdict") == "PASS"
                and bool(
                    SHA256.fullmatch(
                        str(verification_context.get("envelope_digest", ""))
                    )
                )
                and bool(
                    SHA256.fullmatch(
                        str(
                            verification_context.get(
                                "verification_digest",
                                "",
                            )
                        )
                    )
                )
                and verification_context.get("packet_digest")
                == digest(packet.to_dict())
                and verification_context.get("authority_id")
                == packet.authority.authority_id
                and verification_context.get("scope")
                == packet.authority.scope
            )
        ),
    }
    if packet.kind in EVIDENCE_KINDS:
        checks.update(_payload_checks(packet, ledger))
    current_state = evidence_summary(ledger)["observed_state"]
    empirical_complete = (
        current_state["certified_bridges"] == 28
        and current_state["domain_population"] == 144
        and current_state["independent_replays"] == 144
    )
    checks["dependency_ready"] = (
        empirical_complete
        if packet.kind == "DEFECT_CLOSURE"
        else empirical_complete and current_state["blocking_defects"] == 0
        if packet.kind == "IC10_PROMOTION"
        else True
    )
    admitted = all(checks.values())
    next_ledger = dict(ledger)
    if admitted:
        packet_body = packet.to_dict()
        record_body = {
            "sequence": len(existing) + 1,
            "previous_record_digest": ledger["head_digest"],
            "packet": packet_body,
            "packet_digest": digest(packet_body),
            "admission_effect": (
                "TEST_MECHANICS_ONLY"
                if ledger["namespace"] == "TEST"
                else "PRODUCTION_EVIDENCE_OVERLAY"
            ),
            "frozen_crystal_mutated": False,
            **(
                {"cryptographic_context": dict(verification_context)}
                if ledger["namespace"] == "PRODUCTION"
                else {}
            ),
        }
        record = {**record_body, "record_digest": digest(record_body)}
        ledger_body = {
            key: value for key, value in ledger.items() if key != "ledger_digest"
        }
        ledger_body["records"] = [*existing, record]
        ledger_body["head_digest"] = record["record_digest"]
        ledger_body["truth_effect"] = (
            "NONE"
            if ledger["namespace"] == "TEST"
            else "EVIDENCE_OVERLAY_ONLY"
        )
        next_ledger = _seal_ledger(ledger_body)
    return {
        "schema": "KC144.M12EvidenceAdmission.V6",
        "status": "ADMITTED" if admitted else "HOLD",
        "checks": checks,
        "record": next_ledger.get("records", [None])[-1] if admitted else None,
        "ledger": next_ledger,
        "frozen_crystal_mutated": False,
        "promotion_effect": (
            "IC10_DECISION_RECORDED"
            if admitted
            and packet.kind == "IC10_PROMOTION"
            and ledger["namespace"] == "PRODUCTION"
            else "NONE"
        ),
    }
