# 🚀 Stock Analytics Pro - Complete Deployment Guide

This guide will help you deploy your Stock Analytics Pro application with real-time data integration.

## 📁 Project Structure

```
stock-analytics-pro/
├── backend/
│   ├── server.js
│   ├── package.json
│   ├── routes/
│   │   ├── stocks.js
│   │   ├── indices.js
│   │   └── news.js
│   ├── services/
│   │   ├── alphaVantage.js
│   │   ├── yahooFinance.js
│   │   └── websocket.js
│   ├── utils/
│   │   ├── cache.js
│   │   └── rateLimiter.js
│   └── .env
├── frontend/
│   ├── index.html
│   ├── css/
│   │   └── styles.css
│   ├── js/
│   │   ├── app.js
│   │   └── config.js
│   └── assets/
├── docker-compose.yml
├── Dockerfile
├── nginx.conf
└── README.md
```

## 🛠️ Step 1: Backend Setup

### package.json
```json
{
  "name": "stock-analytics-backend",
  "version": "1.0.0",
  "description": "Stock Analytics Pro Backend API",
  "main": "server.js",
  "scripts": {
    "start": "node server.js",
    "dev": "nodemon server.js",
    "test": "jest"
  },
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5",
    "dotenv": "^16.0.3",
    "axios": "^1.3.4",
    "ws": "^8.13.0",
    "redis": "^4.6.5",
    "node-cron": "^3.0.2",
    "helmet": "^6.1.5",
    "express-rate-limit": "^6.7.0",
    "compression": "^1.7.4"
  },
  "devDependencies": {
    "nodemon": "^2.0.22",
    "jest": "^29.5.0"
  },
  "engines": {
    "node": ">=16.0.0"
  }
}
```

### server.js
```javascript
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
require('dotenv').config();

const stockRoutes = require('./routes/stocks');
const indicesRoutes = require('./routes/indices');
const newsRoutes = require('./routes/news');
const WebSocketService = require('./services/websocket');

const app = express();
const PORT = process.env.PORT || 3000;

// Security middleware
app.use(helmet());
app.use(compression());
app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
  credentials: true
}));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 1000, // limit each IP to 1000 requests per windowMs
  message: 'Too many requests from this IP'
});
app.use(limiter);

app.use(express.json());
app.use(express.static('frontend'));

// API Routes
app.use('/api/stocks', stockRoutes);
app.use('/api/indices', indicesRoutes);
app.use('/api/news', newsRoutes);

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'OK', timestamp: new Date().toISOString() });
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Something went wrong!' });
});

// Start server
const server = app.listen(PORT, () => {
  console.log(`🚀 Stock Analytics Pro server running on port ${PORT}`);
});

// Initialize WebSocket server
const wsService = new WebSocketService(server);

process.on('SIGTERM', () => {
  console.log('SIGTERM received. Shutting down gracefully...');
  server.close(() => {
    process.exit(0);
  });
});
```

