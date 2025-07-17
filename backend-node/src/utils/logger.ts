import winston from 'winston';
import DailyRotateFile from 'winston-daily-rotate-file';
import { env } from '../config/env';
import path from 'path';

// Custom log levels for military context
const customLevels = {
  levels: {
    critical: 0,
    error: 1,
    warn: 2,
    security: 3,
    info: 4,
    debug: 5
  },
  colors: {
    critical: 'red bold',
    error: 'red',
    warn: 'yellow',
    security: 'magenta',
    info: 'cyan',
    debug: 'grey'
  }
};

// Hebrew-aware formatter
const hebrewFormatter = winston.format.combine(
  winston.format.timestamp({
    format: 'YYYY-MM-DD HH:mm:ss'
  }),
  winston.format.errors({ stack: true }),
  winston.format.json({
    replacer: (key, value) => {
      // Ensure Hebrew text is properly encoded
      if (typeof value === 'string' && /[\u0590-\u05FF]/.test(value)) {
        return Buffer.from(value, 'utf8').toString('utf8');
      }
      return value;
    }
  })
);

// Security-focused formatter for audit logs
const securityFormatter = winston.format.combine(
  winston.format.timestamp(),
  winston.format.errors({ stack: true }),
  winston.format.json(),
  winston.format.printf(({ timestamp, level, message, ...meta }) => {
    return JSON.stringify({
      timestamp,
      level,
      message,
      security_event: true,
      ...meta
    });
  })
);

// Create logger instance
export class Logger {
  private static instance: winston.Logger;

  static getInstance(): winston.Logger {
    if (!Logger.instance) {
      Logger.instance = winston.createLogger({
        levels: customLevels.levels,
        level: env.LOG_LEVEL,
        format: hebrewFormatter,
        defaultMeta: {
          service: 'IDF-Testing-Infrastructure',
          environment: env.NODE_ENV
        },
        transports: [
          // Console transport for development
          new winston.transports.Console({
            format: winston.format.combine(
              winston.format.colorize({ colors: customLevels.colors }),
              winston.format.simple()
            ),
            silent: env.NODE_ENV === 'test'
          }),

          // Application logs
          new DailyRotateFile({
            filename: path.join(env.LOG_DIRECTORY, 'application-%DATE%.log'),
            datePattern: 'YYYY-MM-DD',
            maxSize: env.LOG_FILE_MAX_SIZE,
            maxFiles: env.LOG_FILE_MAX_FILES,
            format: hebrewFormatter,
            level: 'info'
          }),

          // Error logs
          new DailyRotateFile({
            filename: path.join(env.LOG_DIRECTORY, 'error-%DATE%.log'),
            datePattern: 'YYYY-MM-DD',
            maxSize: env.LOG_FILE_MAX_SIZE,
            maxFiles: env.LOG_FILE_MAX_FILES,
            format: hebrewFormatter,
            level: 'error'
          }),

          // Security audit logs
          new DailyRotateFile({
            filename: path.join(env.LOG_DIRECTORY, 'security-%DATE%.log'),
            datePattern: 'YYYY-MM-DD',
            maxSize: env.LOG_FILE_MAX_SIZE,
            maxFiles: env.LOG_FILE_MAX_FILES * 2, // Keep security logs longer
            format: securityFormatter,
            level: 'security'
          }),

          // Critical alerts (for monitoring systems)
          new DailyRotateFile({
            filename: path.join(env.LOG_DIRECTORY, 'critical-%DATE%.log'),
            datePattern: 'YYYY-MM-DD',
            maxSize: env.LOG_FILE_MAX_SIZE,
            maxFiles: env.LOG_FILE_MAX_FILES * 3, // Keep critical logs even longer
            format: hebrewFormatter,
            level: 'critical'
          })
        ],
        
        // Handle uncaught exceptions and rejections
        exceptionHandlers: [
          new DailyRotateFile({
            filename: path.join(env.LOG_DIRECTORY, 'exceptions-%DATE%.log'),
            datePattern: 'YYYY-MM-DD',
            maxSize: env.LOG_FILE_MAX_SIZE,
            maxFiles: env.LOG_FILE_MAX_FILES
          })
        ],
        
        rejectionHandlers: [
          new DailyRotateFile({
            filename: path.join(env.LOG_DIRECTORY, 'rejections-%DATE%.log'),
            datePattern: 'YYYY-MM-DD',
            maxSize: env.LOG_FILE_MAX_SIZE,
            maxFiles: env.LOG_FILE_MAX_FILES
          })
        ]
      });

      // Add custom colors
      winston.addColors(customLevels.colors);
    }

    return Logger.instance;
  }

  // Convenience methods for structured logging
  static logSecurityEvent(event: string, details: any, userId?: string, ip?: string) {
    this.getInstance().log('security', `Security Event: ${event}`, {
      event,
      details,
      userId,
      ip,
      timestamp: new Date().toISOString()
    });
  }

  static logAuthEvent(action: string, userId: string, ip: string, success: boolean, details?: any) {
    this.getInstance().log('security', `Auth Event: ${action}`, {
      action,
      userId,
      ip,
      success,
      details,
      timestamp: new Date().toISOString()
    });
  }

  static logFileOperation(operation: string, fileId: string, userId: string, fileName?: string, details?: any) {
    this.getInstance().log('info', `File Operation: ${operation}`, {
      operation,
      fileId,
      userId,
      fileName,
      details,
      timestamp: new Date().toISOString()
    });
  }

  static logDatabaseOperation(operation: string, table: string, recordId?: string, userId?: string) {
    this.getInstance().log('info', `Database Operation: ${operation}`, {
      operation,
      table,
      recordId,
      userId,
      timestamp: new Date().toISOString()
    });
  }

  static logHebrewTextProcessing(operation: string, inputLength: number, outputLength: number, language: string) {
    this.getInstance().log('debug', `Hebrew Text Processing: ${operation}`, {
      operation,
      inputLength,
      outputLength,
      language,
      timestamp: new Date().toISOString()
    });
  }

  static logPerformanceMetric(operation: string, duration: number, details?: any) {
    this.getInstance().log('info', `Performance Metric: ${operation}`, {
      operation,
      duration,
      details,
      timestamp: new Date().toISOString()
    });
  }
}

// Export singleton instance
export const logger = Logger.getInstance();