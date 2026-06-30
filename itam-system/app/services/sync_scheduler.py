import asyncio
import logging

from app.core.database import SessionLocal
from app.services.identity_service import IdentityService


logger = logging.getLogger(__name__)


async def daily_ldap_sync_loop(interval_seconds: int = 24 * 60 * 60) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        db = SessionLocal()
        try:
            created, updated, offboarded = IdentityService.sync_enabled_ldap_providers(db)
            if created or updated or offboarded:
                logger.info("Daily LDAP sync finished: created=%s updated=%s offboarded=%s", created, updated, offboarded)
        except Exception:
            logger.exception("Daily LDAP sync failed")
        finally:
            db.close()


def start_daily_ldap_sync() -> asyncio.Task:
    return asyncio.create_task(daily_ldap_sync_loop())
