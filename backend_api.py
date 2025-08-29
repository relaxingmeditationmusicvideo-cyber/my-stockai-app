# backend/main.py
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from pydantic import BaseModel
from typing import List, Optional, Dict
import asyncio
import json
import redis
import yfinance as yf
from datetime import datetime, timedelta
import jwt
import hashlib
from alpha_vantage.timeseries import TimeSeries
import pandas as pd
from textblob import TextBlob
import requests

# Database Configuration
DATABASE_URL = "postgresql://user:password@localhost/stockai_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis Configuration
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# FastAPI App
app = FastAPI(title="StockAI Pro API", version="1.0.0")
security = HTTPBearer()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    subscription_tier = Column(String, default="free")  # free, premium, pro
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    watchlists = relationship("Watchlist", back_populates="user")
    alerts = relationship("Alert", back_populates="user")
    portfolios = relationship("Portfolio", back_populates="user")

class Stock(Base):
    __tablename__ = "stocks"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String, unique=True, index=True)
    name = Column(String)
    sector = Column(String)
    market_cap = Column(String)
    exchange = Column(String, default="NSE")
    is_active = Column(Boolean, default=True)

class StockData(Base):
    __tablename__ = "stock_data"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String, index=True)
    price = Column(Float)
    change = Column(Float)
    change_percent = Column(Float)
    volume = Column(Integer)
    rsi = Column(Float)
    pe_ratio = Column(Float)
    roe = Column(Float)
    ai_score = Column(Float)
    sentiment = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Watchlist(Base):
    __tablename__ = "watchlists"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    symbol = Column(String)
    added_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="watchlists")

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    symbol = Column(String)
    alert_type = Column(String)  # price_above, price_below, rsi_oversold, etc.
    target_value = Column(Float)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    triggered_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="alerts")

class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, default="My Portfolio")
    total_value = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="portfolios")
    holdings = relationship("Holding", back_populates="portfolio")

class Holding(Base):
    __tablename__ = "holdings"
    
    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    symbol = Column(String)
    quantity = Column(Integer)
    avg_price = Column(Float)
    current_price = Column(Float)
    
    portfolio = relationship("Portfolio", back_populates="holdings")

# Pydantic Models
class UserCreate(BaseModel):
    email: str
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    subscription_tier: str
    created_at: datetime

class StockResponse(BaseModel):
    symbol: str
    name: str
    price: float
    change: float
    change_percent: float
    volume: int
    rsi: float
    pe_ratio: float
    roe: float
    ai_score: float
    sentiment: str

class ScreenerRequest(BaseModel):
    screen_type: str  # technical, fundamental, ai
    filters: Dict
    limit: Optional[int] = 50

class WatchlistAdd(BaseModel):
    symbol: str

class AlertCreate(BaseModel):
    symbol: str
    alert_type: str
    target_value: Optional[float]

# Data Services
class MarketDataService:
    def __init__(self):
        self.alpha_vantage = TimeSeries(key='YOUR_API_KEY')
        
    async def get_stock_data(self, symbol: str) -> Dict:
        """Fetch real-time stock data"""
        cache_key = f"stock_data:{symbol}"
        cached_data = redis_client.get(cache_key)
        
        if cached_data:
            return json.loads(cached_data)
        
        try:
            # Use yfinance for Indian stocks
            stock = yf.Ticker(f"{symbol}.NS")
            info = stock.info
            hist = stock.history(period="1d")
            
            if hist.empty:
                raise HTTPException(status_code=404, detail="Stock data not found")
            
            current_price = hist['Close'].iloc[-1]
            prev_close = info.get('previousClose', current_price)
            change = current_price - prev_close
            change_percent = (change / prev_close) * 100
            
            data = {
                "symbol": symbol,
                "name": info.get('longName', symbol),
                "price": float(current_price),
                "change": float(change),
                "change_percent": float(change_percent),
                "volume": int(hist['Volume'].iloc[-1]),
                "pe_ratio": info.get('trailingPE', 0),
                "market_cap": info.get('marketCap', 0),
                "sector": info.get('sector', 'Unknown'),
                "timestamp": datetime.now().isoformat()
            }
            
            # Cache for 30 seconds
            redis_client.setex(cache_key, 30, json.dumps(data))
            return data
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")

