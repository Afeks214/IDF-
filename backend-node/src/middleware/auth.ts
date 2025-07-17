import { Request, Response, NextFunction } from 'express';
import { AuthService } from '../services/AuthService';
import { UserRole } from '../models/User';

declare global {
  namespace Express {
    interface Request {
      user?: {
        userId: string;
        email: string;
        role: UserRole;
      };
    }
  }
}

export class AuthMiddleware {
  private authService = new AuthService();

  authenticateToken = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const authHeader = req.headers.authorization;
      const token = authHeader?.startsWith('Bearer ') ? authHeader.slice(7) : null;

      if (!token) {
        res.status(401).json({
          error: 'UNAUTHORIZED',
          message: 'אין אסימון גישה',
          hebrewMessage: 'Access token required'
        });
        return;
      }

      const decoded = await this.authService.verifyToken(token);
      req.user = {
        userId: decoded.userId,
        email: decoded.email,
        role: decoded.role
      };

      next();
    } catch (error) {
      res.status(401).json({
        error: 'INVALID_TOKEN',
        message: 'אסימון גישה לא חוקי',
        hebrewMessage: 'Invalid access token'
      });
    }
  };

  requireRole = (roles: UserRole | UserRole[]) => {
    return (req: Request, res: Response, next: NextFunction): void => {
      if (!req.user) {
        res.status(401).json({
          error: 'UNAUTHORIZED',
          message: 'משתמש לא מזוהה'
        });
        return;
      }

      const allowedRoles = Array.isArray(roles) ? roles : [roles];
      
      if (!allowedRoles.includes(req.user.role)) {
        res.status(403).json({
          error: 'INSUFFICIENT_PERMISSIONS',
          message: 'אין הרשאות מתאימות',
          required: allowedRoles,
          current: req.user.role
        });
        return;
      }

      next();
    };
  };

  requireAdmin = this.requireRole(UserRole.ADMIN);
  
  requireInspector = this.requireRole([UserRole.ADMIN, UserRole.INSPECTOR]);
  
  requireManager = this.requireRole([UserRole.ADMIN, UserRole.BUILDING_MANAGER]);
}

export const authMiddleware = new AuthMiddleware();