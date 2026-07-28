from __future__ import annotations

import hashlib
import io
import json
import stat
import sys
import tempfile
import zipfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any, Iterator, Mapping

from .agent_receipts import content_address


P31_RELEASE_ID = "KC144_P31_LIVE_COGNITION_OS_V3_3"
P31_RESULT_ID = "KC144.P31::db5a6446ce54cf4bc53515be"
P31_PARENT_RESULT_ID = "KC144.P30::1f40beaa81e8c0ba956ce835"
P31_ARCHIVE_SHA256 = (
    "77629d53ef00c970cf115d7cbf94d5e4c9b97928814a702ada8d3f883212d091"
)
P31_PARENT_ARCHIVE_SHA256 = (
    "f35650ad2de99ad625baa15afd539c12ffa71cbc2e2a7606f7ce44ae4d970231"
)
P31_ENTRY_ADDRESS = "KC144.V1::GID006::H06"
P31_MYCELIUM_NEXUS = "KC144.V1::GID003::H03"
P31_EVIDENCE_LEDGER = "KC144.V1::GID005::H05"
P31_ROUTE_LEDGER = "KC144.V1::GID141::M09"
P31_RETURN_ADDRESS = "KC144.V1::GID144::M12"

MAX_ARCHIVE_MEMBERS = 50_000
MAX_SELECTED_MEMBER_BYTES = 64 * 1024 * 1024
MAX_COMPRESSION_RATIO = 250


class P31AdapterError(ValueError):
    pass


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _safe_member_name(name: str) -> bool:
    path = PurePosixPath(name)
    return (
        bool(name)
        and not name.startswith("/")
        and not path.is_absolute()
        and ".." not in path.parts
        and "\\" not in name
    )


