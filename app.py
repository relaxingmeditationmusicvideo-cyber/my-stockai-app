from flask import Flask, render_template, jsonify, request
import yfinance as yf
import os

app = Flask(__name__)

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Indian Stock Analytics Pro',
        'market': 'NSE/BSE'
    })

@app.route('/api/stock/<symbol>')
def get_stock_data(symbol):
    """Get Indian stock data"""
    try:
        # Add .NS for NSE if not present
        if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
            symbol = symbol.upper() + '.NS'
        
        stock = yf.Ticker(symbol)
        hist = stock.history(period='5d')
        info = stock.info
        
        if hist.empty:
            return jsonify({'error': 'Stock not found'}), 404
            
        current_price = hist['Close'].iloc[-1]
        previous_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
        change = current_price - previous_close
        change_percent = (change / previous_close) * 100 if previous_close != 0 else 0
        
        return jsonify({
            'symbol': symbol,
            'current_price': round(current_price, 2),
            'change': round(change, 2),
            'change_percent': round(change_percent, 2),
            'volume': info.get('volume', 0),
            'company_name': info.get('longName', symbol),
            'exchange': 'NSE' if symbol.endswith('.NS') else 'BSE'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/nifty-indices')
def get_nifty_indices():
    """Get Indian market indices"""
    try:
        indices = {
            '^NSEI': 'NIFTY 50',
            '^BSESN': 'SENSEX',
            '^NSEBANK': 'BANK NIFTY'
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

@app.route('/api/trending')
def get_trending_stocks():
    """Get popular Indian stocks"""
    try:
        stocks = ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS']
        
        results = []
        for symbol in stocks:
            try:
                stock = yf.Ticker(symbol)
                hist = stock.history(period='2d')
                info = stock.info
                
                if not hist.empty:
                    current = hist['Close'].iloc[-1]
                    previous = hist['Close'].iloc[-2] if len(hist) > 1 else current
                    change_percent = ((current - previous) / previous) * 100 if previous != 0 else 0
                    
                    results.append({
                        'symbol': symbol,
                        'name': info.get('shortName', symbol.replace('.NS', '')),
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
