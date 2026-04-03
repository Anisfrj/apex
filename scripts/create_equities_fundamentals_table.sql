-- Migration: Create equities_fundamentals table
-- Run this on apex-db container: docker exec -it apex-db psql -U apex -d apex_screener -f /path/to/this/file.sql

CREATE TABLE IF NOT EXISTS equities_fundamentals (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) UNIQUE NOT NULL,
    company_name TEXT,
    sector VARCHAR(100),
    industry VARCHAR(100),
    market_cap BIGINT,
    price NUMERIC(20, 4),
    pe_ratio NUMERIC(10, 2),
    pb_ratio NUMERIC(10, 2),
    ps_ratio NUMERIC(10, 2),
    peg_ratio NUMERIC(10, 2),
    roe NUMERIC(10, 4),
    profit_margin NUMERIC(10, 4),
    revenue_growth NUMERIC(10, 4),
    earnings_growth NUMERIC(10, 4),
    debt_to_equity NUMERIC(10, 2),
    sma_50 NUMERIC(20, 4),
    sma_200 NUMERIC(20, 4),
    volume BIGINT,
    avg_volume BIGINT,
    beta NUMERIC(10, 4),
    dividend_yield NUMERIC(10, 4),
    earnings_date TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index pour filtrage rapide
CREATE INDEX IF NOT EXISTS idx_equities_sector ON equities_fundamentals(sector);
CREATE INDEX IF NOT EXISTS idx_equities_market_cap ON equities_fundamentals(market_cap);
CREATE INDEX IF NOT EXISTS idx_equities_pe_ratio ON equities_fundamentals(pe_ratio);
CREATE INDEX IF NOT EXISTS idx_equities_updated_at ON equities_fundamentals(updated_at);

-- Commentaire pour documentation
COMMENT ON TABLE equities_fundamentals IS 'Fundamentals data for S&P 500 + NASDAQ 100 scraped via yfinance';
