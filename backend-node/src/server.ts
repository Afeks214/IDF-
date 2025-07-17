import 'reflect-metadata';
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import morgan from 'morgan';
import { env } from './config/env';
import { databaseManager } from './config/database';
import { redisManager } from './config/redis';
import { logger } from './utils/logger';
import { errorHandler, notFoundHandler, setupGlobalErrorHandlers } from './middleware/errorHandler';
import { securityHeaders, sanitizeInput, securityLogger, apiRateLimit } from './middleware/security';

// Import routes
import authRoutes from './routes/auth';
import testingDataRoutes from './routes/testing-data';

class Server {
  private app: express.Application;

  constructor() {
    this.app = express();
    this.setupGlobalErrorHandlers();
    this.setupMiddleware();
    this.setupRoutes();
    this.setupErrorHandling();
  }

  private setupGlobalErrorHandlers(): void {
    setupGlobalErrorHandlers();
  }

  private setupMiddleware(): void {
    // Security middleware
    this.app.use(helmet(securityHeaders));
    this.app.use(securityLogger);
    
    // CORS configuration
    this.app.use(cors({
      origin: env.CORS_ORIGINS.split(','),
      credentials: true,
      methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
      allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With']
    }));

    // Basic middleware
    this.app.use(compression());
    this.app.use(express.json({ limit: env.BODY_LIMIT }));
    this.app.use(express.urlencoded({ extended: true, limit: env.BODY_LIMIT }));
    
    // Logging middleware
    this.app.use(morgan('combined', {
      stream: {
        write: (message: string) => logger.info(message.trim())
      }
    }));

    // Security middleware
    this.app.use(sanitizeInput);
    this.app.use(apiRateLimit);

    // Trust proxy for correct IP addresses
    if (env.NODE_ENV === 'production') {
      this.app.set('trust proxy', env.TRUSTED_PROXIES.split(','));
    }
  }

  private setupRoutes(): void {
    // Health check endpoint
    this.app.get('/health', async (req, res) => {
      try {
        const [dbHealth, redisHealth] = await Promise.all([
          databaseManager.healthCheck(),
          redisManager.healthCheck()
        ]);

        const health = {
          status: 'healthy',
          timestamp: new Date().toISOString(),
          version: '1.0.0',
          services: {
            database: dbHealth,
            redis: redisHealth
          },
          uptime: process.uptime(),
          memory: process.memoryUsage(),
          environment: env.NODE_ENV
        };

        const overallHealthy = dbHealth.status === 'healthy' && redisHealth.status === 'healthy';
        res.status(overallHealthy ? 200 : 503).json(health);
      } catch (error) {
        res.status(503).json({
          status: 'unhealthy',
          timestamp: new Date().toISOString(),
          error: error instanceof Error ? error.message : 'Unknown error'
        });
      }
    });

    // Root endpoint with Hebrew support info
    this.app.get('/', (req, res) => {
      res.json({
        message: 'IDF Testing Infrastructure API',
        version: '1.0.0',
        status: 'operational',
        features: {
          hebrewSupport: true,
          rtlText: true,
          militaryGradeSecurity: true,
          excelProcessing: true
        },
        documentation: `${req.protocol}://${req.get('host')}/api/docs`,
        health: `${req.protocol}://${req.get('host')}/health`
      });
    });

    // API routes
    this.app.use('/api/auth', authRoutes);
    this.app.use('/api/testing-data', testingDataRoutes);

    // Swagger documentation (if enabled)
    if (env.SWAGGER_ENABLED) {
      this.setupSwagger();
    }
  }

  private setupSwagger(): void {
    try {
      const swaggerUi = require('swagger-ui-express');
      const swaggerJSDoc = require('swagger-jsdoc');

      const swaggerOptions = {
        definition: {
          openapi: '3.0.0',
          info: {
            title: 'IDF Testing Infrastructure API',
            version: '1.0.0',
            description: 'Military-grade API for testing infrastructure management with Hebrew support',
            contact: {
              name: 'IDF Testing Infrastructure Team',
              email: 'support@idf-testing.mil'
            }
          },
          servers: [
            {
              url: `http://localhost:${env.PORT}`,
              description: 'Development server'
            }
          ],
          components: {
            securitySchemes: {
              BearerAuth: {
                type: 'http',
                scheme: 'bearer',
                bearerFormat: 'JWT'
              }
            }
          },
          security: [
            {
              BearerAuth: []
            }
          ]
        },
        apis: ['./src/routes/*.ts', './src/controllers/*.ts']
      };

      const swaggerSpec = swaggerJSDoc(swaggerOptions);
      
      this.app.use('/api/docs', swaggerUi.serve);
      this.app.get('/api/docs', swaggerUi.setup(swaggerSpec, {
        customCss: `
          .swagger-ui .topbar { display: none; }
          .swagger-ui .info .title { color: #1f4e79; }
          body { direction: ltr; }
        `,
        customSiteTitle: 'IDF Testing Infrastructure API Documentation'
      }));

      this.app.get('/api/docs.json', (req, res) => {
        res.setHeader('Content-Type', 'application/json');
        res.send(swaggerSpec);
      });

      logger.info('Swagger documentation enabled at /api/docs');
    } catch (error) {
      logger.warn('Failed to setup Swagger documentation', { error });
    }
  }

  private setupErrorHandling(): void {
    // 404 handler
    this.app.use(notFoundHandler);
    
    // Global error handler
    this.app.use(errorHandler);
  }

  public async start(): Promise<void> {
    try {
      // Initialize database connection
      await databaseManager.connect();
      logger.info('Database connected successfully');

      // Initialize Redis connection
      await redisManager.connect();
      logger.info('Redis connected successfully');

      // Start server
      this.app.listen(env.PORT, () => {
        logger.info(`🚀 IDF Testing Infrastructure API started`, {
          port: env.PORT,
          environment: env.NODE_ENV,
          hebrewSupport: true,
          documentation: env.SWAGGER_ENABLED ? `http://localhost:${env.PORT}/api/docs` : 'disabled'
        });
      });

    } catch (error) {
      logger.error('Failed to start server', { error });
      process.exit(1);
    }
  }

  public getApp(): express.Application {
    return this.app;
  }
}

// Create and start server
if (require.main === module) {
  const server = new Server();
  server.start();
}

export default Server;