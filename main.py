# main.py - FastAPI Backend
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import yfinance as yf
import pandas as pd
import numpy as np
import redis
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import ta
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
import os
from io import StringIO
import logging

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/stockdb")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# FastAPI app
app = FastAPI(title="Stock Screener API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
except:
    redis_client = None
    logging.warning("Redis not available - caching disabled")

# Models
class Stock(Base):
    __tablename__ = "stocks"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True)
    company_name = Column(String)
    sector = Column(String)
    exchange = Column(String)
    market_cap = Column(Float)
    last_updated = Column(DateTime)

class Watchlist(Base):
    __tablename__ = "watchlists"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    name = Column(String)
    symbols = Column(String)  # JSON string
    created_at = Column(DateTime)

Base.metadata.create_all(bind=engine)

# Pydantic models
class ScreenerRequest(BaseModel):
    criteria: Dict
    limit: Optional[int] = 50

class WatchlistCreate(BaseModel):
    name: str
    symbols: List[str]

class TechnicalIndicators(BaseModel):
    symbol: str
    period: str = "1y"
    
# Indian Stock Symbols - Major NSE stocks
NSE_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "HINDUNILVR.NS",
    "ICICIBANK.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS", "ITC.NS",
    "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS", "BAJFINANCE.NS",
    "HCLTECH.NS", "WIPRO.NS", "ULTRACEMCO.NS", "TITAN.NS", "SUNPHARMA.NS",
    "NESTLEIND.NS", "POWERGRID.NS", "NTPC.NS", "TATAMOTORS.NS", "ONGC.NS",
    "M&M.NS", "TECHM.NS", "JSWSTEEL.NS", "DRREDDY.NS", "INDUSINDBK.NS"
]

# Utility Functions
def get_cached_data(key: str):
    """Get data from Redis cache"""
    if not redis_client:
        return None
    try:
        data = redis_client.get(key)
        return json.loads(data) if data else None
    except:
        return None

def cache_data(key: str, data: dict, expiry: int = 300):
    """Cache data in Redis with expiry"""
    if not redis_client:
        return
    try:
        redis_client.setex(key, expiry, json.dumps(data))
    except:
        pass

def get_indian_stock_data(symbol: str, period: str = "1y"):
    """Fetch Indian stock data from Yahoo Finance"""
    cache_key = f"stock_data:{symbol}:{period}"
    cached = get_cached_data(cache_key)
    
    if cached:
        return pd.DataFrame(cached)
    
    try:
        # Ensure NSE suffix
        if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
            symbol += '.NS'
            
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)
        
        if data.empty:
            # Try BSE suffix if NSE fails
            symbol_bse = symbol.replace('.NS', '.BO')
            ticker = yf.Ticker(symbol_bse)
            data = ticker.history(period=period)
        
        # Cache for 5 minutes (300 seconds)
        if not data.empty:
            cache_data(cache_key, data.to_dict('records'), 300)
        
        return data
    except Exception as e:
        logging.error(f"Error fetching {symbol}: {str(e)}")
        return pd.DataFrame()

