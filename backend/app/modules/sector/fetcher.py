"""Module 2: Radar Sectoriel — ETF GICS + MM200 + Force Relative.

Uses Yahoo Finance v8 chart API directly (no yfinance library needed).
This avoids cookie/session issues that block yfinance in Docker containers.
"""

from datetime import date, timedelta, datetime
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from ...core.config import get_settings
from ...core.http_client import http_get
from ...core.logging import get_logger
from ...models.sector import SectorETF, SECTOR_ETFS

logger = get_logger("sector_fetcher")

SP500_PROXY = "SPY"

# Yahoo Finance v8 chart API — no auth needed, works from servers
YF_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart"


async def fetch_historical_prices(symbol: str, days: int = 300) -> list[dict]:
    """Fetch historical daily prices via Yahoo Finance chart API."""
    url = f"{YF_CHART_URL}/{symbol}"

    # Calculate period timestamps
    end_ts = int(datetime.now().timestamp())
    start_ts = int((datetime.now() - timedelta(days=days)).timestamp())

    params = {
        "period1": str(start_ts),
        "period2": str(end_ts),
        "interval": "1d",
        "includePrePost": "false",
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    try:
        response = await http_get(
            url,
            source="yahoo",
            rate_limit=0.5,  # Be gentle with Yahoo
            params=params,
            headers=headers,
        )
        data = response.json()

        chart = data.get("chart", {}).get("result", [])
        if not chart:
            logger.warning("yf_no_chart_data", symbol=symbol)
            return []

        result = chart[0]
        timestamps = result.get("timestamp", [])
        closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])

        if not timestamps or not closes:
            logger.warning("yf_empty_data", symbol=symbol)
            return []

        # Build records (most recent first)
        records = []
        for ts, close in zip(timestamps, closes):
            if close is None:
                continue
            dt = datetime.fromtimestamp(ts).date()
            records.append({"date": dt, "close": float(close)})

        records.reverse()  # Most recent first
        logger.info("yf_prices_fetched", symbol=symbol, count=len(records))
        return records

    except Exception as e:
        logger.error("yf_fetch_error", symbol=symbol, error=str(e))
        return []


def compute_sma(prices: list[float], window: int = 200) -> float | None:
    """Calcul Moyenne Mobile Simple."""
    if len(prices) < window:
        return None
    return float(np.mean(prices[:window]))


def compute_relative_strength(
    etf_prices: list[float], benchmark_prices: list[float], period: int = 30
) -> float | None:
    """Calcul Force Relative = (ETF return / Benchmark return) sur N jours."""
    if len(etf_prices) < period + 1 or len(benchmark_prices) < period + 1:
        return None

    etf_return = (etf_prices[0] / etf_prices[period]) - 1
    bench_return = (benchmark_prices[0] / benchmark_prices[period]) - 1

    if bench_return == 0:
        return 0.0

    return (1 + etf_return) / (1 + bench_return)


async def sync_sector_data(db: AsyncSession):
    """Synchronise données sectorielles avec calculs MM200 + RS."""

    # 1. Fetch S&P 500 benchmark
    sp500_prices_raw = await fetch_historical_prices(SP500_PROXY, days=300)
    if not sp500_prices_raw:
        logger.error("sp500_fetch_failed")
        return 0

    sp500_closes = [p["close"] for p in sp500_prices_raw]
    total_upserted = 0

    # 2. Fetch each sector ETF
    for symbol, sector_name in SECTOR_ETFS.items():
        etf_prices_raw = await fetch_historical_prices(symbol, days=300)
        if not etf_prices_raw:
            continue

        etf_closes = [p["close"] for p in etf_prices_raw]

        latest = etf_prices_raw[0]
        sma_200 = compute_sma(etf_closes, 200)
        rs_30 = compute_relative_strength(etf_closes, sp500_closes, 30)
        above_sma = latest["close"] > sma_200 if sma_200 else None

        latest_date = latest["date"]
        record_id = f"{symbol}_{latest_date.isoformat()}"
        stmt = insert(SectorETF).values(
            id=record_id,
            symbol=symbol,
            date=latest_date,
            close_price=latest["close"],
            sma_200=round(sma_200, 2) if sma_200 else None,
            relative_strength_30d=round(rs_30, 4) if rs_30 else None,
            above_sma200=above_sma,
            sector_name=sector_name,
        ).on_conflict_do_update(
            index_elements=["id"],
            set_={
                "close_price": latest["close"],
                "sma_200": round(sma_200, 2) if sma_200 else None,
                "relative_strength_30d": round(rs_30, 4) if rs_30 else None,
                "above_sma200": above_sma,
            },
        )
        await db.execute(stmt)
        total_upserted += 1

    await db.commit()
    logger.info("sector_sync_complete", total_upserted=total_upserted)
    return total_upserted
