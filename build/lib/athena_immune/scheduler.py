from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .canonical import content_hash, utc_now
from .models import RepairItem, RepairStatus


class RepairScheduler:
    """Collect and rank repairs without collapsing unresolved branches."""

    def collect(self, contradiction: dict[str, Any]) -> list[RepairItem]:
        contradiction_id = str(contradiction["contradiction_id"])
        repairs: list[RepairItem] = []
        for index, candidate in enumerate(contradiction.get("candidate_repairs", []), start=1):
            residual_code = str(candidate.get("residual_code", "UNRESOLVED"))
            repair_id = str(
                candidate.get("repair_id")
                or f"{contradiction_id}.REPAIR.{index:03d}"
            )
            repairs.append(
                RepairItem(
                    repair_id=repair_id,
                    contradiction_id=contradiction_id,
                    residual_code=residual_code,
                    damaged_layer=str(candidate.get("damaged_layer", "unknown")),
                    required_operation=str(candidate.get("operation", "PRESERVE_UNRESOLVED")),
                    required_witnesses=list(candidate.get("required_witnesses", [])),
                    dependencies=list(candidate.get("dependencies", [])),
                    blockers=list(candidate.get("blockers", [])),
                    propagation_radius=int(candidate.get("propagation_radius", 0)),
                    severity=float(candidate.get("severity", contradiction.get("severity", 0.0))),
                    harm_sensitive=bool(candidate.get("harm_sensitive", False)),
                    replay_blocking=bool(candidate.get("replay_blocking", False)),
                    reversible=bool(candidate.get("reversible", True)),
                    assigned_role=str(candidate.get("assigned_role", "INTEGRATOR")),
                )
            )
        return repairs

    def rank(self, items: Iterable[RepairItem]) -> list[RepairItem]:
        return sorted(
            items,
            key=lambda item: (
                -item.priority_vector[0],
                -item.priority_vector[1],
                -item.priority_vector[2],
                -item.priority_vector[3],
                -item.priority_vector[4],
                item.priority_vector[5],
                item.repair_id,
            ),
        )

    def schedule(self, contradiction: dict[str, Any]) -> dict[str, Any]:
        ranked = self.rank(self.collect(contradiction))
        for item in ranked:
            item.status = RepairStatus.SCHEDULED
        body = {
            "schema_version": "ATHENA_REPAIR_PLAN/1",
            "plan_id": f"{contradiction['contradiction_id']}.PLAN",
            "contradiction_id": contradiction["contradiction_id"],
            "priority_law": [
                "blocking",
                "safety_harm",
                "replay_failure",
                "propagation_radius",
                "severity",
                "age",
            ],
            "items": [item.to_dict() for item in ranked],
            "unresolved_preserved": not bool(ranked),
            "created_at": utc_now(),
        }
        body["packet_hash"] = content_hash(body)
        return body

