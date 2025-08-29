const WebSocket = require('ws');
const yahooService = require('./yahooFinance');

class WebSocketService {
  constructor(server) {
    this.wss = new WebSocket.Server({ server, path: '/ws' });
    this.clients = new Map();
    this.subscriptions = new Map();
    this.updateInterval = null;
    
    this.initialize();
  }

  initialize() {
    console.log('🔌 WebSocket server initialized');
    
    this.wss.on('connection', (ws, req) => {
      const clientId = this.generateClientId();
      const clientIP = req.socket.remoteAddress;
      
      console.log(`📱 Client connected: ${clientId} from ${clientIP}`);
      
      // Store client connection
      this.clients.set(clientId, {
        ws,
        subscriptions: new Set(),
        connectedAt: new Date(),
        lastPing: new Date()
      });

      // Send welcome message
      this.sendToClient(clientId, {
        type: 'connection',
        status: 'connected',
        clientId: clientId,
        timestamp: new Date().toISOString()
      });

      // Handle incoming messages
      ws.on('message', (data) => {
        try {
          const message = JSON.parse(data);
          this.handleClientMessage(clientId, message);
        } catch (error) {
          console.error(`Invalid JSON from client ${clientId}:`, error.message);
          this.sendError(clientId, 'Invalid JSON format');
        }
      });

      // Handle client disconnect
      ws.on('close', (code, reason) => {
        console.log(`📱 Client disconnected: ${clientId} (${code}: ${reason})`);
        this.handleClientDisconnect(clientId);
      });

      // Handle connection errors
      ws.on('error', (error) => {
        console.error(`WebSocket error for client ${clientId}:`, error.message);
        this.handleClientDisconnect(clientId);
      });

      // Setup ping/pong for connection health
      ws.on('pong', () => {
        const client = this.clients.get(clientId);
        if (client) {
          client.lastPing = new Date();
        }
      });
    });

    // Start periodic updates
    this.startPeriodicUpdates();
    
    // Setup heartbeat check
    this.setupHeartbeat();
  }

