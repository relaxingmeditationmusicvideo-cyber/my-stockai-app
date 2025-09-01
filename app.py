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
        'service': 'Indian Stock Analytics Pro',
        'market': 'NSE/BSE'
    })

@app.route('/api/stock/<symbol>')
def get_stock_data(symbol):
    """Get Indian stock data for a specific symbol"""
    try:
        # Add .NS (NSE) suffix if not present for Indian stocks
        if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
            if symbol.upper() in ['RELIANCE', 'TCS', 'INFY', 'HINDUNILVR', 'ICICIBANK', 'HDFC', 'HDFCBANK', 'KOTAKBANK', 'BHARTIARTL', 'ITC', 'SBIN', 'BAJFINANCE', 'ASIANPAINT', 'MARUTI', 'AXISBANK', 'LT', 'NESTLEIND', 'WIPRO', 'ULTRACEMCO']:
                symbol = symbol.upper() + '.NS'
            else:
                symbol = symbol.upper() + '.NS'  # Default to NSE
        
        # Get stock info
        stock = yf.Ticker(symbol)
        
        # Get current price and basic info
        info = stock.info
        hist = stock.history(period='5d')
        
        if hist.empty:
            # Try with .BO (BSE) suffix if .NS doesn't work
            if symbol.endswith('.NS'):
                symbol = symbol.replace('.NS', '.BO')
                stock = yf.Ticker(symbol)
                hist = stock.history(period='5d')
                info = stock.info
            
            if hist.empty:
                return jsonify({'error': 'Stock symbol not found. Try symbols like RELIANCE.NS, TCS.NS, INFY.NS'}), 404
            
        current_price = hist['Close'].iloc[-1]
        previous_close = info.get('previousClose', current_price)
        change = current_price - previous_close
        change_percent = (change / previous_close) * 100 if previous_close != 0 else 0
        
        return jsonify({
            'symbol': symbol,
            'current_price': round(current_price, 2),
            'change': round(change, 2),
            'change_percent': round(change_percent, 2),
            'volume': info.get('volume', 0),
            'market_cap': info.get('marketCap', 0),
            'pe_ratio': info.get('trailingPE', 0),
            'company_name': info.get('longName', symbol),
            'currency': 'INR',
            'exchange': 'NSE' if symbol.endswith('.NS') else 'BSE',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': f'Error fetching data: {str(e)}'}), 500

@app.route('/api/stock/<symbol>/history')
def get_stock_history(symbol):
    """Get historical Indian stock data"""
    try:
        period = request.args.get('period', '1mo')  # 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
        
        # Add .NS suffix if not present
        if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
            symbol = symbol.upper() + '.NS'
        
        stock = yf.Ticker(symbol)
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
            'symbol': symbol,
            'period': period,
            'currency': 'INR',
            'data': data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/nifty-indices')
def get_nifty_indices():
    """Get major Indian market indices (NIFTY, SENSEX, etc.)"""
    try:
        indices = {
            '^NSEI': 'NIFTY 50',
            '^BSESN': 'SENSEX',
            '^NSEBANK': 'BANK NIFTY',
            '^NSEIT': 'NIFTY IT',
            'NIFTYNEXT50.NS': 'NIFTY NEXT 50'
        }
        
        results = []
        for symbol, name in indices.items():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period='5d')
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
                        'change_percent': round(change_percent, 2),
                        'currency': 'INR'
                    })
            except:
                continue
                
        return jsonify({'indices': results})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search/<query>')
def search_indian_stocks(query):
    """Search for Indian stocks by symbol or company name"""
    try:
        # Add .NS suffix and try to get info
        symbol = query.upper()
        if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
            symbol = symbol + '.NS'
        
        results = []
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if 'longName' in info:
                results.append({
                    'symbol': symbol,
                    'name': info.get('longName', symbol),
                    'sector': info.get('sector', 'N/A'),
                    'industry': info.get('industry', 'N/A'),
                    'exchange': 'NSE' if symbol.endswith('.NS') else 'BSE'
                })
        except:
            pass
            
        return jsonify({'results': results})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/trending-indian')
def get_trending_indian_stocks():
    """Get trending Indian stocks (NIFTY 50 top stocks)"""
    try:
        # Popular Indian stock symbols
        indian_symbols = [
            'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'HINDUNILVR.NS',
            'ICICIBANK.NS', 'KOTAKBANK.NS', 'HDFC.NS', 'BHARTIARTL.NS', 'ITC.NS',
            'SBIN.NS', 'BAJFINANCE.NS', 'ASIANPAINT.NS', 'MARUTI.NS', 'AXISBANK.NS'
        ]
        
        results = []
        for symbol in indian_symbols[:8]:  # Limit to 8 for performance
            try:
                stock = yf.Ticker(symbol)
                info = stock.info
                hist = stock.history(period='5d')
                
                if not hist.empty:
                    current = hist['Close'].iloc[-1]
                    previous = hist['Close'].iloc[-2] if len(hist) > 1 else current
                    change_percent = ((current - previous) / previous) * 100 if previous != 0 else 0
                    
                    results.append({
                        'symbol': symbol,
                        'name': info.get('shortName', symbol.replace('.NS', '')),
                        'current_price': round(current, 2),
                        'change_percent': round(change_percent, 2),
                        'currency': 'INR'
                    })
            except:
                continue
                
        return jsonify({'trending': results})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/market-news')
def get_indian_market_news():
    """Get Indian market news (basic implementation)"""
    try:
        # This is a placeholder - you would integrate with news APIs
        news_items = [
            {
                'title': 'Indian Markets Update',
                'description': 'Real-time market data available through the dashboard',
                'timestamp': datetime.now().isoformat()
            }
        ]
        
        return jsonify({'news': news_items})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