### services/alphaVantage.js
```javascript
const axios = require('axios');
const cache = require('../utils/cache');

class AlphaVantageService {
  constructor() {
    this.apiKey = process.env.ALPHA_VANTAGE_API_KEY;
    this.baseUrl = 'https://www.alphavantage.co/query';
    this.requestsPerMinute = 5; // Free tier limit
    this.requestQueue = [];
    this.isProcessing = false;
  }

  async getQuote(symbol) {
    const cacheKey = `quote:${symbol}`;
    const cached = await cache.get(cacheKey);
    
    if (cached) {
      return cached;
    }

    try {
      const response = await this.makeRequest({
        function: 'GLOBAL_QUOTE',
        symbol: symbol
      });

      const data = response.data['Global Quote'];
      const quote = {
        symbol: data['01. symbol'],
        price: parseFloat(data['05. price']),
        change: parseFloat(data['09. change']),
        changePercent: data['10. change percent'].replace('%', ''),
        volume: parseInt(data['06. volume']),
        timestamp: new Date().toISOString()
      };

      await cache.set(cacheKey, quote, 60); // Cache for 1 minute
      return quote;
    } catch (error) {
      console.error('Alpha Vantage API error:', error.message);
      throw error;
    }
  }

  async getTopGainersLosers() {
    const cacheKey = 'top_gainers_losers';
    const cached = await cache.get(cacheKey);
    
    if (cached) {
      return cached;
    }

    try {
      const response = await this.makeRequest({
        function: 'TOP_GAINERS_LOSERS'
      });

      const data = {
        gainers: response.data.top_gainers.slice(0, 5).map(stock => ({
          symbol: stock.ticker,
          price: parseFloat(stock.price),
          changePercent: parseFloat(stock.change_percentage.replace('%', ''))
        })),
        losers: response.data.top_losers.slice(0, 5).map(stock => ({
          symbol: stock.ticker,
          price: parseFloat(stock.price),
          changePercent: parseFloat(stock.change_percentage.replace('%', ''))
        }))
      };

      await cache.set(cacheKey, data, 300); // Cache for 5 minutes
      return data;
    } catch (error) {
      console.error('Error fetching gainers/losers:', error.message);
      throw error;
    }
  }

  async makeRequest(params) {
    return new Promise((resolve, reject) => {
      this.requestQueue.push({ params, resolve, reject });
      this.processQueue();
    });
  }

  async processQueue() {
    if (this.isProcessing || this.requestQueue.length === 0) {
      return;
    }

    this.isProcessing = true;
    const { params, resolve, reject } = this.requestQueue.shift();

    try {
      const response = await axios.get(this.baseUrl, {
        params: { ...params, apikey: this.apiKey },
        timeout: 10000
      });

      resolve(response);
      
      // Rate limiting: wait before next request
      setTimeout(() => {
        this.isProcessing = false;
        this.processQueue();
      }, 12000); // 12 seconds between requests (5 per minute)
      
    } catch (error) {
      reject(error);
      this.isProcessing = false;
      this.processQueue();
    }
  }
}

module.exports = new AlphaVantageService();
```

### services/yahooFinance.js
```javascript
const axios = require('axios');
const cache = require('../utils/cache');

class YahooFinanceService {
  constructor() {
    this.baseUrl = 'https://query1.finance.yahoo.com';
  }

  async getIndianIndices() {
    const symbols = [
      '^NSEI',    // Nifty 50
      '^NSEBANK', // Bank Nifty
      '^CNXIT',   // Nifty IT
      '^BSESN'    // Sensex
    ];

    const cacheKey = 'indian_indices';
    const cached = await cache.get(cacheKey);
    
    if (cached) {
      return cached;
    }

    try {
      const promises = symbols.map(symbol => this.getQuote(symbol));
      const results = await Promise.all(promises);
      
      const indices = results.map((result, index) => ({
        symbol: symbols[index],
        name: this.getIndexName(symbols[index]),
        ...result
      }));

      await cache.set(cacheKey, indices, 30); // Cache for 30 seconds
      return indices;
    } catch (error) {
      console.error('Error fetching Indian indices:', error.message);
      throw error;
    }
  }

  async getQuote(symbol) {
    try {
      const response = await axios.get(
        `${this.baseUrl}/v8/finance/chart/${symbol}`,
        { timeout: 5000 }
      );

      const data = response.data.chart.result[0];
      const meta = data.meta;
      const quote = data.indicators.quote[0];

      return {
        price: meta.regularMarketPrice,
        change: meta.regularMarketPrice - meta.previousClose,
        changePercent: ((meta.regularMarketPrice - meta.previousClose) / meta.previousClose * 100),
        volume: quote.volume[quote.volume.length - 1],
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      console.error(`Error fetching quote for ${symbol}:`, error.message);
      throw error;
    }
  }

  getIndexName(symbol) {
    const names = {
      '^NSEI': 'NIFTY 50',
      '^NSEBANK': 'BANK NIFTY',
      '^CNXIT': 'NIFTY IT',
      '^BSESN': 'SENSEX'
    };
    return names[symbol] || symbol;
  }
}

module.exports = new YahooFinanceService();
```