class ExactP31Archive:
    """Fail-closed adapter for the one immutable P31 runtime artifact."""

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser().resolve()
        if not self.path.is_file():
            raise FileNotFoundError(f"P31 runtime not found: {self.path}")
        self.archive_sha256 = _sha256_file(self.path)
        if self.archive_sha256 != P31_ARCHIVE_SHA256:
            raise P31AdapterError(
                f"P31_ARCHIVE_SHA256_MISMATCH:{self.archive_sha256}"
            )
        self._validate_container()
        self._validate_identity()

    @property
    def prefix(self) -> str:
        return P31_RELEASE_ID + "/"

    def _member(self, relative: str) -> str:
        return self.prefix + relative

    def _validate_container(self) -> None:
        with zipfile.ZipFile(self.path) as archive:
            members = archive.infolist()
            if len(members) > MAX_ARCHIVE_MEMBERS:
                raise P31AdapterError("P31_ARCHIVE_MEMBER_LIMIT")
            names: set[str] = set()
            for member in members:
                if not _safe_member_name(member.filename):
                    raise P31AdapterError("P31_ARCHIVE_UNSAFE_PATH")
                if member.filename in names:
                    raise P31AdapterError("P31_ARCHIVE_DUPLICATE_MEMBER")
                names.add(member.filename)
                mode = member.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise P31AdapterError("P31_ARCHIVE_SYMLINK")
                if (
                    member.file_size > 0
                    and member.compress_size == 0
                ):
                    raise P31AdapterError("P31_ARCHIVE_COMPRESSION_RATIO")
                if (
                    member.compress_size > 0
                    and member.file_size / member.compress_size
                    > MAX_COMPRESSION_RATIO
                ):
                    raise P31AdapterError("P31_ARCHIVE_COMPRESSION_RATIO")

    def read_bytes(self, relative: str) -> bytes:
        with zipfile.ZipFile(self.path) as archive:
            try:
                return archive.read(self._member(relative))
            except KeyError as exc:
                raise P31AdapterError(
                    f"P31_ARCHIVE_MEMBER_MISSING:{relative}"
                ) from exc

    def read_json(self, relative: str) -> Any:
        return json.loads(self.read_bytes(relative).decode("utf-8"))

    def iter_jsonl(self, relative: str) -> Iterator[dict[str, Any]]:
        with zipfile.ZipFile(self.path) as archive:
            try:
                raw = archive.open(self._member(relative), "r")
            except KeyError as exc:
                raise P31AdapterError(
                    f"P31_ARCHIVE_MEMBER_MISSING:{relative}"
                ) from exc
            with raw:
                with io.TextIOWrapper(raw, encoding="utf-8") as handle:
                    for line in handle:
                        if line.strip():
                            yield json.loads(line)

    def _validate_identity(self) -> None:
        receipt = self.read_json("BUILD_RECEIPT.json")
        state = self.read_json("state/compiled_live_cognition_state.json")
        ledger = self.read_json("reports/merge_ledger.json")
        expected = {
            "release_id": P31_RELEASE_ID,
            "result_id": P31_RESULT_ID,
            "parent_result_id": P31_PARENT_RESULT_ID,
            "parent_archive_sha256": "sha256:" + P31_PARENT_ARCHIVE_SHA256,
        }
        for key, value in expected.items():
            if receipt.get(key) != value:
                raise P31AdapterError(f"P31_{key.upper()}_MISMATCH")
        if state.get("result_id") != P31_RESULT_ID:
            raise P31AdapterError("P31_STATE_RESULT_ID_MISMATCH")
        if not ledger.get("all_required_packets_admitted"):
            raise P31AdapterError("P31_LANE_ADMISSION_INCOMPLETE")
        if ledger.get("quarantined_packets"):
            raise P31AdapterError("P31_QUARANTINED_PACKET_PRESENT")
        if receipt.get("truth_credit_assigned") != 0:
            raise P31AdapterError("P31_TRUTH_CREDIT_INFLATION")
        if receipt.get("real_user_outcomes_claimed") != 0:
            raise P31AdapterError("P31_REAL_OUTCOME_INFLATION")

    def status(self) -> dict[str, Any]:
        receipt = self.read_json("BUILD_RECEIPT.json")
        acceptance = self.read_json("reports/acceptance_matrix.json")
        state = self.read_json("state/compiled_live_cognition_state.json")
        body = {
            "schema": "KC144.P31.ExactRuntimeBinding.V1",
            "release_id": P31_RELEASE_ID,
            "result_id": P31_RESULT_ID,
            "parent_result_id": P31_PARENT_RESULT_ID,
            "archive_sha256": "sha256:" + self.archive_sha256,
            "acceptance_state": receipt["acceptance_state"],
            "measured_state": state["measured_state"],
            "closed_gates": acceptance["closed_gates"],
            "open_gates": acceptance["open_gates"],
            "truth_credit_assigned": 0,
            "real_user_outcomes_claimed": 0,
            "production_authority": "HOLD",
        }
        return {
            **body,
            "binding_digest": content_address("kc144.p31.binding", body),
        }

    def _extract_selected(self, root: Path) -> Path:
        selected_prefixes = (
            self._member("src/kc144_omega34/"),
            self._member("src/kc144_p31_root/"),
        )
        selected_files = {
            self._member("data/parent_expanded_navigation_graph.json")
        }
        total = 0
        with zipfile.ZipFile(self.path) as archive:
            for member in archive.infolist():
                if (
                    member.filename not in selected_files
                    and not member.filename.startswith(selected_prefixes)
                ):
                    continue
                if member.is_dir():
                    continue
                total += member.file_size
                if total > MAX_SELECTED_MEMBER_BYTES:
                    raise P31AdapterError("P31_SELECTED_MEMBER_LIMIT")
                destination = root.joinpath(*PurePosixPath(member.filename).parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.read(member))
        return root / P31_RELEASE_ID

    @contextmanager
    def runtime(self) -> Iterator[dict[str, Any]]:
        # Reject preloaded modules so host-controlled module-cache state cannot
        # substitute code for the exact archive.
        hostile = [
            name
            for name in sys.modules
            if name == "kc144_omega34"
            or name.startswith("kc144_omega34.")
            or name == "kc144_p31_root"
            or name.startswith("kc144_p31_root.")
        ]
        if hostile:
            raise P31AdapterError("P31_MODULE_CACHE_NOT_CLEAN")
        with tempfile.TemporaryDirectory(prefix="kc144-p31-adapter-") as temporary:
            release_root = self._extract_selected(Path(temporary))
            source = release_root / "src"
            sys.path.insert(0, str(source))
            try:
                from kc144_omega34 import (
                    QueryCompiler,
                    ReplayEngine,
                    RouteEngine,
                    UtilityPolicy,
                    counterfactual_compare,
                    load_graph,
                )
                from kc144_p31_root import compile_next_wave

                graph = load_graph(
                    release_root
                    / "data"
                    / "parent_expanded_navigation_graph.json"
                )
                yield {
                    "graph": graph,
                    "compiler": QueryCompiler(graph),
                    "engine": RouteEngine(graph),
                    "ReplayEngine": ReplayEngine,
                    "UtilityPolicy": UtilityPolicy,
                    "counterfactual_compare": counterfactual_compare,
                    "compile_next_wave": compile_next_wave,
                }
            finally:
                if sys.path and sys.path[0] == str(source):
                    sys.path.pop(0)
                for name in list(sys.modules):
                    if (
                        name == "kc144_omega34"
                        or name.startswith("kc144_omega34.")
                        or name == "kc144_p31_root"
                        or name.startswith("kc144_p31_root.")
                    ):
                        sys.modules.pop(name, None)


def _query_summary(query_ir: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "query_id": query_ir["query_id"],
        "question": query_ir["question"],
        "candidate_coordinates": query_ir["candidate_coordinates"],
        "required_invariants": query_ir["required_invariants"],
        "source_permissions": query_ir["source_permissions"],
        "surface_orders": query_ir["surface_orders"],
        "return_requirement": query_ir["return_requirement"],
        "unresolved_terms": query_ir["unresolved_terms"],
        "graph_digest": query_ir["graph_digest"],
        "truth_credit": 0,
    }


