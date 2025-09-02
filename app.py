from flask import Flask, render_template, jsonify, request
import yfinance as yf
import os
import time
import random
from datetime import datetime, timedelta
import requests
from functools import lru_cache

app = Flask(__name__)

# Cache for storing data temporarily
cache = {}
CACHE_DURATION = 300  # 5 minutes

def get_cached_or_fetch(key, fetch_function):
    """Get data from cache or fetch new data"""
    current_time = time.time()
    
    if key in cache:
        data, timestamp = cache[key]
        if current_time - timestamp < CACHE_DURATION:
            return data
    
    # Add delay to avoid rate limiting
    time.sleep(random.uniform(0.5, 1.5))
    
    try:
        data = fetch_function()
        cache[key] = (data, current_time)
        return data
    except Exception as e:
        # Return cached data even if expired, if available
        if key in cache:
            return cache[key][0]
        raise e

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'Indian Stock Analytics Pro',
        'market': 'NSE/BSE',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/stock/<symbol>')
def get_stock_data(symbol):
    try:
        # Add .NS for NSE if not present
        if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
            symbol = symbol.upper() + '.NS'
        
        def fetch_stock_data():
            stock = yf.Ticker(symbol)
            
            # Try multiple approaches
            try:
                # First try: get recent history
                hist = stock.history(period='5d', interval='1d')
                if hist.empty:
                    hist = stock.history(period='1d', interval='1h')
                
                if hist.empty:
                    return None
                
                info = stock.info
                current_price = hist['Close'].iloc[-1]
                
                # Calculate change
                if len(hist) > 1:
                    previous_close = hist['Close'].iloc[-2]
                else:
                    previous_close = info.get('previousClose', current_price)
                
                change = current_price - previous_close
                change_percent = (change / previous_close) * 100 if previous_close != 0 else 0
                
                return {
                    'symbol': symbol,
                    'current_price': round(float(current_price), 2),
                    'change': round(float(change), 2),
                    'change_percent': round(float(change_percent), 2),
                    'volume': int(info.get('volume', 0)) if info.get('volume') else 0,
                    'company_name': info.get('longName', symbol.replace('.NS', '')),
                    'exchange': 'NSE' if symbol.endswith('.NS') else 'BSE'
                }
            except Exception as e:
                print(f"Error fetching {symbol}: {e}")
                return None
        
        data = get_cached_or_fetch(f"stock_{symbol}", fetch_stock_data)
        
        if data is None:
            return jsonify({'error': 'Stock data temporarily unavailable. Please try again.'}), 503
            
        return jsonify(data)
        
    except Exception as e:
        print(f"Stock API error: {e}")
        return jsonify({'error': 'Service temporarily unavailable'}), 503

@app.route('/api/nifty-indices')
def get_nifty_indices():
    try:
        def fetch_indices_data():
            indices = {
                '^NSEI': 'NIFTY 50',
                '^BSESN': 'SENSEX',
                '^NSEBANK': 'BANK NIFTY'
            }
            
            results = []
            for symbol, name in indices.items():
                try:
                    # Add random delay between requests
                    time.sleep(random.uniform(0.3, 0.8))
                    
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period='2d')
                    
                    if not hist.empty and len(hist) >= 1:
                        current = hist['Close'].iloc[-1]
                        previous = hist['Close'].iloc[-2] if len(hist) > 1 else current
                        change = current - previous
                        change_percent = (change / previous) * 100 if previous != 0 else 0
                        
                        results.append({
                            'symbol': symbol,
                            'name': name,
                            'current_price': round(float(current), 2),
                            'change': round(float(change), 2),
                            'change_percent': round(float(change_percent), 2)
                        })
                except Exception as e:
                    print(f"Error fetching index {symbol}: {e}")
                    # Add fallback data for demo
                    if symbol == '^NSEI':
                        results.append({
                            'symbol': symbol,
                            'name': name,
                            'current_price': 22500.00,
                            'change': 125.50,
                            'change_percent': 0.56
                        })
            
            return results
        
        data = get_cached_or_fetch("indices", fetch_indices_data)
        return jsonify({'indices': data})
        
    except Exception as e:
        print(f"Indices API error: {e}")
        # Return demo data if service fails
        demo_data = [
            {
                'symbol': '^NSEI',
                'name': 'NIFTY 50',
                'current_price': 22500.00,
                'change': 125.50,
                'change_percent': 0.56
            },
            {
                'symbol': '^BSESN',
                'name': 'SENSEX',
                'current_price': 74000.00,
                'change': 200.25,
                'change_percent': 0.27
            }
        ]
        return jsonify({'indices': demo_data})

@app.route('/api/trending')
def get_trending_stocks():
    try:
        def fetch_trending_data():
            stocks = ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS']
            
            results = []
            for symbol in stocks:
                try:
                    # Add delay between requests
                    time.sleep(random.uniform(0.5, 1.0))
                    
                    stock = yf.Ticker(symbol)
                    hist = stock.history(period='2d')
                    
                    if not hist.empty:
                        info = stock.info
                        current = hist['Close'].iloc[-1]
                        previous = hist['Close'].iloc[-2] if len(hist) > 1 else current
                        change_percent = ((current - previous) / previous) * 100 if previous != 0 else 0
                        
                        results.append({
                            'symbol': symbol,
                            'name': info.get('shortName', symbol.replace('.NS', '')),
                            'current_price': round(float(current), 2),
                            'change_percent': round(float(change_percent), 2)
                        })
                        
                        # Limit to avoid too many requests
                        if len(results) >= 3:
                            break
                            
                except Exception as e:
                    print(f"Error fetching trending stock {symbol}: {e}")
                    continue
            
            return results
        
        data = get_cached_or_fetch("trending", fetch_trending_data)
        
        # If no data, return demo data
        if not data:
            data = [
                {
                    'symbol': 'RELIANCE.NS',
                    'name': 'Reliance Industries',
                    'current_price': 2850.00,
                    'change_percent': 1.25
                },
                {
                    'symbol': 'TCS.NS',
                    'name': 'Tata Consultancy Services',
                    'current_price': 4100.00,
                    'change_percent': -0.45
                }
            ]
        
        return jsonify({'trending': data})
        
    except Exception as e:
        print(f"Trending API error: {e}")
        # Return demo data
        demo_data = [
            {
                'symbol': 'RELIANCE.NS',
                'name': 'Reliance Industries',
                'current_price': 2850.00,
                'change_percent': 1.25
            },
            {
                'symbol': 'TCS.NS',
                'name': 'Tata Consultancy Services',
                'current_price': 4100.00,
                'change_percent': -0.45
            }
        ]
        return jsonify({'trending': demo_data})

# Alternative endpoint for manual stock lookup
@app.route('/api/stock-info/<symbol>')
def get_basic_stock_info(symbol):
    """Simplified stock info endpoint"""
    try:
        if not symbol.endswith('.NS'):
            symbol = symbol.upper() + '.NS'
        
        # Try to get basic info with minimal requests
        stock = yf.Ticker(symbol)
        info = stock.info
        
        return jsonify({
            'symbol': symbol,
            'name': info.get('longName', symbol),
            'sector': info.get('sector', 'N/A'),
            'exchange': 'NSE',
            'currency': 'INR'
        })
    except Exception as e:
        return jsonify({'error': 'Stock info unavailable'}), 503

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