### routes/indices.js
```javascript
const express = require('express');
const router = express.Router();
const yahooService = require('../services/yahooFinance');
const alphaVantageService = require('../services/alphaVantage');

// Get market indices
router.get('/', async (req, res) => {
  try {
    // Try Yahoo Finance first for Indian indices
    const indices = await yahooService.getIndianIndices();
    res.json({
      success: true,
      data: indices,
      source: 'yahoo_finance'
    });
  } catch (error) {
    console.error('Indices API error:', error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch market indices'
    });
  }
});

// Get specific index
router.get('/:symbol', async (req, res) => {
  try {
    const { symbol } = req.params;
    const quote = await yahooService.getQuote(symbol);
    
    res.json({
      success: true,
      data: {
        symbol,
        name: yahooService.getIndexName(symbol),
        ...quote
      }
    });
  } catch (error) {
    console.error(`Error fetching ${req.params.symbol}:`, error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch index data'
    });
  }
});

module.exports = router;
```

### utils/cache.js
```javascript
const redis = require('redis');

class CacheService {
  constructor() {
    this.client = null;
    this.isConnected = false;
    this.init();
  }

  async init() {
    try {
      if (process.env.REDIS_URL) {
        this.client = redis.createClient({
          url: process.env.REDIS_URL
        });
        
        await this.client.connect();
        this.isConnected = true;
        console.log('✅ Redis connected');
      } else {
        console.log('⚠️  No Redis URL provided, using memory cache');
        this.memoryCache = new Map();
      }
    } catch (error) {
      console.error('Redis connection error:', error.message);
      this.memoryCache = new Map();
    }
  }

  async get(key) {
    try {
      if (this.isConnected) {
        const value = await this.client.get(key);
        return value ? JSON.parse(value) : null;
      } else {
        return this.memoryCache.get(key) || null;
      }
    } catch (error) {
      console.error('Cache get error:', error.message);
      return null;
    }
  }

  async set(key, value, ttlSeconds = 3600) {
    try {
      if (this.isConnected) {
        await this.client.setEx(key, ttlSeconds, JSON.stringify(value));
      } else {
        this.memoryCache.set(key, value);
        // Simple TTL for memory cache
        setTimeout(() => {
          this.memoryCache.delete(key);
        }, ttlSeconds * 1000);
      }
    } catch (error) {
      console.error('Cache set error:', error.message);
    }
  }

  async del(key) {
    try {
      if (this.isConnected) {
        await this.client.del(key);
      } else {
        this.memoryCache.delete(key);
      }
    } catch (error) {
      console.error('Cache delete error:', error.message);
    }
  }
}

module.exports = new CacheService();
```

## 🐳 Step 2: Docker Configuration

### Dockerfile
```dockerfile
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY backend/package*.json ./
RUN npm ci --only=production

# Copy backend source
COPY backend/ .

# Copy frontend files
COPY frontend/ ./frontend/

EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1

CMD ["npm", "start"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - ALPHA_VANTAGE_API_KEY=${ALPHA_VANTAGE_API_KEY}
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    command: redis-server --appendonly yes

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - app
    restart: unless-stopped

volumes:
  redis_data:
```

## 🚀 Step 3: Deployment Instructions

### Local Development Setup

1. **Clone and Setup:**
```bash
# Create project directory
mkdir stock-analytics-pro
cd stock-analytics-pro

# Create backend directory
mkdir backend
cd backend
npm init -y
npm install express cors dotenv axios ws redis helmet express-rate-limit compression
```

2. **Environment Variables:**
```bash
# Create .env file in backend directory
cat > .env << EOF
NODE_ENV=development
PORT=3000
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key_here
REDIS_URL=redis://localhost:6379
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
EOF
```

3. **Get API Keys:**

**Alpha Vantage (Recommended for beginners):**
- Go to: https://www.alphavantage.co/support/#api-key
- Sign up for free account
- Get API key (5 requests/minute free)
- Add to your .env file

**Alternative APIs:**
```bash
# Finnhub.io (Good real-time data)
FINNHUB_API_KEY=your_finnhub_key

# Polygon.io (Professional grade)
POLYGON_API_KEY=your_polygon_key
```

### Cloud Deployment Options

#### Option A: Heroku (Easiest)

