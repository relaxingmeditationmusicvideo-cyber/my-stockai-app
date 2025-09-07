# main.py - Improved FastAPI Backend
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import yfinance as yf
import pandas as pd
import numpy as np
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import ta
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
import os
from io import StringIO
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./stocks.db")
REDIS_URL = os.getenv("REDIS_URL")

# Handle SQLite vs PostgreSQL
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis (optional for caching)
redis_client = None
try:
    if REDIS_URL:
        import redis
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        redis_client.ping()  # Test connection
        logger.info("Redis connected successfully")
except Exception as e:
    logger.warning(f"Redis not available: {e}")
    redis_client = None

# FastAPI app
app = FastAPI(
    title="Indian Stock Screener API", 
    version="2.0.0",
    description="Professional stock screening platform for Indian markets"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Models
class Stock(Base):
    __tablename__ = "stocks"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, index=True)
    company_name = Column(String(200))
    sector = Column(String(100))
    exchange = Column(String(10))
    market_cap = Column(Float)
    last_updated = Column(DateTime, default=datetime.now)

class Watchlist(Base):
    __tablename__ = "watchlists"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), index=True, default="default")
    name = Column(String(100))
    symbols = Column(Text)  # JSON string
    created_at = Column(DateTime, default=datetime.now)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic models
class ScreenerRequest(BaseModel):
    criteria: Dict
    limit: Optional[int] = 30

class WatchlistCreate(BaseModel):
    name: str
    symbols: List[str]

class StockResponse(BaseModel):
    symbol: str
    price: float
    change_percent: float
    volume: int
    technical_indicators: Dict

# Indian Stock Symbols (Top NSE stocks)
NSE_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "HINDUNILVR.NS",
    "ICICIBANK.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS", "ITC.NS",
    "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS", "BAJFINANCE.NS",
    "HCLTECH.NS", "WIPRO.NS", "ULTRACEMCO.NS", "TITAN.NS", "SUNPHARMA.NS",
    "NESTLEIND.NS", "POWERGRID.NS", "NTPC.NS", "TATAMOTORS.NS", "ONGC.NS",
    "M&M.NS", "TECHM.NS", "JSWSTEEL.NS", "DRREDDY.NS", "INDUSINDBK.NS",
    "COALINDIA.NS", "DIVISLAB.NS", "ADANIENT.NS", "HEROMOTOCO.NS", "BRITANNIA.NS"
]

# Utility Functions
def get_cached_data(key: str):
    """Get data from cache"""
    if not redis_client:
        return None
    try:
        data = redis_client.get(key)
        return json.loads(data) if data else None
    except Exception as e:
        logger.error(f"Cache get error: {e}")
        return None

def cache_data(key: str, data: dict, expiry: int = 300):
    """Cache data with expiry"""
    if not redis_client:
        return
    try:
        redis_client.setex(key, expiry, json.dumps(data, default=str))
    except Exception as e:
        logger.error(f"Cache set error: {e}")

def get_indian_stock_data(symbol: str, period: str = "3mo"):
    """Fetch Indian stock data with caching"""
    cache_key = f"stock_data:{symbol}:{period}"
    cached = get_cached_data(cache_key)
    
    if cached:
        logger.info(f"Cache hit for {symbol}")
        df = pd.DataFrame(cached)
        df.index = pd.to_datetime(df.index)
        return df
    
    try:
        # Ensure NSE suffix
        if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
            symbol += '.NS'
            
        logger.info(f"Fetching fresh data for {symbol}")
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)
        
        if data.empty:
            # Try BSE suffix if NSE fails
            symbol_bse = symbol.replace('.NS', '.BO')
            ticker = yf.Ticker(symbol_bse)
            data = ticker.history(period=period)
        
        # Cache for 5 minutes
        if not data.empty:
            cache_data(cache_key, data.reset_index().to_dict('records'), 300)
        
        return data
        
    except Exception as e:
        logger.error(f"Error fetching {symbol}: {str(e)}")
        return pd.DataFrame()

