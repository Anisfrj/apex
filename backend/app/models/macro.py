"""Models — Module 1: Macroéconomie."""

from sqlalchemy import Column, String, Float, Date, DateTime, Index
from sqlalchemy.sql import func
from ..core.database import Base


class MacroSeries(Base):
    """Séries temporelles macroéconomiques (FRED)."""
    __tablename__ = "macro_series"

    id = Column(String, primary_key=True)  # e.g. "DFF_2024-01-15"
    series_id = Column(String(20), nullable=False, index=True)  # DFF, WM2NS, T10Y2Y
    date = Column(Date, nullable=False)
    value = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_macro_series_date", "series_id", "date", unique=True),
    )
