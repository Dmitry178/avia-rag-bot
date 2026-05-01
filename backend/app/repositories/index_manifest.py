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

    async def insert(self, manifest: IndexManifest) -> IndexManifest:
        """
        Persist a new manifest row.
        """

        self.session.add(manifest)
        await self.session.flush()
        await self.session.refresh(manifest)
        
        return manifest

    async def get_latest(self) -> IndexManifest | None:
        """
        Return the most recently built manifest.
        """

        statement = select(IndexManifest).order_by(IndexManifest.built_at.desc()).limit(1)
        result = await self.session.execute(statement)
        
        return result.scalar_one_or_none()
