"""Module 3b: Screener Fondamental — Crypto (DeFiLlama)."""

from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select, desc

from ...core.config import get_settings
from ...core.http_client import http_get
from ...core.logging import get_logger
from ...models.screener import CryptoFundamentals

logger = get_logger("crypto_screener")

DEFILLAMA_BASE = "https://api.llama.fi"


async def fetch_all_protocols() -> list[dict]:
    """Fetch tous les protocoles DeFi depuis DeFiLlama."""
    settings = get_settings()
    try:
        response = await http_get(
            f"{DEFILLAMA_BASE}/protocols",
            source="defillama",
            rate_limit=settings.defillama_rate_limit,
        )
        protocols = response.json()
        logger.info("defillama_protocols_fetched", count=len(protocols))
        return protocols
    except Exception as e:
        logger.error("defillama_fetch_error", error=str(e))
        return []


async def fetch_fees_revenue(slug: str) -> dict | None:
    """Fetch fees et revenue d'un protocole via DeFiLlama."""
    settings = get_settings()
    try:
        response = await http_get(
            f"{DEFILLAMA_BASE}/summary/fees/{slug}",
            source="defillama",
            rate_limit=settings.defillama_rate_limit,
        )
        data = response.json()
        # Check if valid response (some return error objects)
        if "total24h" in data or "totalRevenue24h" in data:
            return data
        return None
    except Exception:
        # Not all protocols have fee data — this is expected
        return None


async def sync_crypto_fundamentals(db: AsyncSession, top_n: int = 100):
    """Synchronise les top N protocoles DeFi par TVL."""
    protocols = await fetch_all_protocols()
    if not protocols:
        return 0

    # Sort by TVL descending, take top N
    protocols.sort(key=lambda p: p.get("tvl", 0) or 0, reverse=True)
    top_protocols = protocols[:top_n]

    total_upserted = 0
    today = date.today()
    today_str = today.isoformat()

    for proto in top_protocols:
        slug = proto.get("slug", "")
        tvl = proto.get("tvl", 0) or 0
        mcap = proto.get("mcap", 0) or 0
        fdv = proto.get("fdv", 0) or 0
        chain = proto.get("chain", "Multi")
        category = proto.get("category", "")

        tvl_1d = proto.get("change_1d", 0) or 0
        tvl_7d = proto.get("change_7d", 0) or 0

        mcap_fdv = round(mcap / fdv, 4) if fdv and fdv > 0 else None

        # Fetch fees — skip silently on error (many protocols don't have fee data)
        fees_data = await fetch_fees_revenue(slug)
        fees_24h = fees_data.get("total24h") if fees_data else None
        fees_7d = fees_data.get("total7d") if fees_data else None
        revenue_24h = fees_data.get("totalRevenue24h") if fees_data else None

        record_id = f"{slug}_{today_str}"
        record = {
            "id": record_id,
            "protocol": slug,
            "date": today,  # Use date object, not string
            "tvl": tvl,
            "tvl_change_1d": tvl_1d,
            "tvl_change_7d": tvl_7d,
            "mcap": mcap,
            "fdv": fdv,
            "mcap_fdv_ratio": mcap_fdv,
            "fees_24h": fees_24h,
            "fees_7d": fees_7d,
            "revenue_24h": revenue_24h,
            "chain": chain,
            "category": category,
        }

        stmt = insert(CryptoFundamentals).values(**record).on_conflict_do_update(
            index_elements=["id"],
            set_=record,
        )
        await db.execute(stmt)
        total_upserted += 1

    await db.commit()
    logger.info("crypto_sync_complete", total_upserted=total_upserted)
    return total_upserted


async def detect_tvl_spike(db: AsyncSession, threshold_pct: float = 20.0) -> list[dict]:
    """Détecte les protocoles avec un spike anormal de TVL (>threshold %)."""
    today = date.today()
    result = await db.execute(
        select(CryptoFundamentals)
        .where(CryptoFundamentals.date == today)
        .where(CryptoFundamentals.tvl_change_1d > threshold_pct)
        .order_by(desc(CryptoFundamentals.tvl_change_1d))
    )
    spikes = result.scalars().all()
    return [
        {
            "protocol": s.protocol,
            "tvl": s.tvl,
            "tvl_change_1d": s.tvl_change_1d,
            "mcap": s.mcap,
            "fdv": s.fdv,
            "mcap_fdv_ratio": s.mcap_fdv_ratio,
            "fees_24h": s.fees_24h,
        }
        for s in spikes
    ]
