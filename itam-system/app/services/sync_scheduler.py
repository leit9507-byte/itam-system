import asyncio
import logging

from sqlalchemy import text

from app.core.database import SessionLocal
from app.services.identity_service import IdentityService


logger = logging.getLogger(__name__)
LDAP_SYNC_LOCK_NAME = "itam_daily_ldap_sync"


def acquire_scheduler_lock(db) -> bool:
    if not db.bind or db.bind.dialect.name not in {"mysql", "mariadb"}:
        return True
    return bool(db.execute(text("SELECT GET_LOCK(:name, 0)"), {"name": LDAP_SYNC_LOCK_NAME}).scalar())


def release_scheduler_lock(db) -> None:
    if db.bind and db.bind.dialect.name in {"mysql", "mariadb"}:
        db.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": LDAP_SYNC_LOCK_NAME})


async def daily_ldap_sync_loop(interval_seconds: int = 24 * 60 * 60) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        db = SessionLocal()
        locked = False
        try:
            locked = acquire_scheduler_lock(db)
            if not locked:
                logger.info("Daily LDAP sync skipped because another worker owns the lock")
                continue
            created, updated, offboarded = IdentityService.sync_enabled_ldap_providers(db)
            if created or updated or offboarded:
                logger.info("Daily LDAP sync finished: created=%s updated=%s offboarded=%s", created, updated, offboarded)
        except Exception:
            logger.exception("Daily LDAP sync failed")
        finally:
            if locked:
                release_scheduler_lock(db)
            db.close()


def start_daily_ldap_sync() -> asyncio.Task:
    return asyncio.create_task(daily_ldap_sync_loop())
