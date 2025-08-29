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