def calculate_technical_indicators(data: pd.DataFrame):
    """Calculate comprehensive technical indicators"""
    if data.empty or len(data) < 20:
        return {}
    
    try:
        indicators = {}
        
        # RSI
        indicators['RSI'] = float(ta.momentum.RSIIndicator(data['Close'], window=14).rsi().iloc[-1])
        
        # MACD
        macd_indicator = ta.trend.MACD(data['Close'])
        indicators['MACD'] = float(macd_indicator.macd().iloc[-1])
        indicators['MACD_Signal'] = float(macd_indicator.macd_signal().iloc[-1])
        indicators['MACD_Histogram'] = float(macd_indicator.macd_diff().iloc[-1])
        
        # Bollinger Bands
        bb = ta.volatility.BollingerBands(data['Close'], window=20)
        indicators['BB_Upper'] = float(bb.bollinger_hband().iloc[-1])
        indicators['BB_Lower'] = float(bb.bollinger_lband().iloc[-1])
        indicators['BB_Middle'] = float(bb.bollinger_mavg().iloc[-1])
        
        # Moving Averages
        indicators['SMA_20'] = float(ta.trend.SMAIndicator(data['Close'], window=20).sma_indicator().iloc[-1])
        indicators['SMA_50'] = float(ta.trend.SMAIndicator(data['Close'], window=50).sma_indicator().iloc[-1]) if len(data) >= 50 else None
        indicators['EMA_12'] = float(ta.trend.EMAIndicator(data['Close'], window=12).ema_indicator().iloc[-1])
        indicators['EMA_26'] = float(ta.trend.EMAIndicator(data['Close'], window=26).ema_indicator().iloc[-1])
        
        # ADX (Average Directional Index)
        if len(data) >= 14:
            indicators['ADX'] = float(ta.trend.ADXIndicator(data['High'], data['Low'], data['Close']).adx().iloc[-1])
        
        # Volume indicators
        if len(data) >= 20:
            vol_sma = ta.volume.VolumeSMAIndicator(data['Close'], data['Volume'], window=20)
            indicators['Volume_SMA'] = float(vol_sma.volume_sma().iloc[-1])
        
        # Clean NaN values
        cleaned_indicators = {k: v for k, v in indicators.items() if v is not None and not pd.isna(v)}
        
        return cleaned_indicators
        
    except Exception as e:
        logger.error(f"Error calculating indicators: {str(e)}")
        return {}

def calculate_stock_score(indicators: dict, latest_data: dict) -> float:
    """Calculate a composite score for stock ranking"""
    score = 0
    
    try:
        # RSI score (prefer 40-60 range, bonus for oversold)
        rsi = indicators.get('RSI', 50)
        if 40 <= rsi <= 60:
            score += 15
        elif rsi < 30:
            score += 20  # Oversold - potential opportunity
        elif 30 <= rsi <= 40:
            score += 10
        
        # MACD bullish signal
        if indicators.get('MACD', 0) > indicators.get('MACD_Signal', 0):
            score += 15
        
        # Price vs Moving Averages
        price = latest_data.get('Close', 0)
        sma_20 = indicators.get('SMA_20', 0)
        if price > sma_20 and sma_20 > 0:
            score += 10
        
        # ADX trend strength
        adx = indicators.get('ADX', 0)
        if adx > 25:
            score += 10
        elif adx > 20:
            score += 5
        
        # Volume above average
        volume = latest_data.get('Volume', 0)
        vol_sma = indicators.get('Volume_SMA', 0)
        if volume > vol_sma * 1.2 and vol_sma > 0:  # 20% above average
            score += 10
        
        return float(score)
        
    except Exception as e:
        logger.error(f"Error calculating score: {str(e)}")
        return 0.0

# API Endpoints
@app.get("/")
async def root():
    return {
        "message": "Indian Stock Screener API v2.0", 
        "status": "running",
        "features": ["Technical Screening", "Watchlists", "Real-time Data", "Export"],
        "data_source": "Yahoo Finance (15min delayed)"
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "redis_connected": redis_client is not None,
        "database": "connected"
    }

@app.get("/api/stocks/list")
async def get_stock_list():
    """Get list of available NSE stocks"""
    return {
        "stocks": [
            {
                "symbol": symbol.replace('.NS', ''), 
                "full_symbol": symbol,
                "exchange": "NSE"
            } 
            for symbol in NSE_STOCKS
        ],
        "count": len(NSE_STOCKS),
        "last_updated": datetime.now().isoformat()
    }

