const express = require('express');
const router = express.Router();

// Sample news data
const sampleNews = [
  {
    id: 1,
    title: 'Stock Markets Hit New Record Highs Amid Economic Optimism',
    summary: 'Major indices reached all-time highs as investors showed confidence in upcoming earnings season.',
    content: 'The stock market continued its upward trajectory today, with the S&P 500 and Dow Jones reaching new record levels...',
    source: 'Financial Times',
    publishedAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    url: '#',
    category: 'market',
    image: 'https://via.placeholder.com/400x200?text=Stock+Market'
  },
  {
    id: 2,
    title: 'Tech Giants Report Strong Q3 Earnings',
    summary: 'Apple, Google, and Microsoft exceeded analyst expectations with robust quarterly results.',
    content: 'Technology companies dominated earnings reports this quarter, showing strong revenue growth...',
    source: 'Reuters',
    publishedAt: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
    url: '#',
    category: 'earnings',
    image: 'https://via.placeholder.com/400x200?text=Tech+Earnings'
  },
  {
    id: 3,
    title: 'Federal Reserve Hints at Interest Rate Changes',
    summary: 'Fed officials suggest potential policy adjustments in upcoming meetings.',
    content: 'The Federal Reserve indicated possible changes to monetary policy in response to economic indicators...',
    source: 'Bloomberg',
    publishedAt: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
    url: '#',
    category: 'policy',
    image: 'https://via.placeholder.com/400x200?text=Federal+Reserve'
  },
  {
    id: 4,
    title: 'Cryptocurrency Market Shows Volatility',
    summary: 'Bitcoin and major altcoins experience significant price swings amid regulatory concerns.',
    content: 'The cryptocurrency market showed increased volatility as regulatory discussions continue...',
    source: 'CoinDesk',
    publishedAt: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString(),
    url: '#',
    category: 'crypto',
    image: 'https://via.placeholder.com/400x200?text=Cryptocurrency'
  },
  {
    id: 5,
    title: 'Energy Stocks Surge on Oil Price Rally',
    summary: 'Energy sector leads market gains as crude oil prices climb higher.',
    content: 'Energy stocks experienced significant gains today as oil prices continued their upward momentum...',
    source: 'Energy News',
    publishedAt: new Date(Date.now() - 10 * 60 * 60 * 1000).toISOString(),
    url: '#',
    category: 'energy',
    image: 'https://via.placeholder.com/400x200?text=Energy+Stocks'
  }
];

// Get latest news
router.get('/', (req, res) => {
  const { category = 'all', limit = 10, page = 1 } = req.query;
  
  let filteredNews = sampleNews;
  if (category !== 'all') {
    filteredNews = sampleNews.filter(news => news.category === category);
  }
  
  const startIndex = (page - 1) * parseInt(limit);
  const endIndex = startIndex + parseInt(limit);
  const paginatedNews = filteredNews.slice(startIndex, endIndex);
  
  res.json({
    success: true,
    message: 'Latest financial news',
    category,
    data: paginatedNews,
    pagination: {
      page: parseInt(page),
      limit: parseInt(limit),
      total: filteredNews.length,
      totalPages: Math.ceil(filteredNews.length / parseInt(limit))
    },
    timestamp: new Date().toISOString()
  });
});

// Get news by category
router.get('/category/:category', (req, res) => {
  const { category } = req.params;
  const { limit = 10 } = req.query;
  
  const categoryNews = sampleNews.filter(news => news.category === category);
  const limitedNews = categoryNews.slice(0, parseInt(limit));
  
  res.json({
    success: true,
    message: `News for category: ${category}`,
    category,
    data: limitedNews,
    pagination: {
      page: 1,
      limit: parseInt(limit),
      total: categoryNews.length
    },
    timestamp: new Date().toISOString()
  });
});

// Get news for specific stock
router.get('/stock/:symbol', (req, res) => {
  const { symbol } = req.params;
  const { limit = 10 } = req.query;
  
  // Generate stock-specific news
  const stockNews = [
    {
      id: Date.now(),
      title: `${symbol.toUpperCase()} Reports Strong Quarterly Performance`,
      summary: `${symbol.toUpperCase()} exceeded analyst expectations in latest earnings report.`,
      content: `Detailed analysis of ${symbol.toUpperCase()} quarterly results...`,
      source: 'Market Watch',
      publishedAt: new Date().toISOString(),
      url: '#',
      category: 'earnings',
      symbol: symbol.toUpperCase()
    }
  ];
  
  res.json({
    success: true,
    message: `News for stock: ${symbol.toUpperCase()}`,
    symbol: symbol.toUpperCase(),
    data: stockNews,
    pagination: {
      page: 1,
      limit: parseInt(limit),
      total: stockNews.length
    },
    timestamp: new Date().toISOString()
  });
});

// Search news
router.get('/search', (req, res) => {
  const { q, limit = 10 } = req.query;
  
  if (!q) {
    return res.status(400).json({
      success: false,
      message: 'Search query is required',
      timestamp: new Date().toISOString()
    });
  }
  
  const searchResults = sampleNews.filter(news => 
    news.title.toLowerCase().includes(q.toLowerCase()) ||
    news.summary.toLowerCase().includes(q.toLowerCase())
  );
  
  res.json({
    success: true,
    message: `Search results for: ${q}`,
    query: q,
    data: searchResults.slice(0, parseInt(limit)),
    pagination: {
      page: 1,
      limit: parseInt(limit),
      total: searchResults.length
    },
    timestamp: new Date().toISOString()
  });
});

// Get trending news
router.get('/trending', (req, res) => {
  const { limit = 5 } = req.query;
  
  const trendingNews = sampleNews
    .sort((a, b) => new Date(b.publishedAt) - new Date(a.publishedAt))
    .slice(0, parseInt(limit));
  
  res.json({
    success: true,
    message: 'Trending financial news',
    data: trendingNews,
    timestamp: new Date().toISOString()
  });
});

module.exports = router;