from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class HealthRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def ping_database(self) -> bool:
        if self.session is None:
            return False

        result = await self.session.execute(text("SELECT 1 AS ok"))
        row = result.mappings().first()

        return row is not None and row.get("ok") == 1
