from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any, Iterable

from memory_crystal.p03.model import canonical_digest, kc144_gid_to_grid

from .model import (
    ContextAtom,
    FrameworkAddress,
    LifecycleState,
    OriginClass,
    SourceRef,
    TruthState,
)
from .reentry import family_for_gid
from .store import NavStore


class ObservationKind(StrEnum):
    NATIVE_EXCERPT = "NATIVE_EXCERPT"
    SEARCH_HIT = "SEARCH_HIT"
    CONVERSATION_RETRIEVAL = "CONVERSATION_RETRIEVAL"
    REPOSITORY_FILE = "REPOSITORY_FILE"
    LOCAL_FILE = "LOCAL_FILE"


class MappingBasis(StrEnum):
    EXPLICIT_COORDINATE = "EXPLICIT_COORDINATE"
    DERIVED_COORDINATE = "DERIVED_COORDINATE"
    SEARCH_CANDIDATE = "SEARCH_CANDIDATE"
    UNMAPPED = "UNMAPPED"


class AdmissionStatus(StrEnum):
    ADMITTED = "ADMITTED"
    QUARANTINED = "QUARANTINED"
    COLLISION = "COLLISION"


@dataclass(frozen=True, slots=True)
class AtlasCell:
    epoch: str
    gid: int
    grid: str
    station: str
    station_aliases: tuple[str, ...]
    family: str
    structural_status: str
    source: SourceRef
    structural_digest: str

    @classmethod
    def build(
        cls,
        *,
        epoch: str,
        gid: int,
        station: str,
        family: str,
        source: SourceRef,
        station_aliases: tuple[str, ...] = (),
    ) -> "AtlasCell":
        row, column = kc144_gid_to_grid(gid)
        body = {
            "schema": "KC144.AtlasCell.V1",
            "epoch": epoch,
            "gid": gid,
            "grid": f"R{row:02d}C{column:02d}",
            "station": station,
            "station_aliases": sorted(set(station_aliases)),
            "family": family,
            "structural_status": "REGISTERED_NOT_CONTENT",
            "source_key": source.key,
        }
        return cls(
            epoch=epoch,
            gid=gid,
            grid=body["grid"],
            station=station,
            station_aliases=tuple(body["station_aliases"]),
            family=family,
            structural_status=body["structural_status"],
            source=source,
            structural_digest=canonical_digest(body),
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["source"]["key"] = self.source.key
        return value


@dataclass(frozen=True, slots=True)
class LiveObservation:
    observation_id: str
    carrier: str
    source_id: str
    revision: str
    locator: str
    fragment: str
    authority: str
    evidence_root: str
    kind: ObservationKind
    content: str
    metadata: tuple[tuple[str, str], ...]
    observed_at: str | None
    payload_digest: str

    @classmethod
    def build(
        cls,
        *,
        carrier: str,
        source_id: str,
        revision: str,
        locator: str,
        fragment: str,
        authority: str,
        evidence_root: str,
        kind: ObservationKind,
        content: str,
        metadata: dict[str, Any] | None = None,
        observed_at: str | None = None,
    ) -> "LiveObservation":
        required = (
            carrier,
            source_id,
            revision,
            locator,
            fragment,
            authority,
            evidence_root,
            content.strip(),
        )
        if not all(required):
            raise ValueError("live observation requires immutable source and content")
        metadata_items = tuple(
            sorted((str(key), str(value)) for key, value in (metadata or {}).items())
        )
        identity = {
            "schema": "KC144.LiveObservation.Identity.V1",
            "carrier": carrier,
            "source_id": source_id,
            "revision": revision,
            "fragment": fragment,
        }
        payload = {
            "schema": "KC144.LiveObservation.Payload.V1",
            "locator": locator,
            "authority": authority,
            "evidence_root": evidence_root,
            "kind": kind.value,
            "content": content,
            "metadata": metadata_items,
            "observed_at": observed_at,
        }
        return cls(
            observation_id=canonical_digest(identity),
            carrier=carrier,
            source_id=source_id,
            revision=revision,
            locator=locator,
            fragment=fragment,
            authority=authority,
            evidence_root=evidence_root,
            kind=kind,
            content=content,
            metadata=metadata_items,
            observed_at=observed_at,
            payload_digest=canonical_digest(payload),
        )

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "LiveObservation":
        return cls.build(
            carrier=value["carrier"],
            source_id=value["source_id"],
            revision=value["revision"],
            locator=value["locator"],
            fragment=value["fragment"],
            authority=value["authority"],
            evidence_root=value["evidence_root"],
            kind=ObservationKind(value["kind"]),
            content=value["content"],
            metadata=value.get("metadata"),
            observed_at=value.get("observed_at"),
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["kind"] = self.kind.value
        value["metadata"] = dict(self.metadata)
        return value


@dataclass(frozen=True, slots=True)
class AdmissionClaim:
    claim_id: str
    observation_id: str
    address: FrameworkAddress
    basis: MappingBasis
    exact_text: str
    status: AdmissionStatus
    reason: str
    atom_id: str | None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["basis"] = self.basis.value
        value["status"] = self.status.value
        value["address"]["key"] = self.address.key
        value["address"]["grid"] = self.address.grid
        return value


@dataclass(frozen=True, slots=True)
class LiveIngestResult:
    atlas: tuple[tuple[str, int], ...]
    observations: tuple[tuple[str, int], ...]
    claims: tuple[AdmissionClaim, ...]


@dataclass(frozen=True, slots=True)
class AtlasCoverageReport:
    registered_cells: int
    expected_cells: int
    structural_coverage: float
    content_gids: tuple[int, ...]
    content_coverage: float
    source_bound_gids: tuple[int, ...]
    source_bound_coverage: float
    retrieval_only_gids: tuple[int, ...]
    retrieval_only_coverage: float
    admitted_claim_gids: tuple[int, ...]
    quarantined_claims: int
    observation_count: int
    observed_carriers: tuple[str, ...]
    required_carriers: tuple[str, ...]
    carrier_coverage: float
    unresolved_content_gids: tuple[int, ...]
    defects: tuple[str, ...]
    digest: str


def _station_for_gid(gid: int) -> tuple[str, tuple[str, ...]]:
    if 1 <= gid <= 6:
        station = f"H{gid:02d}"
        return station, ()
    if 7 <= gid <= 22:
        poles = ("11", "10", "00", "01")
        lenses = ("SQ", "FL", "CL", "FR")
        offset = gid - 7
        return f"X-{poles[offset // 4]}-{lenses[offset % 4]}", ()
    if 23 <= gid <= 43:
        return f"B{gid - 22:02d}", ()
    if 44 <= gid <= 80:
        return f"F{gid - 43:02d}", ()
    if 81 <= gid <= 90:
        index = gid - 80
        return f"IC10-I{index:02d}", (f"I{index:02d}",)
    if 91 <= gid <= 105:
        return f"KC15-{gid - 90:02d}", ()
    if 106 <= gid <= 132:
        return f"KC27-P{gid - 106:02d}", (f"P{gid - 106:02d}",)
    index = gid - 132
    return f"SSN-M{index:02d}", (f"M{index:02d}",)


def build_active_atlas(source: SourceRef) -> tuple[AtlasCell, ...]:
    return tuple(
        AtlasCell.build(
            epoch="KC144.V1",
            gid=gid,
            station=_station_for_gid(gid)[0],
            station_aliases=_station_for_gid(gid)[1],
            family=family_for_gid(gid),
            source=source,
        )
        for gid in range(1, 145)
    )


class LiveContextCompiler:
    def __init__(self, store: NavStore) -> None:
        self.store = store

    def ingest_bundle(self, bundle: dict[str, Any]) -> LiveIngestResult:
        atlas_source = SourceRef.from_dict(bundle["atlas_source"])
        atlas_counts: dict[str, int] = defaultdict(int)
        for cell in build_active_atlas(atlas_source):
            atlas_counts[self.store.register_atlas_cell(cell.to_dict())] += 1

        observations: dict[str, LiveObservation] = {}
        observation_counts: dict[str, int] = defaultdict(int)
        for row in bundle.get("observations", ()):
            alias = str(row.get("alias", "")).strip()
            if not alias:
                raise ValueError("observation alias is required")
            if alias in observations:
                raise ValueError(f"duplicate observation alias: {alias}")
            observation = LiveObservation.from_dict(row)
            observations[alias] = observation
            observation_counts[
                self.store.save_observation(observation.to_dict())
            ] += 1

        claims = tuple(
            self._admit_claim(observations, row)
            for row in bundle.get("claims", ())
        )
        return LiveIngestResult(
            atlas=tuple(sorted(atlas_counts.items())),
            observations=tuple(sorted(observation_counts.items())),
            claims=claims,
        )

    def _admit_claim(
        self,
        observations: dict[str, LiveObservation],
        row: dict[str, Any],
    ) -> AdmissionClaim:
        alias = row["observation"]
        if alias not in observations:
            raise KeyError(f"unknown observation alias: {alias}")
        observation = observations[alias]
        address = FrameworkAddress.from_dict(row["address"])
        basis = MappingBasis(row.get("basis", "UNMAPPED"))
        exact_text = str(row.get("exact_text", "")).strip()
        reason = "EXPLICIT_SOURCE_COORDINATE_VERIFIED"
        status = AdmissionStatus.ADMITTED
        atom: ContextAtom | None = None

        if basis != MappingBasis.EXPLICIT_COORDINATE:
            status = AdmissionStatus.QUARANTINED
            reason = f"{basis.value}_CANNOT_POPULATE_CONTENT"
        elif not exact_text or exact_text not in observation.content:
            status = AdmissionStatus.QUARANTINED
            reason = "EXCERPT_NOT_EXACT_SUBSTRING_OF_OBSERVATION"
        elif (
            f"GID{address.gid:03d}" not in exact_text
            and f"GID-{address.gid:03d}" not in exact_text
        ):
            status = AdmissionStatus.QUARANTINED
            reason = "EXPLICIT_GID_TOKEN_ABSENT_FROM_EXCERPT"
        else:
            cell = self.store.atlas_cell(address.gid, epoch=address.epoch)
            if cell is None:
                status = AdmissionStatus.QUARANTINED
                reason = "ATLAS_CELL_NOT_REGISTERED"
            else:
                legal_stations = {cell["station"], *cell["station_aliases"]}
                if address.station not in legal_stations:
                    status = AdmissionStatus.QUARANTINED
                    reason = (
                        f"STATION_MISMATCH::{address.station}"
                        f"::EXPECTED={','.join(sorted(legal_stations))}"
                    )

        if status == AdmissionStatus.ADMITTED:
            source = SourceRef(
                carrier=observation.carrier,
                source_id=observation.source_id,
                revision=observation.revision,
                locator=f"{observation.locator}#{observation.fragment}",
                authority=observation.authority,
                evidence_root=observation.evidence_root,
                observed_at=observation.observed_at,
            )
            lifecycle = (
                LifecycleState.RETRIEVED_FRAGMENT
                if observation.kind
                in {
                    ObservationKind.SEARCH_HIT,
                    ObservationKind.CONVERSATION_RETRIEVAL,
                }
                else LifecycleState.SOURCE_BOUND
            )
            origin = OriginClass(
                row.get("origin_class", _origin_for_carrier(observation.carrier).value)
            )
            atom = ContextAtom.build(
                source=source,
                address=address,
                exact_text=exact_text,
                origin_class=origin,
                truth=TruthState(row.get("truth", "RESID")),
                lifecycle=lifecycle,
                tags=tuple(row.get("tags", ()))
                + (
                    "LIVE_CONTEXT",
                    observation.kind.value,
                    basis.value,
                ),
                witnesses=tuple(row.get("witnesses", ()))
                + (f"observation:{observation.observation_id}",),
            )
            atom_result = self.store.ingest_atom(atom)
            if atom_result == "IDENTITY_COLLISION":
                status = AdmissionStatus.COLLISION
                reason = "ATOM_IDENTITY_COLLISION"

        claim_identity = {
            "schema": "KC144.AdmissionClaim.Identity.V1",
            "observation_id": observation.observation_id,
            "address": address.key,
            "basis": basis.value,
            "exact_text": exact_text,
        }
        claim = AdmissionClaim(
            claim_id=canonical_digest(claim_identity),
            observation_id=observation.observation_id,
            address=address,
            basis=basis,
            exact_text=exact_text,
            status=status,
            reason=reason,
            atom_id=atom.atom_id if atom and status == AdmissionStatus.ADMITTED else None,
        )
        self.store.save_admission_claim(claim.to_dict())
        return claim


class AtlasCoverageAuditor:
    def __init__(
        self,
        store: NavStore,
        *,
        required_carriers: Iterable[str] = (
            "conversation_retrieval",
            "google_doc",
            "github_seed",
            "local_file",
        ),
    ) -> None:
        self.store = store
        self.required_carriers = tuple(sorted(set(required_carriers)))

    def audit(self) -> AtlasCoverageReport:
        cells = self.store.atlas_cells()
        registered_gids = {
            int(cell["gid"]) for cell in cells if cell["epoch"] == "KC144.V1"
        }
        atoms = self.store.atoms()
        content_gids = {atom.address.gid for atom in atoms}
        source_bound_gids = {
            atom.address.gid
            for atom in atoms
            if atom.lifecycle != LifecycleState.RETRIEVED_FRAGMENT
        }
        retrieval_only = content_gids - source_bound_gids
        claims = self.store.admission_claims()
        admitted_claim_gids = {
            int(claim["address"]["gid"])
            for claim in claims
            if claim["status"] == AdmissionStatus.ADMITTED.value
        }
        quarantined = sum(
            claim["status"] != AdmissionStatus.ADMITTED.value for claim in claims
        )
        observations = self.store.observations()
        observed_carriers = tuple(
            sorted({observation["carrier"] for observation in observations})
        )
        required = set(self.required_carriers)
        observed_required = required & set(observed_carriers)
        defects: list[str] = []
        if len(registered_gids) != 144:
            defects.append("STRUCTURAL_ATLAS_INCOMPLETE")
        if len(source_bound_gids) != 144:
            defects.append("SOURCE_BOUND_CONTENT_INCOMPLETE")
        if retrieval_only:
            defects.append("RETRIEVAL_ONLY_CONTENT_PRESENT")
        if observed_required != required:
            defects.append("REQUIRED_CARRIER_SET_INCOMPLETE")
        if quarantined:
            defects.append("QUARANTINED_MAPPING_CLAIMS_PRESENT")
        body = {
            "registered_gids": sorted(registered_gids),
            "content_gids": sorted(content_gids),
            "source_bound_gids": sorted(source_bound_gids),
            "retrieval_only": sorted(retrieval_only),
            "admitted_claim_gids": sorted(admitted_claim_gids),
            "quarantined": quarantined,
            "observed_carriers": observed_carriers,
            "required_carriers": self.required_carriers,
            "defects": defects,
        }
        return AtlasCoverageReport(
            registered_cells=len(registered_gids),
            expected_cells=144,
            structural_coverage=len(registered_gids) / 144,
            content_gids=tuple(sorted(content_gids)),
            content_coverage=len(content_gids) / 144,
            source_bound_gids=tuple(sorted(source_bound_gids)),
            source_bound_coverage=len(source_bound_gids) / 144,
            retrieval_only_gids=tuple(sorted(retrieval_only)),
            retrieval_only_coverage=len(retrieval_only) / 144,
            admitted_claim_gids=tuple(sorted(admitted_claim_gids)),
            quarantined_claims=quarantined,
            observation_count=len(observations),
            observed_carriers=observed_carriers,
            required_carriers=self.required_carriers,
            carrier_coverage=(
                len(observed_required) / len(required) if required else 1.0
            ),
            unresolved_content_gids=tuple(
                sorted(set(range(1, 145)) - source_bound_gids)
            ),
            defects=tuple(defects),
            digest=canonical_digest(body),
        )


def _origin_for_carrier(carrier: str) -> OriginClass:
    if carrier == "google_doc":
        return OriginClass.GOOGLE_DOC
    if carrier in {"github_seed", "git_repository"}:
        return OriginClass.GITHUB_SEED
    if carrier == "local_file":
        return OriginClass.LOCAL_FILE
    if carrier in {"conversation", "conversation_retrieval"}:
        return OriginClass.INTERNAL_HISTORY
    return OriginClass.RUNTIME