1. **Install Heroku CLI:**
```bash
# Install Heroku CLI
npm install -g heroku

# Login to Heroku
heroku login
```

2. **Deploy to Heroku:**
```bash
# Create Heroku app
heroku create your-stock-analytics-app

# Add Redis addon
heroku addons:create heroku-redis:mini

# Set environment variables
heroku config:set ALPHA_VANTAGE_API_KEY=your_key_here
heroku config:set NODE_ENV=production

# Deploy
git init
git add .
git commit -m "Initial commit"
heroku git:remote -a your-stock-analytics-app
git push heroku main
```

#### Option B: DigitalOcean/AWS (Production)

1. **Create Droplet/EC2 Instance:**
```bash
# SSH into your server
ssh root@your-server-ip

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
```

2. **Deploy with Docker:**
```bash
# Clone your repository
git clone https://github.com/yourusername/stock-analytics-pro.git
cd stock-analytics-pro

# Create environment file
echo "ALPHA_VANTAGE_API_KEY=your_key_here" > .env

# Deploy
docker-compose up -d
```

#### Option C: Vercel (Frontend) + Railway (Backend)

1. **Frontend on Vercel:**
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy frontend
cd frontend
vercel --prod
```

2. **Backend on Railway:**
```bash
# Connect to Railway
npm install -g @railway/cli
railway login

# Deploy backend
cd backend
railway deploy
```

## 🔧 Step 4: Configuration & Testing

### API Testing

1. **Test Endpoints:**
```bash
# Test health endpoint
curl http://localhost:3000/health

# Test indices endpoint
curl http://localhost:3000/api/indices

# Test specific stock
curl http://localhost:3000/api/stocks/AAPL
```

2. **WebSocket Testing:**
```javascript
// Test WebSocket connection
const ws = new WebSocket('ws://localhost:3000');
ws.onopen = () => {
  ws.send(JSON.stringify({
    action: 'subscribe',
    symbols: ['AAPL', 'GOOGL']
  }));
};
```

### Performance Optimization

1. **Enable Caching:**
```bash
# Start Redis locally
redis-server

# Or use Docker
docker run -d -p 6379:6379 redis:alpine
```

2. **Monitor Performance:**
```javascript
// Add to server.js
const monitor = require('./utils/monitor');
app.use(monitor.requestLogger);
```

## 🔐 Step 5: Security & Production Checklist

### Security Configuration

1. **Environment Variables:**
```bash
# Production .env
NODE_ENV=production
API_RATE_LIMIT=1000
SESSION_SECRET=your-long-random-string
CORS_ORIGINS=https://yourdomain.com
```

2. **SSL Certificate:**
```bash
# Using Certbot for free SSL
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### Monitoring & Logging

1. **Add Logging:**
```javascript
const winston = require('winston');
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.json(),
  transports: [
    new winston.transports.File({ filename: 'error.log', level: 'error' }),
    new winston.transports.File({ filename: 'combined.log' })
  ]
});
```

2. **Health Monitoring:**
```bash
# Add to your server monitoring
curl -f http://yourapp.com/health || alert "App is down!"
```

## 🎯 Quick Start Commands

```bash
# 1. Get API key from Alpha Vantage
echo "Get your API key: https://www.alphavantage.co/support/#api-key"

# 2. Clone and setup
git clone <your-repo>
cd stock-analytics-pro/backend
npm install

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 4. Start development
npm run dev

# 5. Deploy to production
docker-compose up -d
```

## 🚀 Next Steps After Deployment

1. **Domain Setup:** Configure your custom domain
2. **SSL Certificate:** Enable HTTPS with Let's Encrypt
3. **CDN Setup:** Use Cloudflare for better performance
4. **Monitoring:** Set up Uptime Robot or similar
5. **Analytics:** Add Google Analytics for usage tracking
6. **Backup:** Configure automated database backups

Your Stock Analytics Pro app will be live and serving real-time market data! 📈

---

**Need Help?** 
- Check logs: `docker-compose logs app`
- Monitor performance: Use built-in `/health` endpoint
- Scale up: Add more instances behind load balancer