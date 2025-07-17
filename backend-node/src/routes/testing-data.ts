import { Router } from 'express';
import { TestingDataController } from '../controllers/TestingDataController';
import { authMiddleware } from '../middleware/auth';
import { UserRole } from '../models/User';

const router = Router();
const controller = new TestingDataController();

// Apply authentication to all routes
router.use(authMiddleware.authenticateToken);

// Get all testing data with filtering and pagination
router.get('/', controller.getAll);

// Get statistics
router.get('/stats', controller.getStats);

// Get testing data by ID
router.get('/:id', controller.getById);

// Update testing data (requires inspector or admin role)
router.put('/:id',
  authMiddleware.requireRole([UserRole.ADMIN, UserRole.INSPECTOR]),
  controller.update
);

// Delete testing data (admin only)
router.delete('/:id',
  authMiddleware.requireAdmin,
  controller.delete
);

export default router;