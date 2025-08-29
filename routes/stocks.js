const express = require('express');
const router = express.Router();

// Get all stocks
router.get('/', (req, res) => {
  res.json({
    success: true,
    message: 'Stocks API endpoint',
    data: [
      { symbol: 'AAPL', price: 175.50, change: 2.30, changePercent: 1.33 },
      { symbol: 'GOOGL', price: 2850.00, change: -15.50, changePercent: -0.54 },
      { symbol: 'TSLA', price: 245.75, change: 8.25, changePercent: 3.47 },
      { symbol: 'MSFT', price: 380.20, change: 4.80, changePercent: 1.28 },
      { symbol: 'AMZN', price: 145.30, change: -2.10, changePercent: -1.42 }
    ],
    timestamp: new Date().toISOString()
  });
});

// Get specific stock
router.get('/:symbol', (req, res) => {
  const { symbol } = req.params;
  res.json({
    success: true,
    message: `Stock data for ${symbol}`,
    symbol: symbol.toUpperCase(),
    data: {
      price: Math.random() * 200 + 100,
      change: (Math.random() - 0.5) * 10,
      changePercent: (Math.random() - 0.5) * 5,
      high: Math.random() * 220 + 110,
      low: Math.random() * 180 + 90,
      volume: Math.floor(Math.random() * 10000000)
    },
    timestamp: new Date().toISOString()
  });
});

// Get stock historical data
router.get('/:symbol/history', (req, res) => {
  const { symbol } = req.params;
  const { period = '1d' } = req.query;
  
  const data = Array.from({ length: 30 }, (_, i) => ({
    date: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000).toISOString(),
    price: Math.random() * 200 + 100,
    volume: Math.floor(Math.random() * 5000000)
  }));
  
  res.json({
    success: true,
    message: `Historical data for ${symbol}`,
    symbol: symbol.toUpperCase(),
    period,
    data,
    timestamp: new Date().toISOString()
  });
});

module.exports = router;