def calculate_technical_indicators(data: pd.DataFrame):
    """Calculate technical indicators"""
    if data.empty:
        return {}
    
    try:
        # RSI
        data['RSI'] = ta.momentum.RSIIndicator(data['Close']).rsi()
        
        # MACD
        macd = ta.trend.MACD(data['Close'])
        data['MACD'] = macd.macd()
        data['MACD_Signal'] = macd.macd_signal()
        data['MACD_Histogram'] = macd.macd_diff()
        
        # Bollinger Bands
        bb = ta.volatility.BollingerBands(data['Close'])
        data['BB_Upper'] = bb.bollinger_hband()
        data['BB_Lower'] = bb.bollinger_lband()
        data['BB_Middle'] = bb.bollinger_mavg()
        
        # Moving Averages
        data['SMA_20'] = ta.trend.SMAIndicator(data['Close'], window=20).sma_indicator()
        data['SMA_50'] = ta.trend.SMAIndicator(data['Close'], window=50).sma_indicator()
        data['EMA_12'] = ta.trend.EMAIndicator(data['Close'], window=12).ema_indicator()
        data['EMA_26'] = ta.trend.EMAIndicator(data['Close'], window=26).ema_indicator()
        
        # ADX
        data['ADX'] = ta.trend.ADXIndicator(data['High'], data['Low'], data['Close']).adx()
        
        # Volume indicators
        data['Volume_SMA'] = ta.volume.VolumeSMAIndicator(
            data['Close'], data['Volume'], window=20
        ).volume_sma()
        
        # Ichimoku
        ichimoku = ta.trend.IchimokuIndicator(data['High'], data['Low'])
        data['Ichimoku_A'] = ichimoku.ichimoku_a()
        data['Ichimoku_B'] = ichimoku.ichimoku_b()
        
        return data.tail(1).to_dict('records')[0] if not data.empty else {}
        
    except Exception as e:
        logging.error(f"Error calculating indicators: {str(e)}")
        return {}

# API Endpoints
@app.get("/")
async def root():
    return {"message": "Stock Screener API v1.0", "status": "running"}

@app.get("/api/stocks/list")
async def get_stock_list():
    """Get list of available NSE stocks"""
    return {
        "stocks": [
            {"symbol": symbol, "exchange": "NSE"} 
            for symbol in NSE_STOCKS
        ],
        "count": len(NSE_STOCKS)
    }

