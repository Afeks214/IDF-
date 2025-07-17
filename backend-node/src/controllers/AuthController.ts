import { Request, Response } from 'express';
import { AuthService } from '../services/AuthService';
import { validationResult } from 'express-validator';

export class AuthController {
  private authService = new AuthService();

  login = async (req: Request, res: Response): Promise<void> => {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        res.status(400).json({
          error: 'VALIDATION_ERROR',
          message: 'שגיאות בתתי הקלט',
          details: errors.array()
        });
        return;
      }

      const { email, password } = req.body;
      const ipAddress = req.ip || req.socket.remoteAddress || 'unknown';

      const result = await this.authService.login(email, password, ipAddress);

      res.json({
        success: true,
        message: 'התחברות מוצלחת',
        data: result
      });
    } catch (error) {
      res.status(401).json({
        error: 'LOGIN_FAILED',
        message: error instanceof Error ? error.message : 'שגיאה בהתחברות'
      });
    }
  };

  refreshToken = async (req: Request, res: Response): Promise<void> => {
    try {
      const { refreshToken } = req.body;

      if (!refreshToken) {
        res.status(400).json({
          error: 'MISSING_REFRESH_TOKEN',
          message: 'אסימון רענון נדרש'
        });
        return;
      }

      const result = await this.authService.refreshToken(refreshToken);

      res.json({
        success: true,
        message: 'אסימון עודכן בהצלחה',
        data: result
      });
    } catch (error) {
      res.status(401).json({
        error: 'REFRESH_FAILED',
        message: 'אסימון רענון לא חוקי'
      });
    }
  };

  logout = async (req: Request, res: Response): Promise<void> => {
    try {
      const authHeader = req.headers.authorization;
      const accessToken = authHeader?.startsWith('Bearer ') ? authHeader.slice(7) : '';
      const { refreshToken } = req.body;

      await this.authService.logout(accessToken, refreshToken);

      res.json({
        success: true,
        message: 'התנתקות מוצלחת'
      });
    } catch (error) {
      res.status(500).json({
        error: 'LOGOUT_FAILED',
        message: 'שגיאה בהתנתקות'
      });
    }
  };

  me = async (req: Request, res: Response): Promise<void> => {
    res.json({
      success: true,
      data: req.user
    });
  };
}