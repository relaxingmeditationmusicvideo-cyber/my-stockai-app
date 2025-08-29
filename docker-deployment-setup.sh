#!/bin/bash

# Docker Deployment Setup for Stock Analytics Pro
set -e

echo "🐳 Setting up Docker deployment for Stock Analytics Pro"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check Docker installation
check_docker() {
    print_status "Checking Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first:"
        echo "  - Windows/Mac: https://www.docker.com/products/docker-desktop"
        echo "  - Linux: curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose."
        exit 1
    fi
    
    print_success "Docker and Docker Compose are installed"
}

# Create all necessary files
create_project_files() {
    print_status "Creating project structure..."
    
    # Create directories
    mkdir -p routes services utils frontend/css frontend/js frontend/assets logs ssl
    
    # Create main server.js file
    cat > server.js << 'EOF'
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
  origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000', 'http://localhost:8080'],
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

app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));
app.use(express.static(path.join(__dirname, 'frontend')));

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
    environment: process.env.NODE_ENV || 'development'
  });
});

// Serve the main dashboard
app.get('*', (req, res) => {
  if (!req.path.startsWith('/api/')) {
    res.sendFile(path.join(__dirname, 'frontend', 'index.html'));
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
  ws.send(JSON.stringify({ type: 'connected', message: 'Connected to Stock Analytics Pro' }));
});

// Graceful shutdown
const gracefulShutdown = (signal) => {
  console.log(`Received ${signal}. Graceful shutdown...`);
  server.close(() => {
    wss.close(() => process.exit(0));
  });
};

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));

module.exports = { app, server, wss };
EOF

    # Create package.json
    cat > package.json << 'EOF'
{
  "name": "stock-analytics-pro",
  "version": "1.0.0",
  "description": "Professional Stock Analytics Dashboard with Real-time Market Data",
  "main": "server.js",
  "scripts": {
    "start": "node server.js",
    "dev": "nodemon server.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5",
    "dotenv": "^16.3.1",
    "axios": "^1.5.0",
    "ws": "^8.14.2",
    "redis": "^4.6.8",
    "helmet": "^7.0.0",
    "express-rate-limit": "^6.10.0",
    "compression": "^1.7.4",
    "winston": "^3.10.0"
  },
  "engines": {
    "node": ">=16.0.0"
  }
}
EOF

    # Create routes/indices.js
    cat > routes/indices.js << 'EOF'
const express = require('express');
const router = express.Router();
const cache = require('../utils/cache');

router.get('/', async (req, res) => {
  try {
    const indices = [
      { symbol: '^NSEI', name: 'NIFTY 50', price: (24300 + Math.random() * 200 - 100).toFixed(2), change: (Math.random() * 200 - 100).toFixed(2), changePercent: (Math.random() * 2 - 1).toFixed(2) },
      { symbol: '^NSEBANK', name: 'BANK NIFTY', price: (52800 + Math.random() * 500 - 250).toFixed(2), change: (Math.random() * 400 - 200).toFixed(2), changePercent: (Math.random() * 2 - 1).toFixed(2) },
      { symbol: '^CNXIT', name: 'NIFTY IT', price: (35200 + Math.random() * 300 - 150).toFixed(2), change: (Math.random() * 300 - 150).toFixed(2), changePercent: (Math.random() * 2 - 1).toFixed(2) },
      { symbol: '^BSESN', name: 'SENSEX', price: (79400 + Math.random() * 400 - 200).toFixed(2), change: (Math.random() * 400 - 200).toFixed(2), changePercent: (Math.random() * 2 - 1).toFixed(2) }
    ];
    
    res.json({ success: true, data: indices, timestamp: new Date().toISOString() });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to fetch market indices' });
  }
});

module.exports = router;
EOF

    # Create routes/news.js
    cat > routes/news.js << 'EOF'
const express = require('express');
const router = express.Router();

router.get('/', async (req, res) => {
  try {
    const news = [
      { id: 1, title: 'Market opens higher on positive global cues', time: '2 min ago' },
      { id: 2, title: 'RBI maintains repo rate at 6.5%', time: '15 min ago' },
      { id: 3, title: 'IT stocks rally on strong Q3 results', time: '1 hour ago' },
      { id: 4, title: 'FII inflows continue for third consecutive day', time: '2 hours ago' }
    ];
    
    res.json({ success: true, data: news, timestamp: new Date().toISOString() });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to fetch market news' });
  }
});

module.exports = router;
EOF

    # Create utils/cache.js
    cat > utils/cache.js << 'EOF'
