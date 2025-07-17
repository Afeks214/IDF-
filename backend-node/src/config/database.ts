import { DataSource, DataSourceOptions } from 'typeorm';
import { env } from './env';
import { User } from '../models/User';
import { ExcelFile } from '../models/ExcelFile';
import { TestingData } from '../models/TestingData';
import { AuditLog } from '../models/AuditLog';

// Database configuration with military-grade security settings
const baseConfig: DataSourceOptions = {
  type: 'postgres',
  host: env.DB_HOST,
  port: env.DB_PORT,
  username: env.DB_USERNAME,
  password: env.DB_PASSWORD,
  database: env.DB_NAME,
  synchronize: env.NODE_ENV === 'development', // Only in development
  logging: env.NODE_ENV === 'development' ? ['query', 'error'] : ['error'],
  entities: [User, ExcelFile, TestingData, AuditLog],
  migrations: ['src/migrations/**/*.ts'],
  subscribers: ['src/subscribers/**/*.ts'],
  ssl: env.DB_SSL ? {
    rejectUnauthorized: false, // Configure based on your SSL setup
  } : false,
  extra: {
    // Connection pool configuration for performance
    min: env.DB_POOL_MIN,
    max: env.DB_POOL_MAX,
    // Connection security settings
    application_name: 'IDF_Testing_Infrastructure',
    // Connection timeout settings
    connectionTimeoutMillis: 30000,
    idleTimeoutMillis: 30000,
    // Enable prepared statements for security
    statement_timeout: 30000,
    // Database security parameters
    ssl_prefer_server_ciphers: 'on',
  },
  // Enable automatic retries for resilience
  connectTimeoutMS: 30000,
  acquireTimeoutMS: 30000,
  timeout: 30000,
};

// Create DataSource instance
export const AppDataSource = new DataSource(baseConfig);

// Database connection management
export class DatabaseManager {
  private static instance: DatabaseManager;
  private dataSource: DataSource;
  private isConnected = false;

  private constructor() {
    this.dataSource = AppDataSource;
  }

  public static getInstance(): DatabaseManager {
    if (!DatabaseManager.instance) {
      DatabaseManager.instance = new DatabaseManager();
    }
    return DatabaseManager.instance;
  }

  async connect(): Promise<void> {
    try {
      if (!this.isConnected) {
        await this.dataSource.initialize();
        this.isConnected = true;
        console.log('✅ Database connection established successfully');
        
        // Run pending migrations in production
        if (env.NODE_ENV === 'production') {
          await this.dataSource.runMigrations();
          console.log('✅ Database migrations completed');
        }
      }
    } catch (error) {
      console.error('❌ Database connection failed:', error);
      throw new Error(`Database connection failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  async disconnect(): Promise<void> {
    try {
      if (this.isConnected && this.dataSource.isInitialized) {
        await this.dataSource.destroy();
        this.isConnected = false;
        console.log('✅ Database connection closed successfully');
      }
    } catch (error) {
      console.error('❌ Error closing database connection:', error);
    }
  }

  getDataSource(): DataSource {
    if (!this.isConnected) {
      throw new Error('Database not connected. Call connect() first.');
    }
    return this.dataSource;
  }

  isConnectionActive(): boolean {
    return this.isConnected && this.dataSource.isInitialized;
  }

  // Health check for monitoring
  async healthCheck(): Promise<{ status: 'healthy' | 'unhealthy'; latency?: number; error?: string }> {
    try {
      const startTime = Date.now();
      await this.dataSource.query('SELECT 1');
      const latency = Date.now() - startTime;
      
      return {
        status: 'healthy',
        latency
      };
    } catch (error) {
      return {
        status: 'unhealthy',
        error: error instanceof Error ? error.message : 'Unknown database error'
      };
    }
  }
}

// Export singleton instance
export const databaseManager = DatabaseManager.getInstance();

// Export DataSource for migrations and other TypeORM operations
export default AppDataSource;