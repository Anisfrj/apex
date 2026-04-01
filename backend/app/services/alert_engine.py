"""Moteur d'Alertes — Logique de filtrage Top-Down (Entonnoir)."""

import json
import uuid
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select, desc

from ..core.config import get_settings
from ..core.logging import get_logger
from ..models.insider import InsiderTransaction
from ..models.screener import StockFundamentals, CryptoFundamentals
from ..models.sector import SectorETF, SECTOR_ETFS
from ..models.macro import MacroSeries
from ..models.alerts import AlertLog
from ..modules.screener.stocks import (
    sync_stock_fundamentals,
    check_fcf_positive_4q,
    get_latest_roic,
)
from .telegram import send_telegram_message, format_equity_alert, format_crypto_alert

logger = get_logger("alert_engine")


async def get_macro_trend(db: AsyncSession) -> str:
    """Évalue la tendance macro globale."""
    trends = []

    # Fed Funds Rate
    result = await db.execute(
        select(MacroSeries.value)
        .where(MacroSeries.series_id == "DFF")
        .order_by(desc(MacroSeries.date))
        .limit(2)
    )
    dff_values = [row[0] for row in result.fetchall()]
    if len(dff_values) >= 2:
        if dff_values[0] < dff_values[1]:
            trends.append("Fed Funds ↓ (assouplissement)")
        elif dff_values[0] > dff_values[1]:
            trends.append("Fed Funds ↑ (resserrement)")
        else:
            trends.append(f"Fed Funds stable ({dff_values[0]}%)")

    # Yield Curve
    result = await db.execute(
        select(MacroSeries.value)
        .where(MacroSeries.series_id == "T10Y2Y")
        .order_by(desc(MacroSeries.date))
        .limit(1)
    )
    t10y2y = result.fetchone()
    if t10y2y:
        if t10y2y[0] < 0:
            trends.append(f"Courbe inversée ({t10y2y[0]:.2f}) ⚠️")
        else:
            trends.append(f"Courbe normale ({t10y2y[0]:.2f})")

    # M2 Supply
    result = await db.execute(
        select(MacroSeries.value)
        .where(MacroSeries.series_id == "WM2NS")
        .order_by(desc(MacroSeries.date))
        .limit(2)
    )
    m2_values = [row[0] for row in result.fetchall()]
    if len(m2_values) >= 2:
        m2_change = ((m2_values[0] - m2_values[1]) / m2_values[1]) * 100
        trends.append(f"M2 {'↑' if m2_change > 0 else '↓'} ({m2_change:+.2f}%)")

    return " | ".join(trends) if trends else "Données macro non disponibles"


async def get_sector_status(db: AsyncSession, sector_name: str) -> bool | None:
    """Vérifie si un secteur est au-dessus de sa MM200."""
    # Find the ETF symbol for this sector
    symbol = None
    for etf_symbol, name in SECTOR_ETFS.items():
        if name.lower() == sector_name.lower():
            symbol = etf_symbol
            break

    if not symbol:
        return None

    result = await db.execute(
        select(SectorETF.above_sma200)
        .where(SectorETF.symbol == symbol)
        .order_by(desc(SectorETF.date))
        .limit(1)
    )
    row = result.fetchone()
    return row[0] if row else None


async def log_alert(
    db: AsyncSession, alert_type: str, symbol: str, trigger: str,
    status: str, details: dict | None = None
):
    """Log une alerte dans la DB."""
    stmt = insert(AlertLog).values(
        id=str(uuid.uuid4()),
        alert_type=alert_type,
        symbol=symbol,
        trigger=trigger,
        status=status,
        details=json.dumps(details) if details else None,
    )
    await db.execute(stmt)


# ═══════════════════════════════════════════════════════
# WORKFLOW ACTIONS (ÉQUITÉS)
# ═══════════════════════════════════════════════════════

