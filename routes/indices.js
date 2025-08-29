const express = require('express');
const router = express.Router();

// Get all market indices
router.get('/', (req, res) => {
  res.json({
    success: true,
    message: 'Market indices API endpoint',
    data: [
      {
        name: 'NIFTY 50',
        symbol: 'NIFTY',
        value: 19847.25,
        change: 125.30,
        changePercent: 0.64,
        high: 19920.50,
        low: 19750.20,
        open: 19780.00
      },
      {
        name: 'SENSEX',
        symbol: 'SENSEX',
        value: 66589.93,
        change: 450.75,
        changePercent: 0.68,
        high: 66750.25,
        low: 66200.40,
        open: 66350.80
      },
      {
        name: 'NIFTY BANK',
        symbol: 'BANKNIFTY',
        value: 44125.80,
        change: -185.40,
        changePercent: -0.42,
        high: 44350.50,
        low: 43980.25,
        open: 44280.00
      },
      {
        name: 'NIFTY IT',
        symbol: 'NIFTYIT',
        value: 30245.60,
        change: 320.85,
        changePercent: 1.07,
        high: 30450.20,
        low: 29980.40,
        open: 30100.75
      }
    ],
    timestamp: new Date().toISOString()
  });
});

// Get specific index
router.get('/:index', (req, res) => {
  const { index } = req.params;
  res.json({
    success: true,
    message: `Index data for ${index}`,
    index: index.toUpperCase(),
    data: {
      value: Math.random() * 50000 + 15000,
      change: (Math.random() - 0.5) * 500,
      changePercent: (Math.random() - 0.5) * 2,
      high: Math.random() * 52000 + 16000,
      low: Math.random() * 48000 + 14000,
      open: Math.random() * 50000 + 15000,
      volume: Math.floor(Math.random() * 100000000),
      marketCap: Math.floor(Math.random() * 1000000000000)
    },
    timestamp: new Date().toISOString()
  });
});

// Get index historical data
router.get('/:index/history', (req, res) => {
  const { index } = req.params;
  const { period = '1d' } = req.query;
  
  const data = Array.from({ length: 30 }, (_, i) => ({
    date: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000).toISOString(),
    value: Math.random() * 50000 + 15000,
    volume: Math.floor(Math.random() * 50000000)
  }));
  
  res.json({
    success: true,
    message: `Historical data for ${index}`,
    index: index.toUpperCase(),
    period,
    data,
    timestamp: new Date().toISOString()
  });
});

module.exports = router;