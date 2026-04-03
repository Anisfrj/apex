"""
Module Equity Screener — Scraping S&P 500 + NASDAQ 100 via yfinance
"""
import yfinance as yf
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
import asyncio
from ..core.database import get_db_connection

def get_sp500_tickers() -> List[str]:
    """Récupère S&P 500 depuis Wikipedia"""
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
                tables = pd.read_html(url, storage_options={'User-Agent': 'Mozilla/5.0'})
    except Exception as e:
        print(f"Erreur scraping S&P 500: {e}")
        return []

def get_nasdaq100_tickers() -> List[str]:
    """Récupère NASDAQ 100 depuis Wikipedia"""
    try:
        url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
        tables = pd.read_html(url, storage_options={'User-Agent': 'Mozilla/5.0'})        # Index peut varier, chercher table avec colonne "Ticker"
    except Exception as e:
        print(f"Erreur scraping NASDAQ 100: {e}")
        return []

def scrape_ticker_fundamentals(symbol: str) -> Optional[Dict]:
    """
    Scrape fondamentaux d'un ticker via yfinance
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Si pas de données (delisted/erreur), skip
        if not info or 'currentPrice' not in info:
            return None
        
        data = {
            'symbol': symbol,
            'company_name': info.get('longName'),
            'sector': info.get('sector'),
            'industry': info.get('industry'),
            'market_cap': info.get('marketCap'),
            'price': info.get('currentPrice'),
            'pe_ratio': info.get('trailingPE'),
            'pb_ratio': info.get('priceToBook'),
            'ps_ratio': info.get('priceToSalesTrailing12Months'),
            'peg_ratio': info.get('pegRatio'),
            'roe': info.get('returnOnEquity'),
            'profit_margin': info.get('profitMargins'),
            'revenue_growth': info.get('revenueGrowth'),
            'earnings_growth': info.get('earningsGrowth'),
            'debt_to_equity': info.get('debtToEquity'),
            'sma_50': info.get('fiftyDayAverage'),
            'sma_200': info.get('twoHundredDayAverage'),
            'volume': info.get('volume'),
            'avg_volume': info.get('averageVolume'),
            'beta': info.get('beta'),
            'dividend_yield': info.get('dividendYield'),
            'earnings_date': None,  # Timestamp, peut être None
            'updated_at': datetime.now()
        }
        
        # Convertir earnings timestamp si existe
        if 'earningsTimestamp' in info and info['earningsTimestamp']:
            try:
                data['earnings_date'] = datetime.fromtimestamp(info['earningsTimestamp'])
            except:
                pass
        
        return data
    except Exception as e:
        print(f"Erreur scraping {symbol}: {e}")
        return None

async def upsert_equity_fundamental(data: Dict):
    """Upsert dans PostgreSQL"""
    conn = get_db_connection()
    try:
        await conn.execute("""
            INSERT INTO equities_fundamentals (
                symbol, company_name, sector, industry, market_cap, price,
                pe_ratio, pb_ratio, ps_ratio, peg_ratio, roe, profit_margin,
                revenue_growth, earnings_growth, debt_to_equity,
                sma_50, sma_200, volume, avg_volume, beta, dividend_yield,
                earnings_date, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12,
                $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23
            )
            ON CONFLICT (symbol) DO UPDATE SET
                company_name = EXCLUDED.company_name,
                sector = EXCLUDED.sector,
                industry = EXCLUDED.industry,
                market_cap = EXCLUDED.market_cap,
                price = EXCLUDED.price,
                pe_ratio = EXCLUDED.pe_ratio,
                pb_ratio = EXCLUDED.pb_ratio,
                ps_ratio = EXCLUDED.ps_ratio,
                peg_ratio = EXCLUDED.peg_ratio,
                roe = EXCLUDED.roe,
                profit_margin = EXCLUDED.profit_margin,
                revenue_growth = EXCLUDED.revenue_growth,
                earnings_growth = EXCLUDED.earnings_growth,
                debt_to_equity = EXCLUDED.debt_to_equity,
                sma_50 = EXCLUDED.sma_50,
                sma_200 = EXCLUDED.sma_200,
                volume = EXCLUDED.volume,
                avg_volume = EXCLUDED.avg_volume,
                beta = EXCLUDED.beta,
                dividend_yield = EXCLUDED.dividend_yield,
                earnings_date = EXCLUDED.earnings_date,
                updated_at = EXCLUDED.updated_at
        """, *data.values())
    finally:
        await conn.close()

async def sync_equities_screener():
    """
    Task Celery principale : scrape S&P 500 + NASDAQ 100
    """
    print("🔄 Sync Equity Screener — Start")
    
    tickers = list(set(get_sp500_tickers() + get_nasdaq100_tickers()))
    print(f"📊 {len(tickers)} tickers à scraper")
    
    success_count = 0
    for i, symbol in enumerate(tickers):
        if i % 50 == 0:
            print(f"Progress: {i}/{len(tickers)}")
        
        data = scrape_ticker_fundamentals(symbol)
        if data:
            await upsert_equity_fundamental(data)
            success_count += 1
        
        # Rate limit gentil : 0.1s entre chaque requête
        await asyncio.sleep(0.1)
    
    print(f"✅ Equity Screener sync terminé: {success_count}/{len(tickers)} réussis")
    return success_count