def _route_summary(route: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": route["status"],
        "route_id": route.get("route_id"),
        "effect_id": route.get("effect_id"),
        "policy": route.get("policy"),
        "surface_order": route.get("surface_order"),
        "node_ids": route.get("node_ids", []),
        "edge_ids": route.get("edge_ids", []),
        "operator_product": route.get("operator_product"),
        "defect_total": route.get("defect_total"),
        "activated_surfaces": route.get("activated_surfaces", []),
        "source_witnesses": route.get("source_witnesses", []),
        "activated_bands": route.get("activated_bands", []),
        "return_complete": route.get("return_complete", False),
        "suspension": route.get("suspension"),
        "truth_credit": 0,
    }


def navigate_exact_p31(
    query: str,
    *,
    archive_path: str | Path,
    policy: str = "minimum_defect",
    hop_budget: int | None = None,
) -> dict[str, Any]:
    question = query.strip()
    if not question:
        raise P31AdapterError("P31_QUERY_REQUIRED")
    archive = ExactP31Archive(archive_path)
    options: dict[str, Any] = {}
    if hop_budget is not None:
        options["hop_budget"] = int(hop_budget)
    with archive.runtime() as runtime:
        query_ir = runtime["compiler"].compile(question, **options)
        route = runtime["engine"].plan_query(query_ir, policy=policy)
        comparison = runtime["counterfactual_compare"](
            query_ir,
            runtime["engine"],
        )
        comparison_routes = comparison.pop("routes")
        replay_engine = runtime["ReplayEngine"]()
        capsule = replay_engine.freeze(
            query_ir,
            route,
            utility_policy_version=runtime["UtilityPolicy"].VERSION,
        )
        replay = replay_engine.replay(
            capsule,
            runtime["graph"],
            runtime["engine"],
        )
        acceptance = archive.read_json("reports/acceptance_matrix.json")
        failed_gates = sorted(
            gate
            for gate, state in acceptance["open_gates"].items()
            if not state["pass"]
        )
        frontier = {
            "changed_sources": [],
            "underexplored_gids": [
                f"GID{int(row['gid']):03d}"
                for row in query_ir["candidate_coordinates"]
                if row["binding_status"] != "EXACT_DECLARED"
            ],
            "unresolved_mappings": query_ir["unresolved_terms"],
            "failed_gates": failed_gates,
            "real_outcome_observations": 0,
        }
        wave = runtime["compile_next_wave"](frontier)
    receipt_body = {
        "schema": "KC144.P31.AdapterReceipt.V1",
        "release_id": P31_RELEASE_ID,
        "result_id": P31_RESULT_ID,
        "archive_sha256": "sha256:" + archive.archive_sha256,
        "tool_uri": "tool://kc144/live.navigate",
        "entry_address": P31_ENTRY_ADDRESS,
        "mycelium_nexus": P31_MYCELIUM_NEXUS,
        "evidence_ledger": P31_EVIDENCE_LEDGER,
        "route_ledger": P31_ROUTE_LEDGER,
        "return_address": P31_RETURN_ADDRESS,
        "query_id": query_ir["query_id"],
        "route_id": route.get("route_id"),
        "effect_id": route.get("effect_id"),
        "replay_id": capsule["replay_id"],
        "replay_status": replay["status"],
        "truth_credit_assigned": 0,
        "independent_witness_count": 0,
        "real_user_outcomes_claimed": 0,
        "authority_effect": "NONE",
        "production_authority": "HOLD",
    }
    receipt = {
        **receipt_body,
        "receipt_digest": content_address("kc144.p31.adapter-receipt", receipt_body),
        "verified": replay["status"] == "REPLAY_STABLE",
    }
    body = {
        "schema": "KC144.P31.ExactAdapterNavigate.V1",
        "binding": archive.status(),
        "query": _query_summary(query_ir),
        "surface_route": _route_summary(route),
        "counterfactual": {
            **comparison,
            "routes": [_route_summary(item) for item in comparison_routes],
        },
        "replay": {
            "replay_id": capsule["replay_id"],
            "status": replay["status"],
            "source_versions": capsule["source_versions"],
        },
        "next_wave": {
            "parent_result_id": P31_RESULT_ID,
            "structural_graph_parent_result_id": P31_PARENT_RESULT_ID,
            "compiled_wave": wave,
        },
        "receipt": receipt,
        "boundary": {
            "connector_access": "NONE",
            "private_reasoning": "NOT_COLLECTED",
            "real_feedback_events": 0,
            "truth_credit_assigned": 0,
            "independent_witness_count": 0,
            "production_authority": "HOLD",
        },
    }
    return {
        **body,
        "envelope_digest": content_address("kc144.p31.adapter-envelope", body),
    }
