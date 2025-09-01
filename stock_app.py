from flask import Flask, render_template, jsonify, request
import yfinance as yf
import pandas as pd
import json
from datetime import datetime, timedelta
import requests
import os

app = Flask(__name__)

# Configure for production
app.config['ENV'] = 'production'
app.config['DEBUG'] = False

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'Stock Analytics Pro'
    })

@app.route('/api/stock/<symbol>')
def get_stock_data(symbol):
    """Get stock data for a specific symbol"""
    try:
        # Get stock info
        stock = yf.Ticker(symbol.upper())
        
        # Get current price and basic info
        info = stock.info
        hist = stock.history(period='1d', interval='1m')
        
        if hist.empty:
            return jsonify({'error': 'Stock symbol not found'}), 404
            
        current_price = hist['Close'].iloc[-1]
        previous_close = info.get('previousClose', current_price)
        change = current_price - previous_close
        change_percent = (change / previous_close) * 100 if previous_close != 0 else 0
        
        return jsonify({
            'symbol': symbol.upper(),
            'current_price': round(current_price, 2),
            'change': round(change, 2),
            'change_percent': round(change_percent, 2),
            'volume': info.get('volume', 0),
            'market_cap': info.get('marketCap', 0),
            'pe_ratio': info.get('trailingPE', 0),
            'company_name': info.get('longName', symbol.upper()),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stock/<symbol>/history')
def get_stock_history(symbol):
    """Get historical stock data"""
    try:
        period = request.args.get('period', '1mo')  # 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
        
        stock = yf.Ticker(symbol.upper())
        hist = stock.history(period=period)
        
        if hist.empty:
            return jsonify({'error': 'Stock symbol not found'}), 404
            
        # Convert to JSON format
        data = []
        for date, row in hist.iterrows():
            data.append({
                'date': date.strftime('%Y-%m-%d'),
                'open': round(row['Open'], 2),
                'high': round(row['High'], 2),
                'low': round(row['Low'], 2),
                'close': round(row['Close'], 2),
                'volume': int(row['Volume'])
            })
            
        return jsonify({
            'symbol': symbol.upper(),
            'period': period,
            'data': data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/market-indices')
def get_market_indices():
    """Get major market indices"""
    try:
        indices = {
            '^GSPC': 'S&P 500',
            '^DJI': 'Dow Jones',
            '^IXIC': 'NASDAQ',
            '^VIX': 'VIX'
        }
        
        results = []
        for symbol, name in indices.items():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period='2d')
                if not hist.empty:
                    current = hist['Close'].iloc[-1]
                    previous = hist['Close'].iloc[-2] if len(hist) > 1 else current
                    change = current - previous
                    change_percent = (change / previous) * 100 if previous != 0 else 0
                    
                    results.append({
                        'symbol': symbol,
                        'name': name,
                        'current_price': round(current, 2),
                        'change': round(change, 2),
                        'change_percent': round(change_percent, 2)
                    })
            except:
                continue
                
        return jsonify({'indices': results})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search/<query>')
def search_stocks(query):
    """Search for stocks by symbol or company name"""
    try:
        # Simple search using yfinance
        symbols = [query.upper()]
        
        # Try to get info for the symbol
        results = []
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                if 'longName' in info:
                    results.append({
                        'symbol': symbol,
                        'name': info.get('longName', symbol),
                        'sector': info.get('sector', 'N/A'),
                        'industry': info.get('industry', 'N/A')
                    })
            except:
                continue
                
        return jsonify({'results': results})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/trending')
def get_trending_stocks():
    """Get trending stocks (popular symbols)"""
    try:
        # Popular stock symbols
        popular_symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX']
        
        results = []
        for symbol in popular_symbols[:5]:  # Limit to 5 for performance
            try:
                stock = yf.Ticker(symbol)
                info = stock.info
                hist = stock.history(period='2d')
                
                if not hist.empty:
                    current = hist['Close'].iloc[-1]
                    previous = hist['Close'].iloc[-2] if len(hist) > 1 else current
                    change_percent = ((current - previous) / previous) * 100 if previous != 0 else 0
                    
                    results.append({
                        'symbol': symbol,
                        'name': info.get('shortName', symbol),
                        'current_price': round(current, 2),
                        'change_percent': round(change_percent, 2)
                    })
            except:
                continue
                
        return jsonify({'trending': results})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)