from __future__ import annotations

from abc import ABC, abstractmethod
import hashlib
from pathlib import Path
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

from .model import CarrierKind, Coordinate, ProjectionStatus, RoundTripDefect

HEX_COMMIT = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
DOC_ID = re.compile(r"/document/d/([A-Za-z0-9_-]+)")


class CarrierAdapter(ABC):
    carrier: CarrierKind

    @abstractmethod
    def compile(self, raw: dict[str, Any]) -> tuple[Coordinate, ProjectionStatus]:
        raise NotImplementedError

    def return_coordinate(
        self, coordinate: Coordinate
    ) -> tuple[tuple[Coordinate, ...], RoundTripDefect]:
        returned = (coordinate,)
        return returned, RoundTripDefect.compare(coordinate, returned)


class ConversationAdapter(CarrierAdapter):
    carrier = CarrierKind.CONVERSATION

    def compile(self, raw: dict[str, Any]) -> tuple[Coordinate, ProjectionStatus]:
        conversation_id = str(raw.get("conversation_id", "")).strip()
        turn_id = str(raw.get("turn_id", "")).strip() or None
        if not conversation_id:
            raise ValueError("conversation_id is required")
        status = ProjectionStatus.EXACT if turn_id else ProjectionStatus.PARTIAL
        return (
            Coordinate(
                carrier=self.carrier,
                namespace="chatgpt",
                object_id=conversation_id,
                revision=turn_id,
                fragment=raw.get("fragment"),
                digest=raw.get("digest"),
                epoch=raw.get("epoch"),
            ),
            status,
        )


class GoogleDocAdapter(CarrierAdapter):
    carrier = CarrierKind.GOOGLE_DOC

    def compile(self, raw: dict[str, Any]) -> tuple[Coordinate, ProjectionStatus]:
        document_id = str(raw.get("document_id", "")).strip()
        url = str(raw.get("url", "")).strip()
        if not document_id and url:
            match = DOC_ID.search(url)
            if match:
                document_id = match.group(1)
        if not document_id:
            raise ValueError("document_id or canonical Google Docs URL is required")
        revision = str(raw.get("revision_id", "")).strip() or None
        fragment = raw.get("fragment")
        if fragment is None and url:
            parsed = urlparse(url)
            query = parse_qs(parsed.query)
            fragment = parsed.fragment or query.get("heading", [None])[0]
        status = ProjectionStatus.EXACT if revision else ProjectionStatus.PARTIAL
        return (
            Coordinate(
                carrier=self.carrier,
                namespace="docs.google.com",
                object_id=document_id,
                revision=revision,
                fragment=fragment,
                digest=raw.get("digest"),
                epoch=raw.get("epoch"),
            ),
            status,
        )


class LocalFileAdapter(CarrierAdapter):
    carrier = CarrierKind.LOCAL_FILE

    def compile(self, raw: dict[str, Any]) -> tuple[Coordinate, ProjectionStatus]:
        path = Path(str(raw.get("path", ""))).resolve()
        if not path.is_file():
            raise ValueError(f"local file does not exist: {path}")
        root = Path(str(raw.get("root", path.parent))).resolve()
        try:
            object_id = path.relative_to(root).as_posix()
        except ValueError as exc:
            raise ValueError("local file must be contained by its declared root") from exc
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return (
            Coordinate(
                carrier=self.carrier,
                namespace=root.as_posix(),
                object_id=object_id,
                revision=digest,
                fragment=raw.get("fragment"),
                digest=digest,
                epoch=raw.get("epoch"),
            ),
            ProjectionStatus.EXACT,
        )

    def return_coordinate(
        self, coordinate: Coordinate
    ) -> tuple[tuple[Coordinate, ...], RoundTripDefect]:
        path = Path(coordinate.namespace, coordinate.object_id)
        if not path.is_file():
            return (), RoundTripDefect.compare(coordinate, ())
        current, _ = self.compile(
            {
                "path": path,
                "root": coordinate.namespace,
                "fragment": coordinate.fragment,
                "epoch": coordinate.epoch,
            }
        )
        returned = (current,)
        return returned, RoundTripDefect.compare(coordinate, returned)


class GitRepositoryAdapter(CarrierAdapter):
    carrier = CarrierKind.GIT_REPOSITORY

    def compile(self, raw: dict[str, Any]) -> tuple[Coordinate, ProjectionStatus]:
        owner = str(raw.get("owner", "")).strip()
        repository = str(raw.get("repository", "")).strip()
        commit = str(raw.get("commit_sha", "")).strip().lower()
        path = str(raw.get("path", "")).strip().lstrip("/")
        blob_sha = str(raw.get("blob_sha", "")).strip().lower() or None
        if not owner or not repository or not path:
            raise ValueError("owner, repository, and path are required")
        if not HEX_COMMIT.fullmatch(commit):
            raise ValueError("Git coordinates require an immutable 40- or 64-hex commit")
        if blob_sha is not None and not HEX_COMMIT.fullmatch(blob_sha):
            raise ValueError("blob_sha must be 40 or 64 lowercase hex characters")
        return (
            Coordinate(
                carrier=self.carrier,
                namespace=f"github.com/{owner}/{repository}",
                object_id=path,
                revision=commit,
                fragment=raw.get("fragment"),
                digest=raw.get("content_sha256"),
                epoch=raw.get("epoch"),
                metadata=(("blob_sha", blob_sha),) if blob_sha else (),
            ),
            ProjectionStatus.EXACT,
        )


class AdapterCompiler:
    def __init__(self) -> None:
        adapters: tuple[CarrierAdapter, ...] = (
            ConversationAdapter(),
            GoogleDocAdapter(),
            LocalFileAdapter(),
            GitRepositoryAdapter(),
        )
        self._adapters = {adapter.carrier: adapter for adapter in adapters}

    def compile(
        self, carrier: CarrierKind | str, raw: dict[str, Any]
    ) -> tuple[Coordinate, ProjectionStatus]:
        kind = CarrierKind(carrier)
        return self._adapters[kind].compile(raw)

    def return_coordinate(
        self, coordinate: Coordinate
    ) -> tuple[tuple[Coordinate, ...], RoundTripDefect]:
        return self._adapters[coordinate.carrier].return_coordinate(coordinate)
