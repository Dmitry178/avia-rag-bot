"""Chunk metadata persistence."""

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.chunk_meta import ChunkMeta


class ChunkRepository:
    """
    CRUD operations for chunk metadata.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def delete_all(self) -> None:
        """
        Remove all chunk rows (full index rebuild for all languages).
        """

        await self.session.execute(delete(ChunkMeta))

    async def delete_for_language(self, language_code: str) -> None:
        """
        Remove all chunk rows for a single language.
        """

        await self.session.execute(delete(ChunkMeta).where(ChunkMeta.language_code == language_code))

    async def insert_many(self, chunks: list[ChunkMeta]) -> None:
        """
        Insert chunk rows preserving explicit primary keys.
        """

        for chunk in chunks:
            self.session.add(chunk)

        await self.session.flush()

    async def list_all_ordered(self, language_code: str) -> list[ChunkMeta]:
        """
        Return chunks for a language ordered by FAISS row id.
        """

        statement = (
            select(ChunkMeta)
            .where(ChunkMeta.language_code == language_code)
            .order_by(ChunkMeta.id)
        )
        result = await self.session.execute(statement)

        return list(result.scalars().all())

    async def replace_for_language(self, language_code: str, chunks: list[ChunkMeta]) -> None:
        """
        Replace the chunk set for one language (delete language rows, then insert).
        """

        await self.delete_for_language(language_code)
        await self.insert_many(chunks)

    async def replace_all(self, chunks: list[ChunkMeta]) -> None:
        """
        Replace the full chunk set (delete all, then insert).
        """

        await self.delete_all()
        await self.insert_many(chunks)

    async def list_by_ids(self, language_code: str, chunk_ids: list[int]) -> list[ChunkMeta]:
        """
        Return chunks for the given ids within a language (unordered).
        """

        if not chunk_ids:
            return []

        statement = select(ChunkMeta).where(
            ChunkMeta.language_code == language_code,
            ChunkMeta.id.in_(chunk_ids),
        )
        result = await self.session.execute(statement)

        return list(result.scalars().all())

    async def count_by_content_type(self, language_code: str | None = None) -> dict[str, int]:
        """
        Return chunk counts grouped by content_type, optionally scoped to one language.
        """

        statement = select(ChunkMeta.content_type, func.count())

        if language_code is not None:
            statement = statement.where(ChunkMeta.language_code == language_code)

        statement = statement.group_by(ChunkMeta.content_type)
        result = await self.session.execute(statement)

        return {content_type: count for content_type, count in result.all()}

    async def total_count(self, language_code: str | None = None) -> int:
        """
        Return total number of stored chunks, optionally scoped to one language.
        """

        statement = select(func.count()).select_from(ChunkMeta)

        if language_code is not None:
            statement = statement.where(ChunkMeta.language_code == language_code)

        result = await self.session.execute(statement)

        return int(result.scalar_one())
