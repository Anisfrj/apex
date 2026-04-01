"""Models — Module 3: Screener Fondamental."""

from sqlalchemy import Column, String, Float, Date, DateTime, Integer, Index
from sqlalchemy.sql import func
from ..core.database import Base


class StockFundamentals(Base):
    """Données fondamentales trimestrielles des actions."""
    __tablename__ = "stock_fundamentals"

    id = Column(String, primary_key=True)  # e.g. "AAPL_2024Q3"
    symbol = Column(String(10), nullable=False, index=True)
    period = Column(String(10), nullable=False)  # "2024Q3"
    fiscal_date = Column(Date, nullable=False)
    # Cash Flow Statement
    operating_cash_flow = Column(Float, nullable=True)
    capital_expenditures = Column(Float, nullable=True)
    free_cash_flow = Column(Float, nullable=True)
    # Balance Sheet
    total_assets = Column(Float, nullable=True)
    total_debt = Column(Float, nullable=True)
    total_equity = Column(Float, nullable=True)
    cash_and_equivalents = Column(Float, nullable=True)
    # Income Statement (for ROIC)
    net_income = Column(Float, nullable=True)
    ebit = Column(Float, nullable=True)
    tax_rate = Column(Float, nullable=True)
    # Calculated
    invested_capital = Column(Float, nullable=True)  # equity + debt - cash
    roic = Column(Float, nullable=True)  # NOPAT / Invested Capital
    # Meta
    sector = Column(String(50), nullable=True)
    company_name = Column(String(200), nullable=True)
    # Après company_name, par exemple

    # Market / pricing
    market_cap = Column(Float, nullable=True)
    price = Column(Float, nullable=True)

    # Multiples de valorisation
    pe_ttm = Column(Float, nullable=True)
    pb = Column(Float, nullable=True)

    # Croissance (annuelle ou CAGR)
    rev_cagr_3y = Column(Float, nullable=True)
    eps_cagr_3y = Column(Float, nullable=True)

    # Momentum
    perf_6m = Column(Float, nullable=True)
    perf_12m = Column(Float, nullable=True)

    # Dividendes
    dividend_yield = Column(Float, nullable=True)
    payout_ratio = Column(Float, nullable=True)

    # Insiders (aggrégeras depuis ton module insiders)
    insider_net_buy_usd_6m = Column(Float, nullable=True)
    insider_buy_trades_6m = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_stock_fund_period", "symbol", "period", unique=True),
    )


class CryptoFundamentals(Base):
    """Données fondamentales crypto (DeFiLlama + Token Terminal)."""
    __tablename__ = "crypto_fundamentals"

    id = Column(String, primary_key=True)  # e.g. "aave_2024-01-15"
    protocol = Column(String(100), nullable=False, index=True)
    date = Column(Date, nullable=False)
    tvl = Column(Float, nullable=True)          # Total Value Locked
    tvl_change_1d = Column(Float, nullable=True)  # % change 24h
    tvl_change_7d = Column(Float, nullable=True)  # % change 7d
    mcap = Column(Float, nullable=True)          # Market Cap
    fdv = Column(Float, nullable=True)           # Fully Diluted Valuation
    mcap_fdv_ratio = Column(Float, nullable=True)
    fees_24h = Column(Float, nullable=True)      # Fees générés 24h
    fees_7d = Column(Float, nullable=True)       # Fees générés 7j
    revenue_24h = Column(Float, nullable=True)   # Revenue protocole 24h
    chain = Column(String(50), nullable=True)
    category = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_crypto_fund_date", "protocol", "date", unique=True),
    )
