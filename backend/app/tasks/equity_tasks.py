from celery import shared_task
from app.modules.equities_screener import sync_equities_screener
import asyncio

@shared_task(name="sync_equities_screener")
def celery_sync_equities():
    """
    Task Celery : sync equity screener
    Exécution quotidienne à 3h du matin
    """
    try:
        # Créer un nouveau event loop pour cette tâche synchrone
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(sync_equities_screener())
            return {"scraped_count": result}
        finally:
            loop.close()
    except Exception as e:
        print(f"Error in celery_sync_equities: {e}")
        return {"error": str(e)}
