import dotenv from 'dotenv';
import { cleanEnv, str, num, bool, port } from 'envalid';

// Load environment variables
dotenv.config();

export const env = cleanEnv(process.env, {
  // Application
  NODE_ENV: str({ choices: ['development', 'production', 'test'], default: 'development' }),
  PORT: port({ default: 3000 }),
  API_VERSION: str({ default: 'v1' }),
  API_PREFIX: str({ default: '/api/v1' }),

  // Database
  DB_HOST: str({ default: 'localhost' }),
  DB_PORT: port({ default: 5432 }),
  DB_USERNAME: str(),
  DB_PASSWORD: str(),
  DB_NAME: str(),
  DB_SSL: bool({ default: false }),
  DB_POOL_MIN: num({ default: 2 }),
  DB_POOL_MAX: num({ default: 10 }),

  // JWT
  JWT_SECRET: str({ minLength: 32 }),
  JWT_EXPIRES_IN: str({ default: '24h' }),
  JWT_REFRESH_SECRET: str({ minLength: 32 }),
  JWT_REFRESH_EXPIRES_IN: str({ default: '7d' }),

  // Redis
  REDIS_HOST: str({ default: 'localhost' }),
  REDIS_PORT: port({ default: 6379 }),
  REDIS_PASSWORD: str({ default: '' }),
  REDIS_DB: num({ default: 0 }),
  REDIS_CLUSTER: bool({ default: false }),

  // Security
  BCRYPT_ROUNDS: num({ default: 12 }),
  RATE_LIMIT_WINDOW_MS: num({ default: 900000 }), // 15 minutes
  RATE_LIMIT_MAX_REQUESTS: num({ default: 100 }),
  CORS_ORIGINS: str({ default: 'http://localhost:3000' }),
  TRUSTED_PROXIES: str({ default: '127.0.0.1,::1' }),

  // File Upload
  MAX_FILE_SIZE: num({ default: 10485760 }), // 10MB
  UPLOAD_PATH: str({ default: './uploads' }),
  ALLOWED_FILE_TYPES: str({ default: '.xlsx,.xls,.csv' }),
  MAX_FILES_PER_REQUEST: num({ default: 5 }),

  // Hebrew Text Processing
  HEBREW_VALIDATION: bool({ default: true }),
  RTL_SUPPORT: bool({ default: true }),
  UNICODE_NORMALIZATION: bool({ default: true }),

  // Logging
  LOG_LEVEL: str({ choices: ['error', 'warn', 'info', 'debug'], default: 'info' }),
  LOG_FORMAT: str({ choices: ['json', 'simple'], default: 'json' }),
  LOG_FILE_MAX_SIZE: str({ default: '50m' }),
  LOG_FILE_MAX_FILES: num({ default: 14 }),
  LOG_DIRECTORY: str({ default: './logs' }),

  // Email (optional)
  SMTP_HOST: str({ default: '' }),
  SMTP_PORT: port({ default: 587 }),
  SMTP_SECURE: bool({ default: false }),
  SMTP_USER: str({ default: '' }),
  SMTP_PASSWORD: str({ default: '' }),

  // Monitoring
  ENABLE_METRICS: bool({ default: true }),
  ENABLE_HEALTH_CHECK: bool({ default: true }),
  REQUEST_TIMEOUT: num({ default: 30000 }),
  BODY_LIMIT: str({ default: '10mb' }),

  // Development
  DEBUG: bool({ default: false }),
  SWAGGER_ENABLED: bool({ default: true }),
});

export default env;