"""Module 3a: Screener Fondamental — Actions.

Source de données : yfinance (gratuit, sans clé API).
"""

import asyncio
from datetime import datetime, date, timedelta
from typing import List

import yfinance as yf
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select, desc, distinct, func

from ...core.logging import get_logger
from ...models.screener import StockFundamentals
from ...models.insider import InsiderTransaction

logger = get_logger("stock_screener")

SP500_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA",
    "JPM", "JNJ", "V", "MA", "HD", "PG", "XOM", "UNH",
    "BAC", "AVGO", "LLY", "MRK", "COST", "ABBV", "CVX",
    "WMT", "KO", "PEP", "TMO", "NFLX", "AMD", "INTC",
    "ORCL", "ADBE", "CRM", "QCOM", "TXN", "NOW", "INTU",
]


def _safe_float(value) -> float | None:
    try:
        if pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _get_row(df: pd.DataFrame, col, candidates: list) -> float | None:
    for name in candidates:
        if name in df.index:
            return _safe_float(df.loc[name, col])
    return None


def _period_label(dt) -> str:
    try:
        d = pd.Timestamp(dt)
        q = ((d.month - 1) // 3) + 1
        return f"{d.year}Q{q}"
    except Exception:
        return "UNKNOWN"


def calculate_roic(ebit: float, tax_rate: float, invested_capital: float) -> float | None:
    if not invested_capital or invested_capital <= 0 or ebit is None:
        return None
    effective_tax = max(0.0, min(tax_rate or 0.21, 1.0))
    nopat = ebit * (1 - effective_tax)
    return round((nopat / invested_capital) * 100, 2)


def calculate_cagr(value_end: float, value_start: float, years: int) -> float | None:
    if not value_start or value_start <= 0 or not value_end or years <= 0:
        return None
    try:
        return round(((value_end / value_start) ** (1 / years) - 1) * 100, 2)
    except Exception:
        return None


def _fetch_ticker_data(symbol: str) -> dict:
    ticker = yf.Ticker(symbol)
    info = ticker.info or {}

    cf_q  = ticker.quarterly_cashflow
    bs_q  = ticker.quarterly_balance_sheet
    inc_q = getattr(ticker, "quarterly_income_stmt", None)
    if inc_q is None or (hasattr(inc_q, "empty") and inc_q.empty):
        inc_q = ticker.quarterly_financials

    fin_a = getattr(ticker, "income_stmt", None)
    if fin_a is None or (hasattr(fin_a, "empty") and fin_a.empty):
        fin_a = ticker.financials

    hist = ticker.history(period="1y")

    return {
        "info":  info,
        "cf_q":  cf_q,
        "bs_q":  bs_q,
        "inc_q": inc_q,
        "fin_a": fin_a,
        "hist":  hist,
    }


async def sync_stock_fundamentals(db: AsyncSession, symbol: str) -> dict | None:
    symbol = symbol.upper().strip()
    logger.info("stock_sync_start", symbol=symbol)

    loop = asyncio.get_event_loop()
    try:
        data = await loop.run_in_executor(None, _fetch_ticker_data, symbol)
    except Exception as e:
        logger.error("yfinance_fetch_error", symbol=symbol, error=str(e))
        return None

    info  = data["info"]
    cf_q  = data["cf_q"]
    bs_q  = data["bs_q"]
    inc_q = data["inc_q"]
    fin_a = data["fin_a"]
    hist  = data["hist"]

    if cf_q is None or cf_q.empty:
        logger.warning("insufficient_data", symbol=symbol)
        return None

    market_cap  = _safe_float(info.get("marketCap"))
    price       = _safe_float(info.get("currentPrice") or info.get("regularMarketPrice"))
    pe_ttm      = _safe_float(info.get("trailingPE"))
    pb          = _safe_float(info.get("priceToBook"))
    div_yield   = _safe_float(info.get("dividendYield"))
    payout      = _safe_float(info.get("payoutRatio"))
    sector      = info.get("sector") or info.get("quoteType") or "Unknown"
    company_name = info.get("longName") or info.get("shortName") or symbol

    perf_6m  = None
    perf_12m = None
    if hist is not None and not hist.empty and len(hist) > 1:
        close = hist["Close"]
        current_price = close.iloc[-1]
        if len(close) >= 126 and current_price:
            p6m = close.iloc[-126]
            perf_6m = round(((current_price / p6m) - 1) * 100, 2) if p6m else None
        if len(close) >= 2 and current_price:
            p12m = close.iloc[0]
            perf_12m = round(((current_price / p12m) - 1) * 100, 2) if p12m else None

    rev_cagr_3y = None
    eps_cagr_3y = None
    if fin_a is not None and not fin_a.empty and len(fin_a.columns) >= 4:
        cols = list(fin_a.columns)
        rev_end   = _get_row(fin_a, cols[0], ["Total Revenue", "Revenue"])
        rev_start = _get_row(fin_a, cols[3], ["Total Revenue", "Revenue"])
        rev_cagr_3y = calculate_cagr(rev_end, rev_start, years=3)

        ni_end   = _get_row(fin_a, cols[0], ["Net Income", "Net Income Common Stockholders"])
        ni_start = _get_row(fin_a, cols[3], ["Net Income", "Net Income Common Stockholders"])
        shares   = _safe_float(info.get("sharesOutstanding"))
        if shares and shares > 0 and ni_end and ni_start:
            eps_cagr_3y = calculate_cagr(ni_end / shares, ni_start / shares, years=3)

    cutoff_6m = date.today() - timedelta(days=180)
    ins_result = await db.execute(
        select(
            func.sum(InsiderTransaction.total_value),
            func.count(InsiderTransaction.id),
        )
        .where(InsiderTransaction.symbol == symbol)
        .where(InsiderTransaction.transaction_code == "P")
        .where(InsiderTransaction.filing_date >= cutoff_6m)
    )
    ins_row = ins_result.fetchone()
    insider_net_buy   = ins_row[0] if ins_row and ins_row[0] else None
    insider_buy_count = ins_row[1] if ins_row and ins_row[1] else None

    results = []
    quarters = list(cf_q.columns[:8])

    for qt in quarters:
        try:
            fiscal_date = pd.Timestamp(qt).date()
        except Exception:
            continue

        period = _period_label(qt)
        if period == "UNKNOWN":
            continue

        ocf       = _get_row(cf_q, qt, ["Operating Cash Flow", "Total Cash From Operating Activities", "Cash From Operations"])
        capex_raw = _get_row(cf_q, qt, ["Capital Expenditure", "Capital Expenditures", "Purchases Of Property Plant And Equipment"])
        capex     = abs(capex_raw) if capex_raw is not None else None
        fcf       = (ocf - capex) if (ocf is not None and capex is not None) else ocf

        total_assets = total_debt = total_equity = cash_eq = None
        if bs_q is not None and not bs_q.empty and qt in bs_q.columns:
            total_assets = _get_row(bs_q, qt, ["Total Assets"])
            total_equity = _get_row(bs_q, qt, ["Stockholders Equity", "Total Stockholder Equity", "Common Stock Equity"])
            total_debt   = _get_row(bs_q, qt, ["Total Debt", "Long Term Debt", "Total Long Term Debt"])
            cash_eq      = _get_row(bs_q, qt, ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments", "Cash"])

        invested_capital = None
        if total_equity is not None and total_debt is not None and cash_eq is not None:
            invested_capital = total_equity + total_debt - cash_eq

        net_income = ebit_actual = None
        effective_tax = 0.21
        if inc_q is not None and not inc_q.empty and qt in inc_q.columns:
            net_income   = _get_row(inc_q, qt, ["Net Income", "Net Income Common Stockholders", "Net Income From Continuing Operations"])
            ebit_actual  = _get_row(inc_q, qt, ["EBIT", "Operating Income", "Pretax Income"])
            tax_exp      = _get_row(inc_q, qt, ["Tax Provision", "Income Tax Expense"])
            pretax       = _get_row(inc_q, qt, ["Pretax Income", "Income Before Tax"])
            if tax_exp and pretax and pretax != 0:
                effective_tax = tax_exp / pretax

        roic = calculate_roic(ebit_actual, effective_tax, invested_capital)

        record = {
            "id":                     f"{symbol}_{period}",
            "symbol":                 symbol,
            "period":                 period,
            "fiscal_date":            fiscal_date,
            "operating_cash_flow":    ocf,
            "capital_expenditures":   capex,
            "free_cash_flow":         fcf,
            "total_assets":           total_assets,
            "total_debt":             total_debt,
            "total_equity":           total_equity,
            "cash_and_equivalents":   cash_eq,
            "net_income":             net_income,
            "ebit":                   ebit_actual,
            "tax_rate":               effective_tax,
            "invested_capital":       invested_capital,
            "roic":                   roic,
            "sector":                 sector,
            "company_name":           company_name,
            "market_cap":             market_cap,
            "price":                  price,
            "pe_ttm":                 pe_ttm,
            "pb":                     pb,
            "rev_cagr_3y":            rev_cagr_3y,
            "eps_cagr_3y":            eps_cagr_3y,
            "perf_6m":                perf_6m,
            "perf_12m":               perf_12m,
            "dividend_yield":         div_yield,
            "payout_ratio":           payout,
            "insider_net_buy_usd_6m": insider_net_buy,
            "insider_buy_trades_6m":  insider_buy_count,
        }

        update_fields = {k: v for k, v in record.items() if k != "id"}
        stmt = (
            insert(StockFundamentals)
            .values(**record)
            .on_conflict_do_update(index_elements=["id"], set_=update_fields)
        )
        await db.execute(stmt)
        results.append(record)

    await db.commit()
    logger.info("stock_fundamentals_synced", symbol=symbol, quarters=len(results))
    return results[0] if results else None


async def sync_all_stock_fundamentals(db: AsyncSession) -> int:
    logger.info("batch_sync_start", total_symbols=len(SP500_UNIVERSE))
    success_count = 0
    for i, symbol in enumerate(SP500_UNIVERSE):
        try:
            result = await sync_stock_fundamentals(db, symbol)
            if result:
                success_count += 1
        except Exception as e:
            logger.error("batch_symbol_failed", symbol=symbol, error=str(e))
        await asyncio.sleep(1.0)
    logger.info("batch_sync_complete", success=success_count, total=len(SP500_UNIVERSE))
    return success_count


async def backfill_from_insider_transactions(db: AsyncSession) -> int:
    result = await db.execute(
        select(distinct(InsiderTransaction.symbol))
        .where(InsiderTransaction.symbol.isnot(None))
    )
    symbols = [row[0] for row in result.fetchall()]
    logger.info("backfill_start", unique_symbols=len(symbols))

    success_count = 0
    for i, symbol in enumerate(symbols):
        existing = await db.execute(
            select(StockFundamentals.id)
            .where(StockFundamentals.symbol == symbol)
            .limit(1)
        )
        if existing.fetchone():
            logger.debug("backfill_skip_exists", symbol=symbol)
            continue

        try:
            result = await sync_stock_fundamentals(db, symbol)
            if result:
                success_count += 1
                logger.info("backfill_symbol_done", symbol=symbol, index=i + 1, total=len(symbols))
        except Exception as e:
            logger.error("backfill_symbol_failed", symbol=symbol, error=str(e))

        await asyncio.sleep(1.5)

    logger.info("backfill_complete", success=success_count, total=len(symbols))
    return success_count


async def check_fcf_positive_4q(db: AsyncSession, symbol: str) -> bool:
    result = await db.execute(
        select(StockFundamentals.free_cash_flow)
        .where(StockFundamentals.symbol == symbol)
        .order_by(desc(StockFundamentals.fiscal_date))
        .limit(4)
    )
    fcf_values = [row[0] for row in result.fetchall()]
    if len(fcf_values) < 4:
        return False
    return all(fcf is not None and fcf > 0 for fcf in fcf_values)


async def get_latest_roic(db: AsyncSession, symbol: str) -> float | None:
    result = await db.execute(
        select(StockFundamentals.roic)
        .where(StockFundamentals.symbol == symbol)
        .order_by(desc(StockFundamentals.fiscal_date))
        .limit(1)
    )
    row = result.fetchone()
    return row[0] if row else None