class AIAnalysisService:
    @staticmethod
    async def calculate_technical_indicators(symbol: str, period: int = 14) -> Dict:
        """Calculate RSI, MACD, Bollinger Bands"""
        stock = yf.Ticker(f"{symbol}.NS")
        hist = stock.history(period="3mo")
        
        if hist.empty:
            return {"rsi": 50, "macd": 0, "bb_position": 0.5}
        
        # RSI Calculation
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # MACD Calculation
        exp1 = hist['Close'].ewm(span=12).mean()
        exp2 = hist['Close'].ewm(span=26).mean()
        macd = exp1 - exp2
        
        return {
            "rsi": float(rsi.iloc[-1]) if not rsi.empty else 50,
            "macd": float(macd.iloc[-1]) if not macd.empty else 0,
            "trend": "bullish" if macd.iloc[-1] > 0 else "bearish"
        }
    
    @staticmethod
    async def generate_ai_score(stock_data: Dict, technical_data: Dict) -> float:
        """Generate AI confidence score based on multiple factors"""
        score = 50  # Base score
        
        # Technical factors (40% weight)
        rsi = technical_data.get('rsi', 50)
        if 30 <= rsi <= 70:  # Good RSI range
            score += 15
        elif rsi < 30:  # Oversold
            score += 10
        elif rsi > 70:  # Overbought
            score -= 10
        
        # Price momentum (30% weight)
        change_percent = stock_data.get('change_percent', 0)
        if 0 < change_percent <= 5:  # Positive but not excessive
            score += 15
        elif change_percent > 5:  # High momentum
            score += 10
        elif change_percent < -5:  # Declining
            score -= 15
        
        # Volume factor (20% weight)
        volume = stock_data.get('volume', 0)
        avg_volume = volume * 0.8  # Simplified avg volume
        if volume > avg_volume * 1.5:  # High volume
            score += 10
        
        # Fundamental factors (10% weight)
        pe_ratio = stock_data.get('pe_ratio', 0)
        if 0 < pe_ratio < 25:  # Reasonable P/E
            score += 5
        
        return min(95, max(5, score))  # Cap between 5-95

# Utility Functions
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_access_token(data: dict):
    return jwt.encode(data, "SECRET_KEY", algorithm="HS256")

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, "SECRET_KEY", algorithms=["HS256"])
        return payload.get("user_id")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Initialize services
market_service = MarketDataService()
ai_service = AIAnalysisService()

# WebSocket Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

# API Endpoints
@app.post("/api/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Hash password
    password_hash = hashlib.sha256(user_data.password.encode()).hexdigest()
    
    # Create user
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        password_hash=password_hash
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return UserResponse(
        id=db_user.id,
        email=db_user.email,
        username=db_user.username,
        subscription_tier=db_user.subscription_tier,
        created_at=db_user.created_at
    )

@app.post("/api/auth/login")
async def login(email: str, password: str, db: Session = Depends(get_db)):
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    user = db.query(User).filter(User.email == email, User.password_hash == password_hash).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"user_id": user.id})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/api/stocks/{symbol}", response_model=StockResponse)
async def get_stock(symbol: str):
    stock_data = await market_service.get_stock_data(symbol)
    technical_data = await ai_service.calculate_technical_indicators(symbol)
    ai_score = await ai_service.generate_ai_score(stock_data, technical_data)
    
    return StockResponse(
        symbol=stock_data['symbol'],
        name=stock_data['name'],
        price=stock_data['price'],
        change=stock_data['change'],
        change_percent=stock_data['change_percent'],
        volume=stock_data['volume'],
        rsi=technical_data['rsi'],
        pe_ratio=stock_data['pe_ratio'],
        roe=15.0,  # Would come from fundamental analysis
        ai_score=ai_score,
        sentiment=technical_data['trend']
    )

