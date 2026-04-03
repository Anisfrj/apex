"""FastAPI API routes — Dashboard data endpoints."""

from datetime import date, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, text

from ..core.database import get_db
from ..core.logging import get_logger
from ..models.macro import MacroSeries
from ..models.sector import SectorETF, SECTOR_ETFS
from ..models.screener import StockFundamentals, CryptoFundamentals
from ..models.insider import InsiderTransaction
from ..models.alerts import AlertLog
from app.services.ideas import (
    get_ideas_ranked,
    get_idea_detail,
    generate_ideas_from_signals
)
from ..services.ai_summary import generate_ai_summary

logger = get_logger("api")

router = APIRouter(prefix="/api", tags=["dashboard"])


# ═══════════════════════════════════════════════════
# HEALTH & STATUS
# ═══════════════════════════════════════════════════

@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "apex-screener"}


@router.get("/status")
async def system_status(db: AsyncSession = Depends(get_db)):
    """Vue globale de l'état du système."""
    macro_count = await db.execute(select(func.count(MacroSeries.id)))
    sector_count = await db.execute(select(func.count(SectorETF.id)))
    stock_count = await db.execute(select(func.count(StockFundamentals.id)))
    crypto_count = await db.execute(select(func.count(CryptoFundamentals.id)))
    insider_count = await db.execute(select(func.count(InsiderTransaction.id)))
    alert_count = await db.execute(select(func.count(AlertLog.id)))

    macro_latest = await db.execute(select(func.max(MacroSeries.created_at)))
    insider_latest = await db.execute(select(func.max(InsiderTransaction.created_at)))

    return {
        "modules": {
            "macro": {"records": macro_count.scalar(), "last_update": str(macro_latest.scalar())},
            "sectors": {"records": sector_count.scalar()},
            "stocks": {"records": stock_count.scalar()},
            "crypto": {"records": crypto_count.scalar()},
            "insiders": {"records": insider_count.scalar(), "last_update": str(insider_latest.scalar())},
        },
        "alerts_total": alert_count.scalar(),
    }


# ═══════════════════════════════════════════════════
# MODULE 1: MACROÉCONOMIE
# ═══════════════════════════════════════════════════

