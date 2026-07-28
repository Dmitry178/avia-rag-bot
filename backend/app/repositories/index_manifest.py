"""Index manifest persistence."""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.index_manifest import IndexManifest


class IndexManifestRepository:
    """
    CRUD operations for index build manifests.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def delete_all(self) -> None:
        """
        Remove all manifest rows.
        """

        await self.session.execute(delete(IndexManifest))

    async def delete_for_language(self, language_code: str) -> None:
        """
        Remove manifest rows for a single language.
        """

        await self.session.execute(delete(IndexManifest).where(IndexManifest.language_code == language_code))

    async def insert(self, manifest: IndexManifest) -> IndexManifest:
        """
        Persist a new manifest row.
        """

        self.session.add(manifest)
        await self.session.flush()
        await self.session.refresh(manifest)

        return manifest

    async def get_latest(self, language_code: str) -> IndexManifest | None:
        """
        Return the most recently built manifest for a language.
        """

        statement = (
            select(IndexManifest)
            .where(IndexManifest.language_code == language_code)
            .order_by(IndexManifest.built_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)

        return result.scalar_one_or_none()
