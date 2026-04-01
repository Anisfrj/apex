# backend/app/models/ideas.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Signal(BaseModel):
    id: int
    symbol: str
    as_of: datetime
    signal_type: str
    direction: str
    strength: float
    horizon: Optional[str]
    drivers: Optional[dict]
    source_engine: Optional[str]
    created_at: datetime

class Idea(BaseModel):
    id: int
    symbol: str
    status: str
    thesis_summary: Optional[str]
    conviction_score: Optional[int]
    risk_score: Optional[int]
    recommended_action: Optional[str]
    time_horizon: Optional[str]
    entry_zone_min: Optional[float]
    entry_zone_max: Optional[float]
    target_price: Optional[float]
    stop_loss: Optional[float]
    rationale: Optional[dict]
    created_at: datetime
    updated_at: datetime

class IdeaRanked(BaseModel):
    id: int
    symbol: str
    conviction_score: Optional[int]
    risk_score: Optional[int]
    recommended_action: Optional[str]
    status: str
    thesis_summary: Optional[str]
    entry_zone_min: Optional[float]
    entry_zone_max: Optional[float]
    target_price: Optional[float]
    stop_loss: Optional[float]
    # Fondamentaux
    pe_ttm: Optional[float]
    roic: Optional[float]
    free_cash_flow: Optional[float]
    rev_cagr_3y: Optional[float]
    market_cap: Optional[float]
    sector: Optional[str]
    # Signal
    signal_label: Optional[str]
    signal_strength: Optional[float]
    filing_date: Optional[str]
    # Secteur
    sector_etf: Optional[str]
    sector_above_sma200: Optional[bool]
    sector_rs30d: Optional[float]
    # Macro
    yield_curve: Optional[float]
    fed_funds: Optional[float]
    # Score final
    score_final_adjusted: Optional[int]
    final_label: Optional[str]
    created_at: datetime
    updated_at: datetime
