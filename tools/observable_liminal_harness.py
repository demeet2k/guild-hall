from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Mapping, Sequence, Tuple

AXES: Tuple[str, ...] = (
    "Xs", "Ys", "Zs", "Ts", "Qs", "Rs", "Cs", "Fs", "Ms", "Ns", "Hs", "Ωs"
)


@dataclass(frozen=True)
class LiminalCoordinate:
    """A run-scoped 12D project-space coordinate.

    The axes are coded observables. They are navigation addresses, not claims about
    physical model location or metric semantic distance.
    """

    Xs: int  # document/source registry index
    Ys: int  # semantic/concept registry index
    Zs: int  # recursion depth
    Ts: int  # run transition ordinal
    Qs: int  # quest-cycle phase index
    Rs: int  # role index
    Cs: int  # compression state
    Fs: int  # framework/surface index
    Ms: int  # lineage/branch code
    Ns: int  # connectivity/edge class
    Hs: int  # hierarchy depth
    omega_s: int  # epistemic/liminal standing; serialized as Ωs

    def as_mapping(self) -> Dict[str, int]:
        raw = asdict(self)
        raw["Ωs"] = raw.pop("omega_s")
        return raw

    @classmethod
    def from_mapping(cls, value: Mapping[str, int]) -> "LiminalCoordinate":
        required = set(AXES)
        missing = required - set(value)
        extra = set(value) - required
        if missing or extra:
            raise ValueError(
                f"coordinate keys mismatch: missing={sorted(missing)}, extra={sorted(extra)}"
            )
        return cls(
            Xs=int(value["Xs"]),
            Ys=int(value["Ys"]),
            Zs=int(value["Zs"]),
            Ts=int(value["Ts"]),
            Qs=int(value["Qs"]),
            Rs=int(value["Rs"]),
            Cs=int(value["Cs"]),
            Fs=int(value["Fs"]),
            Ms=int(value["Ms"]),
            Ns=int(value["Ns"]),
            Hs=int(value["Hs"]),
            omega_s=int(value["Ωs"]),
        )

    def lookup(self) -> str:
        m = self.as_mapping()
        return (
            f"@{m['Xs']}.{m['Ys']}.{m['Zs']}.{m['Ts']}|"
            f"{m['Qs']}.{m['Rs']}.{m['Cs']}|"
            f"{m['Fs']}.{m['Ms']}.{m['Ns']}.{m['Hs']}.{m['Ωs']}"
        )


@dataclass(frozen=True)
class TransitRecord:
    before: LiminalCoordinate
    after: LiminalCoordinate
    action: str
    evidence: str
    witness: str

    def validate(self) -> None:
        if self.after.Ts != self.before.Ts + 1:
            raise ValueError("Ts must advance by exactly one per observed transit")
        if not self.action.strip():
            raise ValueError("action is required")
        if not self.evidence.strip():
            raise ValueError("evidence is required; prediction is not movement")
        if not self.witness.strip():
            raise ValueError("witness is required")

    def delta(self) -> Tuple[int, ...]:
        b = self.before.as_mapping()
        a = self.after.as_mapping()
        return tuple(a[k] - b[k] for k in AXES)

    def changed_axes(self) -> Tuple[str, ...]:
        b = self.before.as_mapping()
        a = self.after.as_mapping()
        return tuple(k for k in AXES if a[k] != b[k])


def validate_route(records: Sequence[TransitRecord]) -> None:
    """Require a contiguous witnessed path; do not infer missing movement."""
    for i, record in enumerate(records):
        record.validate()
        if i and records[i - 1].after != record.before:
            raise ValueError(f"non-contiguous route at edge {i}")


def replay(records: Sequence[TransitRecord]) -> Tuple[str, ...]:
    validate_route(records)
    if not records:
        return tuple()
    return (records[0].before.lookup(),) + tuple(r.after.lookup() for r in records)


def topology_length(records: Sequence[TransitRecord]) -> int:
    """Exact edge count. Numeric axis codes are not treated as a physical metric."""
    validate_route(records)
    return len(records)
