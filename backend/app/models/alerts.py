"""Models — Historique des alertes envoyées."""

from sqlalchemy import Column, String, Float, DateTime, Text, Index
from sqlalchemy.sql import func
from ..core.database import Base


class AlertLog(Base):
    """Log de toutes les alertes (envoyées et rejetées)."""
    __tablename__ = "alert_logs"

    id = Column(String, primary_key=True)
    alert_type = Column(String(20), nullable=False, index=True)  # "equity" or "crypto"
    symbol = Column(String(20), nullable=False, index=True)
    trigger = Column(String(50), nullable=False)  # "insider_buy", "tvl_spike"
    status = Column(String(20), nullable=False)  # "sent", "rejected_fcf", "rejected_roic", etc.
    details = Column(Text, nullable=True)  # JSON details
    telegram_sent = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_alert_created", "created_at"),
    )