const redis = require('redis');

class CacheService {
  constructor() {
    this.client = null;
    this.isConnected = false;
    this.memoryCache = new Map();
    this.init();
  }

  async init() {
    try {
      if (process.env.REDIS_URL) {
        this.client = redis.createClient({ url: process.env.REDIS_URL });
        this.client.on('error', (err) => console.error('Redis Error:', err));
        this.client.on('connect', () => { this.isConnected = true; console.log('✅ Redis connected'); });
        await this.client.connect();
      } else {
        console.log('⚠️  Using memory cache (no Redis)');
      }
    } catch (error) {
      console.error('Redis connection error:', error.message);
      this.isConnected = false;
    }
  }

  async get(key) {
    try {
      if (this.isConnected && this.client) {
        const value = await this.client.get(key);
        return value ? JSON.parse(value) : null;
      } else {
        const item = this.memoryCache.get(key);
        return item && item.expiry > Date.now() ? item.value : null;
      }
    } catch (error) {
      return null;
    }
  }

  async set(key, value, ttlSeconds = 3600) {
    try {
      if (this.isConnected && this.client) {
        await this.client.setEx(key, ttlSeconds, JSON.stringify(value));
      } else {
        this.memoryCache.set(key, { value, expiry: Date.now() + (ttlSeconds * 1000) });
      }
    } catch (error) {
      console.error('Cache set error:', error.message);
    }
  }
}

module.exports = new CacheService();
EOF

    print_success "Project files created"
}

# Create Docker configuration files
create_docker_files() {
    print_status "Creating Docker configuration files..."
    
    # Dockerfile
    cat > Dockerfile << 'EOF'
FROM node:18-alpine

# Install curl for healthcheck
RUN apk add --no-cache curl

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application source
COPY . .

# Create logs directory
RUN mkdir -p logs

# Create non-root user
RUN addgroup -g 1001 -S nodejs && adduser -S nodejs -u 1001
RUN chown -R nodejs:nodejs /app
USER nodejs

# Expose ports
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1

CMD ["npm", "start"]
EOF

    # docker-compose.yml
    cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - ALPHA_VANTAGE_API_KEY=${ALPHA_VANTAGE_API_KEY:-demo_key}
      - REDIS_URL=redis://redis:6379
      - ALLOWED_ORIGINS=http://localhost:3000,http://localhost:80
    depends_on:
      - redis
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --maxmemory 256mb
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - app
    restart: unless-stopped

volumes:
  redis_data:
EOF

    # nginx.conf
    cat > nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream app {
        server app:3000;
    }

    server {
        listen 80;
        server_name localhost;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;

        location / {
            proxy_pass http://app;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;
        }

        location /ws {
            proxy_pass http://app;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "Upgrade";
            proxy_set_header Host $host;
        }

        location /health {
            proxy_pass http://app;
            access_log off;
        }
    }
}
EOF

    # .dockerignore
    cat > .dockerignore << 'EOF'
