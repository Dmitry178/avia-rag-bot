"""Chunk metadata persistence."""

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk_meta import ChunkMeta


class ChunkRepository:
    """
    CRUD operations for chunk metadata.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def delete_all(self) -> None:
        """
        Remove all chunk rows (full index rebuild).
        """

        await self.session.execute(delete(ChunkMeta))

    async def insert_many(self, chunks: list[ChunkMeta]) -> None:
        """
        Insert chunk rows preserving explicit primary keys.
        """

        for chunk in chunks:
            self.session.add(chunk)

        await self.session.flush()

    async def list_all_ordered(self) -> list[ChunkMeta]:
        """
        Return all chunks ordered by FAISS row id (primary key).
        """

        statement = select(ChunkMeta).order_by(ChunkMeta.id)
        result = await self.session.execute(statement)

        return list(result.scalars().all())

    async def replace_all(self, chunks: list[ChunkMeta]) -> None:
        """
        Replace the full chunk set (delete all, then insert).
        """

        await self.delete_all()
        await self.insert_many(chunks)

    async def list_by_ids(self, chunk_ids: list[int]) -> list[ChunkMeta]:
        """
        Return chunks for the given ids (unordered).
        """

        if not chunk_ids:
            return []

        statement = select(ChunkMeta).where(ChunkMeta.id.in_(chunk_ids))
        result = await self.session.execute(statement)

        return list(result.scalars().all())

    async def count_by_content_type(self) -> dict[str, int]:
        """
        Return chunk counts grouped by content_type.
        """

        statement = select(ChunkMeta.content_type, func.count()).group_by(ChunkMeta.content_type)
        result = await self.session.execute(statement)

        return {content_type: count for content_type, count in result.all()}

    async def total_count(self) -> int:
        """
        Return total number of stored chunks.
        """

        result = await self.session.execute(select(func.count()).select_from(ChunkMeta))
        return int(result.scalar_one())