@app.get("/api/stock/{symbol}")
async def get_stock_data(symbol: str, period: str = "3mo"):
    """Get comprehensive stock data with technical indicators"""
    try:
        # Add .NS suffix if not present
        if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
            symbol += '.NS'
            
        data = get_indian_stock_data(symbol, period)
        
        if data.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
        
        # Calculate indicators
        indicators = calculate_technical_indicators(data.copy())
        
        # Get latest price data
        latest = data.iloc[-1]
        previous = data.iloc[-2] if len(data) > 1 else latest
        
        # Calculate price change
        price_change = float(latest['Close'] - previous['Close'])
        price_change_percent = float((price_change / previous['Close']) * 100) if previous['Close'] != 0 else 0
        
        # Calculate score
        score = calculate_stock_score(indicators, latest.to_dict())
        
        return {
            "symbol": symbol.replace('.NS', '').replace('.BO', ''),
            "full_symbol": symbol,
            "latest_price": float(latest['Close']),
            "change": price_change,
            "change_percent": price_change_percent,
            "volume": int(latest['Volume']),
            "high": float(latest['High']),
            "low": float(latest['Low']),
            "open": float(latest['Open']),
            "technical_indicators": indicators,
            "score": score,
            "last_updated": datetime.now().isoformat(),
            "data_points": len(data)
        }
        
    except Exception as e:
        logger.error(f"Error fetching stock data for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching stock data: {str(e)}")

@app.post("/api/screener/scan")
async def run_screener(request: ScreenerRequest):
    """Run advanced stock screener"""
    try:
        results = []
        criteria = request.criteria
        processed_count = 0
        
        logger.info(f"Starting screener with criteria: {criteria}")
        
        # Process stocks with limit
        stocks_to_process = NSE_STOCKS[:min(request.limit, 50)]  # Cap at 50 for performance
        
        for symbol in stocks_to_process:
            try:
                data = get_indian_stock_data(symbol, "3mo")
                processed_count += 1
                
                if data.empty or len(data) < 20:
                    continue
                
                indicators = calculate_technical_indicators(data.copy())
                latest = data.iloc[-1]
                previous = data.iloc[-2] if len(data) > 1 else latest
                
                # Calculate basic metrics
                price_change = float(latest['Close'] - previous['Close'])
                price_change_percent = float((price_change / previous['Close']) * 100) if previous['Close'] != 0 else 0
                
                # Apply screening criteria
                passes_screen = True
                
                # RSI filters
                rsi = indicators.get('RSI', 50)
                if 'rsi_min' in criteria and rsi < float(criteria['rsi_min']):
                    passes_screen = False
                if 'rsi_max' in criteria and rsi > float(criteria['rsi_max']):
                    passes_screen = False
                
                # Price above SMA filter
                if criteria.get('price_above_sma20', False):
                    sma_20 = indicators.get('SMA_20', 0)
                    if latest['Close'] <= sma_20:
                        passes_screen = False
                
                # Volume filter
                if 'min_volume' in criteria:
                    min_vol = float(criteria['min_volume'])
                    if latest['Volume'] < min_vol:
                        passes_screen = False
                
                # MACD bullish filter
                if criteria.get('macd_bullish', False):
                    macd = indicators.get('MACD', 0)
                    macd_signal = indicators.get('MACD_Signal', 0)
                    if macd <= macd_signal:
                        passes_screen = False
                
                if passes_screen:
                    score = calculate_stock_score(indicators, latest.to_dict())
                    
                    results.append({
                        "symbol": symbol.replace('.NS', ''),
                        "price": float(latest['Close']),
                        "change": price_change,
                        "change_percent": price_change_percent,
                        "volume": int(latest['Volume']),
                        "rsi": round(rsi, 2),
                        "macd": round(indicators.get('MACD', 0), 4),
                        "sma_20": round(indicators.get('SMA_20', 0), 2),
                        "adx": round(indicators.get('ADX', 0), 2),
                        "score": round(score, 1),
                        "last_updated": datetime.now().isoformat()
                    })
                
            except Exception as e:
                logger.error(f"Error processing {symbol}: {str(e)}")
                continue
        
        # Sort by score descending
        results.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        logger.info(f"Screener completed: {len(results)} matches from {processed_count} stocks")
        
        return {
            "results": results,
            "total_scanned": processed_count,
            "total_available": len(NSE_STOCKS),
            "matches": len(results),
            "criteria": criteria,
            "timestamp": datetime.now().isoformat(),
            "execution_summary": f"Found {len(results)} stocks matching criteria"
        }
        
    except Exception as e:
        logger.error(f"Screening error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Screening error: {str(e)}")