async def process_equity_alerts(db: AsyncSession):
    """
    Workflow Actions — Filtrage en entonnoir :
    1. Déclencheur : Form 4 (Code P) > 250k$
    2. Vérif Niveau 3 : FCF positif 4Q + ROIC > 10%
    3. Vérif Niveau 2 : Secteur au-dessus MM200
    4. Alerte Telegram
    """
    settings = get_settings()

    # Step 1: Get unprocessed insider buys > threshold
    result = await db.execute(
        select(InsiderTransaction)
        .where(InsiderTransaction.transaction_code == "P")
        .where(InsiderTransaction.total_value >= settings.insider_min_amount)
        .where(InsiderTransaction.alert_sent == False)
        .where(InsiderTransaction.passed_filters == None)
    )
    transactions = result.scalars().all()
    logger.info("equity_workflow_start", pending_transactions=len(transactions))

    alerts_sent = 0
    for txn in transactions:
        symbol = txn.symbol
        if not symbol:
            continue

        # Sync fundamentals if needed
        await sync_stock_fundamentals(db, symbol)

        # Step 2: Check FCF positive (4 quarters)
        fcf_ok = await check_fcf_positive_4q(db, symbol)
        if not fcf_ok:
            txn.passed_filters = False
            txn.rejection_reason = "FCF négatif sur les 4 derniers trimestres"
            await log_alert(db, "equity", symbol, "insider_buy", "rejected_fcf", {
                "insider": txn.insider_name, "amount": txn.total_value
            })
            logger.info("equity_rejected_fcf", symbol=symbol)
            continue

        # Step 2b: Check ROIC > threshold
        roic = await get_latest_roic(db, symbol)
        if roic is None or roic < settings.roic_min_threshold:
            txn.passed_filters = False
            txn.rejection_reason = f"ROIC insuffisant ({roic}% < {settings.roic_min_threshold}%)"
            await log_alert(db, "equity", symbol, "insider_buy", "rejected_roic", {
                "insider": txn.insider_name, "roic": roic
            })
            logger.info("equity_rejected_roic", symbol=symbol, roic=roic)
            continue

        # Step 3: Check sector above SMA200
        # Get sector from fundamentals
        fund_result = await db.execute(
            select(StockFundamentals.sector)
            .where(StockFundamentals.symbol == symbol)
            .order_by(desc(StockFundamentals.fiscal_date))
            .limit(1)
        )
        sector_row = fund_result.fetchone()
        sector = sector_row[0] if sector_row else None

        if sector:
            above_sma = await get_sector_status(db, sector)
            if above_sma is False:
                txn.passed_filters = False
                txn.rejection_reason = f"Secteur {sector} sous MM200"
                await log_alert(db, "equity", symbol, "insider_buy", "rejected_sector", {
                    "sector": sector
                })
                logger.info("equity_rejected_sector", symbol=symbol, sector=sector)
                continue
        else:
            above_sma = None

        # Step 4: All filters passed → Send alert
        macro_trend = await get_macro_trend(db)

        # Get latest FCF value
        fcf_result = await db.execute(
            select(StockFundamentals.free_cash_flow)
            .where(StockFundamentals.symbol == symbol)
            .order_by(desc(StockFundamentals.fiscal_date))
            .limit(1)
        )
        fcf_row = fcf_result.fetchone()
        fcf_value = fcf_row[0] if fcf_row else 0

        message = format_equity_alert(
            company_name=txn.company_name or symbol,
            symbol=symbol,
            insider_name=txn.insider_name,
            insider_title=txn.insider_title or "N/A",
            amount=txn.total_value,
            roic=roic,
            fcf=fcf_value,
            sector=sector or "N/A",
            above_sma200=above_sma if above_sma is not None else True,
            macro_trend=macro_trend,
        )

        sent = await send_telegram_message(message)
        txn.alert_sent = sent
        txn.passed_filters = True
        alerts_sent += 1

        await log_alert(db, "equity", symbol, "insider_buy", "sent" if sent else "send_failed", {
            "insider": txn.insider_name,
            "amount": txn.total_value,
            "roic": roic,
            "fcf": fcf_value,
        })
        logger.info("equity_alert_sent", symbol=symbol, insider=txn.insider_name)

    await db.commit()
    logger.info("equity_workflow_complete", alerts_sent=alerts_sent)
    return alerts_sent


# ═══════════════════════════════════════════════════════
# WORKFLOW CRYPTO (ON-CHAIN)
# ═══════════════════════════════════════════════════════

async def process_crypto_alerts(db: AsyncSession):
    """
    Workflow Crypto — Filtrage en entonnoir :
    1. Déclencheur : TVL spike > seuil (20%)
    2. Vérif : MCap/FDV > 0.4
    3. Alerte Telegram
    """
    settings = get_settings()

    # Step 1: Find TVL spikes from today's data
    result = await db.execute(
        select(CryptoFundamentals)
        .where(CryptoFundamentals.date == date.today())
        .where(CryptoFundamentals.tvl_change_1d > settings.tvl_spike_threshold)
        .order_by(desc(CryptoFundamentals.tvl_change_1d))
    )
    spikes = result.scalars().all()
    logger.info("crypto_workflow_start", tvl_spikes=len(spikes))

    alerts_sent = 0
    for proto in spikes:
        # Step 2: Check MCap/FDV ratio
        if proto.mcap_fdv_ratio is None or proto.mcap_fdv_ratio < settings.crypto_mcap_fdv_min_ratio:
            await log_alert(db, "crypto", proto.protocol, "tvl_spike", "rejected_dilution", {
                "mcap_fdv_ratio": proto.mcap_fdv_ratio,
                "tvl_change": proto.tvl_change_1d,
            })
            logger.info("crypto_rejected_dilution", protocol=proto.protocol,
                       ratio=proto.mcap_fdv_ratio)
            continue

        # Step 3: Send alert
        message = format_crypto_alert(
            protocol=proto.protocol,
            tvl=proto.tvl or 0,
            tvl_change=proto.tvl_change_1d or 0,
            mcap=proto.mcap or 0,
            fdv=proto.fdv or 0,
            mcap_fdv_ratio=proto.mcap_fdv_ratio or 0,
            fees_24h=proto.fees_24h,
        )

        sent = await send_telegram_message(message)
        alerts_sent += 1

        await log_alert(db, "crypto", proto.protocol, "tvl_spike",
                       "sent" if sent else "send_failed", {
                           "tvl": proto.tvl,
                           "tvl_change": proto.tvl_change_1d,
                           "mcap_fdv": proto.mcap_fdv_ratio,
                       })
        logger.info("crypto_alert_sent", protocol=proto.protocol)

    await db.commit()
    logger.info("crypto_workflow_complete", alerts_sent=alerts_sent)
    return alerts_sent
