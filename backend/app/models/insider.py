"""Models — Module 4: Traqueur d'Initiés (EDGAR Form 4)."""

from sqlalchemy import Column, String, Float, Date, DateTime, Boolean, Index
from sqlalchemy.sql import func

from ..core.database import Base


class InsiderTransaction(Base):
    """Transactions d'initiés SEC Form 4 (tous codes : P, S, A, M, F, etc.)."""

    __tablename__ = "insider_transactions"

    id = Column(String, primary_key=True)  # ID unique par filing + symbol + date + code
    filing_date = Column(Date, nullable=False, index=True)

    # Issuer / titre
    symbol = Column(String(10), nullable=False, index=True)
    company_name = Column(String(200), nullable=True)
    company_cik = Column(String(20), nullable=True)

    # Initié
    insider_name = Column(String(200), nullable=False)
    insider_title = Column(String(200), nullable=True)

    # Détail de la transaction
    transaction_date = Column(Date, nullable=True)
    transaction_code = Column(String(5), nullable=True)   # P, S, A, M, F, ...
    acquired_disposed = Column(String(1), nullable=True)  # 'A' ou 'D'
    shares = Column(Float, nullable=True)
    price_per_share = Column(Float, nullable=True)
    total_value = Column(Float, nullable=True)
    shares_owned_after = Column(Float, nullable=True)

    # Traitement alertes
    alert_sent = Column(Boolean, default=False)
    passed_filters = Column(Boolean, nullable=True)
    rejection_reason = Column(String(200), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_insider_filing", "filing_date", "symbol"),
    )