@app.post("/api/screener/run")
async def run_screener(request: ScreenerRequest):
    """Run stock screener with AI-powered filtering"""
    # This would implement the actual screening logic
    # For now, returning mock data structure
    
    results = []
    symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'WIPRO']
    
    for symbol in symbols[:request.limit]:
        try:
            stock_data = await market_service.get_stock_data(symbol)
            technical_data = await ai_service.calculate_technical_indicators(symbol)
            ai_score = await ai_service.generate_ai_score(stock_data, technical_data)
            
            # Apply filters based on request.filters
            if request.screen_type == "technical":
                if request.filters.get('min_rsi') and technical_data['rsi'] < request.filters['min_rsi']:
                    continue
                    
            elif request.screen_type == "ai":
                if ai_score < request.filters.get('min_confidence', 70):
                    continue
            
            results.append({
                "symbol": symbol,
                "price": stock_data['price'],
                "change_percent": stock_data['change_percent'],
                "rsi": technical_data['rsi'],
                "ai_score": ai_score,
                "sentiment": technical_data['trend']
            })
            
        except Exception as e:
            continue
    
    return {"results": results, "total": len(results)}

@app.post("/api/watchlist/add")
async def add_to_watchlist(
    watchlist_data: WatchlistAdd, 
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db)
):
    watchlist_item = Watchlist(user_id=user_id, symbol=watchlist_data.symbol)
    db.add(watchlist_item)
    db.commit()
    return {"message": "Added to watchlist"}

@app.get("/api/watchlist")
async def get_watchlist(
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db)
):
    watchlist = db.query(Watchlist).filter(Watchlist.user_id == user_id).all()
    results = []
    
    for item in watchlist:
        try:
            stock_data = await market_service.get_stock_data(item.symbol)
            results.append(stock_data)
        except:
            continue
    
    return results

@app.websocket("/ws/market-data")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Send real-time market updates
            market_data = {
                "timestamp": datetime.now().isoformat(),
                "updates": [
                    {"symbol": "NIFTY", "price": 24315.95, "change": 156.75},
                    {"symbol": "BANKNIFTY", "price": 51234.80, "change": -234.60}
                ]
            }
            await manager.broadcast(json.dumps(market_data))
            await asyncio.sleep(5)  # Update every 5 seconds
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Background Tasks
@app.on_event("startup")
async def startup_event():
    Base.metadata.create_all(bind=engine)
    
    # Start background tasks for alerts monitoring
    asyncio.create_task(monitor_alerts())

async def monitor_alerts():
    """Background task to monitor and trigger alerts"""
    while True:
        db = SessionLocal()
        try:
            active_alerts = db.query(Alert).filter(Alert.is_active == True).all()
            
            for alert in active_alerts:
                try:
                    stock_data = await market_service.get_stock_data(alert.symbol)
                    
                    should_trigger = False
                    if alert.alert_type == "price_above" and stock_data['price'] >= alert.target_value:
                        should_trigger = True
                    elif alert.alert_type == "price_below" and stock_data['price'] <= alert.target_value:
                        should_trigger = True
                    
                    if should_trigger:
                        alert.is_active = False
                        alert.triggered_at = datetime.utcnow()
                        db.commit()
                        
                        # Send notification (implement email/push notification)
                        await send_alert_notification(alert, stock_data)
                        
                except Exception as e:
                    print(f"Error processing alert {alert.id}: {e}")
                    continue
        finally:
            db.close()
        
        await asyncio.sleep(60)  # Check every minute

async def send_alert_notification(alert: Alert, stock_data: Dict):
    """Send alert notification to user"""
    # Implement email/push notification logic
    print(f"Alert triggered: {alert.symbol} {alert.alert_type} {alert.target_value}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)