@app.get("/api/stock/{symbol}/chart")
async def get_chart_data(symbol: str, period: str = "6mo"):
    """Get OHLCV data for charting"""
    try:
        if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
            symbol += '.NS'
            
        data = get_indian_stock_data(symbol, period)
        
        if data.empty:
            raise HTTPException(status_code=404, detail="Chart data not found")
        
        # Format for chart libraries
        chart_data = []
        for index, row in data.iterrows():
            chart_data.append({
                "time": int(index.timestamp() * 1000),  # Milliseconds for JS
                "open": float(row['Open']),
                "high": float(row['High']),
                "low": float(row['Low']),
                "close": float(row['Close']),
                "volume": int(row['Volume'])
            })
        
        return {
            "symbol": symbol.replace('.NS', '').replace('.BO', ''),
            "data": chart_data,
            "period": period,
            "count": len(chart_data)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chart data error: {str(e)}")

# Watchlist Management
@app.post("/api/watchlist")
async def create_watchlist(watchlist: WatchlistCreate):
    """Create new watchlist"""
    db = SessionLocal()
    try:
        # Add .NS suffix to symbols if needed
        processed_symbols = []
        for sym in watchlist.symbols:
            if not sym.endswith('.NS') and not sym.endswith('.BO'):
                processed_symbols.append(sym + '.NS')
            else:
                processed_symbols.append(sym)
        
        db_watchlist = Watchlist(
            user_id="default",
            name=watchlist.name,
            symbols=json.dumps(processed_symbols),
            created_at=datetime.now()
        )
        db.add(db_watchlist)
        db.commit()
        db.refresh(db_watchlist)
        
        return {
            "id": db_watchlist.id,
            "message": f"Watchlist '{watchlist.name}' created successfully",
            "symbols_count": len(processed_symbols)
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating watchlist: {str(e)}")
    finally:
        db.close()

@app.get("/api/watchlists")
async def get_watchlists():
    """Get all watchlists"""
    db = SessionLocal()
    try:
        watchlists = db.query(Watchlist).filter(Watchlist.user_id == "default").all()
        
        result = []
        for w in watchlists:
            symbols = json.loads(w.symbols) if w.symbols else []
            result.append({
                "id": w.id,
                "name": w.name,
                "symbols": [s.replace('.NS', '').replace('.BO', '') for s in symbols],
                "symbols_count": len(symbols),
                "created_at": w.created_at.isoformat() if w.created_at else None
            })
        
        return {
            "watchlists": result,
            "count": len(result)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching watchlists: {str(e)}")
    finally:
        db.close()

@app.get("/api/export/csv")
async def export_screener_results(criteria: str = "{}"):
    """Export screening results to CSV"""
    try:
        # Parse and run screener
        criteria_dict = json.loads(criteria) if criteria != "{}" else {}
        
        # Limit to 30 stocks for export performance
        request = ScreenerRequest(criteria=criteria_dict, limit=30)
        screen_result = await run_screener(request)
        
        if not screen_result["results"]:
            raise HTTPException(status_code=404, detail="No results to export")
        
        # Convert to DataFrame for CSV
        df = pd.DataFrame(screen_result["results"])
        
        # Reorder columns for better readability
        columns_order = ['symbol', 'price', 'change_percent', 'volume', 'rsi', 'macd', 'sma_20', 'adx', 'score']
        df = df[columns_order]
        
        # Create CSV
        output = StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=stock_screener_results_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)