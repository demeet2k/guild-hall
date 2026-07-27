from __future__ import annotations

from typing import Any, Iterable

from memory_crystal.p03.model import canonical_digest

from .model import (
    ContextAtom,
    FrameworkAddress,
    LifecycleState,
    OriginClass,
    SourceRef,
    TruthState,
)


class PersonalContextAdapter:
    """Compile connector retrieval hits without impersonating native turn identity.

    When a hit exposes immutable thread and turn IDs, those coordinates are used.
    Otherwise identity is scoped to the retrieval receipt and result index, and
    the atom remains RESID/RETRIEVED_FRAGMENT.
    """

    def compile_hits(
        self,
        *,
        query_receipt_id: str,
        hits: Iterable[dict[str, Any]],
        address: FrameworkAddress,
        evidence_root: str | None = None,
    ) -> tuple[ContextAtom, ...]:
        if not query_receipt_id:
            raise ValueError("query_receipt_id is required")
        atoms: list[ContextAtom] = []
        for index, hit in enumerate(hits):
            text = str(hit.get("content", "")).strip()
            if not text:
                continue
            thread_id = str(hit.get("thread_id", "")).strip() or None
            turn_id = str(hit.get("turn_id", "")).strip() or None
            native_exact = bool(thread_id and turn_id)
            result_digest = canonical_digest(
                {
                    "query_receipt_id": query_receipt_id,
                    "index": index,
                    "content": text,
                }
            )
            source = SourceRef(
                carrier="conversation" if native_exact else "conversation_retrieval",
                source_id=thread_id or f"{query_receipt_id}:result:{index}",
                revision=turn_id or result_digest,
                locator=(
                    f"conversation:{thread_id}:turn:{turn_id}"
                    if native_exact
                    else f"personal-context:{query_receipt_id}:{index}"
                ),
                authority=(
                    str(hit.get("authority", "")).strip()
                    or "secondary-experiential-history"
                ),
                evidence_root=(
                    str(hit.get("evidence_root", "")).strip()
                    or evidence_root
                    or f"retrieval-root:{query_receipt_id}:{index}"
                ),
                observed_at=hit.get("observed_at"),
            )
            tags = ["PERSONAL_CONTEXT", "NATIVE_TURN" if native_exact else "RETRIEVAL_SCOPED"]
            atoms.append(
                ContextAtom.build(
                    source=source,
                    address=address,
                    exact_text=text,
                    origin_class=OriginClass.INTERNAL_HISTORY,
                    truth=TruthState.RESID,
                    lifecycle=LifecycleState.RETRIEVED_FRAGMENT,
                    tags=tuple(tags),
                    witnesses=(f"query-receipt:{query_receipt_id}",),
                )
            )
        return tuple(atoms)
