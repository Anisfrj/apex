"""Models — Module 2: Radar Sectoriel."""

from sqlalchemy import Column, String, Float, Date, DateTime, Boolean, Index
from sqlalchemy.sql import func
from ..core.database import Base


class SectorETF(Base):
    """Données quotidiennes des ETF sectoriels GICS."""
    __tablename__ = "sector_etfs"

    id = Column(String, primary_key=True)  # e.g. "XLK_2024-01-15"
    symbol = Column(String(10), nullable=False, index=True)
    date = Column(Date, nullable=False)
    close_price = Column(Float, nullable=False)
    sma_200 = Column(Float, nullable=True)  # Moyenne Mobile 200j
    relative_strength_30d = Column(Float, nullable=True)  # Force relative vs S&P500 30j
    above_sma200 = Column(Boolean, nullable=True)
    sector_name = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_sector_etfs_date", "symbol", "date", unique=True),
    )


# Mapping ETF -> Secteur GICS
SECTOR_ETFS = {
    "XLK": "Technology",
    "XLV": "Health Care",
    "XLF": "Financials",
    "XLE": "Energy",
    "XLI": "Industrials",
    "XLC": "Communication Services",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLRE": "Real Estate",
    "XLB": "Materials",
    "XLU": "Utilities",
}

SP500_SYMBOL = "^GSPC"
