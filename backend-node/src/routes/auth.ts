import { Router } from 'express';
import { body } from 'express-validator';
import { AuthController } from '../controllers/AuthController';
import { authMiddleware } from '../middleware/auth';
import { loginRateLimit } from '../middleware/security';

const router = Router();
const authController = new AuthController();

// Login endpoint with validation and rate limiting
router.post('/login',
  loginRateLimit,
  [
    body('email')
      .isEmail()
      .withMessage('כתובת אימייל לא חוקית')
      .normalizeEmail(),
    body('password')
      .isLength({ min: 6 })
      .withMessage('סיסמה חייבת להיות לפחות 6 תווים')
  ],
  authController.login
);

// Refresh token endpoint
router.post('/refresh',
  authController.refreshToken
);

// Logout endpoint
router.post('/logout',
  authMiddleware.authenticateToken,
  authController.logout
);

// Get current user info
router.get('/me',
  authMiddleware.authenticateToken,
  authController.me
);

export default router;