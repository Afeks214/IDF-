import { Request, Response, NextFunction } from 'express';
import { Logger } from '../utils/logger';
import { env } from '../config/env';

export interface ApiError extends Error {
  statusCode?: number;
  code?: string;
  details?: any;
  isOperational?: boolean;
}

export class AppError extends Error implements ApiError {
  public statusCode: number;
  public code: string;
  public isOperational: boolean;
  public details?: any;

  constructor(message: string, statusCode: number = 500, code?: string, details?: any) {
    super(message);
    this.statusCode = statusCode;
    this.code = code || 'INTERNAL_ERROR';
    this.isOperational = true;
    this.details = details;

    Error.captureStackTrace(this, this.constructor);
  }
}

// Predefined error types with Hebrew messages
export class ValidationError extends AppError {
  constructor(message: string, details?: any) {
    super(message, 400, 'VALIDATION_ERROR', details);
  }
}

export class AuthenticationError extends AppError {
  constructor(message: string = 'לא מורשה') {
    super(message, 401, 'AUTHENTICATION_ERROR');
  }
}

export class AuthorizationError extends AppError {
  constructor(message: string = 'אין הרשאות מתאימות') {
    super(message, 403, 'AUTHORIZATION_ERROR');
  }
}

export class NotFoundError extends AppError {
  constructor(message: string = 'המשאב לא נמצא') {
    super(message, 404, 'NOT_FOUND');
  }
}

export class ConflictError extends AppError {
  constructor(message: string = 'קונפליקט במידע') {
    super(message, 409, 'CONFLICT');
  }
}

export class RateLimitError extends AppError {
  constructor(message: string = 'נחרגת ממגבלת הבקשות') {
    super(message, 429, 'RATE_LIMIT_EXCEEDED');
  }
}

export class FileUploadError extends AppError {
  constructor(message: string, details?: any) {
    super(message, 400, 'FILE_UPLOAD_ERROR', details);
  }
}

export class DatabaseError extends AppError {
  constructor(message: string = 'שגיאה במסד הנתונים', details?: any) {
    super(message, 500, 'DATABASE_ERROR', details);
  }
}

// Global error handler middleware
export const errorHandler = (error: ApiError, req: Request, res: Response, next: NextFunction): void => {
  let statusCode = error.statusCode || 500;
  let code = error.code || 'INTERNAL_ERROR';
  let message = error.message || 'שגיאה פנימית';

  // Handle specific error types
  if (error.name === 'ValidationError') {
    statusCode = 400;
    code = 'VALIDATION_ERROR';
    message = 'שגיאות בולידציה';
  } else if (error.name === 'CastError') {
    statusCode = 400;
    code = 'INVALID_ID';
    message = 'מזהה לא חוקי';
  } else if (error.name === 'MulterError') {
    statusCode = 400;
    code = 'FILE_UPLOAD_ERROR';
    
    if (error.message.includes('File too large')) {
      message = 'הקובץ גדול מדי';
    } else if (error.message.includes('Too many files')) {
      message = 'יותר מדי קבצים';
    } else {
      message = 'שגיאה בהעלאת הקובץ';
    }
  } else if (error.name === 'JsonWebTokenError') {
    statusCode = 401;
    code = 'INVALID_TOKEN';
    message = 'אסימון לא חוקי';
  } else if (error.name === 'TokenExpiredError') {
    statusCode = 401;
    code = 'TOKEN_EXPIRED';
    message = 'אסימון פג תוקף';
  }

  // Log error with appropriate level
  const logLevel = statusCode >= 500 ? 'error' : 'warn';
  const logMessage = `${req.method} ${req.originalUrl} - ${statusCode} - ${message}`;
  
  Logger.getInstance().log(logLevel, logMessage, {
    error: {
      name: error.name,
      message: error.message,
      stack: error.stack,
      code,
      statusCode
    },
    request: {
      method: req.method,
      url: req.originalUrl,
      ip: req.ip,
      userAgent: req.get('User-Agent'),
      userId: req.user?.userId,
      body: req.body,
      params: req.params,
      query: req.query
    }
  });

  // Log security events for suspicious activity
  if (statusCode === 401 || statusCode === 403) {
    Logger.logSecurityEvent('Unauthorized Access Attempt', {
      statusCode,
      message,
      url: req.originalUrl,
      method: req.method
    }, req.user?.userId, req.ip);
  }

  // Prepare response
  const response: any = {
    success: false,
    error: code,
    message,
    timestamp: new Date().toISOString(),
    path: req.originalUrl
  };

  // Include details in development mode
  if (env.NODE_ENV === 'development') {
    response.details = {
      stack: error.stack,
      originalMessage: error.message
    };
  }

  // Include validation details if available
  if (error.details) {
    response.details = error.details;
  }

  res.status(statusCode).json(response);
};

// Handle 404 errors
export const notFoundHandler = (req: Request, res: Response): void => {
  const message = `הנתיב ${req.originalUrl} לא נמצא`;
  
  Logger.getInstance().warn('Route not found', {
    method: req.method,
    url: req.originalUrl,
    ip: req.ip,
    userAgent: req.get('User-Agent')
  });

  res.status(404).json({
    success: false,
    error: 'NOT_FOUND',
    message,
    timestamp: new Date().toISOString(),
    path: req.originalUrl
  });
};

// Async error wrapper
export const asyncHandler = (fn: Function) => (req: Request, res: Response, next: NextFunction) => {
  Promise.resolve(fn(req, res, next)).catch(next);
};

// Process unhandled errors
export const setupGlobalErrorHandlers = (): void => {
  process.on('uncaughtException', (error: Error) => {
    Logger.getInstance().log('critical', 'Uncaught Exception', {
      error: {
        name: error.name,
        message: error.message,
        stack: error.stack
      }
    });
    
    process.exit(1);
  });

  process.on('unhandledRejection', (reason: any, promise: Promise<any>) => {
    Logger.getInstance().log('critical', 'Unhandled Promise Rejection', {
      reason,
      promise: promise.toString()
    });
    
    process.exit(1);
  });

  // Graceful shutdown on SIGTERM
  process.on('SIGTERM', () => {
    Logger.getInstance().info('SIGTERM received, shutting down gracefully');
    process.exit(0);
  });

  // Graceful shutdown on SIGINT
  process.on('SIGINT', () => {
    Logger.getInstance().info('SIGINT received, shutting down gracefully');
    process.exit(0);
  });
};