@app.get("/api/stock/{symbol}")
async def get_stock_data(symbol: str, period: str = "1y"):
    """Get stock data with technical indicators"""
    try:
        data = get_indian_stock_data(symbol, period)
        
        if data.empty:
            raise HTTPException(status_code=404, detail="Stock data not found")
        
        indicators = calculate_technical_indicators(data.copy())
        
        # Latest price data
        latest = data.tail(1).iloc[0]
        
        return {
            "symbol": symbol,
            "latest_price": float(latest['Close']),
            "change": float(latest['Close'] - data['Close'].iloc[-2]) if len(data) > 1 else 0,
            "change_percent": float(((latest['Close'] - data['Close'].iloc[-2]) / data['Close'].iloc[-2]) * 100) if len(data) > 1 else 0,
            "volume": int(latest['Volume']),
            "high": float(latest['High']),
            "low": float(latest['Low']),
            "technical_indicators": indicators,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stock data: {str(e)}")

@app.post("/api/screener/scan")
async def run_screener(request: ScreenerRequest):
    """Run stock screener with technical criteria"""
    try:
        results = []
        criteria = request.criteria
        
        # Process stocks in batches for better performance
        for symbol in NSE_STOCKS[:request.limit]:
            try:
                data = get_indian_stock_data(symbol, "3mo")  # 3 months for faster processing
                
                if data.empty:
                    continue
                    
                indicators = calculate_technical_indicators(data.copy())
                latest = data.tail(1).iloc[0]
                
                # Apply screening criteria
                passes_screen = True
                
                # RSI filter
                if 'rsi_min' in criteria and indicators.get('RSI', 0) < criteria['rsi_min']:
                    passes_screen = False
                if 'rsi_max' in criteria and indicators.get('RSI', 100) > criteria['rsi_max']:
                    passes_screen = False
                
                # Price above SMA
                if 'price_above_sma20' in criteria and criteria['price_above_sma20']:
                    if latest['Close'] <= indicators.get('SMA_20', 0):
                        passes_screen = False
                
                # Volume filter
                if 'min_volume' in criteria and latest['Volume'] < criteria['min_volume']:
                    passes_screen = False
                
                # MACD filter
                if 'macd_bullish' in criteria and criteria['macd_bullish']:
                    if indicators.get('MACD', 0) <= indicators.get('MACD_Signal', 0):
                        passes_screen = False
                
                if passes_screen:
                    results.append({
                        "symbol": symbol,
                        "price": float(latest['Close']),
                        "change_percent": float(((latest['Close'] - data['Close'].iloc[-2]) / data['Close'].iloc[-2]) * 100) if len(data) > 1 else 0,
                        "volume": int(latest['Volume']),
                        "rsi": indicators.get('RSI'),
                        "macd": indicators.get('MACD'),
                        "sma_20": indicators.get('SMA_20'),
                        "score": calculate_score(indicators)  # Custom scoring
                    })
                    
            except Exception as e:
                logging.error(f"Error processing {symbol}: {str(e)}")
                continue
        
        # Sort by score
        results.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return {
            "results": results,
            "total_scanned": len(NSE_STOCKS),
            "matches": len(results),
            "criteria": criteria,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Screening error: {str(e)}")

def calculate_score(indicators: dict) -> float:
    """Calculate a technical score for ranking"""
    score = 0
    
    # RSI score (prefer 30-70 range)
    rsi = indicators.get('RSI', 50)
    if 30 <= rsi <= 70:
        score += 10
    elif rsi < 30:
        score += 5  # Oversold - potential buy
    
    # MACD bullish
    if indicators.get('MACD', 0) > indicators.get('MACD_Signal', 0):
        score += 15
    
    # ADX strength
    adx = indicators.get('ADX', 0)
    if adx > 25:
        score += 10
    
    return score

@app.get("/api/stock/{symbol}/chart")
async def get_chart_data(symbol: str, period: str = "6mo"):
    """Get chart data for TradingView or custom charts"""
    try:
        data = get_indian_stock_data(symbol, period)
        
        if data.empty:
            raise HTTPException(status_code=404, detail="Chart data not found")
        
        # Format for chart consumption
        chart_data = []
        for index, row in data.iterrows():
            chart_data.append({
                "time": int(index.timestamp()),
                "open": float(row['Open']),
                "high": float(row['High']),
                "low": float(row['Low']),
                "close": float(row['Close']),
                "volume": int(row['Volume'])
            })
        
        return {
            "symbol": symbol,
            "data": chart_data,
            "period": period
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chart data error: {str(e)}")

# Watchlist endpoints
@app.post("/api/watchlist")
async def create_watchlist(watchlist: WatchlistCreate):
    """Create a new watchlist"""
    db = SessionLocal()
    try:
        db_watchlist = Watchlist(
            user_id="default",  # For now, use default user
            name=watchlist.name,
            symbols=json.dumps(watchlist.symbols),
            created_at=datetime.now()
        )
        db.add(db_watchlist)
        db.commit()
        db.refresh(db_watchlist)
        
        return {"id": db_watchlist.id, "message": "Watchlist created"}
        
    finally:
        db.close()

@app.get("/api/watchlists")
async def get_watchlists():
    """Get all watchlists"""
    db = SessionLocal()
    try:
        watchlists = db.query(Watchlist).filter(Watchlist.user_id == "default").all()
        return [
            {
                "id": w.id,
                "name": w.name,
                "symbols": json.loads(w.symbols),
                "created_at": w.created_at
            } for w in watchlists
        ]
    finally:
        db.close()

@app.get("/api/export/csv")
async def export_screener_results(criteria: str = "{}"):
    """Export screener results to CSV"""
    try:
        # Parse criteria
        criteria_dict = json.loads(criteria)
        
        # Run screener
        results = []
        for symbol in NSE_STOCKS[:50]:  # Limit for export
            try:
                data = get_indian_stock_data(symbol, "1mo")
                if not data.empty:
                    latest = data.tail(1).iloc[0]
                    indicators = calculate_technical_indicators(data.copy())
                    
                    results.append({
                        "Symbol": symbol,
                        "Price": latest['Close'],
                        "Volume": latest['Volume'],
                        "RSI": indicators.get('RSI', 0),
                        "MACD": indicators.get('MACD', 0),
                        "SMA_20": indicators.get('SMA_20', 0),
                        "ADX": indicators.get('ADX', 0)
                    })
            except:
                continue
        
        # Convert to CSV
        df = pd.DataFrame(results)
        output = StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=screener_results.csv"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)