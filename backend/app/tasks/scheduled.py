"""Celery scheduled tasks — wraps async module functions."""

import asyncio
from .celery_app import celery_app
from ..core.database import create_session_factory
from ..core.logging import get_logger
from ..modules.screener.stocks import sync_all_stock_fundamentals

logger = get_logger("tasks")


def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.scheduled.task_sync_macro", bind=True, max_retries=3)
def task_sync_macro(self):
    async def _run():
        from ..modules.macro.fetcher import sync_macro_data
        engine, factory = create_session_factory()
        async with factory() as db:
            try:
                count = await sync_macro_data(db)
                logger.info("task_sync_macro_complete", records=count)
                return count
            finally:
                await engine.dispose()
    try:
        return run_async(_run())
    except Exception as e:
        logger.error("task_sync_macro_failed", error=str(e))
        self.retry(countdown=60 * (self.request.retries + 1))


@celery_app.task(name="app.tasks.scheduled.task_sync_sectors", bind=True, max_retries=3)
def task_sync_sectors(self):
    async def _run():
        from ..modules.sector.fetcher import sync_sector_data
        engine, factory = create_session_factory()
        async with factory() as db:
            try:
                count = await sync_sector_data(db)
                logger.info("task_sync_sectors_complete", records=count)
                return count
            finally:
                await engine.dispose()
    try:
        return run_async(_run())
    except Exception as e:
        logger.error("task_sync_sectors_failed", error=str(e))
        self.retry(countdown=60 * (self.request.retries + 1))


@celery_app.task(name="app.tasks.scheduled.task_sync_crypto", bind=True, max_retries=3)
def task_sync_crypto(self):
    async def _run():
        from ..modules.screener.crypto import sync_crypto_fundamentals
        engine, factory = create_session_factory()
        async with factory() as db:
            try:
                count = await sync_crypto_fundamentals(db, top_n=100)
                logger.info("task_sync_crypto_complete", records=count)
                return count
            finally:
                await engine.dispose()
    try:
        return run_async(_run())
    except Exception as e:
        logger.error("task_sync_crypto_failed", error=str(e))
        self.retry(countdown=120 * (self.request.retries + 1))


@celery_app.task(name="app.tasks.scheduled.task_sync_stocks", bind=True, max_retries=3)
def task_sync_stocks(self):
    async def _run():
        engine, factory = create_session_factory()
        async with factory() as db:
            try:
                count = await sync_all_stock_fundamentals(db)
                logger.info("task_sync_stocks_complete", records=count)
                return count
            finally:
                await engine.dispose()
    try:
        return run_async(_run())
    except Exception as e:
        logger.error("task_sync_stocks_failed", error=str(e))
        self.retry(countdown=60 * (self.request.retries + 1))


@celery_app.task(name="app.tasks.scheduled.task_scan_insiders", bind=True, max_retries=3)
def task_scan_insiders(self, days_back: int = 1):
    async def _run():
        from ..modules.insider.fetcher import sync_insider_transactions
        engine, factory = create_session_factory()
        async with factory() as db:
            try:
                txns = await sync_insider_transactions(db, days_back=days_back)
                logger.info("task_scan_insiders_complete", new_transactions=len(txns))
                return len(txns)
            finally:
                await engine.dispose()
    try:
        return run_async(_run())
    except Exception as e:
        logger.error("task_scan_insiders_failed", error=str(e))
        self.retry(countdown=60 * (self.request.retries + 1))


@celery_app.task(name="app.tasks.scheduled.task_process_equity_alerts", bind=True, max_retries=2)
def task_process_equity_alerts(self):
    async def _run():
        from ..services.alert_engine import process_equity_alerts
        engine, factory = create_session_factory()
        async with factory() as db:
            try:
                count = await process_equity_alerts(db)
                logger.info("task_equity_alerts_complete", alerts_sent=count)
                return count
            finally:
                await engine.dispose()
    try:
        return run_async(_run())
    except Exception as e:
        logger.error("task_equity_alerts_failed", error=str(e))
        self.retry(countdown=120)


@celery_app.task(name="app.tasks.scheduled.task_process_crypto_alerts", bind=True, max_retries=2)
def task_process_crypto_alerts(self):
    async def _run():
        from ..services.alert_engine import process_crypto_alerts
        engine, factory = create_session_factory()
        async with factory() as db:
            try:
                count = await process_crypto_alerts(db)
                logger.info("task_crypto_alerts_complete", alerts_sent=count)
                return count
            finally:
                await engine.dispose()
    try:
        return run_async(_run())
    except Exception as e:
        logger.error("task_crypto_alerts_failed", error=str(e))
        self.retry(countdown=120)
