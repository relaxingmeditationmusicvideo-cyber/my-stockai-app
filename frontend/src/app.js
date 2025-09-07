import React, { useState, useEffect } from 'react';
import { Search, TrendingUp, TrendingDown, BarChart3, Filter, Download, Star, RefreshCw } from 'lucide-react';

const API_BASE = 'http://localhost:3000';

// Components
const StockCard = ({ stock, onAddToWatchlist }) => {
  const isPositive = stock.change_percent >= 0;
  
  return (
    <div className="bg-white rounded-lg shadow-md p-4 hover:shadow-lg transition-shadow">
      <div className="flex justify-between items-start mb-2">
        <h3 className="font-semibold text-lg text-gray-800">{stock.symbol}</h3>
        <button 
          onClick={() => onAddToWatchlist(stock.symbol)}
          className="text-gray-400 hover:text-yellow-500 transition-colors"
        >
          <Star size={18} />
        </button>
      </div>
      
      <div className="flex items-center justify-between mb-2">
        <span className="text-2xl font-bold text-gray-900">₹{stock.price?.toFixed(2) || 'N/A'}</span>
        <div className={`flex items-center ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
          {isPositive ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
          <span className="ml-1 font-medium">{stock.change_percent?.toFixed(2) || 0}%</span>
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-2 text-sm text-gray-600">
        <div>RSI: <span className="font-medium">{stock.rsi?.toFixed(2) || 'N/A'}</span></div>
        <div>Volume: <span className="font-medium">{stock.volume ? (stock.volume / 1000000).toFixed(1) + 'M' : 'N/A'}</span></div>
        <div>MACD: <span className="font-medium">{stock.macd?.toFixed(4) || 'N/A'}</span></div>
        <div>Score: <span className="font-medium text-blue-600">{stock.score?.toFixed(1) || 'N/A'}</span></div>
      </div>
    </div>
  );
};

const ScreenerForm = ({ onScreen, loading }) => {
  const [criteria, setCriteria] = useState({
    rsi_min: '',
    rsi_max: '',
    min_volume: '',
    price_above_sma20: false,
    macd_bullish: false
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    
    // Clean up criteria (remove empty values)
    const cleanCriteria = {};
    Object.keys(criteria).forEach(key => {
      if (criteria[key] !== '' && criteria[key] !== false) {
        if (key === 'price_above_sma20' || key === 'macd_bullish') {
          cleanCriteria[key] = criteria[key];
        } else {
          cleanCriteria[key] = parseFloat(criteria[key]);
        }
      }
    });
    
    onScreen(cleanCriteria);
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-bold mb-4 flex items-center">
        <Filter className="mr-2" />
        Stock Screener Criteria
      </h2>
      
      <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            RSI Min (0-100)
          </label>
          <input
            type="number"
            min="0"
            max="100"
            value={criteria.rsi_min}
            onChange={(e) => setCriteria({...criteria, rsi_min: e.target.value})}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="e.g., 30"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            RSI Max (0-100)
          </label>
          <input
            type="number"
            min="0"
            max="100"
            value={criteria.rsi_max}
            onChange={(e) => setCriteria({...criteria, rsi_max: e.target.value})}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="e.g., 70"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Min Volume
          </label>
          <input
            type="number"
            value={criteria.min_volume}
            onChange={(e) => setCriteria({...criteria, min_volume: e.target.value})}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="e.g., 100000"
          />
        </div>
        
        <div className="space-y-2">
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={criteria.price_above_sma20}
              onChange={(e) => setCriteria({...criteria, price_above_sma20: e.target.checked})}
              className="mr-2 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <span className="text-sm font-medium text-gray-700">Price above 20 SMA</span>
          </label>
          
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={criteria.macd_bullish}
              onChange={(e) => setCriteria({...criteria, macd_bullish: e.target.checked})}
              className="mr-2 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <span className="text-sm font-medium text-gray-700">MACD Bullish</span>
          </label>
        </div>
        
        <div className="md:col-span-2">
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
          >
            {loading ? (
              <>
                <RefreshCw className="animate-spin mr-2" size={16} />
                Scanning...
              </>
            ) : (
              <>
                <Search className="mr-2" size={16} />
                Run Screen
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

const WatchlistPanel = ({ watchlists, onCreateWatchlist, onSelectWatchlist }) => {
  const [isCreating, setIsCreating] = useState(false);
  const [newWatchlistName, setNewWatchlistName] = useState('');

  const handleCreate = () => {
    if (newWatchlistName.trim()) {
      onCreateWatchlist(newWatchlistName.trim());
      setNewWatchlistName('');
      setIsCreating(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold flex items-center">
          <Star className="mr-2" />
          Watchlists
        </h2>
        <button
          onClick={() => setIsCreating(true)}
          className="bg-green-600 text-white px-3 py-1 rounded-md text-sm hover:bg-green-700"
        >
          + New
        </button>
      </div>
      
      {isCreating && (
        <div className="mb-4 p-3 border border-gray-200 rounded-md">
          <input
            type="text"
            value={newWatchlistName}
            onChange={(e) => setNewWatchlistName(e.target.value)}
            placeholder="Watchlist name..."
            className="w-full px-3 py-2 border border-gray-300 rounded-md mb-2"
          />
          <div className="flex gap-2">
            <button
              onClick={handleCreate}
              className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
            >
              Create
            </button>
            <button
              onClick={() => setIsCreating(false)}
              className="bg-gray-300 text-gray-700 px-3 py-1 rounded text-sm hover:bg-gray-400"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
      
      <div className="space-y-2">
        {watchlists.length === 0 ? (
          <p className="text-gray-500 text-sm">No watchlists created yet</p>
        ) : (
          watchlists.map(watchlist => (
            <div
              key={watchlist.id}
              onClick={() => onSelectWatchlist(watchlist)}
              className="p-3 border border-gray-200 rounded-md cursor-pointer hover:bg-gray-50 transition-colors"
            >
              <h3 className="font-medium">{watchlist.name}</h3>
              <p className="text-sm text-gray-600">
                {watchlist.symbols_count || 0} stocks
              </p>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

const StockSearcher = ({ onSelectStock }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const searchStocks = async (searchQuery) => {
    if (!searchQuery.trim()) {
      setResults([]);
      return;
    }
    
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/stocks/list`);
      const data = await response.json();
      
      const filtered = data.stocks.filter(stock =>
        stock.symbol.toLowerCase().includes(searchQuery.toLowerCase())
      );
      
      setResults(filtered.slice(0, 10)); // Limit to 10 results
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timeout = setTimeout(() => {
      searchStocks(query);
    }, 300);
    
    return () => clearTimeout(timeout);
  }, [query]);

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-bold mb-4 flex items-center">
        <Search className="mr-2" />
        Stock Search
      </h2>
      
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search NSE stocks... (e.g., RELIANCE, TCS)"
        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      
      {loading && (
        <div className="mt-2 text-sm text-gray-500">Searching...</div>
      )}
      
      {results.length > 0 && (
        <div className="mt-4 max-h-64 overflow-y-auto">
          {results.map(stock => (
            <div
              key={stock.symbol}
              onClick={() => onSelectStock(stock.symbol)}
              className="p-2 hover:bg-gray-50 cursor-pointer border-b border-gray-100 last:border-b-0"
            >
              <div className="font-medium">{stock.symbol}</div>
              <div className="text-sm text-gray-600">{stock.exchange}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// Main App Component
const App = () => {
  const [screenResults, setScreenResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [watchlists, setWatchlists] = useState([]);
  const [selectedStock, setSelectedStock] = useState(null);
  const [activeTab, setActiveTab] = useState('screener');
  const [notification, setNotification] = useState('');

  // Load watchlists on component mount
  useEffect(() => {
    loadWatchlists();
    testApiConnection();
  }, []);

  const testApiConnection = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/health`);
      if (response.ok) {
        showNotification('API connection successful', 'success');
      }
    } catch (error) {
      showNotification('API connection failed - check if backend is running', 'error');
    }
  };

  const loadWatchlists = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/watchlists`);
      if (response.ok) {
        const data = await response.json();
        setWatchlists(data.watchlists || []);
      }
    } catch (error) {
      console.error('Error loading watchlists:', error);
    }
  };

  const runScreener = async (criteria) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/screener/scan`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ criteria, limit: 30 }),
      });
      
      if (response.ok) {
        const data = await response.json();
        setScreenResults(data.results);
        showNotification(`Found ${data.matches} stocks matching criteria`);
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Screening failed');
      }
    } catch (error) {
      console.error('Screening error:', error);
      showNotification(`Error: ${error.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const createWatchlist = async (name) => {
    try {
      const response = await fetch(`${API_BASE}/api/watchlist`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name, symbols: [] }),
      });
      
      if (response.ok) {
        await loadWatchlists();
        showNotification(`Watchlist "${name}" created successfully`);
      } else {
        throw new Error('Failed to create watchlist');
      }
    } catch (error) {
      console.error('Error creating watchlist:', error);
      showNotification('Error creating watchlist', 'error');
    }
  };

  const addToWatchlist = async (symbol) => {
    // For now, just show a notification
    showNotification(`${symbol} would be added to watchlist`);
  };

  const selectStock = (symbol) => {
    setSelectedStock(symbol);
    setActiveTab('stock');
  };

  const showNotification = (message, type = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(''), 5000);
  };

  const exportResults = async () => {
    try {
      const criteria = encodeURIComponent(JSON.stringify({}));
      window.open(`${API_BASE}/api/export/csv?criteria=${criteria}`, '_blank');
      showNotification('Export started. Check your downloads.');
    } catch (error) {
      showNotification('Export failed', 'error');
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <BarChart3 className="h-8 w-8 text-blue-600 mr-3" />
              <h1 className="text-2xl font-bold text-gray-900">
                🇮🇳 Indian Stock Screener
              </h1>
            </div>
            
            <nav className="flex space-x-4">
              <button
                onClick={() => setActiveTab('screener')}
                className={`px-3 py-2 rounded-md text-sm font-medium ${
                  activeTab === 'screener'
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                Screener
              </button>
              <button
                onClick={() => setActiveTab('watchlist')}
                className={`px-3 py-2 rounded-md text-sm font-medium ${
                  activeTab === 'watchlist'
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                Watchlists
              </button>
              <button
                onClick={() => setActiveTab('search')}
                className={`px-3 py-2 rounded-md text-sm font-medium ${
                  activeTab === 'search'
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                Search
              </button>
            </nav>
          </div>
        </div>
      </header>

      {/* Notification */}
      {notification && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-2 rounded-md shadow-lg max-w-md ${
          notification.type === 'error' 
            ? 'bg-red-500 text-white' 
            : 'bg-green-500 text-white'
        }`}>
          {notification.message}
        </div>
      )}

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        {activeTab === 'screener' && (
          <div className="space-y-6">
            <ScreenerForm onScreen={runScreener} loading={loading} />
            
            {screenResults.length > 0 && (
              <div>
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-xl font-bold">
                    Screening Results ({screenResults.length} stocks)
                  </h2>
                  <button
                    onClick={exportResults}
                    className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 flex items-center"
                  >
                    <Download className="mr-2" size={16} />
                    Export CSV
                  </button>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {screenResults.map(stock => (
                    <StockCard
                      key={stock.symbol}
                      stock={stock}
                      onAddToWatchlist={addToWatchlist}
                    />
                  ))}
                </div>
              </div>
            )}
            
            {!loading && screenResults.length === 0 && (
              <div className="bg-white rounded-lg shadow-md p-8 text-center">
                <BarChart3 className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">No screening results yet</h3>
                <p className="text-gray-500">Set your criteria above and click "Run Screen" to find stocks</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'watchlist' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1">
              <WatchlistPanel
                watchlists={watchlists}
                onCreateWatchlist={createWatchlist}
                onSelectWatchlist={(wl) => console.log('Selected:', wl)}
              />
            </div>
            <div className="lg:col-span-2">
              <div className="bg-white rounded-lg shadow-md p-6">
                <h2 className="text-xl font-bold mb-4">Watchlist Stocks</h2>
                <p className="text-gray-500">
                  Select a watchlist to view stocks or create a new one to get started
                </p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'search' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <StockSearcher onSelectStock={selectStock} />
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-bold mb-4">Stock Details</h2>
              {selectedStock ? (
                <div>
                  <h3 className="text-lg font-semibold">{selectedStock}</h3>
                  <p className="text-gray-600 mt-2">
                    Detailed analysis would appear here
                  </p>
                </div>
              ) : (
                <p className="text-gray-500">
                  Search and select a stock to view details
                </p>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-12">
        <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8">
          <div className="text-center text-sm text-gray-500">
            <p>Indian Stock Screener - Real-time NSE & BSE Analysis</p>
            <p className="mt-1">
              Data delayed by ~15 minutes | For educational purposes only
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;