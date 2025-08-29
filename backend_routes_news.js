const express = require('express');
const axios = require('axios');
const router = express.Router();
const cache = require('../utils/cache');

// Get market news
router.get('/', async (req, res) => {
  try {
    const { limit = 10, category = 'general' } = req.query;
    const cacheKey = `news:${category}:${limit}`;
    
    let news = await cache.get(cacheKey);
    
    if (!news) {
      // Try to fetch from news API (replace with your preferred news service)
      news = await fetchMarketNews(category, limit);
      await cache.set(cacheKey, news, 600); // Cache for 10 minutes
    }
    
    res.json({
      success: true,
      data: news,
      category: category,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('News API error:', error.message);
    
    // Fallback to demo news data
    const fallbackNews = getDemoNews();
    res.json({
      success: true,
      data: fallbackNews,
      source: 'fallback',
      timestamp: new Date().toISOString()
    });
  }
});

// Get news for specific stock
router.get('/stock/:symbol', async (req, res) => {
  try {
    const { symbol } = req.params;
    const { limit = 5 } = req.query;
    const cacheKey = `news:stock:${symbol}`;
    
    let news = await cache.get(cacheKey);
    
    if (!news) {
      news = await fetchStockNews(symbol, limit);
      await cache.set(cacheKey, news, 900); // Cache for 15 minutes
    }
    
    res.json({
      success: true,
      data: news,
      symbol: symbol,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error(`Stock news error for ${req.params.symbol}:`, error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch stock news'
    });
  }
});

// Fetch market news from external API
async function fetchMarketNews(category, limit) {
  try {
    // Option 1: NewsAPI (requires API key)
    if (process.env.NEWS_API_KEY) {
      const response = await axios.get('https://newsapi.org/v2/everything', {
        params: {
          q: 'stock market OR NSE OR BSE OR Sensex OR Nifty',
          language: 'en',
          sortBy: 'publishedAt',
          pageSize: limit,
          apiKey: process.env.NEWS_API_KEY
        },
        timeout: 5000
      });
      
      return response.data.articles.map(article => ({
        title: article.title,
        description: article.description,
        url: article.url,
        source: article.source.name,
        publishedAt: article.publishedAt,
        urlToImage: article.urlToImage
      }));
    }
    
    // Option 2: RSS feeds (free alternative)
    return await fetchRSSNews();
    
  } catch (error) {
    console.error('Error fetching external news:', error.message);
    return getDemoNews();
  }
}

// Fetch stock-specific news
async function fetchStockNews(symbol, limit) {
  try {
    if (process.env.NEWS_API_KEY) {
      const response = await axios.get('https://newsapi.org/v2/everything', {
        params: {
          q: symbol,
          language: 'en',
          sortBy: 'publishedAt',
          pageSize: limit,
          apiKey: process.env.NEWS_API_KEY
        },
        timeout: 5000
      });
      
      return response.data.articles.map(article => ({
        title: article.title,
        description: article.description,
        url: article.url,
        source: article.source.name,
        publishedAt: article.publishedAt,
        relevantStock: symbol
      }));
    }
    
    return getDemoStockNews(symbol);
    
  } catch (error) {
    console.error(`Error fetching news for ${symbol}:`, error.message);
    return getDemoStockNews(symbol);
  }
}

// Fetch from RSS feeds (free alternative to NewsAPI)
async function fetchRSSNews() {
  // This is a placeholder - you would use an RSS parser library
  // like 'rss-parser' to fetch from financial news RSS feeds
  
  const rssFeeds = [
    'https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms',
    'https://www.moneycontrol.com/rss/results.xml',
    'https://feeds.feedburner.com/ndtvprofit-latest'
  ];
  
  // For demo purposes, return sample data
  return getDemoNews();
}

// Demo news data
function getDemoNews() {
  const newsItems = [
    {
      title: 'Sensex surges 400 points on strong global cues',
      description: 'Indian benchmark indices opened higher on positive sentiment from global markets...',
      source: 'Economic Times',
      publishedAt: new Date(Date.now() - 2 * 60 * 1000).toISOString(), // 2 minutes ago
      url: 'https://example.com/news/1'
    },
    {
      title: 'RBI maintains repo rate at 6.5% in monetary policy review',
      description: 'Reserve Bank of India keeps key policy rates unchanged as expected by market participants...',
      source: 'Business Standard',
      publishedAt: new Date(Date.now() - 15 * 60 * 1000).toISOString(), // 15 minutes ago
      url: 'https://example.com/news/2'
    },
    {
      title: 'IT stocks rally on strong Q3 earnings expectations',
      description: 'Technology stocks lead market gains ahead of quarterly results announcement...',
      source: 'Mint',
      publishedAt: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(), // 1 hour ago
      url: 'https://example.com/news/3'
    },
    {
      title: 'FII inflows continue for third consecutive trading session',
      description: 'Foreign institutional investors remain net buyers in Indian equities...',
      source: 'Moneycontrol',
      publishedAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
      url: 'https://example.com/news/4'
    },
    {
      title: 'Auto sector shows signs of recovery amid festival demand',
      description: 'Automobile manufacturers report improved sales figures during festival season...',
      source: 'CNBC TV18',
      publishedAt: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(), // 3 hours ago
      url: 'https://example.com/news/5'
    },
    {
      title: 'Banking stocks mixed on credit growth concerns',
      description: 'Public sector banks outperform private peers on policy expectations...',
      source: 'BloombergQuint',
      publishedAt: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(), // 4 hours ago
      url: 'https://example.com/news/6'
    }
  ];
  
  return newsItems;
}

// Demo stock-specific news
function getDemoStockNews(symbol) {
  const stockNews = {
    'RELIANCE': [
      {
        title: `${symbol} announces expansion in renewable energy sector`,
        description: 'Company commits additional investment in clean energy projects...',
        source: 'Economic Times',
        publishedAt: new Date(Date.now() - 30 * 60 * 1000).toISOString()
      }
    ],
    'TCS': [
      {
        title: `${symbol} wins major digital transformation contract`,
        description: 'Leading IT services company secures multi-year deal with Fortune 500 client...',
        source: 'Business Standard',
        publishedAt: new Date(Date.now() - 45 * 60 * 1000).toISOString()
      }
    ],
    'INFY': [
      {
        title: `${symbol} reports strong quarterly performance`,
        description: 'Infosys beats analyst estimates with robust revenue growth...',
        source: 'Mint',
        publishedAt: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString()
      }
    ]
  };
  
  return stockNews[symbol] || [
    {
      title: `${symbol} in focus: Latest market updates`,
      description: `Recent developments and analyst views on ${symbol}...`,
      source: 'Market News',
      publishedAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString()
    }
  ];
}

// Get news sentiment analysis
router.get('/sentiment/:symbol', async (req, res) => {
  try {
    const { symbol } = req.params;
    const cacheKey = `sentiment:${symbol}`;
    
    let sentiment = await cache.get(cacheKey);
    
    if (!sentiment) {
      // In a real implementation, you would use a sentiment analysis service
      // like Google Cloud Natural Language API or AWS Comprehend
      sentiment = {
        symbol: symbol,
        overall: Math.random() > 0.5 ? 'positive' : 'negative',
        score: (Math.random() * 2 - 1).toFixed(2), // -1 to 1
        confidence: (Math.random() * 0.5 + 0.5).toFixed(2), // 0.5 to 1
        newsCount: Math.floor(Math.random() * 20) + 5,
        timestamp: new Date().toISOString()
      };
      
      await cache.set(cacheKey, sentiment, 1800); // Cache for 30 minutes
    }
    
    res.json({
      success: true,
      data: sentiment
    });
  } catch (error) {
    console.error(`Sentiment analysis error for ${req.params.symbol}:`, error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to analyze news sentiment'
    });
  }
});

module.exports = router;