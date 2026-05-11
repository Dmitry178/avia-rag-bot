"""Ingest diff planning for incremental ETL."""

from dataclasses import dataclass

from app.models.chunk_meta import ChunkMeta
from etl.types import ChunkDraft


@dataclass(frozen=True)
class IngestDiffStats:
    """
    Counts of chunk changes detected during ingest planning.
    """

    added: int
    updated: int
    unchanged: int
    removed: int


@dataclass(frozen=True)
class IngestPlan:
    """
    Embedding plan for a single ingest run.
    """

    embed_indices: list[int]
    reused_vectors: dict[int, list[float]]
    stats: IngestDiffStats


def plan_ingest(
    drafts: list[ChunkDraft],
    existing_chunks: list[ChunkMeta],
    existing_vectors: list[list[float]],
    checkpoint_vectors: dict[str, list[float]],
    *,
    rebuild: bool,
    can_reuse_existing: bool,
) -> IngestPlan:
    """
    Decide which draft indices need new embeddings and which vectors can be reused.

    Reuse order: checkpoint by content_hash, then existing DB+FAISS by node_id+content_hash.
    """

    existing_by_node: dict[str, ChunkMeta] = {chunk.node_id: chunk for chunk in existing_chunks}
    new_node_ids = {draft.node_id for draft in drafts}

    added = updated = unchanged = 0
    embed_indices: list[int] = []
    reused_vectors: dict[int, list[float]] = {}

    for index, draft in enumerate(drafts):
        existing = existing_by_node.get(draft.node_id)

        if existing is None:
            added += 1
        elif existing.content_hash == draft.content_hash:
            unchanged += 1
        else:
            updated += 1

        if draft.content_hash in checkpoint_vectors:
            reused_vectors[index] = checkpoint_vectors[draft.content_hash]
            continue

        if rebuild or not can_reuse_existing:
            embed_indices.append(index)
            continue

        if (
            existing is not None
            and existing.content_hash == draft.content_hash
            and existing.id is not None
            and existing.id < len(existing_vectors)
        ):
            reused_vectors[index] = existing_vectors[existing.id]
            continue

        if index not in embed_indices:
            embed_indices.append(index)

    removed = sum(1 for chunk in existing_chunks if chunk.node_id not in new_node_ids)

    return IngestPlan(
        embed_indices=embed_indices,
        reused_vectors=reused_vectors,
        stats=IngestDiffStats(
            added=added,
            updated=updated,
            unchanged=unchanged,
            removed=removed,
        ),
    )
