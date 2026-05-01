from app.core.db_manager import DBManager
from app.core.logs import logger


class HealthService:
    """
    Health probe service.
    """

    def __init__(self, db: DBManager) -> None:
        self.db = db

    async def is_ready(self) -> bool:
        """
        Check whether the database is reachable.

        Returns False on any failure instead of raising — readiness probes must not
        propagate DB exceptions to the API error handler.
        """

        try:
            return await self.db.health.ping_database()

        except Exception as exc:  # noqa: BLE001
            logger.warning("readiness_check_failed", error=str(exc))
            return False
