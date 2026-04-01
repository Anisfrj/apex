"""Module 3b: Synchro fondamentaux actions (yfinance)."""

from datetime import datetime
from typing import List

import yfinance as yf
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from ..core.logging import get_logger
from ..models.screener import StockFundamentals

logger = get_logger("stocks_sync")

UNIVERSE_TICKERS = [
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


async def sync_stock_fundamentals(
    db: AsyncSession,
    symbols: List[str] | None = None,
    max_quarters: int = 8,
) -> int:
    if symbols is None:
        symbols = UNIVERSE_TICKERS

    total_upserted = 0

    for sym in symbols:
        symbol = sym.upper().strip()
        logger.info("stocks_sync_symbol_start", symbol=symbol)

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}

            company_name = info.get("longName") or info.get("shortName") or symbol
            sector = info.get("sector") or info.get("quoteType") or "Unknown"

            # ─────────────────────────────
            # 1) Données de marché / dividendes
            # ─────────────────────────────
            market_cap = _safe_float(info.get("marketCap"))
            price = _safe_float(
                info.get("currentPrice")
                or info.get("regularMarketPrice")
                or info.get("previousClose")
            )
            pe_ttm = _safe_float(info.get("trailingPE"))
            pb = _safe_float(info.get("priceToBook"))

            dividend_yield = None
            raw_yield = info.get("dividendYield")
            if raw_yield is not None:
                # yfinance renvoie souvent 0.03 pour 3%
                dividend_yield = float(raw_yield) * 100.0

            payout_ratio = None
            raw_payout = info.get("payoutRatio")
            if raw_payout is not None:
                payout_ratio = float(raw_payout) * 100.0

            # ─────────────────────────────
            # 2) Historique de prix pour momentum
            # ─────────────────────────────
            hist = ticker.history(period="5y", auto_adjust=False)
            perf_6m = None
            perf_12m = None
            if hist is not None and not hist.empty:
                close = hist["Close"].dropna()
                if not close.empty:
                    last_price = close.iloc[-1]
                    # 6 mois ~ 126 jours de bourse
                    if len(close) > 126:
                        past_6m = close.iloc[-126]
                        if past_6m > 0:
                            perf_6m = ((last_price / past_6m) - 1.0) * 100.0
                    # 12 mois ~ 252 jours de bourse
                    if len(close) > 252:
                        past_12m = close.iloc[-252]
                        if past_12m > 0:
                            perf_12m = ((last_price / past_12m) - 1.0) * 100.0

            # ─────────────────────────────
            # 3) Cashflow / bilan / ROIC (ton code existant)
            # ─────────────────────────────
            cf_q = ticker.quarterly_cashflow
            bs_q = ticker.quarterly_balance_sheet

            if cf_q is None or cf_q.empty:
                logger.warning("stocks_sync_no_cashflow", symbol=symbol)
                continue

            symbol_upserted = 0
            quarters = list(cf_q.columns[:max_quarters])

            for qt in quarters:
                try:
                    fiscal_date = pd.Timestamp(qt).date()
                except Exception:
                    continue

                period = _period_label(qt)

                operating_cf = _get_row(cf_q, qt, [
                    "Operating Cash Flow",
                    "Total Cash From Operating Activities",
                    "Cash From Operations",
                ])
                capex = _get_row(cf_q, qt, [
                    "Capital Expenditure",
                    "Capital Expenditures",
                    "Purchases Of Property Plant And Equipment",
                ])
                net_income = _get_row(cf_q, qt, [
                    "Net Income",
                    "Net Income From Continuing Operations",
                    "Net Income Common Stockholders",
                ])

                free_cf = None
                if operating_cf is not None and capex is not None:
                    # capex est généralement négatif dans yfinance
                    free_cf = operating_cf + capex

                total_assets = None
                total_debt = None
                total_equity = None
                cash_eq = None

                if bs_q is not None and not bs_q.empty and qt in bs_q.columns:
                    total_assets = _get_row(bs_q, qt, ["Total Assets"])
                    total_equity = _get_row(bs_q, qt, [
                        "Stockholders Equity",
                        "Total Stockholder Equity",
                        "Common Stock Equity",
                    ])
                    total_debt = _get_row(bs_q, qt, [
                        "Total Debt",
                        "Long Term Debt",
                        "Total Long Term Debt",
                    ])
                    cash_eq = _get_row(bs_q, qt, [
                        "Cash And Cash Equivalents",
                        "Cash Cash Equivalents And Short Term Investments",
                        "Cash",
                    ])

                invested_capital = None
                if (
                    total_equity is not None
                    and total_debt is not None
                    and cash_eq is not None
                ):
                    invested_capital = total_equity + total_debt - cash_eq

                roic = None
                if invested_capital and invested_capital != 0 and net_income is not None:
                    roic = net_income / invested_capital

                # ─────────────────────────────
                # 4) Upsert complet avec nouveaux champs
                # ─────────────────────────────
                stmt = (
                    insert(StockFundamentals)
                    .values(
                        id=f"{symbol}_{period}",
                        symbol=symbol,
                        period=period,
                        fiscal_date=fiscal_date,
                        operating_cash_flow=operating_cf,
                        capital_expenditures=capex,
                        free_cash_flow=free_cf,
                        total_assets=total_assets,
                        total_debt=total_debt,
                        total_equity=total_equity,
                        cash_and_equivalents=cash_eq,
                        net_income=net_income,
                        ebit=None,
                        tax_rate=None,
                        invested_capital=invested_capital,
                        roic=roic,
                        sector=sector,
                        company_name=company_name,
                        # Nouveaux champs screener
                        market_cap=market_cap,
                        price=price,
                        pe_ttm=pe_ttm,
                        pb=pb,
                        rev_cagr_3y=None,
                        eps_cagr_3y=None,
                        perf_6m=perf_6m,
                        perf_12m=perf_12m,
                        dividend_yield=dividend_yield,
                        payout_ratio=payout_ratio,
                        insider_net_buy_usd_6m=None,
                        insider_buy_trades_6m=None,
                    )
                    .on_conflict_do_update(
                        index_elements=["symbol", "period"],
                        set_={
                            "fiscal_date": fiscal_date,
                            "operating_cash_flow": operating_cf,
                            "capital_expenditures": capex,
                            "free_cash_flow": free_cf,
                            "total_assets": total_assets,
                            "total_debt": total_debt,
                            "total_equity": total_equity,
                            "cash_and_equivalents": cash_eq,
                            "net_income": net_income,
                            "invested_capital": invested_capital,
                            "roic": roic,
                            "sector": sector,
                            "company_name": company_name,
                            "market_cap": market_cap,
                            "price": price,
                            "pe_ttm": pe_ttm,
                            "pb": pb,
                            "perf_6m": perf_6m,
                            "perf_12m": perf_12m,
                            "dividend_yield": dividend_yield,
                            "payout_ratio": payout_ratio,
                            # rev_cagr_3y, eps_cagr_3y, insiders: à enrichir plus tard
                        },
                    )
                )
                await db.execute(stmt)
                symbol_upserted += 1

            await db.commit()
            total_upserted += symbol_upserted
            logger.info(
                "stocks_sync_symbol_complete",
                symbol=symbol,
                quarters_upserted=symbol_upserted,
            )

        except Exception as e:
            logger.warning("stocks_sync_symbol_error", symbol=symbol, error=str(e))
            await db.rollback()

    logger.info("stocks_sync_complete", total_upserted=total_upserted)
    return total_upserted