@router.get("/macro")
async def get_macro_data(
    series_id: str = Query(None, description="Filter by series (DFF, WM2NS, T10Y2Y)"),
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Données macroéconomiques FRED."""
    cutoff = date.today() - timedelta(days=days)
    query = select(MacroSeries).where(MacroSeries.date >= cutoff)
    if series_id:
        query = query.where(MacroSeries.series_id == series_id)
    query = query.order_by(MacroSeries.series_id, desc(MacroSeries.date))

    result = await db.execute(query)
    rows = result.scalars().all()
    return [
        {
            "series_id": r.series_id,
            "date": r.date.isoformat(),
            "value": r.value,
        }
        for r in rows
    ]


# ═══════════════════════════════════════════════════
# MODULE 2: RADAR SECTORIEL
# ═══════════════════════════════════════════════════

@router.get("/sectors")
async def get_sector_data(db: AsyncSession = Depends(get_db)):
    """Dernières données sectorielles avec MM200 et Force Relative."""
    results = []
    for symbol in SECTOR_ETFS:
        result = await db.execute(
            select(SectorETF)
            .where(SectorETF.symbol == symbol)
            .order_by(desc(SectorETF.date))
            .limit(1)
        )
        row = result.scalars().first()
        if row:
            results.append({
                "symbol": row.symbol,
                "sector_name": row.sector_name,
                "close_price": row.close_price,
                "sma_200": row.sma_200,
                "relative_strength_30d": row.relative_strength_30d,
                "above_sma200": row.above_sma200,
                "date": row.date.isoformat(),
            })

    results.sort(key=lambda x: x.get("relative_strength_30d") or 0, reverse=True)
    return results


# ═══════════════════════════════════════════════════
# MODULE 3a: SCREENER ACTIONS — STATIQUES (avant /{symbol})
# ═══════════════════════════════════════════════════

class StockScreenerItem(BaseModel):
    symbol: str
    company_name: Optional[str] = None
    sector: Optional[str] = None
    fiscal_date: str
    market_cap: Optional[float] = None
    price: Optional[float] = None
    pe_ttm: Optional[float] = None
    pb: Optional[float] = None
    roic: Optional[float] = None
    free_cash_flow: Optional[float] = None
    total_debt: Optional[float] = None
    total_equity: Optional[float] = None
    rev_cagr_3y: Optional[float] = None
    eps_cagr_3y: Optional[float] = None
    perf_6m: Optional[float] = None
    perf_12m: Optional[float] = None
    dividend_yield: Optional[float] = None
    payout_ratio: Optional[float] = None
    insider_net_buy_usd_6m: Optional[float] = None
    insider_buy_trades_6m: Optional[int] = None


class StockScreenerResponse(BaseModel):
    results: List[StockScreenerItem]
    count: int
    page: int
    page_size: int
    has_more: bool


# FIX #1: /stocks/screener déclaré AVANT /stocks/{symbol}
@router.get("/stocks/screener", response_model=StockScreenerResponse)
async def stocks_screener(
    sector: Optional[List[str]] = Query(default=None),
    min_market_cap: Optional[float] = Query(default=None),
    max_market_cap: Optional[float] = Query(default=None),
    max_pe: Optional[float] = Query(default=None),
    max_pb: Optional[float] = Query(default=None),
    min_roic: Optional[float] = Query(default=None),
    min_fcf: Optional[float] = Query(default=None),
    max_debt_to_equity: Optional[float] = Query(default=None),
    min_rev_cagr_3y: Optional[float] = Query(default=None),
    min_eps_cagr_3y: Optional[float] = Query(default=None),
    min_perf_12m: Optional[float] = Query(default=None),
    min_dividend_yield: Optional[float] = Query(default=None),
    max_payout_ratio: Optional[float] = Query(default=None),
    min_insider_net_buy_usd_6m: Optional[float] = Query(default=None),
    min_insider_buy_trades_6m: Optional[int] = Query(default=None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """
    Screener multi-facteurs: value, quality, growth, momentum, dividendes, insiders.
    Un enregistrement par action (dernier fiscal_date).
    """
    subq = (
        select(
            StockFundamentals.symbol,
            func.max(StockFundamentals.fiscal_date).label("max_date"),
        )
        .group_by(StockFundamentals.symbol)
        .subquery()
    )

    query = (
        select(StockFundamentals)
        .join(
            subq,
            (StockFundamentals.symbol == subq.c.symbol)
            & (StockFundamentals.fiscal_date == subq.c.max_date),
        )
    )

    if sector:
        query = query.where(StockFundamentals.sector.in_(sector))
    if min_market_cap is not None:
        query = query.where(StockFundamentals.market_cap >= min_market_cap)
    if max_market_cap is not None:
        query = query.where(StockFundamentals.market_cap <= max_market_cap)
    if max_pe is not None:
        query = query.where(StockFundamentals.pe_ttm <= max_pe)
    if max_pb is not None:
        query = query.where(StockFundamentals.pb <= max_pb)
    if min_roic is not None:
        query = query.where(StockFundamentals.roic >= min_roic)
    if min_fcf is not None:
        query = query.where(StockFundamentals.free_cash_flow >= min_fcf)
    if max_debt_to_equity is not None:
        query = query.where(
            (StockFundamentals.total_equity > 0)
            & (StockFundamentals.total_debt / StockFundamentals.total_equity <= max_debt_to_equity)
        )
    if min_rev_cagr_3y is not None:
        query = query.where(StockFundamentals.rev_cagr_3y >= min_rev_cagr_3y)
    if min_eps_cagr_3y is not None:
        query = query.where(StockFundamentals.eps_cagr_3y >= min_eps_cagr_3y)
    if min_perf_12m is not None:
        query = query.where(StockFundamentals.perf_12m >= min_perf_12m)
    if min_dividend_yield is not None:
        query = query.where(StockFundamentals.dividend_yield >= min_dividend_yield)
    if max_payout_ratio is not None:
        query = query.where(StockFundamentals.payout_ratio <= max_payout_ratio)
    if min_insider_net_buy_usd_6m is not None:
        query = query.where(StockFundamentals.insider_net_buy_usd_6m >= min_insider_net_buy_usd_6m)
    if min_insider_buy_trades_6m is not None:
        query = query.where(StockFundamentals.insider_buy_trades_6m >= min_insider_buy_trades_6m)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(desc(StockFundamentals.market_cap))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    rows = result.scalars().all()

    items: list[StockScreenerItem] = [
        StockScreenerItem(
            symbol=r.symbol,
            company_name=r.company_name,
            sector=r.sector,
            fiscal_date=r.fiscal_date.isoformat(),
            market_cap=r.market_cap,
            price=r.price,
            pe_ttm=r.pe_ttm,
            pb=r.pb,
            roic=r.roic,
            free_cash_flow=r.free_cash_flow,
            total_debt=r.total_debt,
            total_equity=r.total_equity,
            rev_cagr_3y=r.rev_cagr_3y,
            eps_cagr_3y=r.eps_cagr_3y,
            perf_6m=r.perf_6m,
            perf_12m=r.perf_12m,
            dividend_yield=r.dividend_yield,
            payout_ratio=r.payout_ratio,
            insider_net_buy_usd_6m=r.insider_net_buy_usd_6m,
            insider_buy_trades_6m=r.insider_buy_trades_6m,
        )
        for r in rows
    ]

    return StockScreenerResponse(
        results=items,
        count=total,
        page=page,
        page_size=page_size,
        has_more=page * page_size < total,
    )


# FIX #1: /stocks/{symbol}/ai-summary déclaré AVANT /stocks/{symbol}
@router.get("/stocks/{symbol}/ai-summary")
async def get_ai_summary(symbol: str, db: AsyncSession = Depends(get_db)):
    """Génère un résumé analyste IA pour un ticker via Groq LLM."""
    symbol = symbol.upper()

    result = await db.execute(
        select(StockFundamentals)
        .where(StockFundamentals.symbol == symbol)
        .order_by(StockFundamentals.fiscal_date.desc())
        .limit(1)
    )
    stock = result.scalar_one_or_none()

    summary = await generate_ai_summary(
        symbol=symbol,
        company_name=stock.company_name if stock else None,
        roic=stock.roic if stock else None,
        fcf=stock.free_cash_flow if stock else None,
        sector=stock.sector if stock else None,
    )
    return {"symbol": symbol, **summary}


# FIX #1: /stocks/{symbol} déclaré EN DERNIER parmi les routes /stocks/
@router.get("/stocks/{symbol}")
async def get_stock_fundamentals(symbol: str, db: AsyncSession = Depends(get_db)):
    """Fondamentaux d'une action spécifique."""
    result = await db.execute(
        select(StockFundamentals)
        .where(StockFundamentals.symbol == symbol.upper())
        .order_by(desc(StockFundamentals.fiscal_date))
        .limit(4)
    )
    rows = result.scalars().all()
    if not rows:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")

    return [
        {
            "symbol": r.symbol,
            "period": r.period,
            "fiscal_date": r.fiscal_date.isoformat(),
            "free_cash_flow": r.free_cash_flow,
            "roic": r.roic,
            "operating_cash_flow": r.operating_cash_flow,
            "capital_expenditures": r.capital_expenditures,
            "invested_capital": r.invested_capital,
            "company_name": r.company_name,
            "sector": r.sector,
        }
        for r in rows
    ]


# ═══════════════════════════════════════════════════
# MODULE 3b: SCREENER CRYPTO
# ═══════════════════════════════════════════════════

@router.get("/crypto")
async def get_crypto_data(
    sort_by: str = Query("tvl", description="Sort field: tvl, tvl_change_1d, mcap_fdv_ratio, fees_24h"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Top protocoles DeFi par TVL."""
    query = (
        select(CryptoFundamentals)
        .order_by(desc(CryptoFundamentals.date))
        .limit(limit * 2)
    )
    result = await db.execute(query)
    rows = result.scalars().all()

    seen = set()
    unique_rows = []
    for r in rows:
        if r.protocol not in seen:
            seen.add(r.protocol)
            unique_rows.append(r)
        if len(unique_rows) >= limit:
            break

    data = [
        {
            "protocol": r.protocol,
            "tvl": r.tvl,
            "tvl_change_1d": r.tvl_change_1d,
            "tvl_change_7d": r.tvl_change_7d,
            "mcap": r.mcap,
            "fdv": r.fdv,
            "mcap_fdv_ratio": r.mcap_fdv_ratio,
            "fees_24h": r.fees_24h,
            "fees_7d": r.fees_7d,
            "revenue_24h": r.revenue_24h,
            "chain": r.chain,
            "category": r.category,
            "date": r.date.isoformat(),
        }
        for r in unique_rows
    ]

    sort_key = sort_by if sort_by in ("tvl", "tvl_change_1d", "mcap_fdv_ratio", "fees_24h") else "tvl"
    data.sort(key=lambda x: x.get(sort_key) or 0, reverse=True)
    return data


# ═══════════════════════════════════════════════════
# MODULE 4: INSIDER TRANSACTIONS
# ═══════════════════════════════════════════════════

@router.get("/insiders")
async def get_insider_transactions(
    days: int = Query(7, ge=1, le=365),
    min_amount: float = Query(0),
    codes: str = Query("P,A", description="Codes de transaction à inclure, séparés par des virgules"),
    db: AsyncSession = Depends(get_db),
):
    """Transactions d'initiés récentes (achats par défaut)."""
    cutoff = date.today() - timedelta(days=days)

    codes_list = [c.strip().upper() for c in codes.split(",") if c.strip()]
    if not codes_list:
        codes_list = ["P", "A"]

    query = (
        select(InsiderTransaction)
        .where(InsiderTransaction.filing_date >= cutoff)
    )
    if min_amount > 0:
        query = query.where(InsiderTransaction.total_value >= min_amount)

    query = query.order_by(desc(InsiderTransaction.total_value))
    result = await db.execute(query)
    rows = result.scalars().all()

    return [
        {
            "symbol": r.symbol,
            "company_name": r.company_name,
            "insider_name": r.insider_name,
            "insider_title": r.insider_title,
            "transaction_date": r.transaction_date.isoformat() if r.transaction_date else None,
            "transaction_code": r.transaction_code,
            "acquired_disposed": r.acquired_disposed,
            "shares": r.shares,
            "price_per_share": r.price_per_share,
            "total_value": r.total_value,
            "filing_date": r.filing_date.isoformat(),
            "passed_filters": r.passed_filters,
            "alert_sent": r.alert_sent,
            "rejection_reason": r.rejection_reason,
        }
        for r in rows
    ]


# FIX #2: /insiders/scored déclaré AVANT /insiders (route statique avant paramétrique)
# FIX #2 + #3: rewritten with AsyncSession + text() — no more get_db_connection()
@router.get("/insiders/scored")
async def list_insiders_scored(
    min_score: int = 30,
    days: int = 7,
    min_amount: float = 50000,
    db: AsyncSession = Depends(get_db),
):
    """Transactions initiés enrichies avec score de conviction."""
    query = text("""
        SELECT
            symbol, company_name, insider_name, insider_title,
            transaction_code, total_value, roic, free_cash_flow,
            pe_ttm, sector, insider_score, signal_label, filing_date
        FROM v_insider_scored
        WHERE filing_date >= CURRENT_DATE - CAST(:days AS INTEGER) * INTERVAL '1 day'
          AND total_value >= :min_amount
          AND insider_score >= :min_score
        ORDER BY insider_score DESC, total_value DESC
    """)
    result = await db.execute(query, {
        "days": days,
        "min_amount": min_amount,
        "min_score": min_score,
    })
    rows = result.mappings().all()
    return [dict(row) for row in rows]


# ═══════════════════════════════════════════════════
# ALERTES LOG
# ═══════════════════════════════════════════════════

@router.get("/alerts")
async def get_alert_logs(
    alert_type: str = Query(None, description="Filter: equity or crypto"),
    status: str = Query(None, description="Filter: sent, rejected_fcf, etc."),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Historique des alertes."""
    query = select(AlertLog).order_by(desc(AlertLog.created_at))
    if alert_type:
        query = query.where(AlertLog.alert_type == alert_type)
    if status:
        query = query.where(AlertLog.status == status)
    query = query.limit(limit)

    result = await db.execute(query)
    rows = result.scalars().all()

    return [
        {
            "id": r.id,
            "alert_type": r.alert_type,
            "symbol": r.symbol,
            "trigger": r.trigger,
            "status": r.status,
            "details": r.details,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


# FIX #2: /alerts/enriched rewritten with AsyncSession + text()
@router.get("/alerts/enriched")
async def list_alerts_enriched(
    status: str = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Alertes enrichies avec champs JSONB dépliés."""
    if status:
        raw_query = text("""
            SELECT
                al.id, al.alert_type, al.symbol, al.trigger,
                al.status, al.severity, al.channel,
                al.details::jsonb->>'score_final'   AS score_final,
                al.details::jsonb->>'sector'         AS sector,
                al.details::jsonb->>'sector_etf'     AS sector_etf,
                al.details::jsonb->>'conviction'     AS conviction,
                al.idea_id,
                al.created_at, al.telegram_sent
            FROM alert_logs al
            WHERE al.status = :status
            ORDER BY al.created_at DESC
            LIMIT :limit
        """)
        result = await db.execute(raw_query, {"status": status, "limit": limit})
    else:
        raw_query = text("""
            SELECT
                al.id, al.alert_type, al.symbol, al.trigger,
                al.status, al.severity, al.channel,
                al.details::jsonb->>'score_final'   AS score_final,
                al.details::jsonb->>'sector'         AS sector,
                al.details::jsonb->>'sector_etf'     AS sector_etf,
                al.details::jsonb->>'conviction'     AS conviction,
                al.idea_id,
                al.created_at, al.telegram_sent
            FROM alert_logs al
            ORDER BY al.created_at DESC
            LIMIT :limit
        """)
        result = await db.execute(raw_query, {"limit": limit})

    rows = result.mappings().all()
    return [dict(row) for row in rows]


# ═══════════════════════════════════════════════════
# MODULE 3a: SCREENER EQUITIES (raw SQL)
# FIX #3: rewritten with AsyncSession + text() — no more asyncpg conn.fetch()
# ═══════════════════════════════════════════════════

@router.get("/screener/equities")
async def get_equity_screener(
    sector: str | None = None,
    min_market_cap: float | None = None,
    max_pe: float | None = None,
    min_roe: float | None = None,
    above_sma200: bool | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    search: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Screener actions avec filtres — version SQLAlchemy async."""
    conditions = ["1=1"]
    params: dict = {}

    if sector:
        conditions.append("sector = :sector")
        params["sector"] = sector

    if min_market_cap is not None:
        conditions.append("market_cap >= :min_market_cap")
        params["min_market_cap"] = min_market_cap

    if max_pe is not None:
        conditions.append("pe_ratio <= :max_pe AND pe_ratio > 0")
        params["max_pe"] = max_pe

    if min_roe is not None:
        conditions.append("roe >= :min_roe")
        params["min_roe"] = min_roe

    if above_sma200 is True:
        conditions.append("price > sma_200 AND sma_200 IS NOT NULL")

    if min_price is not None:
        conditions.append("price >= :min_price")
        params["min_price"] = min_price

    if max_price is not None:
        conditions.append("price <= :max_price")
        params["max_price"] = max_price

    if search:
        conditions.append("(symbol ILIKE :search OR company_name ILIKE :search)")
        params["search"] = f"%{search.upper()}%"

    safe_limit = min(limit, 500)
    raw_query = text(f"""
        SELECT * FROM equities_fundamentals
        WHERE {' AND '.join(conditions)}
        ORDER BY market_cap DESC NULLS LAST
        LIMIT {safe_limit}
    """)

    result = await db.execute(raw_query, params)
    rows = result.mappings().all()
    return [dict(row) for row in rows]


# ═══════════════════════════════════════════════════
# IDEAS / OPPORTUNITÉS
# ═══════════════════════════════════════════════════

@router.get("/ideas")
async def list_ideas(
    label: str = None,
    sector: str = None,
    min_score: int = 0,
    db: AsyncSession = Depends(get_db),
):
    return await get_ideas_ranked(db=db, label=label, sector=sector, min_score=min_score)


@router.get("/ideas/{idea_id}")
async def get_idea(idea_id: int, db: AsyncSession = Depends(get_db)):
    idea = await get_idea_detail(db=db, idea_id=idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    return idea


@router.post("/ideas/generate")
async def trigger_idea_generation(db: AsyncSession = Depends(get_db)):
    nb = await generate_ideas_from_signals(db=db)
    return {"generated": nb}


# ═══════════════════════════════════════════════════
# MANUAL TRIGGERS (for testing / on-demand)
# ═══════════════════════════════════════════════════

@router.post("/trigger/sync-macro")
async def trigger_sync_macro():
    from ..tasks.scheduled import task_sync_macro
    task = task_sync_macro.delay()
    return {"task_id": task.id, "status": "queued"}


@router.post("/trigger/sync-sectors")
async def trigger_sync_sectors():
    from ..tasks.scheduled import task_sync_sectors
    task = task_sync_sectors.delay()
    return {"task_id": task.id, "status": "queued"}


@router.post("/trigger/sync-crypto")
async def trigger_sync_crypto():
    from ..tasks.scheduled import task_sync_crypto
    task = task_sync_crypto.delay()
    return {"task_id": task.id, "status": "queued"}


@router.post("/trigger/scan-insiders")
async def trigger_scan_insiders():
    from ..tasks.scheduled import task_scan_insiders
    task = task_scan_insiders.delay()
    return {"task_id": task.id, "status": "queued"}


@router.post("/trigger/process-equity-alerts")
async def trigger_equity_alerts():
    from ..tasks.scheduled import task_process_equity_alerts
    task = task_process_equity_alerts.delay()
    return {"task_id": task.id, "status": "queued"}


@router.post("/trigger/process-crypto-alerts")
async def trigger_crypto_alerts():
    from ..tasks.scheduled import task_process_crypto_alerts
    task = task_process_crypto_alerts.delay()
    return {"task_id": task.id, "status": "queued"}


@router.post("/trigger/sync-stocks")
async def trigger_sync_stocks():
    from ..tasks.scheduled import task_sync_stocks
    task = task_sync_stocks.delay()
    return {"task_id": task.id, "status": "queued"}


@router.post("/trigger/sync-equities")
async def trigger_sync_equities():
    from ..tasks.equity_tasks import celery_sync_equities
    task = celery_sync_equities.delay()
    return {"status": "success", "message": "Equity screener sync triggered", "task_id": task.id}