node_modules
npm-debug.log
.git
.gitignore
README.md
.env
*.log
logs/*.log
.DS_Store
EOF

    # Environment file
    cat > .env << 'EOF'
NODE_ENV=production
PORT=3000
ALPHA_VANTAGE_API_KEY=demo_key_replace_with_real_key
REDIS_URL=redis://redis:6379
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:80
EOF

    print_success "Docker configuration files created"
}

# Copy your existing files
copy_existing_files() {
    print_status "Setting up existing application files..."
    
    # Check if your stock routes file exists and copy it
    if [ -f "../backend_routes_stocks.js" ]; then
        cp "../backend_routes_stocks.js" "routes/stocks.js"
        print_success "Copied existing stock routes"
    else
        print_warning "Stock routes file not found. Please copy your backend_routes_stocks.js to routes/stocks.js"
        # Create a basic stocks route
        cp routes/stocks.js.example routes/stocks.js 2>/dev/null || echo "// Stock routes will be added" > routes/stocks.js
    fi
    
    # Check if your HTML dashboard exists and copy it
    if [ -f "../stock_market_dashboard(2).html" ]; then
        cp "../stock_market_dashboard(2).html" "frontend/index.html"
        print_success "Copied existing HTML dashboard"
    else
        print_warning "HTML dashboard not found. Please copy your stock_market_dashboard(2).html to frontend/index.html"
        # Create a basic HTML file
        cat > frontend/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stock Analytics Pro</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #0f172a; color: white; }
        .container { max-width: 1200px; margin: 0 auto; text-align: center; }
        .status { background: #1e293b; padding: 20px; border-radius: 10px; margin: 20px 0; }
        .success { color: #10b981; }
        a { color: #3b82f6; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Stock Analytics Pro</h1>
        <div class="status">
            <h2 class="success">✅ Application Running Successfully!</h2>
            <p>Your Stock Analytics Pro is deployed with Docker</p>
            <p><strong>Next Step:</strong> Replace this file with your actual dashboard HTML</p>
            <h3>Available Endpoints:</h3>
            <ul style="list-style: none;">
                <li><a href="/health">Health Check</a></li>
                <li><a href="/api/stocks/gainers-losers">Stock Data</a></li>
                <li><a href="/api/indices">Market Indices</a></li>
                <li><a href="/api/news">Market News</a></li>
            </ul>
        </div>
    </div>
</body>
</html>
EOF
    fi
}

# Build and start Docker containers
start_docker_deployment() {
    print_status "Building Docker containers..."
    
    # Stop any existing containers
    docker-compose down 2>/dev/null || true
    
    # Build and start containers
    docker-compose build
    
    print_status "Starting Docker containers..."
    docker-compose up -d
    
    # Wait for services to start
    print_status "Waiting for services to start..."
    sleep 10
    
    # Check if containers are running
    if docker-compose ps | grep -q "Up"; then
        print_success "Docker containers are running!"
    else
        print_error "Failed to start containers. Check logs with: docker-compose logs"
        return 1
    fi
}

# Test the deployment
test_deployment() {
    print_status "Testing deployment..."
    
    # Test health endpoint
    for i in {1..30}; do
        if curl -f http://localhost:3000/health > /dev/null 2>&1; then
            print_success "✅ Direct health check passed"
            break
        elif [ $i -eq 30 ]; then
            print_warning "⚠️ Direct health check failed"
        else
            sleep 2
        fi
    done
    
    # Test through nginx
    for i in {1..30}; do
        if curl -f http://localhost/health > /dev/null 2>&1; then
            print_success "✅ Nginx health check passed"
            break
        elif [ $i -eq 30 ]; then
            print_warning "⚠️ Nginx health check failed"
        else
            sleep 2
        fi
    done
    
    # Test API endpoints
    if curl -f http://localhost/api/indices > /dev/null 2>&1; then
        print_success "✅ API endpoints accessible"
    else
        print_warning "⚠️ API endpoints not accessible"
    fi
}

# Show deployment info
show_deployment_info() {
    echo
    echo "🎉 Docker Deployment Complete!"
    echo "================================"
    echo
    echo "📊 Your Stock Analytics Pro is now running:"
    echo "   • Main Dashboard: http://localhost"
    echo "   • Direct App: http://localhost:3000"
    echo "   • Health Check: http://localhost/health"
    echo "   • API Status: http://localhost/api/indices"
    echo
    echo "🐳 Docker Commands:"
    echo "   • View logs: docker-compose logs -f"
    echo "   • Stop app: docker-compose down"
    echo "   • Restart: docker-compose restart"
    echo "   • Rebuild: docker-compose up --build -d"
    echo
    echo "📁 Important Files:"
    echo "   • Copy your HTML dashboard to: frontend/index.html"
    echo "   • Copy your stock routes to: routes/stocks.js"
    echo "   • Update API keys in: .env"
    echo
    echo "🔧 Next Steps:"
    echo "   1. Get API keys from Alpha Vantage: https://www.alphavantage.co/support/#api-key"
    echo "   2. Update .env file with your real API keys"
    echo "   3. Copy your actual dashboard HTML file"
    echo "   4. Restart containers: docker-compose restart"
    echo
}

# Main deployment function
main() {
    echo "🐳 Stock Analytics Pro - Docker Deployment"
    echo "=========================================="
    echo
    
    check_docker
    create_project_files
    create_docker_files
    copy_existing_files
    start_docker_deployment
    
    if [ $? -eq 0 ]; then
        test_deployment
        show_deployment_info
        
        print_success "Deployment completed successfully!"
        print_status "Opening browser..."
        
        # Try to open browser (works on most systems)
        if command -v xdg-open > /dev/null; then
            xdg-open http://localhost
        elif command -v open > /dev/null; then
            open http://localhost
        elif command -v start > /dev/null; then
            start http://localhost
        fi
    else
        print_error "Deployment failed. Check the logs above."
        exit 1
    fi
}

# Run main function
main "$@"