from celery import shared_task
from app.modules.equities_screener import sync_equities_screener

@shared_task(name="sync_equities_screener")
def celery_sync_equities():
    """
    Task Celery : sync equity screener
    Exécution quotidienne à 3h du matin
    """
    import asyncio
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(sync_equities_screener())
    return {"scraped_count": result}
