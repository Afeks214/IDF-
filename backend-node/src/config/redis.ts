import Redis, { RedisOptions } from 'ioredis';
import { env } from './env';

// Redis configuration with security and performance optimizations
const redisConfig: RedisOptions = {
  host: env.REDIS_HOST,
  port: env.REDIS_PORT,
  password: env.REDIS_PASSWORD || undefined,
  db: env.REDIS_DB,
  
  // Connection settings
  connectTimeout: 10000,
  commandTimeout: 10000,
  retryDelayOnFailover: 100,
  maxRetriesPerRequest: 3,
  
  // Connection pool settings
  lazyConnect: true,
  keepAlive: 30000,
  
  // Security settings
  tls: env.NODE_ENV === 'production' ? {} : undefined,
  
  // Performance settings
  maxmemoryPolicy: 'allkeys-lru',
  
  // Retry strategy for resilience
  retryStrategy(times: number) {
    const delay = Math.min(times * 50, 2000);
    return delay;
  },
  
  // Reconnect on error
  reconnectOnError(err: Error) {
    const targetError = 'READONLY';
    return err.message.includes(targetError);
  },
};

export class RedisManager {
  private static instance: RedisManager;
  private client: Redis;
  private isConnected = false;

  private constructor() {
    this.client = new Redis(redisConfig);
    this.setupEventHandlers();
  }

  public static getInstance(): RedisManager {
    if (!RedisManager.instance) {
      RedisManager.instance = new RedisManager();
    }
    return RedisManager.instance;
  }

  private setupEventHandlers(): void {
    this.client.on('connect', () => {
      console.log('🔗 Redis connection established');
      this.isConnected = true;
    });

    this.client.on('ready', () => {
      console.log('✅ Redis client ready');
    });

    this.client.on('error', (error) => {
      console.error('❌ Redis connection error:', error);
      this.isConnected = false;
    });

    this.client.on('close', () => {
      console.log('🔌 Redis connection closed');
      this.isConnected = false;
    });

    this.client.on('reconnecting', () => {
      console.log('🔄 Redis reconnecting...');
    });
  }

  async connect(): Promise<void> {
    try {
      await this.client.connect();
      console.log('✅ Redis connected successfully');
    } catch (error) {
      console.error('❌ Redis connection failed:', error);
      throw new Error(`Redis connection failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  async disconnect(): Promise<void> {
    try {
      await this.client.quit();
      console.log('✅ Redis disconnected successfully');
    } catch (error) {
      console.error('❌ Error disconnecting Redis:', error);
    }
  }

  getClient(): Redis {
    if (!this.isConnected) {
      throw new Error('Redis not connected. Call connect() first.');
    }
    return this.client;
  }

  isConnectionActive(): boolean {
    return this.isConnected && this.client.status === 'ready';
  }

  // Cache operations with Hebrew support
  async set(key: string, value: any, ttl?: number): Promise<void> {
    try {
      const serializedValue = JSON.stringify(value);
      if (ttl) {
        await this.client.setex(key, ttl, serializedValue);
      } else {
        await this.client.set(key, serializedValue);
      }
    } catch (error) {
      console.error('Redis set error:', error);
      throw error;
    }
  }

  async get<T>(key: string): Promise<T | null> {
    try {
      const value = await this.client.get(key);
      return value ? JSON.parse(value) : null;
    } catch (error) {
      console.error('Redis get error:', error);
      throw error;
    }
  }

  async del(key: string): Promise<void> {
    try {
      await this.client.del(key);
    } catch (error) {
      console.error('Redis delete error:', error);
      throw error;
    }
  }

  async exists(key: string): Promise<boolean> {
    try {
      const result = await this.client.exists(key);
      return result === 1;
    } catch (error) {
      console.error('Redis exists error:', error);
      throw error;
    }
  }

  // Session management for JWT blacklisting
  async blacklistToken(token: string, expiresIn: number): Promise<void> {
    const key = `blacklist:${token}`;
    await this.set(key, true, expiresIn);
  }

  async isTokenBlacklisted(token: string): Promise<boolean> {
    const key = `blacklist:${token}`;
    return await this.exists(key);
  }

  // Rate limiting support
  async incrementRateLimit(key: string, window: number): Promise<number> {
    try {
      const multi = this.client.multi();
      multi.incr(key);
      multi.expire(key, window);
      const results = await multi.exec();
      return results?.[0]?.[1] as number || 0;
    } catch (error) {
      console.error('Redis rate limit error:', error);
      throw error;
    }
  }

  // Health check for monitoring
  async healthCheck(): Promise<{ status: 'healthy' | 'unhealthy'; latency?: number; error?: string }> {
    try {
      const startTime = Date.now();
      await this.client.ping();
      const latency = Date.now() - startTime;
      
      return {
        status: 'healthy',
        latency
      };
    } catch (error) {
      return {
        status: 'unhealthy',
        error: error instanceof Error ? error.message : 'Unknown Redis error'
      };
    }
  }
}

// Export singleton instance
export const redisManager = RedisManager.getInstance();

// Export client for direct access when needed
export const redisClient = redisManager.getClient();