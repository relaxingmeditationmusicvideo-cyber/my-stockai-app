const express = require('express');
const router = express.Router();
const alphaVantageService = require('../services/alphaVantage');
const yahooService = require('../services/yahooFinance');
const cache = require('../utils/cache');

// Get top gainers and losers
router.get('/gainers-losers', async (req, res) => {
  try {
    const data = await alphaVantageService.getTopGainersLosers();
    res.json({
      success: true,
      data: data,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('Gainers/Losers API error:', error.message);
    
    // Fallback to demo data
    const fallbackData = {
      gainers: [
        { symbol: 'RELIANCE', price: 2847.65, changePercent: 3.45 },
        { symbol: 'TCS', price: 3890.20, changePercent: 2.87 },
        { symbol: 'INFY', price: 1675.80, changePercent: 2.54 },
        { symbol: 'HCLTECH', price: 1289.30, changePercent: 2.23 },
        { symbol: 'WIPRO', price: 587.25, changePercent: 1.98 }
      ],
      losers: [
        { symbol: 'BAJFINANCE', price: 6847.25, changePercent: -2.87 },
        { symbol: 'HDFC', price: 1698.45, changePercent: -2.34 },
        { symbol: 'ICICIBANK', price: 1187.30, changePercent: -1.98 },
        { symbol: 'SBIN', price: 785.40, changePercent: -1.76 },
        { symbol: 'AXISBANK', price: 1045.60, changePercent: -1.45 }
      ]
    };
    
    res.json({
      success: true,
      data: fallbackData,
      source: 'fallback',
      timestamp: new Date().toISOString()
    });
  }
});

// Get stock quote
router.get('/quote/:symbol', async (req, res) => {
  try {
    const { symbol } = req.params;
    const quote = await alphaVantageService.getQuote(symbol);
    
    res.json({
      success: true,
      data: quote,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error(`Quote API error for ${req.params.symbol}:`, error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch stock quote',
      symbol: req.params.symbol
    });
  }
});

// Stock screener endpoint
router.get('/screener/:type', async (req, res) => {
  try {
    const { type } = req.params;
    const cacheKey = `screener:${type}`;
    
    let data = await cache.get(cacheKey);
    
    if (!data) {
      // Generate screener data based on type
      data = generateScreenerData(type);
      await cache.set(cacheKey, data, 300); // Cache for 5 minutes
    }
    
    res.json({
      success: true,
      data: data,
      type: type,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error(`Screener API error for ${req.params.type}:`, error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch screener data'
    });
  }
});

// Market statistics
router.get('/market-stats', async (req, res) => {
  try {
    const cacheKey = 'market_stats';
    let stats = await cache.get(cacheKey);
    
    if (!stats) {
      stats = {
        advances: Math.floor(Math.random() * 1000) + 1500,
        declines: Math.floor(Math.random() * 800) + 800,
        volume: (Math.random() * 5 + 2).toFixed(1) + 'L Cr',
        high52w: Math.floor(Math.random() * 200) + 300,
        timestamp: new Date().toISOString()
      };
      
      await cache.set(cacheKey, stats, 180); // Cache for 3 minutes
    }
    
    res.json({
      success: true,
      data: stats
    });
  } catch (error) {
    console.error('Market stats error:', error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch market statistics'
    });
  }
});

// Search stocks
router.get('/search', async (req, res) => {
  try {
    const { query, limit = 10 } = req.query;
    
    if (!query || query.length < 2) {
      return res.status(400).json({
        success: false,
        error: 'Query must be at least 2 characters long'
      });
    }
    
    // For demo purposes, return matching stocks from a predefined list
    const allStocks = [
      'RELIANCE', 'TCS', 'INFY', 'HCLTECH', 'WIPRO', 'ITC', 'SBIN', 'HDFC',
      'ICICIBANK', 'BHARTIARTL', 'ASIANPAINT', 'MARUTI', 'LT', 'ULTRACEMCO',
      'NESTLEIND', 'KOTAKBANK', 'BAJFINANCE', 'HDFCBANK', 'TITAN', 'POWERGRID'
    ];
    
    const matches = allStocks
      .filter(stock => stock.toLowerCase().includes(query.toLowerCase()))
      .slice(0, parseInt(limit))
      .map(symbol => ({
        symbol,
        name: `${symbol} Ltd.`,
        type: 'equity'
      }));
    
    res.json({
      success: true,
      data: matches,
      query: query
    });
  } catch (error) {
    console.error('Search error:', error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to search stocks'
    });
  }
});

// Helper function to generate screener data
function generateScreenerData(type) {
  const stocks = [
    'RELIANCE', 'TCS', 'INFY', 'HCLTECH', 'WIPRO', 'ITC', 'SBIN', 'HDFC',
    'ICICIBANK', 'BHARTIARTL', 'ASIANPAINT', 'MARUTI', 'LT', 'ULTRACEMCO'
  ];
  
  const signals = {
    bullish: ['Strong Buy', 'Buy', 'Accumulate'],
    bearish: ['Sell', 'Strong Sell', 'Reduce'],
    breakout: ['Breakout', 'Momentum', 'Trending Up'],
    value: ['Undervalued', 'Value Pick', 'Fair Value'],
    growth: ['High Growth', 'Growth Leader', 'Expanding']
  };
  
  const screenerSignals = signals[type] || signals.bullish;
  
  return stocks.slice(0, 8).map(symbol => ({
    symbol,
    signal: screenerSignals[Math.floor(Math.random() * screenerSignals.length)],
    strength: Math.floor(Math.random() * 40) + 60, // 60-100% strength
    price: (Math.random() * 3000 + 100).toFixed(2),
    changePercent: type === 'bearish' ? 
      -(Math.random() * 5).toFixed(2) : 
      (Math.random() * 5).toFixed(2)
  }));
}

module.exports = router;