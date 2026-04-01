"""Module 1: Macroéconomie — Extraction FRED API."""

from datetime import date, timedelta, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from ...core.config import get_settings
from ...core.http_client import http_get
from ...core.logging import get_logger
from ...models.macro import MacroSeries

logger = get_logger("macro_fetcher")

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

# Séries macroéconomiques à tracker
MACRO_SERIES = {
    "DFF": "Federal Funds Effective Rate",
    "WM2NS": "M2 Money Supply (Liquidité)",
    "T10Y2Y": "10Y-2Y Treasury Yield Spread (Inversion)",
}


def parse_date(date_str: str) -> date:
    """Convert 'YYYY-MM-DD' string to a proper date object."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()


async def fetch_fred_series(series_id: str, lookback_days: int = 365) -> list[dict]:
    """Fetch une série FRED."""
    settings = get_settings()
    if not settings.fred_api_key:
        logger.warning("fred_api_key_missing", series=series_id)
        return []

    start_date = (date.today() - timedelta(days=lookback_days)).isoformat()

    params = {
        "series_id": series_id,
        "api_key": settings.fred_api_key,
        "file_type": "json",
        "observation_start": start_date,
        "sort_order": "desc",
    }

    try:
        response = await http_get(
            FRED_BASE_URL,
            source="fred",
            rate_limit=settings.fred_rate_limit,
            params=params,
        )
        data = response.json()
        observations = data.get("observations", [])
        logger.info("fred_fetched", series=series_id, count=len(observations))
        return observations
    except Exception as e:
        logger.error("fred_fetch_error", series=series_id, error=str(e))
        return []


async def sync_macro_data(db: AsyncSession, lookback_days: int = 365):
    """Synchronise toutes les séries macro dans la DB."""
    total_upserted = 0

    for series_id, description in MACRO_SERIES.items():
        observations = await fetch_fred_series(series_id, lookback_days)

        for obs in observations:
            if obs.get("value") == ".":  # FRED uses "." for missing data
                continue

            obs_date = parse_date(obs["date"])  # Convert string to date object
            record_id = f"{series_id}_{obs['date']}"
            stmt = insert(MacroSeries).values(
                id=record_id,
                series_id=series_id,
                date=obs_date,
                value=float(obs["value"]),
            ).on_conflict_do_update(
                index_elements=["id"],
                set_={"value": float(obs["value"])},
            )
            await db.execute(stmt)
            total_upserted += 1

    await db.commit()
    logger.info("macro_sync_complete", total_upserted=total_upserted)
    return total_upserted