  generateClientId() {
    return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  handleClientMessage(clientId, message) {
    const { action, type, symbols, symbol, data } = message;

    switch (action || type) {
      case 'subscribe':
        this.handleSubscription(clientId, symbols || [symbol]);
        break;
        
      case 'unsubscribe':
        this.handleUnsubscription(clientId, symbols || [symbol]);
        break;
        
      case 'ping':
        this.sendToClient(clientId, { type: 'pong', timestamp: new Date().toISOString() });
        break;
        
      case 'get_quote':
        this.handleQuoteRequest(clientId, symbol);
        break;
        
      case 'get_indices':
        this.handleIndicesRequest(clientId);
        break;
        
      default:
        console.log(`Unknown action from client ${clientId}:`, action || type);
        this.sendError(clientId, `Unknown action: ${action || type}`);
    }
  }

  handleSubscription(clientId, symbols) {
    const client = this.clients.get(clientId);
    if (!client) return;

    symbols.forEach(symbol => {
      // Add symbol to client subscriptions
      client.subscriptions.add(symbol);
      
      // Add client to global subscriptions
      if (!this.subscriptions.has(symbol)) {
        this.subscriptions.set(symbol, new Set());
      }
      this.subscriptions.get(symbol).add(clientId);
      
      console.log(`📈 Client ${clientId} subscribed to ${symbol}`);
    });

    this.sendToClient(clientId, {
      type: 'subscription_confirmed',
      symbols: symbols,
      timestamp: new Date().toISOString()
    });

    // Send initial data for subscribed symbols
    this.sendInitialData(clientId, symbols);
  }

  handleUnsubscription(clientId, symbols) {
    const client = this.clients.get(clientId);
    if (!client) return;

    symbols.forEach(symbol => {
      // Remove from client subscriptions
      client.subscriptions.delete(symbol);
      
      // Remove client from global subscriptions
      const symbolSubs = this.subscriptions.get(symbol);
      if (symbolSubs) {
        symbolSubs.delete(clientId);
        if (symbolSubs.size === 0) {
          this.subscriptions.delete(symbol);
        }
      }
      
      console.log(`📉 Client ${clientId} unsubscribed from ${symbol}`);
    });

    this.sendToClient(clientId, {
      type: 'unsubscription_confirmed',
      symbols: symbols,
      timestamp: new Date().toISOString()
    });
  }

  async handleQuoteRequest(clientId, symbol) {
    try {
      const quote = await yahooService.getQuote(symbol);
      this.sendToClient(clientId, {
        type: 'quote',
        symbol: symbol,
        data: quote,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      this.sendError(clientId, `Failed to get quote for ${symbol}: ${error.message}`);
    }
  }

  async handleIndicesRequest(clientId) {
    try {
      const indices = await yahooService.getIndianIndices();
      this.sendToClient(clientId, {
        type: 'indices',
        data: indices,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      this.sendError(clientId, `Failed to get indices: ${error.message}`);
    }
  }

  async sendInitialData(clientId, symbols) {
    try {
      for (const symbol of symbols) {
        // Send current quote data
        await this.handleQuoteRequest(clientId, symbol);
        
        // Add small delay to avoid overwhelming the client
        await new Promise(resolve => setTimeout(resolve, 100));
      }
    } catch (error) {
      console.error(`Error sending initial data to ${clientId}:`, error.message);
    }
  }

  handleClientDisconnect(clientId) {
    const client = this.clients.get(clientId);
    if (!client) return;

    // Remove client from all symbol subscriptions
    client.subscriptions.forEach(symbol => {
      const symbolSubs = this.subscriptions.get(symbol);
      if (symbolSubs) {
        symbolSubs.delete(clientId);
        if (symbolSubs.size === 0) {
          this.subscriptions.delete(symbol);
        }
      }
    });

    // Remove client from clients map
    this.clients.delete(clientId);
  }

  sendToClient(clientId, data) {
    const client = this.clients.get(clientId);
    if (!client || client.ws.readyState !== WebSocket.OPEN) {
      return false;
    }

    try {
      client.ws.send(JSON.stringify(data));
      return true;
    } catch (error) {
      console.error(`Failed to send data to client ${clientId}:`, error.message);
      this.handleClientDisconnect(clientId);
      return false;
    }
  }

  sendError(clientId, message) {
    this.sendToClient(clientId, {
      type: 'error',
      message: message,
      timestamp: new Date().toISOString()
    });
  }

  broadcast(data, filterFn = null) {
    let sentCount = 0;
    
    this.clients.forEach((client, clientId) => {
      if (filterFn && !filterFn(clientId, client)) {
        return;
      }
      
      if (this.sendToClient(clientId, data)) {
        sentCount++;
      }
    });
    
    return sentCount;
  }

  broadcastToSubscribers(symbol, data) {
    const subscribers = this.subscriptions.get(symbol);
    if (!subscribers) return 0;

    let sentCount = 0;
    subscribers.forEach(clientId => {
      if (this.sendToClient(clientId, { ...data, symbol })) {
        sentCount++;
      }
    });
    
    return sentCount;
  }

  startPeriodicUpdates() {
    // Update market data every 30 seconds
    this.updateInterval = setInterval(async () => {
      try {
        await this.updateMarketData();
      } catch (error) {
        console.error('Periodic update error:', error.message);
      }
    }, 30000);

    console.log('⏰ Periodic updates started (30s interval)');
  }

  async updateMarketData() {
    const uniqueSymbols = Array.from(this.subscriptions.keys());
    
    if (uniqueSymbols.length === 0) {
      return; // No active subscriptions
    }

    console.log(`🔄 Updating ${uniqueSymbols.length} symbols for ${this.clients.size} clients`);

    // Update indices first (commonly subscribed)
    try {
      const indices = await yahooService.getIndianIndices();
      indices.forEach(index => {
        this.broadcastToSubscribers(index.symbol, {
          type: 'quote_update',
          data: index,
          timestamp: new Date().toISOString()
        });
      });
    } catch (error) {
      console.error('Error updating indices:', error.message);
    }

    // Update individual stocks
    for (const symbol of uniqueSymbols) {
      try {
        // Skip if it's an index (already updated above)
        if (symbol.startsWith('^')) continue;
        
        const quote = await yahooService.getQuote(`${symbol}.NS`);
        this.broadcastToSubscribers(symbol, {
          type: 'quote_update',
          data: quote,
          timestamp: new Date().toISOString()
        });
        
        // Small delay to avoid overwhelming APIs
        await new Promise(resolve => setTimeout(resolve, 200));
      } catch (error) {
        console.error(`Error updating ${symbol}:`, error.message);
      }
    }
  }

  setupHeartbeat() {
    // Send ping to all clients every 45 seconds
    setInterval(() => {
      this.clients.forEach((client, clientId) => {
        if (client.ws.readyState === WebSocket.OPEN) {
          client.ws.ping();
          
          // Check if client hasn't responded to ping in 60 seconds
          const timeSinceLastPing = Date.now() - client.lastPing.getTime();
          if (timeSinceLastPing > 60000) {
            console.log(`⚠️  Client ${clientId} not responding to pings, disconnecting`);
            client.ws.terminate();
            this.handleClientDisconnect(clientId);
          }
        }
      });
    }, 45000);
  }

  // Admin/monitoring methods
  getStats() {
    return {
      connectedClients: this.clients.size,
      activeSubscriptions: this.subscriptions.size,
      totalSubscriptions: Array.from(this.subscriptions.values())
        .reduce((total, subs) => total + subs.size, 0),
      uptime: process.uptime(),
      memoryUsage: process.memoryUsage()
    };
  }

  getClientInfo() {
    const clientInfo = [];
    this.clients.forEach((client, clientId) => {
      clientInfo.push({
        id: clientId,
        connectedAt: client.connectedAt,
        subscriptions: Array.from(client.subscriptions),
        lastPing: client.lastPing
      });
    });
    return clientInfo;
  }

  // Graceful shutdown
  shutdown() {
    console.log('🔌 Shutting down WebSocket server...');
    
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
    }

    // Notify all clients of shutdown
    this.broadcast({
      type: 'server_shutdown',
      message: 'Server is shutting down',
      timestamp: new Date().toISOString()
    });

    // Close all connections
    this.clients.forEach((client, clientId) => {
      client.ws.close(1001, 'Server shutdown');
    });

    this.wss.close();
  }
}

module.exports = WebSocketService;