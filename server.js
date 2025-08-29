const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const path = require('path');
const WebSocket = require('ws');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

// Import routes
const stockRoutes = require('./routes/stocks');
const indicesRoutes = require('./routes/indices');
const newsRoutes = require('./routes/news');

// Security middleware
app.use(helmet({
  contentSecurityPolicy: false,
  crossOriginEmbedderPolicy: false
}));
app.use(compression());
app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000', 'http://localhost:3001', 'http://localhost:8080'],
  credentials: true
}));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 1000,
  message: { error: 'Too many requests from this IP' },
  standardHeaders: true,
  legacyHeaders: false,
});
app.use('/api/', limiter);

app.use(express.json());
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Create frontend directory if it doesn't exist and serve static files
app.use(express.static(path.join(__dirname, 'frontend')));
app.use(express.static(path.join(__dirname, 'public')));

// API Routes
app.use('/api/stocks', stockRoutes);
app.use('/api/indices', indicesRoutes);
app.use('/api/news', newsRoutes);

// Health check
app.get('/health', (req, res) => {
  res.json({ 
    status: 'OK', 
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    environment: process.env.NODE_ENV || 'development',
    version: '1.0.0'
  });
});

// Dashboard endpoint
app.get('/dashboard', (req, res) => {
  res.json({
    status: 'OK',
    message: 'Stock Analytics Pro Dashboard API',
    endpoints: {
      health: '/health',
      stocks: '/api/stocks',
      indices: '/api/indices',
      news: '/api/news'
    },
    timestamp: new Date().toISOString()
  });
});

// Serve the main dashboard or default page
app.get('*', (req, res) => {
  if (!req.path.startsWith('/api/')) {
    // Try to serve index.html from frontend or public directory
    const frontendPath = path.join(__dirname, 'frontend', 'index.html');
    const publicPath = path.join(__dirname, 'public', 'index.html');
    
    // Check if frontend/index.html exists
    const fs = require('fs');
    if (fs.existsSync(frontendPath)) {
      res.sendFile(frontendPath);
    } else if (fs.existsSync(publicPath)) {
      res.sendFile(publicPath);
    } else {
      // Serve a default HTML page
      res.send(`
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Stock Analytics Pro</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                h1 { color: #333; text-align: center; }
                .endpoints { background: #f8f9fa; padding: 20px; border-radius: 4px; margin: 20px 0; }
                .endpoint { margin: 10px 0; }
                .endpoint a { color: #007bff; text-decoration: none; }
                .endpoint a:hover { text-decoration: underline; }
                .status { background: #d4edda; color: #155724; padding: 10px; border-radius: 4px; text-align: center; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 Stock Analytics Pro</h1>
                <div class="status">✅ Server is running successfully!</div>
                <div class="endpoints">
                    <h3>Available API Endpoints:</h3>
                    <div class="endpoint">📊 <a href="/api/stocks">Stocks Data</a> - Get stock information</div>
                    <div class="endpoint">📈 <a href="/api/indices">Market Indices</a> - Get market indices data</div>
                    <div class="endpoint">📰 <a href="/api/news">Financial News</a> - Get latest financial news</div>
                    <div class="endpoint">🏥 <a href="/health">Health Check</a> - Server health status</div>
                    <div class="endpoint">📱 <a href="/dashboard">Dashboard Info</a> - API information</div>
                </div>
                <div style="text-align: center; margin-top: 30px; color: #666;">
                    <p>Stock Analytics Pro v1.0.0</p>
                    <p>Server uptime: <span id="uptime">Loading...</span></p>
                </div>
            </div>
            <script>
                fetch('/health')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('uptime').textContent = Math.floor(data.uptime) + ' seconds';
                    })
                    .catch(error => {
                        document.getElementById('uptime').textContent = 'Error loading';
                    });
            </script>
        </body>
        </html>
      `);
    }
  } else {
    res.status(404).json({ error: 'API endpoint not found' });
  }
});

// Error handling
app.use((err, req, res, next) => {
  console.error('Server Error:', err.stack);
  res.status(500).json({ 
    error: 'Something went wrong!',
    message: process.env.NODE_ENV === 'development' ? err.message : 'Internal server error'
  });
});

// Start server
const server = app.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 Stock Analytics Pro server running on port ${PORT}`);
  console.log(`📊 Dashboard available at: http://localhost:${PORT}`);
  console.log(`🌍 Environment: ${process.env.NODE_ENV || 'development'}`);
  console.log(`📡 API Endpoints:`);
  console.log(`   - Health: http://localhost:${PORT}/health`);
  console.log(`   - Stocks: http://localhost:${PORT}/api/stocks`);
  console.log(`   - Indices: http://localhost:${PORT}/api/indices`);
  console.log(`   - News: http://localhost:${PORT}/api/news`);
});

// WebSocket server
const wss = new WebSocket.Server({ server, path: '/ws' });
wss.on('connection', (ws, req) => {
  console.log('New WebSocket connection');
  
  ws.on('message', (message) => {
    try {
      const data = JSON.parse(message);
      if (data.action === 'subscribe') {
        ws.send(JSON.stringify({
          type: 'subscription_confirmed',
          symbols: data.symbols,
          message: 'Subscribed to real-time updates'
        }));
      }
    } catch (error) {
      console.error('WebSocket error:', error);
    }
  });
  
  // Send welcome message
  ws.send(JSON.stringify({ 
    type: 'connected', 
    message: 'Connected to Stock Analytics Pro',
    timestamp: new Date().toISOString()
  }));
  
  // Send periodic updates
  const interval = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'market_update',
        data: {
          timestamp: new Date().toISOString(),
          nifty: 19847 + (Math.random() - 0.5) * 100,
          sensex: 66589 + (Math.random() - 0.5) * 500
        }
      }));
    }
  }, 5000);
  
  ws.on('close', () => {
    clearInterval(interval);
  });
});

// Graceful shutdown
const gracefulShutdown = (signal) => {
  console.log(`Received ${signal}. Graceful shutdown...`);
  server.close(() => {
    wss.close(() => {
      console.log('Server shutdown complete');
      process.exit(0);
    });
  });
};

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));